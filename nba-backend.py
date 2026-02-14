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
        
        # Try to get leaders first (simpler and more reliable)
        if 'leaders' in data:
            for leader_category in data['leaders']:
                for leader in leader_category.get('leaders', []):
                    athlete = leader.get('athlete', {})
                    if athlete:
                        # Get stats from display value
                        display_value = leader.get('displayValue', '0')
                        value = float(display_value.split()[0]) if display_value else 0
                        
                        name = athlete.get('displayName', 'Unknown')
                        team = athlete.get('team', {}).get('abbreviation', 'N/A')
                        
                        # Check if we already have this player
                        existing = next((p for p in top_performers if p['name'] == name), None)
                        if not existing:
                            top_performers.append({
                                'name': name,
                                'team': team,
                                'points': 0,
                                'rebounds': 0,
                                'assists': 0
                            })
                            existing = top_performers[-1]
                        
                        # Update the relevant stat
                        category = leader_category.get('name', '').lower()
                        if 'point' in category:
                            existing['points'] = int(value)
                        elif 'rebound' in category:
                            existing['rebounds'] = int(value)
                        elif 'assist' in category:
                            existing['assists'] = int(value)
        
        # If leaders didn't work, try boxscore
        if not top_performers and 'boxscore' in data and 'players' in data['boxscore']:
            all_players = []
            
            for team in data['boxscore']['players']:
                team_abbr = team['team']['abbreviation']
                
                for stat_group in team.get('statistics', []):
                    if stat_group.get('name') != 'starters':
                        continue
                        
                    for player in stat_group.get('athletes', []):
                        try:
                            name = player['athlete']['displayName']
                            stats = player.get('stats', [])
                            
                            if len(stats) >= 15:  # ESPN has many stat columns
                                # Common positions: PTS, REB, AST
                                points = int(stats[14]) if stats[14] and stats[14] != '--' else 0
                                rebounds = int(stats[11]) if stats[11] and stats[11] != '--' else 0
                                assists = int(stats[12]) if stats[12] and stats[12] != '--' else 0
                                
                                if points > 0:  # Only include players who scored
                                    all_players.append({
                                        'name': name,
                                        'team': team_abbr,
                                        'points': points,
                                        'rebounds': rebounds,
                                        'assists': assists
                                    })
                        except (ValueError, TypeError, IndexError):
                            continue
            
            # Sort by points and get top 4
            all_players.sort(key=lambda x: x['points'], reverse=True)
            top_performers = all_players[:4]
        
        # If still no performers, return empty (game might not have stats yet)
        if not top_performers:
            top_performers = []
        
        return jsonify({
            'success': True,
            'topPerformers': top_performers
        })
        
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/news', methods=['GET'])
def get_news():
    """Get NBA news from ESPN RSS feed"""
    try:
        import xml.etree.ElementTree as ET
        
        # ESPN NBA RSS feed
        rss_url = "https://www.espn.com/espn/rss/nba/news"
        response = requests.get(rss_url, timeout=10)
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        news_items = []
        for item in root.findall('.//item')[:10]:  # Get first 10 items
            title = item.find('title').text if item.find('title') is not None else ''
            description = item.find('description').text if item.find('description') is not None else ''
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
            
            # Determine type based on keywords
            title_lower = title.lower()
            if any(word in title_lower for word in ['trade', 'deal', 'acquire', 'sign']):
                news_type = 'trade'
            elif any(word in title_lower for word in ['injury', 'hurt', 'out', 'return', 'status']):
                news_type = 'injury'
            else:
                news_type = 'news'
            
            # Format time
            try:
                from datetime import datetime
                dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                time_ago = get_time_ago(dt)
            except:
                time_ago = 'Recently'
            
            news_items.append({
                'type': news_type,
                'headline': title,
                'details': description[:200] + '...' if len(description) > 200 else description,
                'time': time_ago
            })
        
        return jsonify({
            'success': True,
            'news': news_items
        })
        
    except Exception as e:
        print(f"News error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

def get_time_ago(dt):
    """Convert datetime to 'X hours ago' format"""
    from datetime import datetime
    now = datetime.utcnow()
    diff = now - dt
    
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return f"{int(diff.total_seconds() / 60)} minutes ago"
    elif hours < 24:
        return f"{int(hours)} hours ago"
    else:
        return f"{int(hours / 24)} days ago"

@app.route('/api/social', methods=['GET'])
def get_social():
    """Get NBA social content from Reddit"""
    try:
        # Reddit NBA subreddit (no auth needed for public posts)
        reddit_url = "https://www.reddit.com/r/nba/hot.json?limit=15"
        headers = {'User-Agent': 'NBA-Hub/1.0'}
        
        response = requests.get(reddit_url, headers=headers, timeout=10)
        data = response.json()
        
        posts = []
        for post_data in data.get('data', {}).get('children', []):
            post = post_data.get('data', {})
            
            # Skip pinned posts
            if post.get('stickied'):
                continue
            
            title = post.get('title', '')
            author = post.get('author', 'NBA Fan')
            score = post.get('score', 0)
            comments = post.get('num_comments', 0)
            
            # Format score
            if score >= 1000:
                score_str = f"{score/1000:.1f}K"
            else:
                score_str = str(score)
            
            # Format comments
            if comments >= 1000:
                comments_str = f"{comments/1000:.1f}K"
            else:
                comments_str = str(comments)
            
            posts.append({
                'platform': '🔴',  # Reddit icon
                'user': f'r/NBA',
                'handle': f'u/{author}',
                'avatar': '🏀',
                'content': title,
                'likes': score_str,
                'retweets': comments_str
            })
            
            if len(posts) >= 10:
                break
        
        return jsonify({
            'success': True,
            'posts': posts
        })
        
    except Exception as e:
        print(f"Social error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
