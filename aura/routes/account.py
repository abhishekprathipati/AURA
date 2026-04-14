"""
AURA Account Management Routes
================================
FIX #48: Password change functionality.
"""
import hmac
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from aura.utils.database import get_db
from aura.models.user import UserModel
from aura.utils.auth_helpers import login_required, verify_password, hash_password

account_bp = Blueprint('account', __name__)


@account_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow authenticated users to change their password."""
    if request.method == 'POST':
        # CSRF validation
        form_token = request.form.get('csrf_token', '')
        session_token = session.get('csrf_token', '')
        if not form_token or not session_token or not hmac.compare_digest(form_token, session_token):
            flash('Invalid request. Please try again.', 'danger')
            return render_template('change_password.html'), 403

        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not current_pw or not new_pw or not confirm_pw:
            flash('All fields are required.', 'danger')
            return render_template('change_password.html')

        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'danger')
            return render_template('change_password.html')

        if len(new_pw) < 8:
            flash('New password must be at least 8 characters.', 'danger')
            return render_template('change_password.html')

        # Verify current password
        db = get_db()
        user = db[UserModel.collection_name].find_one({'email': session['user_email']})
        if not user or not verify_password(user['hashed_password'], current_pw):
            flash('Current password is incorrect.', 'danger')
            return render_template('change_password.html')

        # Update password
        db[UserModel.collection_name].update_one(
            {'email': session['user_email']},
            {'$set': {
                'hashed_password': hash_password(new_pw),
                'must_change_password': False,
            }}
        )

        flash('Password changed successfully!', 'success')
        role = session.get('user_role', 'student')
        if role == 'student':
            return redirect('/student/dashboard')
        elif role == 'proctor':
            return redirect('/proctor/dashboard')
        else:
            return redirect('/')

    return render_template('change_password.html')
