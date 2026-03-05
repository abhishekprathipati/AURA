from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file FIRST

from flask import Flask, redirect, session, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room, leave_room
from routes import init_routes
from flask_mail import Mail
from models import init_models
from utils.database import init_db
from config import Config
import os, logging

# ═══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger('aura')

# ═══════════════════════════════════════════════════════════════════════════════
#  APP FACTORY
# ═══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = app.config['SECRET_KEY']

# ── Reverse-proxy header trust (nginx / caddy / load-balancer) ──
if Config.PROXY_FIX_ENABLED:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=Config.PROXY_FIX_X_FOR,
        x_proto=Config.PROXY_FIX_X_PROTO,
        x_host=Config.PROXY_FIX_X_HOST,
    )
    log.info('ProxyFix enabled (x_for=%s, x_proto=%s, x_host=%s)',
             Config.PROXY_FIX_X_FOR, Config.PROXY_FIX_X_PROTO, Config.PROXY_FIX_X_HOST)

# ── Rate limiter (memory in dev, Redis in prod) ──
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=Config.RATELIMIT_STORAGE_URI,
)
app.limiter = limiter

# ── Email ──
mail = Mail(app)

# ── SocketIO ──
_cors_origins = os.getenv('CORS_ORIGINS', '').strip()
cors_allowed = _cors_origins.split(',') if _cors_origins else '*'
socketio = SocketIO(app, cors_allowed_origins=cors_allowed, async_mode='threading',
                    logger=False, engineio_logger=False)

# ── MongoDB ──
init_db()
init_models()
init_routes(app)
log.info('App initialised  (env=%s, debug=%s, limiter=%s)',
         Config.ENV, Config.DEBUG, Config.RATELIMIT_STORAGE_URI)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════════════════════
@app.after_request
def add_security_headers(response):
    h = response.headers
    h['X-Content-Type-Options'] = 'nosniff'
    h['X-Frame-Options'] = 'DENY'
    h['X-XSS-Protection'] = '1; mode=block'
    h['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    h['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    h['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    h['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.socket.io 'unsafe-inline'; "
        "style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
    )

    # Static asset caching: aggressive in prod, no-cache in dev
    if response.mimetype in ('text/css', 'application/javascript', 'image/svg+xml'):
        if Config.DEBUG:
            h['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        else:
            h['Cache-Control'] = 'public, max-age=2592000, immutable'  # 30 days

    return response

# Ensure indexes on startup
def ensure_production_indexes():
    """Create optimized indexes for production queries."""
    try:
        from utils.database import get_db
        db = get_db()
        
        # Proctor-related indexes
        db['risk_incidents'].create_index([('status', 1), ('risk_level', -1), ('timestamp', -1)], name='queue_view', background=True)
        db['risk_incidents'].create_index([('timestamp', -1), ('status', 1)], name='time_filter', background=True)
        db['risk_incidents'].create_index([('anonymous_student_id', 1)], name='student_lookup', background=True)
        db['proctor_actions'].create_index([('timestamp', -1)], name='audit_timeline', background=True)
        db['proctor_actions'].create_index([('incident_id', 1)], name='incident_actions', background=True)
        db['proctor_actions'].create_index([('proctor_id', 1), ('timestamp', -1)], name='proctor_activity', background=True)
        
        # Phase 4: Student wellness indexes
        db['student_wellness'].create_index([('student_id', 1), ('timestamp', -1)], name='wellness_timeline', background=True)
        db['student_wellness'].create_index([('student_id', 1), ('data_type', 1)], name='wellness_by_type', background=True)
        db['support_requests'].create_index([('student_id', 1), ('timestamp', -1)], name='support_timeline', background=True)
        
        # Connect Hub indexes
        db['connections'].create_index([('user_email', 1), ('connected_to', 1)], name='conn_pair', unique=True, background=True)
        db['connections'].create_index([('connected_to', 1), ('status', 1)], name='conn_incoming', background=True)
        db['connections'].create_index([('user_email', 1), ('status', 1)], name='conn_outgoing', background=True)
        db['groups'].create_index([('group_id', 1)], name='group_id_uniq', unique=True, background=True)
        db['groups'].create_index([('members', 1)], name='group_members', background=True)
        db['groups'].create_index([('type', 1)], name='group_type', background=True)
        db['events'].create_index([('event_id', 1)], name='event_id_uniq', unique=True, background=True)
        db['events'].create_index([('date', 1)], name='event_date', background=True)
        db['resources'].create_index([('resource_id', 1)], name='resource_id_uniq', unique=True, background=True)
        db['resources'].create_index([('tags', 1)], name='resource_tags', background=True)
        db['resources'].create_index([('created_at', -1)], name='resource_recent', background=True)
        db['hub_activity'].create_index([('user_email', 1)], name='hub_act_user', unique=True, background=True)
        db['hub_activity'].create_index([('last_active', 1)], name='hub_act_time', background=True)

        # Connect Hub v2 — chat, feed, notifications
        db['peer_messages'].create_index([('from_email', 1), ('to_email', 1), ('created_at', -1)], name='dm_pair', background=True)
        db['peer_messages'].create_index([('to_email', 1), ('seen', 1)], name='dm_unread', background=True)
        db['group_messages'].create_index([('group_id', 1), ('created_at', -1)], name='gchat_group', background=True)
        db['hub_feed'].create_index([('created_at', -1)], name='feed_recent', background=True)
        db['hub_notifications'].create_index([('user_email', 1), ('created_at', -1)], name='notif_user', background=True)
        db['hub_notifications'].create_index([('user_email', 1), ('read', 1)], name='notif_unread', background=True)

        # Audit logging indexes
        db['proctor_activity_logs'].create_index([('timestamp', -1)], name='audit_log_time', background=True)
        db['proctor_activity_logs'].create_index([('proctor_email', 1), ('timestamp', -1)], name='audit_log_proctor', background=True)
        db['proctor_activity_logs'].create_index([('action', 1), ('timestamp', -1)], name='audit_log_action', background=True)
        
        log.info('Production indexes ensured')
    except Exception as e:
        log.warning('Index creation warning: %s', e)

with app.app_context():
    ensure_production_indexes()

@app.route('/')
def index():
    """Root route - redirect based on login status and role."""
    if 'user_email' in session:
        role = session.get('user_role', 'student')
        if role == 'student':
            return redirect('/student/dashboard')
        elif role == 'proctor':
            return redirect('/proctor/dashboard')
        elif role == 'hod':
            return redirect('/proctor/hod')
        else:
            return redirect('/student/dashboard')
    # Check for parent session
    elif session.get('parent_logged_in'):
        return redirect('/parent/dashboard')
    return redirect('/login')


@app.route('/dashboard')
def dashboard_redirect():
    """Generic dashboard redirect based on user role."""
    if 'user_email' in session:
        role = session.get('user_role', 'student')
        if role == 'student':
            return redirect('/student/dashboard')
        elif role == 'proctor':
            return redirect('/proctor/dashboard')
        elif role == 'hod':
            return redirect('/proctor/hod')
    elif session.get('parent_logged_in'):
        return redirect('/parent/dashboard')
    return redirect('/login')

@app.route('/health')
def health():
    """Production health-check endpoint (load-balancer / uptime monitor)."""
    from datetime import datetime
    checks = {'app': 'ok'}
    status = 200
    try:
        from utils.database import get_db
        db = get_db()
        db.command('ping')
        checks['mongodb'] = 'ok'
    except Exception as e:
        checks['mongodb'] = f'error: {e}'
        status = 503
    checks['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    checks['env'] = Config.ENV
    return jsonify(checks), status

# --- Error handlers ---
@app.errorhandler(404)
def not_found(e):
    if request.accept_mimetypes.best == 'application/json':
        return jsonify({'error': 'Not found'}), 404
    return render_template('base.html', show_nav=False, error_code=404, error_msg='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    if request.accept_mimetypes.best == 'application/json':
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('base.html', show_nav=False, error_code=500, error_msg='Something went wrong'), 500

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': str(e.description) if hasattr(e, 'description') else 'Too many requests.',
        'retry_after_seconds': 60
    }), 429, {'Retry-After': '60', 'X-RateLimit-Remaining': '0'}

@app.route('/ui/chat')
def ui_chat():
    """Render the high-end chat UI template."""
    return render_template('index.html')

# ═══════════════════════════════════════════════════════════════════════════════
#  SOCKET.IO EVENT HANDLERS — Connect Hub Real-Time
# ═══════════════════════════════════════════════════════════════════════════════

@socketio.on('connect')
def handle_connect():
    """Client connected — join personal room + role-based rooms."""
    from flask import session as s
    email = s.get('user_email')
    role = s.get('user_role', '')
    if email:
        join_room(email)                # personal room for DMs
        join_room('hub_global')          # shared feed room
        # Proctors & HOD get real-time incident alerts
        if role in ('proctor', 'hod'):
            join_room('proctor_alerts')
        try:
            from utils.database import get_db
            db = get_db()
            db['hub_activity'].update_one(
                {'user_email': email},
                {'$set': {'user_email': email, 'last_active': __import__('datetime').datetime.utcnow()}},
                upsert=True)
            emit('online_update', {'email': email, 'online': True}, room='hub_global')
        except Exception:
            pass

@socketio.on('disconnect')
def handle_disconnect():
    from flask import session as s
    email = s.get('user_email')
    role = s.get('user_role', '')
    if email:
        leave_room(email)
        leave_room('hub_global')
        if role in ('proctor', 'hod'):
            leave_room('proctor_alerts')
        emit('online_update', {'email': email, 'online': False}, room='hub_global')

@socketio.on('join_group_room')
def handle_join_group(data):
    gid = data.get('group_id', '')
    if gid:
        join_room(f'group_{gid}')

@socketio.on('leave_group_room')
def handle_leave_group(data):
    gid = data.get('group_id', '')
    if gid:
        leave_room(f'group_{gid}')

@socketio.on('typing')
def handle_typing(data):
    from flask import session as s
    email = s.get('user_email', '')
    name = s.get('user_name', email.split('@')[0])
    target_type = data.get('type', 'dm')
    target = data.get('target', '')
    if target_type == 'dm' and target:
        emit('typing_indicator', {'from': email, 'name': name, 'type': 'dm'}, room=target)
    elif target_type == 'group' and target:
        emit('typing_indicator', {'from': email, 'name': name, 'type': 'group', 'group_id': target}, room=f'group_{target}', include_self=False)

@socketio.on('send_dm')
def handle_send_dm(data):
    """Real-time DM — saves to DB + emits to recipient."""
    from flask import session as s
    from utils.database import get_db
    from datetime import datetime
    import re as _re

    email = s.get('user_email', '')
    if not email:
        return
    peer = data.get('to', '')
    text = (data.get('message', '') or '').strip()
    if not text or len(text) > 500 or not peer:
        return

    db = get_db()
    # Check connection + profanity + rate limit
    BLOCKED = ['abuse','hate','spam','inappropriate','offensive','harassment','violence','threat','kill','harm']
    if _re.search(r'\b(?:' + '|'.join(_re.escape(w) for w in BLOCKED) + r')\b', text.lower()):
        emit('dm_error', {'error': 'Inappropriate content'})
        return
    conn = db['connections'].find_one({'$or': [
        {'user_email': email, 'connected_to': peer, 'status': 'accepted'},
        {'user_email': peer, 'connected_to': email, 'status': 'accepted'},
    ]})
    if not conn:
        emit('dm_error', {'error': 'Not connected'})
        return

    now = datetime.utcnow()
    msg_doc = {
        'from_email': email, 'to_email': peer,
        'message': text, 'seen': False, 'created_at': now,
    }
    db['peer_messages'].insert_one(msg_doc)

    name = s.get('user_name', email.split('@')[0]).split()[0]
    payload = {
        'from': email, 'to': peer, 'message': text,
        'sender_name': name, 'mine': False, 'seen': False,
        'time': now.isoformat(),
    }
    # Send to recipient's personal room
    emit('new_dm', payload, room=peer)
    # Echo back to sender as 'mine'
    payload_mine = {**payload, 'mine': True}
    emit('new_dm', payload_mine, room=email)

@socketio.on('send_group_msg')
def handle_send_group_msg(data):
    """Real-time group message — saves to DB + emits to group room."""
    from flask import session as s
    from utils.database import get_db
    from datetime import datetime
    import re as _re

    email = s.get('user_email', '')
    if not email:
        return
    gid = data.get('group_id', '')
    text = (data.get('message', '') or '').strip()
    if not text or len(text) > 500 or not gid:
        return

    db = get_db()
    g = db['groups'].find_one({'group_id': gid})
    if not g or email not in g.get('members', []):
        emit('group_error', {'error': 'Not a member'})
        return

    BLOCKED = ['abuse','hate','spam','inappropriate','offensive','harassment','violence','threat','kill','harm']
    if _re.search(r'\b(?:' + '|'.join(_re.escape(w) for w in BLOCKED) + r')\b', text.lower()):
        emit('group_error', {'error': 'Inappropriate content'})
        return

    now = datetime.utcnow()
    name = s.get('user_name', email.split('@')[0]).split()[0]
    db['group_messages'].insert_one({
        'group_id': gid, 'sender_email': email,
        'sender_name': name, 'message': text, 'created_at': now,
    })

    emit('new_group_msg', {
        'group_id': gid, 'sender': email, 'sender_name': name,
        'message': text, 'time': now.isoformat(),
    }, room=f'group_{gid}')

@socketio.on('mark_dm_read')
def handle_mark_dm_read(data):
    from flask import session as s
    from utils.database import get_db
    email = s.get('user_email', '')
    peer = data.get('peer', '')
    if email and peer:
        db = get_db()
        db['peer_messages'].update_many(
            {'from_email': peer, 'to_email': email, 'seen': False},
            {'$set': {'seen': True}})
        emit('read_receipt', {'from': email, 'peer': peer}, room=peer)


if __name__ == '__main__':
    debug = Config.DEBUG
    port  = int(os.getenv('PORT', '5000'))
    host  = os.getenv('HOST', '0.0.0.0')
    log.info('Starting AURA  host=%s port=%d debug=%s', host, port, debug)
    socketio.run(app, host=host, port=port, debug=debug, use_reloader=debug,
                 allow_unsafe_werkzeug=debug)  # Werkzeug dev-server only in debug


def emit_proctor_alert(alert_data):
    """Emit a real-time alert to all connected proctors/HOD.
    Call from any route to push live notifications to the proctor dashboard.
    alert_data: dict with keys like type, risk_level, anonymous_student_id, message, incident_id
    """
    try:
        socketio.emit('proctor_alert', alert_data, room='proctor_alerts')
    except Exception as e:
        log.error('Failed to emit proctor alert: %s', e)
