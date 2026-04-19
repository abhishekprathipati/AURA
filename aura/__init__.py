import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from config import Config

# Primary SocketIO instance — threading mode for gthread/sync workers
socketio = SocketIO(async_mode='threading', cors_allowed_origins="*")

# Resolve paths relative to project root (one level up from this package)
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_pkg_dir)

def create_app(config_class=Config):
    """Application Factory Pattern."""
    app = Flask(
        __name__,
        template_folder=os.path.join(_project_root, 'templates'),
        static_folder=os.path.join(_project_root, 'static'),
    )
    app.config.from_object(config_class)
    app.secret_key = app.config.get('SECRET_KEY')
    
    # 0. ProxyFix Middleware
    if app.config.get('PROXY_FIX_ENABLED'):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get('PROXY_FIX_X_FOR', 1),
            x_proto=app.config.get('PROXY_FIX_X_PROTO', 1),
            x_host=app.config.get('PROXY_FIX_X_HOST', 1),
        )
    
    # 1. Initialize Logging
    _setup_logging(app)
    
    # 2. Initialize Extensions
    _init_extensions(app)
    
    # 3. Register Middleware
    from aura.middleware import register_middleware
    register_middleware(app)
    
    # 4. Initialize Database & Models
    from aura.utils.database import init_db
    from aura.models import init_models
    init_db()
    init_models()
    
    # 5. Register Blueprints
    _register_blueprints(app)
    
    # 6. Initialize SocketIO Handlers
    from aura import sockets  # Import to register decorators
    socketio.init_app(app)
    
    # 7. Startup Logic
    from aura.startup import run_startup_tasks
    with app.app_context():
        run_startup_tasks(app)
        
    return app

def _setup_logging(app):
    logging.basicConfig(
        level=getattr(logging, app.config.get('LOG_LEVEL', 'INFO'), logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    app.logger.info('AURA logging initialized')

def _init_extensions(app):
    """Initialize individual Flask extensions."""
    # Sentry
    if app.config.get('SENTRY_DSN'):
        _init_sentry(app)
        
    # Rate Limiter
    from aura.utils.rate_limit import limiter
    app.config['RATELIMIT_STORAGE_URL'] = app.config.get('RATELIMIT_STORAGE_URI')
    app.config['RATELIMIT_STORAGE_URI'] = app.config.get('RATELIMIT_STORAGE_URI')
    limiter.init_app(app)
    app.limiter = limiter
    
    # Mail
    try:
        from flask_mail import Mail
        app.mail = Mail(app)
        app.logger.info('Flask-Mail initialized')
    except ImportError:
        app.logger.warning('Flask-Mail not installed')

def _init_sentry(app):
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        sentry_sdk.init(
            dsn=app.config['SENTRY_DSN'],
            environment=app.config.get('SENTRY_ENVIRONMENT', 'production'),
            integrations=[
                FlaskIntegration(transaction_style='url'),
                LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
            ],
            traces_sample_rate=app.config.get('SENTRY_TRACES_SAMPLE_RATE', 0.1),
            send_default_pii=False,
        )
        app.logger.info('Sentry error monitoring initialized')
    except ImportError:
        app.logger.warning('sentry-sdk not installed')

def _register_blueprints(app):
    """Register all application blueprints."""
    from aura.routes import init_routes
    init_routes(app)
    app.logger.info('Blueprints registered')
