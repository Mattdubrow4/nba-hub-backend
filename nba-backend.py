from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Sample NBA games data that always works
SAMPLE_GAMES = [
    {
        'id': '1',
        'status': 'Final',
        'home': 'Los Angeles Lakers',
        'away': 'Golden State Warriors',
        'homeScore': 118,
        'awayScore': 112,
        'time': 'February 13, 2026'
    },
    {
        'id': '2',
        'status': 'Final',
        'home': 'Boston Celtics',
        'away': 'Miami Heat',
        'homeScore': 124,
        'awayScore': 105,
        'time': 'February 13, 2026'
    }
]

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get today's NBA games"""
    return jsonify({
        'success': True,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'games': SAMPLE_GAMES
    })

@app.route('/api/game/<game_id>/stats', methods=['GET'])
def get_game_stats(game_id):
    """Get game stats"""
    performers = [
        {'name': 'LeBron James', 'team': 'LAL', 'points': 32, 'rebounds': 8, 'assists': 11},
        {'name': 'Stephen Curry', 'team': 'GSW', 'points': 28, 'rebounds': 5, 'assists': 7}
    ]
    return jsonify({'success': True, 'topPerformers': performers})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
