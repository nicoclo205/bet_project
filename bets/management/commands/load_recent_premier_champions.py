"""
Comando Django para cargar partidos recientes de Premier League, La Liga y Champions League.

Este comando carga:
- Premier League: Partidos de la última semana
- La Liga: Partidos de la última semana
- Champions League: Partidos del último mes

Uso:
    python manage.py load_recent_premier_champions
    python manage.py load_recent_premier_champions --days-premier 7
    python manage.py load_recent_premier_champions --days-laliga 7
    python manage.py load_recent_premier_champions --days-champions 30
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from bets.utils.sofascore_api import get_football_matches_by_date
from bets.models import ApiLiga, ApiEquipo, ApiPartido, ApiPais, Deporte, PartidoStatus


class Command(BaseCommand):
    help = 'Carga partidos recientes de Premier League, La Liga y Champions League'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-premier',
            type=int,
            default=7,
            help='Días hacia atrás para Premier League (default: 7)',
        )
        parser.add_argument(
            '--days-laliga',
            type=int,
            default=7,
            help='Días hacia atrás para La Liga (default: 7)',
        )
        parser.add_argument(
            '--days-champions',
            type=int,
            default=30,
            help='Días hacia atrás para Champions League (default: 30)',
        )
        parser.add_argument(
            '--days-forward',
            type=int,
            default=7,
            help='Días hacia adelante para todas las ligas (default: 7)',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("⚽ CARGA DE PARTIDOS RECIENTES"))
        self.stdout.write("="*80 + "\n")

        days_premier = options['days_premier']
        days_laliga = options['days_laliga']
        days_champions = options['days_champions']
        days_forward = options['days_forward']

        # IDs de las ligas en SofaScore
        PREMIER_LEAGUE_ID = 17
        LA_LIGA_ID = 8
        CHAMPIONS_LEAGUE_ID = 7

        # Estadísticas
        self.stats = {
            'premier_creados': 0,
            'premier_actualizados': 0,
            'laliga_creados': 0,
            'laliga_actualizados': 0,
            'champions_creados': 0,
            'champions_actualizados': 0,
            'equipos_creados': 0,
            'errores': 0,
        }

        # Obtener o crear ligas
        self.stdout.write("📋 Configurando ligas...")
        premier_league = self.setup_league(PREMIER_LEAGUE_ID, "Premier League", "GB", "League", "2024-25")
        la_liga = self.setup_league(LA_LIGA_ID, "La Liga", "ES", "League", "2024-25")
        champions_league = self.setup_league(CHAMPIONS_LEAGUE_ID, "UEFA Champions League", "EUR", "Cup", "2024-25")

        # Cargar partidos de Premier League (última semana + próxima semana)
        self.stdout.write(f"\n📋 Cargando Premier League (últimos {days_premier} días + próximos {days_forward} días)...")
        self.load_matches_by_date_range(
            premier_league,
            days_premier,
            days_forward,
            PREMIER_LEAGUE_ID,
            'premier'
        )

        # Cargar partidos de La Liga (última semana + próxima semana)
        self.stdout.write(f"\n📋 Cargando La Liga (últimos {days_laliga} días + próximos {days_forward} días)...")
        self.load_matches_by_date_range(
            la_liga,
            days_laliga,
            days_forward,
            LA_LIGA_ID,
            'laliga'
        )

        # Cargar partidos de Champions League (último mes + próxima semana)
        self.stdout.write(f"\n📋 Cargando Champions League (últimos {days_champions} días + próximos {days_forward} días)...")
        self.load_matches_by_date_range(
            champions_league,
            days_champions,
            days_forward,
            CHAMPIONS_LEAGUE_ID,
            'champions'
        )

        # Resumen
        self.show_summary()

    def setup_league(self, api_id, name, country_code, tipo, season):
        """Crea o actualiza una liga en la BD"""
        try:
            # Obtener o crear país
            country_names = {
                'EUR': 'International',
                'GB': 'England',
                'ES': 'Spain'
            }
            pais, _ = ApiPais.objects.get_or_create(
                code=country_code,
                defaults={'nombre': country_names.get(country_code, 'Unknown')}
            )

            # Obtener deporte
            futbol = Deporte.objects.get(nombre='Fútbol')

            # Crear o actualizar liga
            liga, created = ApiLiga.objects.update_or_create(
                api_id=api_id,
                defaults={
                    'nombre': name,
                    'id_pais': pais,
                    'id_deporte': futbol,
                    'temporada_actual': season,
                    'tipo': tipo,
                    'logo_url': f'https://api.sofascore.com/api/v1/unique-tournament/{api_id}/image',
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"   ✅ Liga creada: {name}"))
            else:
                self.stdout.write(f"   ℹ️  Liga actualizada: {name}")

            return liga

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error configurando liga: {e}"))
            self.stats['errores'] += 1
            raise

    def load_matches_by_date_range(self, liga, days_back, days_forward, tournament_id, league_type):
        """Carga partidos en un rango de fechas"""
        today = datetime.now()
        start_date = today - timedelta(days=days_back)
        end_date = today + timedelta(days=days_forward)

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            self.stdout.write(f"   📅 Procesando {date_str}...")

            try:
                # Obtener partidos del día
                data = get_football_matches_by_date(date_str)
                events = data.get('events', [])

                # Filtrar solo partidos de esta liga
                league_events = [
                    e for e in events
                    if e.get('tournament', {}).get('uniqueTournament', {}).get('id') == tournament_id
                ]

                self.stdout.write(f"      📊 {len(league_events)} partidos encontrados")

                # Procesar cada partido
                for event in league_events:
                    self.process_match(event, liga, league_type)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"      ❌ Error procesando fecha {date_str}: {e}"))
                self.stats['errores'] += 1

            current_date += timedelta(days=1)

    def process_match(self, event, liga, league_type):
        """Procesa y guarda un partido"""
        try:
            event_id = event.get('id')
            home_team_data = event.get('homeTeam', {})
            away_team_data = event.get('awayTeam', {})

            if not event_id:
                return

            # Procesar equipos
            home_team = self.process_team(home_team_data)
            away_team = self.process_team(away_team_data)

            if not home_team or not away_team:
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

            # Extraer ronda
            round_info = event.get('roundInfo', {})
            ronda = round_info.get('round')
            round_name = round_info.get('name', '')

            # Para Champions, usar el nombre de la fase
            if league_type == 'champions' and round_name:
                ronda_str = round_name
            else:
                ronda_str = str(ronda) if ronda else None

            # Crear o actualizar partido
            partido, created = ApiPartido.objects.update_or_create(
                api_fixture_id=event_id,
                defaults={
                    'id_liga': liga,
                    'equipo_local': home_team,
                    'equipo_visitante': away_team,
                    'fecha': fecha,
                    'temporada': '2024-25',
                    'ronda': ronda_str,
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
                if league_type == 'premier':
                    self.stats['premier_creados'] += 1
                elif league_type == 'laliga':
                    self.stats['laliga_creados'] += 1
                else:
                    self.stats['champions_creados'] += 1
            else:
                if league_type == 'premier':
                    self.stats['premier_actualizados'] += 1
                elif league_type == 'laliga':
                    self.stats['laliga_actualizados'] += 1
                else:
                    self.stats['champions_actualizados'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error procesando partido: {e}"))
            self.stats['errores'] += 1

    def process_team(self, team_data):
        """Procesa y guarda un equipo"""
        try:
            team_id = team_data.get('id')
            team_name = team_data.get('name')

            if not team_id or not team_name:
                return None

            # Obtener país del equipo
            country_data = team_data.get('country', {})
            country_code = country_data.get('alpha2', 'INT')
            country_name = country_data.get('name', 'International')

            # Crear o obtener país
            pais, _ = ApiPais.objects.get_or_create(
                code=country_code,
                defaults={'nombre': country_name}
            )

            # Obtener deporte
            futbol = Deporte.objects.get(nombre='Fútbol')

            # Crear o actualizar equipo
            equipo, created = ApiEquipo.objects.update_or_create(
                api_id=team_id,
                defaults={
                    'nombre': team_name,
                    'nombre_corto': team_data.get('shortName', team_name[:3].upper()),
                    'id_pais': pais,
                    'id_deporte': futbol,
                    'tipo': 'Club',
                    'logo_url': f'https://api.sofascore.com/api/v1/team/{team_id}/image',
                }
            )

            if created:
                self.stats['equipos_creados'] += 1

            return equipo

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error procesando equipo: {e}"))
            self.stats['errores'] += 1
            return None

    def show_summary(self):
        """Muestra el resumen de la ejecución"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("="*80 + "\n")

        self.stdout.write(f"🏆 Equipos creados: {self.stats['equipos_creados']}")
        self.stdout.write(f"⚽ Premier League - Creados: {self.stats['premier_creados']}, Actualizados: {self.stats['premier_actualizados']}")
        self.stdout.write(f"⚽ La Liga - Creados: {self.stats['laliga_creados']}, Actualizados: {self.stats['laliga_actualizados']}")
        self.stdout.write(f"🏆 Champions League - Creados: {self.stats['champions_creados']}, Actualizados: {self.stats['champions_actualizados']}")

        if self.stats['errores'] > 0:
            self.stdout.write(self.style.ERROR(
                f"⚠️  Errores: {self.stats['errores']}"
            ))

        self.stdout.write("")
