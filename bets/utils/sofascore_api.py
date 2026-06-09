"""
Módulo centralizado para interactuar con la API no oficial de SofaScore.
Reutilizable para todos los deportes: Fútbol, Tenis, Baloncesto, F1.

Características:
- Delays anti-bloqueo aleatorios
- Headers realistas
- Funciones específicas por deporte
- Type hints para mejor desarrollo
- Sistema de logging

Uso:
    from bets.utils.sofascore_api import get_event, get_football_matches_by_date

    # Obtener partidos de fútbol de hoy
    matches = get_football_matches_by_date('2024-12-01')

    # Obtener detalles de un evento específico
    event = get_event(12345678)

Advertencia:
    Esta es una API no oficial de SofaScore. Puede cambiar sin previo aviso.
    Usar con delays adecuados para evitar bloqueos.
"""

import requests
import time
import random
import logging
import urllib3
from typing import Dict, List, Optional, Any
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurar logging
logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTES
# ============================================================================

class SofaScoreSport:
    """IDs de deportes en SofaScore"""
    FOOTBALL = 1      # Fútbol/Soccer
    BASKETBALL = 2    # Baloncesto
    TENNIS = 5        # Tenis
    MOTORSPORT = 19   # F1 y otras carreras


class SofaScoreTournaments:
    """IDs de torneos principales en SofaScore"""
    # Fútbol
    LA_LIGA = {'tournament_id': 8, 'season_2024_25': 61642, 'season_2025_26': 77559}
    PREMIER_LEAGUE = {'tournament_id': 17, 'season_2024_25': 61627}
    SERIE_A = {'tournament_id': 23, 'season_2024_25': 61644}
    BUNDESLIGA = {'tournament_id': 35, 'season_2024_25': 61643}
    LIGUE_1 = {'tournament_id': 34, 'season_2024_25': 61645}
    CHAMPIONS_LEAGUE = {'tournament_id': 7, 'season_2024_25': 61644}

    # Tenis - Torneos principales
    ATP_TOUR = 222
    WTA_TOUR = 223
    AUSTRALIAN_OPEN = 2
    ROLAND_GARROS = 5
    WIMBLEDON = 1
    US_OPEN = 4

    # Baloncesto
    NBA = {'tournament_id': 132}
    EUROLEAGUE = {'tournament_id': 167}

    # F1
    F1_CHAMPIONSHIP = {'tournament_id': 164, 'season_2024': 59225}


BASE_URL = "https://api.sofascore.com/api/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


# ============================================================================
# FUNCIÓN INTERNA DE PETICIONES
# ============================================================================

def _get(endpoint: str, params: Optional[Dict] = None, delay: bool = True,
         min_delay: float = 2.0, max_delay: float = 5.0) -> Dict[str, Any]:
    """
    Realiza una petición GET a la API de SofaScore.

    Args:
        endpoint: Ruta del endpoint (ej: '/event/12345678')
        params: Parámetros de query string (opcional)
        delay: Si True, añade delay aleatorio anti-bloqueo
        min_delay: Delay mínimo en segundos (default: 2.0)
        max_delay: Delay máximo en segundos (default: 5.0)

    Returns:
        Dict con la respuesta JSON de la API

    Raises:
        requests.exceptions.HTTPError: Si la petición falla
        requests.exceptions.Timeout: Si se agota el timeout
        requests.exceptions.RequestException: Otros errores de red

    Example:
        >>> data = _get('/event/12345678')
        >>> print(data['event']['homeTeam']['name'])
        'Real Madrid'
    """
    if delay:
        sleep_time = random.uniform(min_delay, max_delay)
        logger.debug(f"Esperando {sleep_time:.2f}s antes de petición")
        time.sleep(sleep_time)

    url = f"{BASE_URL}{endpoint}"
    logger.info(f"GET {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=15,
            verify=False
        )
        response.raise_for_status()

        data = response.json()
        logger.debug(f"Respuesta exitosa: {len(str(data))} caracteres")
        return data

    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP {e.response.status_code}: {url}")
        raise
    except requests.exceptions.Timeout:
        logger.error(f"Timeout en petición: {url}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en petición: {e}")
        raise


# ============================================================================
# FUNCIONES GENÉRICAS (Todos los deportes)
# ============================================================================

def get_event(event_id: int) -> Dict[str, Any]:
    """
    Obtiene detalles completos de cualquier evento/partido por su ID.
    Funciona para todos los deportes.

    Args:
        event_id: ID único del evento en SofaScore

    Returns:
        Dict con toda la información del evento:
        - event: Datos principales (equipos, score, estado, fecha)
        - homeTeam / awayTeam: Información de equipos
        - homeScore / awayScore: Marcadores
        - status: Estado del evento (notstarted, inprogress, finished, etc.)

    Example:
        >>> event = get_event(12345678)
        >>> print(f"{event['event']['homeTeam']['name']} vs {event['event']['awayTeam']['name']}")
        'Real Madrid vs Barcelona'
        >>> print(f"Estado: {event['event']['status']['type']}")
        'Estado: finished'
    """
    return _get(f"/event/{event_id}")


def get_event_lineups(event_id: int) -> Dict[str, Any]:
    """
    Obtiene las alineaciones de un evento (si están disponibles).

    Args:
        event_id: ID del evento

    Returns:
        Dict con alineaciones de ambos equipos
    """
    return _get(f"/event/{event_id}/lineups")


def get_event_statistics(event_id: int) -> Dict[str, Any]:
    """
    Obtiene estadísticas detalladas de un evento finalizado.

    Args:
        event_id: ID del evento

    Returns:
        Dict con estadísticas (posesión, tiros, corners, etc.)
    """
    return _get(f"/event/{event_id}/statistics")


def get_event_incidents(event_id: int) -> Dict[str, Any]:
    """
    Obtiene incidentes/eventos de un partido (goles, tarjetas, sustituciones).

    Args:
        event_id: ID del evento

    Returns:
        Dict con lista de incidentes ordenados cronológicamente
    """
    return _get(f"/event/{event_id}/incidents")


# ============================================================================
# FÚTBOL - Torneos y Temporadas
# ============================================================================

def get_football_tournament(tournament_id: int) -> Dict[str, Any]:
    """
    Obtiene información general de un torneo de fútbol.

    Args:
        tournament_id: ID del torneo (ej: 8 para La Liga)

    Returns:
        Dict con información del torneo
    """
    return _get(f"/unique-tournament/{tournament_id}")


def get_football_tournament_season(tournament_id: int, season_id: int) -> Dict[str, Any]:
    """
    Obtiene información de una temporada específica de un torneo.

    Args:
        tournament_id: ID del torneo
        season_id: ID de la temporada (ej: 61642 para La Liga 2024/25)

    Returns:
        Dict con información de la temporada, equipos participantes, etc.

    Example:
        >>> season = get_football_tournament_season(8, 61642)
        >>> print(season['season']['name'])
        '24/25'
    """
    return _get(f"/unique-tournament/{tournament_id}/season/{season_id}")


def get_football_tournament_standings(tournament_id: int, season_id: int) -> Dict[str, Any]:
    """
    Obtiene la tabla de posiciones de un torneo.

    Args:
        tournament_id: ID del torneo
        season_id: ID de la temporada

    Returns:
        Dict con tabla de posiciones (equipos, puntos, partidos jugados, etc.)
    """
    return _get(f"/unique-tournament/{tournament_id}/season/{season_id}/standings/total")


def get_football_tournament_events(tournament_id: int, season_id: int,
                                   round_number: Optional[int] = None) -> Dict[str, Any]:
    """
    Obtiene los eventos/partidos de un torneo en una temporada.

    Args:
        tournament_id: ID del torneo
        season_id: ID de la temporada
        round_number: Número de jornada/ronda (opcional)

    Returns:
        Dict con lista de eventos

    Example:
        >>> # Obtener todos los partidos de La Liga 2024/25
        >>> events = get_football_tournament_events(8, 61642)

        >>> # Obtener solo jornada 15
        >>> events = get_football_tournament_events(8, 61642, round_number=15)
    """
    if round_number:
        endpoint = f"/unique-tournament/{tournament_id}/season/{season_id}/events/round/{round_number}"
    else:
        endpoint = f"/unique-tournament/{tournament_id}/season/{season_id}/events/last/0"

    return _get(endpoint)


# ============================================================================
# FÚTBOL - Partidos por Fecha
# ============================================================================

def get_football_matches_by_date(date: str) -> Dict[str, Any]:
    """
    Obtiene todos los partidos de fútbol programados para una fecha específica.

    Args:
        date: Fecha en formato 'YYYY-MM-DD' (ej: '2024-12-01')

    Returns:
        Dict con lista de eventos de fútbol del día

    Example:
        >>> matches = get_football_matches_by_date('2024-12-01')
        >>> for event in matches['events']:
        ...     print(f"{event['homeTeam']['name']} vs {event['awayTeam']['name']}")
    """
    return _get(f"/sport/football/scheduled-events/{date}")


def get_football_live_matches() -> Dict[str, Any]:
    """
    Obtiene todos los partidos de fútbol que están en vivo ahora.

    Returns:
        Dict con lista de eventos en vivo
    """
    return _get("/sport/football/events/live")


# ============================================================================
# FÚTBOL - Equipos
# ============================================================================

def get_football_team(team_id: int) -> Dict[str, Any]:
    """
    Obtiene información detallada de un equipo de fútbol.

    Args:
        team_id: ID del equipo en SofaScore

    Returns:
        Dict con información del equipo (nombre, país, logo, estadio, etc.)

    Example:
        >>> team = get_football_team(2829)
        >>> print(team['team']['name'])
        'Barcelona'
        >>> print(team['team']['country']['name'])
        'Spain'
    """
    return _get(f"/team/{team_id}")


def get_football_team_players(team_id: int) -> Dict[str, Any]:
    """
    Obtiene la plantilla de jugadores de un equipo.

    Args:
        team_id: ID del equipo

    Returns:
        Dict con lista de jugadores del equipo
    """
    return _get(f"/team/{team_id}/players")


def get_football_team_next_matches(team_id: int, page: int = 0) -> Dict[str, Any]:
    """
    Obtiene los próximos partidos de un equipo.

    Args:
        team_id: ID del equipo
        page: Página de resultados (default: 0)

    Returns:
        Dict con próximos partidos del equipo
    """
    return _get(f"/team/{team_id}/events/next/{page}")


# ============================================================================
# TENIS
# ============================================================================

def get_tennis_matches_by_date(date: str) -> Dict[str, Any]:
    """
    Obtiene todos los partidos de tenis programados para una fecha.

    Args:
        date: Fecha en formato 'YYYY-MM-DD'

    Returns:
        Dict con lista de partidos de tenis del día
    """
    return _get(f"/sport/tennis/scheduled-events/{date}")


def get_tennis_live_matches() -> Dict[str, Any]:
    """
    Obtiene partidos de tenis en vivo.

    Returns:
        Dict con lista de partidos en vivo
    """
    return _get("/sport/tennis/events/live")


def get_tennis_player(player_id: int) -> Dict[str, Any]:
    """
    Obtiene información de un jugador de tenis.

    Args:
        player_id: ID del jugador en SofaScore

    Returns:
        Dict con información del jugador
    """
    return _get(f"/player/{player_id}")


def get_tennis_tournament(tournament_id: int, season_id: int) -> Dict[str, Any]:
    """
    Obtiene información de un torneo de tenis.

    Args:
        tournament_id: ID del torneo
        season_id: ID de la temporada/año

    Returns:
        Dict con información del torneo
    """
    return _get(f"/unique-tournament/{tournament_id}/season/{season_id}")


# ============================================================================
# BALONCESTO
# ============================================================================

def get_basketball_matches_by_date(date: str) -> Dict[str, Any]:
    """
    Obtiene todos los partidos de baloncesto programados para una fecha.

    Args:
        date: Fecha en formato 'YYYY-MM-DD'

    Returns:
        Dict con lista de partidos de baloncesto del día
    """
    return _get(f"/sport/basketball/scheduled-events/{date}")


def get_basketball_live_matches() -> Dict[str, Any]:
    """
    Obtiene partidos de baloncesto en vivo.

    Returns:
        Dict con lista de partidos en vivo
    """
    return _get("/sport/basketball/events/live")


def get_basketball_team(team_id: int) -> Dict[str, Any]:
    """
    Obtiene información de un equipo de baloncesto.

    Args:
        team_id: ID del equipo

    Returns:
        Dict con información del equipo
    """
    return _get(f"/team/{team_id}")


def get_basketball_tournament_events(tournament_id: int, season_id: int) -> Dict[str, Any]:
    """
    Obtiene eventos de un torneo de baloncesto.

    Args:
        tournament_id: ID del torneo
        season_id: ID de la temporada

    Returns:
        Dict con lista de eventos
    """
    return _get(f"/unique-tournament/{tournament_id}/season/{season_id}/events/last/0")


# ============================================================================
# FÓRMULA 1 / MOTORSPORT
# ============================================================================

def get_f1_season_events(season_year: int) -> Dict[str, Any]:
    """
    Obtiene todas las carreras de F1 de una temporada.

    Args:
        season_year: Año de la temporada (ej: 2024)

    Returns:
        Dict con lista de carreras de la temporada

    Example:
        >>> races = get_f1_season_events(2024)
        >>> for event in races['events']:
        ...     print(f"{event['tournament']['name']} - {event['status']['type']}")
    """
    # ID 164 es F1 World Championship
    season_id = _get_f1_season_id(season_year)
    return _get(f"/unique-tournament/164/season/{season_id}/events/last/0")


def get_f1_event_results(event_id: int) -> Dict[str, Any]:
    """
    Obtiene resultados detallados de una carrera de F1.

    Args:
        event_id: ID del evento/carrera

    Returns:
        Dict con clasificación final, tiempos, puntos, etc.
    """
    return get_event(event_id)


def _get_f1_season_id(year: int) -> int:
    """
    Mapeo interno de años a IDs de temporada de F1.

    Args:
        year: Año de la temporada

    Returns:
        ID de temporada en SofaScore
    """
    # Mapeo conocido (actualizar según sea necesario)
    seasons = {
        2024: 59225,
        2025: 62000,  # Placeholder - actualizar cuando esté disponible
    }
    return seasons.get(year, 59225)


# ============================================================================
# UTILIDADES
# ============================================================================

def test_connection() -> bool:
    """
    Prueba la conexión con la API de SofaScore.

    Returns:
        True si la conexión es exitosa, False en caso contrario

    Example:
        >>> if test_connection():
        ...     print("API disponible")
        ... else:
        ...     print("API no responde")
    """
    try:
        # Intentar obtener un evento conocido (un partido cualquiera)
        data = get_football_matches_by_date(datetime.now().strftime('%Y-%m-%d'))
        logger.info("✅ Conexión exitosa con SofaScore API")
        return True
    except Exception as e:
        logger.error(f"❌ Error conectando con SofaScore API: {e}")
        return False


def get_status_mapping() -> Dict[str, str]:
    """
    Retorna el mapeo de estados de SofaScore a estados de Django.

    Returns:
        Dict con mapeo de estados
    """
    return {
        'notstarted': 'programado',
        'inprogress': 'en_curso',
        'finished': 'finalizado',
        'canceled': 'cancelado',
        'postponed': 'pospuesto',
        'interrupted': 'suspendido',
        'abandoned': 'suspendido',
        'delayed': 'pospuesto',
    }


# ============================================================================
# FUNCIÓN DE PRUEBA INLINE
# ============================================================================

def run_inline_tests():
    """
    Ejecuta pruebas inline del módulo sin crear archivos adicionales.

    Uso:
        python -c "from bets.utils.sofascore_api import run_inline_tests; run_inline_tests()"
    """
    print("\n" + "="*80)
    print("🧪 PRUEBAS DEL MÓDULO SOFASCORE_API.PY")
    print("="*80 + "\n")

    # Test 1: Conexión básica
    print("Test 1: Verificar conexión con API...")
    try:
        if test_connection():
            print("✅ PASS - Conexión exitosa\n")
        else:
            print("❌ FAIL - No se pudo conectar\n")
            return
    except Exception as e:
        print(f"❌ FAIL - Error: {e}\n")
        return

    # Test 2: Obtener partidos de hoy
    print("Test 2: Obtener partidos de fútbol de hoy...")
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        matches = get_football_matches_by_date(today)

        if 'events' in matches:
            num_matches = len(matches['events'])
            print(f"✅ PASS - Se encontraron {num_matches} partidos")

            if num_matches > 0:
                first_match = matches['events'][0]
                home = first_match.get('homeTeam', {}).get('name', 'N/A')
                away = first_match.get('awayTeam', {}).get('name', 'N/A')
                print(f"   Ejemplo: {home} vs {away}\n")
            else:
                print("   (No hay partidos hoy)\n")
        else:
            print("❌ FAIL - Respuesta sin campo 'events'\n")
    except Exception as e:
        print(f"❌ FAIL - Error: {e}\n")

    # Test 3: Obtener info de La Liga
    print("Test 3: Obtener información de La Liga...")
    try:
        la_liga = get_football_tournament(8)

        if 'uniqueTournament' in la_liga:
            name = la_liga['uniqueTournament'].get('name', 'N/A')
            print(f"✅ PASS - Torneo: {name}\n")
        else:
            print("❌ FAIL - Respuesta sin campo 'uniqueTournament'\n")
    except Exception as e:
        print(f"❌ FAIL - Error: {e}\n")

    # Test 4: Obtener info de un equipo (Real Madrid)
    print("Test 4: Obtener información de Real Madrid...")
    try:
        real_madrid = get_football_team(2829)

        if 'team' in real_madrid:
            name = real_madrid['team'].get('name', 'N/A')
            country = real_madrid['team'].get('country', {}).get('name', 'N/A')
            print(f"✅ PASS - Equipo: {name} ({country})\n")
        else:
            print("❌ FAIL - Respuesta sin campo 'team'\n")
    except Exception as e:
        print(f"❌ FAIL - Error: {e}\n")

    # Test 5: Mapeo de estados
    print("Test 5: Verificar mapeo de estados...")
    try:
        mapping = get_status_mapping()
        if len(mapping) >= 5:
            print(f"✅ PASS - {len(mapping)} estados mapeados")
            print(f"   Ejemplo: 'notstarted' → '{mapping['notstarted']}'\n")
        else:
            print("❌ FAIL - Mapeo incompleto\n")
    except Exception as e:
        print(f"❌ FAIL - Error: {e}\n")

    print("="*80)
    print("✅ PRUEBAS COMPLETADAS")
    print("="*80 + "\n")

    print("💡 Próximos pasos:")
    print("   1. Crear comandos Django que usen estas funciones")
    print("   2. Implementar load_sofascore_laliga.py")
    print("   3. Implementar update_sofascore_football.py")
    print("   4. Configurar cron job para actualización diaria\n")


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    # Configurar logging para ejecución directa
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    run_inline_tests()
