"""
Comando Django para cargar partidos recientes de múltiples ligas desde SofaScore.

Carga partidos de los últimos 7 días y próximos 7 días para las ligas especificadas.

Uso:
    # Cargar partidos recientes de todas las ligas principales
    python manage.py load_recent_matches

    # Cargar solo de ligas específicas
    python manage.py load_recent_matches --leagues premier champions laliga
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from bets.utils.sofascore_api import get_football_matches_by_date
from bets.models import ApiLiga, ApiEquipo, ApiPartido, ApiPais, Deporte, PartidoStatus


# IDs de SofaScore
LEAGUES = {
    'premier': {
        'id': 17,
        'name': 'Premier League',
        'country_code': 'GB',
        'country_name': 'England',
    },
    'laliga': {
        'id': 8,
        'name': 'La Liga',
        'country_code': 'ES',
        'country_name': 'Spain',
    },
    'champions': {
        'id': 7,
        'name': 'UEFA Champions League',
        'country_code': 'EUR',
        'country_name': 'Europe',
    },
    'seriea': {
        'id': 23,
        'name': 'Serie A',
        'country_code': 'IT',
        'country_name': 'Italy',
    },
    'bundesliga': {
        'id': 35,
        'name': 'Bundesliga',
        'country_code': 'DE',
        'country_name': 'Germany',
    },
}


class Command(BaseCommand):
    help = 'Carga partidos recientes de las principales ligas desde SofaScore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--leagues',
            nargs='*',
            type=str,
            choices=list(LEAGUES.keys()),
            default=list(LEAGUES.keys()),
            help='Ligas a cargar (default: todas)',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=7,
            help='Días hacia atrás para cargar (default: 7)',
        )
        parser.add_argument(
            '--days-forward',
            type=int,
            default=7,
            help='Días hacia adelante para cargar (default: 7)',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("⚽ CARGA DE PARTIDOS RECIENTES"))
        self.stdout.write("="*80 + "\n")

        leagues_to_load = options['leagues']
        days_back = options['days_back']
        days_forward = options['days_forward']

        self.stdout.write(f"📅 Rango: {days_back} días atrás - {days_forward} días adelante")
        self.stdout.write(f"🏆 Ligas: {', '.join([LEAGUES[l]['name'] for l in leagues_to_load])}\n")

        # Estadísticas
        self.stats = {
            'ligas_creadas': 0,
            'equipos_creados': 0,
            'partidos_creados': 0,
            'partidos_actualizados': 0,
            'errores': 0,
        }

        # Obtener deporte
        try:
            futbol = Deporte.objects.get(nombre='Fútbol')
        except Deporte.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Deporte 'Fútbol' no encontrado en BD"))
            return

        # Crear/actualizar ligas
        for league_key in leagues_to_load:
            league_data = LEAGUES[league_key]
            self.setup_league(league_data, futbol)

        # Generar fechas a procesar
        today = datetime.now()
        dates_to_process = []
        for i in range(-days_back, days_forward + 1):
            date_obj = today + timedelta(days=i)
            dates_to_process.append(date_obj.strftime('%Y-%m-%d'))

        self.stdout.write(f"\n📅 Procesando {len(dates_to_process)} fechas...\n")

        # Procesar cada fecha
        for date_str in dates_to_process:
            self.process_date(date_str, leagues_to_load)

        # Resumen
        self.show_summary()

    def setup_league(self, league_data, futbol):
        """Crea o actualiza una liga"""
        try:
            # Obtener o crear país
            pais, _ = ApiPais.objects.get_or_create(
                code=league_data['country_code'],
                defaults={'nombre': league_data['country_name']}
            )

            # Crear o actualizar liga
            liga, created = ApiLiga.objects.update_or_create(
                api_id=league_data['id'],
                defaults={
                    'nombre': league_data['name'],
                    'id_pais': pais,
                    'id_deporte': futbol,
                    'tipo': 'Cup' if 'Champions' in league_data['name'] else 'League',
                    'logo_url': f'https://api.sofascore.com/api/v1/unique-tournament/{league_data["id"]}/image',
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"   ✅ Liga creada: {league_data['name']}"))
                self.stats['ligas_creadas'] += 1
            else:
                self.stdout.write(f"   ℹ️  Liga actualizada: {league_data['name']}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error configurando liga {league_data['name']}: {e}"))
            self.stats['errores'] += 1

    def process_date(self, date_str, leagues_filter):
        """Procesa todos los partidos de una fecha"""
        try:
            # Obtener partidos del día desde SofaScore
            matches_data = get_football_matches_by_date(date_str)
            events = matches_data.get('events', [])

            if not events:
                return

            # Filtrar solo partidos de las ligas que queremos
            league_ids = [LEAGUES[k]['id'] for k in leagues_filter]
            relevant_events = []

            for event in events:
                tournament = event.get('tournament', {}).get('uniqueTournament', {})
                tournament_id = tournament.get('id')
                if tournament_id in league_ids:
                    relevant_events.append(event)

            if not relevant_events:
                return

            self.stdout.write(self.style.WARNING(f"📅 {date_str}: {len(relevant_events)} partidos"))

            # Procesar cada partido
            for event in relevant_events:
                self.process_match(event)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error procesando fecha {date_str}: {e}"))
            self.stats['errores'] += 1

    def process_match(self, event):
        """Procesa y guarda un partido"""
        try:
            event_id = event.get('id')
            home_team_data = event.get('homeTeam', {})
            away_team_data = event.get('awayTeam', {})
            tournament = event.get('tournament', {}).get('uniqueTournament', {})

            if not event_id:
                return

            # Buscar liga
            liga = ApiLiga.objects.filter(api_id=tournament.get('id')).first()
            if not liga:
                return

            # Crear/obtener equipos
            home_team = self.get_or_create_team(home_team_data)
            away_team = self.get_or_create_team(away_team_data)

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
            ronda = round_info.get('name') or round_info.get('round')

            # Extraer temporada
            season = event.get('season', {}).get('name', '2024-25')

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
                    f"      ✅ {home_team.nombre} {score_str} {away_team.nombre} ({liga.nombre})"
                )
                self.stats['partidos_creados'] += 1
            else:
                self.stats['partidos_actualizados'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error procesando partido: {e}"))
            self.stats['errores'] += 1

    def get_or_create_team(self, team_data):
        """Obtiene o crea un equipo"""
        try:
            team_id = team_data.get('id')
            team_name = team_data.get('name')

            if not team_id or not team_name:
                return None

            # Buscar por api_id
            equipo = ApiEquipo.objects.filter(api_id=team_id).first()
            if equipo:
                return equipo

            # Si no existe, crearlo
            country_data = team_data.get('country', {})
            country_code = country_data.get('alpha2', 'INT')
            country_name = country_data.get('name', 'International')

            pais, _ = ApiPais.objects.get_or_create(
                code=country_code,
                defaults={'nombre': country_name}
            )

            futbol = Deporte.objects.get(nombre='Fútbol')

            equipo = ApiEquipo.objects.create(
                api_id=team_id,
                nombre=team_name,
                nombre_corto=team_data.get('shortName', team_name[:3].upper()),
                codigo=team_data.get('slug', team_name.lower().replace(' ', '-')),
                id_pais=pais,
                id_deporte=futbol,
                logo_url=f'https://api.sofascore.com/api/v1/team/{team_id}/image',
            )

            self.stdout.write(f"         🆕 Equipo creado: {team_name}")
            self.stats['equipos_creados'] += 1

            return equipo

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"         ❌ Error creando equipo: {e}"))
            self.stats['errores'] += 1
            return None

    def show_summary(self):
        """Muestra el resumen"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("="*80 + "\n")

        self.stdout.write(f"🏆 Ligas creadas: {self.stats['ligas_creadas']}")
        self.stdout.write(f"⚽ Equipos creados: {self.stats['equipos_creados']}")
        self.stdout.write(f"📅 Partidos creados: {self.stats['partidos_creados']}")
        self.stdout.write(f"📅 Partidos actualizados: {self.stats['partidos_actualizados']}")

        if self.stats['errores'] > 0:
            self.stdout.write(self.style.ERROR(f"⚠️  Errores: {self.stats['errores']}"))

        self.stdout.write("")
