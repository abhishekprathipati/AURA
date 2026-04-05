"""
═══════════════════════════════════════════════════════════════
AURA — Rate Limiting Utilities
═══════════════════════════════════════════════════════════════
Production-grade rate limiting for proctor & API endpoints.
Strictly relies on external Redis memory (via Flask-Limiter) 
to ensure consistent limits across multiple Gunicorn workers.
"""
from flask import jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ─── Named limit strings ──────────────────────────────────
class Limits:
    """Centralised rate-limit strings (Flask-Limiter format)."""
    STRICT   = "5 per minute"       # auth / destructive
    MODERATE = "30 per minute"      # writes
    STANDARD = "60 per minute"      # reads
    RELAXED  = "120 per minute"     # page loads
    EXPORT   = "10 per minute"      # CSV exports
    BULK     = "10 per minute"      # bulk operations
    SEARCH   = "30 per minute"      # search queries

# Ensure we use headers that most load balancers and CDNs respect
def _rate_limit_error(e):
    return make_response(jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': f'Too many requests. Limit: {e.description}. Please wait and try again.',
        'retry_after_seconds': 60
    }), 429)

# Global Limiter object.
# storage_uri is provided dynamically in app.py during init_app()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    strategy="fixed-window",
)
limiter.request_filter(lambda: False) # Default pass
limiter.on_breach = _rate_limit_error

# Primary decorator override
apply_rate_limit = limiter.limit

# ─── Specialized overrides for explicit fallback removals ────
# We use the active explicit Redis store configured for Limiter
# to handle specific IP+Email rate limits across scaled workers.
from flask import current_app
import os


_memory_store = {}

def _get_redis():
    """Get Redis connection using primary REDIS_URL or fallback."""
    try:
        import redis
    except ImportError:
        raise RuntimeError(
            "'redis' package is not installed. "
            "Install it with: pip install redis"
        )
    url = os.environ.get('REDIS_URL') or current_app.config.get('RATELIMIT_STORAGE_URI') or 'redis://localhost:6379'
    if url.startswith('memory://'):
        return None
    return redis.from_url(url)

def check_login_rate(ip: str, email: str = ''):
    """
    Checks if the IP+Email combo has breached limits.
    Returns: {'allowed': bool, 'message': str}
    """
    key = f"aura:bruteforce:{ip}:{email.lower()}"
    try:
        r = _get_redis()
        if r is None:
            # Use memory fallback
            import time
            record = _memory_store.get(key)
            if record and record['expires'] > time.time():
                if record['attempts'] >= 5:
                    return {'allowed': False, 'message': 'Account locked due to too many failed attempts. Please try again in 5 minutes.'}
            elif record and record['expires'] <= time.time():
                del _memory_store[key]
            return {'allowed': True, 'message': 'OK'}

        attempts = r.get(key)
        if attempts and int(attempts) >= 5:
            return {
                'allowed': False,
                'message': 'Account locked due to too many failed attempts. Please try again in 5 minutes.'
            }
        # Success - no lockout in effect
        return {'allowed': True, 'message': 'OK'}
    except Exception as e:
        # FAIL-CLOSED: If Redis is down, we must block to prevent brute-force.
        current_app.logger.error(f"CRITICAL: Rate limit Redis check failed (Failing Closed): {e}")
        return {
            'allowed': False,
            'message': 'System security check unavailable. Please try again later.'
        }

def record_failed_login(ip: str, email: str = ''):
    key = f"aura:bruteforce:{ip}:{email.lower()}"
    try:
        r = _get_redis()
        if r is None:
            import time
            record = _memory_store.get(key, {'attempts': 0, 'expires': time.time() + 300})
            record['attempts'] += 1
            record['expires'] = time.time() + 300
            _memory_store[key] = record
            return

        r.incr(key)
        r.expire(key, 300) # 5 minutes lockout
    except Exception as e:
        current_app.logger.warning(f"Failed to record login attempt: {e}")

def clear_login_attempts(ip: str, email: str = ''):
    key = f"aura:bruteforce:{ip}:{email.lower()}"
    try:
        r = _get_redis()
        if r is None:
            if key in _memory_store:
                del _memory_store[key]
            return

        r.delete(key)
    except Exception as e:
        current_app.logger.warning(f"Failed to clear login attempts: {e}")
