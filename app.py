"""
AURA Application Entry Point

This file serves as a thin wrapper around the modular application factory
located in the `aura` package. It ensures backward compatibility for scripts
and WSGI servers (like Gunicorn) that expect `app` and `socketio` in the root.
"""

import eventlet
eventlet.monkey_patch()

from dotenv import load_dotenv
import os

# Load environment variables FIRST before any internal imports
load_dotenv() 

from aura import create_app, socketio

# Create the application instance using the factory
app = create_app()

if __name__ == '__main__':
    debug = app.config.get('DEBUG', False)
    port = int(os.getenv('PORT', '5000'))
    host = os.getenv('HOST', '0.0.0.0')
    
    app.logger.info(f"Starting AURA  host={host} port={port} debug={debug}")
    # Run using SocketIO's development server
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=debug)
