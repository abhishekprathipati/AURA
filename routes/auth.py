from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.database import get_db
from models.user import UserModel
from utils.auth_helpers import verify_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')
        
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
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')
        
        # Verify password
        if not verify_password(user['hashed_password'], password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')
        
        # Set session
        session['user_email'] = user['email']
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        
        flash(f'Welcome back, {user["name"]}!', 'success')
        
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
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
