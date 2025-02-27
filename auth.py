import requests
from config import HEADERS

def get_auth_token(username, password, client_id="fec9e3fd-8f88-45ab-8cbd-b70b9d65dde0"):
    """
    Obtiene el token de autenticación usando usuario y contraseña
    """
    url = 'https://login.laliga.es/laligadspprob2c.onmicrosoft.com/oauth2/v2.0/token?p=B2C_1A_ResourceOwnerv2'
    
    data = {
        'grant_type': 'password',
        'client_id': client_id,
        'scope': f'openid {client_id} offline_access',
        'redirect_url': 'authredirect://com.lfp.laligafantasy',
        'username': username,
        'password': password,
        'response_type': 'id_token'
    }
    
    response = requests.post(url, data=data, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Error al obtener el token: {response.status_code} - {response.text}")
