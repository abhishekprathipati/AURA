import os
import logging
from aura.utils.database import get_db

log = logging.getLogger(__name__)

def run_startup_tasks(app):
    """Run required startup logic within app context."""
    _runtime_readiness_checks(app)
    ensure_production_indexes()
    
    # Start background threads if needed
    _start_otp_countdown_emitter(app)

def _runtime_readiness_checks(app):
    """Log actionable configuration warnings without crashing startup."""
    issues = []
    env = app.config.get('ENV', '').strip().lower()
    is_prod = env == 'production'

    if is_prod and not app.config.get('SECRET_KEY'):
        issues.append('SECRET_KEY is not set in environment')

    if is_prod and not app.config.get('SESSION_COOKIE_SECURE'):
        issues.append('SESSION_COOKIE_SECURE is False in production')

    if is_prod and app.config.get('RATELIMIT_STORAGE_URI', '').startswith('memory://'):
        issues.append('RATELIMIT_STORAGE_URI uses memory backend in production')

    ai_keys = ('GEMINI_API_KEY', 'OPENAI_API_KEY', 'GROQ_API_KEY', 'DEEPSEEK_API_KEY')
    if not any(app.config.get(k, '').strip() for k in ai_keys):
        issues.append('No AI provider key configured')

    if not app.config.get('MONGODB_URI', '').strip():
        issues.append('MONGODB_URI is missing')

    if issues:
        for issue in issues:
            log.warning('Readiness: %s', issue)
    else:
        log.info('Readiness: all core runtime checks passed')

_INDEXES_ENSURED = False

def ensure_production_indexes():
    """Create optimized indexes for production queries."""
    global _INDEXES_ENSURED
    if _INDEXES_ENSURED:
        return

    try:
        from pymongo.errors import OperationFailure
        db = get_db()
        if db is None:
            return

        def _safe_create_index(collection, keys, **kwargs):
            try:
                collection.create_index(keys, **kwargs)
            except OperationFailure as e:
                if getattr(e, 'code', None) == 85:  # IndexOptionsConflict
                    log.info('Index already exists with different name on %s', collection.name)
                    return
                raise
        
        # Incident and audit indexes
        _safe_create_index(db['risk_incidents'], [('status', 1), ('risk_level', -1), ('timestamp', -1)], name='queue_view', background=True)
        _safe_create_index(db['proctor_actions'], [('timestamp', -1)], name='audit_timeline', background=True)
        
        # Student wellness indexes
        _safe_create_index(db['student_wellness'], [('student_id', 1), ('timestamp', -1)], name='wellness_timeline', background=True)
        
        # Connect Hub indexes
        _safe_create_index(db['connections'], [('user_email', 1), ('connected_to', 1)], name='conn_pair', unique=True, background=True)
        _safe_create_index(db['groups'], [('members', 1)], name='group_members', background=True)
        
        # Chat, feed, notifications
        _safe_create_index(db['peer_messages'], [('from_email', 1), ('to_email', 1), ('created_at', -1)], name='dm_pair', background=True)
        _safe_create_index(db['hub_feed'], [('created_at', -1)], name='feed_recent', background=True)

        _INDEXES_ENSURED = True
        log.info('Production indexes ensured')
    except Exception as e:
        log.warning('Index creation warning: %s', e)

# Background thread logic for OTP
_countdown_thread = None
_countdown_running = False

def _start_otp_countdown_emitter(app):
    """Background thread that emits OTP countdown ticks."""
    global _countdown_thread, _countdown_running
    from aura.services.otp_timer_service import OTPTimerService
    from aura import socketio
    import threading
    import time

    if _countdown_running:
        return

    def countdown_loop():
        global _countdown_running
        while _countdown_running:
            try:
                active_phones = OTPTimerService.get_all_active_sessions()
                for phone in active_phones:
                    remaining = OTPTimerService.get_remaining_seconds(phone)
                    room_name = f'otp_{phone[-4:] if len(phone) >= 4 else phone}'
                    if remaining is not None and remaining > 0:
                        socketio.emit('otp_timer_tick', {'seconds_remaining': remaining, 'expired': False}, room=room_name)
                    else:
                        socketio.emit('otp_timer_tick', {'seconds_remaining': 0, 'expired': True}, room=room_name)
                        OTPTimerService.cancel_otp_session(phone)
                OTPTimerService.cleanup_expired_sessions()
                time.sleep(1)
            except Exception as e:
                log.error('OTP countdown emitter error: %s', e)
                time.sleep(1)

    _countdown_running = True
    _countdown_thread = threading.Thread(target=countdown_loop, daemon=True)
    _countdown_thread.start()
    log.info('OTP countdown emitter started')
