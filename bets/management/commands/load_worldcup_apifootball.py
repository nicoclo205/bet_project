"""
Comando Django para cargar equipos y partidos de la Copa Mundial FIFA 2026
usando API-Football (api-football.com) en lugar de SofaScore.

Uso:
    python manage.py load_worldcup_apifootball
    python manage.py load_worldcup_apifootball --only-teams
    python manage.py load_worldcup_apifootball --only-fixtures

Requiere:
    API_FOOTBALL_KEY=<tu_api_key> en el archivo .env
"""

import requests
import time
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime

from bets.models import ApiLiga, ApiEquipo, ApiPartido, ApiPais, Deporte, PartidoStatus


API_KEY = os.environ.get('API_FOOTBALL_KEY', '')
API_BASE = 'https://v3.football.api-sports.io'
HEADERS = {
    'x-apisports-key': API_KEY,
}

# FIFA World Cup en API-Football
WC_LEAGUE_ID = 1
WC_SEASON = 2026

# Mapeo de estados API-Football → PartidoStatus
STATUS_MAP = {
    'NS':   PartidoStatus.PROGRAMADO,
    'TBD':  PartidoStatus.PROGRAMADO,
    '1H':   PartidoStatus.EN_CURSO,
    'HT':   PartidoStatus.EN_CURSO,
    '2H':   PartidoStatus.EN_CURSO,
    'ET':   PartidoStatus.EN_CURSO,
    'BT':   PartidoStatus.EN_CURSO,
    'P':    PartidoStatus.EN_CURSO,
    'LIVE': PartidoStatus.EN_CURSO,
    'SUSP': PartidoStatus.SUSPENDIDO,
    'INT':  PartidoStatus.SUSPENDIDO,
    'FT':   PartidoStatus.FINALIZADO,
    'AET':  PartidoStatus.FINALIZADO,
    'PEN':  PartidoStatus.FINALIZADO,
    'AWD':  PartidoStatus.FINALIZADO,
    'WO':   PartidoStatus.FINALIZADO,
    'PST':  PartidoStatus.POSPUESTO,
    'CANC': PartidoStatus.CANCELADO,
    'ABD':  PartidoStatus.CANCELADO,
}


def api_get(endpoint, params=None):
    """Hace una request a API-Football y devuelve response[]."""
    url = f"{API_BASE}/{endpoint}"
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    errors = data.get('errors', {})
    if errors:
        raise Exception(f"API error: {errors}")
    return data.get('response', [])


class Command(BaseCommand):
    help = 'Carga equipos y partidos del Mundial 2026 desde API-Football'

    def add_arguments(self, parser):
        parser.add_argument('--only-teams', action='store_true', help='Solo cargar equipos')
        parser.add_argument('--only-fixtures', action='store_true', help='Solo cargar partidos')

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("🌍 CARGA MUNDIAL 2026 — API-FOOTBALL"))
        self.stdout.write("="*80 + "\n")

        if not API_KEY:
            self.stdout.write(self.style.ERROR(
                "❌ API_FOOTBALL_KEY no encontrada en el entorno.\n"
                "   Agrega API_FOOTBALL_KEY=<tu_key> al archivo .env y reinicia los contenedores."
            ))
            return

        self.stats = {'equipos_creados': 0, 'equipos_actualizados': 0,
                      'partidos_creados': 0, 'partidos_actualizados': 0, 'errores': 0}

        # Dependencias
        try:
            futbol = Deporte.objects.get(nombre='Fútbol')
        except Deporte.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "❌ Deporte 'Fútbol' no encontrado. Ejecuta primero:\n"
                "   python manage.py shell -c \"from bets.models import Deporte; Deporte.objects.get_or_create(nombre='Fútbol')\""
            ))
            return

        internacional, _ = ApiPais.objects.get_or_create(
            code='INT', defaults={'nombre': 'International'}
        )

        # Crear/obtener la liga del Mundial
        liga, created = ApiLiga.objects.update_or_create(
            api_id=WC_LEAGUE_ID,
            defaults={
                'nombre': 'FIFA World Cup 2026',
                'id_pais': internacional,
                'id_deporte': futbol,
                'temporada_actual': str(WC_SEASON),
                'tipo': 'Cup',
                'logo_url': 'https://media.api-sports.io/football/leagues/1.png',
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'✅ Liga creada' if created else '✅ Liga encontrada'}: FIFA World Cup 2026"
        ))

        if not options['only_fixtures']:
            self.stdout.write(self.style.WARNING("\n📋 Cargando equipos..."))
            self.load_teams(futbol)

        if not options['only_teams']:
            self.stdout.write(self.style.WARNING("\n📋 Cargando partidos..."))
            self.load_fixtures(liga)

        self.show_summary()

    def load_teams(self, futbol):
        """Carga las 48 selecciones del Mundial 2026."""
        try:
            response = api_get('teams', {'league': WC_LEAGUE_ID, 'season': WC_SEASON})
            self.stdout.write(f"   📊 Selecciones encontradas: {len(response)}")

            for item in response:
                team = item.get('team', {})
                team_id = team.get('id')
                team_name = team.get('name')

                if not team_id or not team_name:
                    continue

                # Buscar país por código o nombre
                country_name = team.get('country', team_name)
                pais, _ = ApiPais.objects.get_or_create(
                    nombre=country_name,
                    defaults={'code': team.get('code', 'INT')[:10]}
                )

                equipo, created = ApiEquipo.objects.update_or_create(
                    api_id=team_id,
                    defaults={
                        'nombre': team_name,
                        'nombre_corto': team.get('code') or team_name[:20],
                        'logo_url': team.get('logo', ''),
                        'id_pais': pais,
                        'id_deporte': futbol,
                        'tipo': 'National',
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"      ✅ {team_name}"))
                    self.stats['equipos_creados'] += 1
                else:
                    self.stats['equipos_actualizados'] += 1

                time.sleep(0.1)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error cargando equipos: {e}"))
            self.stats['errores'] += 1

    def load_fixtures(self, liga):
        """Carga todos los partidos del Mundial 2026."""
        try:
            response = api_get('fixtures', {'league': WC_LEAGUE_ID, 'season': WC_SEASON})
            self.stdout.write(f"   📊 Partidos encontrados: {len(response)}")

            for item in response:
                self.process_fixture(item, liga)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error cargando partidos: {e}"))
            self.stats['errores'] += 1

    def process_fixture(self, item, liga):
        """Procesa y guarda un partido en la BD."""
        try:
            fixture = item.get('fixture', {})
            teams = item.get('teams', {})
            goals = item.get('goals', {})

            fixture_id = fixture.get('id')
            home_data = teams.get('home', {})
            away_data = teams.get('away', {})

            if not fixture_id:
                return

            # Buscar equipos en BD
            home_team = ApiEquipo.objects.filter(api_id=home_data.get('id')).first()
            away_team = ApiEquipo.objects.filter(api_id=away_data.get('id')).first()

            if not home_team or not away_team:
                self.stdout.write(self.style.WARNING(
                    f"      ⚠️ Equipos no encontrados: "
                    f"{home_data.get('name')} vs {away_data.get('name')}"
                ))
                self.stats['errores'] += 1
                return

            # Fecha
            date_str = fixture.get('date')
            if date_str:
                fecha = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if timezone.is_naive(fecha):
                    fecha = timezone.make_aware(fecha)
            else:
                fecha = timezone.now()

            # Estado
            status_short = fixture.get('status', {}).get('short', 'NS')
            estado = STATUS_MAP.get(status_short, PartidoStatus.PROGRAMADO)

            # Ronda
            league_data = item.get('league', {})
            ronda = league_data.get('round', 'Group Stage')

            partido, created = ApiPartido.objects.update_or_create(
                api_fixture_id=fixture_id,
                defaults={
                    'id_liga': liga,
                    'equipo_local': home_team,
                    'equipo_visitante': away_team,
                    'fecha': fecha,
                    'temporada': str(WC_SEASON),
                    'ronda': ronda,
                    'estado': estado,
                    'goles_local': goals.get('home'),
                    'goles_visitante': goals.get('away'),
                }
            )

            if created:
                self.stdout.write(
                    f"      ✅ {home_team.nombre} vs {away_team.nombre} ({ronda})"
                )
                self.stats['partidos_creados'] += 1
            else:
                self.stats['partidos_actualizados'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error procesando partido: {e}"))
            self.stats['errores'] += 1

    def show_summary(self):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("="*80 + "\n")
        self.stdout.write(f"🌍 Selecciones creadas:      {self.stats['equipos_creados']}")
        self.stdout.write(f"🌍 Selecciones actualizadas: {self.stats['equipos_actualizados']}")
        self.stdout.write(f"⚽ Partidos creados:         {self.stats['partidos_creados']}")
        self.stdout.write(f"⚽ Partidos actualizados:    {self.stats['partidos_actualizados']}")
        if self.stats['errores']:
            self.stdout.write(self.style.ERROR(f"⚠️  Errores: {self.stats['errores']}"))
