"""
Django management command: mark_knockout_matches

Sets is_knockout=True on ApiPartido rows whose 'ronda' field matches
any of the known knockout round patterns for the World Cup / Champions
League / general cup competitions.

Usage:
    python manage.py mark_knockout_matches
    python manage.py mark_knockout_matches --liga-id 1
    python manage.py mark_knockout_matches --dry-run
    python manage.py mark_knockout_matches --rondas "Round of 16" "Quarter" "Semi" "Final"
    python manage.py mark_knockout_matches --partido-id 42 --set True
"""

import logging

from django.core.management.base import BaseCommand

from bets.models import ApiPartido

logger = logging.getLogger(__name__)

# Default round keywords that indicate a knockout match (case-insensitive)
DEFAULT_KNOCKOUT_KEYWORDS = [
    'round of 16',
    'round of 32',
    'octavos',
    'quarter',
    'cuartos',
    'semi',
    'final',
]


class Command(BaseCommand):
    help = 'Marks ApiPartido rows as is_knockout=True based on their ronda field'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without saving',
        )
        parser.add_argument(
            '--liga-id',
            type=int,
            default=None,
            help='Restrict to a specific league (id_liga)',
        )
        parser.add_argument(
            '--rondas',
            nargs='+',
            default=None,
            help='Override the default keyword list for ronda matching',
        )
        parser.add_argument(
            '--partido-id',
            type=int,
            default=None,
            help='Set/unset a single match by id_partido (use with --set)',
        )
        parser.add_argument(
            '--set',
            dest='set_value',
            choices=['True', 'False'],
            default='True',
            help='Value to set for is_knockout when using --partido-id',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        liga_id = options['liga_id']
        keywords = options['rondas'] or DEFAULT_KNOCKOUT_KEYWORDS
        partido_id = options['partido_id']
        set_value = options['set_value'] == 'True'

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN — no changes will be saved\n'))

        # Single-match mode
        if partido_id is not None:
            try:
                partido = ApiPartido.objects.get(id_partido=partido_id)
            except ApiPartido.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Partido {partido_id} not found'))
                return
            self.stdout.write(
                f'{"Would set" if dry_run else "Setting"} partido {partido_id} '
                f'({partido}) is_knockout={set_value}'
            )
            if not dry_run:
                partido.is_knockout = set_value
                partido.save(update_fields=['is_knockout'])
            return

        # Bulk keyword mode
        from django.db.models import Q
        q = Q()
        for kw in keywords:
            q |= Q(ronda__icontains=kw)

        qs = ApiPartido.objects.filter(q, is_knockout=False)
        if liga_id:
            qs = qs.filter(id_liga_id=liga_id)

        count = qs.count()
        self.stdout.write(f'Matches to mark as knockout: {count}')

        for p in qs.select_related('equipo_local', 'equipo_visitante')[:20]:
            self.stdout.write(
                f'  • [{p.id_partido}] {p.equipo_local.nombre} vs '
                f'{p.equipo_visitante.nombre} — ronda: {p.ronda}'
            )
        if count > 20:
            self.stdout.write(f'  … and {count - 20} more')

        if not dry_run and count:
            updated = qs.update(is_knockout=True)
            self.stdout.write(self.style.SUCCESS(f'Updated {updated} matches to is_knockout=True'))
        elif dry_run:
            self.stdout.write(self.style.WARNING('Dry run — nothing saved'))
        else:
            self.stdout.write('Nothing to update')
