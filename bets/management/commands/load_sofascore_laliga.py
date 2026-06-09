"""
Comando Django para cargar equipos y fixtures de La Liga desde SofaScore.

Este comando realiza la carga INICIAL de:
- Los 20 equipos de La Liga temporada 2024/25
- Todos los fixtures/partidos de la temporada
- Información de estadios (venues)

Uso:
    python manage.py load_sofascore_laliga

    # Con opciones:
    python manage.py load_sofascore_laliga --skip-teams     # Solo cargar fixtures
    python manage.py load_sofascore_laliga --skip-fixtures  # Solo cargar equipos
    python manage.py load_sofascore_laliga --round 15       # Solo cargar jornada 15

Notas:
    - Este comando debe ejecutarse UNA SOLA VEZ al inicio
    - Para actualizaciones diarias usar: update_sofascore_football.py
    - Usa delays anti-bloqueo automáticos
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import datetime
from bets.utils.sofascore_api import (
    get_football_tournament_season,
    get_football_tournament_events,
    get_football_team,
    SofaScoreTournaments,
)
from bets.models import (
    ApiEquipo, ApiLiga, ApiPais, Deporte, ApiPartido,
    ApiVenue, PartidoStatus
)


# IDs de SofaScore para La Liga
LA_LIGA_TOURNAMENT_ID = 8
LA_LIGA_SEASON_2024_25 = 61642
LA_LIGA_SEASON_2025_26 = 77559


class Command(BaseCommand):
    help = 'Carga inicial de equipos y fixtures de La Liga desde SofaScore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-teams',
            action='store_true',
            help='No cargar equipos, solo fixtures',
        )
        parser.add_argument(
            '--skip-fixtures',
            action='store_true',
            help='No cargar fixtures, solo equipos',
        )
        parser.add_argument(
            '--round',
            type=int,
            help='Cargar solo una jornada específica (ej: 15)',
        )
        parser.add_argument(
            '--tournament-id',
            type=int,
            default=LA_LIGA_TOURNAMENT_ID,
            help='ID del torneo en SofaScore (default: 8 - La Liga)',
        )
        parser.add_argument(
            '--season-id',
            type=int,
            default=LA_LIGA_SEASON_2025_26,
            help='ID de la temporada en SofaScore (default: 77559 - 2025/26)',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("⚽ CARGA INICIAL DE LA LIGA DESDE SOFASCORE"))
        self.stdout.write("="*80 + "\n")

        tournament_id = options['tournament_id']
        season_id = options['season_id']
        skip_teams = options['skip_teams']
        skip_fixtures = options['skip_fixtures']
        specific_round = options['round']

        # Verificar referencias en BD
        try:
            spain = ApiPais.objects.get(code='ES')
            self.stdout.write(self.style.SUCCESS(f"✅ País encontrado: {spain.nombre}"))
        except ApiPais.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "❌ Error: País 'Spain' (ES) no encontrado en BD.\n"
                "   Ejecuta primero: python Populate_countries.py"
            ))
            return

        try:
            futbol = Deporte.objects.get(nombre='Fútbol')
            self.stdout.write(self.style.SUCCESS(f"✅ Deporte encontrado: {futbol.nombre}"))
        except Deporte.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "❌ Error: Deporte 'Fútbol' no encontrado en BD.\n"
                "   Crea un deporte 'Fútbol' en el admin de Django."
            ))
            return

        # Crear o actualizar La Liga
        liga, created = ApiLiga.objects.get_or_create(
            api_id=tournament_id,
            defaults={
                'nombre': 'La Liga',
                'id_pais': spain,
                'id_deporte': futbol,
                'temporada_actual': '2025-26',
                'tipo': 'League',
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"🆕 Liga creada: {liga.nombre}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Liga encontrada: {liga.nombre}"))

        self.stdout.write("")

        # PASO 1: Cargar equipos
        if not skip_teams:
            self.stdout.write(self.style.WARNING("📥 PASO 1: Cargando equipos de La Liga..."))
            self.load_teams(tournament_id, season_id, spain, futbol)
        else:
            self.stdout.write(self.style.WARNING("⏭️  PASO 1: Equipos omitidos (--skip-teams)"))

        self.stdout.write("")

        # PASO 2: Cargar fixtures
        if not skip_fixtures:
            self.stdout.write(self.style.WARNING("📥 PASO 2: Cargando fixtures de La Liga..."))
            self.load_fixtures(tournament_id, season_id, liga, specific_round)
        else:
            self.stdout.write(self.style.WARNING("⏭️  PASO 2: Fixtures omitidos (--skip-fixtures)"))

        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("="*80 + "\n")

        # Resumen final
        total_equipos = ApiEquipo.objects.filter(id_pais=spain, tipo='Club').count()
        total_partidos = ApiPartido.objects.filter(id_liga=liga).count()

        self.stdout.write(f"📊 Equipos en BD: {total_equipos}")
        self.stdout.write(f"📊 Partidos en BD: {total_partidos}\n")

    def load_teams(self, tournament_id, season_id, spain, futbol):
        """Carga los equipos de La Liga desde SofaScore"""

        try:
            teams = []

            # Intentar obtener equipos desde la temporada
            try:
                self.stdout.write("   Obteniendo datos de la temporada...")
                season_data = get_football_tournament_season(tournament_id, season_id)

                # Opción 1: standings
                if 'standings' in season_data:
                    standings = season_data['standings']
                    if isinstance(standings, list) and len(standings) > 0:
                        if 'rows' in standings[0]:
                            for row in standings[0]['rows']:
                                if 'team' in row:
                                    teams.append(row['team'])

                # Opción 2: participants
                if not teams and 'participants' in season_data:
                    teams = season_data['participants']
            except Exception as season_error:
                self.stdout.write(self.style.WARNING(
                    f"   No se pudo obtener datos de temporada: {season_error}"
                ))

            # Si no hay equipos, obtener de eventos/partidos
            if not teams:
                self.stdout.write(self.style.WARNING(
                    "   Obteniendo equipos desde partidos..."
                ))

                # Intentar obtener de todas las jornadas
                teams_dict = {}

                try:
                    events_data = get_football_tournament_events(tournament_id, season_id)
                    events = events_data.get('events', [])

                    for event in events:
                        home_team = event.get('homeTeam', {})
                        away_team = event.get('awayTeam', {})

                        if home_team.get('id'):
                            teams_dict[home_team['id']] = home_team

                        if away_team.get('id'):
                            teams_dict[away_team['id']] = away_team
                except Exception as events_error:
                    self.stdout.write(self.style.WARNING(
                        f"   Error obteniendo eventos: {events_error}"
                    ))

                # Si no funciona, obtener de partidos por fecha
                if not teams_dict:
                    from datetime import datetime, timedelta
                    from bets.utils.sofascore_api import get_football_matches_by_date

                    self.stdout.write("   Obteniendo equipos de partidos recientes...")

                    # Buscar partidos en los últimos 30 días
                    for days_back in range(30):
                        date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                        try:
                            matches_data = get_football_matches_by_date(date)
                            events = matches_data.get('events', [])

                            # Filtrar solo partidos de La Liga
                            laliga_events = [e for e in events
                                           if e.get('tournament', {}).get('uniqueTournament', {}).get('id') == tournament_id]

                            for event in laliga_events:
                                home_team = event.get('homeTeam', {})
                                away_team = event.get('awayTeam', {})

                                if home_team.get('id'):
                                    teams_dict[home_team['id']] = home_team

                                if away_team.get('id'):
                                    teams_dict[away_team['id']] = away_team

                            # Si ya encontramos al menos 15 equipos, suficiente
                            if len(teams_dict) >= 15:
                                break
                        except:
                            continue

                teams = list(teams_dict.values())

            if not teams:
                self.stdout.write(self.style.ERROR("   ❌ No se pudieron obtener equipos"))
                return

            self.stdout.write(f"   ✅ Se encontraron {len(teams)} equipos\n")

            # Guardar equipos en BD
            created_count = 0
            updated_count = 0
            skipped_count = 0

            for team_data in teams:
                team_id = team_data.get('id')
                team_name = team_data.get('name')

                if not team_id or not team_name:
                    skipped_count += 1
                    continue

                # Verificar si ya existe
                existing = ApiEquipo.objects.filter(api_id=team_id).first()

                if existing:
                    # Actualizar si es necesario
                    updated = False
                    if existing.nombre != team_name:
                        existing.nombre = team_name
                        updated = True

                    logo_url = team_data.get('logo')
                    if logo_url and existing.logo_url != logo_url:
                        existing.logo_url = logo_url
                        updated = True

                    if updated:
                        existing.save()
                        updated_count += 1
                        self.stdout.write(f"   🔄 Actualizado: {team_name}")
                    else:
                        skipped_count += 1
                else:
                    # Crear nuevo equipo
                    equipo = ApiEquipo.objects.create(
                        api_id=team_id,
                        nombre=team_name,
                        nombre_corto=team_data.get('shortName', team_name[:20]),
                        logo_url=team_data.get('logo'),
                        id_pais=spain,
                        id_deporte=futbol,
                        tipo='Club',
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"   🆕 Creado: {team_name}"))

            self.stdout.write(f"\n   Resumen:")
            self.stdout.write(f"   - Creados: {created_count}")
            self.stdout.write(f"   - Actualizados: {updated_count}")
            self.stdout.write(f"   - Sin cambios: {skipped_count}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error cargando equipos: {e}"))
            import traceback
            traceback.print_exc()

    def load_fixtures(self, tournament_id, season_id, liga, specific_round=None):
        """Carga los fixtures de La Liga desde SofaScore"""

        try:
            created_count = 0
            updated_count = 0
            skipped_count = 0

            if specific_round:
                # Cargar solo una jornada específica
                rounds_to_load = [specific_round]
                self.stdout.write(f"   Cargando solo jornada {specific_round}...")
            else:
                # Cargar todas las jornadas (1-38 para La Liga)
                rounds_to_load = range(1, 39)
                self.stdout.write("   Cargando todas las jornadas (1-38)...")

            for round_num in rounds_to_load:
                try:
                    events_data = get_football_tournament_events(
                        tournament_id,
                        season_id,
                        round_number=round_num
                    )

                    events = events_data.get('events', [])

                    if not events:
                        continue

                    self.stdout.write(f"   Jornada {round_num}: {len(events)} partidos")

                    for event in events:
                        result = self.save_fixture(event, liga, round_num)
                        if result == 'created':
                            created_count += 1
                        elif result == 'updated':
                            updated_count += 1
                        else:
                            skipped_count += 1

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Error en jornada {round_num}: {e}"))
                    continue

            self.stdout.write(f"\n   Resumen:")
            self.stdout.write(f"   - Creados: {created_count}")
            self.stdout.write(f"   - Actualizados: {updated_count}")
            self.stdout.write(f"   - Sin cambios: {skipped_count}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error cargando fixtures: {e}"))
            import traceback
            traceback.print_exc()

    def save_fixture(self, event, liga, round_num):
        """Guarda o actualiza un fixture en la BD"""

        try:
            event_id = event.get('id')
            home_team_data = event.get('homeTeam', {})
            away_team_data = event.get('awayTeam', {})

            home_team_id = home_team_data.get('id')
            away_team_id = away_team_data.get('id')

            if not event_id or not home_team_id or not away_team_id:
                return 'skipped'

            # Buscar equipos en BD
            home_team = ApiEquipo.objects.filter(api_id=home_team_id).first()
            away_team = ApiEquipo.objects.filter(api_id=away_team_id).first()

            if not home_team or not away_team:
                self.stdout.write(self.style.WARNING(
                    f"      ⚠️ Equipos no encontrados: {home_team_data.get('name')} vs {away_team_data.get('name')}"
                ))
                return 'skipped'

            # Extraer datos del evento
            timestamp = event.get('startTimestamp')
            if timestamp:
                from datetime import datetime as dt
                fecha = timezone.make_aware(dt.fromtimestamp(timestamp))
            else:
                fecha = timezone.now()

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
            }
            estado = status_mapping.get(status_type, PartidoStatus.PROGRAMADO)

            # Extraer marcadores
            home_score = event.get('homeScore', {})
            away_score = event.get('awayScore', {})

            goles_local = home_score.get('current')
            goles_visitante = away_score.get('current')

            # Crear o actualizar partido
            partido, created = ApiPartido.objects.update_or_create(
                api_fixture_id=event_id,
                defaults={
                    'id_liga': liga,
                    'equipo_local': home_team,
                    'equipo_visitante': away_team,
                    'fecha': fecha,
                    'ronda': f"Regular - {round_num}",
                    'temporada': '2025-26',
                    'estado': estado,
                    'goles_local': goles_local,
                    'goles_visitante': goles_visitante,
                }
            )

            if created:
                return 'created'
            else:
                return 'updated'

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error guardando fixture: {e}"))
            return 'skipped'
