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
        response_data = response.json()
        
        # Manejar diferentes formatos de respuesta
        if isinstance(response_data, dict):
            return response_data.get('data', [])
        elif isinstance(response_data, list):
            return response_data
        else:
            log.warning(f"Formato de respuesta inesperado para jugador {player_id}: {type(response_data)}")
            return []
    except requests.exceptions.RequestException as e:
        log.warning(f"No se pudo obtener el historial de valor para el jugador {player_id}: {e}")
        return []

def get_all_players_with_clause():
    """
    Obtiene todos los jugadores de la liga que actualmente tienen una cláusula de rescisión.
    Usa la API del mercado para obtener jugadores y filtrar los que tienen cláusulas.
    """
    token = config.get_bearer_token()
    auth = config.BearerAuth(token)
    all_players_with_clause = []

    try:
        log.info("Iniciando obtención de jugadores con cláusula...")
        
        # Obtener el ID de la liga
        leagues_response = requests.get(config.URLS['leagues'], auth=auth, headers=config.HEADERS)
        leagues_response.raise_for_status()
        leagues_list = leagues_response.json()
        
        if not leagues_list:
            log.warning("No se encontraron ligas para este usuario.")
            return []
        
        league_id = leagues_list[0]['id']
        log.info(f"ID de liga encontrado: {league_id}")
        
        # Obtener jugadores del mercado
        market_url = f"{config.URLS['league_market']}/{league_id}/market"
        log.info(f"Obteniendo jugadores del mercado con URL: {market_url}")
        
        market_response = requests.get(market_url, auth=auth, headers=config.HEADERS)
        market_response.raise_for_status()
        market_data = market_response.json()
        
        if isinstance(market_data, dict):
            players_on_market = market_data.get('data', [])
        elif isinstance(market_data, list):
            players_on_market = market_data
        else:
            players_on_market = []
            log.warning(f"Unexpected response format from market API: {market_data}")
        
        log.info(f"Encontrados {len(players_on_market)} jugadores en el mercado.")
        
        # Debug: imprimir la estructura del primer jugador
        if players_on_market:
            log.info(f"DEBUG - Estructura del primer jugador del mercado: {players_on_market[0]}")
        
        filtered_players_data = []
        for player_data in players_on_market:
            # Intentar diferentes rutas para obtener el manager
            owner_name = None
            if 'manager' in player_data:
                owner_name = player_data['manager'].get('managerName')
            elif 'sellerTeam' in player_data and player_data['sellerTeam']:
                owner_name = player_data['sellerTeam'].get('managerName')
            
            if not owner_name:
                owner_name = 'N/A'
            
            player_info = player_data.get('playerMaster', {})
            
            if not player_info:
                continue
                
            player_name = player_info.get('nickname', 'N/A')
            team_name = player_info.get('team', {}).get('name', 'N/A')
            
            log.info(f"Processing player: {player_name} - Team: {team_name} - Owner: {owner_name}")
            
            # Exclude players from "Pushita Alemany"
            if owner_name != 'Pushita Alemany':
                # Verificar si el jugador tiene cláusula de rescisión
                buyout_clause = player_data.get('price')
                # También verificar otros campos posibles
                if not buyout_clause:
                    buyout_clause = player_data.get('buyoutClause')
                if not buyout_clause:
                    buyout_clause = player_data.get('clause')
                
                log.info(f"DEBUG - Buyout clause for {player_name}: {buyout_clause}")
                
                if buyout_clause and buyout_clause > 0:
                    player_id = player_info.get('id')
                    market_value = player_info.get('marketValue')
                    end_protection_str = player_data.get('until')
                    
                    log.info(f"Player with clause - Name: {player_name}, Team: {team_name}, Clause: {buyout_clause}, Value: {market_value}, Until: {end_protection_str}")
                    
                    history = get_market_value_history(player_id, token)
                    trend = 0
                    if len(history) > 1:
                        trend = history[-1]['marketValue'] - history[-2]['marketValue']
                    
                    time_remaining_seconds = 0
                    if end_protection_str:
                        try:
                            end_protection_date = datetime.fromisoformat(end_protection_str.replace('Z', '+00:00'))
                            time_diff = end_protection_date - datetime.now(end_protection_date.tzinfo)
                            time_remaining_seconds = int(time_diff.total_seconds())
                            log.info(f"Time remaining for {player_name}: {time_remaining_seconds} seconds")
                        except Exception as e:
                            log.warning(f"Error parsing date for {player_name}: {e}")

                    # Obtener imagen del jugador
                    images = player_info.get('images', {})
                    image_url = (
                        images.get('transparent', {}).get('256x256') or
                        'https://assets-fantasy.llt-services.com/players/no-player-sq.png'
                    )

                    player_data_obj = {
                        'id': player_id,
                        'name': player_name,
                        'team_name': team_name,
                        'position': POSITIONS.get(player_info.get('positionId'), 'N/A'),
                        'position_id': player_info.get('positionId'),
                        'image_url': image_url,
                        'owner': owner_name,
                        'buyout_clause': buyout_clause,
                        'market_value': market_value,
                        'player_points': player_info.get('points', 0),
                        'market_value_trend': trend,
                        'time_remaining_seconds': time_remaining_seconds,
                        'expirationDate': end_protection_str
                    }
                    
                    log.info(f"Added player with clause: {player_data_obj}")
                    filtered_players_data.append(player_data_obj)
        
        # Sort players by time_remaining_seconds (earliest first)
        filtered_players_data.sort(key=lambda x: x['time_remaining_seconds'])
        
        all_players_with_clause = filtered_players_data
        log.info(f"Procesados {len(all_players_with_clause)} jugadores con cláusula (excluyendo 'Pushita Alemany').")

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
