@app.route('/invite')
def invite_referral():
    ref = request.args.get('ref')
    if ref and ref.isdigit():
        session['referral_inviter'] = str(ref)
        session.modified = True
    # Redirect to login (or homepage)
    return redirect('/auth/discord/login')
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

    return jsonify({
        'user_id': user_id,
        'stats': aggregated,
        'vip_tier': vip_tier
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

# Owner check endpoint
@app.route('/api/owner-check/<int:user_id>')
def api_owner_check(user_id: int):
    owner_config_file = os.path.join(DATA_DIR, 'owner_config.json')
    owner_data = load_json(owner_config_file, {'owner_ids': []})
    is_owner = user_id in owner_data.get('owner_ids', [])
    return jsonify({'is_owner': is_owner, 'user_id': user_id})

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
        

        # --- Referral reward logic ---
        try:
            users_data = load_json(USERS_FILE, {"users": []})
            users_set = set(str(u) for u in users_data.get('users', []))
            new_user = False
            if str(user_data['id']) not in users_set:
                users_set.add(str(user_data['id']))
                save_json(USERS_FILE, {"users": sorted(list(users_set))})
                new_user = True

            # Check for referral in session
            inviter_id = session.pop('referral_inviter', None)
            if new_user and inviter_id and inviter_id != str(user_data['id']):
                # Prevent self-referral
                referrals = load_json(REFERRALS_FILE, {})
                key = f'{inviter_id}:{user_data["id"]}'
                if key not in referrals:
                    # Reward inviter with 10 points (guild_id=0 for global)
                    points = load_json(POINTS_FILE, {})
                    guild_id = '0'
                    inviter_entry = points.get(guild_id, {}).get(inviter_id)
                    if not inviter_entry:
                        inviter_entry = {'points': 0, 'wins': 0, 'games': 0, 'best': 0, 'total_score': 0}
                    inviter_entry['points'] += 10
                    # Save back
                    if guild_id not in points:
                        points[guild_id] = {}
                    points[guild_id][inviter_id] = inviter_entry
                    save_json(POINTS_FILE, points)
                    # Log referral
                    referrals[key] = {'ts': int(time.time())}
                    save_json(REFERRALS_FILE, referrals)
                    logging.info(f"Referral: {inviter_id} invited {user_data['id']} (10 points awarded)")
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
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory(BASE_DIR, 'dashboard.html')

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
