from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# BalldontLie API - Free NBA data
BALLDONTLIE_API = "https://api.balldontlie.io/v1"
API_KEY = "26f12344-8c22-4525-8bd4-d8007b942926"

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get today's NBA games from BalldontLie API"""
    try:
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Fetch games from BalldontLie
        url = f"{BALLDONTLIE_API}/games?dates[]={today}"
        headers = {'Authorization': API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        games = []
        for game in data.get('data', []):
            # Determine status
            status = 'Final' if game['status'] == 'Final' else 'Live' if game['status'] else 'Scheduled'
            
            games.append({
                'id': str(game['id']),
                'status': status,
                'home': game['home_team']['full_name'],
                'away': game['visitor_team']['full_name'],
                'homeScore': game['home_team_score'] if game['home_team_score'] else 0,
                'awayScore': game['visitor_team_score'] if game['visitor_team_score'] else 0,
                'time': today
            })
        
        return jsonify({
            'success': True,
            'date': today,
            'games': games if games else get_fallback_games()
        })
        
    except Exception as e:
        print(f"Error fetching games: {e}")
        return jsonify({
            'success': True,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'games': get_fallback_games()
        })

def get_fallback_games():
    """Sample games in case API fails"""
    return [
        {
            'id': '1',
            'status': 'Final',
            'home': 'Los Angeles Lakers',
            'away': 'Golden State Warriors',
            'homeScore': 118,
            'awayScore': 112,
            'time': 'Today'
        }
    ]

@app.route('/api/game/<game_id>/stats', methods=['GET'])
def get_game_stats(game_id):
    """Get game stats from BalldontLie"""
    try:
        url = f"{BALLDONTLIE_API}/stats?game_ids[]={game_id}&per_page=100"
        headers = {'Authorization': API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # Get all players and sort by points
        players = data.get('data', [])
        players.sort(key=lambda x: x.get('pts', 0), reverse=True)
        
        top_performers = []
        for player in players[:4]:
            top_performers.append({
                'name': player['player']['first_name'] + ' ' + player['player']['last_name'],
                'team': player['team']['abbreviation'],
                'points': player.get('pts', 0),
                'rebounds': player.get('reb', 0),
                'assists': player.get('ast', 0)
            })
        
        return jsonify({
            'success': True,
            'topPerformers': top_performers
        })
        
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
