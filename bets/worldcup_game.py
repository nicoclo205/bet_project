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

# Fecha limite para modificar R16/QF/SF/Final (8 de julio 2026, 12:00 m. COL)
MODIFICATION_DEADLINE = datetime(2026, 7, 8, 17, 0, tzinfo=dt_tz.utc)

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

# -- Puntaje --
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

# Matches modifiable after group stage: R16 through Final
MODIFY_MATCH_NOS = set(R16_NOS + QF_NOS + SF_NOS + [FINAL_NO])


def _is_locked():
    return timezone.now() >= PREDICTION_DEADLINE


def _can_modify():
    """Window to re-pick R16/QF/SF/Final: open until QF starts (July 8)."""
    return timezone.now() < MODIFICATION_DEADLINE


def _get_usuario(request):
    try:
        return Usuario.objects.get(user=request.user)
    except Usuario.DoesNotExist:
        return None


# -- Resolucion del bracket segun la prediccion del usuario --

def resolve_prediction(group_order, thirds, ko_winners, trust_picks=None):
    """Calcula los cruces R32 -> Final a partir de la prediccion.

    Devuelve (rounds, clean_winners):
    - rounds: [{ronda, matches: [{match_no, home, away, winner}]}]
      (nombres de equipo o None si aun no se puede resolver)
    - clean_winners: {match_no(int): nombre} solo picks validos/consistentes

    trust_picks: optional set of match_no ints whose ko_winners picks
    should be accepted without bracket validation (for modification mode).
    """
    trust_picks = trust_picks or set()
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
        if no in trust_picks:
            winners[no] = w if w else None
        else:
            if not (w and h and a and w in (h, a)):
                w = None
            winners[no] = w
        r32.append({"match_no": no, "home": h, "away": a, "winner": winners[no]})
    rounds.append({"ronda": "Round of 32", "matches": r32})

    for ronda in ["Round of 16", "Quarter-Final", "Semi-Final", "Final"]:
        ms = []
        for no, (hs, as_, r) in sorted(KO_TEMPLATE.items()):
            if r != ronda or no == 103:
                continue
            h = winners.get(int(hs[1:])) if hs.startswith("W") else None
            a = winners.get(int(as_[1:])) if as_.startswith("W") else None
            w = ko_winners.get(str(no))
            if no in trust_picks:
                winners[no] = w if w else None
            else:
                if not (w and h and a and w in (h, a)):
                    w = None
                winners[no] = w
            ms.append({"match_no": no, "home": h, "away": a, "winner": winners[no]})
        rounds.append({"ronda": ronda, "matches": ms})

    clean = {no: w for no, w in winners.items() if w}
    return rounds, clean


# -- Resultados reales (leidos de ApiPartido, nunca se escribe) --

def _wc_liga():
    return ApiLiga.objects.filter(api_id=WC_LIGA_API_ID).first()


def actual_results():
    """Calcula resultados reales del torneo para el scoring."""
    liga = _wc_liga()
    out = {"group_pos": {}, "thirds": None, "r16": set(), "qf": set(),
           "sf": set(), "final": set(), "champion": None, "team_info": {},
           "ko_matches": {}}
    if liga is None:
        return out

    partidos = list(
        ApiPartido.objects.filter(id_liga=liga)
        .select_related("equipo_local", "equipo_visitante")
        .order_by("api_fixture_id")
    )

    for p in partidos:
        for eq in (p.equipo_local, p.equipo_visitante):
            if eq.api_id != TBD_API_ID and eq.nombre not in out["team_info"]:
                out["team_info"][eq.nombre] = {
                    "id_equipo": eq.id_equipo, "logo": eq.logo_url,
                }

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

    for no in KO_PICK_NOS:
        p = by_no.get(no)
        if not p:
            continue
        h = p.equipo_local.nombre if p.equipo_local.api_id != TBD_API_ID else None
        a = p.equipo_visitante.nombre if p.equipo_visitante.api_id != TBD_API_ID else None
        match_finished = p.estado == PartidoStatus.FINALIZADO and p.goles_local is not None
        winner = None
        if match_finished and h and a:
            if p.goles_local > p.goles_visitante:
                winner = h
            elif p.goles_visitante > p.goles_local:
                winner = a
        out["ko_matches"][no] = {
            "home": h, "away": a, "finished": match_finished, "winner": winner,
        }

    pf = by_no.get(FINAL_NO)
    if (pf and pf.estado == PartidoStatus.FINALIZADO
            and pf.goles_local is not None
            and pf.goles_local != pf.goles_visitante):
        winner = (pf.equipo_local if pf.goles_local > pf.goles_visitante
                  else pf.equipo_visitante)
        if winner.api_id != TBD_API_ID:
            out["champion"] = winner.nombre
    return out


def viable_r16_teams(actual):
    """For each R16 match, return the two actual teams from R32 winners.

    Returns {r16_match_no: [home_team, away_team]} for each R16 where
    both feeder R32 matches have known winners/teams.
    """
    viable = {}
    for r16_no in R16_NOS:
        hs, as_, _ = KO_TEMPLATE[r16_no]
        h_no = int(hs[1:])  # R32 match number
        a_no = int(as_[1:])
        home = None
        away = None
        # Try R32 match winners first
        h_match = actual["ko_matches"].get(h_no)
        a_match = actual["ko_matches"].get(a_no)
        if h_match and h_match.get("winner"):
            home = h_match["winner"]
        if a_match and a_match.get("winner"):
            away = a_match["winner"]
        # Fallback: R16 match data (teams already assigned by FIFA)
        r16_match = actual["ko_matches"].get(r16_no)
        if r16_match:
            home = home or r16_match.get("home")
            away = away or r16_match.get("away")
        if home and away:
            viable[r16_no] = [home, away]
    return viable


def viable_qf_teams(actual):
    """For each QF match, return the two actual teams from R16 winners.

    Returns {qf_match_no: [home_team, away_team]} for each QF where
    both teams are known.
    """
    viable = {}
    for qf_no in QF_NOS:
        hs, as_, _ = KO_TEMPLATE[qf_no]
        h_no = int(hs[1:])
        a_no = int(as_[1:])
        home = None
        away = None
        h_match = actual["ko_matches"].get(h_no)
        a_match = actual["ko_matches"].get(a_no)
        if h_match and h_match.get("winner"):
            home = h_match["winner"]
        if a_match and a_match.get("winner"):
            away = a_match["winner"]
        qf_match = actual["ko_matches"].get(qf_no)
        if qf_match:
            home = home or qf_match.get("home")
            away = away or qf_match.get("away")
        if home and away:
            viable[qf_no] = [home, away]
    return viable


def score_prediction(pred, actual):
    """Puntos de una prediccion contra los resultados reales."""
    pts_groups = pts_thirds = pts_ko = 0
    exact = 0

    trust = MODIFY_MATCH_NOS if pred.completed else None
    rounds, winners = resolve_prediction(
        pred.group_order, pred.thirds, pred.ko_winners, trust_picks=trust)

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


def detailed_score(pred, actual):
    """Granular per-group / per-third / per-ko-match scoring for summary."""
    trust = MODIFY_MATCH_NOS if pred.completed else None
    _, winners = resolve_prediction(
        pred.group_order, pred.thirds, pred.ko_winners, trust_picks=trust)

    group_detail = {}
    pts_groups_total = 0

    for g in sorted(GROUPS):
        pred_order = (pred.group_order or {}).get(g)
        if not (isinstance(pred_order, list) and len(pred_order) == 4):
            continue

        actual_order = actual["group_pos"].get(g)
        gd = {"positions": [], "subtotal": 0, "resolved": actual_order is not None}

        if actual_order:
            top2 = set(actual_order[:2])
            for i in range(4):
                team = pred_order[i]
                pts = 0
                st = "pending"
                if i < 2:
                    if team == actual_order[i]:
                        pts = PTS_GROUP_EXACT
                        st = "exact"
                    elif team in top2:
                        pts = PTS_GROUP_QUALIFY
                        st = "qualify"
                    else:
                        st = "miss"
                else:
                    st = "n/a"
                gd["positions"].append({"team": team, "pos": i + 1,
                                        "pts": pts, "status": st})
                gd["subtotal"] += pts
        else:
            for i in range(4):
                gd["positions"].append({"team": pred_order[i], "pos": i + 1,
                                        "pts": 0, "status": "pending"})

        pts_groups_total += gd["subtotal"]
        group_detail[g] = gd

    pred_thirds = pred.thirds or []
    third_detail = []
    pts_thirds_total = 0
    thirds_resolved = actual["thirds"] is not None

    for g in pred_thirds:
        pred_order = (pred.group_order or {}).get(g)
        team = pred_order[2] if pred_order and len(pred_order) > 2 else "?"
        if thirds_resolved:
            correct = g in actual["thirds"]
            pts = PTS_THIRD if correct else 0
        else:
            correct = None
            pts = 0
        pts_thirds_total += pts
        third_detail.append({"group": g, "team": team, "correct": correct,
                             "pts": pts})

    ko_stages = [
        ("Round of 32", R32_NOS, actual["r16"], PTS_TO_R16),
        ("Round of 16", R16_NOS, actual["qf"], PTS_TO_QF),
        ("Quarter-Final", QF_NOS, actual["sf"], PTS_TO_SF),
        ("Semi-Final", SF_NOS, actual["final"], PTS_TO_FINAL),
        ("Final", [FINAL_NO], None, PTS_CHAMPION),
    ]
    ko_detail = {}
    pts_ko_total = 0

    for ronda, nos, advanced, pts_val in ko_stages:
        for no in nos:
            pick = winners.get(no)
            if not pick:
                ko_detail[no] = {"pick": None, "pts": 0, "status": "no_pick",
                                 "ronda": ronda}
                continue

            real_match = actual["ko_matches"].get(no)

            if ronda == "Final":
                if actual["champion"]:
                    if pick == actual["champion"]:
                        ko_detail[no] = {"pick": pick, "pts": PTS_CHAMPION,
                                         "status": "correct", "ronda": ronda}
                        pts_ko_total += PTS_CHAMPION
                    else:
                        ko_detail[no] = {"pick": pick, "pts": 0,
                                         "status": "miss", "ronda": ronda}
                else:
                    ko_detail[no] = {"pick": pick, "pts": 0,
                                     "status": "pending", "ronda": ronda}
                continue

            if advanced and pick in advanced:
                ko_detail[no] = {"pick": pick, "pts": pts_val,
                                 "status": "correct", "ronda": ronda}
                pts_ko_total += pts_val
            elif real_match and real_match["finished"]:
                ko_detail[no] = {"pick": pick, "pts": 0,
                                 "status": "miss", "ronda": ronda}
            elif real_match and (real_match["home"] or real_match["away"]):
                ko_detail[no] = {"pick": pick, "pts": 0,
                                 "status": "pending", "ronda": ronda}
            else:
                ko_detail[no] = {"pick": pick, "pts": 0,
                                 "status": "pending", "ronda": ronda}

    return {
        "group_detail": group_detail,
        "third_detail": third_detail,
        "thirds_resolved": thirds_resolved,
        "ko_detail": {str(k): v for k, v in ko_detail.items()},
        "totals": {
            "groups": pts_groups_total,
            "thirds": pts_thirds_total,
            "knockout": pts_ko_total,
            "total": pts_groups_total + pts_thirds_total + pts_ko_total,
        },
    }


# -- Serializacion del estado --

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

    trust = MODIFY_MATCH_NOS if pred.completed else None
    rounds, clean = resolve_prediction(group_order, thirds, pred.ko_winners,
                                       trust_picks=trust)

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

    actual = actual_results()
    score_detail = detailed_score(pred, actual)

    can_modify = _can_modify() and pred.completed
    viable_r16 = viable_r16_teams(actual) if can_modify else {}
    viable_qf_data = viable_qf_teams(actual) if can_modify else {}

    return {
        "deadline": PREDICTION_DEADLINE.isoformat(),
        "locked": _is_locked(),
        "can_modify": can_modify,
        "modification_deadline": MODIFICATION_DEADLINE.isoformat(),
        "viable_r16": viable_r16,
        "viable_qf": viable_qf_data,
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
        "score_detail": score_detail,
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


# -- Endpoints --

@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def game_state(request):
    usuario = _get_usuario(request)
    if usuario is None:
        return Response({"error": "Perfil de usuario no encontrado"},
                        status=status.HTTP_404_NOT_FOUND)

    pred, _ = WorldCupPrediction.objects.get_or_create(usuario=usuario)

    if request.method == "PUT":
        data = request.data or {}
        is_modify = bool(data.get("modify_ko"))

        # ── Modification mode (R16/QF/SF/Final re-picks) ──
        if is_modify:
            if not (_can_modify() and pred.completed):
                return Response(
                    {"error": "La ventana de modificacion no esta activa "
                              "o la prediccion no esta completa."},
                    status=status.HTTP_403_FORBIDDEN)

            incoming = data.get("ko_winners", {})
            if not isinstance(incoming, dict):
                return Response({"error": "ko_winners debe ser un objeto"},
                                status=status.HTTP_400_BAD_REQUEST)

            actual = actual_results()
            viable_r16 = viable_r16_teams(actual)
            viable_qf = viable_qf_teams(actual)
            merged = dict(pred.ko_winners or {})

            for no_str, team in incoming.items():
                try:
                    no_int = int(no_str)
                except (TypeError, ValueError):
                    return Response({"error": f"Partido invalido: {no_str}"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if no_int not in MODIFY_MATCH_NOS:
                    return Response(
                        {"error": f"Solo se pueden modificar octavos, "
                                  f"cuartos, semis y final (partido {no_int})"},
                        status=status.HTTP_400_BAD_REQUEST)

                if team is None:
                    merged.pop(str(no_int), None)
                    continue

                if not isinstance(team, str):
                    return Response({"error": "Ganador invalido"},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Validate R16 picks against actual R32 winners
                if no_int in R16_NOS:
                    v = viable_r16.get(no_int)
                    if not v or team not in v:
                        return Response(
                            {"error": f"Equipo '{team}' no es viable "
                                      f"para el partido {no_int}"},
                            status=status.HTTP_400_BAD_REQUEST)
                # Validate QF picks: actual R16 winners OR user's R16 picks
                elif no_int in QF_NOS:
                    v = viable_qf.get(no_int)
                    if v:
                        if team not in v:
                            return Response(
                                {"error": f"Equipo '{team}' no es viable "
                                          f"para el partido {no_int}"},
                                status=status.HTTP_400_BAD_REQUEST)
                    else:
                        hs, as_, _ = KO_TEMPLATE[no_int]
                        h_pick = merged.get(str(int(hs[1:])))
                        a_pick = merged.get(str(int(as_[1:])))
                        if team not in (h_pick, a_pick):
                            return Response(
                                {"error": f"Equipo '{team}' no es viable "
                                          f"para el partido {no_int}"},
                                status=status.HTTP_400_BAD_REQUEST)
                # Validate SF picks against user's QF winners
                elif no_int in SF_NOS:
                    hs, as_, _ = KO_TEMPLATE[no_int]
                    h_pick = merged.get(str(int(hs[1:])))
                    a_pick = merged.get(str(int(as_[1:])))
                    if team not in (h_pick, a_pick):
                        return Response(
                            {"error": f"Equipo '{team}' no es viable "
                                      f"para la semifinal {no_int}"},
                            status=status.HTTP_400_BAD_REQUEST)
                # Validate Final pick against user's SF winners
                elif no_int == FINAL_NO:
                    hs, as_, _ = KO_TEMPLATE[no_int]
                    h_pick = merged.get(str(int(hs[1:])))
                    a_pick = merged.get(str(int(as_[1:])))
                    if team not in (h_pick, a_pick):
                        return Response(
                            {"error": f"Equipo '{team}' no es viable "
                                      f"para la final"},
                            status=status.HTTP_400_BAD_REQUEST)

                merged[str(no_int)] = team

            # Cascade: if R16 pick changed, invalidate dependent QF/SF/Final
            for qf_no in QF_NOS:
                qf_pick = merged.get(str(qf_no))
                if qf_pick:
                    v = viable_qf.get(qf_no)
                    if v:
                        if qf_pick not in v:
                            merged.pop(str(qf_no), None)
                    else:
                        hs, as_, _ = KO_TEMPLATE[qf_no]
                        h = merged.get(str(int(hs[1:])))
                        a = merged.get(str(int(as_[1:])))
                        if qf_pick not in (h, a):
                            merged.pop(str(qf_no), None)

            for sf_no in SF_NOS:
                sf_pick = merged.get(str(sf_no))
                if sf_pick:
                    hs, as_, _ = KO_TEMPLATE[sf_no]
                    h_team = merged.get(str(int(hs[1:])))
                    a_team = merged.get(str(int(as_[1:])))
                    if sf_pick not in (h_team, a_team):
                        merged.pop(str(sf_no), None)

            f_pick = merged.get(str(FINAL_NO))
            if f_pick:
                hs, as_, _ = KO_TEMPLATE[FINAL_NO]
                h_team = merged.get(str(int(hs[1:])))
                a_team = merged.get(str(int(as_[1:])))
                if f_pick not in (h_team, a_team):
                    merged.pop(str(FINAL_NO), None)

            pred.ko_winners = merged
            pred.save()
            return Response(_state_json(pred, _team_info_map()))

        # ── Regular save (before deadline) ──
        if _is_locked():
            return Response(
                {"error": "Las predicciones cerraron el 18 de julio de "
                          "2026 a las 12:00 (hora Colombia)."},
                status=status.HTTP_403_FORBIDDEN)

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

        trust = MODIFY_MATCH_NOS if pred.completed else None
        _, clean = resolve_prediction(
            pred.group_order, pred.thirds, pred.ko_winners,
            trust_picks=trust)
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
        trust = MODIFY_MATCH_NOS if pred.completed else None
        prog = _progress(pred.group_order or {}, pred.thirds or [],
                         resolve_prediction(pred.group_order, pred.thirds,
                                            pred.ko_winners,
                                            trust_picks=trust)[1])
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
