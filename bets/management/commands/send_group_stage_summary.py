"""
Django management command: send_group_stage_summary

Sends a group-stage wrap-up email to every verified member of each active room
once all group-stage matches have finished.

Gate conditions (all must pass before any email is sent):
  1. All matches whose 'ronda' contains RONDA_PATRON are in 'finalizado' state.
  2. No email has already been sent for this room in this phase
     (idempotent lock via SalaNotificacion with tipo='resumen_fase_grupo').

Usage:
    python manage.py send_group_stage_summary
    python manage.py send_group_stage_summary --dry-run
    python manage.py send_group_stage_summary --ronda-patron "Group Stage"
    python manage.py send_group_stage_summary --liga-id 1 --ronda-patron "Group Stage"
    python manage.py send_group_stage_summary --sala-id 3
"""

import logging

from django.core.management.base import BaseCommand
from django.db.models import Sum

from bets.models import (
    ApiPartido,
    ApuestaFutbol,
    ApuestaStatus,
    PartidoStatus,
    Sala,
    SalaNotificacion,
    UsuarioSala,
)

logger = logging.getLogger(__name__)

TIPO_RESUMEN = 'resumen_fase_grupo'


class Command(BaseCommand):
    help = 'Verifica que la fase de grupos haya terminado y envía el resumen por email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin enviar emails ni marcar notificaciones',
        )
        parser.add_argument(
            '--ronda-patron',
            default='group',
            help='Fragmento de texto (case-insensitive) para identificar '
                 'partidos de fase de grupos via ronda__icontains. '
                 'Default: "group"',
        )
        parser.add_argument(
            '--liga-id',
            type=int,
            default=None,
            help='Limita la búsqueda de partidos a una liga concreta (id_liga)',
        )
        parser.add_argument(
            '--sala-id',
            type=int,
            default=None,
            help='Procesa únicamente la sala con este ID en lugar de todas',
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        patron = options['ronda_patron']
        liga_id = options['liga_id']
        sala_id = options['sala_id']

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('🏆 RESUMEN FASE DE GRUPOS — FriendlyBet'))
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO DRY-RUN (sin cambios reales)'))
        self.stdout.write('=' * 70 + '\n')

        # ── GATE 1: verificar que TODOS los partidos de grupo están finalizados ──
        group_qs = ApiPartido.objects.filter(ronda__icontains=patron)
        if liga_id:
            group_qs = group_qs.filter(id_liga_id=liga_id)

        total_grupo = group_qs.count()
        if total_grupo == 0:
            self.stdout.write(self.style.WARNING(
                f'No se encontraron partidos con ronda__icontains="{patron}"'
                + (f' en liga {liga_id}' if liga_id else '')
                + '. Abortando.'
            ))
            return

        finalizados = group_qs.filter(estado=PartidoStatus.FINALIZADO).count()
        self.stdout.write(
            f'Partidos de fase de grupos: {finalizados}/{total_grupo} finalizados\n'
        )

        if finalizados < total_grupo:
            pendientes = group_qs.exclude(estado=PartidoStatus.FINALIZADO)
            self.stdout.write(self.style.ERROR(
                f'❌ GATE FAIL: {total_grupo - finalizados} partido(s) aún no finalizado(s). '
                'No se enviarán emails.'
            ))
            self.stdout.write('   Partidos pendientes (muestra):')
            for p in pendientes.select_related('equipo_local', 'equipo_visitante')[:5]:
                self.stdout.write(
                    f'      • {p.equipo_local.nombre} vs {p.equipo_visitante.nombre} '
                    f'— estado: {p.estado} — fecha: {p.fecha:%Y-%m-%d %H:%M}'
                )
            return

        self.stdout.write(self.style.SUCCESS(
            '✅ GATE PASS: todos los partidos de grupo están finalizados.\n'
        ))

        group_ids = list(group_qs.values_list('id_partido', flat=True))

        # ── Obtener salas a procesar ──
        salas_qs = Sala.objects.filter(estado=True)
        if sala_id:
            salas_qs = salas_qs.filter(id_sala=sala_id)

        salas = list(salas_qs)
        if not salas:
            self.stdout.write(self.style.WARNING('No hay salas activas para procesar.'))
            return

        self.stdout.write(f'Salas a procesar: {len(salas)}\n')

        stats = {'sent': 0, 'skipped': 0, 'failed': 0}

        for sala in salas:
            result = self._procesar_sala(sala, group_ids, dry_run)
            for key in stats:
                stats[key] += result.get(key, 0)

        # ── Resumen final ──
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('RESUMEN FINAL'))
        self.stdout.write(f'  Emails enviados : {stats["sent"]}')
        self.stdout.write(f'  Salas saltadas  : {stats["skipped"]} (ya enviados)')
        self.stdout.write(f'  Fallos          : {stats["failed"]}')
        self.stdout.write('=' * 70 + '\n')

    # ------------------------------------------------------------------
    def _procesar_sala(self, sala, group_ids, dry_run):
        """
        Procesa una sala individual.  Devuelve dict con claves sent/skipped/failed.
        """
        self.stdout.write(f'\n📋 Sala: "{sala.nombre}" (id={sala.id_sala})')

        # ── GATE 2: idempotent — ¿ya se envió el resumen para esta sala? ──
        if SalaNotificacion.objects.filter(id_sala=sala, tipo=TIPO_RESUMEN).exists():
            self.stdout.write(self.style.WARNING(
                '   ⏭  Resumen ya enviado para esta sala. Saltando.'
            ))
            return {'skipped': 1}

        # ── Calcular clasificación de fase de grupos para esta sala ──
        miembros = list(
            UsuarioSala.objects.filter(id_sala=sala).select_related('id_usuario')
        )
        if not miembros:
            self.stdout.write('   Sin miembros. Saltando.')
            return {'skipped': 1}

        standings = []
        for m in miembros:
            pts = (
                ApuestaFutbol.objects.filter(
                    id_sala=sala,
                    id_usuario=m.id_usuario,
                    id_partido_id__in=group_ids,
                    estado=ApuestaStatus.GANADA,
                ).aggregate(total=Sum('puntos_ganados'))['total']
                or 0
            )
            standings.append({'usuario': m.id_usuario, 'puntos': pts})

        standings.sort(key=lambda x: x['puntos'], reverse=True)

        # Mostrar top-3 en consola
        medals = ['🥇', '🥈', '🥉']
        for i, entry in enumerate(standings[:3]):
            gap_str = ''
            if i > 0 and standings[0]['puntos'] != entry['puntos']:
                gap = standings[0]['puntos'] - entry['puntos']
                gap_str = f' (-{gap} pts)'
            medal = medals[i] if i < 3 else f'{i+1}.'
            self.stdout.write(
                f'   {medal} {entry["usuario"].nombre_usuario}: '
                f'{entry["puntos"]} pts{gap_str}'
            )

        if dry_run:
            self.stdout.write(self.style.WARNING('   [DRY-RUN] Email no enviado.'))
            return {'sent': 0}

        # ── Enviar email vía capa de servicio ──
        try:
            from bets.email_service import send_phase_transition_email
            result = send_phase_transition_email(sala.id_sala)
            sent = result.get('sent', 0)
            failed = result.get('failed', 0)
        except Exception as exc:
            logger.error(f'Error calling send_phase_transition_email for sala {sala.id_sala}: {exc}')
            self.stdout.write(self.style.ERROR(f'   ❌ Error al enviar email: {exc}'))
            return {'failed': 1}

        # ── Marcar como enviado (idempotent lock) ──
        SalaNotificacion.objects.create(
            id_sala=sala,
            tipo=TIPO_RESUMEN,
            mensaje=f'Resumen de fase de grupos enviado ({sent} destinatarios)',
            icono='🏆',
            color='text-yellow-500',
        )

        self.stdout.write(self.style.SUCCESS(
            f'   ✅ Email enviado: {sent} destinatarios, {failed} fallos'
        ))
        return {'sent': sent, 'failed': failed}
