"""
Reglas de puntuación para el sistema de apuestas
"""

# Reglas por defecto para fútbol
DEFAULT_FOOTBALL_SCORING = {
    'resultado_exacto': 10,      # Acertar marcador exacto
    'acertar_ganador': 5,         # Acertar quién gana (sin marcador exacto)
    'acertar_empate': 5,          # Acertar que es empate (sin marcador exacto)
    'diferencia_goles': 3,        # Legado: acertar diferencia de goles (no usado desde v2)
    'bonus_parcial': 1,           # Bonus por acertar el gol de un equipo individual
}

def get_scoring_rules(deporte='futbol', reglas_custom=None):
    """
    Obtiene las reglas de puntuación a usar
    
    Args:
        deporte: Tipo de deporte ('futbol', 'tenis', etc)
        reglas_custom: Reglas personalizadas (dict) o None
    
    Returns:
        dict con las reglas de puntuación a aplicar
    """
    if reglas_custom:
        return reglas_custom
    
    if deporte == 'futbol':
        return DEFAULT_FOOTBALL_SCORING
    
    return DEFAULT_FOOTBALL_SCORING