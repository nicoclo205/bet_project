"""
Lógica de cálculo de puntos para apuestas
"""
from .scoring_rules import get_scoring_rules


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
    Calcula los puntos ganados en una apuesta de fútbol.

    Matriz de puntuación (tiers alcanzables):
      - Marcador exacto:                            resultado_exacto       (10 pts)
      - Diferencia de goles correcta*:              acertar_X + diff        (8 pts)
      - Resultado correcto + un equipo exacto:      acertar_X + bp          (6 pts)
      - Resultado correcto únicamente:              acertar_X               (5 pts)
      - Resultado incorrecto + un equipo exacto:    bonus_parcial           (1 pt)
      - Fallo total:                                                         (0 pts)

      * Si la diferencia de goles es correcta, el resultado también lo es por definición.
        Además, misma diferencia + acierto parcial de equipo individual → siempre es
        marcador exacto (10 pts), por lo que el tier de 9 pts es matemáticamente inalcanzable.

    Args:
        prediccion_local: Goles predichos del equipo local
        prediccion_visitante: Goles predichos del equipo visitante
        goles_local: Goles reales del equipo local
        goles_visitante: Goles reales del equipo visitante
        reglas_custom: Reglas personalizadas de puntuación (opcional)

    Returns:
        int: Puntos ganados
    """
    if goles_local is None or goles_visitante is None:
        return 0

    reglas = get_scoring_rules('futbol', reglas_custom)
    bonus_parcial = reglas.get('bonus_parcial', 1)

    # 1. Marcador exacto — máxima puntuación, sin acumulación adicional
    if prediccion_local == goles_local and prediccion_visitante == goles_visitante:
        return reglas['resultado_exacto']

    outcome_real = _get_outcome(goles_local, goles_visitante)
    outcome_pred = _get_outcome(prediccion_local, prediccion_visitante)

    # ¿Acertó al menos el gol de un equipo individual?
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

    # 3. Resultado incorrecto — crédito parcial si acertó el gol de un equipo
    if un_equipo_correcto:
        return bonus_parcial

    return 0


def determinar_estado_apuesta(puntos_ganados):
    """
    Determina el estado de una apuesta según los puntos ganados.

    Returns:
        str: 'ganada' si ganó puntos, 'perdida' si no
    """
    return 'ganada' if puntos_ganados > 0 else 'perdida'
