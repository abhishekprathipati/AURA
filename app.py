from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file FIRST

from flask import Flask, redirect, session, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from routes import init_routes
from flask_mail import Mail
from models import init_models
from utils.database import init_db
import os

app = Flask(__name__)
app.config.from_object('config.Config')

# Configure session secret key
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize email
mail = Mail(app)

# Initialize MongoDB (no Flask app context required)
init_db()
init_models()
init_routes(app)

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; "
        "style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
    )
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Prevent CSS/JS caching during development
    if response.mimetype in ['text/css', 'application/javascript']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

# Ensure indexes on startup
def ensure_production_indexes():
    """Create optimized indexes for production queries."""
    try:
        from utils.database import get_db
        db = get_db()
        
        # Proctor-related indexes
        db['risk_incidents'].create_index([('status', 1), ('risk_level', -1), ('timestamp', -1)], name='queue_view', background=True)
        db['risk_incidents'].create_index([('timestamp', -1), ('status', 1)], name='time_filter', background=True)
        db['risk_incidents'].create_index([('anonymous_student_id', 1)], name='student_lookup', background=True)
        db['proctor_actions'].create_index([('timestamp', -1)], name='audit_timeline', background=True)
        db['proctor_actions'].create_index([('incident_id', 1)], name='incident_actions', background=True)
        db['proctor_actions'].create_index([('proctor_id', 1), ('timestamp', -1)], name='proctor_activity', background=True)
        
        # Phase 4: Student wellness indexes
        db['student_wellness'].create_index([('student_id', 1), ('timestamp', -1)], name='wellness_timeline', background=True)
        db['student_wellness'].create_index([('student_id', 1), ('data_type', 1)], name='wellness_by_type', background=True)
        db['support_requests'].create_index([('student_id', 1), ('timestamp', -1)], name='support_timeline', background=True)
        
        print("✓ Production indexes ensured")
    except Exception as e:
        print(f"⚠ Index creation warning: {e}")

with app.app_context():
    ensure_production_indexes()

@app.route('/')
def index():
    """Root route - redirect based on login status and role."""
    if 'user_email' in session:
        role = session.get('user_role', 'student')
        if role == 'student':
            return redirect('/student/dashboard')
        elif role == 'proctor':
            return redirect('/proctor/dashboard')
        elif role == 'hod':
            return redirect('/proctor/hod')
        else:
            return redirect('/student/dashboard')
    # Check for parent session
    elif session.get('parent_logged_in'):
        return redirect('/parent/dashboard')
    return redirect('/login')


@app.route('/dashboard')
def dashboard_redirect():
    """Generic dashboard redirect based on user role."""
    if 'user_email' in session:
        role = session.get('user_role', 'student')
        if role == 'student':
            return redirect('/student/dashboard')
        elif role == 'proctor':
            return redirect('/proctor/dashboard')
        elif role == 'hod':
            return redirect('/proctor/hod')
    elif session.get('parent_logged_in'):
        return redirect('/parent/dashboard')
    return redirect('/login')

@app.route('/health')
def health():
    return {'status': 'ok', 'app': 'AURA'}

@app.route('/ui/chat')
def ui_chat():
    """Render the high-end chat UI template."""
    return render_template('index.html')

if __name__ == '__main__':
    # Respect FLASK_DEBUG environment variable for local development
    debug = os.getenv('FLASK_DEBUG', '').strip().lower() in ('1','true','yes','on')
    use_reloader = debug
    print(f"Starting app with debug={debug}")
    app.run(debug=debug, use_reloader=use_reloader)
