"""
Actualiza los cruces eliminatorios del Mundial 2026 en la BD.

Idempotente: se puede ejecutar en cualquier momento, las veces que sea.
Solo escribe equipos cuando son DEFINITIVOS:
  - 1ro/2do de grupo: cuando el grupo completo sus 6 partidos.
  - Mejores terceros: cuando los 12 grupos terminaron (tabla oficial FIFA).
  - Ganador/perdedor de eliminatoria: cuando ese partido esta finalizado.
    Si termino empatado (penales), indica el ganador con --winner.

Uso:
    # Normal (despues de cargar resultados con enter_results)
    python manage.py update_worldcup_bracket

    # Ver que haria sin guardar nada
    python manage.py update_worldcup_bracket --dry-run

    # Partido eliminatorio definido por penales: gano el local del P89
    python manage.py update_worldcup_bracket --winner 89=local

    # Sobrescribir un cruce ya asignado (usar con cuidado si hay apuestas)
    python manage.py update_worldcup_bracket --force
"""

from django.core.management.base import BaseCommand, CommandError

from bets.models import ApiLiga, ApiPartido, ApiEquipo, PartidoStatus
from bets.worldcup_bracket import (
    FIXTURE_ID_BASE, GROUPS, R32_TEMPLATE, KO_TEMPLATE, THIRD_ASSIGN,
)

TBD_API_ID = 9049
MATCHES_PER_GROUP = 6


class Command(BaseCommand):
    help = 'Asigna equipos definitivos a los cruces eliminatorios del Mundial 2026'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Muestra los cambios sin guardarlos')
        parser.add_argument('--force', action='store_true',
                            help='Permite sobrescribir cruces ya asignados')
        parser.add_argument('--no-input', action='store_true', dest='no_input',
                            help='No preguntar nada (para uso automatico)')
        parser.add_argument('--winner', action='append', default=[],
                            metavar='N=local|visitante',
                            help='Ganador por penales de un partido empatado. '
                                 'Repetible. Ej: --winner 89=local')

    # ──────────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        self.dry = options['dry_run']
        self.force = options['force']
        self.no_input = options['no_input']

        # Parsear --winner
        self.penalty_winners = {}
        for spec in options['winner']:
            try:
                n, side = spec.split('=')
                n = int(n)
                side = side.strip().lower()
                if side not in ('local', 'visitante'):
                    raise ValueError
                self.penalty_winners[n] = side
            except ValueError:
                raise CommandError(
                    f"--winner invalido: '{spec}'. Formato: 89=local")

        liga = ApiLiga.objects.filter(api_id=9001).first()
        if liga is None:
            raise CommandError('Liga del Mundial (api_id=9001) no encontrada')

        self.tbd = ApiEquipo.objects.filter(api_id=TBD_API_ID).first()
        partidos = list(
            ApiPartido.objects.filter(id_liga=liga)
            .select_related('equipo_local', 'equipo_visitante')
        )
        self.by_fixture = {p.api_fixture_id: p for p in partidos}

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('🏆  ACTUALIZACION DE CRUCES — MUNDIAL 2026'))
        if self.dry:
            self.stdout.write(self.style.WARNING('   [DRY RUN — no se guarda nada]'))
        self.stdout.write('=' * 70 + '\n')

        # ── 1. Posiciones por grupo (solo partidos finalizados) ─────────
        tables = {g: {} for g in GROUPS}
        finished = {g: 0 for g in GROUPS}
        for p in partidos:
            ronda = p.ronda or ''
            if not ronda.startswith('Group'):
                continue
            letter = ronda[6:7]
            if letter not in tables:
                continue
            for eq in (p.equipo_local, p.equipo_visitante):
                tables[letter].setdefault(eq.id_equipo, {
                    'eq': eq, 'gf': 0, 'gc': 0, 'pts': 0})
            if p.estado != PartidoStatus.FINALIZADO or p.goles_local is None:
                continue
            finished[letter] += 1
            h = tables[letter][p.equipo_local.id_equipo]
            a = tables[letter][p.equipo_visitante.id_equipo]
            gl, gv = p.goles_local, p.goles_visitante
            h['gf'] += gl; h['gc'] += gv
            a['gf'] += gv; a['gc'] += gl
            if gl > gv:
                h['pts'] += 3
            elif gl < gv:
                a['pts'] += 3
            else:
                h['pts'] += 1; a['pts'] += 1

        self.sorted_tables = {}
        for letter, rows in tables.items():
            lst = sorted(rows.values(), key=lambda r: (
                -r['pts'], -(r['gf'] - r['gc']), -r['gf'], r['eq'].nombre))
            self.sorted_tables[letter] = lst
        self.group_complete = {g: finished[g] >= MATCHES_PER_GROUP for g in GROUPS}
        self.all_complete = all(self.group_complete.values())

        done = sum(1 for g in GROUPS if self.group_complete[g])
        self.stdout.write(f'   Grupos completos: {done}/12\n')

        # ── 2. Asignacion de terceros (solo si los 12 terminaron) ───────
        self.third_map = {}
        if self.all_complete:
            thirds = []
            for letter, rows in self.sorted_tables.items():
                if len(rows) >= 3:
                    t = rows[2]
                    thirds.append((letter, t))
            thirds.sort(key=lambda x: (
                -x[1]['pts'], -(x[1]['gf'] - x[1]['gc']), -x[1]['gf'],
                x[1]['eq'].nombre))
            best8 = thirds[:8]
            combo = ''.join(sorted(l for l, _ in best8))
            assign = THIRD_ASSIGN.get(combo)
            if assign:
                third_by_group = {l: t['eq'] for l, t in thirds}
                self.third_map = {slot: third_by_group[grp]
                                  for slot, grp in assign.items()}
                self.stdout.write(self.style.SUCCESS(
                    f'   Mejores 8 terceros (combinacion {combo}) asignados.\n'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'   ⚠️  Combinacion de terceros {combo} no encontrada '
                    'en la tabla FIFA — revisar.\n'))

        # ── 3. Resolver y escribir cruces ────────────────────────────────
        self.changes = 0
        self.pending = []

        for n, (hs, as_) in sorted(R32_TEMPLATE.items()):
            self._apply(n, hs, as_)
        for n, (hs, as_, _r) in sorted(KO_TEMPLATE.items()):
            self._apply(n, hs, as_)

        # ── Resumen ──────────────────────────────────────────────────────
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'   ✅ Asignaciones nuevas: {self.changes}')
        if self.pending:
            self.stdout.write(f'   ⏳ Slots aun no definidos: {len(self.pending)}')
            for s in self.pending[:6]:
                self.stdout.write(f'       - {s}')
            if len(self.pending) > 6:
                self.stdout.write(f'       ... y {len(self.pending) - 6} mas')
        if self.dry and self.changes:
            self.stdout.write(self.style.WARNING(
                '\n   [DRY RUN — ejecuta sin --dry-run para guardar]'))
        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────────
    def _resolve(self, slot, match_no):
        """Devuelve ApiEquipo si el slot es definitivo, si no None."""
        if slot.startswith('3-'):
            return self.third_map.get(slot)
        if slot.startswith('W') or slot.startswith('RU'):
            want_winner = slot.startswith('W')
            src = int(slot[1:]) if want_winner else int(slot[2:])
            p = self.by_fixture.get(FIXTURE_ID_BASE + src)
            if not p or p.estado != PartidoStatus.FINALIZADO or p.goles_local is None:
                return None
            # Equipos del partido fuente deben ser reales
            if p.equipo_local.api_id == TBD_API_ID or p.equipo_visitante.api_id == TBD_API_ID:
                return None
            if p.goles_local != p.goles_visitante:
                winner_is_local = p.goles_local > p.goles_visitante
            else:
                side = self.penalty_winners.get(src)
                if side is None and not self.no_input and not self.dry:
                    side = self._ask_penalties(src, p)
                if side is None:
                    self.pending.append(
                        f'P{match_no}: P{src} empato '
                        f'{p.goles_local}-{p.goles_visitante} — indica el '
                        f'ganador con --winner {src}=local|visitante')
                    return None
                winner_is_local = side == 'local'
            if want_winner == winner_is_local:
                return p.equipo_local
            return p.equipo_visitante
        # '1A' / '2B'
        pos, grp = int(slot[0]), slot[1]
        if not self.group_complete.get(grp):
            return None
        rows = self.sorted_tables.get(grp, [])
        return rows[pos - 1]['eq'] if len(rows) >= pos else None

    def _ask_penalties(self, match_no, p):
        local = p.equipo_local.nombre
        visit = p.equipo_visitante.nombre
        try:
            raw = input(
                f'   ⚖️  P{match_no} {local} {p.goles_local}-'
                f'{p.goles_visitante} {visit} fue a penales. '
                f'¿Quien avanzo? [l]ocal={local} / [v]isitante={visit} '
                f'/ Enter=saltar: ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if raw in ('l', 'local'):
            return 'local'
        if raw in ('v', 'visitante'):
            return 'visitante'
        return None

    def _apply(self, match_no, home_slot, away_slot):
        p = self.by_fixture.get(FIXTURE_ID_BASE + match_no)
        if p is None:
            self.stdout.write(self.style.WARNING(
                f'   ⚠️  P{match_no} no existe en la BD'))
            return
        for attr, slot in (('equipo_local', home_slot),
                           ('equipo_visitante', away_slot)):
            current = getattr(p, attr)
            team = self._resolve(slot, match_no)
            if team is None:
                if current.api_id == TBD_API_ID:
                    self.pending.append(f'P{match_no} {slot}')
                continue
            if current.id_equipo == team.id_equipo:
                continue  # ya asignado igual
            if current.api_id != TBD_API_ID and not self.force:
                self.stdout.write(self.style.WARNING(
                    f'   ⚠️  P{match_no} {slot}: ya tiene a '
                    f'{current.nombre}, calculado {team.nombre}. '
                    f'Usa --force para cambiarlo.'))
                continue
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ P{match_no} ({p.ronda}) {slot} → {team.nombre}'))
            if not self.dry:
                setattr(p, attr, team)
                p.save(update_fields=[attr])
            self.changes += 1
