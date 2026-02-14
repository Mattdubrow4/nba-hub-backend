from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ESPN API - Free, no auth needed
ESPN_API = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get NBA games - today's games or recent games if none today"""
    try:
        all_games = []
        dates_to_check = []
        
        # Check today, yesterday, and 2 days ago
        for days_ago in range(0, 3):
            date = datetime.now() - timedelta(days=days_ago)
            dates_to_check.append(date)
        
        # Try each date until we find games
        for date in dates_to_check:
            date_str = date.strftime('%Y%m%d')
            url = f"{ESPN_API}?dates={date_str}"
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            games_found = []
            for event in data.get('events', []):
                competition = event['competitions'][0]
                home_team = competition['competitors'][0]
                away_team = competition['competitors'][1]
                
                # Determine status
                status_type = competition['status']['type']['name']
                if status_type == 'STATUS_FINAL':
                    status = 'Final'
                elif status_type == 'STATUS_IN_PROGRESS':
                    status = 'Live'
                else:
                    status = 'Scheduled'
                
                games_found.append({
                    'id': event['id'],
                    'status': status,
                    'home': home_team['team']['displayName'],
                    'away': away_team['team']['displayName'],
                    'homeScore': int(home_team.get('score', 0)),
                    'awayScore': int(away_team.get('score', 0)),
                    'time': date.strftime('%B %d, %Y')
                })
            
            # If we found games, use them
            if games_found:
                all_games = games_found
                break
        
        # If still no games (e.g., All-Star break), return message
        if not all_games:
            all_games = [{
                'id': '0',
                'status': 'Info',
                'home': 'No Recent Games',
                'away': 'All-Star Break',
                'homeScore': 0,
                'awayScore': 0,
                'time': 'Check back after Feb 20th'
            }]
        
        return jsonify({
            'success': True,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'games': all_games
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/game/<game_id>/stats', methods=['GET'])
def get_game_stats(game_id):
    """Get game stats from ESPN"""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        top_performers = []
        
        # Get top players from boxscore
        if 'boxscore' in data and 'players' in data['boxscore']:
            all_players = []
            
            for team in data['boxscore']['players']:
                for player_group in team['statistics']:
                    for player in player_group.get('athletes', []):
                        stats = player.get('stats', [])
                        if len(stats) >= 3:
                            try:
                                points = int(stats[0]) if stats[0] and stats[0] != '--' else 0
                                rebounds = int(stats[1]) if stats[1] and stats[1] != '--' else 0
                                assists = int(stats[2]) if stats[2] and stats[2] != '--' else 0
                                
                                all_players.append({
                                    'name': player['athlete']['displayName'],
                                    'team': team['team']['abbreviation'],
                                    'points': points,
                                    'rebounds': rebounds,
                                    'assists': assists
                                })
                            except (ValueError, TypeError):
                                continue
            
            # Sort by points and get top 4
            all_players.sort(key=lambda x: x['points'], reverse=True)
            top_performers = all_players[:4]
        
        return jsonify({
            'success': True,
            'topPerformers': top_performers
        })
        
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
