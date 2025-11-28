# bets/utils/api_counter.py
"""
Sistema de conteo de peticiones a API-Football para evitar exceder el límite diario.
Plan gratuito: 100 requests/día
"""
import os
import json
from datetime import date
from pathlib import Path

# Ubicación del archivo de conteo
COUNTER_FILE = Path(__file__).parent.parent / 'api_request_count.json'
DAILY_LIMIT = 100  # Límite del plan gratuito de API-Football


def get_today_count():
    """
    Obtiene el número de peticiones hechas hoy.

    Returns:
        int: Número de peticiones realizadas hoy
    """
    if not COUNTER_FILE.exists():
        return 0

    try:
        with open(COUNTER_FILE, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0

    today = str(date.today())
    return data.get(today, 0)


def increment_count():
    """
    Incrementa el contador de peticiones de hoy.

    Returns:
        int: Nuevo número de peticiones realizadas hoy
    """
    data = {}

    # Leer datos existentes
    if COUNTER_FILE.exists():
        try:
            with open(COUNTER_FILE, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {}

    # Incrementar contador del día actual
    today = str(date.today())
    data[today] = data.get(today, 0) + 1

    # Guardar datos
    try:
        COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COUNTER_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"⚠️ Warning: Could not save API counter: {e}")

    return data[today]


def can_make_request(limit=None):
    """
    Verifica si se puede hacer otra petición sin exceder el límite.

    Args:
        limit (int, optional): Límite personalizado. Por defecto usa DAILY_LIMIT.

    Returns:
        tuple: (bool: puede_hacer_peticion, int: peticiones_actuales)
    """
    if limit is None:
        limit = DAILY_LIMIT

    count = get_today_count()
    return count < limit, count


def get_remaining_requests(limit=None):
    """
    Obtiene el número de peticiones restantes para hoy.

    Args:
        limit (int, optional): Límite personalizado. Por defecto usa DAILY_LIMIT.

    Returns:
        int: Número de peticiones restantes
    """
    if limit is None:
        limit = DAILY_LIMIT

    count = get_today_count()
    remaining = limit - count
    return max(0, remaining)  # No puede ser negativo


def reset_old_counts(days_to_keep=7):
    """
    Limpia conteos de días anteriores para mantener el archivo pequeño.
    Mantiene solo los últimos N días.

    Args:
        days_to_keep (int): Número de días a mantener en el historial
    """
    if not COUNTER_FILE.exists():
        return

    try:
        with open(COUNTER_FILE, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    today = date.today()
    new_data = {}

    for date_str, count in data.items():
        try:
            file_date = date.fromisoformat(date_str)
            days_diff = (today - file_date).days
            if days_diff <= days_to_keep:
                new_data[date_str] = count
        except ValueError:
            # Ignorar fechas con formato inválido
            continue

    try:
        with open(COUNTER_FILE, 'w') as f:
            json.dump(new_data, f, indent=2)
    except IOError as e:
        print(f"⚠️ Warning: Could not clean old API counts: {e}")


def get_stats():
    """
    Obtiene estadísticas de uso de la API.

    Returns:
        dict: Diccionario con estadísticas
    """
    count = get_today_count()
    remaining = get_remaining_requests()

    return {
        'today': str(date.today()),
        'used': count,
        'remaining': remaining,
        'limit': DAILY_LIMIT,
        'percentage_used': round((count / DAILY_LIMIT) * 100, 1) if DAILY_LIMIT > 0 else 0
    }
