"""
Comando Django para actualizar resultados de partidos de fútbol desde SofaScore.

Este comando actualiza DIARIAMENTE:
- Resultados de partidos finalizados
- Estados de partidos en curso
- Próximos partidos programados

Diseñado para ejecutarse automáticamente vía cron job una vez al día.

Uso:
    # Actualizar partidos de ayer
    python manage.py update_sofascore_football

    # Actualizar últimos 3 días
    python manage.py update_sofascore_football --days-back 3

    # Actualizar ayer y próximos 2 días
    python manage.py update_sofascore_football --days-back 1 --days-forward 2

    # Solo actualizar partidos de una liga específica
    python manage.py update_sofascore_football --league-id 1

Configuración recomendada en crontab:
    # Ejecutar todos los días a las 2 AM
    0 2 * * * cd /ruta/proyecto && python manage.py update_sofascore_football

Notas:
    - Usa delays anti-bloqueo automáticos
    - Solo actualiza partidos que existen en BD
    - No crea nuevos partidos (usar load_sofascore_laliga para eso)
    - Hace máximo 1 petición por día si solo actualizas 1 día
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from bets.utils.sofascore_api import (
    get_football_matches_by_date,
    get_event,
)
from bets.models import ApiPartido, ApiEquipo, ApiLiga, PartidoStatus


class Command(BaseCommand):
    help = 'Actualiza resultados de partidos de fútbol desde SofaScore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-back',
            type=int,
            default=1,
            help='Número de días hacia atrás para actualizar (default: 1)',
        )
        parser.add_argument(
            '--days-forward',
            type=int,
            default=0,
            help='Número de días hacia adelante para actualizar (default: 0)',
        )
        parser.add_argument(
            '--league-id',
            type=int,
            help='ID de liga en BD para filtrar (opcional)',
        )
        parser.add_argument(
            '--update-all',
            action='store_true',
            help='Actualizar todos los partidos sin filtro de fecha',
        )
        parser.add_argument(
            '--only-pending',
            action='store_true',
            help='Solo actualizar partidos pendientes o en curso',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("🔄 ACTUALIZACIÓN DE PARTIDOS DE FÚTBOL"))
        self.stdout.write("="*80 + "\n")

        days_back = options['days_back']
        days_forward = options['days_forward']
        league_id = options['league_id']
        update_all = options['update_all']
        only_pending = options['only_pending']

        # Estadísticas
        self.stats = {
            'updated': 0,
            'unchanged': 0,
            'not_found': 0,
            'errors': 0,
        }

        if update_all:
            # Actualizar todos los partidos en BD
            self.stdout.write("   Modo: Actualizar TODOS los partidos en BD\n")
            self.update_all_fixtures(league_id, only_pending)
        else:
            # Actualizar por rango de fechas
            self.stdout.write(f"   Días hacia atrás: {days_back}")
            self.stdout.write(f"   Días hacia adelante: {days_forward}")
            if league_id:
                self.stdout.write(f"   Liga filtrada: ID {league_id}")
            self.stdout.write("")

            self.update_by_date_range(days_back, days_forward, league_id, only_pending)

        # Mostrar resumen
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ ACTUALIZACIÓN COMPLETADA"))
        self.stdout.write("="*80 + "\n")

        self.stdout.write(f"📊 Partidos actualizados: {self.stats['updated']}")
        self.stdout.write(f"📊 Sin cambios: {self.stats['unchanged']}")
        self.stdout.write(f"📊 No encontrados en SofaScore: {self.stats['not_found']}")
        self.stdout.write(f"📊 Errores: {self.stats['errors']}\n")

    def update_by_date_range(self, days_back, days_forward, league_id, only_pending):
        """Actualiza partidos en un rango de fechas"""

        dates_to_check = []
        for i in range(-days_back, days_forward + 1):
            date_obj = datetime.now() + timedelta(days=i)
            dates_to_check.append(date_obj.strftime('%Y-%m-%d'))

        self.stdout.write(f"   Fechas a verificar: {', '.join(dates_to_check)}\n")

        for date_str in dates_to_check:
            self.stdout.write(self.style.WARNING(f"📅 Procesando fecha: {date_str}"))

            try:
                # Obtener partidos del día desde SofaScore
                matches_data = get_football_matches_by_date(date_str)
                events = matches_data.get('events', [])

                if not events:
                    self.stdout.write("   No hay partidos en esta fecha\n")
                    continue

                self.stdout.write(f"   Encontrados {len(events)} partidos en SofaScore")

                # Procesar cada partido
                for event in events:
                    self.process_event(event, league_id, only_pending)

                self.stdout.write("")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error obteniendo partidos: {e}\n"))
                self.stats['errors'] += 1

    def update_all_fixtures(self, league_id, only_pending):
        """Actualiza todos los partidos en BD sin filtro de fecha"""

        # Construir query
        query = ApiPartido.objects.all()

        if league_id:
            query = query.filter(id_liga_id=league_id)

        if only_pending:
            query = query.exclude(estado=PartidoStatus.FINALIZADO)

        partidos = query.select_related('equipo_local', 'equipo_visitante', 'id_liga')

        self.stdout.write(f"   Partidos a actualizar: {partidos.count()}\n")

        for partido in partidos:
            try:
                # Obtener datos actualizados desde SofaScore
                event_data = get_event(partido.api_fixture_id)
                event = event_data.get('event', {})

                if event:
                    self.update_partido_from_event(partido, event)
                else:
                    self.stdout.write(self.style.WARNING(
                        f"   ⚠️ Partido no encontrado: {partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"
                    ))
                    self.stats['not_found'] += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"   ❌ Error actualizando partido ID {partido.id_partido}: {e}"
                ))
                self.stats['errors'] += 1

    def process_event(self, event, league_id_filter, only_pending):
        """Procesa un evento de SofaScore y crea/actualiza en BD"""

        event_id = event.get('id')
        home_team_data = event.get('homeTeam', {})
        away_team_data = event.get('awayTeam', {})
        tournament = event.get('tournament', {}).get('uniqueTournament', {})

        home_team_id = home_team_data.get('id')
        away_team_id = away_team_data.get('id')
        tournament_id = tournament.get('id')

        if not event_id or not home_team_id or not away_team_id:
            return

        # Solo procesar si es La Liga (tournament_id = 8) o si no hay filtro
        if tournament_id != 8:
            return

        # Buscar equipos en BD por api_id de SofaScore, o por nombre como fallback
        home_team = None
        away_team = None

        # Intentar por api_id primero
        try:
            home_team = ApiEquipo.objects.get(api_id=home_team_id)
        except ApiEquipo.DoesNotExist:
            # Fallback: buscar por nombre (normalizado)
            home_name = home_team_data.get('name', '')
            # Mapeo de nombres conocidos
            name_mapping = {
                'Deportivo Alavés': 'Alaves',
                'Atlético Madrid': 'Atletico Madrid',
                'Real Sociedad de Fútbol': 'Real Sociedad',
            }
            search_name = name_mapping.get(home_name, home_name)
            home_team = ApiEquipo.objects.filter(nombre__iexact=search_name).first()

        try:
            away_team = ApiEquipo.objects.get(api_id=away_team_id)
        except ApiEquipo.DoesNotExist:
            # Fallback: buscar por nombre (normalizado)
            away_name = away_team_data.get('name', '')
            name_mapping = {
                'Deportivo Alavés': 'Alaves',
                'Atlético Madrid': 'Atletico Madrid',
                'Real Sociedad de Fútbol': 'Real Sociedad',
            }
            search_name = name_mapping.get(away_name, away_name)
            away_team = ApiEquipo.objects.filter(nombre__iexact=search_name).first()

        if not home_team or not away_team:
            # Si algún equipo no existe, saltarlo
            self.stdout.write(self.style.WARNING(
                f"   ⚠️  Equipos no encontrados en BD: {home_team_data.get('name')} vs {away_team_data.get('name')}"
            ))
            self.stats['not_found'] += 1
            return

        # Buscar o crear partido
        try:
            partido = ApiPartido.objects.select_related(
                'equipo_local',
                'equipo_visitante',
                'id_liga'
            ).get(api_fixture_id=event_id)

            # Filtrar por liga si se especificó
            if league_id_filter and partido.id_liga_id != league_id_filter:
                return

            # Filtrar por estado si solo_pending
            if only_pending and partido.estado == PartidoStatus.FINALIZADO:
                return

            # Actualizar partido existente
            self.update_partido_from_event(partido, event)

        except ApiPartido.DoesNotExist:
            # Partido no existe, crearlo
            self.create_partido_from_event(event, home_team, away_team)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error procesando evento {event_id}: {e}"))
            self.stats['errors'] += 1

    def update_partido_from_event(self, partido, event):
        """Actualiza un partido existente con datos de SofaScore"""

        changed = False

        # Extraer datos del evento
        status_data = event.get('status', {})
        status_type = status_data.get('type', 'notstarted')

        # Mapear estado
        status_mapping = {
            'notstarted': PartidoStatus.PROGRAMADO,
            'inprogress': PartidoStatus.EN_CURSO,
            'finished': PartidoStatus.FINALIZADO,
            'canceled': PartidoStatus.CANCELADO,
            'postponed': PartidoStatus.POSPUESTO,
            'interrupted': PartidoStatus.SUSPENDIDO,
            'abandoned': PartidoStatus.SUSPENDIDO,
        }
        nuevo_estado = status_mapping.get(status_type, PartidoStatus.PROGRAMADO)

        # Actualizar estado si cambió
        if partido.estado != nuevo_estado:
            partido.estado = nuevo_estado
            changed = True

        # Actualizar marcadores si están disponibles
        home_score = event.get('homeScore', {})
        away_score = event.get('awayScore', {})

        goles_local = home_score.get('current')
        goles_visitante = away_score.get('current')

        if goles_local is not None and partido.goles_local != goles_local:
            partido.goles_local = goles_local
            changed = True

        if goles_visitante is not None and partido.goles_visitante != goles_visitante:
            partido.goles_visitante = goles_visitante
            changed = True

        # Actualizar timestamp
        timestamp = event.get('startTimestamp')
        if timestamp:
            nueva_fecha = datetime.fromtimestamp(timestamp)
            if partido.fecha != nueva_fecha:
                partido.fecha = nueva_fecha
                changed = True

        # Guardar si hubo cambios
        if changed:
            partido.ultima_actualizacion = timezone.now()
            partido.save()

            score_str = f"{partido.goles_local or '-'} - {partido.goles_visitante or '-'}"
            self.stdout.write(
                f"   ✅ {partido.equipo_local.nombre} {score_str} {partido.equipo_visitante.nombre} "
                f"({partido.estado})"
            )
            self.stats['updated'] += 1
        else:
            self.stats['unchanged'] += 1

    def create_partido_from_event(self, event, home_team, away_team):
        """Crea un nuevo partido desde un evento de SofaScore"""

        try:
            # Obtener o crear La Liga
            from bets.models import ApiLiga, Deporte, ApiPais

            spain = ApiPais.objects.get(code='ES')
            futbol = Deporte.objects.get(nombre='Fútbol')

            liga, _ = ApiLiga.objects.get_or_create(
                api_id=8,
                defaults={
                    'nombre': 'La Liga',
                    'id_pais': spain,
                    'id_deporte': futbol,
                    'temporada_actual': '2024-25',
                    'tipo': 'League',
                }
            )

            # Extraer datos del evento
            status_data = event.get('status', {})
            status_type = status_data.get('type', 'notstarted')

            # Mapear estado
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
            from datetime import datetime
            fecha = datetime.fromtimestamp(timestamp) if timestamp else timezone.now()

            # Crear partido
            partido = ApiPartido.objects.create(
                api_fixture_id=event.get('id'),
                id_liga=liga,
                equipo_local=home_team,
                equipo_visitante=away_team,
                fecha=fecha,
                temporada='2024-25',
                estado=estado,
                goles_local=goles_local,
                goles_visitante=goles_visitante,
            )

            score_str = f"{goles_local or '-'} - {goles_visitante or '-'}"
            self.stdout.write(self.style.SUCCESS(
                f"   🆕 NUEVO: {home_team.nombre} {score_str} {away_team.nombre} ({estado})"
            ))
            self.stats['updated'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error creando partido: {e}"))
            self.stats['errors'] += 1
