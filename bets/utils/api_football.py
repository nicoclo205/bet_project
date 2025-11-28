# bets/utils/api_football.py
import os
import requests
from typing import Optional, Dict, Any, List
from .api_counter import can_make_request, increment_count, get_remaining_requests, DAILY_LIMIT

API_KEY = os.environ.get('API_FOOTBALL_KEY')
BASE_URL = 'https://v3.football.api-sports.io'

HEADERS = {
    'x-apisports-key': API_KEY or '',
    'Accept': 'application/json'
}

def _get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Realiza una petición GET a la API de Football con control de límite diario.

    Args:
        endpoint: Ruta del endpoint (ej: '/teams', '/leagues')
        params: Parámetros de la petición

    Returns:
        Dict con la respuesta JSON de la API

    Raises:
        Exception: Si se alcanzó el límite diario de peticiones
    """
    # Verificar límite ANTES de hacer la petición
    can_request, current_count = can_make_request()

    if not can_request:
        raise Exception(
            f"🚫 LÍMITE DIARIO ALCANZADO\n"
            f"   Peticiones usadas: {current_count}/{DAILY_LIMIT}\n"
            f"   No se pueden hacer más peticiones hasta mañana.\n"
            f"   Para aumentar el límite, actualiza tu plan en: https://www.api-football.com/pricing"
        )

    # Advertencias progresivas según peticiones restantes
    remaining = get_remaining_requests()

    if remaining <= 5:
        print(f"🔴 ALERTA CRÍTICA: Solo quedan {remaining} peticiones disponibles!")
    elif remaining <= 10:
        print(f"🟠 ADVERTENCIA: Solo quedan {remaining} peticiones disponibles")
    elif remaining <= 20:
        print(f"🟡 ATENCIÓN: Quedan {remaining} peticiones disponibles")
    else:
        print(f"✅ Petición {current_count + 1}/{DAILY_LIMIT} (quedan {remaining})")

    # Hacer la petición a la API
    url = f"{BASE_URL}{endpoint}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)

    # Incrementar contador DESPUÉS de petición exitosa
    new_count = increment_count()

    # Verificar errores HTTP
    resp.raise_for_status()

    return resp.json()

def get_league(league_id: int, season: Optional[int] = None) -> Dict[str, Any]:
    params = {'id': league_id}
    if season:
        params['season'] = season
    return _get('/leagues', params)

def get_teams_by_league(league_id: int, season: int) -> Dict[str, Any]:
    params = {'league': league_id, 'season': season}
    return _get('/teams', params)

def get_team_by_id(team_id: int) -> Dict[str, Any]:
    params = {'id': team_id}
    return _get('/teams', params)

def get_countries() -> Dict[str, Any]:
    return _get('/countries')

def get_fixtures_by_league(league_id: int, season: int, status: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None, next_: Optional[int] = None) -> Dict[str, Any]:
    params = {'league': league_id, 'season': season}
    if status:
        params['status'] = status
    if from_date:
        params['from'] = from_date
    if to_date:
        params['to'] = to_date
    if next_:
        params['next'] = next_
    return _get('/fixtures', params)

def search_teams_by_country(country: str) -> Dict[str, Any]:
    params = {'country': country}
    return _get('/teams', params)
