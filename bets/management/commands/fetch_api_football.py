# bets/management/commands/fetch_api_football.py
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from bets.utils.api_football import (
    get_teams_by_league,
    get_league,
    get_fixtures_by_league,
    search_teams_by_country
)

from bets.models import ApiEquipo, ApiLiga, ApiPais, Deporte

# Default leagues (IDs often used in API-Football; you can override with --leagues)
DEFAULT_LEAGUES = [
    239,  # Liga Colombiana (Categoría Primera A)
    140,  # La Liga (España)
    39,   # Premier League (Inglaterra)
    135,  # Serie A (Italia)
    2,    # UEFA Champions League
]


# Example: Countries for national teams (FIFA)
DEFAULT_COUNTRIES = [
    # Sudamérica
    'Colombia', 'Brazil', 'Argentina', 'Uruguay', 'Chile', 'Peru', 'Ecuador', 'Paraguay',
    # Europa principales
    'Spain', 'Italy', 'England', 'France', 'Germany', 'Portugal', 'Netherlands', 'Belgium',
    # Otros
    'Mexico', 'USA', 'Japan', 'South Korea'
]

def find_country(country_code: str, country_name: str):
    """
    Try to find ApiPais by code (country code) or by name. Returns ApiPais or None.
    """
    if country_code:
        p = ApiPais.objects.filter(code__iexact=country_code).first()
        if p:
            return p
    if country_name:
        p = ApiPais.objects.filter(nombre__iexact=country_name).first()
        if p:
            return p
    return None

def get_football_deporte():
    """
    Try to find Deporte record for football. Fallback to the first Deporte.
    """
    de = Deporte.objects.filter(nombre__icontains='futbol').first()
    if not de:
        de = Deporte.objects.first()
    return de

class Command(BaseCommand):
    help = 'Fetch leagues, teams and fixtures from API-Football and upsert into DB'

    def add_arguments(self, parser):
        parser.add_argument('--leagues', nargs='*', type=int, help='List of league IDs to fetch', default=DEFAULT_LEAGUES)
        parser.add_argument('--season', type=int, help='Season year to fetch (e.g., 2024)', default=None)
        parser.add_argument('--countries', nargs='*', type=str, help='Country names for national teams', default=DEFAULT_COUNTRIES)
        parser.add_argument('--fixtures_for', nargs='*', type=int, help='League IDs to fetch upcoming fixtures for', default=[])

    def handle(self, *args, **options):
        from bets.utils.api_counter import get_today_count, get_remaining_requests, DAILY_LIMIT, reset_old_counts

        leagues = options['leagues']
        season = options['season']
        countries = options['countries'] or []
        fixtures_for = options['fixtures_for'] or []

        # Limpiar conteos antiguos al inicio
        reset_old_counts()

        # Mostrar estado inicial de peticiones
        initial_count = get_today_count()
        initial_remaining = get_remaining_requests()

        self.stdout.write(self.style.WARNING(
            f"\n{'='*60}\n"
            f"📊 ESTADO DE PETICIONES API\n"
            f"{'='*60}\n"
            f"   Peticiones usadas hoy: {initial_count}/{DAILY_LIMIT}\n"
            f"   Peticiones disponibles: {initial_remaining}\n"
            f"   Porcentaje usado: {round((initial_count/DAILY_LIMIT)*100, 1)}%\n"
            f"{'='*60}\n"
        ))

        if initial_remaining < 20:
            self.stdout.write(self.style.WARNING(
                f"⚠️  ADVERTENCIA: Quedan menos de 20 peticiones disponibles.\n"
                f"   Considera ejecutar este comando mañana o actualizar tu plan.\n"
            ))

        deporte = get_football_deporte()
        if not deporte:
            self.stdout.write(self.style.ERROR('No Deporte found in DB. Please create a Deporte record first.'))
            return

        self.stdout.write(self.style.NOTICE(f"Using Deporte: {deporte.nombre}"))

        # Fetch league metadata & teams
        for league_id in leagues:
            try:
                self.stdout.write(self.style.NOTICE(f"Fetching league {league_id} (season={season})..."))
                league_resp = get_league(league_id, season)  # may return areas/leagues
                # league_resp['response'] is an array
                leagues_resp = league_resp.get('response', [])
                if leagues_resp:
                    league_data = leagues_resp[0].get('league', {})
                    country_data = leagues_resp[0].get('country', {})
                    comp_name = league_data.get('name') or f"League {league_id}"
                    comp_logo = league_data.get('logo') or None
                    comp_country = country_data.get('name')
                    comp_country_code = country_data.get('code')  # ISO2 if available

                    # Match country to ApiPais
                    pais = find_country(comp_country_code, comp_country)
                    liga_obj, _ = ApiLiga.objects.get_or_create(
                        api_id=league_id,
                        defaults={
                            'nombre': comp_name,
                            'logo_url': comp_logo or None,
                            'id_pais': pais,
                            'id_deporte': deporte,
                            'tipo': league_data.get('type', 'League')
                        }
                    )
                    # update logo if changed
                    if comp_logo and liga_obj.logo_url != comp_logo:
                        liga_obj.logo_url = comp_logo
                        liga_obj.save()
                    self.stdout.write(self.style.SUCCESS(f"Upserted competition: {liga_obj.nombre}"))
                else:
                    self.stdout.write(self.style.WARNING(f"No league info returned for {league_id}"))

                # fetch teams in league
                teams_resp = get_teams_by_league(league_id, season or timezone.now().year)
                teams = teams_resp.get('response', [])
                for t in teams:
                    team = t.get('team', {})
                    team_name = team.get('name')
                    team_logo = team.get('logo') or None
                    team_country = t.get('country', {}).get('name') or team.get('country') or None
                    team_country_code = t.get('country', {}).get('code') or None

                    # find ApiPais
                    pais = find_country(team_country_code, team_country)
                    # Get team API ID from response
                    team_api_id = team.get('id')
                    # upsert ApiEquipo by api_id
                    eq, created = ApiEquipo.objects.get_or_create(
                        api_id=team_api_id,
                        defaults={
                            'nombre': team_name,
                            'logo_url': team_logo or None,
                            'id_pais': pais,
                            'id_deporte': deporte,
                            'tipo': 'Club'
                        }
                    )
                    # update logo or country if changed
                    changed = False
                    if team_logo and eq.logo_url != team_logo:
                        eq.logo_url = team_logo
                        changed = True
                    if pais and eq.id_pais != pais:
                        eq.id_pais = pais
                        changed = True
                    if changed:
                        eq.save()
                    self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} team: {eq.nombre}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error with league {league_id}: {e}"))

        # Fetch national teams by country (search teams by country)
        for country in countries:
            try:
                self.stdout.write(self.style.NOTICE(f"Searching national teams for country: {country}"))
                resp = search_teams_by_country(country)
                results = resp.get('response', [])
                for r in results:
                    team = r.get('team', {})
                    team_name = team.get('name')
                    team_logo = team.get('logo') or None
                    team_country = r.get('country', {}).get('name') or None
                    team_country_code = r.get('country', {}).get('code') or None
                    is_national = team.get('national', False)

                    # Only save national teams (skip clubs)
                    if not is_national:
                        continue

                    pais = find_country(team_country_code, team_country)
                    team_api_id = team.get('id')
                    eq, created = ApiEquipo.objects.get_or_create(
                        api_id=team_api_id,
                        defaults={
                            'nombre': team_name,
                            'logo_url': team_logo or None,
                            'id_pais': pais,
                            'id_deporte': deporte,
                            'tipo': 'National'
                        }
                    )
                    changed = False
                    if team_logo and eq.logo_url != team_logo:
                        eq.logo_url = team_logo
                        changed = True
                    if pais and eq.id_pais != pais:
                        eq.id_pais = pais
                        changed = True
                    if changed:
                        eq.save()
                    self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} national team: {eq.nombre}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching teams for country {country}: {e}"))

        # Fetch upcoming fixtures for requested competitions (useful for qualifiers)
        for comp_id in fixtures_for:
            try:
                self.stdout.write(self.style.NOTICE(f"Fetching next fixtures for competition {comp_id}"))
                fx = get_fixtures_by_league(comp_id, season or timezone.now().year, next_=10)  # next 10 fixtures
                fixtures = fx.get('response', [])
                for f in fixtures:
                    # This command only logs fixtures for now and leaves insertion to later
                    fixture_time = f.get('fixture', {}).get('date')
                    teams = f.get('teams', {})
                    home = teams.get('home', {}).get('name')
                    away = teams.get('away', {}).get('name')
                    self.stdout.write(self.style.SUCCESS(f"Fixture: {home} vs {away} @ {fixture_time}"))
                self.stdout.write(self.style.NOTICE(f"Fetched {len(fixtures)} fixtures for competition {comp_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching fixtures for {comp_id}: {e}"))

        # Mostrar resumen final de peticiones
        final_count = get_today_count()
        final_remaining = get_remaining_requests()
        used_in_this_run = final_count - initial_count

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n"
            f"✅ COMANDO COMPLETADO\n"
            f"{'='*60}\n"
            f"   Peticiones usadas en esta ejecución: {used_in_this_run}\n"
            f"   Total usado hoy: {final_count}/{DAILY_LIMIT}\n"
            f"   Peticiones restantes: {final_remaining}\n"
            f"   Porcentaje usado: {round((final_count/DAILY_LIMIT)*100, 1)}%\n"
            f"{'='*60}\n"
        ))

        if final_remaining <= 10:
            self.stdout.write(self.style.ERROR(
                f"🔴 ALERTA: Solo quedan {final_remaining} peticiones!\n"
                f"   Ten cuidado al ejecutar comandos adicionales.\n"
            ))
        elif final_remaining <= 30:
            self.stdout.write(self.style.WARNING(
                f"🟡 ATENCIÓN: Quedan {final_remaining} peticiones disponibles.\n"
            ))

        self.stdout.write(self.style.SUCCESS("Done."))
