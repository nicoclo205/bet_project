"""
Comando Django para cargar estadísticas detalladas de partidos finalizados.

Este comando:
1. Busca partidos finalizados sin estadísticas cargadas
2. Obtiene las estadísticas desde SofaScore
3. Guarda las estadísticas en la base de datos

Uso:
    python manage.py load_match_statistics
    python manage.py load_match_statistics --limit 20
    python manage.py load_match_statistics --force  # Recargar estadísticas
"""

from django.core.management.base import BaseCommand
from bets.utils.sofascore_api import get_event_statistics
from bets.models import ApiPartido, ApiPartidoEstadisticas, PartidoStatus
import time


class Command(BaseCommand):
    help = 'Carga estadísticas detalladas de partidos finalizados desde SofaScore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Número máximo de partidos a procesar (default: 50)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar recarga de estadísticas ya cargadas',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("📊 CARGA DE ESTADÍSTICAS DE PARTIDOS"))
        self.stdout.write("="*80 + "\n")

        limit = options['limit']
        force = options['force']

        # Estadísticas
        self.stats = {
            'procesados': 0,
            'exitosos': 0,
            'sin_datos': 0,
            'errores': 0,
        }

        # Obtener partidos finalizados
        if force:
            partidos = ApiPartido.objects.filter(
                estado=PartidoStatus.FINALIZADO
            ).order_by('-fecha')[:limit]
            self.stdout.write(f"🔍 Modo forzado: recargando estadísticas de {partidos.count()} partidos")
        else:
            partidos = ApiPartido.objects.filter(
                estado=PartidoStatus.FINALIZADO,
                estadisticas_cargadas=False
            ).order_by('-fecha')[:limit]
            self.stdout.write(f"🔍 Encontrados {partidos.count()} partidos finalizados sin estadísticas\n")

        if partidos.count() == 0:
            self.stdout.write(self.style.SUCCESS("✅ No hay partidos para procesar"))
            return

        # Procesar cada partido
        for partido in partidos:
            self.process_match_statistics(partido, force)
            time.sleep(2)  # Delay para no saturar la API

        # Mostrar resumen
        self.show_summary()

    def process_match_statistics(self, partido, force=False):
        """Procesa y guarda las estadísticas de un partido"""
        try:
            self.stats['procesados'] += 1

            match_info = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"
            self.stdout.write(f"\n📊 [{self.stats['procesados']}] {match_info}")
            self.stdout.write(f"   Fecha: {partido.fecha.strftime('%Y-%m-%d')}")
            self.stdout.write(f"   Resultado: {partido.goles_local} - {partido.goles_visitante}")

            # Obtener estadísticas desde SofaScore
            try:
                stats_data = get_event_statistics(partido.api_fixture_id)
            except Exception as e:
                if "404" in str(e):
                    self.stdout.write(self.style.WARNING(f"   ⚠️  No hay estadísticas disponibles"))
                    self.stats['sin_datos'] += 1
                    return
                raise

            if not stats_data or 'statistics' not in stats_data:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Respuesta sin datos de estadísticas"))
                self.stats['sin_datos'] += 1
                return

            statistics = stats_data.get('statistics', [])

            if len(statistics) < 2:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Datos incompletos"))
                self.stats['sin_datos'] += 1
                return

            # Procesar estadísticas de cada equipo
            for period_stats in statistics:
                if period_stats.get('period') != 'ALL':
                    continue  # Solo procesar estadísticas del partido completo

                groups = period_stats.get('groups', [])

                # Procesar estadísticas del equipo local
                home_stats = self.extract_team_statistics(groups, 0)
                self.save_team_statistics(partido, partido.equipo_local, home_stats, force)

                # Procesar estadísticas del equipo visitante
                away_stats = self.extract_team_statistics(groups, 1)
                self.save_team_statistics(partido, partido.equipo_visitante, away_stats, force)

            # Marcar partido como estadísticas cargadas
            partido.estadisticas_cargadas = True
            partido.save()

            self.stdout.write(self.style.SUCCESS(f"   ✅ Estadísticas guardadas correctamente"))
            self.stats['exitosos'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error: {e}"))
            self.stats['errores'] += 1

    def extract_team_statistics(self, groups, team_index):
        """Extrae estadísticas de un equipo desde los grupos de estadísticas"""
        stats = {}

        for group in groups:
            for stat_item in group.get('statisticsItems', []):
                name = stat_item.get('name', '')
                value = stat_item.get('home' if team_index == 0 else 'away')

                # Mapear nombres de estadísticas
                stat_mapping = {
                    'Ball possession': 'posesion',
                    'Total shots': 'tiros_total',
                    'Shots on target': 'tiros_a_puerta',
                    'Shots off target': 'tiros_fuera',
                    'Blocked shots': 'tiros_bloqueados',
                    'Corner kicks': 'corners',
                    'Offsides': 'offsides',
                    'Fouls': 'faltas',
                    'Yellow cards': 'tarjetas_amarillas',
                    'Red cards': 'tarjetas_rojas',
                }

                if name in stat_mapping:
                    field_name = stat_mapping[name]

                    # Convertir posesión de string a float
                    if field_name == 'posesion' and isinstance(value, str):
                        value = float(value.replace('%', ''))

                    stats[field_name] = value

        return stats

    def save_team_statistics(self, partido, equipo, stats, force=False):
        """Guarda las estadísticas de un equipo"""
        if not stats:
            return

        # Crear o actualizar estadísticas
        obj, created = ApiPartidoEstadisticas.objects.update_or_create(
            id_partido=partido,
            id_equipo=equipo,
            defaults=stats
        )

        if created or force:
            action = "Creadas" if created else "Actualizadas"
            self.stdout.write(f"      {action}: {equipo.nombre}")

    def show_summary(self):
        """Muestra el resumen de la ejecución"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("="*80 + "\n")

        self.stdout.write(f"📊 Partidos procesados: {self.stats['procesados']}")
        self.stdout.write(f"✅ Estadísticas cargadas: {self.stats['exitosos']}")
        self.stdout.write(f"⚠️  Sin datos disponibles: {self.stats['sin_datos']}")

        if self.stats['errores'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Errores: {self.stats['errores']}"))

        self.stdout.write("")
