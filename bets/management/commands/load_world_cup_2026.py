"""
Comando Django para cargar partidos de la Copa Mundial FIFA 2026 desde SofaScore.

Este comando:
1. Carga selecciones nacionales participantes
2. Carga partidos del Mundial 2026
3. Actualiza información de competición y selecciones

Uso:
    # Cargar selecciones y partidos
    python manage.py load_world_cup_2026

    # Cargar solo selecciones
    python manage.py load_world_cup_2026 --only-teams

    # Cargar solo partidos
    python manage.py load_world_cup_2026 --only-fixtures

Notas:
    - Copa Mundial 2026 se celebrará en Canadá, México y USA
    - Primer Mundial con 48 selecciones
    - El ID y temporada se actualizarán cuando SofaScore lo habilite
    - Por ahora carga datos de preparación/clasificatorias
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import requests
import urllib3
urllib3.disable_warnings()

from bets.utils.sofascore_api import BASE_URL, HEADERS
from bets.models import ApiLiga, ApiEquipo, ApiPartido, ApiPais, Deporte, PartidoStatus


class Command(BaseCommand):
    help = 'Carga selecciones y partidos de la Copa Mundial FIFA 2026 desde SofaScore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--only-teams',
            action='store_true',
            help='Solo cargar selecciones',
        )
        parser.add_argument(
            '--only-fixtures',
            action='store_true',
            help='Solo cargar partidos',
        )
        parser.add_argument(
            '--load-qualifiers',
            action='store_true',
            help='Cargar partidos de clasificatorias en vez del mundial',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("🌍 CARGA DE COPA MUNDIAL FIFA 2026"))
        self.stdout.write("="*80 + "\n")

        only_teams = options['only_teams']
        only_fixtures = options['only_fixtures']
        load_qualifiers = options['load_qualifiers']

        # NOTA: Estos IDs se deben actualizar cuando SofaScore habilite el Mundial 2026
        # Por ahora usamos IDs estimados basados en patrones anteriores
        if load_qualifiers:
            # Clasificatorias CONMEBOL (ejemplo)
            TOURNAMENT_ID = 116  # CONMEBOL World Cup Qualifiers
            SEASON_ID = 62000  # Actualizar con ID real
            TOURNAMENT_NAME = "World Cup 2026 Qualifiers - CONMEBOL"
            season = "2024-26"
        else:
            # Mundial 2026
            TOURNAMENT_ID = 16
            SEASON_ID = 58210  # Confirmado en SofaScore
            TOURNAMENT_NAME = "FIFA World Cup 2026"
            season = "2026"

        self.stdout.write(f"📅 Competición: {TOURNAMENT_NAME}")
        self.stdout.write(f"🔢 Tournament ID: {TOURNAMENT_ID}, Season ID: {SEASON_ID}")

        # Estadísticas
        self.stats = {
            'equipos_creados': 0,
            'equipos_actualizados': 0,
            'partidos_creados': 0,
            'partidos_actualizados': 0,
            'errores': 0,
        }

        # Paso 1: Crear/obtener competición
        if not only_fixtures:
            self.stdout.write(self.style.WARNING("📋 Paso 1: Configurando competición..."))
            liga = self.setup_tournament(TOURNAMENT_ID, TOURNAMENT_NAME, season)
        else:
            try:
                liga = ApiLiga.objects.get(api_id=TOURNAMENT_ID)
            except ApiLiga.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    "❌ Competición no encontrada. Ejecuta sin --only-fixtures primero."
                ))
                return

        # Paso 2: Cargar selecciones
        if not only_fixtures:
            self.stdout.write(self.style.WARNING("\n📋 Paso 2: Cargando selecciones..."))
            try:
                self.load_teams(TOURNAMENT_ID, SEASON_ID, liga)
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"   ❌ Error: {e}\n"
                    f"   Esto es esperado si SofaScore aún no ha habilitado el Mundial 2026"
                ))
                self.stats['errores'] += 1

        # Paso 3: Cargar partidos
        if not only_teams:
            self.stdout.write(self.style.WARNING("\n📋 Paso 3: Cargando partidos..."))
            try:
                self.load_fixtures(TOURNAMENT_ID, SEASON_ID, liga, season)
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"   ❌ Error: {e}\n"
                    f"   Esto es esperado si SofaScore aún no ha habilitado el Mundial 2026"
                ))
                self.stats['errores'] += 1

        # Resumen
        self.show_summary()

    def setup_tournament(self, tournament_id, tournament_name, season):
        """Crea o actualiza la competición en la BD"""
        try:
            # Obtener o crear país (Internacional)
            internacional, _ = ApiPais.objects.get_or_create(
                code='INT',
                defaults={'nombre': 'International'}
            )

            # Obtener deporte
            futbol = Deporte.objects.get(nombre='Fútbol')

            # Crear o actualizar liga
            liga, created = ApiLiga.objects.update_or_create(
                api_id=tournament_id,
                defaults={
                    'nombre': tournament_name,
                    'id_pais': internacional,
                    'id_deporte': futbol,
                    'temporada_actual': season,
                    'tipo': 'Cup',  # Mundial es torneo de copa
                    'logo_url': f'https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/image',
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"   ✅ Competición creada: {tournament_name}"))
            else:
                self.stdout.write(f"   ℹ️  Competición actualizada: {tournament_name}")

            return liga

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error configurando competición: {e}"))
            self.stats['errores'] += 1
            raise

    def fetch_all_events(self, tournament_id, season_id):
        """Obtiene todos los eventos paginando next y last."""
        all_events = []
        seen_ids = set()

        for direction in ('next', 'last'):
            page = 0
            while True:
                url = f"{BASE_URL}/unique-tournament/{tournament_id}/season/{season_id}/events/{direction}/{page}"
                try:
                    r = requests.get(url, headers=HEADERS, verify=False, timeout=15)
                    if r.status_code == 404:
                        break
                    r.raise_for_status()
                    data = r.json()
                    events = data.get('events', [])
                    if not events:
                        break
                    new = [e for e in events if e.get('id') not in seen_ids]
                    if not new:
                        break
                    for e in new:
                        seen_ids.add(e['id'])
                    all_events.extend(new)
                    import time
                    time.sleep(2)
                    page += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"      ⚠️ {direction}/{page}: {e}"))
                    break

        return all_events

    def load_teams(self, tournament_id, season_id, liga):
        """Carga las selecciones del Mundial 2026"""
        try:
            events = self.fetch_all_events(tournament_id, season_id)

            teams_dict = {}
            for event in events:
                for key in ('homeTeam', 'awayTeam'):
                    team = event.get(key)
                    if team and team['id'] not in teams_dict:
                        teams_dict[team['id']] = team

            teams = list(teams_dict.values())
            self.stdout.write(f"   📊 Selecciones encontradas: {len(teams)}")

            for team_data in teams:
                self.process_team(team_data)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error cargando selecciones: {e}"))
            raise

    def process_team(self, team_data):
        """Procesa y guarda una selección en la BD"""
        try:
            team_id = team_data.get('id')
            team_name = team_data.get('name')

            if not team_id or not team_name:
                return

            # Obtener país de la selección
            country_data = team_data.get('country', {})
            country_code = country_data.get('alpha2', 'INT')
            country_name = country_data.get('name', team_name)

            # Crear o obtener país
            pais, _ = ApiPais.objects.get_or_create(
                code=country_code,
                defaults={'nombre': country_name}
            )

            futbol = Deporte.objects.filter(nombre='Fútbol').first()

            equipo, created = ApiEquipo.objects.update_or_create(
                api_id=team_id,
                defaults={
                    'nombre': team_name,
                    'nombre_corto': team_data.get('shortName', country_code),
                    'id_pais': pais,
                    'logo_url': f'https://api.sofascore.app/api/v1/team/{team_id}/image',
                    'tipo': 'National',
                    'id_deporte': futbol,
                }
            )

            if created:
                self.stdout.write(f"      ✅ Selección creada: {team_name}")
                self.stats['equipos_creados'] += 1
            else:
                self.stats['equipos_actualizados'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error procesando selección: {e}"))
            self.stats['errores'] += 1

    def load_fixtures(self, tournament_id, season_id, liga, season):
        """Carga los partidos del Mundial 2026"""
        try:
            events = self.fetch_all_events(tournament_id, season_id)
            self.stdout.write(f"   📊 Partidos encontrados: {len(events)}")

            for event in events:
                self.process_fixture(event, liga, season)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error cargando partidos: {e}"))
            raise

    def process_fixture(self, event, liga, season):
        """Procesa y guarda un partido en la BD"""
        try:
            event_id = event.get('id')
            home_team_data = event.get('homeTeam', {})
            away_team_data = event.get('awayTeam', {})

            if not event_id:
                return

            # Buscar selecciones en BD
            try:
                home_team = ApiEquipo.objects.get(api_id=home_team_data.get('id'))
                away_team = ApiEquipo.objects.get(api_id=away_team_data.get('id'))
            except ApiEquipo.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"      ⚠️ Selecciones no encontradas: {home_team_data.get('name')} vs {away_team_data.get('name')}"
                ))
                return

            # Mapear estado
            status_data = event.get('status', {})
            status_type = status_data.get('type', 'notstarted')
            status_mapping = {
                'notstarted': PartidoStatus.PROGRAMADO,
                'inprogress': PartidoStatus.EN_CURSO,
                'finished': PartidoStatus.FINALIZADO,
                'canceled': PartidoStatus.CANCELADO,
                'postponed': PartidoStatus.POSPUESTO,
                'interrupted': PartidoStatus.SUSPENDIDO,
                'abandoned': PartidoStatus.SUSPENDIDO,
            }
            estado = status_mapping.get(status_type, PartidoStatus.PROGRAMADO)

            # Extraer marcadores
            home_score = event.get('homeScore', {})
            away_score = event.get('awayScore', {})
            goles_local = home_score.get('current')
            goles_visitante = away_score.get('current')

            # Extraer fecha
            timestamp = event.get('startTimestamp')
            if timestamp:
                fecha = timezone.make_aware(datetime.fromtimestamp(timestamp))
            else:
                fecha = timezone.now()

            round_info = event.get('roundInfo', {})
            ronda = round_info.get('name', 'Group Stage')

            partido, created = ApiPartido.objects.update_or_create(
                api_fixture_id=event_id,
                defaults={
                    'id_liga': liga,
                    'equipo_local': home_team,
                    'equipo_visitante': away_team,
                    'fecha': fecha,
                    'temporada': season,
                    'ronda': ronda,
                    'estado': estado,
                    'goles_local': goles_local,
                    'goles_visitante': goles_visitante,
                }
            )

            if created:
                score_str = f"{goles_local or '-'} - {goles_visitante or '-'}"
                self.stdout.write(
                    f"      ✅ {home_team.nombre} {score_str} {away_team.nombre} ({ronda})"
                )
                self.stats['partidos_creados'] += 1
            else:
                self.stats['partidos_actualizados'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error procesando partido: {e}"))
            self.stats['errores'] += 1

    def show_summary(self):
        """Muestra el resumen de la ejecución"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("="*80 + "\n")

        self.stdout.write(f"🌍 Selecciones creadas: {self.stats['equipos_creados']}")
        self.stdout.write(f"🌍 Selecciones actualizadas: {self.stats['equipos_actualizados']}")
        self.stdout.write(f"⚽ Partidos creados: {self.stats['partidos_creados']}")
        self.stdout.write(f"⚽ Partidos actualizados: {self.stats['partidos_actualizados']}")

        if self.stats['errores'] > 0:
            self.stdout.write(self.style.ERROR(
                f"⚠️  Errores: {self.stats['errores']}"
            ))

