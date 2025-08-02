import os
import json
import requests
import logging
from datetime import datetime, timedelta
from config import URLS, HEADERS, BearerAuth

log = logging.getLogger(__name__)

TOKEN_FILE = 'last_token.json'

class TokenManager:
    def __init__(self):
        self.token_file = TOKEN_FILE
    
    def save_token(self, token):
        """Guarda el token en un archivo local"""
        try:
            token_data = {
                'token': token,
                'saved_at': datetime.now().isoformat(),
                'expires_at': self._get_token_expiry(token)
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
            
            log.info("Token guardado exitosamente")
            return True
        except Exception as e:
            log.error(f"Error al guardar token: {e}")
            return False
    
    def load_token(self):
        """Carga el token guardado"""
        try:
            if not os.path.exists(self.token_file):
                return None
            
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            token = token_data.get('token')
            if not token:
                return None
            
            # Verificar si el token ha expirado
            expires_at = token_data.get('expires_at')
            if expires_at:
                try:
                    expiry_time = datetime.fromisoformat(expires_at)
                    if datetime.now() > expiry_time:
                        log.info("Token guardado ha expirado")
                        return None
                except:
                    pass
            
            return token
        except Exception as e:
            log.error(f"Error al cargar token: {e}")
            return None
    
    def verify_token(self, token):
        """Verifica si el token es válido haciendo una petición de prueba"""
        try:
            auth = BearerAuth(token)
            response = requests.get(URLS['leagues'], auth=auth, headers=HEADERS, timeout=5)
            return response.status_code == 200
        except Exception as e:
            log.warning(f"Error al verificar token: {e}")
            return False
    
    def _get_token_expiry(self, token):
        """Extrae la fecha de expiración del token JWT"""
        try:
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            exp_time = payload.get('exp', 0)
            if exp_time:
                return datetime.fromtimestamp(exp_time).isoformat()
        except:
            pass
        return None
    
    def get_valid_token(self):
        """Obtiene un token válido (guardado o None si no hay válido)"""
        token = self.load_token()
        if token and self.verify_token(token):
            return token
        return None
    
    def clear_token(self):
        """Elimina el token guardado"""
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            return True
        except Exception as e:
            log.error(f"Error al eliminar token: {e}")
            return False

# Instancia global del gestor de tokens
token_manager = TokenManager() 