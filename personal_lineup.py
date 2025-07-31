import json
import logging
import os
import shutil
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

import requests
from config import HEADERS, URLS, BearerAuth, get_bearer_token
import database

log = logging.getLogger(__name__)

RUTA_LIGAS = "mis_ligas/"
REQUEST_TIMEOUT = 30

def get_league_id_and_token():
    """Obtiene el ID de la primera liga del usuario y el token."""
    try:
        token = get_bearer_token()
        log.info("Token cargado para obtener ID de liga.")
    except Exception as e:
        log.error(f"No se pudo cargar el token. Error: {e}", exc_info=True)
        raise

    url = URLS['leagues']
    try:
        response = requests.get(url, auth=BearerAuth(token), headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        # LA API DEVUELVE UNA LISTA DIRECTAMENTE
        leagues_list = response.json()
        
        if not leagues_list:
            log.warning("La respuesta de la API de ligas no contiene datos o está vacía.")
            return None, None
        
        # Asumimos la primera liga de la lista
        league_id = leagues_list[0]['id']
        log.info(f"ID de liga principal encontrado: {league_id}")
        return league_id, token
    except requests.exceptions.RequestException as e:
        log.error(f"Error de red al obtener el ID de la liga: {e}", exc_info=True)
        raise
    except (KeyError, IndexError) as e:
        log.error(f"Error en los datos al procesar el ID de la liga: {e}", exc_info=True)
        raise

def main():
    """Función principal para el scraping de mercado."""
    log.info("Iniciando el proceso principal de scraping de personal_lineup.")
    database.init_db()
    
    try:
        league_id, token = get_league_id_and_token()
        if not league_id:
            return []
        
        market_players = read_market(league_id, token)
        return market_players
    except Exception as e:
        log.error(f"Fallo en la ejecución principal de personal_lineup: {e}", exc_info=True)
        return []

def read_market(league_id, token):
    """Lee los datos del mercado y los actualiza en la base de datos."""
    url = f"{URLS['league_market']}/{league_id}/market"
    log.info(f"Accediendo al mercado con URL: {url}")
    
    try:
        response = requests.get(url, auth=BearerAuth(token), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        market_payload = response.json()
        log.info("Datos del mercado obtenidos correctamente de la API.")
        return database.update_market_data(market_payload)
    except requests.exceptions.RequestException as e:
        log.error(f"Error de red al obtener los datos del mercado: {e}", exc_info=True)
        return []
