"""
PARENT EMAIL PROFILE ENDPOINTS
==============================
Student add parent email -> Verification link sent -> Parent verifies
"""

from flask import Blueprint, request, jsonify, session, render_template_string, current_app
from utils.database import get_db
from utils.auth_helpers import login_required
from utils.parent_verification import (
    create_parent_verification_record,
    send_parent_verification_email,
    verify_parent_email,
    get_parent_verification_status
)
import logging

parent_profile_bp = Blueprint('parent_profile', __name__, url_prefix='/api/student/parent')
log = logging.getLogger(__name__)


@parent_profile_bp.route('/status', methods=['GET'])
@login_required
def get_parent_status():
    """
    Get current parent email status for logged-in student.
    """
    try:
        student_email = session.get('user_email')
        db = get_db()

        status = get_parent_verification_status(db, student_email)

        return jsonify({
            'success': True,
            'data': status,
        }), 200

    except Exception as e:
        log.error('Failed to get parent status: %s', e)
        return jsonify({'error': str(e)}), 500


@parent_profile_bp.route('/add', methods=['POST'])
@login_required
def add_parent_email():
    """
    Student adds parent email.
    Sends verification email to parent.

    JSON:
        {
            "parent_email": "parent@gmail.com",
            "parent_name": "Mr. Parent Name"
        }
    """
    try:
        student_email = session.get('user_email')
        student_name = session.get('user_name', student_email.split('@')[0])

        data = request.get_json() or {}
        parent_email = (data.get('parent_email', '') or '').strip()
        parent_name = (data.get('parent_name', '') or '').strip()

        # Validate
        if not parent_email or '@' not in parent_email:
            return jsonify({'error': 'Invalid email address'}), 400

        if parent_email == student_email:
            return jsonify({'error': 'Parent email cannot be same as student email'}), 400

        db = get_db()

        # Create verification record
        verification = create_parent_verification_record(
            db, student_email, parent_email, parent_name
        )

        # Build verification URL
        base_url = request.host_url.rstrip('/') or 'https://yourdomain.com'
        verification_url = f"{base_url}/parent/verify?token={verification['token']}&email={parent_email}"

        # Send verification email
        mail_ext = current_app.extensions.get('mail')
        email_sent = send_parent_verification_email(
            mail_ext,
            student_name,
            student_email,
            parent_email,
            verification_url
        )

        if not email_sent:
            return jsonify({
                'success': False,
                'message': 'Parent email added but verification email could not be sent',
            }), 200

        log.info('Parent email added for %s: %s', student_email, parent_email)

        return jsonify({
            'success': True,
            'message': f'Verification email sent to {parent_email}. Please ask your parent to check and confirm.',
            'parent_email': parent_email,
            'expires_in_days': 7,
        }), 200

    except Exception as e:
        log.error('Failed to add parent email: %s', e)
        return jsonify({'error': str(e)}), 500


@parent_profile_bp.route('/remove', methods=['POST'])
@login_required
def remove_parent_email():
    """
    Student removes parent email.
    """
    try:
        student_email = session.get('user_email')
        db = get_db()
        users = db['users']

        # Remove parent email
        users.update_one(
            {'email': student_email},
            {'$unset': {
                'parent_email': '',
                'parent_name': '',
                'parent_verified': '',
                'parent_verified_at': '',
            }}
        )

        log.info('Parent email removed for %s', student_email)

        return jsonify({
            'success': True,
            'message': 'Parent email removed. Alerts will no longer be sent to parent.',
        }), 200

    except Exception as e:
        log.error('Failed to remove parent email: %s', e)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PUBLIC ENDPOINT: Parent clicks verification link
# ============================================================================

@parent_profile_bp.route('/verify', methods=['GET'])
def verify_parent_email_page():
    """
    Public endpoint for parent to verify email.
    Parent clicks link from email -> lands on this page.

    Query params:
        token: verification_token
        email: parent_email
    """
    try:
        token = request.args.get('token', '').strip()
        email = request.args.get('email', '').strip()

        if not token or not email:
            return render_template_string("""
                <html>
                <body style="text-align: center; padding: 50px; font-family: Arial;">
                    <h1>Invalid Link</h1>
                    <p>The verification link is missing required information.</p>
                    <p>Please check the email again or contact support.</p>
                </body>
                </html>
            """), 400

        db = get_db()

        # Verify email
        success, message = verify_parent_email(db, token, email)

        if success:
            return render_template_string("""
                <html>
                <head><title>Email Verified</title></head>
                <body style="text-align: center; padding: 50px; font-family: Arial;">
                    <div style="max-width: 500px; margin: 0 auto;">
                        <h1 style="color: green;">Email Verified!</h1>
                        <p style="font-size: 18px;">{{ message }}</p>
                        <p style="color: #666; margin-top: 30px;">
                            You will now receive wellness alerts from AURA when your child's stress is detected.
                        </p>
                        <div style="background: #f0f0f0; padding: 20px; margin-top: 30px; border-radius: 5px;">
                            <h3>What happens next:</h3>
                            <ul style="text-align: left;">
                                <li>HIGH STRESS alerts - when stress score > 70</li>
                                <li>CRISIS alerts - if harmful keywords detected</li>
                                <li>Emergency resources & guidance included</li>
                            </ul>
                        </div>
                        <p style="margin-top: 30px; color: #999;">
                            Questions? Contact: support@aura-system.com
                        </p>
                    </div>
                </body>
                </html>
            """, message=message), 200

        else:
            return render_template_string("""
                <html>
                <head><title>Verification Failed</title></head>
                <body style="text-align: center; padding: 50px; font-family: Arial;">
                    <div style="max-width: 500px; margin: 0 auto;">
                        <h1 style="color: red;">Verification Failed</h1>
                        <p style="font-size: 18px;">{{ message }}</p>
                        <p style="margin-top: 30px; color: #666;">
                            Please ask your child to send you a new verification email.
                        </p>
                        <p style="margin-top: 30px; color: #999;">
                            Questions? Contact: support@aura-system.com
                        </p>
                    </div>
                </body>
                </html>
            """, message=message), 400

    except Exception as e:
        log.error('Verification error: %s', e)
        return render_template_string("""
            <html>
            <body style="text-align: center; padding: 50px; font-family: Arial;">
                <h1>Error</h1>
                <p>An error occurred while processing your request.</p>
                <p style="color: #666;">{{ error }}</p>
            </body>
            </html>
        """, error=str(e)), 500
