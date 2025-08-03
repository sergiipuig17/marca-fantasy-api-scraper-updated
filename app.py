from flask import Flask, render_template, redirect, url_for, request
import logging
import os
import personal_lineup
import database
import clausulazos
import config
from clausulazos import get_league_ranking

# --- Configuración ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] (%(threadName)-10s) %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# --- Constantes y Caché ---
MY_MANAGER_NAME = "Pushita Alemany"
market_data_cache = []
clausulazos_data_cache = []
my_team_cache = []
ranking_cache = []

def fa_scraping_job():
    global market_data_cache, clausulazos_data_cache, my_team_cache, ranking_cache
    logging.info("Iniciando ciclo de scraping manual...")
    try:
        # Verificar autenticación antes de continuar
        token = config.get_bearer_token()
        if token:
            logging.info("Autenticación exitosa")
        else:
            logging.warning("No hay token válido disponible")
            return
        
        market_data_cache = personal_lineup.main()
        logging.info(f"Ciclo de scraping de mercado completado: {len(market_data_cache)} jugadores.")
        
        all_clausulazos = clausulazos.get_all_players_with_clause()
        clausulazos_data_cache = all_clausulazos
        logging.info(f"Ciclo de scraping de clausulazos completado: {len(clausulazos_data_cache)} jugadores.")
        
        # Obtener todos los jugadores de mi equipo
        my_team_cache = clausulazos.get_my_team_players()
        logging.info(f"Datos de mi equipo cargados: {len(my_team_cache)} jugadores.")

        ranking_cache = get_league_ranking()
        if ranking_cache:
            logging.info(f"Clasificación de la liga cargada: {len(ranking_cache)} mánagers.")
        else:
            logging.warning("No se pudo cargar la clasificación de la liga.")

    except Exception as e:
        logging.error(f"Ocurrió un error durante el scraping: {e}", exc_info=True)

# --- Rutas de la Aplicación Web ---
@app.route('/')
def index():
    if not market_data_cache:
        return render_template('no_data.html', 
                             message="No hay datos del mercado disponibles",
                             details="Es posible que necesites configurar un token de autenticación válido.")
    
    sort_by = request.args.get('sort', 'market_value_desc')
    players_to_display = list(market_data_cache)
    
    key_map = {
        'market_value_asc': ('market_value', False),
        'market_value_desc': ('market_value', True),
        'points_desc': ('player_points', True),
        'growth_desc': ('market_value_trend', True) # Nueva opción de ordenación
    }
    
    sort_key, reverse = key_map.get(sort_by, ('market_value', True))
    players_to_display.sort(key=lambda p: p.get(sort_key) or -999999, reverse=reverse)

    return render_template('index.html', players=players_to_display, sort_by=sort_by)

@app.route('/clausulazos')
def clausulazos_page():
    # Obtener múltiples criterios de ordenación
    sort_criteria = request.args.getlist('sort')
    if not sort_criteria:
        sort_criteria = ['time_remaining_asc']  # Ordenación por defecto
    
    # Si no hay datos en cache, usar lista vacía en lugar de mostrar página de configuración
    if not clausulazos_data_cache:
        players_to_display = []
        owners = []
    else:
        players_to_display = list(clausulazos_data_cache)
        # Get unique owners for the filter checklist
        owners = sorted(list(set(p['owner'] for p in players_to_display if 'owner' in p)))

    # Mapeo de criterios de ordenación
    key_map = {
        'time_remaining_asc': ('time_remaining_seconds', False),
        'time_remaining_desc': ('time_remaining_seconds', True),
        'buyout_clause_desc': ('buyout_clause', True),
        'buyout_clause_asc': ('buyout_clause', False),
        'position_asc': ('position_id', False),
        'position_desc': ('position_id', True),
        'market_value_desc': ('market_value', True),
        'market_value_asc': ('market_value', False),
        'market_trend_desc': ('market_value_trend', True),
        'market_trend_asc': ('market_value_trend', False),
        'name_asc': ('name', False),
        'name_desc': ('name', True),
        'team_asc': ('team_name', False),
        'team_desc': ('team_name', True),
        'owner_asc': ('owner', False),
        'owner_desc': ('owner', True)
    }

    # Aplicar ordenación múltiple
    for sort_by in reversed(sort_criteria):  # Aplicar en orden inverso para prioridad correcta
        sort_key, reverse = key_map.get(sort_by, ('time_remaining_seconds', False))
        players_to_display.sort(key=lambda p: p.get(sort_key) or float('inf'), reverse=reverse)
    
    return render_template('clausulazos.html', players=players_to_display, sort_by=sort_criteria, owners=owners)

@app.route('/my_team')
def my_team_page():
    # --- Datos de Clasificación ---
    my_ranking_info = {}
    if ranking_cache:
        for manager in ranking_cache:
            if manager.get('managerName') == MY_MANAGER_NAME:
                my_ranking_info = {
                    'points': manager.get('points', 0),
                    'position': manager.get('position', 'N/A')
                }
                break

    # --- Análisis de Jugadores ---
    players_to_display = list(my_team_cache)
    
    # 1. Alerta de Clausulazos (protección < 48h)
    alert_players = [p for p in players_to_display if p.get('time_remaining_seconds', float('inf')) < 172800]
    alert_players.sort(key=lambda p: p.get('time_remaining_seconds', float('inf')))

    # 2. Estudio de Mercado
    gainers = sorted([p for p in players_to_display if p.get('market_value_trend', 0) > 0], key=lambda p: p.get('market_value_trend'), reverse=True)[:5]
    losers = sorted([p for p in players_to_display if p.get('market_value_trend', 0) < 0], key=lambda p: p.get('market_value_trend'))[:5]
    
    # 3. Rentabilidad (puntos por millón)
    for p in players_to_display:
        p['profitability'] = (p.get('player_points', 0) / (p.get('market_value', 1) / 1000000)) if p.get('market_value') else 0
    
    most_profitable = sorted(players_to_display, key=lambda p: p.get('profitability', 0), reverse=True)[:5]

    return render_template('my_team.html', 
                           players=players_to_display, 
                           my_ranking=my_ranking_info,
                           alert_players=alert_players,
                           top_gainers=gainers,
                           top_losers=losers,
                           most_profitable=most_profitable)

@app.route('/refresh')
def refresh_data():
    fa_scraping_job()
    referrer = request.referrer or url_for('index')
    return redirect(referrer)

@app.route('/api/save_token', methods=['POST'])
def save_token():
    """Guarda un nuevo token desde el frontend y ejecuta el scraping"""
    try:
        data = request.get_json()
        token = data.get('token')
        if not token:
            return {'success': False, 'error': 'Token no proporcionado'}, 400
        
        from token_manager import token_manager
        if token_manager.save_token(token):
            # Ejecutar el scraping después de guardar el token
            try:
                fa_scraping_job()
                return {'success': True, 'message': 'Token guardado y datos cargados exitosamente'}
            except Exception as scraping_error:
                return {'success': True, 'message': 'Token guardado pero error al cargar datos: ' + str(scraping_error)}
        else:
            return {'success': False, 'error': 'Error al guardar el token'}, 500
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/api/check_auth')
def check_auth():
    """Verifica si hay un token válido"""
    try:
        token = config.get_bearer_token()
        return {'authenticated': token is not None}
    except Exception as e:
        return {'authenticated': False, 'error': str(e)}

# --- Arranque de la Aplicación ---
if __name__ == '__main__':
    if os.path.exists(database.DATABASE_FILE):
        os.remove(database.DATABASE_FILE)
    database.init_db()
    fa_scraping_job()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
