from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file FIRST

from flask import Flask, redirect, session, render_template
from routes import init_routes
from flask_mail import Mail
from models import init_models
from utils.database import init_db
import os

app = Flask(__name__)
app.config.from_object('config.Config')

# Configure session secret key
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize email
mail = Mail(app)

# Initialize MongoDB (no Flask app context required)
init_db()
init_models()
init_routes(app)

@app.route('/')
def index():
    """Root route - redirect based on login status."""
    if 'user_email' in session:
        role = session.get('user_role', 'student')
        if role == 'student':
            return redirect('/student/dashboard')
        elif role == 'proctor':
            return redirect('/proctor/dashboard')
        elif role == 'hod':
            return redirect('/proctor/hod')
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
