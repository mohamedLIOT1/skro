
import os
import json
import time
import secrets
import logging
import jwt
from dotenv import load_dotenv
from urllib.parse import urlencode
import requests
from flask import Flask, jsonify, session, redirect, request, url_for, make_response, send_from_directory
from datetime import timedelta, datetime

load_dotenv()  # Load .env if exists



app = Flask(__name__)
# Use hardcoded SECRET_KEY (defined below in the Discord config section)
# This will be set after imports
app.permanent_session_lifetime = timedelta(days=7)

# --- Cookie settings for custom domain/HTTPS ---
# More permissive settings for better compatibility across different hosting platforms
is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RENDER')
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(is_production),  # Only secure in production
    SESSION_COOKIE_HTTPONLY=False,  # Allow JS access for debugging
    SESSION_COOKIE_DOMAIN=None,
    SESSION_COOKIE_PATH='/'
)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Use 'data' folder instead of 'كروت سكرو' for website deployment
DATA_DIR = os.path.join(BASE_DIR, 'data')
POINTS_FILE = os.path.join(DATA_DIR, 'points.json')
VIP_FILE = os.path.join(DATA_DIR, 'vip_members.json')
SERVERS_FILE = os.path.join(DATA_DIR, 'servers.json')
REFERRALS_FILE = os.path.join(DATA_DIR, 'referrals.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')  # unique users who logged into website
BLACKLIST_FILE = os.path.join(DATA_DIR, 'blacklist.json')  # blacklisted users

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Discord OAuth Config - Direct values (no env vars needed)
DISCORD_CLIENT_ID = '1424342801801416834'
DISCORD_CLIENT_SECRET = '0Wz9RdaBDLXIRkeacKL99kAwrOBHfteS'
DISCORD_REDIRECT_URI = 'https://www.skrew.ct.ws/auth/discord/callback'

# Secret key for Flask sessions
SECRET_KEY_VALUE = '492bf62f7c5918057247d2a810c7644d3da99a01b59d49527566219cf296c8c4'
app.secret_key = SECRET_KEY_VALUE  # Set the secret key here

# Debug: Print loaded values
print(f"🔑 CLIENT_ID: {DISCORD_CLIENT_ID}")
print(f"🔐 CLIENT_SECRET: ***{DISCORD_CLIENT_SECRET[-4:]}")
print(f"🔗 REDIRECT_URI: {DISCORD_REDIRECT_URI}")
DISCORD_OAUTH_BASE = 'https://discord.com/api/oauth2'
DISCORD_API_BASE = 'https://discord.com/api'

OAUTH_SCOPES = ['identify', 'guilds']

# API key for bot-to-website VIP sync (change this to a private value if needed)
VIP_API_KEY = os.getenv('VIP_API_KEY', 'skro_vip_api_key_change_me')

# Security monitoring webhook
SECURITY_WEBHOOK_URL = 'https://discord.com/api/webhooks/1427963349970452501/p3azMQM8b8W-VvXNeXrGhEYlWPJimVayKTxLbIsRd9vZ1iDgK2MyvsYDyeDHSqYxZ_Lm'

def send_security_alert(alert_type, message, details=None):
    """Send security alert to Discord webhook"""
    try:
        colors = {
            'error': 15548997,  # Red
            'warning': 16776960,  # Yellow
            'suspicious': 16744272,  # Orange
            'info': 3447003  # Blue
        }
        
        embed = {
            "title": f"🚨 {alert_type.upper()} - تنبيه أمني",
            "description": message,
            "color": colors.get(alert_type, colors['info']),
            "fields": [],
            "footer": {"text": "نظام الحماية - موقع سكرو"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if details:
            for key, value in details.items():
                embed["fields"].append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })
        
        # Add request info
        try:
            embed["fields"].extend([
                {"name": "IP", "value": request.remote_addr or 'Unknown', "inline": True},
                {"name": "User Agent", "value": request.headers.get('User-Agent', 'Unknown')[:100], "inline": False},
                {"name": "Path", "value": request.path, "inline": True},
                {"name": "Method", "value": request.method, "inline": True}
            ])
        except:
            pass
        
        requests.post(SECURITY_WEBHOOK_URL, json={"embeds": [embed]}, timeout=3)
    except Exception as e:
        logging.error(f'Failed to send security alert: {e}')

def _require_api_key():
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    if api_key != VIP_API_KEY:
        return False
    return True

# --- JWT Helpers ---

def create_jwt_token(user_data):
    """Create JWT token with user data"""
    payload = {
        'user': user_data,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY_VALUE, algorithm='HS256')
    return token

def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY_VALUE, algorithms=['HS256'])
        return payload.get('user')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_user_from_request():
    """Get user from JWT token in cookie or header"""
    # Try cookie first
    token = request.cookies.get('auth_token')
    # Try Authorization header as fallback
    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
    
    if token:
        return verify_jwt_token(token)
    return None

# --- JSON Helpers ---

def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f'Failed saving {path}: {e}')

# --- API Routes ---

@app.route('/api/stats')
def api_stats():
    servers_data = load_json(SERVERS_FILE, {"servers": 0})
    guild_count = int(servers_data.get('servers', 0))
    # Players count = unique users found in points.json
    points_data = load_json(POINTS_FILE, {})
    unique_users = set()
    try:
        for _guild, users in points_data.items():
            for uid in users.keys():
                unique_users.add(str(uid))
    except Exception:
        pass
    players_count = len(unique_users)

    # Registered users count
    users_data = load_json(USERS_FILE, {"users": []})
    users_registered = len(set(str(u) for u in users_data.get('users', [])))

    return jsonify({
        'guild_count': guild_count,
        'players_count': players_count,
        'users_registered': users_registered,
    })

@app.route('/api/user/<int:user_id>/points')
def api_user_points(user_id: int):
    points_data = load_json(POINTS_FILE, {})
    # points.json structure: { guild_id: { user_id: {...} } }
    aggregated = {
        'points': 0,
        'wins': 0,
        'games': 0,
        'best': 0,
        'total_score': 0
    }
    for guild_id, users in points_data.items():
        user_entry = users.get(str(user_id))
        if user_entry:
            aggregated['points'] += user_entry.get('points', 0)
            aggregated['wins'] += user_entry.get('wins', 0)
            aggregated['games'] += user_entry.get('games', 0)
            aggregated['best'] = max(aggregated['best'], user_entry.get('best', 0))
            aggregated['total_score'] += user_entry.get('total_score', 0)
    aggregated['average'] = (aggregated['total_score'] / aggregated['games']) if aggregated['games'] else 0
    # credits = تحويل النقاط للعملة (مثال: كل 10 نقاط = 1 كريدت)
    rate = 0.1
    aggregated['credits'] = round(aggregated['points'] * rate, 2)

    # VIP status
    vip_data = load_json(VIP_FILE, {})
    vip_tier = vip_data.get(str(user_id))

    # Blacklist status
    blacklist_data = load_json(BLACKLIST_FILE, {})
    blacklist_info = blacklist_data.get(str(user_id))

    return jsonify({
        'user_id': user_id,
        'stats': aggregated,
        'vip_tier': vip_tier,
        'blacklisted': blacklist_info is not None,
        'blacklist_reason': blacklist_info.get('reason') if blacklist_info else None,
        'blacklist_date': blacklist_info.get('date') if blacklist_info else None
    })

@app.route('/api/user/<int:user_id>/license')
def api_user_license(user_id: int):
    # Placeholder: لو عنده كريدت >= 50 نعتبره عنده لايسنس بريميوم
    user_points = api_user_points(user_id).json
    has_license = user_points['stats']['credits'] >= 50
    return jsonify({
        'user_id': user_id,
        'has_license': has_license
    })

@app.route('/api/user/<int:user_id>/purchase', methods=['POST'])
def api_purchase_license(user_id: int):
    body = request.json or {}
    target = body.get('product', 'premium_license')
    user_points_resp = api_user_points(user_id)
    data = user_points_resp.json
    credits = data['stats']['credits']
    cost = 50
    if target == 'bot_instance':
        cost = 80
    if credits < cost:
        return jsonify({'ok': False, 'error': 'رصيد غير كافي'}), 400
    # NOTE: هنا المفروض ننقص النقاط فعلياً ونخزن عملية الشراء في قاعدة بيانات حقيقية
    return jsonify({'ok': True, 'message': 'تم منح الترخيص مؤقتاً (محاكاة)', 'product': target})

# Friend Mode Purchase endpoints
FRIEND_MODE_FILE = os.path.join(DATA_DIR, 'friend_mode_purchases.json')

@app.route('/api/user/<int:user_id>/friend-mode')
def api_check_friend_mode(user_id: int):
    """Check if user has purchased friend mode"""
    purchases = load_json(FRIEND_MODE_FILE, {})
    purchased = str(user_id) in purchases
    purchase_date = purchases.get(str(user_id), {}).get('date') if purchased else None
    return jsonify({
        'user_id': user_id,
        'purchased': purchased,
        'purchase_date': purchase_date
    })

@app.route('/api/user/<int:user_id>/purchase-friend-mode', methods=['POST'])
def api_purchase_friend_mode(user_id: int):
    """Purchase friend mode (سكرووو صاحب صحبه)"""
    # Check current credits
    user_points_resp = api_user_points(user_id)
    data = user_points_resp.json
    credits = data['stats']['credits']
    
    if credits < 50:
        return jsonify({'ok': False, 'error': 'رصيد غير كافي. تحتاج إلى 50 كريدت.'}), 400
    
    # Check if already purchased
    purchases = load_json(FRIEND_MODE_FILE, {})
    if str(user_id) in purchases:
        return jsonify({'ok': False, 'error': 'لقد قمت بشراء هذا المنتج مسبقاً'}), 400
    
    # Deduct credits from all guilds
    points_data = load_json(POINTS_FILE, {})
    total_deducted = 0
    credits_to_deduct = 50.0
    
    for guild_id, guild_data in points_data.items():
        if str(user_id) in guild_data:
            user_entry = guild_data[str(user_id)]
            user_credits = user_entry.get('points', 0) / 10.0  # 10 points = 1 credit
            
            if user_credits > 0:
                deduct_amount = min(user_credits, credits_to_deduct - total_deducted)
                points_to_deduct = int(deduct_amount * 10)
                user_entry['points'] = max(0, user_entry['points'] - points_to_deduct)
                total_deducted += deduct_amount
                
                if total_deducted >= credits_to_deduct:
                    break
    
    save_json(POINTS_FILE, points_data)
    
    # Record purchase
    purchases[str(user_id)] = {
        'date': datetime.utcnow().isoformat(),
        'credits_spent': 50
    }
    save_json(FRIEND_MODE_FILE, purchases)
    
    # Log purchase
    logging.info(f"User {user_id} purchased Friend Mode for 50 credits")
    
    return jsonify({
        'ok': True,
        'message': 'تم شراء وضع صاحب صحبه بنجاح',
        'new_credits': credits - 50
    })

# Owner check endpoint
@app.route('/api/owner-check/<int:user_id>')
def api_owner_check(user_id: int):
    owner_config_file = os.path.join(DATA_DIR, 'owner_config.json')
    owner_data = load_json(owner_config_file, {'owner_ids': []})
    is_owner = user_id in owner_data.get('owner_ids', [])
    return jsonify({'is_owner': is_owner, 'user_id': user_id})

# Blacklist check endpoint
@app.route('/api/blacklist/<int:user_id>')
def api_check_blacklist(user_id: int):
    """Check if user is blacklisted"""
    blacklist_data = load_json(BLACKLIST_FILE, {})
    user_blacklist = blacklist_data.get(str(user_id))
    
    if user_blacklist:
        return jsonify({
            'blacklisted': True,
            'user_id': user_id,
            'reason': user_blacklist.get('reason', 'غير محدد'),
            'date': user_blacklist.get('date'),
            'by': user_blacklist.get('by', 'الإدارة')
        })
    return jsonify({'blacklisted': False, 'user_id': user_id})

# Blacklist management endpoint (for bot)
@app.route('/api/blacklist/set', methods=['POST'])
def api_set_blacklist():
    """Add or remove user from blacklist"""
    if not _require_api_key():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 401
    
    payload = request.json or {}
    user_id = str(payload.get('user_id'))
    action = payload.get('action', 'add')  # 'add' or 'remove'
    reason = payload.get('reason', 'مخالفة القواعد')
    by_user = payload.get('by', 'الإدارة')
    
    if not user_id:
        return jsonify({'ok': False, 'error': 'user_id مفقود'}), 400
    
    blacklist_data = load_json(BLACKLIST_FILE, {})
    
    if action == 'add':
        blacklist_data[user_id] = {
            'reason': reason,
            'date': datetime.utcnow().isoformat(),
            'by': by_user
        }
        save_json(BLACKLIST_FILE, blacklist_data)
        logging.info(f"🚫 User {user_id} added to blacklist. Reason: {reason}")
        return jsonify({'ok': True, 'action': 'added', 'user_id': int(user_id)})
    
    elif action == 'remove':
        if user_id in blacklist_data:
            del blacklist_data[user_id]
            save_json(BLACKLIST_FILE, blacklist_data)
            logging.info(f"✅ User {user_id} removed from blacklist")
            return jsonify({'ok': True, 'action': 'removed', 'user_id': int(user_id)})
        return jsonify({'ok': False, 'error': 'المستخدم ليس في البلاك ليست'}), 404
    
    return jsonify({'ok': False, 'error': 'action غير صالح'}), 400

# --- VIP endpoints for sync with the bot ---
@app.route('/api/vip/<int:user_id>')
def api_get_vip(user_id: int):
    vip_data = load_json(VIP_FILE, {})
    tier = vip_data.get(str(user_id))
    return jsonify({'user_id': user_id, 'vip_tier': tier})

@app.route('/api/vip/set', methods=['POST'])
def api_set_vip():
    # Simple API key auth
    if not _require_api_key():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 401
    payload = request.json or {}
    user_id = str(payload.get('user_id'))
    tier = payload.get('vip_tier')  # None or string like "Diamond" | "Gold" | "Silver"
    if not user_id:
        return jsonify({'ok': False, 'error': 'user_id مفقود'}), 400
    vip_data = load_json(VIP_FILE, {})
    if tier:
        vip_data[user_id] = tier
    else:
        # Remove VIP if tier is falsy
        vip_data.pop(user_id, None)
    save_json(VIP_FILE, vip_data)
    return jsonify({'ok': True, 'user_id': int(user_id), 'vip_tier': tier})

# --- Leaderboard endpoint ---
@app.route('/api/leaderboard')
def api_leaderboard():
    """Get top players by points, wins, and games"""
    try:
        points_data = load_json(POINTS_FILE, {})
        # إذا لم يوجد ملف users.json، استخدم dict فارغ
        try:
            users_data = load_json(USERS_FILE, {})
        except Exception:
            users_data = {}
        
        # Aggregate all players data
        all_players = []
        
        for guild_id, guild_data in points_data.items():
            for user_id, stats in guild_data.items():
                # Try to get user info
                user_info = users_data.get(user_id, {})
                # Prefer global_name, then username, fallback: جلب من Discord API إذا لم يوجد
                username = user_info.get('username')
                if not username:
                    # جلب اسم المستخدم من Discord API
                    try:
                        discord_api_url = f"https://discord.com/api/users/{user_id}"
                        headers = {}
                        bot_token = os.environ.get('DISCORD_BOT_TOKEN')
                        if bot_token:
                            headers['Authorization'] = f'Bot {bot_token}'
                        resp = requests.get(discord_api_url, headers=headers, timeout=2)
                        logging.info(f"[LEADERBOARD] Discord API fetch user {user_id} | Status: {resp.status_code} | Response: {resp.text}")
                        if resp.status_code == 200:
                            discord_user = resp.json()
                            username = discord_user.get('global_name') or discord_user.get('username') or f'User {user_id}'
                            # حفظ الاسم في users.json
                            user_info['username'] = username
                            users_data[user_id] = user_info
                            save_json(USERS_FILE, users_data)
                        elif resp.status_code == 401:
                            logging.error(f"[LEADERBOARD] Discord API Unauthorized (401): تحقق من توكن البوت وصلاحياته!")
                            username = f'User {user_id}'
                        elif resp.status_code == 403:
                            logging.error(f"[LEADERBOARD] Discord API Forbidden (403): البوت ليس في نفس السيرفر أو لا يملك صلاحية View Members!")
                            username = f'User {user_id}'
                        elif resp.status_code == 404:
                            logging.error(f"[LEADERBOARD] Discord API Not Found (404): user_id غير صحيح أو المستخدم غير متاح.")
                            username = f'User {user_id}'
                        else:
                            logging.error(f"[LEADERBOARD] Discord API Error {resp.status_code}: {resp.text}")
                            username = f'User {user_id}'
                    except Exception as ex:
                        logging.error(f"[LEADERBOARD] Exception fetching Discord user {user_id}: {ex}")
                        username = f'User {user_id}'
                avatar = user_info.get('avatar')
                avatar_url = None
                # Check for valid avatar (not None, not empty, not 'None', not 'null')
                if avatar and str(avatar).lower() not in ['none', 'null', '']:
                    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=256"
                else:
                    # Try to fetch from Discord API if not found
                    try:
                        discord_user = None
                        discord_api_url = f"https://discord.com/api/users/{user_id}"
                        headers = {}
                        bot_token = os.environ.get('DISCORD_BOT_TOKEN')
                        if bot_token:
                            headers['Authorization'] = f'Bot {bot_token}'
                        resp = requests.get(discord_api_url, headers=headers, timeout=2)
                        logging.info(f"Discord API response for user {user_id}: {resp.status_code} {resp.text}")
                        if resp.status_code == 200:
                            discord_user = resp.json()
                            avatar = discord_user.get('avatar')
                            if avatar:
                                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=256"
                                # Update users.json for next time
                                user_info['avatar'] = avatar
                                users_data[user_id] = user_info
                                save_json(USERS_FILE, users_data)
                        if not avatar_url:
                            # fallback: use Discord default avatar (256px)
                            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png?size=256"
                    except Exception as ex:
                        logging.error(f"Error fetching Discord avatar for {user_id}: {ex}")
                        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png?size=256"
                # تأكد أن avatar_url ليس None أبداً
                if not avatar_url:
                    avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png?size=256"
                logging.info(f"Leaderboard user: {username} | avatar_url: {avatar_url}")
                all_players.append({
                    'user_id': user_id,
                    'username': username,
                    'avatar': avatar_url,
                    'points': stats.get('points', 0),
                    'wins': stats.get('wins', 0),
                    'games': stats.get('games', 0),
                    'best': stats.get('best', 0)
                })
        
        # Sort by different criteria and get top 10
        top_points = sorted(all_players, key=lambda x: x['points'], reverse=True)[:10]
        top_wins = sorted(all_players, key=lambda x: x['wins'], reverse=True)[:10]
        top_games = sorted(all_players, key=lambda x: x['games'], reverse=True)[:10]
        
        return jsonify({
            'points': top_points,
            'wins': top_wins,
            'games': top_games
        })
    except Exception as e:
        logging.error(f"Error in leaderboard endpoint: {e}")
        return jsonify({
            'points': [],
            'wins': [],
            'games': []
        })

# --- Points sync (from bot) ---
@app.route('/api/points/update', methods=['POST'])
def api_points_update():
    if not _require_api_key():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 401
    body = request.json or {}
    guild_id = str(body.get('guild_id'))
    user_id = str(body.get('user_id'))
    if not guild_id or not user_id:
        return jsonify({'ok': False, 'error': 'guild_id أو user_id مفقود'}), 400

    mode = (body.get('mode') or 'inc').lower()  # 'inc' or 'set'
    delta_points = int(body.get('points') or 0)
    delta_wins = int(body.get('wins') or 0)
    delta_games = int(body.get('games') or 0)
    score = body.get('score')  # points achieved in last game (affects best and total_score)
    best = body.get('best')
    total_score = body.get('total_score')

    data = load_json(POINTS_FILE, {})
    guild_map = data.get(guild_id) or {}
    user_entry = guild_map.get(user_id) or {
        'points': 0,
        'wins': 0,
        'games': 0,
        'best': 0,
        'total_score': 0
    }

    if mode == 'set':
        if body.get('points') is not None:
            user_entry['points'] = int(body['points'])
        if body.get('wins') is not None:
            user_entry['wins'] = int(body['wins'])
        if body.get('games') is not None:
            user_entry['games'] = int(body['games'])
        if best is not None:
            user_entry['best'] = int(best)
        if total_score is not None:
            user_entry['total_score'] = int(total_score)
    else:
        # inc mode
        user_entry['points'] += delta_points
        user_entry['wins'] += delta_wins
        user_entry['games'] += delta_games
        if best is not None:
            user_entry['best'] = max(int(best), int(user_entry.get('best', 0)))
        if score is not None:
            try:
                s = int(score)
                user_entry['total_score'] += s
                user_entry['best'] = max(int(user_entry.get('best', 0)), s)
            except Exception:
                pass

    guild_map[user_id] = user_entry
    data[guild_id] = guild_map
    save_json(POINTS_FILE, data)

    # Build aggregated like /api/user/<id>/points
    aggregated = {
        'points': user_entry['points'],
        'wins': user_entry['wins'],
        'games': user_entry['games'],
        'best': user_entry['best'],
        'total_score': user_entry['total_score']
    }
    aggregated['average'] = (aggregated['total_score'] / aggregated['games']) if aggregated['games'] else 0

    return jsonify({'ok': True, 'guild_id': int(guild_id), 'user_id': int(user_id), 'entry': user_entry, 'aggregated': aggregated})

# --- Servers (guilds) count sync ---
@app.route('/api/servers/set', methods=['POST'])
def api_servers_set():
    if not _require_api_key():
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 401
    body = request.json or {}
    count = body.get('servers')
    if count is None:
        return jsonify({'ok': False, 'error': 'servers مفقود'}), 400
    try:
        count = int(count)
    except Exception:
        return jsonify({'ok': False, 'error': 'servers يجب أن يكون رقم'}), 400

    save_json(SERVERS_FILE, {'servers': count})
    return jsonify({'ok': True, 'servers': count})

# Referral system endpoint (for سكرووو_صاحب_صحبو)
@app.route('/api/referral', methods=['POST'])
def api_referral():
    payload = request.json or {}
    inviter_id = str(payload.get('inviter_id'))
    friend_id = str(payload.get('friend_id'))
    if not inviter_id or not friend_id or inviter_id == friend_id:
        return jsonify({'ok': False, 'error': 'بيانات غير صالحة'}), 400
    data = load_json(REFERRALS_FILE, {})
    key = f'{inviter_id}:{friend_id}'
    if key in data:
        return jsonify({'ok': False, 'error': 'تم استخدام هذا الإحالة سابقاً'}), 409
    data[key] = {'ts': int(time.time())}
    save_json(REFERRALS_FILE, data)
    # هنا المفروض تكافئ الاثنين في points.json (محاكاة حالياً)
    return jsonify({'ok': True, 'message': 'تم تسجيل الإحالة'})

# Feedback/Reviews endpoint - sends to Discord webhook
FEEDBACK_WEBHOOK_URL = 'https://discord.com/api/webhooks/1427961929145651332/apIkIXgrbe4ZM0k8ouMIIPBDeY5Q2Xs3Q5im8S8JFbtKguIDY7YfbG1hTOreR8Was3DR'

@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    payload = request.json or {}
    name = payload.get('name', 'مجهول').strip()
    feedback = payload.get('feedback', '').strip()
    rating = payload.get('rating', 0)
    feedback_type = payload.get('type', 'general')
    
    if not feedback:
        return jsonify({'ok': False, 'error': 'الرجاء كتابة رأيك'}), 400
    
    if len(feedback) > 1000:
        return jsonify({'ok': False, 'error': 'الرأي طويل جداً (الحد الأقصى 1000 حرف)'}), 400
    
    # Type labels and colors
    type_info = {
        'general': {'label': '💬 رأي عام', 'color': 5814783},
        'bug': {'label': '🐛 تقرير مشكلة', 'color': 15548997},
        'feature': {'label': '💡 اقتراح ميزة', 'color': 5763719},
        'support': {'label': '🆘 طلب دعم', 'color': 15844367}
    }
    
    type_data = type_info.get(feedback_type, type_info['general'])
    
    # Prepare Discord embed
    stars = '⭐' * min(int(rating), 5) if rating else 'بدون تقييم'
    embed = {
        "title": f"{type_data['label']} - رأي جديد من الموقع",
        "color": type_data['color'],
        "fields": [
            {"name": "👤 الاسم", "value": name, "inline": True},
            {"name": "⭐ التقييم", "value": stars, "inline": True},
            {"name": "💬 الرأي", "value": feedback, "inline": False}
        ],
        "footer": {"text": "موقع سكرو - صفحة الآراء"},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        response = requests.post(
            FEEDBACK_WEBHOOK_URL,
            json={"embeds": [embed]},
            timeout=5
        )
        if response.status_code in [200, 204]:
            return jsonify({'ok': True, 'message': 'شكراً لك! تم إرسال رأيك بنجاح 🎉'})
        else:
            logging.error(f'Webhook failed: {response.status_code} - {response.text}')
            return jsonify({'ok': False, 'error': 'فشل إرسال الرأي'}), 500
    except Exception as e:
        logging.error(f'Webhook error: {e}')
        return jsonify({'ok': False, 'error': 'خطأ في الاتصال'}), 500

# ------------------ OAuth2 Flow ------------------
@app.route('/auth/discord/login')
def discord_login():
    if not DISCORD_CLIENT_ID:
        return 'خادم غير مهيأ (اضبط env DISCORD_CLIENT_ID)', 500
    state = secrets.token_hex(16)
    session.permanent = True
    session['oauth_state'] = state
    session.modified = True
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': DISCORD_REDIRECT_URI,
        'scope': ' '.join(OAUTH_SCOPES),
        'state': state,
        'prompt': 'consent'
    }
    return redirect(f"{DISCORD_OAUTH_BASE}/authorize?{urlencode(params)}")

@app.route('/auth/discord/callback')
def discord_callback():
    error = request.args.get('error')
    if error:
        return f'خطأ OAuth: {error}', 400
    state = request.args.get('state')
    code = request.args.get('code')
    
    # More lenient state check
    stored_state = session.get('oauth_state')
    if not code:
        return 'لم يتم استلام code من Discord', 400
    
    if not DISCORD_CLIENT_SECRET:
        return 'خادم غير مهيأ (اضبط env DISCORD_CLIENT_SECRET)', 500
    
    token_data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'scope': ' '.join(OAUTH_SCOPES)
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    try:
        token_resp = requests.post(f'{DISCORD_OAUTH_BASE}/token', data=token_data, headers=headers)
        if token_resp.status_code != 200:
            logging.error(f'Token error: {token_resp.status_code} - {token_resp.text}')
            return f'فشل جلب التوكن ({token_resp.status_code}): {token_resp.text}', 400
        
        token_json = token_resp.json()
        access_token = token_json.get('access_token')
        if not access_token:
            return 'لا يوجد access_token', 400
        
        user_resp = requests.get(f'{DISCORD_API_BASE}/users/@me', headers={'Authorization': f'Bearer {access_token}'})
        if user_resp.status_code != 200:
            logging.error(f'User fetch error: {user_resp.status_code}')
            return f'فشل جلب المستخدم ({user_resp.status_code})', 400
        
        user = user_resp.json()
        
        # Create user data for JWT
        user_data = {
            'id': user.get('id'),
            'username': user.get('username'),
            'global_name': user.get('global_name'),
            'avatar': user.get('avatar')
        }
        
        # Create JWT token
        jwt_token = create_jwt_token(user_data)
        
        logging.info(f'User {user.get("username")} logged in successfully')
        

        # --- Save user info for leaderboard ---
        try:
            users_db = load_json(USERS_FILE, {})
            user_id = str(user_data['id'])
            
            # Save/update user info with username and avatar
            users_db[user_id] = {
                'username': user_data.get('global_name') or user_data.get('username'),
                'avatar': user_data.get('avatar'),
                'last_login': datetime.utcnow().isoformat()
            }
            save_json(USERS_FILE, users_db)
            
            # Check if new user for referral tracking
            is_new_user = user_id not in users_db

            # Check for referral in session
            inviter_id = session.pop('referral_from', None)
            if is_new_user and inviter_id and inviter_id != str(user_data['id']):
                # Prevent self-referral
                referrals = load_json(REFERRALS_FILE, {})
                key = f'{inviter_id}:{user_data["id"]}'
                if key not in referrals:
                    # Reward inviter with 100 points = 10 credits (guild_id=0 for global)
                    points = load_json(POINTS_FILE, {})
                    guild_id = '0'
                    if guild_id not in points:
                        points[guild_id] = {}
                    inviter_entry = points[guild_id].get(inviter_id)
                    if not inviter_entry:
                        inviter_entry = {'points': 0, 'wins': 0, 'games': 0, 'best': 0, 'total_score': 0}
                    inviter_entry['points'] += 100  # 100 points = 10 credits
                    # Save back
                    points[guild_id][inviter_id] = inviter_entry
                    save_json(POINTS_FILE, points)
                    # Log referral
                    referrals[key] = {'ts': int(time.time()), 'reward': 100}
                    save_json(REFERRALS_FILE, referrals)
                    logging.info(f"✅ Referral: {inviter_id} invited {user_data['id']} (100 points = 10 credits awarded)")
        except Exception as e:
            logging.warning(f"Failed referral logic: {e}")

        # Create response and set JWT token in cookie
        response = make_response(redirect('/dashboard'))
        response.set_cookie(
            'auth_token', 
            jwt_token, 
            max_age=60*60*24*7,  # 7 days
            secure=False,  # Set to False for debugging (change to True in production with HTTPS)
            httponly=False,  # Allow JS access
            samesite='Lax',
            path='/'
        )
        return response
        
    except Exception as e:
        logging.error(f'Callback error: {str(e)}')
        return f'خطأ في معالجة OAuth: {str(e)}', 500

@app.route('/auth/logout')
def auth_logout():
    # Clear server-side session (fallback)
    session.clear()
    # Clear JWT cookies on client
    response = make_response(redirect('/'))
    response.set_cookie('auth_token', '', expires=0, path='/', samesite='Lax')
    response.set_cookie('user_logged_in', '', expires=0, path='/', samesite='Lax')
    return response

@app.route('/api/auth/me')
def auth_me():
    user = get_user_from_request()
    if not user:
        return jsonify({'authenticated': False})
    return jsonify({'authenticated': True, 'user': user})

# ---- Discord OAuth (مبسطة - تحتاج استكمال) ----
@app.route('/health')
def health():
    return jsonify({'ok': True, 'time': int(time.time())})

############### Frontend Serving ###############

@app.route('/')
def serve_index():
    # Always show splash screen on fresh visits (session-based, not persistent cookie)
    if not session.get('splash_shown_this_session'):
        return send_from_directory(BASE_DIR, 'splash.html')
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/home')
def serve_home():
    # Mark splash as shown for this session only (cleared when browser closes)
    session['splash_shown_this_session'] = True
    session.permanent = False  # Session expires when browser closes
    response = make_response(send_from_directory(BASE_DIR, 'index.html'))
    return response

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory(BASE_DIR, 'dashboard.html')

@app.route('/invite')
def invite():
    """Handle referral invitation links"""
    ref = request.args.get('ref')
    if not ref:
        # No referral code, redirect to home
        return redirect(url_for('serve_index'))
    
    # Store referral code in session for tracking when user logs in
    session['referral_from'] = ref
    session.permanent = True
    
    # Redirect to Discord login to complete the referral
    return redirect(url_for('discord_login'))

@app.route('/<path:filename>')
def serve_static_files(filename):
    # Serve files (css, js, images). Security: prevent directory traversal.
    safe_path = os.path.normpath(os.path.join(BASE_DIR, filename))
    if not safe_path.startswith(BASE_DIR):
        return 'Not allowed', 403
    if os.path.isfile(safe_path):
        directory = os.path.dirname(safe_path)
        fname = os.path.basename(safe_path)
        return send_from_directory(directory, fname)
    return 'Not Found', 404

# --- Error Handlers & Security ---
from collections import defaultdict
from time import time as current_time

request_counts = defaultdict(list)

@app.before_request
def check_rate_limit():
    """Simple rate limiting - 100 requests per minute per IP"""
    ip = request.remote_addr
    now = current_time()
    
    # Clean old requests
    request_counts[ip] = [t for t in request_counts[ip] if now - t < 60]
    
    # Check limit
    if len(request_counts[ip]) > 100:
        send_security_alert('suspicious', f'تجاوز حد الطلبات من IP: {ip}', {
            'Requests': len(request_counts[ip]),
            'Limit': '100/minute'
        })
        return jsonify({'ok': False, 'error': 'تجاوزت حد الطلبات المسموح'}), 429
    
    request_counts[ip].append(now)

@app.errorhandler(400)
def bad_request(e):
    send_security_alert('warning', 'طلب غير صالح (400)', {'Error': str(e)})
    return jsonify({'ok': False, 'error': 'طلب غير صالح'}), 400

@app.errorhandler(401)
def unauthorized(e):
    send_security_alert('warning', 'محاولة وصول غير مصرح (401)', {'Error': str(e)})
    return jsonify({'ok': False, 'error': 'غير مصرح'}), 401

@app.errorhandler(403)
def forbidden(e):
    send_security_alert('suspicious', 'محاولة وصول محظور (403)', {'Error': str(e)})
    return jsonify({'ok': False, 'error': 'محظور'}), 403

@app.errorhandler(404)
def not_found(e):
    # Don't alert for common 404s
    if not request.path.endswith(('.ico', '.map', '.txt', '.xml', '.json')):
        send_security_alert('info', f'صفحة غير موجودة: {request.path}')
    return jsonify({'ok': False, 'error': 'غير موجود'}), 404

@app.errorhandler(500)
def internal_error(e):
    send_security_alert('error', 'خطأ داخلي في الخادم (500)', {'Error': str(e)})
    return jsonify({'ok': False, 'error': 'خطأ في الخادم'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    send_security_alert('error', f'استثناء غير متوقع: {type(e).__name__}', {'Error': str(e)})
    logging.error(f'Unhandled exception: {e}', exc_info=True)
    return jsonify({'ok': False, 'error': 'حدث خطأ غير متوقع'}), 500

if __name__ == '__main__':
    # Get port from environment variable (for production hosting)
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running in production
    is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RENDER')
    
    print(f'Starting Flask server on port {port}')
    print(f'Environment: {"Production" if is_production else "Development"}')
    
    try:
        from waitress import serve
        print('🚀 Using Waitress WSGI server for better stability')
        serve(app, host='0.0.0.0', port=port, threads=6)
    except ImportError:
        print('⚠️ Waitress not found, falling back to Flask dev server')
        app.run(host='0.0.0.0', port=port, debug=not is_production)
