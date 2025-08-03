import clausulazos
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] (%(threadName)-10s) %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def test_my_team():
    print("=== TESTING get_my_team_players() ===")
    
    try:
        players = clausulazos.get_my_team_players()
        print(f"Resultado: {len(players)} jugadores encontrados")
        
        if players:
            print("\nPrimeros 3 jugadores:")
            for i, player in enumerate(players[:3]):
                print(f"{i+1}. {player['name']} - {player['team_name']} - {player['position']}")
        else:
            print("No se encontraron jugadores")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_my_team() 