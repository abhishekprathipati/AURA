from app import app, socketio
from config import Config
import os

if __name__ == '__main__':
    debug = Config.DEBUG
    port  = int(os.getenv('PORT', '5000'))
    host  = os.getenv('HOST', '0.0.0.0')
    # allow_unsafe_werkzeug must only be True in dev/debug mode.
    # In production, gunicorn (via Procfile) is used instead of this script.
    socketio.run(app, host=host, port=port, debug=debug,
                 allow_unsafe_werkzeug=debug)
