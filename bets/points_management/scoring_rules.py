"""
Reglas de puntuacion para el sistema de apuestas
"""

# Reglas por defecto para futbol
DEFAULT_FOOTBALL_SCORING = {
    'resultado_exacto': 10,      # Acertar marcador exacto
    'acertar_ganador': 5,        # Acertar quien gana (sin marcador exacto)
    'acertar_empate': 5,         # Acertar que es empate (sin marcador exacto)
    'diferencia_goles': 3,       # Bonus por acertar la diferencia de goles exacta
    'bonus_parcial': 1,          # Bonus por acertar el gol de un equipo individual
}

# Knockout phase bonus points (applied on top of the base score)
KO_BONUS_ET_PREDICTION = 1    # correctly predicted whether extra time would happen (non-draw bets)
KO_BONUS_PENALTY_WINNER = 2   # correctly predicted the penalty shootout winner (draw bets)


def get_scoring_rules(deporte='futbol', reglas_custom=None):
    """
    Obtiene las reglas de puntuacion a usar

    Args:
        deporte: Tipo de deporte ('futbol', 'tenis', etc)
        reglas_custom: Reglas personalizadas (dict) o None

    Returns:
        dict con las reglas de puntuacion a aplicar
    """
    if reglas_custom:
        return reglas_custom

    if deporte == 'futbol':
        return DEFAULT_FOOTBALL_SCORING

    return DEFAULT_FOOTBALL_SCORING
