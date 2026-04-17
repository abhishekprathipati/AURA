from flask import current_app
from aura.utils.database import get_db
from datetime import datetime
import logging

try:
    from flask_mail import Message
except ImportError:
    Message = None

log = logging.getLogger(__name__)


def send_institutional_alert(student_email: str, score: int) -> dict:
    """
    Send stress alert to proctor, parent, AND the student directly.
    Triggered when stress score > 70.

    Recipients:
      - Proctor (assigned or department-level fallback)
      - Parent (if parent_email is set on the student account)
      - Student themselves (supportive, not alarming)

    Returns: {
        'success': bool,
        'proctor_sent': bool,
        'parent_sent': bool,
        'student_sent': bool,
        'proctor_email': str,
        'parent_email': str,
        'message': str
    }
    """
    db = get_db()
    users = db['users']
    alerts = db['alerts']

    student = users.find_one({'email': student_email}) or {}
    student_name = student.get('name', 'Student')

    # Look up the student's assigned proctor
    proctor_record = db['proctor_students'].find_one({'email': student_email, 'status': 'active'})
    proctor_email = proctor_record.get('proctor_id') if proctor_record else None
    proctor = {}
    if proctor_email:
        proctor = users.find_one({'email': proctor_email, 'role': 'proctor'}) or {}
    # Fallback: department proctor or any proctor
    if not proctor:
        dept = student.get('department') or ''
        if dept:
            proctor = users.find_one({'role': 'proctor', 'department': dept}) or {}
        if not proctor:
            proctor = users.find_one({'role': 'proctor'}) or {}

    proctor_email = proctor.get('email')
    proctor_name = proctor.get('name', 'Your Proctor')
    parent_email = student.get('parent_email')

    # ── Email: Proctor & Parent (Institutional Alert) ──────────────────────
    subject_staff = f"⚠️ AURA ALERT: High Stress Detected ({score}/100) — {student_name}"
    body_staff = (
        f"AURA Student Wellness System — Stress Alert\n"
        f"{'='*55}\n\n"
        f"A student under your care has recorded a HIGH stress score.\n\n"
        f"  Student Name   : {student_name}\n"
        f"  Student Email  : {student_email}\n"
        f"  Stress Score   : {score}/100\n"
        f"  Department     : {student.get('department', 'N/A')}\n"
        f"  Alert Time     : {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}\n\n"
        f"Recommended Actions:\n"
        f"  1. Reach out to the student promptly via message or in-person\n"
        f"  2. Offer emotional support and active listening\n"
        f"  3. Connect to campus counselling service if needed\n\n"
        f"Indian Support Helplines (share with student if required):\n"
        f"  • iCall (TISS)          : 9152987821\n"
        f"  • Vandrevala Foundation : 9999 666 555 (24/7, Free)\n"
        f"  • AASRA                 : 9820466726\n"
        f"  • National Emergency    : 112\n\n"
        f"{'='*55}\n"
        f"This is an automated alert from the AURA Student Wellness System.\n"
        f"Please do not reply to this email.\n"
    )

    # ── Email: Student (Supportive, non-alarming) ──────────────────────────
    subject_student = f"💙 AURA: We noticed you might be feeling overwhelmed"
    body_student = (
        f"Hi {student_name},\n\n"
        f"AURA's wellness monitor has detected that your current stress level is HIGH ({score}/100). "
        f"This is just a gentle check-in — you're not in trouble.\n\n"
        f"Your proctor, {proctor_name}, has been notified and is here to support you.\n\n"
        f"Right now, please try:\n"
        f"  • Taking 5 deep breaths (box breathing: inhale 4s, hold 4s, exhale 4s)\n"
        f"  • Drinking a glass of water and stepping away from your screen\n"
        f"  • Talking to someone you trust\n\n"
        f"Free & Confidential Indian Helplines:\n"
        f"  • iCall (TISS)          : 9152987821  (Mon–Sat, 8am–10pm)\n"
        f"  • Vandrevala Foundation : 9999 666 555 (24/7, multilingual)\n"
        f"  • AASRA Crisis Support  : 9820466726\n"
        f"  • National Emergency    : 112\n\n"
        f"You can also open the AURA Mental Chatbot anytime for immediate, anonymous support.\n\n"
        f"You've got this. 💙\n"
        f"— The AURA Wellness Team\n"
    )

    proctor_sent = False
    parent_sent = False
    student_sent = False
    errors = []

    mail_ext = current_app.extensions.get('mail') if current_app else None

    # ── Send to PROCTOR ────────────────────────────────────────────────────
    if proctor_email:
        try:
            if mail_ext and Message:
                msg = Message(subject=subject_staff, recipients=[proctor_email], body=body_staff)
                mail_ext.send(msg)
                proctor_sent = True
                log.info('Stress alert sent to proctor: %s (score=%d, student=%s)', proctor_email, score, student_email)
            else:
                errors.append('Mail not configured')
                log.warning('Mail not available for proctor alert')
        except Exception as e:
            errors.append(f'Proctor email failed: {str(e)}')
            log.error('Failed to send alert to proctor %s: %s', proctor_email, e)
    else:
        errors.append('No proctor assigned')
        log.warning('No proctor found for student %s', student_email)

    # ── Send to PARENT ─────────────────────────────────────────────────────
    if parent_email:
        try:
            if mail_ext and Message:
                msg = Message(subject=subject_staff, recipients=[parent_email], body=body_staff)
                mail_ext.send(msg)
                parent_sent = True
                log.info('Stress alert sent to parent: %s (score=%d, student=%s)', parent_email, score, student_email)
            else:
                errors.append('Mail not configured for parent')
        except Exception as e:
            errors.append(f'Parent email failed: {str(e)}')
            log.error('Failed to send alert to parent %s: %s', parent_email, e)
    else:
        log.warning('No parent email configured for student %s', student_email)

    # ── Send to STUDENT (supportive message) ───────────────────────────────
    try:
        if mail_ext and Message:
            msg = Message(subject=subject_student, recipients=[student_email], body=body_student)
            mail_ext.send(msg)
            student_sent = True
            log.info('Supportive stress alert sent to student: %s (score=%d)', student_email, score)
        else:
            errors.append('Mail not configured for student')
    except Exception as e:
        errors.append(f'Student email failed: {str(e)}')
        log.error('Failed to send supportive alert to student %s: %s', student_email, e)

    # ── Log to database ────────────────────────────────────────────────────
    try:
        alerts.insert_one({
            'alert_type': 'HIGH_STRESS',
            'student_email': student_email,
            'student_name': student_name,
            'score': score,
            'proctor_email': proctor_email,
            'parent_email': parent_email,
            'proctor_sent': proctor_sent,
            'parent_sent': parent_sent,
            'student_sent': student_sent,
            'errors': errors,
            'created_at': datetime.utcnow(),
            'status': 'success' if (proctor_sent or parent_sent or student_sent) else 'failed',
        })
    except Exception as e:
        log.error('Failed to log alert: %s', e)

    success = proctor_sent or parent_sent or student_sent
    result = {
        'success': success,
        'proctor_sent': proctor_sent,
        'parent_sent': parent_sent,
        'student_sent': student_sent,
        'proctor_email': proctor_email,
        'parent_email': parent_email,
        'message': 'Alert sent successfully' if success else f'Alert failed: {", ".join(errors)}',
        'errors': errors,
    }

    if success:
        log.info('Stress alert pipeline complete for %s (score=%d): proctor=%s, parent=%s, student=%s',
                 student_email, score, proctor_sent, parent_sent, student_sent)
    else:
        log.error('ALL stress alerts failed for student %s: %s', student_email, ', '.join(errors))

    return result


def send_crisis_alert(student_email: str, student_name: str, message: str,
                     risk_level: str = 'HIGH') -> dict:
    """
    Send CRITICAL crisis alert (self-harm, suicidal ideation, threats).

    This is URGENT and bypasses all thresholds.
    Sent IMMEDIATELY to proctor and parent with full message content.

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

    # Find proctor
    proctor_record = db['proctor_students'].find_one({'email': student_email, 'status': 'active'})
    proctor_email = proctor_record.get('proctor_id') if proctor_record else None
    proctor = {}
    if proctor_email:
        proctor = users.find_one({'email': proctor_email, 'role': 'proctor'}) or {}
    if not proctor:
        dept = student.get('department') or ''
        if dept:
            proctor = users.find_one({'role': 'proctor', 'department': dept}) or {}
        if not proctor:
            proctor = users.find_one({'role': 'proctor'}) or {}

    proctor_email = proctor.get('email')
    parent_email = student.get('parent_email')

    # CRITICAL ALERT EMAIL
    subject = f"[CRITICAL] CRISIS ALERT - {student_name} - IMMEDIATE ACTION REQUIRED"

    body = f"""
CRISIS ALERT — IMMEDIATE ACTION REQUIRED
===============================================

Risk Level      : {risk_level}
Student Name    : {student_name}
Student Email   : {student_email}
Department      : {student.get('department', 'N/A')}
Report Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}

STUDENT MESSAGE:
"{message}"

ACTION REQUIRED (DO THIS NOW):
1. CONTACT STUDENT IMMEDIATELY — by phone or in-person
2. Ensure their PHYSICAL SAFETY at all times
3. Do NOT leave them alone if they express intent to harm
4. Connect them to professional mental health support:

   Indian Crisis Helplines (Free & Confidential):
   • iCall (TISS)           : 9152987821  (Mon–Sat, 8am–10pm)
   • Vandrevala Foundation  : 9999 666 555 (24/7, multilingual)
   • AASRA Crisis Support   : 9820466726
   • Snehi                  : 044-24640050
   • National Emergency     : 112
   • Campus Counsellor      : Contact institution welfare office

CONFIDENTIAL — FOR AUTHORISED PERSONNEL ONLY
AURA Student Wellness System
    """.strip()

    proctor_sent = False
    parent_sent = False
    errors = []

    # Get mail extension
    mail_ext = current_app.extensions.get('mail') if current_app else None

    # SEND TO PROCTOR (PRIORITY)
    if proctor_email:
        try:
            if mail_ext and Message:
                msg = Message(subject=subject, recipients=[proctor_email], body=body)
                mail_ext.send(msg)
                proctor_sent = True
                log.critical('CRISIS ALERT sent to proctor %s: student=%s, risk_level=%s',
                           proctor_email, student_email, risk_level)
            else:
                errors.append('Mail not configured for proctor')
        except Exception as e:
            errors.append(f'Proctor alert failed: {str(e)}')
            log.error('FAILED to send CRISIS ALERT to proctor %s: %s', proctor_email, e)
    else:
        errors.append('No proctor assigned')
        log.warning('No proctor found for crisis alert: %s', student_email)

    # SEND TO PARENT (PRIORITY)
    if parent_email:
        try:
            if mail_ext and Message:
                msg = Message(subject=subject, recipients=[parent_email], body=body)
                mail_ext.send(msg)
                parent_sent = True
                log.critical('CRISIS ALERT sent to parent %s: student=%s, risk_level=%s',
                           parent_email, student_email, risk_level)
            else:
                errors.append('Mail not configured for parent')
        except Exception as e:
            errors.append(f'Parent alert failed: {str(e)}')
            log.error('FAILED to send CRISIS ALERT to parent %s: %s', parent_email, e)
    else:
        log.warning('No parent email configured for crisis alert: %s', student_email)

    # LOG CRISIS ALERT (CRITICAL RECORD)
    try:
        alerts.insert_one({
            'alert_type': 'CRISIS_DETECTION',
            'student_email': student_email,
            'student_name': student_name,
            'risk_level': risk_level,
            'message_content': message,
            'proctor_email': proctor_email,
            'parent_email': parent_email,
            'proctor_sent': proctor_sent,
            'parent_sent': parent_sent,
            'errors': errors,
            'created_at': datetime.utcnow(),
            'status': 'critical',
            'requires_immediate_action': True,
        })
        log.critical('Crisis alert logged: student=%s, risk=%s', student_email, risk_level)
    except Exception as e:
        log.error('Failed to log crisis alert: %s', e)

    result = {
        'success': proctor_sent or parent_sent,
        'proctor_sent': proctor_sent,
        'parent_sent': parent_sent,
        'proctor_email': proctor_email,
        'parent_email': parent_email,
        'message': 'CRISIS ALERT sent successfully' if (proctor_sent or parent_sent) else f'CRISIS ALERT failed: {", ".join(errors)}',
        'errors': errors,
    }

    if proctor_sent or parent_sent:
        log.critical('CRISIS ALERT successfully sent for %s (risk=%s)', student_email, risk_level)
    else:
        log.critical('CRISIS ALERT FAILED for %s: %s', student_email, ', '.join(errors))

    return result
