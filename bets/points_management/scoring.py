"""
Lógica de cálculo de puntos para apuestas
"""
from .scoring_rules import get_scoring_rules


def calcular_puntos_futbol(prediccion_local, prediccion_visitante, 
                           goles_local, goles_visitante, reglas_custom=None):
    """
    Calcula los puntos ganados en una apuesta de fútbol
    
    Args:
        prediccion_local: Goles predichos del equipo local
        prediccion_visitante: Goles predichos del equipo visitante
        goles_local: Goles reales del equipo local
        goles_visitante: Goles reales del equipo visitante
        reglas_custom: Reglas personalizadas de puntuación (opcional)
    
    Returns:
        int: Puntos ganados
    """
    # Validar que los resultados no sean None
    if goles_local is None or goles_visitante is None:
        return 0
    
    puntos = 0
    reglas = get_scoring_rules('futbol', reglas_custom)
    
    # 1. Verificar resultado exacto (máxima puntuación)
    if prediccion_local == goles_local and prediccion_visitante == goles_visitante:
        puntos += reglas['resultado_exacto']
        return puntos  # Si acertó exacto, no sumar puntos adicionales
    
    # 2. Calcular diferencia de goles real y predicha
    diferencia_real = goles_local - goles_visitante
    diferencia_predicha = prediccion_local - prediccion_visitante
    
    # 3. Verificar si acertó la diferencia de goles
    if diferencia_real == diferencia_predicha:
        puntos += reglas['diferencia_goles']
    
    # 4. Verificar si acertó el resultado (ganador/empate)
    # Empate
    if diferencia_real == 0 and diferencia_predicha == 0:
        puntos += reglas['acertar_empate']
    # Ganó local
    elif diferencia_real > 0 and diferencia_predicha > 0:
        puntos += reglas['acertar_ganador']
    # Ganó visitante
    elif diferencia_real < 0 and diferencia_predicha < 0:
        puntos += reglas['acertar_ganador']
    
    return puntos


def determinar_estado_apuesta(puntos_ganados):
    """
    Determina el estado de una apuesta según los puntos ganados
    
    Args:
        puntos_ganados: Puntos obtenidos en la apuesta
    
    Returns:
        str: 'ganada' si ganó puntos, 'perdida' si no
    """
    return 'ganada' if puntos_ganados > 0 else 'perdida'
