import os
from flask import Blueprint, redirect, session, jsonify, render_template, request
from aura.utils.database import get_db

core_bp = Blueprint('core', __name__)

@core_bp.route('/')
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
    elif session.get('parent_logged_in'):
        return redirect('/parent/dashboard')
    return redirect('/login')

@core_bp.route('/dashboard')
def dashboard_redirect():
    """Generic dashboard redirect."""
    return index()

@core_bp.route('/health')
def health():
    """Production health-check endpoint."""
    from datetime import datetime
    from config import Config
    
    checks = {
        'app': 'ok',
        'env': Config.ENV,
        'ai_configured': {
            'gemini': bool(os.getenv('GEMINI_API_KEY', '').strip()),
            'openai': bool(os.getenv('OPENAI_API_KEY', '').strip()),
        },
    }
    status = 200
    try:
        db = get_db()
        db.command('ping')
        checks['mongodb'] = 'ok'
    except Exception as e:
        checks['mongodb'] = f'error: {e}'
        status = 503

    checks['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    return jsonify(checks), status

@core_bp.route('/ui/chat')
def ui_chat():
    """Render the high-end chat UI template."""
    return render_template('index.html')
