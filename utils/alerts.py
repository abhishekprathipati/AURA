from flask import current_app
from utils.database import get_db
from datetime import datetime

try:
    from flask_mail import Message
except ImportError:
    Message = None


def send_institutional_alert(student_email: str, score: int) -> None:
    """Send alert to proctor and parent if configured, and log to DB."""
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

    recipients = []
    if proctor.get('email'):
        recipients.append(proctor['email'])
    if student.get('parent_email'):
        recipients.append(student['parent_email'])

    # Log alert regardless of mail availability
    alerts.insert_one({
        'student_email': student_email,
        'score': score,
        'proctor_email': proctor.get('email'),
        'parent_email': student.get('parent_email'),
        'created_at': datetime.utcnow(),
        'status': 'sent' if recipients else 'logged',
    })

    if not recipients:
        return

    mail_ext = current_app.extensions.get('mail') if current_app else None
    if not mail_ext:
        return

    subject = f"AURA Alert: High Stress ({score}) for {student.get('name','student')}"
    body = (
        f"This is an automated alert from AURA.\n\n"
        f"Student: {student.get('name','Unknown')} ({student_email})\n"
        f"Stress score: {score}\n\n"
        f"Please reach out and provide guidance."
    )

    if not Message:
        return

    msg = Message(subject=subject, recipients=recipients, body=body)
    try:
        mail_ext.send(msg)
    except Exception:
        # Fail silently; alert already logged in DB
        pass
