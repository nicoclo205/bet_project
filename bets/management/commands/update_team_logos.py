"""
Comando Django para actualizar logos de equipos desde SofaScore.

Este comando actualiza los logos de equipos que aparecen en próximos partidos,
obteniendo las URLs correctas desde la API de SofaScore.

Uso:
    python manage.py update_team_logos

    # Con opciones:
    python manage.py update_team_logos --all  # Actualizar todos los equipos
    python manage.py update_team_logos --limit 50  # Solo próximos 50 partidos
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from bets.models import ApiEquipo, ApiPartido, PartidoStatus
import time
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


class Command(BaseCommand):
    help = 'Actualiza logos de equipos desde SofaScore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Actualizar todos los equipos en la BD',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Número de próximos partidos a considerar (default: 50)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización incluso si ya tienen logo',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("ACTUALIZACION DE LOGOS DE EQUIPOS"))
        self.stdout.write("="*80 + "\n")

        update_all = options['all']
        limit = options['limit']
        force = options['force']

        if update_all:
            self.stdout.write("Modo: Actualizar TODOS los equipos en la BD")
            equipos_a_actualizar = ApiEquipo.objects.all()
        else:
            self.stdout.write(f"Modo: Actualizar equipos en proximos {limit} partidos")
            # Obtener equipos que aparecen en próximos partidos
            equipos_a_actualizar = self.get_teams_in_upcoming_matches(limit)

        if not equipos_a_actualizar:
            self.stdout.write(self.style.WARNING("No hay equipos para actualizar"))
            return

        total_equipos = len(equipos_a_actualizar) if isinstance(equipos_a_actualizar, list) else equipos_a_actualizar.count()
        self.stdout.write(f"Total equipos a procesar: {total_equipos}\n")

        # Filtrar equipos sin logo o si se fuerza la actualización
        if not force:
            if isinstance(equipos_a_actualizar, list):
                equipos_a_actualizar = [e for e in equipos_a_actualizar if not e.logo_url]
            else:
                equipos_a_actualizar = equipos_a_actualizar.filter(logo_url__isnull=True)

            equipos_count = len(equipos_a_actualizar) if isinstance(equipos_a_actualizar, list) else equipos_a_actualizar.count()
            self.stdout.write(f"Equipos sin logo: {equipos_count}\n")

        # Actualizar logos
        updated_count = 0
        failed_count = 0
        skipped_count = 0

        for equipo in equipos_a_actualizar:
            if not equipo.api_id:
                self.stdout.write(self.style.WARNING(f"   {equipo.nombre}: Sin api_id"))
                skipped_count += 1
                continue

            try:
                # Simplemente construir la URL del logo directamente
                self.stdout.write(f"   Actualizando logo de: {equipo.nombre}...", ending='')

                # La URL del logo en SofaScore sigue el patrón:
                # https://api.sofascore.app/api/v1/team/{team_id}/image
                logo_url = f"https://api.sofascore.app/api/v1/team/{equipo.api_id}/image"

                # Actualizar equipo
                equipo.logo_url = logo_url
                equipo.save()

                self.stdout.write(self.style.SUCCESS(" OK"))
                updated_count += 1

                # Delay para evitar rate limiting
                time.sleep(0.3)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f" Error: {e}"))
                failed_count += 1
                time.sleep(1)  # Delay más largo en caso de error

        # Resumen
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("ACTUALIZACION COMPLETADA"))
        self.stdout.write("="*80 + "\n")

        self.stdout.write(f"Resumen:")
        self.stdout.write(f"   - Actualizados: {updated_count}")
        self.stdout.write(f"   - Fallidos: {failed_count}")
        self.stdout.write(f"   - Omitidos: {skipped_count}")
        self.stdout.write(f"   - Total: {updated_count + failed_count + skipped_count}\n")

    def get_teams_in_upcoming_matches(self, limit):
        """Obtiene equipos únicos que aparecen en próximos partidos"""

        ahora = timezone.now()

        # Obtener próximos partidos
        partidos = ApiPartido.objects.filter(
            fecha__gte=ahora,
            estado=PartidoStatus.PROGRAMADO
        ).select_related('equipo_local', 'equipo_visitante').order_by('fecha')[:limit]

        # Extraer equipos únicos
        equipos_ids = set()
        for partido in partidos:
            if partido.equipo_local:
                equipos_ids.add(partido.equipo_local.id_equipo)
            if partido.equipo_visitante:
                equipos_ids.add(partido.equipo_visitante.id_equipo)

        # Obtener objetos de equipo
        equipos = ApiEquipo.objects.filter(id_equipo__in=equipos_ids)

        self.stdout.write(f"   Encontrados {len(equipos_ids)} equipos unicos en {partidos.count()} partidos")

        return list(equipos)
