import hmac
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.database import get_db
from models.user import UserModel
from utils.auth_helpers import verify_password, DEMO_EMAILS
from utils.audit_logger import log_activity, AuditAction
from utils.rate_limit import check_login_rate, record_failed_login, clear_login_attempts

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # SECURITY FIX #6: Validate CSRF token on login form POST
        form_token = request.form.get('csrf_token', '')
        session_token = session.get('csrf_token', '')
        if not form_token or not session_token or not hmac.compare_digest(form_token, session_token):
            flash('Invalid request. Please try again.', 'danger')
            return render_template('login.html'), 403

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')
        
        # ── Brute-force protection ──
        ip = request.remote_addr or '0.0.0.0'
        rate_check = check_login_rate(ip, email)
        if not rate_check['allowed']:
            flash(rate_check['message'], 'danger')
            return render_template('login.html'), 429
        
        # Find user in MongoDB
        database = None
        try:
            database = get_db()
        except Exception:
            database = None

        if database is None:
            flash('Database connection error. Please try again.', 'danger')
            return render_template('login.html')

        users_collection = database[UserModel.collection_name]
        user = users_collection.find_one({'email': email})
        
        if not user:
            record_failed_login(ip, email)
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')
        
        # Verify password
        if not verify_password(user['hashed_password'], password):
            record_failed_login(ip, email)
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')
        
        # Success — clear login rate limit
        clear_login_attempts(ip, email)
        
        # Set session
        session['user_email'] = user['email']
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        session['user_department'] = user.get('department', '')
        session['user_roll'] = user.get('roll_number', '')
        session['is_demo'] = user['email'] in DEMO_EMAILS
        
        if user['role'] in ('proctor', 'hod'):
            log_activity(
                action=AuditAction.LOGIN,
                target_type='session',
                target_id=user['email'],
                metadata={'role': user['role'], 'department': user.get('department', '')}
            )
        
        flash(f'Welcome back, {user["name"]}!', 'success')
        
        # Prompt users with a temporary password to change it immediately
        if user.get('must_change_password'):
            flash(
                'You are using a temporary password. Please change it now for account security.',
                'warning'
            )

        # Redirect based on role
        if user['role'] == 'student':
            return redirect('/student/dashboard')
        elif user['role'] == 'proctor':
            return redirect('/proctor/dashboard')
        elif user['role'] == 'hod':
            return redirect('/proctor/hod')
        else:
            return redirect('/student/dashboard')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@auth_bp.route('/auth/logout')  # safety alias for legacy links
def logout():
    user_role = session.get('user_role', '')
    if user_role in ('proctor', 'hod'):
        log_activity(
            action=AuditAction.LOGOUT,
            target_type='session',
            target_id=session.get('user_email', ''),
        )
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
