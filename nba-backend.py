"""
NBA Live Data Backend
Fetches real-time NBA scores, stats, and news
Run this on any free hosting service (Render, Railway, Heroku)
"""

from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

# NBA Stats API endpoints
NBA_SCOREBOARD = "https://stats.nba.com/stats/scoreboardv2"
NBA_BOXSCORE = "https://stats.nba.com/stats/boxscoretraditionalv2"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://stats.nba.com/',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true'
}

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get today's NBA games with scores"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            'GameDate': today,
            'LeagueID': '00',
            'DayOffset': '0'
        }
        
        response = requests.get(NBA_SCOREBOARD, params=params, headers=HEADERS, timeout=10)
        data = response.json()
        
        games = []
        game_headers = data['resultSets'][0]['rowSet']
        line_score = data['resultSets'][1]['rowSet']
        
        for game in game_headers:
            game_id = game[2]
            status = game[4]
            home_team = game[6]
            away_team = game[7]
            
            # Find scores from line score
            home_score = None
            away_score = None
            
            for score in line_score:
                if score[3] == game_id:
                    if score[4] == home_team:
                        home_score = score[22]  # PTS
                    elif score[4] == away_team:
                        away_score = score[22]
            
            games.append({
                'id': game_id,
                'status': status,
                'home': home_team,
                'away': away_team,
                'homeScore': home_score,
                'awayScore': away_score,
                'time': game[0]
            })
        
        return jsonify({
            'success': True,
            'date': today,
            'games': games
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/game/<game_id>/stats', methods=['GET'])
def get_game_stats(game_id):
    """Get detailed stats for a specific game"""
    try:
        params = {
            'GameID': game_id,
            'StartPeriod': '0',
            'EndPeriod': '10',
            'StartRange': '0',
            'EndRange': '28800',
            'RangeType': '0'
        }
        
        response = requests.get(NBA_BOXSCORE, params=params, headers=HEADERS, timeout=10)
        data = response.json()
        
        player_stats = data['resultSets'][0]['rowSet']
        
        # Get top performers (top 4 by points)
        players = []
        for player in player_stats:
            players.append({
                'name': player[5],
                'team': player[3],
                'points': player[26],
                'rebounds': player[20],
                'assists': player[21],
                'minutes': player[8]
            })
        
        # Sort by points and get top 4
        players.sort(key=lambda x: x['points'] if x['points'] else 0, reverse=True)
        top_performers = players[:4]
        
        return jsonify({
            'success': True,
            'gameId': game_id,
            'topPerformers': top_performers
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """Get NBA news from RSS feeds"""
    try:
        # This would integrate with NewsAPI or ESPN RSS
        # For now, returning structure
        news = [
            {
                'type': 'trade',
                'headline': 'Check ESPN for latest trade news',
                'details': 'Connect NewsAPI or ESPN RSS feed here',
                'time': 'Live feed coming soon'
            }
        ]
        
        return jsonify({
            'success': True,
            'news': news
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
