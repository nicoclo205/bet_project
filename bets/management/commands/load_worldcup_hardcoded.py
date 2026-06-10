"""
Comando Django para cargar la Copa Mundial FIFA 2026 completa.
Fuente: Fixture oficial FIFA (WCup_2026_4.2.6_en.xlsx).

Tiempos: extraídos del Excel en UTC+2, convertidos a UTC para almacenar.
Para ver en hora Colombia (UTC-5): restar 5 horas al UTC almacenado.

Incluye:
  - 16 estadios oficiales
  - 48 selecciones (12 grupos)
  - 72 partidos de fase de grupos con equipos, fechas, estadios reales
  - 32 partidos de rondas eliminatorias con fechas y estadios (equipos TBD)

Uso:
    docker compose exec web python manage.py load_worldcup_hardcoded
    docker compose exec web python manage.py load_worldcup_hardcoded --only-teams
    docker compose exec web python manage.py load_worldcup_hardcoded --only-fixtures
    docker compose exec web python manage.py load_worldcup_hardcoded --reset
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timezone as dt_tz
from bets.models import ApiLiga, ApiEquipo, ApiPartido, ApiPais, ApiVenue, Deporte, PartidoStatus


# ─────────────────────────────────────────────────────────────────────────────
# IDs SINTÉTICOS (para no colisionar con APIs externas)
# ─────────────────────────────────────────────────────────────────────────────
WC_LEAGUE_API_ID = 9001
VENUE_ID_BASE    = 9001   # api_id venues: 9001..9016
TEAM_ID_BASE     = 9001   # api_id equipos: 9001..9049 (9049 = TBD)
FIXTURE_ID_BASE  = 9_000_001

# ─────────────────────────────────────────────────────────────────────────────
# 16 ESTADIOS OFICIALES
# Capacidades aproximadas según información pública FIFA 2026.
# ─────────────────────────────────────────────────────────────────────────────
VENUES = [
    # (venue_no, nombre, ciudad, pais_code, capacidad)
    (1,  "BC Place",                        "Vancouver",              "CA", 54_500),
    (2,  "BMO Field",                        "Toronto",                "CA", 45_736),
    (3,  "MetLife Stadium",                  "New York / New Jersey",  "US", 82_500),
    (4,  "Arrowhead Stadium",                "Kansas City",            "US", 76_416),
    (5,  "AT&T Stadium",                     "Dallas",                 "US", 80_000),
    (6,  "NRG Stadium",                      "Houston",                "US", 72_220),
    (7,  "Mercedes-Benz Stadium",            "Atlanta",                "US", 71_000),
    (8,  "SoFi Stadium",                     "Los Angeles",            "US", 70_240),
    (9,  "Lincoln Financial Field",          "Philadelphia",           "US", 69_176),
    (10, "Lumen Field",                      "Seattle",                "US", 68_740),
    (11, "Levi's Stadium",                   "San Francisco Bay Area", "US", 68_500),
    (12, "Gillette Stadium",                 "Boston",                 "US", 65_878),
    (13, "Hard Rock Stadium",                "Miami",                  "US", 64_767),
    (14, "Estadio Azteca",                   "Mexico City",            "MX", 87_523),
    (15, "Estadio Akron",                    "Guadalajara",            "MX", 49_850),
    (16, "Estadio BBVA",                     "Monterrey",              "MX", 53_500),
]

# ─────────────────────────────────────────────────────────────────────────────
# 48 SELECCIONES  (+ 1 TBD para rondas eliminatorias)
# ─────────────────────────────────────────────────────────────────────────────
TEAMS = [
    # api_id, nombre_db, code_pais, grupo
    (9001, "Mexico",                  "MX",     "A"),
    (9002, "South Africa",            "ZA",     "A"),
    (9003, "South Korea",             "KR",     "A"),
    (9004, "Czech Republic",          "CZ",     "A"),
    (9005, "Canada",                  "CA",     "B"),
    (9006, "Bosnia and Herzegovina",  "BA",     "B"),
    (9007, "Qatar",                   "QA",     "B"),
    (9008, "Switzerland",             "CH",     "B"),
    (9009, "Brazil",                  "BR",     "C"),
    (9010, "Morocco",                 "MA",     "C"),
    (9011, "Haiti",                   "HT",     "C"),
    (9012, "Scotland",                "GB-SCT", "C"),
    (9013, "United States",           "US",     "D"),
    (9014, "Paraguay",                "PY",     "D"),
    (9015, "Australia",               "AU",     "D"),
    (9016, "Turkey",                  "TR",     "D"),
    (9017, "Germany",                 "DE",     "E"),
    (9018, "Curacao",                 "CW",     "E"),
    (9019, "Ivory Coast",             "CI",     "E"),
    (9020, "Ecuador",                 "EC",     "E"),
    (9021, "Netherlands",             "NL",     "F"),
    (9022, "Japan",                   "JP",     "F"),
    (9023, "Sweden",                  "SE",     "F"),
    (9024, "Tunisia",                 "TN",     "F"),
    (9025, "Belgium",                 "BE",     "G"),
    (9026, "Egypt",                   "EG",     "G"),
    (9027, "Iran",                    "IR",     "G"),
    (9028, "New Zealand",             "NZ",     "G"),
    (9029, "Spain",                   "ES",     "H"),
    (9030, "Cape Verde",              "CV",     "H"),
    (9031, "Saudi Arabia",            "SA",     "H"),
    (9032, "Uruguay",                 "UY",     "H"),
    (9033, "France",                  "FR",     "I"),
    (9034, "Senegal",                 "SN",     "I"),
    (9035, "Iraq",                    "IQ",     "I"),
    (9036, "Norway",                  "NO",     "I"),
    (9037, "Argentina",               "AR",     "J"),
    (9038, "Algeria",                 "DZ",     "J"),
    (9039, "Austria",                 "AT",     "J"),
    (9040, "Jordan",                  "JO",     "J"),
    (9041, "Portugal",                "PT",     "K"),
    (9042, "DR Congo",                "CD",     "K"),
    (9043, "Uzbekistan",              "UZ",     "K"),
    (9044, "Colombia",                "CO",     "K"),
    (9045, "England",                 "GB",     "L"),
    (9046, "Croatia",                 "HR",     "L"),
    (9047, "Ghana",                   "GH",     "L"),
    (9048, "Panama",                  "PA",     "L"),
    # Equipo placeholder para rondas eliminatorias (TBD)
    (9049, "TBD",                     "INT",    None),
]

# Nombres del Excel → nombre en BD
EXCEL_NAME_MAP = {
    "Rep. of Korea":  "South Korea",
    "Czech Rep.":     "Czech Republic",
    "Bosnia/Herzeg.": "Bosnia and Herzegovina",
    "USA":            "United States",
    "Curaçao":        "Curacao",
    "IR Iran":        "Iran",
}

# ─────────────────────────────────────────────────────────────────────────────
# 104 PARTIDOS OFICIALES
# Columnas: (match_no, home, away, utc_datetime_str, venue_no, ronda)
# UTC = "my time" del Excel (UTC+2) − 2 horas.
# Hora Colombia (UTC-5) se indica en el comentario al final de cada línea.
# ─────────────────────────────────────────────────────────────────────────────
FIXTURES = [
    # ── FASE DE GRUPOS ──────────────────────────────────────────────────────
    (1,   "Mexico",          "South Africa",          "2026-06-11 19:00", 14, "Group A - Matchday 1"),   # COL 14:00
    (2,   "Rep. of Korea",   "Czech Rep.",             "2026-06-12 02:00", 15, "Group A - Matchday 1"),   # COL 21:00 (Jun 11)
    (3,   "Canada",          "Bosnia/Herzeg.",         "2026-06-12 19:00",  2, "Group B - Matchday 1"),   # COL 14:00
    (4,   "USA",             "Paraguay",               "2026-06-13 01:00",  8, "Group D - Matchday 1"),   # COL 20:00 (Jun 12)
    (5,   "Haiti",           "Scotland",               "2026-06-14 01:00", 12, "Group C - Matchday 1"),   # COL 20:00 (Jun 13)
    (6,   "Australia",       "Turkey",                 "2026-06-14 04:00",  1, "Group D - Matchday 1"),   # COL 23:00 (Jun 13)
    (7,   "Brazil",          "Morocco",                "2026-06-13 22:00",  3, "Group C - Matchday 1"),   # COL 17:00
    (8,   "Qatar",           "Switzerland",            "2026-06-13 19:00", 11, "Group B - Matchday 1"),   # COL 14:00
    (9,   "Ivory Coast",     "Ecuador",                "2026-06-14 23:00",  9, "Group E - Matchday 1"),   # COL 18:00
    (10,  "Germany",         "Curaçao",                "2026-06-14 17:00",  6, "Group E - Matchday 1"),   # COL 12:00
    (11,  "Netherlands",     "Japan",                  "2026-06-14 20:00",  5, "Group F - Matchday 1"),   # COL 15:00
    (12,  "Sweden",          "Tunisia",                "2026-06-15 02:00", 16, "Group F - Matchday 1"),   # COL 21:00 (Jun 14)
    (13,  "Saudi Arabia",    "Uruguay",                "2026-06-15 22:00", 13, "Group H - Matchday 1"),   # COL 17:00
    (14,  "Spain",           "Cape Verde",             "2026-06-15 16:00",  7, "Group H - Matchday 1"),   # COL 11:00
    (15,  "IR Iran",         "New Zealand",            "2026-06-16 01:00",  8, "Group G - Matchday 1"),   # COL 20:00 (Jun 15)
    (16,  "Belgium",         "Egypt",                  "2026-06-15 19:00", 10, "Group G - Matchday 1"),   # COL 14:00
    (17,  "France",          "Senegal",                "2026-06-16 19:00",  3, "Group I - Matchday 1"),   # COL 14:00
    (18,  "Iraq",            "Norway",                 "2026-06-16 22:00", 12, "Group I - Matchday 1"),   # COL 17:00
    (19,  "Argentina",       "Algeria",                "2026-06-17 01:00",  4, "Group J - Matchday 1"),   # COL 20:00 (Jun 16)
    (20,  "Austria",         "Jordan",                 "2026-06-17 04:00", 11, "Group J - Matchday 1"),   # COL 23:00 (Jun 16)
    (21,  "Ghana",           "Panama",                 "2026-06-17 23:00",  2, "Group L - Matchday 1"),   # COL 18:00
    (22,  "England",         "Croatia",                "2026-06-17 20:00",  5, "Group L - Matchday 1"),   # COL 15:00
    (23,  "Portugal",        "DR Congo",               "2026-06-17 17:00",  6, "Group K - Matchday 1"),   # COL 12:00
    (24,  "Uzbekistan",      "Colombia",               "2026-06-18 02:00", 14, "Group K - Matchday 1"),   # COL 21:00 (Jun 17)
    (25,  "Czech Rep.",      "South Africa",           "2026-06-18 16:00",  7, "Group A - Matchday 2"),   # COL 11:00
    (26,  "Switzerland",     "Bosnia/Herzeg.",         "2026-06-18 19:00",  8, "Group B - Matchday 2"),   # COL 14:00
    (27,  "Canada",          "Qatar",                  "2026-06-18 22:00",  1, "Group B - Matchday 2"),   # COL 17:00
    (28,  "Mexico",          "Rep. of Korea",          "2026-06-19 01:00", 15, "Group A - Matchday 2"),   # COL 20:00 (Jun 18)
    (29,  "Brazil",          "Haiti",                  "2026-06-20 00:30",  9, "Group C - Matchday 2"),   # COL 19:30 (Jun 19)
    (30,  "Scotland",        "Morocco",                "2026-06-19 22:00", 12, "Group C - Matchday 2"),   # COL 17:00
    (31,  "Turkey",          "Paraguay",               "2026-06-20 03:00", 11, "Group D - Matchday 2"),   # COL 22:00 (Jun 19)
    (32,  "USA",             "Australia",              "2026-06-19 19:00", 10, "Group D - Matchday 2"),   # COL 14:00
    (33,  "Germany",         "Ivory Coast",            "2026-06-20 20:00",  2, "Group E - Matchday 2"),   # COL 15:00
    (34,  "Ecuador",         "Curaçao",                "2026-06-21 00:00",  4, "Group E - Matchday 2"),   # COL 19:00 (Jun 20)
    (35,  "Netherlands",     "Sweden",                 "2026-06-20 17:00",  6, "Group F - Matchday 2"),   # COL 12:00
    (36,  "Tunisia",         "Japan",                  "2026-06-21 04:00", 16, "Group F - Matchday 2"),   # COL 23:00 (Jun 20)
    (37,  "Uruguay",         "Cape Verde",             "2026-06-21 22:00", 13, "Group H - Matchday 2"),   # COL 17:00
    (38,  "Spain",           "Saudi Arabia",           "2026-06-21 16:00",  7, "Group H - Matchday 2"),   # COL 11:00
    (39,  "Belgium",         "IR Iran",                "2026-06-21 19:00",  8, "Group G - Matchday 2"),   # COL 14:00
    (40,  "New Zealand",     "Egypt",                  "2026-06-22 01:00",  1, "Group G - Matchday 2"),   # COL 20:00 (Jun 21)
    (41,  "Norway",          "Senegal",                "2026-06-23 00:00",  3, "Group I - Matchday 2"),   # COL 19:00 (Jun 22)
    (42,  "France",          "Iraq",                   "2026-06-22 21:00",  9, "Group I - Matchday 2"),   # COL 16:00
    (43,  "Argentina",       "Austria",                "2026-06-22 17:00",  5, "Group J - Matchday 2"),   # COL 12:00
    (44,  "Jordan",          "Algeria",                "2026-06-23 03:00", 11, "Group J - Matchday 2"),   # COL 22:00 (Jun 22)
    (45,  "England",         "Ghana",                  "2026-06-23 20:00", 12, "Group L - Matchday 2"),   # COL 15:00
    (46,  "Panama",          "Croatia",                "2026-06-23 23:00",  2, "Group L - Matchday 2"),   # COL 18:00
    (47,  "Portugal",        "Uzbekistan",             "2026-06-23 17:00",  6, "Group K - Matchday 2"),   # COL 12:00
    (48,  "Colombia",        "DR Congo",               "2026-06-24 02:00", 15, "Group K - Matchday 2"),   # COL 21:00 (Jun 23)
    (49,  "Scotland",        "Brazil",                 "2026-06-24 22:00", 13, "Group C - Matchday 3"),   # COL 17:00
    (50,  "Morocco",         "Haiti",                  "2026-06-24 22:00",  7, "Group C - Matchday 3"),   # COL 17:00  (simultáneo)
    (51,  "Switzerland",     "Canada",                 "2026-06-24 19:00",  1, "Group B - Matchday 3"),   # COL 14:00
    (52,  "Bosnia/Herzeg.",  "Qatar",                  "2026-06-24 19:00", 10, "Group B - Matchday 3"),   # COL 14:00  (simultáneo)
    (53,  "Czech Rep.",      "Mexico",                 "2026-06-25 01:00", 14, "Group A - Matchday 3"),   # COL 20:00 (Jun 24)
    (54,  "South Africa",    "Rep. of Korea",          "2026-06-25 01:00", 16, "Group A - Matchday 3"),   # COL 20:00 (Jun 24)  (simultáneo)
    (55,  "Curaçao",         "Ivory Coast",            "2026-06-25 20:00",  9, "Group E - Matchday 3"),   # COL 15:00
    (56,  "Ecuador",         "Germany",                "2026-06-25 20:00",  3, "Group E - Matchday 3"),   # COL 15:00  (simultáneo)
    (57,  "Japan",           "Sweden",                 "2026-06-25 23:00",  5, "Group F - Matchday 3"),   # COL 18:00
    (58,  "Tunisia",         "Netherlands",            "2026-06-25 23:00",  4, "Group F - Matchday 3"),   # COL 18:00  (simultáneo)
    (59,  "Turkey",          "USA",                    "2026-06-26 02:00",  8, "Group D - Matchday 3"),   # COL 21:00 (Jun 25)
    (60,  "Paraguay",        "Australia",              "2026-06-26 02:00", 11, "Group D - Matchday 3"),   # COL 21:00 (Jun 25)  (simultáneo)
    (61,  "Norway",          "France",                 "2026-06-26 19:00", 12, "Group I - Matchday 3"),   # COL 14:00
    (62,  "Senegal",         "Iraq",                   "2026-06-26 19:00",  2, "Group I - Matchday 3"),   # COL 14:00  (simultáneo)
    (63,  "Egypt",           "IR Iran",                "2026-06-27 03:00", 10, "Group G - Matchday 3"),   # COL 22:00 (Jun 26)
    (64,  "New Zealand",     "Belgium",                "2026-06-27 03:00",  1, "Group G - Matchday 3"),   # COL 22:00 (Jun 26)  (simultáneo)
    (65,  "Cape Verde",      "Saudi Arabia",           "2026-06-27 00:00",  6, "Group H - Matchday 3"),   # COL 19:00 (Jun 26)
    (66,  "Uruguay",         "Spain",                  "2026-06-27 00:00", 15, "Group H - Matchday 3"),   # COL 19:00 (Jun 26)  (simultáneo)
    (67,  "Panama",          "England",                "2026-06-27 21:00",  3, "Group L - Matchday 3"),   # COL 16:00
    (68,  "Croatia",         "Ghana",                  "2026-06-27 21:00",  9, "Group L - Matchday 3"),   # COL 16:00  (simultáneo)
    (69,  "Algeria",         "Austria",                "2026-06-28 02:00",  4, "Group J - Matchday 3"),   # COL 21:00 (Jun 27)
    (70,  "Jordan",          "Argentina",              "2026-06-28 02:00",  5, "Group J - Matchday 3"),   # COL 21:00 (Jun 27)  (simultáneo)
    (71,  "Colombia",        "Portugal",               "2026-06-27 23:30", 13, "Group K - Matchday 3"),   # COL 18:30
    (72,  "DR Congo",        "Uzbekistan",             "2026-06-27 23:30",  7, "Group K - Matchday 3"),   # COL 18:30  (simultáneo)
    # ── RONDA DE 32 ─────────────────────────────────────────────────────────
    (73,  "TBD",             "TBD",                    "2026-06-28 19:00",  8, "Round of 32"),             # COL 14:00
    (74,  "TBD",             "TBD",                    "2026-06-29 20:30", 12, "Round of 32"),             # COL 15:30
    (75,  "TBD",             "TBD",                    "2026-06-30 01:00", 16, "Round of 32"),             # COL 20:00 (Jun 29)
    (76,  "TBD",             "TBD",                    "2026-06-29 17:00",  6, "Round of 32"),             # COL 12:00
    (77,  "TBD",             "TBD",                    "2026-06-30 21:00",  3, "Round of 32"),             # COL 16:00
    (78,  "TBD",             "TBD",                    "2026-06-30 17:00",  5, "Round of 32"),             # COL 12:00
    (79,  "TBD",             "TBD",                    "2026-07-01 01:00", 14, "Round of 32"),             # COL 20:00 (Jun 30)
    (80,  "TBD",             "TBD",                    "2026-07-01 16:00",  7, "Round of 32"),             # COL 11:00
    (81,  "TBD",             "TBD",                    "2026-07-02 00:00", 11, "Round of 32"),             # COL 19:00 (Jul 1)
    (82,  "TBD",             "TBD",                    "2026-07-01 20:00", 10, "Round of 32"),             # COL 15:00
    (83,  "TBD",             "TBD",                    "2026-07-02 23:00",  2, "Round of 32"),             # COL 18:00
    (84,  "TBD",             "TBD",                    "2026-07-02 19:00",  8, "Round of 32"),             # COL 14:00
    (85,  "TBD",             "TBD",                    "2026-07-03 03:00",  1, "Round of 32"),             # COL 22:00 (Jul 2)
    (86,  "TBD",             "TBD",                    "2026-07-03 22:00", 13, "Round of 32"),             # COL 17:00
    (87,  "TBD",             "TBD",                    "2026-07-04 01:30",  4, "Round of 32"),             # COL 20:30 (Jul 3)
    (88,  "TBD",             "TBD",                    "2026-07-03 18:00",  5, "Round of 32"),             # COL 13:00
    # ── RONDA DE 16 ─────────────────────────────────────────────────────────
    (89,  "TBD",             "TBD",                    "2026-07-04 21:00",  9, "Round of 16"),             # COL 16:00
    (90,  "TBD",             "TBD",                    "2026-07-04 17:00",  6, "Round of 16"),             # COL 12:00
    (91,  "TBD",             "TBD",                    "2026-07-05 20:00",  3, "Round of 16"),             # COL 15:00
    (92,  "TBD",             "TBD",                    "2026-07-06 00:00", 14, "Round of 16"),             # COL 19:00 (Jul 5)
    (93,  "TBD",             "TBD",                    "2026-07-06 19:00",  5, "Round of 16"),             # COL 14:00
    (94,  "TBD",             "TBD",                    "2026-07-07 00:00", 10, "Round of 16"),             # COL 19:00 (Jul 6)
    (95,  "TBD",             "TBD",                    "2026-07-07 16:00",  7, "Round of 16"),             # COL 11:00
    (96,  "TBD",             "TBD",                    "2026-07-07 20:00",  1, "Round of 16"),             # COL 15:00
    # ── CUARTOS DE FINAL ────────────────────────────────────────────────────
    (97,  "TBD",             "TBD",                    "2026-07-09 20:00", 12, "Quarter-Final"),           # COL 15:00
    (98,  "TBD",             "TBD",                    "2026-07-10 19:00",  8, "Quarter-Final"),           # COL 14:00
    (99,  "TBD",             "TBD",                    "2026-07-11 21:00", 13, "Quarter-Final"),           # COL 16:00
    (100, "TBD",             "TBD",                    "2026-07-12 01:00",  4, "Quarter-Final"),           # COL 20:00 (Jul 11)
    # ── SEMIFINALES ─────────────────────────────────────────────────────────
    (101, "TBD",             "TBD",                    "2026-07-14 19:00",  5, "Semi-Final"),              # COL 14:00
    (102, "TBD",             "TBD",                    "2026-07-15 19:00",  7, "Semi-Final"),              # COL 14:00
    # ── TERCER PUESTO ───────────────────────────────────────────────────────
    (103, "TBD",             "TBD",                    "2026-07-18 21:00", 13, "Third Place"),             # COL 16:00
    # ── FINAL ───────────────────────────────────────────────────────────────
    (104, "TBD",             "TBD",                    "2026-07-19 19:00",  3, "Final"),                   # COL 14:00
]

# Países extra no incluidos en populate_countries.py
EXTRA_COUNTRIES = [
    ("Haiti",        "HT"),
    ("Curacao",      "CW"),
    ("Cape Verde",   "CV"),
    ("Jordan",       "JO"),
    ("DR Congo",     "CD"),
    ("Uzbekistan",   "UZ"),
    ("International","INT"),
]


class Command(BaseCommand):
    help = 'Carga equipos y partidos del Mundial 2026 (fixture oficial FIFA)'

    def add_arguments(self, parser):
        parser.add_argument('--only-teams',    action='store_true')
        parser.add_argument('--only-fixtures', action='store_true')
        parser.add_argument('--reset',         action='store_true',
                            help='Elimina todos los datos del Mundial antes de recargar')

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🌍  COPA MUNDIAL FIFA 2026 — CARGA OFICIAL"))
        self.stdout.write("=" * 80 + "\n")

        self.stats = dict(equipos=0, venues=0, partidos=0, actualizados=0)

        try:
            futbol = Deporte.objects.get(nombre='Fútbol')
        except Deporte.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "❌ Deporte 'Fútbol' no existe. Ejecuta primero load_initial_data."))
            return

        self._ensure_countries()
        liga = self._setup_league(futbol)

        if options['reset']:
            self.stdout.write(self.style.WARNING("🗑️  Eliminando datos anteriores..."))
            ApiPartido.objects.filter(id_liga=liga).delete()
            ApiEquipo.objects.filter(api_id__in=[t[0] for t in TEAMS]).delete()
            ApiVenue.objects.filter(api_id__range=(VENUE_ID_BASE, VENUE_ID_BASE + 20)).delete()
            self.stdout.write("   ✅ Listo\n")

        if not options['only_fixtures']:
            self._load_venues()
            self._load_teams(futbol)

        if not options['only_teams']:
            self._load_fixtures(liga)

        self._summary()

    # ─────────────────────────────────────────────────────────────────────────
    def _ensure_countries(self):
        for nombre, code in EXTRA_COUNTRIES:
            _, created = ApiPais.objects.get_or_create(
                code=code, defaults={'nombre': nombre})
            if created:
                self.stdout.write(f"   🌐 País creado: {nombre}")

    def _setup_league(self, futbol):
        internacional = ApiPais.objects.get(code='INT')
        liga, created = ApiLiga.objects.update_or_create(
            api_id=WC_LEAGUE_API_ID,
            defaults={
                'nombre':           'FIFA World Cup 2026',
                'id_pais':          internacional,
                'id_deporte':       futbol,
                'temporada_actual': '2026',
                'tipo':             'Cup',
                'logo_url':         'https://upload.wikimedia.org/wikipedia/en/thumb/0/04/'
                                    '2026_FIFA_World_Cup_emblem.svg/200px-2026_FIFA_World_Cup_emblem.svg.png',
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f"✅ Liga {'creada' if created else 'encontrada'}: FIFA World Cup 2026\n"))
        return liga

    def _load_venues(self):
        self.stdout.write(self.style.WARNING("🏟️  Cargando 16 estadios...\n"))
        for venue_no, nombre, ciudad, pais_code, capacidad in VENUES:
            try:
                pais = ApiPais.objects.get(code=pais_code)
            except ApiPais.DoesNotExist:
                pais = None
            _, created = ApiVenue.objects.update_or_create(
                api_id=VENUE_ID_BASE + venue_no - 1,
                defaults={
                    'nombre':     nombre,
                    'ciudad':     ciudad,
                    'id_pais':    pais,
                    'capacidad':  capacidad,
                    'superficie': 'grass',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ [{venue_no:02d}] {nombre} — {ciudad}"))
                self.stats['venues'] += 1

    def _load_teams(self, futbol):
        self.stdout.write(self.style.WARNING("\n📋 Cargando 48 selecciones (+TBD)...\n"))
        for api_id, nombre, code, grupo in TEAMS:
            try:
                pais = ApiPais.objects.get(code=code)
            except ApiPais.DoesNotExist:
                pais, _ = ApiPais.objects.get_or_create(
                    code=code, defaults={'nombre': nombre})

            _, created = ApiEquipo.objects.update_or_create(
                api_id=api_id,
                defaults={
                    'nombre':       nombre,
                    'nombre_corto': nombre[:20],
                    'id_pais':      pais,
                    'id_deporte':   futbol,
                    'tipo':         'National',
                    'logo_url':     '',
                }
            )
            if created:
                tag = f"[{grupo}]" if grupo else "[KO]"
                self.stdout.write(self.style.SUCCESS(f"   ✅ {tag} {nombre}"))
                self.stats['equipos'] += 1

    def _load_fixtures(self, liga):
        self.stdout.write(self.style.WARNING("\n⚽ Cargando 104 partidos...\n"))

        # Pre-cargar lookup de equipos y venues
        team_db = {t[1]: ApiEquipo.objects.filter(api_id=t[0]).first() for t in TEAMS}
        # Alias para nombres del Excel que difieren del nombre en BD
        for excel_name, db_name in EXCEL_NAME_MAP.items():
            team_db[excel_name] = team_db.get(db_name)
        tbd = ApiEquipo.objects.filter(api_id=9049).first()
        venue_db = {v[0]: ApiVenue.objects.filter(api_id=VENUE_ID_BASE + v[0] - 1).first()
                    for v in VENUES}

        fixture_id = FIXTURE_ID_BASE
        current_round = None

        for match_no, home_name, away_name, utc_str, venue_no, ronda in FIXTURES:
            # Cabecera de sección
            if ronda != current_round:
                current_round = ronda
                section = ronda.split(" - ")[0] if " - " in ronda else ronda
                self.stdout.write(f"\n   {'─'*60}")
                self.stdout.write(f"   {section}")
                self.stdout.write(f"   {'─'*60}")

            home = team_db.get(home_name, tbd) if home_name != "TBD" else tbd
            away = team_db.get(away_name, tbd) if away_name != "TBD" else tbd

            if not home or not away:
                self.stdout.write(self.style.WARNING(
                    f"   ⚠️  #{match_no} Equipo no encontrado: {home_name} / {away_name}"))
                fixture_id += 1
                continue

            naive = datetime.strptime(utc_str, '%Y-%m-%d %H:%M')
            fecha = timezone.make_aware(naive, dt_tz.utc)
            venue = venue_db.get(venue_no)

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
                    'id_venue':         venue,
                }
            )

            venue_name = venue.nombre if venue else '?'
            if created:
                self.stdout.write(
                    f"   #{match_no:3d} {home.nombre:<22} vs {away.nombre:<22}"
                    f"  {utc_str} UTC  [{venue_name}]"
                )
                self.stats['partidos'] += 1
            else:
                self.stats['actualizados'] += 1

            fixture_id += 1

    def _summary(self):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"🏟️  Estadios cargados:    {self.stats['venues']}")
        self.stdout.write(f"🌍 Selecciones cargadas: {self.stats['equipos']}")
        self.stdout.write(f"⚽ Partidos creados:     {self.stats['partidos']}")
        self.stdout.write(f"🔄 Partidos actualizados:{self.stats['actualizados']}\n")
