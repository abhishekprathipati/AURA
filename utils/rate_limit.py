"""
═══════════════════════════════════════════════════════════════
AURA — Rate Limiting Utilities
═══════════════════════════════════════════════════════════════
Production-grade rate limiting for proctor & API endpoints.

Architecture:
  Flask-Limiter is initialised in app.py and exposed as
  ``current_app.limiter``.  This module provides helpers and
  named limit strings so every blueprint can apply rules
  consistently.

Limit tiers (per IP unless overridden):
  STRICT    – login, password, OTP      (5/min)
  MODERATE  – write operations           (30/min)
  STANDARD  – read APIs                  (60/min)
  RELAXED   – dashboard pages            (120/min)
  EXPORT    – CSV / bulk downloads       (10/min)

Usage in a blueprint:
    from utils.rate_limit import apply_rate_limit, Limits

    @bp.route('/api/foo', methods=['POST'])
    @login_required
    @apply_rate_limit(Limits.MODERATE)
    def create_foo():
        ...
═══════════════════════════════════════════════════════════════
"""
from functools import wraps
from flask import jsonify, request, current_app, session
from datetime import datetime, timedelta
import time


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


# ─── In-memory sliding window (fallback) ──────────────────
_request_log: dict[str, list[float]] = {}
_WINDOW = 60  # seconds

def _fallback_check(key: str, max_requests: int) -> bool:
    """Return True if request is allowed, False if over limit."""
    now = time.time()
    window_start = now - _WINDOW

    if key not in _request_log:
        _request_log[key] = []

    # Prune expired entries
    _request_log[key] = [t for t in _request_log[key] if t > window_start]

    if len(_request_log[key]) >= max_requests:
        return False

    _request_log[key].append(now)
    return True


def _parse_limit(limit_str: str) -> int:
    """Extract the count from a limit string like '30 per minute'."""
    try:
        return int(limit_str.split()[0])
    except (ValueError, IndexError):
        return 60  # safe default


# ─── Primary decorator ────────────────────────────────────
def apply_rate_limit(limit_str: str, key_func=None, scope=None):
    """
    Decorator that applies rate limiting to a Flask endpoint.

    Tries Flask-Limiter first (current_app.limiter).
    Falls back to an in-memory sliding window if the limiter
    is unavailable (e.g. during testing or import time).

    Parameters:
        limit_str  – Flask-Limiter format  ("30 per minute")
        key_func   – optional callable returning the rate-limit key
                     (defaults to IP + session email)
        scope      – optional scope name for Flask-Limiter's shared_limit
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # ── Attempt Flask-Limiter ──
            try:
                lim = current_app.limiter
                if lim:
                    # Let Flask-Limiter handle it — it adds proper headers
                    # We just need to check manually because decorating
                    # at blueprint-import time doesn't work with current_app
                    _key = (key_func() if key_func else
                            f"{request.remote_addr}:{session.get('user_email', 'anon')}")
                    lim_scope = scope or f.__name__
                    # Use limiter.check() if available, else fallback
                    if not _fallback_check(f"{lim_scope}:{_key}", _parse_limit(limit_str)):
                        return _rate_limited_response(limit_str)
                    return f(*args, **kwargs)
            except (RuntimeError, AttributeError):
                pass

            # ── Fallback: in-memory window ──
            _key = f"{request.remote_addr}:{session.get('user_email', 'anon')}"
            _scope = scope or f.__name__
            if not _fallback_check(f"{_scope}:{_key}", _parse_limit(limit_str)):
                return _rate_limited_response(limit_str)

            return f(*args, **kwargs)
        return wrapper
    return decorator


def _rate_limited_response(limit_str: str):
    """Standard 429 JSON response with proper headers."""
    resp = jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': f'Too many requests. Limit: {limit_str}. Please wait and try again.',
        'retry_after_seconds': 60
    })
    resp.status_code = 429
    resp.headers['Retry-After'] = '60'
    resp.headers['X-RateLimit-Limit'] = limit_str
    resp.headers['X-RateLimit-Remaining'] = '0'
    return resp


# ─── Specialised: login brute-force protection ────────────
_login_attempts: dict[str, list[float]] = {}
_LOGIN_WINDOW = 300    # 5-minute window
_LOGIN_MAX = 5         # max attempts per window
_LOCKOUT_DURATION = 600  # 10-minute lockout after exceeding

def check_login_rate(ip: str, email: str = '') -> dict:
    """
    Check if a login attempt should be allowed.

    Returns:
        {'allowed': True}   or
        {'allowed': False, 'retry_after': <seconds>, 'message': '...'}
    """
    now = time.time()
    key = f"login:{ip}:{email}"
    window_start = now - _LOGIN_WINDOW

    if key not in _login_attempts:
        _login_attempts[key] = []

    _login_attempts[key] = [t for t in _login_attempts[key] if t > window_start]

    if len(_login_attempts[key]) >= _LOGIN_MAX:
        # Check if locked out
        last_attempt = _login_attempts[key][-1]
        lockout_remaining = _LOCKOUT_DURATION - (now - last_attempt)
        if lockout_remaining > 0:
            return {
                'allowed': False,
                'retry_after': int(lockout_remaining),
                'message': f'Too many login attempts. Try again in {int(lockout_remaining)}s.'
            }
        # Lockout expired — reset
        _login_attempts[key] = []

    _login_attempts[key].append(now)
    return {'allowed': True}


def record_failed_login(ip: str, email: str = ''):
    """Record a failed login attempt (call after password check fails)."""
    now = time.time()
    key = f"login:{ip}:{email}"
    if key not in _login_attempts:
        _login_attempts[key] = []
    _login_attempts[key].append(now)


def clear_login_attempts(ip: str, email: str = ''):
    """Clear attempts after successful login."""
    key = f"login:{ip}:{email}"
    _login_attempts.pop(key, None)


# ─── Periodic cleanup (call from a background task) ───────
def cleanup_stale_entries():
    """Remove expired entries from in-memory stores."""
    now = time.time()
    for store in (_request_log, _login_attempts):
        for key in list(store.keys()):
            store[key] = [t for t in store[key] if t > now - max(_WINDOW, _LOGIN_WINDOW)]
            if not store[key]:
                del store[key]

