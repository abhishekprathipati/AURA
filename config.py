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
    # WARNING: 'memory://' is for DEVELOPMENT ONLY. It stores rate-limit counters
    # in-process memory, which means:
    #   1) Limits reset on every server restart
    #   2) Multi-instance deployments (Gunicorn workers, Kubernetes pods) won't share state
    #   3) No persistence across deploys
    # For production, set RATELIMIT_STORAGE_URI to a Redis URL (e.g., redis://localhost:6379/0)
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', os.getenv('REDIS_URL', 'memory://'))
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

    # ── Timezone ─────────────────────────────────────────────────────────
    # Default timezone offset in minutes from UTC (IST = +330, EST = -300, etc.)
    # Used for time-of-day stress bias calculations
    # Set via DEFAULT_TIMEZONE_OFFSET env var or override per user in their profile
    DEFAULT_TIMEZONE_OFFSET = _int('DEFAULT_TIMEZONE_OFFSET', 330)  # IST (+5:30) default

    # ── Error Monitoring (Sentry) ─────────────────────────────────────────
    # Sentry provides real-time error tracking and performance monitoring.
    # Disabled by default. To enable:
    #   1. Create a Sentry project at https://sentry.io/
    #   2. Get your DSN from Project Settings > Client Keys (DSN)
    #   3. Set SENTRY_DSN environment variable
    #   4. Install sentry-sdk: pip install sentry-sdk[flask]
    SENTRY_DSN         = os.getenv('SENTRY_DSN', '')  # Leave empty to disable
    SENTRY_ENVIRONMENT = os.getenv('SENTRY_ENVIRONMENT', ENV)  # 'production', 'staging', etc.
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))  # 10% of transactions
    SENTRY_PROFILES_SAMPLE_RATE = float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0.1'))  # 10% profiling

    # ── Data Retention ────────────────────────────────────────────────────
    # Used by scripts/cleanup.py for periodic data cleanup
    DATA_RETENTION_CHAT_DAYS = _int('DATA_RETENTION_CHAT_DAYS', 90)   # Days to keep chat messages
    DATA_RETENTION_LOGS_DAYS = _int('DATA_RETENTION_LOGS_DAYS', 365)  # Days to keep stress/mood logs
