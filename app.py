# TODO: ARCHITECTURE #15 - Mixed concerns in app.py
#   This file handles too many responsibilities. Consider separating into:
#   - app.py                  - Flask app factory and minimal configuration
#   - socketio_handlers.py    - All SocketIO event handlers (connect, disconnect, DMs, etc.)
#   - middleware.py           - Security headers, CSRF, request hooks
#   - startup.py              - Database initialization, index creation, readiness checks
#   This would improve testability and maintainability.

# TODO: ARCHITECTURE #14 - No API versioning
#   Add API versioning (e.g., /api/v1/...) to allow backward-compatible changes.
#   Options: URL prefix versioning, header-based versioning, or query param versioning.
#   Consider using Flask blueprints with versioned prefixes like:
#     app.register_blueprint(api_v1_bp, url_prefix='/api/v1')

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file FIRST

from flask import Flask, redirect, session, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from routes import init_routes
from models import init_models
from utils.database import init_db
from config import Config
import os, logging
from utils.auth_helpers import generate_csrf_token
from utils.content_filter import contains_blocked_content, sanitize_message

# Optional: Flask-Mail for email functionality
try:
    from flask_mail import Mail
    MAIL_AVAILABLE = True
except ImportError:
    MAIL_AVAILABLE = False
    Mail = None

def _is_production_env() -> bool:
    return (Config.ENV or '').strip().lower() == 'production'


def _runtime_readiness_checks() -> None:
    """Log actionable configuration warnings without crashing startup."""
    issues = []

    if _is_production_env() and not os.getenv('SECRET_KEY'):
        issues.append('SECRET_KEY is not set in environment; generated fallback will rotate on restart')

    if _is_production_env() and not Config.SESSION_COOKIE_SECURE:
        issues.append('SESSION_COOKIE_SECURE is False in production; set SESSION_COOKIE_SECURE=true for HTTPS deployments')

    if _is_production_env() and Config.RATELIMIT_STORAGE_URI.startswith('memory://'):
        issues.append('RATELIMIT_STORAGE_URI uses memory backend in production (set Redis for multi-instance consistency)')

    ai_keys = ('GEMINI_API_KEY', 'OPENAI_API_KEY', 'GROQ_API_KEY', 'DEEPSEEK_API_KEY')
    if not any(os.getenv(k, '').strip() for k in ai_keys):
        issues.append('No AI provider key configured; chatbot will use local fallback responses')

    if not os.getenv('MONGODB_URI', '').strip():
        issues.append('MONGODB_URI is missing; database startup may fail')

    if issues:
        for issue in issues:
            log.warning('Readiness: %s', issue)
    else:
        log.info('Readiness: all core runtime checks passed')

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
#  ERROR MONITORING (Sentry Integration)
# ═══════════════════════════════════════════════════════════════════════════════
# TODO: Enable Sentry for production error tracking and performance monitoring.
# To enable:
#   1. pip install sentry-sdk[flask]
#   2. Set SENTRY_DSN environment variable with your project's DSN
#   3. Uncomment the initialization code below
#
# Benefits:
#   - Real-time error alerts with full stack traces
#   - Performance monitoring and slow endpoint detection
#   - Release tracking and deployment notifications
#   - User context for debugging student-specific issues
#
# if Config.SENTRY_DSN:
#     import sentry_sdk
#     from sentry_sdk.integrations.flask import FlaskIntegration
#     from sentry_sdk.integrations.logging import LoggingIntegration
#
#     sentry_sdk.init(
#         dsn=Config.SENTRY_DSN,
#         environment=Config.SENTRY_ENVIRONMENT,
#         integrations=[
#             FlaskIntegration(transaction_style='url'),
#             LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
#         ],
#         traces_sample_rate=Config.SENTRY_TRACES_SAMPLE_RATE,
#         profiles_sample_rate=Config.SENTRY_PROFILES_SAMPLE_RATE,
#         send_default_pii=False,  # Don't send personally identifiable information
#     )
#     log.info('Sentry error monitoring initialized (env=%s)', Config.SENTRY_ENVIRONMENT)

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
from utils.rate_limit import limiter
# For older versions of flask_limiter, we might need to set storage options differently
# Limiter(app=...) was deprecated, init_app is standard, but storage_uri cannot always be passed to init_app.
# So we can set the app config directly before init.
app.config['RATELIMIT_STORAGE_URL'] = Config.RATELIMIT_STORAGE_URI
# Also support the newer configuration standard string:
app.config['RATELIMIT_STORAGE_URI'] = Config.RATELIMIT_STORAGE_URI

limiter.init_app(app)
app.limiter = limiter

# ── Email ──
mail = None
if MAIL_AVAILABLE:
    mail = Mail(app)
    log.info('Flask-Mail initialized for email functionality')
else:
    log.warning('Flask-Mail not installed; email functionality disabled')

# ── SocketIO ──
_cors_origins = os.getenv('CORS_ORIGINS', '').strip()
if _cors_origins:
    cors_allowed = _cors_origins.split(',')
elif _is_production_env():
    # In production, don't allow wildcard CORS — require explicit config
    cors_allowed = []
    log.warning('CORS_ORIGINS not set in production; SocketIO will reject cross-origin requests')
else:
    cors_allowed = '*'  # Dev convenience
# TODO: ARCHITECTURE #13 - async_mode='threading' doesn't scale for production.
#   For high-concurrency production deployments, switch to:
#     async_mode='eventlet' (pip install eventlet) or
#     async_mode='gevent' (pip install gevent-websocket)
#   and use a production WSGI server (gunicorn with eventlet/gevent worker).
#   Threading mode is acceptable for low-traffic or development scenarios.
socketio = SocketIO(app, cors_allowed_origins=cors_allowed, async_mode='threading',
                    logger=False, engineio_logger=False)

# ── MongoDB ──
init_db()
init_models()
init_routes(app)
_runtime_readiness_checks()

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

@app.before_request
def ensure_csrf_token():
    if 'csrf_token' not in session:
        generate_csrf_token()

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

    # SECURITY NOTE #7: 'unsafe-inline' in CSP for scripts and styles
    # This is a known limitation due to extensive use of inline scripts and styles
    # in Jinja2 templates throughout the application. Removing 'unsafe-inline' would
    # require refactoring all templates to use external JS/CSS files or implementing
    # a nonce-based approach.
    #
    # TODO: Implement nonce-based CSP for better security:
    #   1. Generate a unique nonce per request: nonce = secrets.token_urlsafe(16)
    #   2. Pass nonce to templates via context processor
    #   3. Add nonce="{{nonce}}" to all inline <script> and <style> tags
    #   4. Update CSP to use 'nonce-{{nonce}}' instead of 'unsafe-inline'
    #   5. Remove 'unsafe-inline' from script-src and style-src
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
# NOTE #30 (SCALABILITY): This function creates indexes that may overlap with
# _ensure_indexes() in utils/database.py. MongoDB's create_index is idempotent
# (creates only if not exists), so duplicate calls are safe but wasteful.
# The _safe_create_index wrapper handles IndexOptionsConflict gracefully.
# Future optimization: Use a startup flag or migration system to run index
# creation only once per deployment, not on every server restart.
_INDEXES_ENSURED = False  # Module-level flag to track if indexes were already created

def ensure_production_indexes():
    """Create optimized indexes for production queries.

    This function is idempotent - indexes are only created if they don't exist.
    Uses a module-level flag to avoid redundant index checks on every startup
    when running multiple workers or during hot reloads.
    """
    global _INDEXES_ENSURED
    if _INDEXES_ENSURED:
        log.debug('Production indexes already ensured this session, skipping')
        return

    try:
        from pymongo.errors import OperationFailure
        from utils.database import get_db
        db = get_db()

        def _safe_create_index(collection, keys, **kwargs):
            """Ignore index-name conflicts when equivalent indexes already exist."""
            try:
                collection.create_index(keys, **kwargs)
            except OperationFailure as e:
                if getattr(e, 'code', None) == 85:  # IndexOptionsConflict
                    log.info('Index already exists with different name on %s (%s)', collection.name, kwargs.get('name', 'unnamed'))
                    return
                if getattr(e, 'code', None) == 11000:  # DuplicateKey
                    log.warning('Skipped unique index on %s (%s) due to existing duplicate data', collection.name, kwargs.get('name', 'unnamed'))
                    return
                raise
        
        # Proctor-related indexes
        _safe_create_index(db['risk_incidents'], [('status', 1), ('risk_level', -1), ('timestamp', -1)], name='queue_view', background=True)
        _safe_create_index(db['risk_incidents'], [('timestamp', -1), ('status', 1)], name='time_filter', background=True)
        _safe_create_index(db['risk_incidents'], [('anonymous_student_id', 1)], name='student_lookup', background=True)
        _safe_create_index(db['proctor_actions'], [('timestamp', -1)], name='audit_timeline', background=True)
        _safe_create_index(db['proctor_actions'], [('incident_id', 1)], name='incident_actions', background=True)
        _safe_create_index(db['proctor_actions'], [('proctor_id', 1), ('timestamp', -1)], name='proctor_activity', background=True)
        
        # Phase 4: Student wellness indexes
        _safe_create_index(db['student_wellness'], [('student_id', 1), ('timestamp', -1)], name='wellness_timeline', background=True)
        _safe_create_index(db['student_wellness'], [('student_id', 1), ('data_type', 1)], name='wellness_by_type', background=True)
        _safe_create_index(db['support_requests'], [('student_id', 1), ('timestamp', -1)], name='support_timeline', background=True)
        
        # Connect Hub indexes
        _safe_create_index(db['connections'], [('user_email', 1), ('connected_to', 1)], name='conn_pair', unique=True, background=True)
        _safe_create_index(db['connections'], [('connected_to', 1), ('status', 1)], name='conn_incoming', background=True)
        _safe_create_index(db['connections'], [('user_email', 1), ('status', 1)], name='conn_outgoing', background=True)
        _safe_create_index(db['groups'], [('group_id', 1)], name='group_id_uniq', unique=True, background=True)
        _safe_create_index(db['groups'], [('members', 1)], name='group_members', background=True)
        _safe_create_index(db['groups'], [('type', 1)], name='group_type', background=True)
        _safe_create_index(db['events'], [('event_id', 1)], name='event_id_uniq', unique=True, background=True)
        _safe_create_index(db['events'], [('date', 1)], name='event_date', background=True)
        _safe_create_index(db['resources'], [('resource_id', 1)], name='resource_id_uniq', unique=True, background=True)
        _safe_create_index(db['resources'], [('tags', 1)], name='resource_tags', background=True)
        _safe_create_index(db['resources'], [('created_at', -1)], name='resource_recent', background=True)
        _safe_create_index(db['hub_activity'], [('user_email', 1)], name='hub_act_user', unique=True, background=True)
        _safe_create_index(db['hub_activity'], [('last_active', 1)], name='hub_act_time', background=True)

        # Connect Hub v2 — chat, feed, notifications
        _safe_create_index(db['peer_messages'], [('from_email', 1), ('to_email', 1), ('created_at', -1)], name='dm_pair', background=True)
        _safe_create_index(db['peer_messages'], [('to_email', 1), ('seen', 1)], name='dm_unread', background=True)
        _safe_create_index(db['group_messages'], [('group_id', 1), ('created_at', -1)], name='gchat_group', background=True)
        _safe_create_index(db['hub_feed'], [('created_at', -1)], name='feed_recent', background=True)
        _safe_create_index(db['hub_notifications'], [('user_email', 1), ('created_at', -1)], name='notif_user', background=True)
        _safe_create_index(db['hub_notifications'], [('user_email', 1), ('read', 1)], name='notif_unread', background=True)

        # Audit logging indexes
        _safe_create_index(db['proctor_activity_logs'], [('timestamp', -1)], name='audit_log_time', background=True)
        _safe_create_index(db['proctor_activity_logs'], [('proctor_email', 1), ('timestamp', -1)], name='audit_log_proctor', background=True)
        _safe_create_index(db['proctor_activity_logs'], [('action', 1), ('timestamp', -1)], name='audit_log_action', background=True)

        _INDEXES_ENSURED = True  # Mark indexes as created for this process
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
    checks = {
        'app': 'ok',
        'env': Config.ENV,
        'limiter_backend': (Config.RATELIMIT_STORAGE_URI or 'memory://').split(':', 1)[0],
        'ai_configured': {
            'gemini': bool(os.getenv('GEMINI_API_KEY', '').strip()),
            'openai': bool(os.getenv('OPENAI_API_KEY', '').strip()),
            'groq': bool(os.getenv('GROQ_API_KEY', '').strip()),
            'deepseek': bool(os.getenv('DEEPSEEK_API_KEY', '').strip()),
        },
    }
    status = 200
    try:
        from utils.database import get_db
        db = get_db()
        db.command('ping')
        checks['mongodb'] = 'ok'
    except Exception as e:
        checks['mongodb'] = f'error: {e}'
        status = 503

    # AI provider connectivity check (non-blocking - does not affect overall status)
    # This verifies API key validity and network connectivity to AI services
    checks['ai_health'] = _check_ai_provider_health()

    checks['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    return jsonify(checks), status


def _check_ai_provider_health():
    """
    Perform a lightweight connectivity check for the first available AI provider.
    Returns status dict. Does not block health check if AI is unavailable.
    """
    import time
    result = {'status': 'unconfigured', 'provider': None, 'latency_ms': None}

    # Check Gemini first (primary provider)
    gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
    if gemini_key:
        try:
            from google.genai import Client
            start = time.time()
            test_client = Client(api_key=gemini_key)
            # List models is a lightweight API call to verify connectivity
            models = test_client.models.list()
            # Just access the iterator to verify the call works
            next(iter(models), None)
            latency = int((time.time() - start) * 1000)
            return {'status': 'ok', 'provider': 'gemini', 'latency_ms': latency}
        except Exception as e:
            result = {'status': f'error: {str(e)[:100]}', 'provider': 'gemini', 'latency_ms': None}
            # Continue to try other providers

    # Check Groq (fast free alternative)
    groq_key = os.getenv('GROQ_API_KEY', '').strip()
    if groq_key and result['status'] != 'ok':
        try:
            from groq import Groq
            start = time.time()
            test_client = Groq(api_key=groq_key)
            test_client.models.list()
            latency = int((time.time() - start) * 1000)
            return {'status': 'ok', 'provider': 'groq', 'latency_ms': latency}
        except Exception as e:
            if result['status'] == 'unconfigured':
                result = {'status': f'error: {str(e)[:100]}', 'provider': 'groq', 'latency_ms': None}

    # Check DeepSeek
    deepseek_key = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if deepseek_key and result['status'] != 'ok':
        try:
            from openai import OpenAI
            start = time.time()
            test_client = OpenAI(api_key=deepseek_key, base_url='https://api.deepseek.com')
            test_client.models.list()
            latency = int((time.time() - start) * 1000)
            return {'status': 'ok', 'provider': 'deepseek', 'latency_ms': latency}
        except Exception as e:
            if result['status'] == 'unconfigured':
                result = {'status': f'error: {str(e)[:100]}', 'provider': 'deepseek', 'latency_ms': None}

    # Check OpenAI (last resort)
    openai_key = os.getenv('OPENAI_API_KEY', '').strip()
    if openai_key and result['status'] != 'ok':
        try:
            from openai import OpenAI
            start = time.time()
            test_client = OpenAI(api_key=openai_key)
            test_client.models.list()
            latency = int((time.time() - start) * 1000)
            return {'status': 'ok', 'provider': 'openai', 'latency_ms': latency}
        except Exception as e:
            if result['status'] == 'unconfigured':
                result = {'status': f'error: {str(e)[:100]}', 'provider': 'openai', 'latency_ms': None}

    return result

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

    email = s.get('user_email', '')
    if not email:
        return
    peer = data.get('to', '')
    raw_text = (data.get('message', '') or '').strip()
    if not raw_text or len(raw_text) > 500 or not peer:
        return

    # Sanitize message (HTML escape) and check for blocked content
    text = sanitize_message(raw_text)
    if text is None:
        return

    if contains_blocked_content(raw_text):
        emit('dm_error', {'error': 'Inappropriate content'})
        return

    db = get_db()
    # Check connection exists
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

    name = (s.get('user_name') or email.split('@')[0] or 'User').split()[0]
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

    email = s.get('user_email', '')
    if not email:
        return
    gid = data.get('group_id', '')
    raw_text = (data.get('message', '') or '').strip()
    if not raw_text or len(raw_text) > 500 or not gid:
        return

    # Sanitize message (HTML escape) and check for blocked content
    text = sanitize_message(raw_text)
    if text is None:
        return

    if contains_blocked_content(raw_text):
        emit('group_error', {'error': 'Inappropriate content'})
        return

    db = get_db()
    g = db['groups'].find_one({'group_id': gid})
    if not g or email not in g.get('members', []):
        emit('group_error', {'error': 'Not a member'})
        return

    now = datetime.utcnow()
    name = (s.get('user_name') or email.split('@')[0] or 'User').split()[0]
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
