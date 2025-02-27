import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

class FantasyAnalyzer:
    def __init__(self, leagues_dir='mis_ligas'):
        self.leagues_dir = leagues_dir
        self.leagues_data = {}
        self.load_leagues()

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

        # Crear directorio para los gráficos si no existe
        output_dir = 'analysis_output'
        os.makedirs(output_dir, exist_ok=True)

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
        plt.savefig(f'{output_dir}/points_{league_id}.png')
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
        plt.savefig(f'{output_dir}/efficiency_{league_id}.png')
        plt.close()

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
    
    # Análisis de equipos
    team_analysis = analyzer.analyze_team_performance(league_id)
    if not team_analysis.empty:
        print("\nRendimiento de equipos:")
        print(team_analysis.sort_values('total_points', ascending=False))
    
    # Generar gráficos
    analyzer.plot_team_comparison(league_id)
    print(f"\nGráficos guardados en el directorio analysis_output/")

if __name__ == "__main__":
    main()
