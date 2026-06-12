"""
Juego de predicciones del Mundial 2026 ("WC Bracket Challenge").

GET  /api/worldcup/game/state    -> estado/prediccion del usuario autenticado
PUT  /api/worldcup/game/state    -> guarda progreso parcial o total
GET  /api/worldcup/game/ranking  -> ranking global de usuarios

Puntaje (balanceado para permitir remontadas en eliminatorias):
- Grupos: 3 pts por equipo clasificado en posicion exacta (1ro o 2do);
  1 pt si quedo en el top-2 pero en la otra posicion.
- Terceros: 1 pt por cada grupo acertado entre los 8 mejores terceros.
- Eliminatorias (si el equipo elegido avanza, sin importar el rival):
  pasa a R16: 2 | a cuartos: 3 | a semis: 5 | a la final: 7 | campeon: 10.
Desempates: 1) acerto el campeon, 2) mas posiciones exactas de grupo,
3) quien completo su prediccion primero.
"""
from datetime import datetime, timezone as dt_tz

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    ApiLiga, ApiPartido, PartidoStatus, Usuario, WorldCupPrediction,
)
from .worldcup_bracket import (
    FIXTURE_ID_BASE, GROUPS, R32_TEMPLATE, KO_TEMPLATE, THIRD_ASSIGN,
)

# 18 de julio de 2026, 12:00 m. hora Colombia (UTC-5)
PREDICTION_DEADLINE = datetime(2026, 7, 18, 17, 0, tzinfo=dt_tz.utc)

TBD_API_ID = 9049
MATCHES_PER_GROUP = 6
WC_LIGA_API_ID = 9001

# Orden inicial que ve el usuario (ranking FIFA). Nombres tal como en BD.
INITIAL_ORDER = {
    "A": ["Mexico", "Rep. of Korea", "Czech Rep.", "South Africa"],
    "B": ["Switzerland", "Canada", "Bosnia/Herzeg.", "Qatar"],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["USA", "Australia", "Turkey", "Paraguay"],
    "E": ["Germany", "Ecuador", "Ivory Coast", "Curaçao"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "IR Iran", "Egypt", "New Zealand"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde"],
    "I": ["France", "Senegal", "Norway", "Iraq"],
    "J": ["Argentina", "Austria", "Algeria", "Jordan"],
    "K": ["Portugal", "Colombia", "Uzbekistan", "DR Congo"],
    "L": ["England", "Croatia", "Panama", "Ghana"],
}

# ── Puntaje ──────────────────────────────────────────────────────────────
PTS_GROUP_EXACT = 3
PTS_GROUP_QUALIFY = 1
PTS_THIRD = 1
PTS_TO_R16 = 2       # gana su partido de R32
PTS_TO_QF = 3        # gana su partido de R16
PTS_TO_SF = 5        # gana su cuarto de final
PTS_TO_FINAL = 7     # gana su semifinal
PTS_CHAMPION = 10    # gana la final

R32_NOS = sorted(R32_TEMPLATE.keys())                      # 73-88
R16_NOS = list(range(89, 97))
QF_NOS = list(range(97, 101))
SF_NOS = [101, 102]
FINAL_NO = 104
KO_PICK_NOS = R32_NOS + R16_NOS + QF_NOS + SF_NOS + [FINAL_NO]  # sin 103
TOTAL_PICKS = len(KO_PICK_NOS)  # 31


def _is_locked():
    return timezone.now() >= PREDICTION_DEADLINE


def _get_usuario(request):
    try:
        return Usuario.objects.get(user=request.user)
    except Usuario.DoesNotExist:
        return None


# ── Resolucion del bracket segun la prediccion del usuario ───────────────

def resolve_prediction(group_order, thirds, ko_winners):
    """Calcula los cruces R32 -> Final a partir de la prediccion.

    Devuelve (rounds, clean_winners):
    - rounds: [{ronda, matches: [{match_no, home, away, winner}]}]
      (nombres de equipo o None si aun no se puede resolver)
    - clean_winners: {match_no(int): nombre} solo picks validos/consistentes
    """
    complete = {g: o for g, o in (group_order or {}).items()
                if g in GROUPS and isinstance(o, list) and len(o) == 4}
    third_map = {}
    if thirds and len(thirds) == 8:
        combo = "".join(sorted(thirds))
        third_map = THIRD_ASSIGN.get(combo, {})

    def slot_team(slot):
        if slot.startswith("3-"):
            g = third_map.get(slot)
            order = complete.get(g) if g else None
            return order[2] if order else None
        pos, g = int(slot[0]), slot[1]
        order = complete.get(g)
        return order[pos - 1] if order else None

    ko_winners = ko_winners or {}
    winners = {}
    rounds = []

    r32 = []
    for no in R32_NOS:
        hs, as_ = R32_TEMPLATE[no]
        h, a = slot_team(hs), slot_team(as_)
        w = ko_winners.get(str(no))
        if not (w and h and a and w in (h, a)):
            w = None
        winners[no] = w
        r32.append({"match_no": no, "home": h, "away": a, "winner": w})
    rounds.append({"ronda": "Round of 32", "matches": r32})

    for ronda in ["Round of 16", "Quarter-Final", "Semi-Final", "Final"]:
        ms = []
        for no, (hs, as_, r) in sorted(KO_TEMPLATE.items()):
            if r != ronda or no == 103:
                continue
            h = winners.get(int(hs[1:])) if hs.startswith("W") else None
            a = winners.get(int(as_[1:])) if as_.startswith("W") else None
            w = ko_winners.get(str(no))
            if not (w and h and a and w in (h, a)):
                w = None
            winners[no] = w
            ms.append({"match_no": no, "home": h, "away": a, "winner": w})
        rounds.append({"ronda": ronda, "matches": ms})

    clean = {no: w for no, w in winners.items() if w}
    return rounds, clean


# ── Resultados reales (leidos de ApiPartido, nunca se escribe) ───────────

def _wc_liga():
    return ApiLiga.objects.filter(api_id=WC_LIGA_API_ID).first()


def actual_results():
    """Calcula resultados reales del torneo para el scoring.

    Devuelve dict con:
    - group_pos: {letra: [4 nombres en orden final]} solo grupos completos
    - thirds: set de letras de los 8 mejores terceros (si los 12 grupos
      estan completos), si no None
    - r16/qf/sf/final_teams: sets de nombres con presencia real en esa ronda
    - champion: nombre o None
    - team_info: {nombre: {"id_equipo", "logo"}}
    """
    liga = _wc_liga()
    out = {"group_pos": {}, "thirds": None, "r16": set(), "qf": set(),
           "sf": set(), "final": set(), "champion": None, "team_info": {}}
    if liga is None:
        return out

    partidos = list(
        ApiPartido.objects.filter(id_liga=liga)
        .select_related("equipo_local", "equipo_visitante")
        .order_by("api_fixture_id")
    )

    # info de equipos (nombre -> logo) a partir de los partidos de grupos
    for p in partidos:
        for eq in (p.equipo_local, p.equipo_visitante):
            if eq.api_id != TBD_API_ID and eq.nombre not in out["team_info"]:
                out["team_info"][eq.nombre] = {
                    "id_equipo": eq.id_equipo, "logo": eq.logo_url,
                }

    # posiciones reales por grupo
    tables = {g: {} for g in GROUPS}
    finished = {g: 0 for g in GROUPS}
    for p in partidos:
        ronda = p.ronda or ""
        if not ronda.startswith("Group"):
            continue
        letter = ronda[6:7]
        if letter not in tables:
            continue
        for eq in (p.equipo_local, p.equipo_visitante):
            tables[letter].setdefault(eq.nombre, {
                "name": eq.nombre, "pts": 0, "dif": 0, "gf": 0})
        if p.estado != PartidoStatus.FINALIZADO or p.goles_local is None:
            continue
        finished[letter] += 1
        h = tables[letter][p.equipo_local.nombre]
        a = tables[letter][p.equipo_visitante.nombre]
        gl, gv = p.goles_local, p.goles_visitante
        h["gf"] += gl; h["dif"] += gl - gv
        a["gf"] += gv; a["dif"] += gv - gl
        if gl > gv:
            h["pts"] += 3
        elif gl < gv:
            a["pts"] += 3
        else:
            h["pts"] += 1; a["pts"] += 1

    sort_key = lambda r: (-r["pts"], -r["dif"], -r["gf"], r["name"])
    third_rows = []
    for g in GROUPS:
        rows = sorted(tables[g].values(), key=sort_key)
        if finished[g] >= MATCHES_PER_GROUP and len(rows) == 4:
            out["group_pos"][g] = [r["name"] for r in rows]
            row3 = dict(rows[2]); row3["group"] = g
            third_rows.append(row3)

    if len(out["group_pos"]) == len(GROUPS):
        third_rows.sort(key=sort_key)
        out["thirds"] = {r["group"] for r in third_rows[:8]}

    # presencia real en rondas eliminatorias
    by_no = {p.api_fixture_id - FIXTURE_ID_BASE: p for p in partidos
             if p.api_fixture_id >= FIXTURE_ID_BASE + 73}

    def round_teams(nos):
        teams = set()
        for no in nos:
            p = by_no.get(no)
            if not p:
                continue
            for eq in (p.equipo_local, p.equipo_visitante):
                if eq.api_id != TBD_API_ID:
                    teams.add(eq.nombre)
        return teams

    out["r16"] = round_teams(R16_NOS)
    out["qf"] = round_teams(QF_NOS)
    out["sf"] = round_teams(SF_NOS)
    out["final"] = round_teams([FINAL_NO])

    pf = by_no.get(FINAL_NO)
    if (pf and pf.estado == PartidoStatus.FINALIZADO
            and pf.goles_local is not None
            and pf.goles_local != pf.goles_visitante):
        winner = (pf.equipo_local if pf.goles_local > pf.goles_visitante
                  else pf.equipo_visitante)
        if winner.api_id != TBD_API_ID:
            out["champion"] = winner.nombre
    return out


def score_prediction(pred, actual):
    """Puntos de una prediccion contra los resultados reales."""
    pts_groups = pts_thirds = pts_ko = 0
    exact = 0
    rounds, winners = resolve_prediction(
        pred.group_order, pred.thirds, pred.ko_winners)

    for g, actual_order in actual["group_pos"].items():
        pred_order = (pred.group_order or {}).get(g)
        if not (isinstance(pred_order, list) and len(pred_order) == 4):
            continue
        top2 = set(actual_order[:2])
        for i in (0, 1):
            if pred_order[i] == actual_order[i]:
                pts_groups += PTS_GROUP_EXACT
                exact += 1
            elif pred_order[i] in top2:
                pts_groups += PTS_GROUP_QUALIFY

    if actual["thirds"] is not None:
        pts_thirds = PTS_THIRD * len(set(pred.thirds or []) & actual["thirds"])

    stages = [
        (R32_NOS, actual["r16"], PTS_TO_R16),
        (R16_NOS, actual["qf"], PTS_TO_QF),
        (QF_NOS, actual["sf"], PTS_TO_SF),
        (SF_NOS, actual["final"], PTS_TO_FINAL),
    ]
    for nos, advanced, pts in stages:
        for no in nos:
            w = winners.get(no)
            if w and w in advanced:
                pts_ko += pts

    champ_pick = winners.get(FINAL_NO)
    champion_correct = bool(
        actual["champion"] and champ_pick == actual["champion"])
    if champion_correct:
        pts_ko += PTS_CHAMPION

    return {
        "total": pts_groups + pts_thirds + pts_ko,
        "groups": pts_groups,
        "thirds": pts_thirds,
        "knockout": pts_ko,
        "exact_positions": exact,
        "champion_pick": champ_pick,
        "champion_correct": champion_correct,
    }


# ── Serializacion del estado ─────────────────────────────────────────────

def _progress(pred_groups, thirds, clean_winners):
    groups_done = sum(
        1 for g in GROUPS
        if isinstance(pred_groups.get(g), list) and len(pred_groups[g]) == 4)
    return {
        "groups_done": groups_done,
        "groups_total": len(GROUPS),
        "thirds_done": len(thirds or []) == 8,
        "ko_picked": len(clean_winners),
        "ko_total": TOTAL_PICKS,
        "completed": (groups_done == len(GROUPS)
                      and len(thirds or []) == 8
                      and len(clean_winners) == TOTAL_PICKS),
    }


def _state_json(pred, team_info):
    group_order = pred.group_order or {}
    thirds = pred.thirds or []
    rounds, clean = resolve_prediction(group_order, thirds, pred.ko_winners)

    groups = []
    for g in sorted(GROUPS):
        saved = (isinstance(group_order.get(g), list)
                 and len(group_order[g]) == 4)
        groups.append({
            "group": g,
            "order": group_order[g] if saved else INITIAL_ORDER[g],
            "saved": saved,
        })

    third_candidates = [
        {"group": g, "team": group_order[g][2]}
        for g in sorted(GROUPS)
        if isinstance(group_order.get(g), list) and len(group_order[g]) == 4
    ]

    return {
        "deadline": PREDICTION_DEADLINE.isoformat(),
        "locked": _is_locked(),
        "groups": groups,
        "thirds": thirds,
        "third_candidates": third_candidates,
        "knockout": rounds,
        "progress": _progress(group_order, thirds, clean),
        "completed_at": (pred.completed_at.isoformat()
                         if pred.completed_at else None),
        "team_info": team_info,
        "scoring": {
            "group_exact": PTS_GROUP_EXACT,
            "group_qualify": PTS_GROUP_QUALIFY,
            "third": PTS_THIRD,
            "to_r16": PTS_TO_R16,
            "to_qf": PTS_TO_QF,
            "to_sf": PTS_TO_SF,
            "to_final": PTS_TO_FINAL,
            "champion": PTS_CHAMPION,
        },
    }


def _team_info_map():
    liga = _wc_liga()
    info = {}
    if liga is None:
        return info
    partidos = (ApiPartido.objects.filter(id_liga=liga)
                .select_related("equipo_local", "equipo_visitante"))
    for p in partidos:
        for eq in (p.equipo_local, p.equipo_visitante):
            if eq.api_id != TBD_API_ID and eq.nombre not in info:
                info[eq.nombre] = {"logo": eq.logo_url}
    return info


# ── Endpoints ────────────────────────────────────────────────────────────

@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def game_state(request):
    usuario = _get_usuario(request)
    if usuario is None:
        return Response({"error": "Perfil de usuario no encontrado"},
                        status=status.HTTP_404_NOT_FOUND)

    pred, _ = WorldCupPrediction.objects.get_or_create(usuario=usuario)

    if request.method == "PUT":
        if _is_locked():
            return Response(
                {"error": "Las predicciones cerraron el 18 de julio de "
                          "2026 a las 12:00 (hora Colombia)."},
                status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}

        if "group_order" in data:
            incoming = data["group_order"]
            if not isinstance(incoming, dict):
                return Response({"error": "group_order debe ser un objeto"},
                                status=status.HTTP_400_BAD_REQUEST)
            merged = dict(pred.group_order or {})
            for g, order in incoming.items():
                if g not in GROUPS:
                    return Response({"error": f"Grupo invalido: {g}"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if (not isinstance(order, list)
                        or sorted(order) != sorted(GROUPS[g])):
                    return Response(
                        {"error": f"Orden invalido para el grupo {g}"},
                        status=status.HTTP_400_BAD_REQUEST)
                merged[g] = order
            pred.group_order = merged

        if "thirds" in data:
            thirds = data["thirds"]
            if (not isinstance(thirds, list)
                    or len(thirds) > 8
                    or len(set(thirds)) != len(thirds)
                    or any(g not in GROUPS for g in thirds)):
                return Response(
                    {"error": "thirds debe ser una lista de hasta 8 "
                              "letras de grupo sin repetir"},
                    status=status.HTTP_400_BAD_REQUEST)
            pred.thirds = thirds

        if "ko_winners" in data:
            incoming = data["ko_winners"]
            if not isinstance(incoming, dict):
                return Response({"error": "ko_winners debe ser un objeto"},
                                status=status.HTTP_400_BAD_REQUEST)
            merged = dict(pred.ko_winners or {})
            for no, team in incoming.items():
                try:
                    no_int = int(no)
                except (TypeError, ValueError):
                    return Response({"error": f"Partido invalido: {no}"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if no_int not in KO_PICK_NOS:
                    return Response({"error": f"Partido invalido: {no}"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if team is None:
                    merged.pop(str(no_int), None)
                elif isinstance(team, str):
                    merged[str(no_int)] = team
                else:
                    return Response({"error": "Ganador invalido"},
                                    status=status.HTTP_400_BAD_REQUEST)
            pred.ko_winners = merged

        # Limpia picks inconsistentes (si cambio el orden de un grupo o
        # los terceros, los cruces afectados se invalidan en cascada).
        _, clean = resolve_prediction(
            pred.group_order, pred.thirds, pred.ko_winners)
        pred.ko_winners = {str(no): w for no, w in clean.items()}

        prog = _progress(pred.group_order or {}, pred.thirds or [], clean)
        pred.completed = prog["completed"]
        if pred.completed and pred.completed_at is None:
            pred.completed_at = timezone.now()
        if not pred.completed:
            pred.completed_at = None
        pred.save()

    return Response(_state_json(pred, _team_info_map()))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_ranking(request):
    actual = actual_results()
    preds = (WorldCupPrediction.objects
             .select_related("usuario")
             .all())

    rows = []
    for pred in preds:
        prog = _progress(pred.group_order or {}, pred.thirds or [],
                         resolve_prediction(pred.group_order, pred.thirds,
                                            pred.ko_winners)[1])
        score = score_prediction(pred, actual)
        rows.append({
            "id_usuario": pred.usuario.id_usuario,
            "nombre_usuario": pred.usuario.nombre_usuario,
            "foto_perfil": pred.usuario.foto_perfil,
            "completed": prog["completed"],
            "completed_at": (pred.completed_at.isoformat()
                             if pred.completed_at else None),
            **score,
        })

    far_future = "9999-12-31T00:00:00"
    rows.sort(key=lambda r: (
        -r["total"],
        -int(r["champion_correct"]),
        -r["exact_positions"],
        r["completed_at"] or far_future,
        r["nombre_usuario"].lower(),
    ))
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    return Response({
        "ranking": rows,
        "tournament": {
            "groups_complete": len(actual["group_pos"]),
            "thirds_known": actual["thirds"] is not None,
            "champion": actual["champion"],
        },
        "deadline": PREDICTION_DEADLINE.isoformat(),
        "locked": _is_locked(),
    })
