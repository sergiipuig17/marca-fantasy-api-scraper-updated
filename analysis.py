import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

class FantasyAnalyzer:
    def __init__(self, leagues_dir='mis_ligas'):
        self.leagues_dir = leagues_dir
        self.leagues_data = {}
        self.output_dir = self._create_output_dir()
        self.load_leagues()

    def _create_output_dir(self):
        """Crea y retorna el directorio de salida para el día actual"""
        # Crear directorio base
        base_dir = 'analysis_output'
        os.makedirs(base_dir, exist_ok=True)
        
        # Crear subdirectorio con la fecha actual
        today = datetime.now().strftime('%Y-%m-%d')
        daily_dir = os.path.join(base_dir, today)
        os.makedirs(daily_dir, exist_ok=True)
        
        return daily_dir

    def load_leagues(self):
        """Carga todos los datos de las ligas"""
        for league_dir in Path(self.leagues_dir).iterdir():
            if league_dir.is_dir():
                league_id = league_dir.name
                self.leagues_data[league_id] = {
                    'market': self._load_json(league_dir / 'market.json'),
                    'teams': self._load_teams(league_dir)
                }

    def _load_json(self, file_path):
        """Carga un archivo JSON"""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _load_teams(self, league_dir):
        """Carga todos los equipos de una liga"""
        teams = {}
        for file in league_dir.glob('*_*.json'):
            if 'market' not in file.name:
                teams[file.stem] = self._load_json(file)
        return teams

    def analyze_market_values(self, league_id):
        """Analiza los valores de mercado en una liga"""
        if league_id not in self.leagues_data:
            print(f"Liga {league_id} no encontrada")
            return

        market_data = self.leagues_data[league_id]['market']
        if not market_data:
            return

        # Extraer datos relevantes de cada jugador
        players_data = []
        for player in market_data:
            if 'playerMaster' in player:
                player_info = player['playerMaster']
                players_data.append({
                    'name': player_info.get('nickname', player_info.get('name', 'Unknown')),
                    'market_value': player_info.get('marketValue', 0),
                    'points': player_info.get('points', 0),
                    'average_points': player_info.get('averagePoints', 0),
                    'position': player_info.get('position', 'Unknown')  # position es un string
                })

        df = pd.DataFrame(players_data)
        
        # Calcular estadísticas básicas
        stats = {
            'Valor medio': df['market_value'].mean() / 1000000,  # Convertir a millones
            'Valor máximo': df['market_value'].max() / 1000000,
            'Valor mínimo': df['market_value'].min() / 1000000,
            'Desviación estándar': df['market_value'].std() / 1000000
        }

        # Calcular ratio puntos/precio (en millones)
        df['value_ratio'] = df['points'] / (df['market_value'] / 1000000)
        
        # Encontrar mejores oportunidades (alto ratio puntos/precio)
        best_value = df.nlargest(5, 'value_ratio')[['name', 'market_value', 'points', 'value_ratio', 'position']]
        
        return {
            'stats': stats,
            'best_value': best_value.to_dict('records')
        }

    def analyze_team_performance(self, league_id):
        """Analiza el rendimiento de los equipos en una liga"""
        if league_id not in self.leagues_data:
            print(f"Liga {league_id} no encontrada")
            return

        teams = self.leagues_data[league_id]['teams']
        team_stats = []

        for team_name, team_data in teams.items():
            if not team_data or 'players' not in team_data:
                continue

            total_points = sum(player['playerMaster']['points'] for player in team_data['players'] if 'playerMaster' in player)
            total_value = sum(player['playerMaster']['marketValue'] for player in team_data['players'] if 'playerMaster' in player) / 1000000  # Convertir a millones
            
            team_stats.append({
                'team': team_name.split('_')[1] if '_' in team_name else team_name,  # Usar solo el nombre del equipo
                'total_points': total_points,
                'total_value': total_value,
                'value_efficiency': total_points / total_value if total_value > 0 else 0,
                'num_players': len(team_data['players'])
            })

        return pd.DataFrame(team_stats)

    def plot_team_comparison(self, league_id):
        """Genera gráficos comparativos de los equipos"""
        df = self.analyze_team_performance(league_id)
        if df is None or df.empty:
            return

        # Crear subdirectorio para la liga
        league_dir = os.path.join(self.output_dir, f'liga_{league_id}')
        os.makedirs(league_dir, exist_ok=True)

        # 1. Gráfico de puntos totales
        plt.figure(figsize=(12, 6))
        bars = plt.bar(df['team'], df['total_points'])
        plt.xticks(rotation=45, ha='right')
        plt.title('Puntos Totales por Equipo')
        plt.ylabel('Puntos')
        
        # Añadir valores encima de las barras
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(os.path.join(league_dir, 'points.png'))
        plt.close()

        # 2. Gráfico de eficiencia (puntos por millón gastado)
        plt.figure(figsize=(12, 6))
        bars = plt.bar(df['team'], df['value_efficiency'])
        plt.xticks(rotation=45, ha='right')
        plt.title('Eficiencia de Valor por Equipo (Puntos por Millón €)')
        plt.ylabel('Puntos/M€')
        
        # Añadir valores encima de las barras
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(os.path.join(league_dir, 'efficiency.png'))
        plt.close()

        # Guardar también los datos en formato CSV
        df.to_csv(os.path.join(league_dir, 'team_stats.csv'), index=False)
        
        return league_dir

    def analyze_rival_players(self, league_id, my_team_name="Pushita Alemany"):
        """Analiza los jugadores de equipos rivales"""
        if league_id not in self.leagues_data:
            print(f"Liga {league_id} no encontrada")
            return

        teams = self.leagues_data[league_id]['teams']
        rival_players = []

        # Recopilar jugadores de equipos rivales
        for team_name, team_data in teams.items():
            if my_team_name not in team_name and 'players' in team_data:
                for player in team_data['players']:
                    if 'playerMaster' in player:
                        player_info = player['playerMaster']
                        # Excluir entrenadores
                        if player_info.get('position', '').lower() != 'entrenador':
                            # Verificar si la cláusula está abierta
                            buyout_locked = False
                            if 'buyoutClauseLockedEndTime' in player:
                                locked_time = datetime.fromisoformat(player['buyoutClauseLockedEndTime'].replace('Z', '+00:00'))
                                buyout_locked = locked_time > datetime.now(locked_time.tzinfo)
                            rival_players.append({
                                'name': player_info.get('nickname', player_info.get('name', 'Unknown')),
                                'team': team_name.split('_')[1] if '_' in team_name else team_name,
                                'position': player_info.get('position', 'Unknown'),
                                'market_value': player_info.get('marketValue', 0),
                                'points': player_info.get('points', 0),
                                'buyout_clause': player.get('buyoutClause', 0),
                                'buyout_locked': buyout_locked,
                                'image_url': player_info.get('images', {}).get('small', {}).get('256x278', '')
                            })

        df = pd.DataFrame(rival_players)
        
        # Crear visualización HTML de jugadores con cláusula abierta
        open_clause_players = df[~df['buyout_locked']].sort_values('points', ascending=False)
        
        html_content = """
        <html>
        <head>
            <style>
                .player-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                    gap: 20px;
                    padding: 20px;
                }
                .player-card {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 10px;
                    text-align: center;
                }
                .player-image {
                    width: 128px;
                    height: 139px;
                    object-fit: cover;
                    border-radius: 4px;
                }
                .player-name {
                    font-weight: bold;
                    margin: 10px 0;
                }
                .player-stats {
                    font-size: 0.9em;
                    color: #666;
                }
                .good-value {
                    color: green;
                }
                .bad-value {
                    color: red;
                }
            </style>
        </head>
        <body>
            <h1>Jugadores Rivales con Cláusula Abierta</h1>
            <div class="player-grid">
        """

        for _, player in open_clause_players.iterrows():
            value_ratio = player['buyout_clause'] / player['market_value'] if player['market_value'] > 0 else float('inf')
            value_class = 'good-value' if value_ratio < 1.5 else 'bad-value'
            
            html_content += f"""
                <div class="player-card">
                    <img class="player-image" src="{player['image_url']}" onerror="this.src='https://assets-fantasy.llt-services.com/players/no-player.png'">
                    <div class="player-name">{player['name']}</div>
                    <div class="player-stats">
                        <div>{player['position']}</div>
                        <div>Equipo: {player['team']}</div>
                        <div>Puntos: {player['points']}</div>
                        <div class="{value_class}">Valor: {player['market_value']/1000000:.2f}M€</div>
                        <div class="{value_class}">Cláusula: {player['buyout_clause']/1000000:.2f}M€</div>
                    </div>
                </div>
            """

        html_content += """
            </div>
        </body>
        </html>
        """

        # Guardar visualización HTML y datos
        league_dir = os.path.join(self.output_dir, f'liga_{league_id}')
        os.makedirs(league_dir, exist_ok=True)
        
        with open(os.path.join(league_dir, 'rival_players.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Guardar datos en CSV
        df.to_csv(os.path.join(league_dir, 'rival_players.csv'), index=False)
        
        # Crear gráfico de dispersión de valor vs puntos
        plt.figure(figsize=(12, 8))
        scatter = plt.scatter(df['market_value']/1000000, df['points'], 
                            c=df['buyout_locked'].map({True: 'red', False: 'green'}),
                            alpha=0.6)
        
        plt.xlabel('Valor de Mercado (M€)')
        plt.ylabel('Puntos')
        plt.title('Valor vs Puntos de Jugadores Rivales')
        
        # Añadir leyenda
        plt.legend(handles=scatter.legend_elements()[0], 
                  labels=['Cláusula Abierta', 'Cláusula Bloqueada'])
        
        # Añadir nombres a algunos puntos
        for _, player in df.nlargest(5, 'points').iterrows():
            plt.annotate(player['name'], 
                        (player['market_value']/1000000, player['points']),
                        xytext=(5, 5), textcoords='offset points')
        
        plt.tight_layout()
        plt.savefig(os.path.join(league_dir, 'rival_players_scatter.png'))
        plt.close()

        return df

def main():
    analyzer = FantasyAnalyzer()
    
    # Analizar la liga específica
    league_id = "015878686"
    print(f"\nAnalizando liga {league_id}")
    
    # Análisis de mercado
    market_analysis = analyzer.analyze_market_values(league_id)
    if market_analysis:
        print("\nEstadísticas de mercado:")
        for key, value in market_analysis['stats'].items():
            print(f"{key}: {value:.2f}M€")
        
        print("\nMejores oportunidades de mercado:")
        for player in market_analysis['best_value']:
            print(f"{player['name']} ({player['position']}): "
                  f"{player['points']} puntos por {player['market_value']/1000000:.2f}M€ "
                  f"(ratio: {player['value_ratio']:.2f} puntos/M€)")
        
        # Guardar análisis de mercado en CSV
        league_dir = os.path.join(analyzer.output_dir, f'liga_{league_id}')
        os.makedirs(league_dir, exist_ok=True)
        pd.DataFrame(market_analysis['best_value']).to_csv(
            os.path.join(league_dir, 'market_opportunities.csv'), 
            index=False
        )
    
    # Análisis de equipos
    team_analysis = analyzer.analyze_team_performance(league_id)
    if not team_analysis.empty:
        print("\nRendimiento de equipos:")
        print(team_analysis.sort_values('total_points', ascending=False))
    
    # Generar gráficos de equipos
    output_dir = analyzer.plot_team_comparison(league_id)
    
    # Análisis de jugadores rivales
    rival_analysis = analyzer.analyze_rival_players(league_id)
    if not rival_analysis.empty:
        open_clause = rival_analysis[~rival_analysis['buyout_locked']]
        print(f"\nJugadores rivales con cláusula abierta: {len(open_clause)}")
        print("\nTop 5 jugadores por puntos con cláusula abierta:")
        top_players = open_clause.nlargest(5, 'points')
        for _, player in top_players.iterrows():
            print(f"{player['name']} ({player['position']}) - "
                  f"Equipo: {player['team']}, "
                  f"Puntos: {player['points']}, "
                  f"Valor: {player['market_value']/1000000:.2f}M€, "
                  f"Cláusula: {player['buyout_clause']/1000000:.2f}M€")
    
    print(f"\nAnálisis completo guardado en: {output_dir}/")
    print("Se ha generado un archivo HTML con todos los jugadores rivales con cláusula abierta")

if __name__ == "__main__":
    main()
