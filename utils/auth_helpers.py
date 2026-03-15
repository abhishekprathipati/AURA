import bcrypt
import secrets
import string
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request
from typing import Callable

# Demo accounts that should have restricted (read-only) access
DEMO_EMAILS = {
    'student@aura.edu',
    'proctor@aura.edu',
    'hod@aura.edu',
}

# Demo usage limits
DEMO_CHAT_LIMIT = 5          # max chat messages per session
DEMO_GAME_TIME_LIMIT = 120   # seconds before games/activities lock

def is_demo_account() -> bool:
    """Check if the current session belongs to a demo account."""
    return session.get('is_demo', False) or session.get('user_email', '') in DEMO_EMAILS

def verify_password(hashed_password: str, password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def generate_temp_password(length: int = 12) -> str:
    """
    Generate a cryptographically secure random temporary password.
    Contains letters, digits, and special chars to meet common complexity rules.
    The caller is responsible for communicating it to the user exactly once.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    # Guarantee at least one of each character class
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    pwd += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)

def login_required(f: Callable) -> Callable:
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def demo_restricted(f: Callable) -> Callable:
    """Decorator to block write/sensitive operations for demo accounts.
    
    Demo users can browse and view all pages, but cannot perform
    actions that modify data (submit forms, send messages, create
    records, change statuses, etc.).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_demo_account():
            # Return JSON error for API endpoints, flash for page requests
            if request.is_json or request.path.startswith('/api/') or request.content_type == 'application/json':
                return jsonify({
                    'error': 'Demo account restriction',
                    'message': 'This action is not available in demo mode. Please register a real account to use this feature.',
                    'demo_restricted': True
                }), 403
            flash('This action is not available in demo mode. Please register a real account.', 'warning')
            return redirect(request.referrer or url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def demo_chat_limited(f: Callable) -> Callable:
    """Decorator that allows demo accounts a limited number of chat messages.
    
    After DEMO_CHAT_LIMIT messages, returns a 403 with a clear
    upgrade prompt. The counter lives in session['demo_chat_count'].
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_demo_account():
            count = session.get('demo_chat_count', 0)
            if count >= DEMO_CHAT_LIMIT:
                return jsonify({
                    'error': 'Demo limit reached',
                    'message': f'You have used all {DEMO_CHAT_LIMIT} demo messages. Register a real account for unlimited access.',
                    'demo_limited': True,
                    'limit': DEMO_CHAT_LIMIT,
                    'used': count
                }), 403
            # Increment counter
            session['demo_chat_count'] = count + 1
            session.modified = True
        return f(*args, **kwargs)
    return decorated_function

def role_required(role: str) -> Callable:
    """Decorator to protect routes that require a specific role."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_email' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('user_role') != role:
                flash(f'Access denied. {role.capitalize()} role required.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
