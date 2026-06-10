"""
Actualiza logo_url de todas las selecciones nacionales usando flagcdn.com.
Las banderas se sirven directamente desde flagcdn.com (CDN gratuito, sin API key).

Uso:
    docker compose exec web python manage.py update_national_logos
    docker compose exec web python manage.py update_national_logos --dry-run   # Solo muestra, no guarda
    docker compose exec web python manage.py update_national_logos --force     # Sobreescribe logos existentes
"""

from django.core.management.base import BaseCommand
from bets.models import ApiEquipo

# ─────────────────────────────────────────────────────────────────────────────
# flagcdn.com usa códigos ISO 3166-1 alpha-2 en minúsculas.
# Para subdivisiones (Escocia, Inglaterra, etc.) usa el código CLDR en minúsculas.
# URL: https://flagcdn.com/w80/{code}.png
# Referencia: https://flagcdn.com/#usage
#
# Excepciones y casos especiales hardcodeados por nombre de equipo:
#   - England  → gb-eng  (Cruz de San Jorge, no Union Jack)
#   - Scotland → gb-sct
#   - Wales    → gb-wls  (por si aparece en futuro)
# ─────────────────────────────────────────────────────────────────────────────

FLAGCDN_BASE = "https://flagcdn.com/w80/{code}.png"

# Forzar código de bandera por nombre de equipo (anula el código del país en BD)
NAME_TO_FLAG_CODE = {
    "England":  "gb-eng",
    "Scotland": "gb-sct",
    "Wales":    "gb-wls",
    "Northern Ireland": "gb-nir",
    "Kosovo":   "xk",       # Kosovo no tiene código ISO oficial; flagcdn usa xk
    "TBD":      None,       # Placeholder, sin bandera
}

# Corrección de códigos de país que vienen mal en la BD
CODE_OVERRIDES = {
    "GB-SCT": "gb-sct",
    "GB-WLS": "gb-wls",
    "GB-NIR": "gb-nir",
    "GB-ENG": "gb-eng",
    "INT":    None,         # Internacional → sin bandera
}


def get_flag_url(equipo) -> str | None:
    """Retorna la URL de bandera para un equipo, o None si no aplica."""

    # 1. Casos especiales por nombre
    if equipo.nombre in NAME_TO_FLAG_CODE:
        code = NAME_TO_FLAG_CODE[equipo.nombre]
        return FLAGCDN_BASE.format(code=code) if code else None

    # 2. Leer código del país asociado
    pais_code = None
    if equipo.id_pais:
        pais_code = equipo.id_pais.code

    if not pais_code:
        return None

    # 3. Aplicar overrides de código
    if pais_code in CODE_OVERRIDES:
        code = CODE_OVERRIDES[pais_code]
        return FLAGCDN_BASE.format(code=code) if code else None

    # 4. Caso general: lowercase del código ISO
    return FLAGCDN_BASE.format(code=pais_code.lower())


class Command(BaseCommand):
    help = 'Actualiza logo_url de selecciones nacionales con banderas de flagcdn.com'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo muestra qué haría, sin guardar en BD')
        parser.add_argument('--force', action='store_true',
                            help='Sobreescribe logos que ya existen en BD')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force   = options['force']

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS(
            "🌍  ACTUALIZACIÓN DE LOGOS — SELECCIONES NACIONALES"
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING("   [DRY RUN — no se guardan cambios]"))
        self.stdout.write("=" * 80 + "\n")

        # Todas las selecciones nacionales (excluir TBD)
        equipos = (
            ApiEquipo.objects
            .select_related('id_pais')
            .filter(tipo='National')
            .exclude(nombre='TBD')
            .order_by('nombre')
        )

        total     = equipos.count()
        updated   = 0
        skipped   = 0
        no_code   = 0

        self.stdout.write(f"Selecciones encontradas en BD: {total}\n")

        for eq in equipos:
            url = get_flag_url(eq)
            pais_code = eq.id_pais.code if eq.id_pais else '—'

            if url is None:
                self.stdout.write(
                    self.style.WARNING(f"   ⚠️  {eq.nombre:<30} (code: {pais_code}) → sin bandera disponible")
                )
                no_code += 1
                continue

            if eq.logo_url and not force:
                self.stdout.write(
                    f"   ⏭️  {eq.nombre:<30} ya tiene logo → omitido (usa --force para sobreescribir)"
                )
                skipped += 1
                continue

            self.stdout.write(
                self.style.SUCCESS(f"   ✅ {eq.nombre:<30} (code: {pais_code}) → {url}")
            )

            if not dry_run:
                eq.logo_url = url
                eq.save(update_fields=['logo_url'])
            updated += 1

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("RESUMEN"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"   Total selecciones:   {total}")
        self.stdout.write(f"   ✅ Actualizadas:     {updated}")
        self.stdout.write(f"   ⏭️  Omitidas:         {skipped}")
        self.stdout.write(f"   ⚠️  Sin código:       {no_code}")
        if dry_run:
            self.stdout.write(self.style.WARNING("\n   [DRY RUN — ejecuta sin --dry-run para guardar]\n"))
        else:
            self.stdout.write(self.style.SUCCESS("\n   ✅ Logos guardados en BD\n"))
