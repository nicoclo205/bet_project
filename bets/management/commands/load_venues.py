"""
Comando Django para cargar información de estadios/venues para partidos existentes.

Este comando:
1. Busca partidos sin venue asignado
2. Obtiene información del venue desde SofaScore
3. Crea el venue en la BD y lo asocia al partido

Uso:
    python manage.py load_venues
    python manage.py load_venues --limit 50
    python manage.py load_venues --force  # Recargar venues
"""

from django.core.management.base import BaseCommand
from bets.utils.sofascore_api import get_event
from bets.models import ApiPartido, ApiVenue, ApiPais
import time


class Command(BaseCommand):
    help = 'Carga información de estadios/venues para partidos desde SofaScore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Número máximo de partidos a procesar (default: 100)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar recarga de venues ya cargados',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("🏟️  CARGA DE ESTADIOS/VENUES"))
        self.stdout.write("="*80 + "\n")

        limit = options['limit']
        force = options['force']

        # Estadísticas
        self.stats = {
            'procesados': 0,
            'venues_creados': 0,
            'partidos_actualizados': 0,
            'sin_venue': 0,
            'errores': 0,
        }

        # Obtener partidos sin venue
        if force:
            partidos = ApiPartido.objects.all().order_by('-fecha')[:limit]
            self.stdout.write(f"🔍 Modo forzado: recargando venues de {partidos.count()} partidos")
        else:
            partidos = ApiPartido.objects.filter(
                id_venue__isnull=True
            ).order_by('-fecha')[:limit]
            self.stdout.write(f"🔍 Encontrados {partidos.count()} partidos sin venue\n")

        if partidos.count() == 0:
            self.stdout.write(self.style.SUCCESS("✅ No hay partidos para procesar"))
            return

        # Procesar cada partido
        for partido in partidos:
            self.process_match_venue(partido, force)
            time.sleep(2)  # Delay para no saturar la API

        # Mostrar resumen
        self.show_summary()

    def process_match_venue(self, partido, force=False):
        """Procesa y guarda el venue de un partido"""
        try:
            self.stats['procesados'] += 1

            match_info = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}"
            self.stdout.write(f"\n🏟️  [{self.stats['procesados']}] {match_info}")
            self.stdout.write(f"   Fecha: {partido.fecha.strftime('%Y-%m-%d')}")

            # Obtener detalles del partido desde SofaScore
            try:
                event_data = get_event(partido.api_fixture_id)
            except Exception as e:
                if "404" in str(e):
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Evento no encontrado"))
                    self.stats['sin_venue'] += 1
                    return
                raise

            if not event_data or 'event' not in event_data:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Respuesta sin datos del evento"))
                self.stats['sin_venue'] += 1
                return

            event = event_data.get('event', {})
            venue_data = event.get('venue')

            if not venue_data:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Partido sin información de venue"))
                self.stats['sin_venue'] += 1
                return

            # Procesar y guardar venue
            venue = self.process_venue(venue_data)

            if venue:
                # Asociar venue al partido
                partido.id_venue = venue
                partido.save()

                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ Venue: {venue.nombre}, {venue.ciudad or 'N/A'}"
                ))
                self.stats['partidos_actualizados'] += 1
            else:
                self.stats['sin_venue'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error: {e}"))
            self.stats['errores'] += 1

    def process_venue(self, venue_data):
        """Procesa y guarda un venue en la BD"""
        try:
            venue_id = venue_data.get('id')
            venue_name = venue_data.get('name')

            if not venue_id or not venue_name:
                return None

            # Obtener ciudad
            city_data = venue_data.get('city', {})
            city_name = city_data.get('name')

            # Obtener país del venue
            country_data = venue_data.get('country', {})
            country_code = country_data.get('alpha2', 'INT')
            country_name = country_data.get('name', 'International')

            # Crear o obtener país
            pais, _ = ApiPais.objects.get_or_create(
                code=country_code,
                defaults={'nombre': country_name}
            )

            # Obtener capacidad
            capacity = venue_data.get('capacity')

            # Crear o actualizar venue
            venue, created = ApiVenue.objects.update_or_create(
                api_id=venue_id,
                defaults={
                    'nombre': venue_name,
                    'ciudad': city_name,
                    'id_pais': pais,
                    'capacidad': capacity,
                    'superficie': 'Grass',  # SofaScore no siempre provee este dato
                }
            )

            if created:
                self.stats['venues_creados'] += 1

            return venue

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Error procesando venue: {e}"))
            self.stats['errores'] += 1
            return None

    def show_summary(self):
        """Muestra el resumen de la ejecución"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("="*80 + "\n")

        self.stdout.write(f"📊 Partidos procesados: {self.stats['procesados']}")
        self.stdout.write(f"🏟️  Venues creados: {self.stats['venues_creados']}")
        self.stdout.write(f"✅ Partidos actualizados: {self.stats['partidos_actualizados']}")
        self.stdout.write(f"⚠️  Sin venue disponible: {self.stats['sin_venue']}")

        if self.stats['errores'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Errores: {self.stats['errores']}"))

        self.stdout.write("")
