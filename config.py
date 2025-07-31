import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Credenciales
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
CLIENT_ID = os.getenv('CLIENT_ID')
BEARER_TOKEN = os.getenv('BEARER_TOKEN')

# Configuración API
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api-fantasy.llt-services.com/api')
API_LANG = os.getenv('API_LANG', 'es')

# URLs de la API
URLS = {
    'leagues': f"{API_BASE_URL}/v4/leagues",
    'players': f"{API_BASE_URL}/v4/players",
    'player_stats': f"{API_BASE_URL}/v3/player",  # Necesita /{id} al final
    'market_value': f"{API_BASE_URL}/v3/player",  # Necesita /{id}/market-value al final
    'league_market': f"{API_BASE_URL}/v3/league",  # Necesita /{id}/market al final
    'league_ranking': f"{API_BASE_URL}/v3/league",  # Necesita /{id}/ranking al final
    'player_offers': f"{API_BASE_URL}/v4/league",  # Necesita /{league_id}/playerTeam/{player_id}/offer al final
    'league_news': f"{API_BASE_URL}/v3/leagues",  # Necesita /{id}/news/{page} al final
}

# Headers comunes
HEADERS = {
    'User-Agent': 'LaLigaFantasy/9.9.1 (com.lfp.laligafantasy; build:5; iOS 18.3.2) Alamofire/5.10.2',
    'X-Lang': API_LANG
}

# Clase para autenticación Bearer
class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r

def get_bearer_token():
    """
    Obtiene el bearer token usando las credenciales del .env
    Si ya hay un BEARER_TOKEN configurado, lo usa directamente
    """
    if BEARER_TOKEN:
        return BEARER_TOKEN
    
    if USERNAME and PASSWORD:
        from auth import get_auth_token
        return get_auth_token(USERNAME, PASSWORD, CLIENT_ID)
    
    raise ValueError("Debes configurar BEARER_TOKEN o USERNAME/PASSWORD en el archivo .env")
