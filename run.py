"""
AURA Development Server Runner
"""

from dotenv import load_dotenv
load_dotenv()

import os
from aura import create_app, socketio

app = create_app()

if __name__ == '__main__':
    debug = app.config.get('DEBUG', False)
    port  = int(os.getenv('PORT', '5000'))
    host  = os.getenv('HOST', '0.0.0.0')
    
    app.logger.info(f"Starting AURA  host={host} port={port} debug={debug}")
    # allow_unsafe_werkzeug=True is safe for local dev only.
    socketio.run(app, host=host, port=port, debug=debug,
                 allow_unsafe_werkzeug=True)
