"""
Logica de calculo de puntos para apuestas
"""
from .scoring_rules import get_scoring_rules, KO_BONUS_ET_PREDICTION, KO_BONUS_PENALTY_WINNER


def _get_outcome(local, visitante):
    """Returns 'local', 'visitante', or 'empate'."""
    if local > visitante:
        return 'local'
    if visitante > local:
        return 'visitante'
    return 'empate'


def calcular_puntos_futbol(prediccion_local, prediccion_visitante,
                           goles_local, goles_visitante, reglas_custom=None):
    """
    Calcula los puntos ganados en una apuesta de futbol.

    Matriz de puntuacion (tiers alcanzables):
      - Marcador exacto:                            resultado_exacto       (10 pts)
      - Diferencia de goles correcta*:              acertar_X + diff        (8 pts)
      - Resultado correcto + un equipo exacto:      acertar_X + bp          (6 pts)
      - Resultado correcto unicamente:              acertar_X               (5 pts)
      - Resultado incorrecto + un equipo exacto:    bonus_parcial           (1 pt)
      - Fallo total:                                                         (0 pts)

      * Si la diferencia de goles es correcta, el resultado tambien lo es por definicion.
        Ademas, misma diferencia + acierto parcial de equipo individual siempre es
        marcador exacto (10 pts), por lo que el tier de 9 pts es matematicamente inalcanzable.

    Args:
        prediccion_local: Goles predichos del equipo local
        prediccion_visitante: Goles predichos del equipo visitante
        goles_local: Goles reales del equipo local
        goles_visitante: Goles reales del equipo visitante
        reglas_custom: Reglas personalizadas de puntuacion (opcional)

    Returns:
        int: Puntos ganados
    """
    if goles_local is None or goles_visitante is None:
        return 0

    reglas = get_scoring_rules('futbol', reglas_custom)
    bonus_parcial = reglas.get('bonus_parcial', 1)

    # 1. Marcador exacto - maxima puntuacion, sin acumulacion adicional
    if prediccion_local == goles_local and prediccion_visitante == goles_visitante:
        return reglas['resultado_exacto']

    outcome_real = _get_outcome(goles_local, goles_visitante)
    outcome_pred = _get_outcome(prediccion_local, prediccion_visitante)

    # Acerto al menos el gol de un equipo individual?
    un_equipo_correcto = (
        prediccion_local == goles_local or
        prediccion_visitante == goles_visitante
    )

    # 2. Resultado correcto (ganador/empate) pero marcador no exacto
    if outcome_real == outcome_pred:
        base = reglas['acertar_empate'] if outcome_real == 'empate' else reglas['acertar_ganador']

        # Bonus adicional por acertar la diferencia de goles exacta
        if (goles_local - goles_visitante) == (prediccion_local - prediccion_visitante):
            base += reglas['diferencia_goles']

        # Bonus adicional por acertar el gol de un equipo individual
        if un_equipo_correcto:
            base += bonus_parcial

        return base

    # 3. Resultado incorrecto - credito parcial si acerto el gol de un equipo
    if un_equipo_correcto:
        return bonus_parcial

    return 0


def calcular_bonus_ko(apuesta, partido):
    """
    Bonus points for correctly predicting knockout-specific outcomes.
    Applied on top of the base calcular_puntos_futbol score.

    Rules:
      - Non-draw prediction: +1 pt if ET prediction (tiene_tiempo_extra) matches
        partido.resultado_tiene_tiempo_extra.
      - Draw prediction (implies ET + penalties): +2 pts if the actual match went
        to penalties AND apuesta.ganador_ko_id matches partido.ganador_penales_id.

    Args:
        apuesta: ApuestaFutbol instance
        partido: ApiPartido instance (must have is_knockout=True and be finalizado)

    Returns:
        int: bonus points (0, 1, or 2)
    """
    pred_local = apuesta.prediccion_local
    pred_visitante = apuesta.prediccion_visitante
    is_draw_pred = (pred_local == pred_visitante)

    real_et = partido.resultado_tiene_tiempo_extra        # bool | None
    real_penales = partido.resultado_tiene_penales        # bool | None
    real_ganador_penales_id = partido.ganador_penales_id  # int | None

    if is_draw_pred:
        # Draw prediction always implies ET + penalties.
        # Reward correctly picking the penalty winner (+2).
        if (
            real_penales is True
            and apuesta.ganador_ko_id is not None
            and apuesta.ganador_ko_id == real_ganador_penales_id
        ):
            return KO_BONUS_PENALTY_WINNER
    else:
        # Non-draw prediction: reward correctly predicting ET (+1).
        if (
            real_et is not None
            and apuesta.tiene_tiempo_extra is not None
            and apuesta.tiene_tiempo_extra == real_et
        ):
            return KO_BONUS_ET_PREDICTION

    return 0


def determinar_estado_apuesta(puntos_ganados):
    """
    Determina el estado de una apuesta segun los puntos ganados.

    Returns:
        str: 'ganada' si gano puntos, 'perdida' si no
    """
    return 'ganada' if puntos_ganados > 0 else 'perdida'
