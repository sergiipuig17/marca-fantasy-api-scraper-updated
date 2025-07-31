import sqlite3
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from config import BearerAuth, get_bearer_token

DATABASE_FILE = "fantasy.db"

def get_db_connection():
    """Crea una conexión a la base de datos."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    conn = get_db_connection()
    cursor = conn.cursor()
    logging.info("Comprobando e inicializando la base de datos...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_players (
        id INTEGER PRIMARY KEY,
        player_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        team_name TEXT,
        position_id INTEGER,
        position TEXT,
        market_value INTEGER,
        player_points INTEGER,
        on_sale_date TEXT,
        owner_name TEXT,
        owner_id TEXT,
        market_value_trend INTEGER,
        image_url TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
    logging.info("Base de datos lista.")

def _fetch_market_trend(player_data):
    """Función auxiliar para obtener la tendencia de mercado de un jugador."""
    player_id = player_data.get('player_id')
    player_data['market_value_trend'] = 0
    if not player_id:
        return player_data
    
    try:
        url = f"https://api-fantasy.llt-services.com/api/v3/player/{player_id}/market-value"
        token = get_bearer_token()
        response = requests.get(url, auth=BearerAuth(token), timeout=10)
        response.raise_for_status()
        history = response.json()
        
        if len(history) >= 2:
            history.sort(key=lambda x: x['date'], reverse=True)
            trend = history[0]['marketValue'] - history[1]['marketValue']
            player_data['market_value_trend'] = trend
    except Exception as e:
        logging.error(f"No se pudo obtener la tendencia de mercado para el jugador {player_id}: {e}")
    
    return player_data

def update_market_data(market_payload):
    """
    Borra los datos del mercado antiguos, los enriquece con la tendencia y los inserta.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    logging.info("Actualizando y enriqueciendo datos del mercado en la base de datos...")
    cursor.execute("DELETE FROM market_players")

    initial_players = []
    for sale in market_payload:
        if sale.get('sellerTeam') is not None:
            continue

        player_master = sale.get('playerMaster', {})
        if not player_master:
            continue
        
        images = player_master.get('images', {})
        image_url = (
            images.get('transparent', {}).get('256x256') or
            'https://assets-fantasy.llt-services.com/players/no-player-sq.png'
        )

        initial_players.append({
            "player_id": player_master.get('id'), "name": player_master.get('nickname'),
            "team_name": player_master.get('team', {}).get('name'),
            "position_id": player_master.get('positionId'), "position": player_master.get('position'),
            "market_value": sale.get('salePrice'), "player_points": player_master.get('points'),
            "on_sale_date": sale.get('expirationDate'), "owner_name": 'Liga', "owner_id": 'LFP',
            "image_url": image_url
        })

    enriched_players = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        enriched_players = list(executor.map(_fetch_market_trend, initial_players))

    for player in enriched_players:
        cursor.execute("""
            INSERT INTO market_players (
                player_id, name, team_name, position_id, position, market_value, 
                player_points, on_sale_date, owner_name, owner_id, market_value_trend, image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player["player_id"], player["name"], player["team_name"], player["position_id"],
            player["position"], player["market_value"], player["player_points"],
            player["on_sale_date"], player["owner_name"], player["owner_id"],
            player.get("market_value_trend", 0), player["image_url"]
        ))

    conn.commit()
    conn.close()
    logging.info(f"Se han insertado {len(enriched_players)} jugadores del mercado en la base de datos.")
    return enriched_players

def get_market_players():
    """Devuelve todos los jugadores del mercado desde la base de datos."""
    conn = get_db_connection()
    players = conn.execute("SELECT * FROM market_players ORDER BY market_value DESC").fetchall()
    conn.close()
    return players
