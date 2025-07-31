import requests
import config
import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

POSITIONS = {
    1: 'Portero',
    2: 'Defensa',
    3: 'Centrocampista',
    4: 'Delantero'
}

def get_market_value_history(player_id, token):
    url = f"{config.URLS['market_value']}/{player_id}/market-value"
    auth = config.BearerAuth(token)
    try:
        response = requests.get(url, auth=auth, headers=config.HEADERS, timeout=5)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        log.warning(f"No se pudo obtener el historial de valor para el jugador {player_id}: {e}")
        return []

def get_all_players_with_clause():
    """
    Obtiene todos los jugadores de la liga que actualmente tienen una cláusula de rescisión.
    """
    token = config.get_bearer_token()
    auth = config.BearerAuth(token)
    all_players_with_clause = []

    try:
        log.info("Iniciando obtención de jugadores con cláusula...")
        leagues_response = requests.get(config.URLS['leagues'], auth=auth, headers=config.HEADERS)
        leagues_response.raise_for_status()
        # LA API DEVUELVE UNA LISTA DIRECTAMENTE
        leagues_list = leagues_response.json()
        
        if not leagues_list:
            log.warning("No se encontraron ligas para este usuario en get_all_players_with_clause.")
            return []

        league_id = leagues_list[0]['id']
        log.info(f"ID de liga encontrado: {league_id}. Obteniendo mercado...")

        market_url = f"{config.URLS['league_market']}/{league_id}/market"
        market_response = requests.get(market_url, auth=auth, headers=config.HEADERS)
        market_response.raise_for_status()
        
        market_data = market_response.json().get('data', {})
        players_on_market = market_data.get('sales', [])
        log.info(f"Encontrados {len(players_on_market)} jugadores en el mercado de fichajes.")

        players_with_clause_count = 0
        for player_data in players_on_market:
            if player_data.get('type') == 'clause':
                players_with_clause_count += 1
                player_info = player_data.get('player', {})
                if not player_info:
                    log.warning(f"Jugador en mercado de cláusulas sin datos de jugador: {player_data}")
                    continue
                
                player_id = player_info.get('id')
                history = get_market_value_history(player_id, token)
                trend = 0
                if len(history) > 1:
                    trend = history[-1]['marketValue'] - history[-2]['marketValue']
                
                end_protection_str = player_data.get('until')
                time_remaining_seconds = 0
                if end_protection_str:
                    end_protection_date = datetime.fromisoformat(end_protection_str.replace('Z', '+00:00'))
                    time_diff = end_protection_date - datetime.now(end_protection_date.tzinfo)
                    time_remaining_seconds = max(0, int(time_diff.total_seconds()))

                all_players_with_clause.append({
                    'id': player_id,
                    'name': player_info.get('nickname', 'N/A'),
                    'team_name': player_info.get('team', {}).get('name', 'N/A'),
                    'position': POSITIONS.get(player_info.get('positionId'), 'N/A'),
                    'position_id': player_info.get('positionId'),
                    'image_url': player_info.get('image', ''),
                    'owner': player_data.get('manager', {}).get('managerName', 'N/A'),
                    'buyout_clause': player_data.get('price'),
                    'market_value': player_info.get('marketValue'),
                    'player_points': player_info.get('points', 0),
                    'market_value_trend': trend,
                    'time_remaining_seconds': time_remaining_seconds
                })
        
        log.info(f"Procesados {players_with_clause_count} jugadores con cláusula.")

    except requests.exceptions.RequestException as e:
        log.error(f"Error de red al obtener jugadores con cláusula: {e}", exc_info=True)
    except (KeyError, IndexError) as e:
        log.error(f"Error de datos al procesar jugadores con cláusula: {e}", exc_info=True)

    return all_players_with_clause

def get_league_ranking():
    """
    Obtiene la clasificación completa de la liga.
    """
    token = config.get_bearer_token()
    auth = config.BearerAuth(token)

    try:
        log.info("Iniciando obtención de ranking de la liga...")
        leagues_response = requests.get(config.URLS['leagues'], auth=auth, headers=config.HEADERS)
        leagues_response.raise_for_status()
        # LA API DEVUELVE UNA LISTA DIRECTAMENTE
        leagues_list = leagues_response.json()
        
        if not leagues_list:
            log.warning("No se encontraron ligas para este usuario en get_league_ranking.")
            return None
        
        league_id = leagues_list[0]['id']
        log.info(f"ID de liga encontrado: {league_id}. Obteniendo ranking...")

        ranking_url = f"{config.URLS['league_ranking']}/{league_id}/ranking"
        ranking_response = requests.get(ranking_url, auth=auth, headers=config.HEADERS)
        ranking_response.raise_for_status()
        ranking_data = ranking_response.json()

        if 'data' in ranking_data and 'ranking' in ranking_data['data']:
            ranking = ranking_data['data']['ranking']
            log.info(f"Ranking obtenido con {len(ranking)} mánagers.")
            return ranking
        else:
            log.warning("La respuesta de la API de ranking no contiene los datos esperados.")
            return None

    except requests.exceptions.RequestException as e:
        log.error(f"Error de red al obtener el ranking: {e}", exc_info=True)
        return None
    except (KeyError, IndexError) as e:
        log.error(f"Error de datos al procesar el ranking: {e}", exc_info=True)
        return None
