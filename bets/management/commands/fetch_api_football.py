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
    # Common league ids used by api-football (these are common but may vary by API plan)
    39,   # Premier League (England)
    140,  # LaLiga (Spain) - sometimes 140 or 2019; adjust if necessary
    135,  # Serie A (Italy)
    61    # Ligue 1 (France)
]

# Example: Countries for national teams (FIFA)
DEFAULT_COUNTRIES = [
    'Colombia', 'Brazil', 'Argentina', 'Uruguay', 'Chile', 'Peru',
    'Spain', 'Italy', 'France', 'England'
]

def find_country(country_code: str, country_name: str):
    """
    Try to find ApiPais by codigo (country code) or by name. Returns ApiPais or None.
    """
    if country_code:
        p = ApiPais.objects.filter(codigo__iexact=country_code).first()
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
        leagues = options['leagues']
        season = options['season']
        countries = options['countries'] or []
        fixtures_for = options['fixtures_for'] or []

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
                        api_league_id=league_id,
                        defaults={
                            'nombre': comp_name,
                            'logo': comp_logo or None,
                            'id_pais': pais,
                            'tipo': league_data.get('type', 'League')
                        }
                    )
                    # update logo if changed
                    if comp_logo and liga_obj.logo != comp_logo:
                        liga_obj.logo = comp_logo
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
                    # upsert ApiEquipo by api_team_id
                    eq, created = ApiEquipo.objects.get_or_create(
                        api_team_id=team_api_id,
                        defaults={
                            'nombre': team_name,
                            'logo': team_logo or None,
                            'id_pais': pais
                        }
                    )
                    # update logo or country if changed
                    changed = False
                    if team_logo and eq.logo != team_logo:
                        eq.logo = team_logo
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
                self.stdout.write(self.style.NOTICE(f"Searching teams for country: {country}"))
                resp = search_teams_by_country(country)
                results = resp.get('response', [])
                for r in results:
                    team = r.get('team', {})
                    team_name = team.get('name')
                    team_logo = team.get('logo') or None
                    team_country = r.get('country', {}).get('name') or None
                    team_country_code = r.get('country', {}).get('code') or None

                    pais = find_country(team_country_code, team_country)
                    team_api_id = team.get('id')
                    eq, created = ApiEquipo.objects.get_or_create(
                        api_team_id=team_api_id,
                        defaults={
                            'nombre': team_name,
                            'logo': team_logo or None,
                            'id_pais': pais
                        }
                    )
                    changed = False
                    if team_logo and eq.logo != team_logo:
                        eq.logo = team_logo
                        changed = True
                    if pais and eq.id_pais != pais:
                        eq.id_pais = pais
                        changed = True
                    if changed:
                        eq.save()
                    self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} national/team: {eq.nombre}"))
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

        self.stdout.write(self.style.SUCCESS("Done."))
