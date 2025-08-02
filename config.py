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
    'league_teams': f"{API_BASE_URL}/v3/league",  # Necesita /{id}/teams al final
    'team_players': f"{API_BASE_URL}/v3/team",  # Necesita /{id}/players al final
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
    Obtiene el bearer token del gestor de tokens
    """
    from token_manager import token_manager
    token = token_manager.get_valid_token()
    if token:
        return token
    
    # Si no hay token válido, intentar con el del .env como fallback
    if BEARER_TOKEN:
        if token_manager.verify_token(BEARER_TOKEN):
            token_manager.save_token(BEARER_TOKEN)
            return BEARER_TOKEN
    
    if USERNAME and PASSWORD:
        from auth import get_auth_token
        try:
            token = get_auth_token(USERNAME, PASSWORD, CLIENT_ID)
            token_manager.save_token(token)
            return token
        except Exception as e:
            print(f"Error al obtener token con credenciales: {e}")
    
    # Si no hay token válido, devolver None para que el frontend pida uno nuevo
    return None
