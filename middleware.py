"""
AURA Middleware — Security Headers & Request Hooks
===================================================
FIX #15: Extracted from app.py to reduce mixed concerns.
"""
import secrets
from flask import g, session


def register_middleware(app):
    """Register all middleware hooks on the Flask app."""

    @app.context_processor
    def inject_csp_nonce():
        """FIX #7: Generate a unique CSP nonce per request."""
        nonce = secrets.token_urlsafe(16)
        g.csp_nonce = nonce
        return dict(csp_nonce=nonce)

    @app.before_request
    def ensure_csrf_token():
        from utils.auth_helpers import generate_csrf_token
        if 'csrf_token' not in session:
            generate_csrf_token()

    @app.after_request
    def add_security_headers(response):
        h = response.headers
        h['X-Content-Type-Options'] = 'nosniff'
        h['X-Frame-Options'] = 'DENY'
        h['X-XSS-Protection'] = '1; mode=block'
        h['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
        h['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        h['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

        # FIX #7: Nonce-based CSP
        nonce = getattr(g, 'csp_nonce', None)
        if nonce:
            script_src = f"'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.socket.io 'nonce-{nonce}'"
            style_src = f"'self' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'nonce-{nonce}'"
        else:
            script_src = "'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.socket.io 'unsafe-inline'"
            style_src = "'self' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'"

        h['Content-Security-Policy'] = (
            "default-src 'self'; "
            f"script-src {script_src}; "
            f"style-src {style_src}; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net data:; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
        )

        # Static asset caching
        from config import Config
        if response.mimetype in ('text/css', 'application/javascript', 'image/svg+xml'):
            if Config.DEBUG:
                h['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            else:
                h['Cache-Control'] = 'public, max-age=2592000, immutable'

        return response
