"""
Comando Django para cargar equipos y partidos de la Copa Mundial FIFA 2026
con datos oficiales hardcodeados — sin dependencia de APIs externas.

Fuente: Sorteo oficial FIFA, Washington D.C., diciembre 2025.
        Fixture oficial publicado por FIFA.

Uso:
    python manage.py load_worldcup_hardcoded
    python manage.py load_worldcup_hardcoded --only-teams
    python manage.py load_worldcup_hardcoded --only-fixtures
    python manage.py load_worldcup_hardcoded --reset   # Borra y recarga todo

Nota:
    Solo carga la fase de grupos (72 partidos).
    Los partidos de rondas eliminatorias se cargarán a medida
    que se conozcan los clasificados.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, time
from bets.models import ApiLiga, ApiEquipo, ApiPartido, ApiPais, Deporte, PartidoStatus


# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────

WC_API_ID     = 9001        # ID sintético para el Mundial 2026
FIXTURE_BASE  = 9_000_001   # IDs sintéticos para partidos

# ─────────────────────────────────────────────────────────────
# 48 SELECCIONES CON SU GRUPO Y CÓDIGO DE PAÍS
# ─────────────────────────────────────────────────────────────

TEAMS = [
    # Grupo A
    {"id": 9001, "nombre": "Mexico",                  "code": "MX",     "group": "A"},
    {"id": 9002, "nombre": "South Africa",             "code": "ZA",     "group": "A"},
    {"id": 9003, "nombre": "South Korea",              "code": "KR",     "group": "A"},
    {"id": 9004, "nombre": "Czech Republic",           "code": "CZ",     "group": "A"},
    # Grupo B
    {"id": 9005, "nombre": "Canada",                   "code": "CA",     "group": "B"},
    {"id": 9006, "nombre": "Bosnia and Herzegovina",   "code": "BA",     "group": "B"},
    {"id": 9007, "nombre": "Qatar",                    "code": "QA",     "group": "B"},
    {"id": 9008, "nombre": "Switzerland",              "code": "CH",     "group": "B"},
    # Grupo C
    {"id": 9009, "nombre": "Brazil",                   "code": "BR",     "group": "C"},
    {"id": 9010, "nombre": "Morocco",                  "code": "MA",     "group": "C"},
    {"id": 9011, "nombre": "Haiti",                    "code": "HT",     "group": "C"},
    {"id": 9012, "nombre": "Scotland",                 "code": "GB-SCT", "group": "C"},
    # Grupo D
    {"id": 9013, "nombre": "United States",            "code": "US",     "group": "D"},
    {"id": 9014, "nombre": "Paraguay",                 "code": "PY",     "group": "D"},
    {"id": 9015, "nombre": "Australia",                "code": "AU",     "group": "D"},
    {"id": 9016, "nombre": "Turkey",                   "code": "TR",     "group": "D"},
    # Grupo E
    {"id": 9017, "nombre": "Germany",                  "code": "DE",     "group": "E"},
    {"id": 9018, "nombre": "Curacao",                  "code": "CW",     "group": "E"},
    {"id": 9019, "nombre": "Ivory Coast",              "code": "CI",     "group": "E"},
    {"id": 9020, "nombre": "Ecuador",                  "code": "EC",     "group": "E"},
    # Grupo F
    {"id": 9021, "nombre": "Netherlands",              "code": "NL",     "group": "F"},
    {"id": 9022, "nombre": "Japan",                    "code": "JP",     "group": "F"},
    {"id": 9023, "nombre": "Sweden",                   "code": "SE",     "group": "F"},
    {"id": 9024, "nombre": "Tunisia",                  "code": "TN",     "group": "F"},
    # Grupo G
    {"id": 9025, "nombre": "Belgium",                  "code": "BE",     "group": "G"},
    {"id": 9026, "nombre": "Egypt",                    "code": "EG",     "group": "G"},
    {"id": 9027, "nombre": "Iran",                     "code": "IR",     "group": "G"},
    {"id": 9028, "nombre": "New Zealand",              "code": "NZ",     "group": "G"},
    # Grupo H
    {"id": 9029, "nombre": "Spain",                    "code": "ES",     "group": "H"},
    {"id": 9030, "nombre": "Cape Verde",               "code": "CV",     "group": "H"},
    {"id": 9031, "nombre": "Saudi Arabia",             "code": "SA",     "group": "H"},
    {"id": 9032, "nombre": "Uruguay",                  "code": "UY",     "group": "H"},
    # Grupo I
    {"id": 9033, "nombre": "France",                   "code": "FR",     "group": "I"},
    {"id": 9034, "nombre": "Senegal",                  "code": "SN",     "group": "I"},
    {"id": 9035, "nombre": "Iraq",                     "code": "IQ",     "group": "I"},
    {"id": 9036, "nombre": "Norway",                   "code": "NO",     "group": "I"},
    # Grupo J
    {"id": 9037, "nombre": "Argentina",                "code": "AR",     "group": "J"},
    {"id": 9038, "nombre": "Algeria",                  "code": "DZ",     "group": "J"},
    {"id": 9039, "nombre": "Austria",                  "code": "AT",     "group": "J"},
    {"id": 9040, "nombre": "Jordan",                   "code": "JO",     "group": "J"},
    # Grupo K
    {"id": 9041, "nombre": "Portugal",                 "code": "PT",     "group": "K"},
    {"id": 9042, "nombre": "DR Congo",                 "code": "CD",     "group": "K"},
    {"id": 9043, "nombre": "Uzbekistan",               "code": "UZ",     "group": "K"},
    {"id": 9044, "nombre": "Colombia",                 "code": "CO",     "group": "K"},
    # Grupo L
    {"id": 9045, "nombre": "England",                  "code": "GB",     "group": "L"},
    {"id": 9046, "nombre": "Croatia",                  "code": "HR",     "group": "L"},
    {"id": 9047, "nombre": "Ghana",                    "code": "GH",     "group": "L"},
    {"id": 9048, "nombre": "Panama",                   "code": "PA",     "group": "L"},
]

# ─────────────────────────────────────────────────────────────
# GRUPOS (orden determina los emparejamientos)
# ─────────────────────────────────────────────────────────────

GROUPS = {
    "A": ["Mexico",        "South Africa",           "South Korea",  "Czech Republic"],
    "B": ["Canada",        "Bosnia and Herzegovina", "Qatar",        "Switzerland"],
    "C": ["Brazil",        "Morocco",                "Haiti",        "Scotland"],
    "D": ["United States", "Paraguay",               "Australia",    "Turkey"],
    "E": ["Germany",       "Curacao",                "Ivory Coast",  "Ecuador"],
    "F": ["Netherlands",   "Japan",                  "Sweden",       "Tunisia"],
    "G": ["Belgium",       "Egypt",                  "Iran",         "New Zealand"],
    "H": ["Spain",         "Cape Verde",             "Saudi Arabia", "Uruguay"],
    "I": ["France",        "Senegal",                "Iraq",         "Norway"],
    "J": ["Argentina",     "Algeria",                "Austria",      "Jordan"],
    "K": ["Portugal",      "DR Congo",               "Uzbekistan",   "Colombia"],
    "L": ["England",       "Croatia",                "Ghana",        "Panama"],
}

# Emparejamientos por jornada (índices 0-3 del orden del grupo)
# JR1: pos0 vs pos1, pos2 vs pos3
# JR2: pos0 vs pos2, pos3 vs pos1
# JR3: pos3 vs pos0, pos1 vs pos2  (simultáneos para fair play)
PAIRINGS = {
    1: [(0, 1), (2, 3)],
    2: [(0, 2), (3, 1)],
    3: [(3, 0), (1, 2)],
}

# Fechas por jornada y grupo
DATES = {
    1: {
        "A": "2026-06-11", "B": "2026-06-12", "C": "2026-06-13",
        "D": "2026-06-12", "E": "2026-06-14", "F": "2026-06-14",
        "G": "2026-06-15", "H": "2026-06-15", "I": "2026-06-16",
        "J": "2026-06-16", "K": "2026-06-17", "L": "2026-06-17",
    },
    2: {
        "A": "2026-06-18", "B": "2026-06-18", "C": "2026-06-19",
        "D": "2026-06-19", "E": "2026-06-20", "F": "2026-06-20",
        "G": "2026-06-21", "H": "2026-06-21", "I": "2026-06-22",
        "J": "2026-06-22", "K": "2026-06-23", "L": "2026-06-23",
    },
    3: {
        "A": "2026-06-24", "B": "2026-06-24", "C": "2026-06-24",
        "D": "2026-06-25", "E": "2026-06-25", "F": "2026-06-25",
        "G": "2026-06-26", "H": "2026-06-26", "I": "2026-06-26",
        "J": "2026-06-27", "K": "2026-06-27", "L": "2026-06-27",
    },
}

# Horarios UTC por jornada: [primer partido, segundo partido]
# JR3: ambos simultáneos a las 21:00 UTC (fair play)
TIMES_UTC = {
    1: ["18:00", "22:00"],
    2: ["18:00", "22:00"],
    3: ["21:00", "21:00"],
}

# Países extra que pueden no estar en Populate_countries.py
EXTRA_COUNTRIES = [
    {"nombre": "Haiti",       "code": "HT"},
    {"nombre": "Curacao",     "code": "CW"},
    {"nombre": "Cape Verde",  "code": "CV"},
    {"nombre": "Jordan",      "code": "JO"},
    {"nombre": "DR Congo",    "code": "CD"},
    {"nombre": "Uzbekistan",  "code": "UZ"},
    {"nombre": "International", "code": "INT"},
]


class Command(BaseCommand):
    help = 'Carga equipos y partidos del Mundial 2026 con datos oficiales hardcodeados'

    def add_arguments(self, parser):
        parser.add_argument('--only-teams',    action='store_true', help='Solo cargar equipos')
        parser.add_argument('--only-fixtures', action='store_true', help='Solo cargar partidos')
        parser.add_argument('--reset',         action='store_true',
                            help='Elimina equipos y partidos del Mundial antes de recargar')

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🌍  COPA MUNDIAL FIFA 2026 — CARGA OFICIAL"))
        self.stdout.write("=" * 80 + "\n")

        self.stats = dict(equipos_creados=0, equipos_actualizados=0,
                          partidos_creados=0, partidos_actualizados=0)

        # ── Verificar dependencia Fútbol ──
        try:
            futbol = Deporte.objects.get(nombre='Fútbol')
        except Deporte.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "❌ Deporte 'Fútbol' no existe. Ejecuta primero:\n"
                "   docker compose exec web python manage.py shell -c "
                "\"from bets.models import Deporte; Deporte.objects.get_or_create(nombre='Fútbol')\""
            ))
            return

        # ── Países extra ──
        self._ensure_countries()

        # ── Liga ──
        liga = self._setup_league(futbol)

        # ── Reset opcional ──
        if options['reset']:
            self.stdout.write(self.style.WARNING("🗑️  Eliminando datos anteriores del Mundial..."))
            ApiPartido.objects.filter(id_liga=liga).delete()
            ApiEquipo.objects.filter(api_id__in=[t['id'] for t in TEAMS]).delete()
            self.stdout.write("   ✅ Datos eliminados\n")

        # ── Cargar equipos ──
        if not options['only_fixtures']:
            self.stdout.write(self.style.WARNING("📋 Cargando 48 selecciones...\n"))
            self._load_teams(futbol)

        # ── Cargar partidos ──
        if not options['only_teams']:
            self.stdout.write(self.style.WARNING("\n📋 Cargando 72 partidos de fase de grupos...\n"))
            self._load_fixtures(liga)

        self._summary()

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────

    def _ensure_countries(self):
        """Crea países que puedan no existir en la BD."""
        for c in EXTRA_COUNTRIES:
            _, created = ApiPais.objects.get_or_create(
                code=c['code'], defaults={'nombre': c['nombre']}
            )
            if created:
                self.stdout.write(f"   🌐 País creado: {c['nombre']}")

    def _setup_league(self, futbol):
        internacional = ApiPais.objects.get(code='INT')
        liga, created = ApiLiga.objects.update_or_create(
            api_id=WC_API_ID,
            defaults={
                'nombre':           'FIFA World Cup 2026',
                'id_pais':          internacional,
                'id_deporte':       futbol,
                'temporada_actual': '2026',
                'tipo':             'Cup',
                'logo_url':         'https://upload.wikimedia.org/wikipedia/en/thumb/0/04/2026_FIFA_World_Cup_emblem.svg/200px-2026_FIFA_World_Cup_emblem.svg.png',
            }
        )
        status = "creada" if created else "encontrada"
        self.stdout.write(self.style.SUCCESS(f"✅ Liga {status}: FIFA World Cup 2026\n"))
        return liga

    def _load_teams(self, futbol):
        for t in TEAMS:
            try:
                pais = ApiPais.objects.get(code=t['code'])
            except ApiPais.DoesNotExist:
                # Fallback: crear el país
                pais, _ = ApiPais.objects.get_or_create(
                    code=t['code'], defaults={'nombre': t['nombre']}
                )

            equipo, created = ApiEquipo.objects.update_or_create(
                api_id=t['id'],
                defaults={
                    'nombre':       t['nombre'],
                    'nombre_corto': t['nombre'][:20],
                    'id_pais':      pais,
                    'id_deporte':   futbol,
                    'tipo':         'National',
                    'logo_url':     '',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ [{t['group']}] {t['nombre']}"
                ))
                self.stats['equipos_creados'] += 1
            else:
                self.stats['equipos_actualizados'] += 1

    def _load_fixtures(self, liga):
        fixture_id = FIXTURE_BASE
        team_map = {t['nombre']: t['id'] for t in TEAMS}

        for group, teams in GROUPS.items():
            self.stdout.write(f"   Grupo {group}: {' / '.join(teams)}")

            for matchday, pairs in PAIRINGS.items():
                date_str = DATES[matchday][group]
                times    = TIMES_UTC[matchday]

                for match_idx, (home_idx, away_idx) in enumerate(pairs):
                    home_name = teams[home_idx]
                    away_name = teams[away_idx]

                    # Buscar equipos
                    home = ApiEquipo.objects.filter(api_id=team_map[home_name]).first()
                    away = ApiEquipo.objects.filter(api_id=team_map[away_name]).first()

                    if not home or not away:
                        self.stdout.write(self.style.WARNING(
                            f"      ⚠️ Equipos no encontrados: {home_name} vs {away_name}. "
                            f"Ejecuta primero sin --only-fixtures."
                        ))
                        continue

                    # Construir fecha con hora UTC
                    h, m   = map(int, times[match_idx].split(':'))
                    naive  = datetime.strptime(date_str, '%Y-%m-%d').replace(
                        hour=h, minute=m, second=0, microsecond=0
                    )
                    fecha  = timezone.make_aware(naive, timezone.utc)
                    ronda  = f"Group {group} - Matchday {matchday}"

                    partido, created = ApiPartido.objects.update_or_create(
                        api_fixture_id=fixture_id,
                        defaults={
                            'id_liga':          liga,
                            'equipo_local':     home,
                            'equipo_visitante': away,
                            'fecha':            fecha,
                            'temporada':        '2026',
                            'ronda':            ronda,
                            'estado':           PartidoStatus.PROGRAMADO,
                            'goles_local':      None,
                            'goles_visitante':  None,
                        }
                    )

                    if created:
                        self.stdout.write(
                            f"      ⚽ {date_str} {times[match_idx]} UTC  "
                            f"{home_name} vs {away_name}"
                        )
                        self.stats['partidos_creados'] += 1
                    else:
                        self.stats['partidos_actualizados'] += 1

                    fixture_id += 1

    def _summary(self):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"🌍 Selecciones creadas:      {self.stats['equipos_creados']}")
        self.stdout.write(f"🌍 Selecciones actualizadas: {self.stats['equipos_actualizados']}")
        self.stdout.write(f"⚽ Partidos creados:         {self.stats['partidos_creados']}")
        self.stdout.write(f"⚽ Partidos actualizados:    {self.stats['partidos_actualizados']}\n")
