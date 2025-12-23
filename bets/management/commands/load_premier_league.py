"""
Comando Django para cargar partidos de la Premier League desde SofaScore.

Este comando:
1. Carga equipos de la Premier League en la BD
2. Carga partidos de la temporada actual
3. Actualiza información de liga y equipos

Uso:
    # Cargar equipos y partidos de la temporada actual
    python manage.py load_premier_league

    # Cargar solo equipos
    python manage.py load_premier_league --only-teams

    # Cargar solo partidos
    python manage.py load_premier_league --only-fixtures

    # Especificar temporada
    python manage.py load_premier_league --season 2024-25

Notas:
    - Premier League ID en SofaScore: 17
    - Temporada 2024/25 ID: 61627
    - País: Inglaterra (GB)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from bets.utils.sofascore_api import (
    get_football_tournament_season,
    get_football_tournament_events,
    get_football_team,
)
from bets.models import ApiLiga, ApiEquipo, ApiPartido, ApiPais, Deporte, PartidoStatus


class Command(BaseCommand):
    help = 'Carga equipos y partidos de la Premier League desde SofaScore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=str,
            default='2024-25',
            help='Temporada a cargar (default: 2024-25)',
        )
        parser.add_argument(
            '--only-teams',
            action='store_true',
            help='Solo cargar equipos',
        )
        parser.add_argument(
            '--only-fixtures',
            action='store_true',
            help='Solo cargar partidos',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("⚽ CARGA DE PREMIER LEAGUE"))
        self.stdout.write("="*80 + "\n")

        season = options['season']
        only_teams = options['only_teams']
        only_fixtures = options['only_fixtures']

        # Mapeo de temporadas a IDs de SofaScore
        season_ids = {
            '2024-25': 61627,
            '2025-26': 77560,  # Actualizar cuando esté disponible
        }

        season_id = season_ids.get(season)
        if not season_id:
            self.stdout.write(self.style.ERROR(
                f"❌ Temporada '{season}' no encontrada. Disponibles: {list(season_ids.keys())}"
            ))
            return

        self.stdout.write(f"📅 Temporada: {season} (ID: {season_id})\n")

        # Constantes
        PREMIER_LEAGUE_ID = 17
        TOURNAMENT_NAME = "Premier League"

        # Estadísticas
        self.stats = {
            'equipos_creados': 0,
            'equipos_actualizados': 0,
            'partidos_creados': 0,
            'partidos_actualizados': 0,
            'errores': 0,
        }

        # Paso 1: Crear/obtener liga
        if not only_fixtures:
            self.stdout.write(self.style.WARNING("📋 Paso 1: Configurando liga..."))
            liga = self.setup_league(PREMIER_LEAGUE_ID, TOURNAMENT_NAME, season)
        else:
            try:
                liga = ApiLiga.objects.get(api_id=PREMIER_LEAGUE_ID)
            except ApiLiga.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    "❌ Liga no encontrada. Ejecuta sin --only-fixtures primero."
                ))
                return

        # Paso 2: Cargar equipos
        if not only_fixtures:
            self.stdout.write(self.style.WARNING("\n📋 Paso 2: Cargando equipos..."))
            self.load_teams(PREMIER_LEAGUE_ID, season_id, liga)

        # Paso 3: Cargar partidos
        if not only_teams:
            self.stdout.write(self.style.WARNING("\n📋 Paso 3: Cargando partidos..."))
            self.load_fixtures(PREMIER_LEAGUE_ID, season_id, liga, season)

        # Resumen
        self.show_summary()

    def setup_league(self, tournament_id, tournament_name, season):
        """Crea o actualiza la liga en la BD"""
        try:
            # Obtener o crear país (Inglaterra)
            inglaterra, _ = ApiPais.objects.get_or_create(
                code='GB',
                defaults={'nombre': 'England'}
            )

            # Obtener deporte
            futbol = Deporte.objects.get(nombre='Fútbol')

            # Crear o actualizar liga
            liga, created = ApiLiga.objects.update_or_create(
                api_id=tournament_id,
                defaults={
                    'nombre': tournament_name,
                    'id_pais': inglaterra,
                    'id_deporte': futbol,
                    'temporada_actual': season,
                    'tipo': 'League',
                    'logo_url': f'https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/image',
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"   ✅ Liga creada: {tournament_name}"))
            else:
                self.stdout.write(f"   ℹ️  Liga actualizada: {tournament_name}")

            return liga

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error configurando liga: {e}"))
            self.stats['errores'] += 1
            raise

    def load_teams(self, tournament_id, season_id, liga):
        """Carga los equipos de la Premier League"""
        try:
            # Obtener datos de la temporada
            season_data = get_football_tournament_season(tournament_id, season_id)

            # Los equipos pueden estar en diferentes lugares según la estructura
            teams = []

            # Intentar obtener equipos del campo standings
            standings_data = season_data.get('standings', [])
            if standings_data:
                for standing in standings_data:
                    rows = standing.get('rows', [])
                    for row in rows:
                        team = row.get('team')
                        if team:
                            teams.append(team)

            if not teams:
                self.stdout.write(self.style.WARNING(
                    "   ⚠️ No se encontraron equipos en standings. Cargando desde partidos..."
                ))
                # Fallback: obtener equipos desde los partidos
                events_data = get_football_tournament_events(tournament_id, season_id)
                events = events_data.get('events', [])
                teams_dict = {}
                for event in events[:50]:  # Solo primeros 50 eventos
                    home_team = event.get('homeTeam')
                    away_team = event.get('awayTeam')
                    if home_team and home_team['id'] not in teams_dict:
                        teams_dict[home_team['id']] = home_team
                    if away_team and away_team['id'] not in teams_dict:
                        teams_dict[away_team['id']] = away_team
                teams = list(teams_dict.values())

            self.stdout.write(f"   📊 Equipos encontrados: {len(teams)}")

            # Procesar cada equipo
            for team_data in teams:
                self.process_team(team_data, liga)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error cargando equipos: {e}"))
            self.stats['errores'] += 1

    def process_team(self, team_data, liga):
        """Procesa y guarda un equipo en la BD"""
        try:
            team_id = team_data.get('id')
            team_name = team_data.get('name')

            if not team_id or not team_name:
                return

            # Crear o actualizar equipo
            equipo, created = ApiEquipo.objects.update_or_create(
                api_id=team_id,
                defaults={
                    'nombre': team_name,
                    'nombre_corto': team_data.get('shortName', team_name[:3].upper()),
                    'id_pais': liga.id_pais,
                    'id_deporte': liga.id_deporte,
                    'tipo': 'Club',
                    'logo_url': f'https://api.sofascore.com/api/v1/team/{team_id}/image',
                }
            )

            if created:
                self.stdout.write(f"      ✅ Equipo creado: {team_name}")
                self.stats['equipos_creados'] += 1
            else:
                self.stats['equipos_actualizados'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error procesando equipo: {e}"))
            self.stats['errores'] += 1

    def load_fixtures(self, tournament_id, season_id, liga, season):
        """Carga los partidos de la Premier League"""
        try:
            # Obtener todos los eventos de la temporada
            events_data = get_football_tournament_events(tournament_id, season_id)
            events = events_data.get('events', [])

            self.stdout.write(f"   📊 Partidos encontrados: {len(events)}")

            # Procesar cada partido
            for event in events:
                self.process_fixture(event, liga, season)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error cargando partidos: {e}"))
            self.stats['errores'] += 1

    def process_fixture(self, event, liga, season):
        """Procesa y guarda un partido en la BD"""
        try:
            event_id = event.get('id')
            home_team_data = event.get('homeTeam', {})
            away_team_data = event.get('awayTeam', {})

            if not event_id:
                return

            # Buscar equipos en BD
            try:
                home_team = ApiEquipo.objects.get(api_id=home_team_data.get('id'))
                away_team = ApiEquipo.objects.get(api_id=away_team_data.get('id'))
            except ApiEquipo.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"      ⚠️ Equipos no encontrados: {home_team_data.get('name')} vs {away_team_data.get('name')}"
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

            # Extraer jornada
            round_info = event.get('roundInfo', {})
            ronda = round_info.get('round')

            # Crear o actualizar partido
            partido, created = ApiPartido.objects.update_or_create(
                api_fixture_id=event_id,
                defaults={
                    'id_liga': liga,
                    'equipo_local': home_team,
                    'equipo_visitante': away_team,
                    'fecha': fecha,
                    'temporada': season,
                    'ronda': str(ronda) if ronda else None,
                    'estado': estado,
                    'goles_local': goles_local,
                    'goles_visitante': goles_visitante,
                }
            )

            if created:
                score_str = f"{goles_local or '-'} - {goles_visitante or '-'}"
                self.stdout.write(
                    f"      ✅ {home_team.nombre} {score_str} {away_team.nombre}"
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

        self.stdout.write(f"🏆 Equipos creados: {self.stats['equipos_creados']}")
        self.stdout.write(f"🏆 Equipos actualizados: {self.stats['equipos_actualizados']}")
        self.stdout.write(f"⚽ Partidos creados: {self.stats['partidos_creados']}")
        self.stdout.write(f"⚽ Partidos actualizados: {self.stats['partidos_actualizados']}")

        if self.stats['errores'] > 0:
            self.stdout.write(self.style.ERROR(
                f"⚠️  Errores: {self.stats['errores']}"
            ))

        self.stdout.write("")
