import os
import json
import time
import secrets
import logging
from dotenv import load_dotenv
from urllib.parse import urlencode
import requests
from flask import Flask, jsonify, session, redirect, request, url_for, make_response, send_from_directory
from datetime import timedelta

load_dotenv()  # Load .env if exists


app = Flask(__name__)
app.secret_key = os.getenv('WEB_SECRET_KEY', 'dev-secret-change')
app.permanent_session_lifetime = timedelta(days=7)
# --- Cookie settings for custom domain/HTTPS ---
app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Use 'data' folder instead of 'كروت سكرو' for website deployment
DATA_DIR = os.path.join(BASE_DIR, 'data')
POINTS_FILE = os.path.join(DATA_DIR, 'points.json')
VIP_FILE = os.path.join(DATA_DIR, 'vip_members.json')
SERVERS_FILE = os.path.join(DATA_DIR, 'servers.json')
REFERRALS_FILE = os.path.join(DATA_DIR, 'referrals.json')

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Discord OAuth Config (env vars)
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:5000/auth/discord/callback')

# Debug: Print loaded env values (remove this in production)
print(f"🔑 CLIENT_ID loaded: {DISCORD_CLIENT_ID}")
print(f"🔐 CLIENT_SECRET loaded: {'***' + (DISCORD_CLIENT_SECRET[-4:] if DISCORD_CLIENT_SECRET else 'None')}")
print(f"🔗 REDIRECT_URI: {DISCORD_REDIRECT_URI}")
DISCORD_OAUTH_BASE = 'https://discord.com/api/oauth2'
DISCORD_API_BASE = 'https://discord.com/api'

OAUTH_SCOPES = ['identify', 'guilds']

# --- Helpers ---

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
    return jsonify({
        'guild_count': guild_count
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
    session['oauth_state'] = state
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
    if not code or not state or state != session.get('oauth_state'):
        return 'State غير صالح', 400
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
    token_resp = requests.post(f'{DISCORD_OAUTH_BASE}/token', data=token_data, headers=headers)
    if token_resp.status_code != 200:
        return f'فشل جلب التوكن ({token_resp.status_code})', 400
    token_json = token_resp.json()
    access_token = token_json.get('access_token')
    if not access_token:
        return 'لا يوجد access_token', 400
    user_resp = requests.get(f'{DISCORD_API_BASE}/users/@me', headers={'Authorization': f'Bearer {access_token}'})
    if user_resp.status_code != 200:
        return 'فشل جلب المستخدم', 400
    user = user_resp.json()
    # Store minimal user info in session
    session['user'] = {
        'id': user.get('id'),
        'username': user.get('username'),
        'global_name': user.get('global_name'),
        'avatar': user.get('avatar')
    }
    session['access_token'] = access_token
    return redirect('/')

@app.route('/auth/logout')
def auth_logout():
    session.clear()
    return redirect('/')

@app.route('/api/auth/me')
def auth_me():
    user = session.get('user')
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
