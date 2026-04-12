from flask import current_app
from utils.database import get_db
from datetime import datetime
import logging

try:
    from flask_mail import Message
except ImportError:
    Message = None

log = logging.getLogger(__name__)


def send_institutional_alert(student_email: str, score: int) -> dict:
    """
    Send alert to proctor and parent if configured, and log to DB.

    Returns: {
        'success': bool,
        'proctor_sent': bool,
        'parent_sent': bool,
        'proctor_email': str,
        'parent_email': str,
        'message': str
    }
    """
    db = get_db()
    users = db['users']
    alerts = db['alerts']

    student = users.find_one({'email': student_email}) or {}

    # Look up the student's assigned proctor from proctor_students, not a
    # random first proctor — ensures the right person is notified.
    proctor_record = db['proctor_students'].find_one({'email': student_email, 'status': 'active'})
    proctor_email = proctor_record.get('proctor_id') if proctor_record else None
    proctor = {}
    if proctor_email:
        proctor = users.find_one({'email': proctor_email, 'role': 'proctor'}) or {}
    # Fallback: any active proctor in the student's department
    if not proctor:
        dept = student.get('department') or ''
        if dept:
            proctor = users.find_one({'role': 'proctor', 'department': dept}) or {}
        if not proctor:
            proctor = users.find_one({'role': 'proctor'}) or {}

    proctor_email = proctor.get('email')
    parent_email = student.get('parent_email')

    # Prepare email content
    subject = f"AURA ALERT: High Stress ({score}/100) - {student.get('name','Student')}"
    body = (
        f"ALERT: Student Stress Detected\n"
        f"{'='*50}\n\n"
        f"Student Name: {student.get('name','Unknown')}\n"
        f"Student Email: {student_email}\n"
        f"Stress Score: {score}/100\n"
        f"Department: {student.get('department','N/A')}\n\n"
        f"Action Required:\n"
        f"- Reach out to the student\n"
        f"- Provide guidance and support\n"
        f"- Connect to counseling if needed\n\n"
        f"This is an automated alert from AURA Student Wellness System."
    )

    # Track results
    proctor_sent = False
    parent_sent = False
    errors = []

    # Get mail extension
    mail_ext = current_app.extensions.get('mail') if current_app else None

    # Send to PROCTOR
    if proctor_email:
        try:
            if mail_ext and Message:
                msg = Message(subject=subject, recipients=[proctor_email], body=body)
                mail_ext.send(msg)
                proctor_sent = True
                log.info('Alert sent to proctor: %s (score=%d, student=%s)', proctor_email, score, student_email)
            else:
                errors.append('Mail not configured for proctor')
                log.warning('Mail not available for proctor alert')
        except Exception as e:
            errors.append(f'Proctor email failed: {str(e)}')
            log.error('Failed to send alert to proctor %s: %s', proctor_email, e)
    else:
        errors.append('No proctor assigned')
        log.warning('No proctor found for student %s', student_email)

    # Send to PARENT
    if parent_email:
        try:
            if mail_ext and Message:
                msg = Message(subject=subject, recipients=[parent_email], body=body)
                mail_ext.send(msg)
                parent_sent = True
                log.info('Alert sent to parent: %s (score=%d, student=%s)', parent_email, score, student_email)
            else:
                errors.append('Mail not configured for parent')
                log.warning('Mail not available for parent alert')
        except Exception as e:
            errors.append(f'Parent email failed: {str(e)}')
            log.error('Failed to send alert to parent %s: %s', parent_email, e)
    else:
        log.warning('No parent email configured for student %s', student_email)

    # Log alert to database
    try:
        alerts.insert_one({
            'student_email': student_email,
            'student_name': student.get('name'),
            'score': score,
            'proctor_email': proctor_email,
            'parent_email': parent_email,
            'proctor_sent': proctor_sent,
            'parent_sent': parent_sent,
            'errors': errors,
            'created_at': datetime.utcnow(),
            'status': 'success' if (proctor_sent or parent_sent) else 'failed',
        })
    except Exception as e:
        log.error('Failed to log alert: %s', e)

    # Return result
    result = {
        'success': proctor_sent or parent_sent,
        'proctor_sent': proctor_sent,
        'parent_sent': parent_sent,
        'proctor_email': proctor_email,
        'parent_email': parent_email,
        'message': 'Alert sent successfully' if (proctor_sent or parent_sent) else f'Alert failed: {", ".join(errors)}',
        'errors': errors,
    }

    if proctor_sent or parent_sent:
        log.info('Alert successfully sent for student %s (score=%d)', student_email, score)
    else:
        log.error('Alert failed for student %s: %s', student_email, ', '.join(errors))

    return result
