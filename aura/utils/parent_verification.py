"""
PARENT EMAIL VERIFICATION SYSTEM
=================================
Students add parent email in profile.
Verification email sent to parent.
Parent clicks link to verify.
Once verified, alerts work.
"""

import secrets
import logging
from datetime import datetime, timedelta
from typing import Tuple

log = logging.getLogger(__name__)


def generate_verification_token(length: int = 32) -> str:
    """Generate secure verification token"""
    return secrets.token_urlsafe(length)


def create_parent_verification_record(db, student_email: str, parent_email: str,
                                      parent_name: str = None) -> dict:
    """
    Create verification record for parent email.

    Returns: {
        'token': verification_token,
        'expires_at': expiration_time,
        'verification_url': url_to_send_to_parent
    }
    """
    token = generate_verification_token()
    expires_at = datetime.utcnow() + timedelta(days=7)  # 7 day expiry

    verifications = db['parent_verifications']

    # Invalidate old tokens
    verifications.update_many(
        {'student_email': student_email},
        {'$set': {'invalidated': True}}
    )

    # Create new verification record
    verifications.insert_one({
        'student_email': student_email,
        'parent_email': parent_email,
        'parent_name': parent_name,
        'token': token,
        'created_at': datetime.utcnow(),
        'expires_at': expires_at,
        'verified': False,
        'invalidated': False,
    })

    log.info('Parent verification created: %s -> %s', student_email, parent_email)

    return {
        'token': token,
        'expires_at': expires_at,
        'parent_email': parent_email,
    }


def send_parent_verification_email(mail_ext, student_name: str, student_email: str,
                                   parent_email: str, verification_url: str, parent_name: str = None) -> bool:
    """
    Send verification email to parent.

    verification_url format: https://yourdomain.com/parent/verify?token=TOKEN&email=PARENT_EMAIL
    """
    if not mail_ext:
        log.error('Mail not configured for verification email')
        return False

    try:
        from flask_mail import Message

        subject = f"[Action Required] Verify Your Email - AURA Student Wellness Alerts"

        body = f"""Hello {parent_name or 'Parent/Guardian'},

{student_name} ({student_email}) has added you as a parent contact in AURA, our student mental health and wellness monitoring system.

=== VERIFY YOUR EMAIL ===

Click the link below to confirm you want to receive wellness alerts for {student_name}:

{verification_url}

This link expires in 7 days. If it doesn't work, copy and paste the full URL into your browser.

=== WHAT IS AURA? ===

AURA monitors student well-being through:
  - Daily mood check-ins
  - Real-time conversation analysis
  - Automatic alerts for high stress or crisis situations

=== WHAT YOU WILL RECEIVE ===

Once verified, you will get:
  - STRESS ALERTS: When {student_name}'s stress score exceeds 70/100
  - CRISIS ALERTS: If harmful keywords are detected (with guidance on how to help)

=== INDIAN SUPPORT HELPLINES ===

(We include these in every alert so you always have resources ready)
  - iCall (TISS)          : 9152987821  (Mon-Sat 8am-10pm)
  - Vandrevala Foundation : 9999 666 555 (24/7, multilingual, free)
  - AASRA                 : 9820466726
  - National Emergency    : 112

=== PRIVACY & SECURITY ===

  - Your email is private and will never be shared
  - You can ask {student_name} to remove you at any time
  - AURA does not share personal counselling data with parents

IF YOU DID NOT EXPECT THIS EMAIL:
  Simply ignore it. No action is needed from you.
  {student_name} may have entered your email by mistake.

---
AURA Student Wellness System
Supporting mental health, one student at a time.
        """.strip()

        msg = Message(
            subject=subject,
            recipients=[parent_email],
            body=body
        )

        mail_ext.send(msg)
        log.info('Verification email sent to parent: %s for student: %s', parent_email, student_email)
        return True

    except Exception as e:
        log.error('Failed to send verification email to %s: %s', parent_email, e)
        return False



def verify_parent_email(db, token: str, parent_email: str) -> Tuple[bool, str]:
    """
    Verify parent email using token.

    Returns: (success, message)
    """
    verifications = db['parent_verifications']
    users = db['users']

    # Find verification record
    record = verifications.find_one({
        'token': token,
        'parent_email': parent_email,
        'verified': False,
        'invalidated': False,
    })

    if not record:
        return False, 'Invalid or expired verification link'

    # Check expiry
    if record['expires_at'] < datetime.utcnow():
        verifications.update_one(
            {'_id': record['_id']},
            {'$set': {'invalidated': True}}
        )
        return False, 'Verification link has expired (7 days)'

    # Mark as verified
    verifications.update_one(
        {'_id': record['_id']},
        {'$set': {
            'verified': True,
            'verified_at': datetime.utcnow(),
        }}
    )

    # Update student profile
    student_email = record['student_email']
    users.update_one(
        {'email': student_email},
        {'$set': {
            'parent_email': parent_email,
            'parent_name': record.get('parent_name'),
            'parent_verified': True,
            'parent_verified_at': datetime.utcnow(),
        }}
    )

    log.info('Parent email verified: %s -> %s', student_email, parent_email)

    return True, f'Email verified! Alerts will now be sent to {parent_email}'


def get_parent_verification_status(db, student_email: str) -> dict:
    """
    Get current parent email verification status.
    """
    users = db['users']
    verifications = db['parent_verifications']

    student = users.find_one({'email': student_email}) or {}
    pending = verifications.find_one({
        'student_email': student_email,
        'verified': False,
        'invalidated': False,
        'expires_at': {'$gt': datetime.utcnow()},
    }) or {}

    return {
        'parent_email': student.get('parent_email'),
        'parent_name': student.get('parent_name'),
        'parent_verified': student.get('parent_verified', False),
        'parent_verified_at': student.get('parent_verified_at'),
        'pending_email': pending.get('parent_email'),
        'pending_since': pending.get('created_at'),
        'pending_expires_at': pending.get('expires_at'),
    }
