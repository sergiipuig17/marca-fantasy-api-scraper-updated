import requests
import config
import json

def test_team_endpoints():
    print("=== TESTING TEAM ENDPOINTS ===")
    
    try:
        token = config.get_bearer_token()
        if not token:
            print("No hay token válido")
            return
        
        auth = config.BearerAuth(token)
        league_id = "016352246"
        
        # Lista de endpoints a probar
        endpoints = [
            f"{config.URLS['league_teams']}/{league_id}/teams/list",
            f"{config.URLS['league_teams']}/{league_id}/teams",
            f"{config.URLS['league_teams']}/{league_id}/team",
            f"{config.URLS['league_teams']}/{league_id}/standings",
            f"{config.URLS['league_teams']}/{league_id}/classification",
            f"{config.URLS['league_teams']}/{league_id}/teams/standings",
            f"{config.URLS['league_teams']}/{league_id}/teams/classification"
        ]
        
        for endpoint in endpoints:
            print(f"\nProbando: {endpoint}")
            try:
                response = requests.get(endpoint, auth=auth, headers=config.HEADERS, timeout=10)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ ÉXITO - Tipo: {type(data)}")
                    
                    if isinstance(data, list):
                        print(f"   Lista con {len(data)} elementos")
                        if len(data) > 0:
                            print(f"   Primer elemento: {list(data[0].keys()) if isinstance(data[0], dict) else data[0]}")
                    elif isinstance(data, dict):
                        print(f"   Dict con claves: {list(data.keys())}")
                        
                        # Buscar equipos en diferentes claves
                        for key in ['teams', 'data', 'teamsList', 'standings', 'classification']:
                            if key in data and isinstance(data[key], list):
                                print(f"   Encontrados equipos en '{key}': {len(data[key])}")
                                if len(data[key]) > 0:
                                    print(f"   Primer equipo: {list(data[key][0].keys()) if isinstance(data[key][0], dict) else data[key][0]}")
                                break
                else:
                    print(f"❌ Error {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    test_team_endpoints() 