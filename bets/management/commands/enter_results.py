"""
Entrada manual de resultados de partidos finalizados.

Uso:
    docker compose exec -it web python manage.py enter_results --date 2026-06-11

El comando muestra los partidos del día y pide el marcador para cada uno.
Formato de marcador: "2-1"  (local-visitante). Enter sin texto = saltar partido.

Después de cargar los resultados, procesa automáticamente las apuestas pendientes.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, timezone as dt_tz
import datetime as dt_module

from bets.models import ApiPartido, ApuestaFutbol, PartidoStatus


class Command(BaseCommand):
    help = 'Entrada manual de resultados para partidos de un día específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            required=True,
            help='Fecha en formato YYYY-MM-DD (ej: 2026-06-11)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra los partidos del día sin modificar nada',
        )

    def handle(self, *args, **options):
        # Parsear fecha
        try:
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        except ValueError:
            self.stdout.write(self.style.ERROR('❌ Formato de fecha inválido. Usa YYYY-MM-DD'))
            return

        dry_run = options['dry_run']

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS(
            f'⚽  RESULTADOS — {target_date.strftime("%A %d %B %Y").upper()}'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('   [DRY RUN — no se guardan cambios]'))
        self.stdout.write('=' * 70 + '\n')

        # Obtener partidos del día (en UTC, buscar rango completo del día)
        day_start = timezone.make_aware(
            datetime.combine(target_date, dt_module.time.min), dt_tz.utc
        )
        day_end = timezone.make_aware(
            datetime.combine(target_date, dt_module.time.max), dt_tz.utc
        )

        partidos = ApiPartido.objects.filter(
            fecha__range=(day_start, day_end)
        ).select_related(
            'equipo_local', 'equipo_visitante', 'id_liga'
        ).order_by('fecha')

        if not partidos.exists():
            self.stdout.write(self.style.WARNING(
                f'   No hay partidos registrados para {target_date}.'
            ))
            return

        self.stdout.write(f'   Partidos encontrados: {partidos.count()}\n')

        updated = 0
        skipped = 0
        bets_processed = 0

        for partido in partidos:
            hora_utc = partido.fecha.strftime('%H:%M UTC')
            local = partido.equipo_local.nombre if partido.equipo_local else '?'
            visitante = partido.equipo_visitante.nombre if partido.equipo_visitante else '?'
            liga = partido.id_liga.nombre if partido.id_liga else ''
            estado_actual = partido.estado

            # Mostrar info del partido
            self.stdout.write(
                f'  [{hora_utc}]  {local}  vs  {visitante}  ({liga})'
            )

            if estado_actual == PartidoStatus.FINALIZADO:
                self.stdout.write(self.style.SUCCESS(
                    f'         → Ya tiene resultado: '
                    f'{partido.goles_local}-{partido.goles_visitante}  (omitir con Enter para no cambiar)\n'
                ))
            else:
                self.stdout.write(
                    f'         → Estado actual: {estado_actual}\n'
                )

            if dry_run:
                continue

            # Pedir marcador
            try:
                raw = input(f'         Marcador [{local[:12]} - {visitante[:12]}] (ej: 2-1, Enter=saltar): ').strip()
            except (EOFError, KeyboardInterrupt):
                self.stdout.write('\n' + self.style.WARNING('   Interrumpido.'))
                break

            if not raw:
                self.stdout.write(self.style.WARNING('         ⏭  Saltado\n'))
                skipped += 1
                continue

            # Validar formato
            try:
                parts = raw.split('-')
                if len(parts) != 2:
                    raise ValueError
                goles_local = int(parts[0].strip())
                goles_visitante = int(parts[1].strip())
                if goles_local < 0 or goles_visitante < 0:
                    raise ValueError
            except ValueError:
                self.stdout.write(self.style.ERROR(
                    '         ❌ Formato inválido, saltando. Usa el formato: 2-1\n'
                ))
                skipped += 1
                continue

            # Actualizar partido
            partido.goles_local = goles_local
            partido.goles_visitante = goles_visitante
            partido.estado = PartidoStatus.FINALIZADO
            partido.save(update_fields=['goles_local', 'goles_visitante', 'estado'])

            self.stdout.write(self.style.SUCCESS(
                f'         ✅ Guardado: {local} {goles_local}-{goles_visitante} {visitante}\n'
            ))
            updated += 1

            # Procesar apuestas pendientes de este partido
            apuestas = ApuestaFutbol.objects.filter(
                id_partido=partido,
                estado='pendiente'
            )
            for apuesta in apuestas:
                apuesta.calcular_y_actualizar_puntos()
                bets_processed += 1

            if bets_processed > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'         🎯 {bets_processed} apuesta(s) procesada(s)\n'
                ))
                bets_processed = 0  # reset per match for display

        # Resumen
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'   ✅ Resultados guardados: {updated}')
        self.stdout.write(f'   ⏭  Saltados:             {skipped}')
        if dry_run:
            self.stdout.write(self.style.WARNING('\n   [DRY RUN — nada fue guardado]\n'))
        else:
            self.stdout.write('')

        # Actualizar cruces eliminatorios del Mundial (idempotente)
        if updated > 0 and not dry_run:
            from django.core.management import call_command
            self.stdout.write('🏆 Actualizando cruces del Mundial 2026...')
            try:
                call_command('update_worldcup_bracket', no_input=True)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(
                    f'   ⚠️  No se pudieron actualizar los cruces: {exc}'))
