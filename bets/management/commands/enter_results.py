"""
Entrada manual de resultados de partidos finalizados.

MODO AUTOMÁTICO (recomendado):
    docker compose exec -it web python manage.py enter_results

    Busca TODOS los partidos pasados sin marcador completo, agrupados por fecha.
    Útil cuando no actualizas diario.

MODO POR FECHA (un día específico):
    docker compose exec -it web python manage.py enter_results --date 2026-06-11

OPCIONES:
    --date YYYY-MM-DD   Solo partidos de esa fecha
    --days-back N       Buscar hasta N días atrás (default: 60)
    --dry-run           Solo muestra lo pendiente, no pide marcadores
    --force             Permite re-ingresar marcadores ya finalizados

Formato de marcador: "2-1"  (local-visitante)
Enter sin texto = saltar partido.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from datetime import timezone as dt_tz
import datetime as dt_module
from collections import defaultdict

from bets.models import ApiPartido, ApuestaFutbol, PartidoStatus

COL_WIDTH = 70


def hr(char='='):
    return char * COL_WIDTH


class Command(BaseCommand):
    help = 'Entrada manual de resultados — busca todos los pendientes automáticamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date', type=str, default=None,
            help='Filtrar solo esta fecha (YYYY-MM-DD). Sin esto busca todos los pendientes.',
        )
        parser.add_argument(
            '--days-back', type=int, default=60,
            help='Buscar hasta N días atrás (default: 60).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra partidos pendientes sin pedir marcadores.',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Permite re-ingresar marcadores ya finalizados.',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']
        force = options['force']
        days_back = options['days_back']
        date_filter = options['date']

        self.stdout.write('\n' + hr())
        self.stdout.write(self.style.SUCCESS(
            '  FRIENDLYBET — INGRESO DE RESULTADOS'
        ))
        self.stdout.write(f'  Hora actual: {now.strftime("%Y-%m-%d %H:%M UTC")}')
        if dry_run:
            self.stdout.write(self.style.WARNING('  [DRY RUN — solo lectura]'))
        self.stdout.write(hr() + '\n')

        # ── Construir queryset ──────────────────────────────────────────────
        cutoff = now - timedelta(days=days_back)

        qs = ApiPartido.objects.filter(
            fecha__lt=now,
            fecha__gte=cutoff,
        ).select_related('equipo_local', 'equipo_visitante', 'id_liga').order_by('fecha')

        if date_filter:
            try:
                target = datetime.strptime(date_filter, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('❌ Fecha inválida. Usa YYYY-MM-DD'))
                return
            day_start = timezone.make_aware(datetime.combine(target, dt_module.time.min), dt_tz.utc)
            day_end   = timezone.make_aware(datetime.combine(target, dt_module.time.max), dt_tz.utc)
            qs = qs.filter(fecha__range=(day_start, day_end))
            self.stdout.write(f'  Filtrando: {target}\n')
        else:
            self.stdout.write(f'  Buscando partidos sin marcador (últimos {days_back} días)\n')

        # Partidos SIN marcador completo (pendientes)
        if not force:
            pending_qs = qs.exclude(
                Q(estado=PartidoStatus.FINALIZADO) &
                Q(goles_local__isnull=False) &
                Q(goles_visitante__isnull=False)
            )
        else:
            pending_qs = qs  # incluye finalizados para re-ingreso

        total_pending = pending_qs.count()

        if total_pending == 0:
            self.stdout.write(self.style.SUCCESS(
                '  ✅ ¡Al día! No hay partidos pasados sin marcador.'
            ))
            self.stdout.write(hr() + '\n')
            return

        self.stdout.write(self.style.WARNING(
            f'  ⚠️  {total_pending} partido(s) pendientes por ingresar marcador'
        ))
        self.stdout.write(hr('-') + '\n')

        # ── Agrupar por fecha (día en UTC) ──────────────────────────────────
        by_date = defaultdict(list)
        for p in pending_qs:
            day_key = p.fecha.date()
            by_date[day_key].append(p)

        updated_total = 0
        skipped_total = 0
        partidos_con_resultado = []  # para procesar apuestas al final

        for day in sorted(by_date.keys()):
            partidos_dia = by_date[day]
            label = day.strftime('%A %d %B %Y').upper()

            self.stdout.write('\n' + self.style.SUCCESS(f'  📅  {label}'))
            self.stdout.write(f'  {len(partidos_dia)} partido(s)')
            self.stdout.write(hr('-'))

            for partido in partidos_dia:
                hora   = partido.fecha.strftime('%H:%M UTC')
                local  = partido.equipo_local.nombre if partido.equipo_local else '?'
                visita = partido.equipo_visitante.nombre if partido.equipo_visitante else '?'
                liga   = partido.id_liga.nombre if partido.id_liga else ''

                ya_tiene = (
                    partido.estado == PartidoStatus.FINALIZADO and
                    partido.goles_local is not None and
                    partido.goles_visitante is not None
                )

                self.stdout.write('\n')
                self.stdout.write(
                    f'  [{hora}]  {local}  vs  {visita}' +
                    (f'  ({liga})' if liga else '')
                )

                if ya_tiene:
                    self.stdout.write(self.style.SUCCESS(
                        f'  → Ya finalizado: {partido.goles_local}-{partido.goles_visitante}'
                        + (' (--force para re-ingresar)' if not force else '')
                    ))
                    if not force:
                        skipped_total += 1
                        continue
                else:
                    self.stdout.write(f'  → Estado: {partido.estado}')

                if dry_run:
                    continue

                # Pedir marcador
                local_short  = local[:14]
                visita_short = visita[:14]
                prompt = f'  Marcador [{local_short} - {visita_short}] (ej: 2-1, Enter=saltar): '

                try:
                    raw = input(prompt).strip()
                except (EOFError, KeyboardInterrupt):
                    self.stdout.write('\n' + self.style.WARNING('  Interrumpido. Guardando lo que se ingresó.'))
                    break

                if not raw:
                    self.stdout.write(self.style.WARNING('  ⏭  Saltado'))
                    skipped_total += 1
                    continue

                # Validar "X-Y"
                try:
                    partes = raw.replace(' ', '').split('-')
                    if len(partes) != 2:
                        raise ValueError
                    gl = int(partes[0])
                    gv = int(partes[1])
                    if gl < 0 or gv < 0:
                        raise ValueError
                except ValueError:
                    self.stdout.write(self.style.ERROR(
                        '  ❌ Formato inválido. Usa: 2-1 (local-visitante). Partido saltado.'
                    ))
                    skipped_total += 1
                    continue

                partido.goles_local     = gl
                partido.goles_visitante = gv
                partido.estado          = PartidoStatus.FINALIZADO
                partido.save(update_fields=['goles_local', 'goles_visitante', 'estado'])

                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Guardado: {local} {gl}-{gv} {visita}'
                ))
                updated_total += 1
                partidos_con_resultado.append(partido)

        # ── Procesar apuestas de todos los partidos actualizados ────────────
        if partidos_con_resultado and not dry_run:
            self.stdout.write('\n' + hr('-'))
            self.stdout.write('  🎯 Calculando puntos de apuestas...')
            bets_total = 0
            for partido in partidos_con_resultado:
                apuestas = ApuestaFutbol.objects.filter(
                    id_partido=partido,
                    estado='pendiente'
                )
                for apuesta in apuestas:
                    apuesta.calcular_y_actualizar_puntos()
                    bets_total += 1
            self.stdout.write(self.style.SUCCESS(
                f'  ✅ {bets_total} apuesta(s) procesada(s)'
            ))

        # Actualizar cruces del Mundial si hubo cambios
        if updated_total > 0 and not dry_run:
            from django.core.management import call_command
            self.stdout.write('  🏆 Actualizando cruces del Mundial 2026...')
            try:
                call_command('update_worldcup_bracket', no_input=True)
                self.stdout.write(self.style.SUCCESS('  ✅ Cruces actualizados'))
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'  ⚠️  No se actualizaron cruces: {exc}'))

        # ── Resumen final ───────────────────────────────────────────────────
        self.stdout.write('\n' + hr())
        self.stdout.write(self.style.SUCCESS('  RESUMEN'))
        self.stdout.write(hr())
        self.stdout.write(f'  ✅ Marcadores guardados : {updated_total}')
        self.stdout.write(f'  ⏭  Saltados / ya tenían: {skipped_total}')
        self.stdout.write(f'  📅 Fechas cubiertas     : {len(by_date)}')
        if dry_run:
            self.stdout.write(self.style.WARNING('  [DRY RUN — nada fue guardado]'))
        self.stdout.write(hr() + '\n')
