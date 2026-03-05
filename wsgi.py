"""
WSGI entry-point for production deployment.

Usage:
  # Gunicorn (Linux / Docker) — with SocketIO support:
  gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 wsgi:app

  # Waitress (Windows):
  waitress-serve --host 0.0.0.0 --port 5000 wsgi:app

  # Or via Python:
  python wsgi.py
"""
from app import app, socketio  # noqa: F401

if __name__ == '__main__':
    import os
    from config import Config
    port = int(os.getenv('PORT', '5000'))
    host = os.getenv('HOST', '0.0.0.0')

    if os.name == 'nt':
        # Windows — use waitress
        from waitress import serve
        print(f'[waitress] Serving AURA on http://{host}:{port}')
        serve(app, host=host, port=port, threads=8)
    else:
        # Linux/Mac — gunicorn (invoked from CLI, this branch is a fallback)
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=False)
