import os
import secrets

# ─── Helpers ───────────────────────────────────────────────────────────
_FALLBACK_SECRET = secrets.token_hex(32)

def _bool(key, default='false'):
    return os.getenv(key, default).strip().lower() in ('1', 'true', 'yes', 'on')

def _int(key, default):
    return int(os.getenv(key, str(default)))


class Config:
    """Centralised configuration — every value overridable via env."""

    # ── Core Flask ──────────────────────────────────────────────────────
    SECRET_KEY        = os.getenv('SECRET_KEY', _FALLBACK_SECRET)
    DEBUG             = _bool('FLASK_DEBUG')
    ENV               = os.getenv('FLASK_ENV', 'production')   # 'development' | 'production'
    LOG_LEVEL         = os.getenv('LOG_LEVEL', 'INFO').upper()  # DEBUG | INFO | WARNING | ERROR

    # ── Session cookies ─────────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE   = _bool('SESSION_COOKIE_SECURE')    # True behind HTTPS
    PERMANENT_SESSION_LIFETIME = _int('SESSION_LIFETIME_SECS', 3600)  # 1 hour default

    # ── Upload limit ────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = _int('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)  # 16 MB

    # ── MongoDB ─────────────────────────────────────────────────────────
    MONGODB_URI       = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB_NAME   = os.getenv('MONGODB_DB_NAME', 'aura_db')
    MONGODB_TLS       = _bool('MONGODB_TLS')
    MONGODB_TLS_ALLOW_INVALID_CERTIFICATES = _bool('MONGODB_TLS_ALLOW_INVALID')

    # ── Rate-limit storage (memory for dev, Redis for prod) ─────────────
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    #   Production: redis://localhost:6379/0   or   redis://<host>:6379/0

    # ── Fast2SMS (parent OTP) ───────────────────────────────────────────
    FAST2SMS_API_KEY  = os.getenv('FAST2SMS_API_KEY', '')
    FAST2SMS_SENDER_ID = os.getenv('FAST2SMS_SENDER_ID', 'AURASM')
    SMS_ENABLED       = _bool('SMS_ENABLED', 'true')

    # ── Mail ────────────────────────────────────────────────────────────
    MAIL_SERVER        = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT          = _int('MAIL_PORT', 587)
    MAIL_USE_TLS       = True
    MAIL_USERNAME      = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD      = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', ''))

    # ── Reverse Proxy ───────────────────────────────────────────────────
    PROXY_FIX_ENABLED  = _bool('PROXY_FIX_ENABLED')  # Set True behind nginx/caddy
    PROXY_FIX_X_FOR    = _int('PROXY_FIX_X_FOR', 1)
    PROXY_FIX_X_PROTO  = _int('PROXY_FIX_X_PROTO', 1)
    PROXY_FIX_X_HOST   = _int('PROXY_FIX_X_HOST', 1)
