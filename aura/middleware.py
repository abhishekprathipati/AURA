import secrets
from flask import g, session, request, jsonify, render_template

def register_middleware(app):
    """Register all middleware hooks on the Flask app."""

    @app.context_processor
    def inject_csrf_token():
        from aura.utils.auth_helpers import generate_csrf_token
        return dict(csrf_token=generate_csrf_token)

    @app.context_processor
    def inject_csp_nonce():
        """FIX #7: Generate a unique CSP nonce per request."""
        nonce = secrets.token_urlsafe(16)
        g.csp_nonce = nonce
        return dict(csp_nonce=nonce)

    @app.before_request
    def ensure_csrf_token():
        from aura.utils.auth_helpers import generate_csrf_token
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
        if response.mimetype in ('text/css', 'application/javascript', 'image/svg+xml'):
            if app.config.get('DEBUG'):
                h['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            else:
                # Use versioned caching rather than immutable to allow ?v= busting
                h['Cache-Control'] = 'public, max-age=3600'

        return response

    # Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.accept_mimetypes.best == 'application/json':
            return jsonify({'error': 'Not found'}), 404
        return render_template('error.html', show_nav=False, error_code=404, error_msg='Page not found'), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.accept_mimetypes.best == 'application/json':
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error.html', show_nav=False, error_code=500, error_msg='Something went wrong'), 500

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'message': str(e.description) if hasattr(e, 'description') else 'Too many requests.',
            'retry_after_seconds': 60
        }), 429, {'Retry-After': '60', 'X-RateLimit-Remaining': '0'}
