"""
Endpoint del tablero del Mundial 2026: posiciones por grupo y bracket
de eliminatorias con resolucion automatica de cruces.

GET /api/worldcup/board?liga=<id_liga>

Los resultados se cargan a la BD con scripts manuales; este endpoint solo
LEE ApiPartido y calcula todo al vuelo (no escribe nada).

Resolucion de slots del bracket:
- Si el partido eliminatorio ya tiene equipos reales en la BD (no TBD),
  esos equipos mandan (confirmed=True).
- Si no, se proyecta desde las posiciones actuales (confirmed=False):
  '1A'/'2A' -> 1ro/2do del grupo A; '3-ABCDF' -> tercero segun la tabla
  oficial FIFA (THIRD_ASSIGN) una vez se conocen los 8 mejores terceros.
- 'W73' -> ganador del partido 73 (si esta finalizado en BD), 'RU101' ->
  perdedor del partido 101.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import ApiPartido, ApiLiga, PartidoStatus
from .worldcup_bracket import (
    FIXTURE_ID_BASE, GROUPS, R32_TEMPLATE, KO_TEMPLATE, THIRD_ASSIGN,
)

TBD_API_ID = 9049
MATCHES_PER_GROUP = 6


def _team_json(equipo):
    if equipo is None or equipo.api_id == TBD_API_ID:
        return None
    return {
        "id_equipo": equipo.id_equipo,
        "nombre": equipo.nombre,
        "logo": equipo.logo_url,
    }


def _blank_row(equipo):
    return {
        "team": _team_json(equipo),
        "pj": 0, "g": 0, "e": 0, "p": 0,
        "gf": 0, "gc": 0, "dif": 0, "pts": 0,
    }


def _standings_sort_key(row):
    # Criterio FIFA simplificado: Pts, diferencia de gol, goles a favor.
    # (FIFA tambien usa head-to-head, fair play y ranking; se omiten.)
    return (-row["pts"], -row["dif"], -row["gf"], row["team"]["nombre"])


@api_view(["GET"])
@permission_classes([AllowAny])
def worldcup_board(request):
    liga_id = request.query_params.get("liga")
    liga = None
    if liga_id:
        liga = ApiLiga.objects.filter(id_liga=liga_id).first()
    if liga is None:
        liga = ApiLiga.objects.filter(api_id=9001).first()
    if liga is None:
        return Response({"error": "Liga del Mundial no encontrada"},
                        status=status.HTTP_404_NOT_FOUND)

    partidos = list(
        ApiPartido.objects.filter(id_liga=liga)
        .select_related("equipo_local", "equipo_visitante", "id_venue")
        .order_by("api_fixture_id")
    )

    # ── 1. Posiciones por grupo ──────────────────────────────────────────
    # Grupo de cada equipo segun el fixture oficial (por nombre en BD)
    team_group = {}
    for letter, names in GROUPS.items():
        for n in names:
            team_group[n] = letter

    tables = {letter: {} for letter in GROUPS}   # letter -> {id_equipo: row}
    finished_count = {letter: 0 for letter in GROUPS}

    group_matches = [p for p in partidos if (p.ronda or "").startswith("Group")]
    for p in group_matches:
        letter = (p.ronda or "")[6:7]  # "Group A - Matchday 1" -> "A"
        if letter not in tables:
            continue
        for eq in (p.equipo_local, p.equipo_visitante):
            if eq.id_equipo not in tables[letter]:
                tables[letter][eq.id_equipo] = _blank_row(eq)
        if p.estado != PartidoStatus.FINALIZADO or p.goles_local is None:
            continue
        finished_count[letter] += 1
        home = tables[letter][p.equipo_local.id_equipo]
        away = tables[letter][p.equipo_visitante.id_equipo]
        gl, gv = p.goles_local, p.goles_visitante
        home["pj"] += 1; away["pj"] += 1
        home["gf"] += gl; home["gc"] += gv
        away["gf"] += gv; away["gc"] += gl
        if gl > gv:
            home["g"] += 1; home["pts"] += 3; away["p"] += 1
        elif gl < gv:
            away["g"] += 1; away["pts"] += 3; home["p"] += 1
        else:
            home["e"] += 1; away["e"] += 1
            home["pts"] += 1; away["pts"] += 1

    groups_json = []
    sorted_tables = {}    # letter -> [rows ordenadas]
    for letter in sorted(GROUPS.keys()):
        rows = list(tables[letter].values())
        for r in rows:
            r["dif"] = r["gf"] - r["gc"]
        rows.sort(key=_standings_sort_key)
        for i, r in enumerate(rows):
            r["pos"] = i + 1
        sorted_tables[letter] = rows
        groups_json.append({
            "group": letter,
            "complete": finished_count[letter] >= MATCHES_PER_GROUP,
            "played": finished_count[letter],
            "standings": rows,
        })

    all_groups_complete = all(g["complete"] for g in groups_json)
    any_results = any(finished_count[l] > 0 for l in GROUPS)

    # ── 2. Ranking de terceros y asignacion FIFA ─────────────────────────
    thirds = []
    for letter, rows in sorted_tables.items():
        if len(rows) >= 3:
            t = dict(rows[2])
            t["group"] = letter
            thirds.append(t)
    thirds.sort(key=lambda r: (-r["pts"], -r["dif"], -r["gf"],
                               r["team"]["nombre"] if r["team"] else ""))
    best_thirds = thirds[:8]
    third_slot_map = {}   # '3-ABCDF' -> grupo del tercero asignado
    if len(best_thirds) == 8:
        combo = "".join(sorted(t["group"] for t in best_thirds))
        third_slot_map = THIRD_ASSIGN.get(combo, {})

    def resolve_group_slot(slot):
        """'1A' / '2B' / '3-ABCDF' -> (team_json | None)"""
        if slot.startswith("3-"):
            grp = third_slot_map.get(slot)
            if grp and len(sorted_tables.get(grp, [])) >= 3:
                return sorted_tables[grp][2]["team"]
            return None
        pos, grp = int(slot[0]), slot[1]
        rows = sorted_tables.get(grp, [])
        if len(rows) >= pos and any_results:
            return rows[pos - 1]["team"]
        return None

    # ── 3. Bracket de eliminatorias ──────────────────────────────────────
    by_fixture = {p.api_fixture_id: p for p in partidos}

    def db_match(match_no):
        return by_fixture.get(FIXTURE_ID_BASE + match_no)

    resolved = {}  # match_no -> {"home": team|None, "away": team|None, ...}

    def winner_loser(match_no):
        p = db_match(match_no)
        if p and p.estado == PartidoStatus.FINALIZADO and p.goles_local is not None:
            if p.goles_local > p.goles_visitante:
                return _team_json(p.equipo_local), _team_json(p.equipo_visitante)
            if p.goles_visitante > p.goles_local:
                return _team_json(p.equipo_visitante), _team_json(p.equipo_local)
        # Empate en eliminatoria: el ganador (penales) debe definirse
        # actualizando el partido siguiente en la BD via script.
        return None, None

    def resolve_ko_slot(slot):
        if slot.startswith("W"):
            return winner_loser(int(slot[1:]))[0]
        if slot.startswith("RU"):
            return winner_loser(int(slot[2:]))[1]
        return resolve_group_slot(slot)

    def side_json(p, db_team, slot, projected_team):
        confirmed = db_team is not None
        team = db_team if confirmed else projected_team
        return {
            "slot": slot,
            "team": team,
            "confirmed": confirmed,
            "projected": (not confirmed) and team is not None,
        }

    def match_json(match_no, home_slot, away_slot, ronda):
        p = db_match(match_no)
        home_db = _team_json(p.equipo_local) if p else None
        away_db = _team_json(p.equipo_visitante) if p else None
        return {
            "match_no": match_no,
            "ronda": ronda,
            "fecha": p.fecha.isoformat() if p else None,
            "venue": p.id_venue.nombre if p and p.id_venue else None,
            "ciudad": p.id_venue.ciudad if p and p.id_venue else None,
            "estado": p.estado if p else None,
            "goles_local": p.goles_local if p else None,
            "goles_visitante": p.goles_visitante if p else None,
            "id_partido": p.id_partido if p else None,
            "home": side_json(p, home_db, home_slot, resolve_ko_slot(home_slot)),
            "away": side_json(p, away_db, away_slot, resolve_ko_slot(away_slot)),
        }

    knockout = []
    r32 = [match_json(n, h, a, "Round of 32")
           for n, (h, a) in sorted(R32_TEMPLATE.items())]
    knockout.append({"ronda": "Round of 32", "matches": r32})
    for ronda in ["Round of 16", "Quarter-Final", "Semi-Final",
                  "Third Place", "Final"]:
        ms = [match_json(n, h, a, r)
              for n, (h, a, r) in sorted(KO_TEMPLATE.items()) if r == ronda]
        knockout.append({"ronda": ronda, "matches": ms})

    return Response({
        "liga": {"id_liga": liga.id_liga, "nombre": liga.nombre,
                 "logo_url": liga.logo_url},
        "all_groups_complete": all_groups_complete,
        "groups": groups_json,
        "thirds_ranking": thirds,
        "third_assignment_known": bool(third_slot_map),
        "knockout": knockout,
        "nota": ("Posiciones: Pts, DIF, GF (criterio FIFA simplificado). "
                 "Cruces marcados como proyeccion hasta que la BD tenga "
                 "los equipos reales."),
    })
