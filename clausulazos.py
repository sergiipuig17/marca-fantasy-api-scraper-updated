import requests
import config
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

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
        
        # La API devuelve directamente una lista con el historial
        if isinstance(response_data, list):
            return response_data
        else:
            return []
    except Exception as e:
        log.warning(f"Error obteniendo historial de valor de mercado para jugador {player_id}: {e}")
        return []

def get_all_players_with_clause():
    """
    Obtiene todos los jugadores de la liga que actualmente tienen una cláusula de rescisión.
    Usa la API del mercado para obtener información actualizada de cláusulas.
    """
    token = config.get_bearer_token()
    auth = config.BearerAuth(token)
    all_players_with_clause = []

    try:
        log.info("Iniciando obtención de jugadores con cláusula desde el mercado...")
        
        # Obtener el ID de la liga
        leagues_response = requests.get(config.URLS['leagues'], auth=auth, headers=config.HEADERS)
        leagues_response.raise_for_status()
        leagues_list = leagues_response.json()
        
        if not leagues_list:
            log.warning("No se encontraron ligas para este usuario.")
            return []
        
        league_id = leagues_list[0]['id']
        log.info(f"ID de liga encontrado: {league_id}")
        
        # Obtener datos del mercado
        market_url = f"{config.URLS['league_market']}/{league_id}/market"
        log.info(f"Obteniendo datos del mercado: {market_url}")
        
        market_response = requests.get(market_url, auth=auth, headers=config.HEADERS, timeout=10)
        market_response.raise_for_status()
        market_data = market_response.json()
        
        if not isinstance(market_data, list):
            log.warning("Formato inesperado de datos del mercado")
            return []
        
        log.info(f"Encontrados {len(market_data)} jugadores en el mercado")
        
        filtered_players_data = []
        
        # Procesar cada jugador del mercado
        for player in market_data:
            if not isinstance(player, dict):
                continue
            
            # Verificar si el jugador tiene sellerTeam (está en venta por un manager)
            seller_team = player.get('sellerTeam')
            if not seller_team:
                continue  # Solo procesar jugadores en venta por managers
            
            # Obtener información del manager
            manager_info = seller_team.get('manager', {})
            manager_name = manager_info.get('managerName', 'N/A')
            
            # Excluir tu propio equipo
            if manager_name == 'Pushita Alemany':
                continue
            
            # Obtener información del jugador
            player_info = player.get('playerMaster', {})
            if not player_info:
                continue
            
            # Obtener información de cláusula desde playerTeam
            player_team = player.get('playerTeam', {})
            buyout_clause = player_team.get('buyoutClause', 0)
            buyout_locked = False
            locked_end_time = player_team.get('buyoutClauseLockedEndTime')
            
            # Verificar si la cláusula está bloqueada y calcular tiempo restante
            # NOTA: Según el usuario, las cláusulas están cerradas por defecto
            # El campo buyoutClauseLockedEndTime indica cuándo termina el bloqueo
            time_remaining_seconds = 0
            if locked_end_time:
                try:
                    locked_time = datetime.fromisoformat(locked_end_time.replace('Z', '+00:00'))
                    time_diff = locked_time - datetime.now(locked_time.tzinfo)
                    # Una cláusula está bloqueada si la fecha de fin de bloqueo es en el futuro
                    # Es decir, si locked_end_time > ahora, entonces está bloqueada
                    buyout_locked = time_diff.total_seconds() > 0
                    if buyout_locked:
                        time_remaining_seconds = int(time_diff.total_seconds())
                except Exception as e:
                    log.warning(f"Error parsing buyoutClauseLockedEndTime: {e}")
                    buyout_locked = True  # Por defecto, bloqueadas si hay error
            
            # Solo incluir jugadores con cláusula
            if buyout_clause > 0:
                player_name = player_info.get('nickname', player_info.get('name', 'N/A'))
                team_name = player_info.get('team', {}).get('name', 'N/A')
                player_id = player_info.get('id')
                market_value = player_info.get('marketValue', 0)
                
                status = "BLOQUEADA" if buyout_locked else "ACTIVA"
                log.info(f"Player with clause - Name: {player_name}, Team: {team_name}, Clause: {buyout_clause}, Manager: {manager_name}, Status: {status}, LockedEndTime: {locked_end_time}")
                
                # Obtener imagen del jugador
                images = player_info.get('images', {})
                image_url = (
                    images.get('transparent', {}).get('256x256') or
                    images.get('small', {}).get('256x278') or
                    'https://assets-fantasy.llt-services.com/players/no-player-sq.png'
                )

                # Obtener historial de valor de mercado para calcular tendencia
                market_value_trend = 0
                try:
                    market_history = get_market_value_history(player_id, token)
                    if market_history and len(market_history) >= 2:
                        # Calcular tendencia basada en los últimos 2 valores
                        recent_values = market_history[-2:]
                        if len(recent_values) == 2:
                            current_val = recent_values[1].get('marketValue', market_value)
                            previous_val = recent_values[0].get('marketValue', market_value)
                            market_value_trend = current_val - previous_val
                            log.info(f"Tendencia calculada para {player_name}: {current_val} - {previous_val} = {market_value_trend}")
                except Exception as e:
                    log.warning(f"Error obteniendo historial de valor para {player_name}: {e}")

                player_data_obj = {
                    'id': player_id,
                    'name': player_name,
                    'team_name': team_name,
                    'position': POSITIONS.get(player_info.get('positionId'), 'N/A'),
                    'position_id': player_info.get('positionId'),
                    'image_url': image_url,
                    'owner': manager_name,
                    'buyout_clause': buyout_clause,
                    'market_value': market_value,
                    'player_points': player_info.get('points', 0),
                    'market_value_trend': market_value_trend,
                    'time_remaining_seconds': time_remaining_seconds,
                    'expirationDate': None,
                    'buyout_locked': buyout_locked,
                    'locked_end_time': locked_end_time
                }
                
                log.info(f"Added player with clause: {player_data_obj}")
                filtered_players_data.append(player_data_obj)
        
        # Sort players by buyout_clause (highest first)
        filtered_players_data.sort(key=lambda x: x['buyout_clause'], reverse=True)
        
        all_players_with_clause = filtered_players_data
        log.info(f"Procesados {len(all_players_with_clause)} jugadores con cláusula (excluyendo 'Pushita Alemany').")

    except Exception as e:
        log.error(f"Error general en get_all_players_with_clause: {e}", exc_info=True)

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

def test_different_apis_for_clauses():
    """
    Función para probar diferentes APIs y encontrar dónde están las cláusulas de rescisión
    """
    token = config.get_bearer_token()
    auth = config.BearerAuth(token)
    
    try:
        # Obtener el ID de la liga
        leagues_response = requests.get(config.URLS['leagues'], auth=auth, headers=config.HEADERS)
        leagues_response.raise_for_status()
        leagues_list = leagues_response.json()
        
        if not leagues_list:
            log.warning("No se encontraron ligas para este usuario.")
            return
        
        league_id = leagues_list[0]['id']
        log.info(f"ID de liga encontrado: {league_id}")
        
        # Probar API v3 de jugadores (la que usa el scraper original)
        log.info("=== Probando API v3 de jugadores ===")
        player_url = f"{config.URLS['player_stats']}/1"  # Probar con el jugador ID 1
        log.info(f"URL: {player_url}")
        
        try:
            player_response = requests.get(player_url, auth=auth, headers=config.HEADERS)
            if player_response.status_code == 200:
                player_data = player_response.json()
                log.info(f"Estructura del jugador: {player_data}")
                log.info(f"Claves disponibles: {list(player_data.keys())}")
                
                # Buscar campos relacionados con cláusulas
                clause_fields = [k for k in player_data.keys() if 'clause' in k.lower() or 'buyout' in k.lower() or 'rescue' in k.lower()]
                if clause_fields:
                    log.info(f"Campos de cláusula encontrados: {clause_fields}")
                    for field in clause_fields:
                        log.info(f"  {field}: {player_data.get(field)}")
                else:
                    log.info("No se encontraron campos de cláusula en el jugador individual")
            else:
                log.warning(f"Player API devolvió status {player_response.status_code}")
        except Exception as e:
            log.warning(f"Error obteniendo jugador: {e}")
        
        # Probar con un jugador que sabemos que está en el mercado
        log.info("=== Probando con jugador del mercado ===")
        market_url = f"{config.URLS['league_market']}/{league_id}/market"
        log.info(f"URL mercado: {market_url}")
        
        try:
            market_response = requests.get(market_url, auth=auth, headers=config.HEADERS)
            market_response.raise_for_status()
            market_data = market_response.json()
            
            if isinstance(market_data, list) and len(market_data) > 0:
                # Tomar el primer jugador que tenga sellerTeam
                for player in market_data:
                    if player.get('sellerTeam'):
                        player_id = player.get('playerMaster', {}).get('id')
                        if player_id:
                            log.info(f"Probando jugador del mercado con ID: {player_id}")
                            
                            # Obtener datos detallados del jugador
                            detailed_player_url = f"{config.URLS['player_stats']}/{player_id}"
                            log.info(f"URL jugador detallado: {detailed_player_url}")
                            
                            try:
                                detailed_response = requests.get(detailed_player_url, auth=auth, headers=config.HEADERS)
                                if detailed_response.status_code == 200:
                                    detailed_data = detailed_response.json()
                                    log.info(f"Estructura del jugador detallado: {detailed_data}")
                                    log.info(f"Claves disponibles: {list(detailed_data.keys())}")
                                    
                                    # Buscar campos relacionados con cláusulas
                                    clause_fields = [k for k in detailed_data.keys() if 'clause' in k.lower() or 'buyout' in k.lower() or 'rescue' in k.lower()]
                                    if clause_fields:
                                        log.info(f"Campos de cláusula encontrados: {clause_fields}")
                                        for field in clause_fields:
                                            log.info(f"  {field}: {detailed_data.get(field)}")
                                    else:
                                        log.info("No se encontraron campos de cláusula en el jugador detallado")
                                else:
                                    log.warning(f"Detailed player API devolvió status {detailed_response.status_code}")
                            except Exception as e:
                                log.warning(f"Error obteniendo jugador detallado: {e}")
                            break  # Solo probar con el primer jugador
            else:
                log.warning("No se encontraron jugadores en el mercado")
                
        except Exception as e:
            log.warning(f"Error obteniendo mercado: {e}")
        
        # Probar API de ligas v4
        log.info("=== Probando API de ligas v4 ===")
        leagues_v4_url = config.URLS['leagues']
        log.info(f"URL: {leagues_v4_url}")
        
        try:
            leagues_v4_response = requests.get(leagues_v4_url, auth=auth, headers=config.HEADERS)
            if leagues_v4_response.status_code == 200:
                leagues_v4_data = leagues_v4_response.json()
                log.info(f"Estructura de ligas v4: {leagues_v4_data}")
                if isinstance(leagues_v4_data, list) and len(leagues_v4_data) > 0:
                    first_league = leagues_v4_data[0]
                    log.info(f"Claves de la primera liga: {list(first_league.keys())}")
            else:
                log.warning(f"Leagues v4 API devolvió status {leagues_v4_response.status_code}")
        except Exception as e:
            log.warning(f"Error obteniendo ligas v4: {e}")
            
    except Exception as e:
        log.error(f"Error general en test_different_apis_for_clauses: {e}", exc_info=True)

def debug_clause_system():
    """
    Función de debug para investigar el sistema de cláusulas en detalle
    """
    token = config.get_bearer_token()
    auth = config.BearerAuth(token)
    
    try:
        # Obtener el ID de la liga
        leagues_response = requests.get(config.URLS['leagues'], auth=auth, headers=config.HEADERS)
        leagues_response.raise_for_status()
        leagues_list = leagues_response.json()
        
        if not leagues_list:
            log.warning("No se encontraron ligas para este usuario.")
            return
        
        league_id = leagues_list[0]['id']
        log.info(f"=== DEBUG CLAUSE SYSTEM - Liga ID: {league_id} ===")
        
        # 1. Probar API del mercado para ver si hay cláusulas ahí
        log.info("1. Probando API del mercado...")
        market_url = f"{config.URLS['league_market']}/{league_id}/market"
        try:
            market_response = requests.get(market_url, auth=auth, headers=config.HEADERS, timeout=10)
            if market_response.status_code == 200:
                market_data = market_response.json()
                log.info(f"   Mercado: {len(market_data) if isinstance(market_data, list) else 'dict'} elementos")
                
                # Buscar jugadores con sellerTeam (en venta por managers)
                if isinstance(market_data, list):
                    sellers = [p for p in market_data if p.get('sellerTeam')]
                    log.info(f"   Jugadores en venta por managers: {len(sellers)}")
                    
                    if sellers:
                        # Analizar el primer jugador en venta
                        first_seller = sellers[0]
                        log.info(f"   Primer jugador en venta: {first_seller}")
                        
                        # Buscar campos relacionados con cláusulas
                        clause_fields = []
                        for key, value in first_seller.items():
                            if any(keyword in key.lower() for keyword in ['clause', 'buyout', 'rescue', 'price', 'value']):
                                clause_fields.append((key, value))
                        
                        if clause_fields:
                            log.info(f"   Campos de cláusula encontrados en mercado: {clause_fields}")
                        else:
                            log.info("   No se encontraron campos de cláusula en el mercado")
            else:
                log.warning(f"   Mercado API devolvió status {market_response.status_code}")
        except Exception as e:
            log.warning(f"   Error con mercado API: {e}")
        
        # 2. Probar diferentes APIs de equipos
        log.info("2. Probando APIs de equipos...")
        team_apis = [
            f"{config.URLS['league_teams']}/{league_id}/teams",
            f"{config.URLS['league_teams']}/{league_id}/team",
            f"{config.URLS['league_teams']}/{league_id}/teams/list",
            f"{config.URLS['league_teams']}/{league_id}/standings",
            f"{config.URLS['league_teams']}/{league_id}/classification"
        ]
        
        for api_url in team_apis:
            try:
                log.info(f"   Probando: {api_url}")
                response = requests.get(api_url, auth=auth, headers=config.HEADERS, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    log.info(f"   ✅ Funciona: {type(data)} - {len(data) if isinstance(data, list) else 'dict'}")
                    
                    # Si es una lista, mostrar el primer elemento
                    if isinstance(data, list) and len(data) > 0:
                        first_item = data[0]
                        log.info(f"   Primer elemento: {list(first_item.keys()) if isinstance(first_item, dict) else first_item}")
                    
                    # Si es un dict, mostrar las claves principales
                    elif isinstance(data, dict):
                        log.info(f"   Claves principales: {list(data.keys())}")
                        
                        # Buscar equipos en diferentes claves posibles
                        for key in ['teams', 'data', 'teamsList', 'standings', 'classification']:
                            if key in data and isinstance(data[key], list):
                                log.info(f"   Encontrados equipos en '{key}': {len(data[key])}")
                                if len(data[key]) > 0:
                                    first_team = data[key][0]
                                    log.info(f"   Primer equipo: {list(first_team.keys()) if isinstance(first_team, dict) else first_team}")
                                break
                else:
                    log.info(f"   ❌ Status {response.status_code}")
            except Exception as e:
                log.info(f"   ❌ Error: {e}")
        
        # 3. Analizar archivos JSON guardados en detalle
        log.info("3. Analizando archivos JSON guardados...")
        ligas_dir = Path("mis_ligas")
        if ligas_dir.exists():
            ligas_disponibles = [d for d in ligas_dir.iterdir() if d.is_dir()]
            if ligas_disponibles:
                league_dir = ligas_disponibles[0]
                log.info(f"   Analizando liga: {league_dir.name}")
                
                # Contar archivos
                team_files = [f for f in league_dir.glob("*.json") if f.name != "market.json"]
                log.info(f"   Archivos de equipos: {len(team_files)}")
                
                # Analizar el primer archivo en detalle
                if team_files:
                    first_file = team_files[0]
                    log.info(f"   Analizando: {first_file.name}")
                    
                    try:
                        with open(first_file, 'r', encoding='utf-8') as f:
                            team_data = json.load(f)
                        
                        if 'players' in team_data:
                            players = team_data['players']
                            log.info(f"   Jugadores en archivo: {len(players)}")
                            
                            # Analizar el primer jugador en detalle
                            if players:
                                first_player = players[0]
                                log.info(f"   Primer jugador - Claves: {list(first_player.keys())}")
                                
                                # Buscar todos los campos relacionados con cláusulas
                                clause_related = []
                                for key, value in first_player.items():
                                    if any(keyword in key.lower() for keyword in ['clause', 'buyout', 'rescue', 'price', 'value', 'lock', 'time', 'end']):
                                        clause_related.append((key, value))
                                
                                if clause_related:
                                    log.info(f"   Campos relacionados con cláusulas: {clause_related}")
                                
                                # Analizar playerMaster
                                if 'playerMaster' in first_player:
                                    player_master = first_player['playerMaster']
                                    log.info(f"   playerMaster - Claves: {list(player_master.keys())}")
                                
                                # Analizar playerMarket si existe
                                if 'playerMarket' in first_player:
                                    player_market = first_player['playerMarket']
                                    log.info(f"   playerMarket - Claves: {list(player_market.keys())}")
                                    log.info(f"   playerMarket - Datos: {player_market}")
                    except Exception as e:
                        log.warning(f"   Error analizando archivo: {e}")
        
        # 4. Probar API de jugadores individuales
        log.info("4. Probando API de jugadores individuales...")
        try:
            # Probar con un jugador que sabemos que existe
            player_url = f"{config.URLS['player_stats']}/2507"  # Dmitrovic
            player_response = requests.get(player_url, auth=auth, headers=config.HEADERS, timeout=10)
            if player_response.status_code == 200:
                player_data = player_response.json()
                log.info(f"   Jugador individual - Claves: {list(player_data.keys())}")
                
                # Buscar campos de cláusula
                clause_fields = []
                for key, value in player_data.items():
                    if any(keyword in key.lower() for keyword in ['clause', 'buyout', 'rescue', 'price', 'value']):
                        clause_fields.append((key, value))
                
                if clause_fields:
                    log.info(f"   Campos de cláusula en jugador individual: {clause_fields}")
                else:
                    log.info("   No se encontraron campos de cláusula en jugador individual")
            else:
                log.warning(f"   Player API devolvió status {player_response.status_code}")
        except Exception as e:
            log.warning(f"   Error con player API: {e}")
        
        log.info("=== FIN DEBUG CLAUSE SYSTEM ===")
        
    except Exception as e:
        log.error(f"Error en debug_clause_system: {e}", exc_info=True)
