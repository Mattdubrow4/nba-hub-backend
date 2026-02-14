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
    """Get game stats using ESPN's key mapping"""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        top_performers = []
        
        if 'boxscore' in data and 'players' in data['boxscore']:
            all_players = []
            
            for team_data in data['boxscore']['players']:
                team_abbr = team_data.get('team', {}).get('abbreviation', 'N/A')
                
                for stat_group in team_data.get('statistics', []):
                    # Get the keys to know which position each stat is in
                    keys = stat_group.get('keys', [])
                    
                    # Find positions of stats we care about
                    pts_idx = next((i for i, k in enumerate(keys) if 'points' in k.lower()), None)
                    reb_idx = next((i for i, k in enumerate(keys) if k.lower() == 'rebounds'), None)
                    ast_idx = next((i for i, k in enumerate(keys) if 'assists' in k.lower()), None)
                    
                    for athlete in stat_group.get('athletes', []):
                        try:
                            name = athlete.get('athlete', {}).get('displayName', '')
                            stats = athlete.get('stats', [])
                            
                            # Extract stats using the key positions
                            points = 0
                            rebounds = 0
                            assists = 0
                            
                            if pts_idx is not None and pts_idx < len(stats):
                                try:
                                    points = int(stats[pts_idx]) if stats[pts_idx] and stats[pts_idx] != '--' else 0
                                except:
                                    pass
                            
                            if reb_idx is not None and reb_idx < len(stats):
                                try:
                                    rebounds = int(stats[reb_idx]) if stats[reb_idx] and stats[reb_idx] != '--' else 0
                                except:
                                    pass
                            
                            if ast_idx is not None and ast_idx < len(stats):
                                try:
                                    assists = int(stats[ast_idx]) if stats[ast_idx] and stats[ast_idx] != '--' else 0
                                except:
                                    pass
                            
                            if points > 0:  # Only include players who scored
                                all_players.append({
                                    'name': name,
                                    'team': team_abbr,
                                    'points': points,
                                    'rebounds': rebounds,
                                    'assists': assists
                                })
                        except Exception as e:
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
        return jsonify({
            'success': True,
            'topPerformers': []
        })
        
@app.route('/api/news', methods=['GET'])
def get_news():
    """Get NBA news from ESPN API (not RSS)"""
    try:
        # Use ESPN's news API instead of RSS
        news_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news"
        response = requests.get(news_url, timeout=10)
        data = response.json()
        
        news_items = []
        
        for article in data.get('articles', [])[:10]:
            headline = article.get('headline', 'No headline')
            description = article.get('description', '')
            
            # Determine type based on keywords
            headline_lower = headline.lower()
            if any(word in headline_lower for word in ['trade', 'deal', 'acquire', 'sign', 'waive']):
                news_type = 'trade'
            elif any(word in headline_lower for word in ['injury', 'hurt', 'out', 'return', 'status', 'questionable']):
                news_type = 'injury'
            else:
                news_type = 'news'
            
            # Get timestamp
            published = article.get('published', '')
            try:
                dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                time_ago = get_time_ago(dt)
            except:
                time_ago = 'Recently'
            
            news_items.append({
                'type': news_type,
                'headline': headline,
                'details': description[:200] + '...' if len(description) > 200 else description,
                'time': time_ago
            })
        
        return jsonify({
            'success': True,
            'news': news_items
        })
        
    except Exception as e:
        print(f"News error: {e}")
        # Return fallback news if API fails
        return jsonify({
            'success': True,
            'news': [
                {
                    'type': 'news',
                    'headline': 'NBA All-Star Weekend in Progress',
                    'details': 'The league\'s best players showcase their skills in Indianapolis.',
                    'time': 'Today'
                },
                {
                    'type': 'news',
                    'headline': 'Regular Season Resumes February 20th',
                    'details': 'Teams return from All-Star break ready for playoff push.',
                    'time': '1 hour ago'
                }
            ]
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
