from flask import Blueprint, jsonify, request, render_template, session, Response, current_app
from functools import wraps
from datetime import datetime, timedelta
import uuid
import io
import csv
from utils.auth_helpers import login_required, demo_restricted
from utils.database import get_db
from utils.audit_logger import log_activity, AuditAction
from utils.rate_limit import apply_rate_limit, Limits
from utils.access_control import (
    get_visible_student_ids, get_visible_students, get_incident_filter,
    can_access_student, create_anonymous_id, get_current_user,
)
from utils.helpers import safe_error

proctor_bp = Blueprint('proctor', __name__)

# Helper to access limiter from app context
def _get_limiter():
    try:
        return current_app.limiter
    except (RuntimeError, AttributeError):
        return None

# ---------------------------------------------
# Helpers
# ---------------------------------------------

def proctor_only(f):
    """Ensure the current user is a proctor or HOD."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('user_role')
        if role not in ['proctor', 'hod']:
            return jsonify({'error': 'Unauthorized access'}), 403
        return f(*args, **kwargs)
    return decorated_function


_indexes_ensured = False

def _ensure_indexes(db):
    """Create indexes once per process lifetime (idempotent guard)."""
    global _indexes_ensured
    if _indexes_ensured:
        return
    db['risk_incidents'].create_index('incident_id', unique=True)
    db['risk_incidents'].create_index('status')
    db['risk_incidents'].create_index('risk_level')
    db['risk_incidents'].create_index('timestamp')

    db['proctor_actions'].create_index('action_id', unique=True)
    db['proctor_actions'].create_index('incident_id')
    db['proctor_actions'].create_index('proctor_id')
    db['proctor_actions'].create_index('timestamp')

    db['system_status'].create_index('status')
    _indexes_ensured = True


def _time_since(ts: datetime) -> str:
    now = datetime.utcnow()
    diff = now - ts
    if diff.days > 0:
        return f"{diff.days}d"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600}h"
    if diff.seconds > 60:
        return f"{diff.seconds // 60}m"
    return "Just now"


def _trend_icon(trend: str) -> str:
    return {
        'RISING': 'â†‘',
        'FALLING': 'â†“',
        'STABLE': 'â†’',
    }.get(trend, 'â†’')


def _risk_color(risk_level: str) -> str:
    return {
        'HIGH': '#dc3545',
        'MEDIUM': '#ffc107',
        'LOW': '#198754',
    }.get(risk_level, '#6c757d')


def _severity_score(risk_level: str) -> int:
    return {
        'HIGH': 3,
        'MEDIUM': 2,
        'LOW': 1,
    }.get(risk_level, 0)


def _serialize_incident(doc: dict) -> dict:
    return {
        'incident_id': doc.get('incident_id'),
        'anonymous_student_id': doc.get('anonymous_student_id'),
        'risk_level': doc.get('risk_level'),
        'trend': doc.get('trend'),
        'trend_icon': _trend_icon(doc.get('trend')),
        'risk_color': _risk_color(doc.get('risk_level')),
        'severity_score': _severity_score(doc.get('risk_level')),
        'trigger_source': doc.get('trigger_source'),
        'incident_type': doc.get('incident_type'),
        'message_excerpt': doc.get('message_excerpt'),
        'details': doc.get('details'),
        'room_name': doc.get('room_name'),
        'timestamp': doc.get('timestamp').isoformat() if doc.get('timestamp') else None,
        'report_count': doc.get('report_count', 1),
        'status': doc.get('status', 'UNREVIEWED'),
        'case_status': doc.get('case_status', 'new'),
        'assigned_to': doc.get('assigned_to'),
        'auto_triggered': doc.get('auto_triggered', False),
        'time_since_trigger': _time_since(doc.get('timestamp')) if doc.get('timestamp') else None,
    }


def _serialize_action(doc: dict) -> dict:
    return {
        'action_id': doc.get('action_id'),
        'incident_id': doc.get('incident_id'),
        'proctor_id': doc.get('proctor_id'),
        'action_type': doc.get('action_type'),
        'reason_code': doc.get('reason_code'),
        'details': doc.get('details'),
        'old_status': doc.get('old_status'),
        'new_status': doc.get('new_status'),
        'old_case_status': doc.get('old_case_status'),
        'new_case_status': doc.get('new_case_status'),
        'timestamp': doc.get('timestamp').isoformat() if doc.get('timestamp') else None,
        'time_since': _time_since(doc.get('timestamp')) if doc.get('timestamp') else None,
    }


def _default_status():
    return {
        'status': 'LIVE',
        'active_students': 0,
        'active_alerts': 0,
        'connection_hub_state': 'CALM',
        'last_update': datetime.utcnow(),
    }

# ---------------------------------------------
# Dashboard Route
# ---------------------------------------------

@proctor_bp.route('/dashboard')
@login_required
@proctor_only
def proctor_dashboard():
    proctor_id = session.get('user_email', 'UNKNOWN')
    proctor_name = session.get('user_name', 'Proctor')
    return render_template('proctor_dashboard.html', proctor_id=proctor_id, proctor_name=proctor_name)


@proctor_bp.route('/student/<anonymous_id>')
@login_required
@proctor_only
def student_detail(anonymous_id):
    """View anonymous student details for proctor review."""
    proctor_id = session.get('user_email', 'UNKNOWN')
    return render_template('student_detail.html', 
                         anonymous_id=anonymous_id, 
                         proctor_id=proctor_id)


@proctor_bp.route('/api/student/add', methods=['POST'])
@login_required
@proctor_only
@apply_rate_limit(Limits.MODERATE)
def add_student():
    """Add a new student under this proctor's ward."""
    try:
        data = request.get_json() or {}

        # â”€â”€ Required fields â”€â”€
        name = (data.get('name') or '').strip()
        roll_number = (data.get('roll_number') or '').strip()
        email = (data.get('email') or '').strip()
        department = (data.get('department') or '').strip()
        parent_name = (data.get('parent_name') or '').strip()
        parent_phone = (data.get('parent_phone') or '').strip()

        if not all([name, roll_number, email, department, parent_name, parent_phone]):
            return jsonify({'success': False, 'error': 'Please fill all required fields (name, roll, email, department, parent name & phone).'}), 400

        VALID_DEPTS = {'AIML', 'CSE', 'ECE', 'CIVIL', 'MECH'}
        if department not in VALID_DEPTS:
            return jsonify({'success': False, 'error': 'Invalid department. Must be one of: AIML, CSE, ECE, CIVIL, MECH.'}), 400

        db = get_db()
        proctor_id = session.get('user_email', 'UNKNOWN')

        # â”€â”€ Check duplicates â”€â”€
        if db['proctor_students'].find_one({'roll_number': roll_number}):
            return jsonify({'success': False, 'error': f'Student with roll number {roll_number} already exists.'}), 409
        if db['proctor_students'].find_one({'email': email}):
            return jsonify({'success': False, 'error': f'Student with email {email} already exists.'}), 409

        # â”€â”€ Build student record â”€â”€
        from utils.auth_helpers import hash_password
        default_password = hash_password('Aura@123')  # default pwd for all students
        # Use centralized anonymous ID helper (single source of truth)
        anonymous_id = create_anonymous_id(email)

        student_record = {
            'student_id': str(uuid.uuid4()),
            'anonymous_id': anonymous_id,
            'name': name,
            'roll_number': roll_number.upper(),
            'email': email.lower(),
            'department': department,
            'semester': data.get('semester', '4'),
            'section': data.get('section', 'A'),
            'risk_level': (data.get('risk_level') or 'low').upper(),
            'blood_group': data.get('blood_group', ''),
            'notes': data.get('notes', ''),
            'proctor_id': proctor_id,
            'status': 'active',
            'created_at': datetime.utcnow(),
            'created_by': proctor_id,
        }

        # â”€â”€ Insert student â”€â”€
        db['proctor_students'].insert_one(student_record)

        # â”€â”€ Also create a user login for the student â”€â”€
        existing_user = db['users'].find_one({'email': email.lower()})
        if not existing_user:
            db['users'].insert_one({
                'email': email.lower(),
                'hashed_password': default_password,
                'name': name,
                'role': 'student',
                'department': department,
                'roll_number': roll_number.upper(),
                'parent_phone': parent_phone,
                'created_at': datetime.utcnow(),
            })
        else:
            # Patch missing fields if user already exists
            update_fields = {}
            if not existing_user.get('roll_number'):
                update_fields['roll_number'] = roll_number.upper()
            if not existing_user.get('parent_phone'):
                update_fields['parent_phone'] = parent_phone
            if update_fields:
                db['users'].update_one({'email': email.lower()}, {'$set': update_fields})

        # â”€â”€ Create parent record â”€â”€
        parent_record = {
            'student_roll': roll_number.upper(),
            'parent_name': parent_name,
            'parent_phone': parent_phone,
            'parent_email': (data.get('parent_email') or '').strip(),
            'relationship': data.get('parent_relationship', 'parent'),
            'auth_type': 'otp',
            'created_at': datetime.utcnow(),
            'is_active': True,
            'notifications_enabled': True,
        }
        db['parents'].update_one(
            {'student_roll': roll_number.upper()},
            {'$set': parent_record},
            upsert=True,
        )

        log_activity(
            action=AuditAction.ADD_STUDENT,
            target_type='student',
            target_id=anonymous_id,
            metadata={'email': email, 'name': name, 'roll_number': roll_number, 'department': department}
        )

        return jsonify({
            'success': True,
            'message': f'Student {name} ({roll_number}) added successfully.',
            'student_id': student_record['student_id'],
            'anonymous_id': anonymous_id,
        })
    except Exception as exc:
        current_app.logger.error('add_student error: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500


@proctor_bp.route('/api/student/<anonymous_id>/details', methods=['GET'])
@login_required
@proctor_only
def get_student_details(anonymous_id):
    """Get FULL intervention profile for an anonymous student."""
    try:
        db = get_db()

        # â”€â”€ RBAC: verify access to this student â”€â”€
        if not can_access_student(anonymous_id):
            return jsonify({'success': False, 'error': 'Access denied â€” student not in your scope'}), 403

        # â”€â”€ All incidents â”€â”€
        incidents = list(db['risk_incidents'].find(
            {'anonymous_student_id': anonymous_id},
            sort=[('timestamp', -1)]
        ))

        # â”€â”€ All proctor actions for these incidents â”€â”€
        incident_ids = [inc.get('incident_id') for inc in incidents]
        actions = list(db['proctor_actions'].find(
            {'incident_id': {'$in': incident_ids}},
            sort=[('timestamp', -1)]
        ))

        # â”€â”€ Proctor notes â”€â”€
        notes = list(db['proctor_notes'].find(
            {'anonymous_student_id': anonymous_id},
            sort=[('timestamp', -1)]
        ).limit(20))
        for n in notes:
            n['_id'] = str(n['_id'])
            if isinstance(n.get('timestamp'), datetime):
                n['time_ago'] = _time_since(n['timestamp'])
                n['timestamp'] = n['timestamp'].isoformat()

        # â”€â”€ Support tickets for this student (match via anonymous_id on incidents) â”€â”€
        support_tickets = list(db['support_requests'].find(
            sort=[('timestamp', -1)]
        ).limit(50))
        # filter to those matching this anonymous student's incidents
        # (support_requests use student_id=email, incidents use anonymous_id)
        student_ticket_types = set()
        for inc in incidents:
            if inc.get('incident_type') in ('support_request', 'urgent_help', 'critical_stress_auto', 'session_booking'):
                student_ticket_types.add(inc.get('incident_type'))

        # â”€â”€ Counseling sessions (matched via anonymous_id) â”€â”€
        sessions = list(db['counseling_sessions'].find(
            {'anonymous_id': anonymous_id},
            sort=[('created_at', -1)]
        ).limit(10))
        for s in sessions:
            s['_id'] = str(s['_id'])
            if isinstance(s.get('created_at'), datetime):
                s['created_at'] = s['created_at'].isoformat()

        # â”€â”€ Stats â”€â”€
        total_incidents = len(incidents)
        high_risk_count = sum(1 for i in incidents if i.get('risk_level') == 'HIGH')
        unreviewed_count = sum(1 for i in incidents if i.get('status') == 'UNREVIEWED')
        auto_escalations = sum(1 for i in incidents if i.get('auto_triggered'))

        # â”€â”€ Determine dominant trigger â”€â”€
        trigger_counts = {}
        for i in incidents:
            t = i.get('trigger_source', 'unknown')
            trigger_counts[t] = trigger_counts.get(t, 0) + 1
        dominant_trigger = max(trigger_counts, key=trigger_counts.get) if trigger_counts else 'none'

        # â”€â”€ Risk stability index â”€â”€
        recent_incidents = [i for i in incidents if i.get('timestamp') and
                           (datetime.utcnow() - i['timestamp']).days <= 7]
        risk_levels_7d = [i.get('risk_level', 'LOW') for i in recent_incidents]
        high_count_7d = risk_levels_7d.count('HIGH')
        total_7d = len(risk_levels_7d)

        if total_7d == 0:
            stability = 'stable'
            stability_label = 'No recent activity'
        elif high_count_7d >= 3:
            stability = 'critical'
            stability_label = 'High stress and rising â€” danger'
        elif high_count_7d >= 1 and total_7d >= 3:
            stability = 'volatile'
            stability_label = 'Medium stress but volatile â€” monitor'
        elif total_7d >= 2 and high_count_7d == 0:
            stability = 'improving'
            stability_label = 'Stress present but improving'
        else:
            stability = 'stable'
            stability_label = 'Low activity â€” stable'

        # â”€â”€ Current case status (from most recent incident) â”€â”€
        current_case = incidents[0].get('case_status', 'new') if incidents else 'new'
        assigned_to = incidents[0].get('assigned_to') if incidents else None

        return jsonify({
            'success': True,
            'data': {
                'anonymous_id': anonymous_id,
                'total_incidents': total_incidents,
                'high_risk_count': high_risk_count,
                'unreviewed_count': unreviewed_count,
                'auto_escalations': auto_escalations,
                'dominant_trigger': dominant_trigger.replace('_', ' ').title(),
                'case_status': current_case,
                'assigned_to': assigned_to,
                'stability': stability,
                'stability_label': stability_label,
                'incidents': [_serialize_incident(i) for i in incidents[:20]],
                'actions': [_serialize_action(a) for a in actions[:20]],
                'notes': notes,
                'sessions': sessions,
                'trigger_breakdown': trigger_counts,
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CASE WORKFLOW: Status transitions & assignment
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@proctor_bp.route('/api/case/<incident_id>/status', methods=['PATCH'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.MODERATE)
def update_case_status(incident_id):
    """Update case workflow status: new â†’ reviewing â†’ assigned â†’ contacted â†’ monitoring â†’ resolved."""
    try:
        db = get_db()
        data = request.get_json() or {}
        new_status = data.get('case_status', '')
        proctor_id = session.get('user_email', 'UNKNOWN')

        valid = ('new', 'reviewing', 'assigned', 'contacted', 'monitoring', 'resolved')
        if new_status not in valid:
            return jsonify({'error': f'Invalid status. Must be one of: {valid}'}), 400

        incident = db['risk_incidents'].find_one({'incident_id': incident_id})
        if not incident:
            return jsonify({'error': 'Incident not found'}), 404

        # â”€â”€ RBAC: verify access â”€â”€
        if not can_access_student(incident.get('anonymous_student_id', '')):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        old_status = incident.get('case_status', 'new')

        # Update incident
        update_fields = {
            'case_status': new_status,
            'status': 'REVIEWED' if new_status not in ('new',) else incident.get('status', 'UNREVIEWED'),
        }
        if new_status == 'resolved':
            update_fields['resolved_by'] = proctor_id
            update_fields['resolved_at'] = datetime.utcnow()

        db['risk_incidents'].update_one(
            {'incident_id': incident_id},
            {'$set': update_fields}
        )

        # Log action in audit trail
        db['proctor_actions'].insert_one({
            'action_id': str(uuid.uuid4()),
            'incident_id': incident_id,
            'proctor_id': proctor_id,
            'action_type': 'STATUS_CHANGE',
            'reason_code': f'{old_status} â†’ {new_status}',
            'details': f'Case status changed from {old_status} to {new_status}',
            'timestamp': datetime.utcnow(),
        })

        log_activity(
            action=AuditAction.CASE_STATUS_CHANGE,
            target_type='incident',
            target_id=incident_id,
            metadata={'old_status': old_status, 'new_status': new_status, 'anonymous_student_id': incident.get('anonymous_student_id')}
        )

        return jsonify({'success': True, 'message': f'Case status updated to {new_status}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/case/<incident_id>/assign', methods=['POST'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.MODERATE)
def assign_counselor(incident_id):
    """Assign a counselor to a case and set status to 'assigned'."""
    try:
        db = get_db()
        data = request.get_json() or {}
        counselor = data.get('counselor', '').strip()
        proctor_id = session.get('user_email', 'UNKNOWN')

        if not counselor:
            return jsonify({'error': 'Counselor name is required'}), 400

        incident = db['risk_incidents'].find_one({'incident_id': incident_id})
        if not incident:
            return jsonify({'error': 'Incident not found'}), 404

        # â”€â”€ RBAC: verify access â”€â”€
        if not can_access_student(incident.get('anonymous_student_id', '')):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        db['risk_incidents'].update_one(
            {'incident_id': incident_id},
            {'$set': {
                'assigned_to': counselor,
                'case_status': 'assigned',
                'status': 'REVIEWED'
            }}
        )

        db['proctor_actions'].insert_one({
            'action_id': str(uuid.uuid4()),
            'incident_id': incident_id,
            'proctor_id': proctor_id,
            'action_type': 'ASSIGN',
            'reason_code': 'COUNSELOR_ASSIGNED',
            'details': f'Assigned to counselor: {counselor}',
            'timestamp': datetime.utcnow(),
        })

        log_activity(
            action=AuditAction.ASSIGN_COUNSELOR,
            target_type='incident',
            target_id=incident_id,
            metadata={'counselor': counselor, 'anonymous_student_id': incident.get('anonymous_student_id')}
        )

        return jsonify({'success': True, 'message': f'Assigned to {counselor}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PROCTOR NOTES: Private intervention notes
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@proctor_bp.route('/api/notes/<anonymous_id>', methods=['GET'])
@login_required
@proctor_only
def get_proctor_notes(anonymous_id):
    """Get all proctor notes for a student."""
    try:
        # â”€â”€ RBAC: verify access â”€â”€
        if not can_access_student(anonymous_id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        db = get_db()
        notes = list(db['proctor_notes'].find(
            {'anonymous_student_id': anonymous_id},
            sort=[('timestamp', -1)]
        ).limit(30))
        for n in notes:
            n['_id'] = str(n['_id'])
            if isinstance(n.get('timestamp'), datetime):
                n['time_ago'] = _time_since(n['timestamp'])
                n['timestamp'] = n['timestamp'].isoformat()
        return jsonify({'success': True, 'notes': notes}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/notes/<anonymous_id>', methods=['POST'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.MODERATE)
def add_proctor_note(anonymous_id):
    """Add a private intervention note for a student."""
    try:
        # â”€â”€ RBAC: verify access â”€â”€
        if not can_access_student(anonymous_id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        db = get_db()
        data = request.get_json() or {}
        note_text = data.get('note', '').strip()
        is_urgent = data.get('urgent', False)
        risk_score = data.get('risk_score')  # optional 0-100
        flag_monitoring = data.get('flag_monitoring', False)
        follow_up_date = data.get('follow_up_date')  # optional YYYY-MM-DD

        if not note_text:
            return jsonify({'error': 'Note text is required'}), 400

        proctor_id = session.get('user_email', 'UNKNOWN')
        proctor_name = session.get('user_name', 'Proctor')

        note_doc = {
            'anonymous_student_id': anonymous_id,
            'proctor_id': proctor_id,
            'proctor_name': proctor_name,
            'note': note_text,
            'urgent': is_urgent,
            'risk_score': risk_score,
            'flag_monitoring': flag_monitoring,
            'follow_up_date': follow_up_date,
            'timestamp': datetime.utcnow(),
        }
        db['proctor_notes'].insert_one(note_doc)

        # If flagged for monitoring, update all open incidents
        if flag_monitoring:
            db['risk_incidents'].update_many(
                {'anonymous_student_id': anonymous_id, 'case_status': {'$nin': ['resolved']}},
                {'$set': {'case_status': 'monitoring'}}
            )

        log_activity(
            action=AuditAction.ADD_NOTE,
            target_type='student',
            target_id=anonymous_id,
            metadata={'urgent': is_urgent, 'flag_monitoring': flag_monitoring, 'follow_up': follow_up_date}
        )

        return jsonify({'success': True, 'message': 'Note added'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/dashboard/summary', methods=['GET'])
@login_required
@proctor_only
def get_dashboard_summary():
    """Get comprehensive dashboard summary â€” RBAC-scoped to visible students."""
    try:
        db = get_db()
        _ensure_indexes(db)
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = datetime.utcnow() - timedelta(days=7)
        
        # ── RBAC: get visible student IDs via centralized helper ──
        visible_ids = get_visible_student_ids()
        visible_studs = get_visible_students()
        visible_emails = [s.get('email', '') for s in visible_studs if s.get('email')]
        scope_filter = {'anonymous_student_id': {'$in': visible_ids}} if visible_ids else {'anonymous_student_id': {'$in': []}}
        
        # â”€â”€ Count incidents by review status (scoped) â”€â”€
        unreviewed = db['risk_incidents'].count_documents({**scope_filter, 'status': 'UNREVIEWED'})
        reviewed = db['risk_incidents'].count_documents({**scope_filter, 'status': 'REVIEWED'})
        dismissed = db['risk_incidents'].count_documents({**scope_filter, 'status': 'DISMISSED'})
        escalated = db['risk_incidents'].count_documents({**scope_filter, 'status': 'ESCALATED'})
        
        # â”€â”€ Count by risk level (unreviewed, scoped) â”€â”€
        high_risk = db['risk_incidents'].count_documents({**scope_filter, 'risk_level': 'HIGH', 'status': 'UNREVIEWED'})
        medium_risk = db['risk_incidents'].count_documents({**scope_filter, 'risk_level': 'MEDIUM', 'status': 'UNREVIEWED'})
        low_risk = db['risk_incidents'].count_documents({**scope_filter, 'risk_level': 'LOW', 'status': 'UNREVIEWED'})
        
        # â”€â”€ Student count â”€â”€
        my_students = len(visible_ids)
        
        # â”€â”€ Needs Immediate Action (scoped) â”€â”€
        if visible_ids:
            needs_action = db['risk_incidents'].count_documents({
                **scope_filter, 'status': 'UNREVIEWED'
            })
            pending_followups = db['risk_incidents'].count_documents({
                **scope_filter, 'case_status': {'$in': ['assigned', 'contacted', 'monitoring']}
            })
            resolved_today = db['risk_incidents'].count_documents({
                **scope_filter, 'case_status': 'resolved',
                '$or': [
                    {'resolved_at': {'$gte': today_start}},
                    {'timestamp': {'$gte': today_start}, 'status': {'$in': ['DISMISSED', 'REMOVED', 'RESOLVED']}}
                ]
            })
        else:
            needs_action = 0
            pending_followups = 0
            resolved_today = 0
        
        # â”€â”€ Today's activity (scoped) â”€â”€
        incidents_today = db['risk_incidents'].count_documents({**scope_filter, 'timestamp': {'$gte': today_start}})
        actions_today = db['proctor_actions'].count_documents({'timestamp': {'$gte': today_start}})
        
        # â”€â”€ Weekly trend (scoped) â”€â”€
        incidents_this_week = db['risk_incidents'].count_documents({**scope_filter, 'timestamp': {'$gte': week_start}})
        
        # â”€â”€ Auto-escalations (scoped) â”€â”€
        auto_total = db['risk_incidents'].count_documents({**scope_filter, 'auto_triggered': True})
        auto_today = db['risk_incidents'].count_documents({**scope_filter, 'auto_triggered': True, 'timestamp': {'$gte': today_start}})
        
        return jsonify({
            'success': True,
            'data': {
                'pending': {
                    'total': unreviewed,
                    'high': high_risk,
                    'medium': medium_risk,
                    'low': low_risk
                },
                'resolved': {
                    'reviewed': reviewed,
                    'dismissed': dismissed,
                    'escalated': escalated
                },
                'today': {
                    'incidents': incidents_today,
                    'actions': actions_today
                },
                'week': {
                    'incidents': incidents_this_week
                },
                'needs_action': needs_action,
                'pending_followups': pending_followups,
                'resolved_today': resolved_today,
                'my_students': my_students,
                'auto_escalations': auto_total,
                'auto_escalations_today': auto_today,
                'grievances_pending': db['grievances'].count_documents({
                    'status': 'pending',
                    'user_email': {'$in': visible_emails}
                }) if visible_emails else 0,
                'grievances_total': db['grievances'].count_documents({
                    'user_email': {'$in': visible_emails}
                }) if visible_emails else 0,
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MY STUDENTS: Full student list for this proctor
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@proctor_bp.route('/api/my-students', methods=['GET'])
@login_required
@proctor_only
def get_my_students():
    """Get all students assigned to this proctor with their wellness & risk data."""
    try:
        db = get_db()

        # â”€â”€ RBAC: use centralized helper (proctor sees assigned, HOD sees dept) â”€â”€
        students = get_visible_students()

        results = []
        for stu in students:
            anon_id = stu.get('anonymous_id', '')
            email = stu.get('email', '')

            # Get latest wellness data
            latest_stress = db['student_wellness'].find_one(
                {'student_id': email, 'data_type': 'stress'},
                sort=[('timestamp', -1)]
            )
            latest_mood = db['student_wellness'].find_one(
                {'student_id': email, 'data_type': 'mood'},
                sort=[('timestamp', -1)]
            )

            # Get 7-day average stress
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_stress = list(db['student_wellness'].find({
                'student_id': email,
                'data_type': 'stress',
                'timestamp': {'$gte': week_ago}
            }))
            avg_stress_7d = int(sum(s.get('value', 0) for s in week_stress) / max(len(week_stress), 1)) if week_stress else 0

            # Calculate trend from last 7 days
            if len(week_stress) >= 2:
                sorted_stress = sorted(week_stress, key=lambda x: x.get('timestamp', datetime.min))
                first_half = sorted_stress[:len(sorted_stress) // 2]
                second_half = sorted_stress[len(sorted_stress) // 2:]
                avg_first = sum(s.get('value', 0) for s in first_half) / max(len(first_half), 1)
                avg_second = sum(s.get('value', 0) for s in second_half) / max(len(second_half), 1)
                if avg_second - avg_first > 5:
                    stress_trend = 'increasing'
                elif avg_first - avg_second > 5:
                    stress_trend = 'improving'
                else:
                    stress_trend = 'stable'
            else:
                stress_trend = 'stable'

            # Get latest incident
            latest_incident = db['risk_incidents'].find_one(
                {'anonymous_student_id': anon_id},
                sort=[('timestamp', -1)]
            )

            # Count unreviewed incidents
            unreviewed = db['risk_incidents'].count_documents({
                'anonymous_student_id': anon_id,
                'status': 'UNREVIEWED'
            })

            # Determine risk level
            risk_level = 'LOW'
            if latest_incident:
                risk_level = latest_incident.get('risk_level', 'LOW')

            current_stress = latest_stress.get('value', 0) if latest_stress else 0
            current_mood = latest_mood.get('value', 3) if latest_mood else 3

            # Determine status based on data
            if current_stress >= 75 or risk_level == 'HIGH':
                status_label = 'needs_intervention'
            elif current_stress >= 50 or risk_level == 'MEDIUM' or unreviewed > 0:
                status_label = 'monitor'
            else:
                status_label = 'normal'

            last_update = None
            if latest_stress and latest_stress.get('timestamp'):
                last_update = _time_since(latest_stress['timestamp'])
            elif latest_incident and latest_incident.get('timestamp'):
                last_update = _time_since(latest_incident['timestamp'])

            results.append({
                'anonymous_id': anon_id,
                'name': stu.get('name', 'Unknown'),
                'roll_number': stu.get('roll_number', ''),
                'email': email,
                'department': stu.get('department', ''),
                'semester': stu.get('semester', ''),
                'section': stu.get('section', ''),
                'current_stress': current_stress,
                'current_mood': current_mood,
                'avg_stress_7d': avg_stress_7d,
                'stress_trend': stress_trend,
                'risk_level': risk_level,
                'status': status_label,
                'unreviewed_incidents': unreviewed,
                'last_update': last_update or 'No data',
                'created_at': stu.get('created_at').isoformat() if stu.get('created_at') else None,
            })

        # Sort: needs_intervention first, then monitor, then normal
        status_order = {'needs_intervention': 0, 'monitor': 1, 'normal': 2}
        results.sort(key=lambda x: (status_order.get(x['status'], 2), -x['current_stress']))

        return jsonify({
            'success': True,
            'data': results,
            'count': len(results),
            'summary': {
                'total': len(results),
                'needs_intervention': sum(1 for r in results if r['status'] == 'needs_intervention'),
                'monitor': sum(1 for r in results if r['status'] == 'monitor'),
                'normal': sum(1 for r in results if r['status'] == 'normal'),
            }
        }), 200

    except Exception as e:
        current_app.logger.error('get_my_students error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/my-students/<anonymous_id>/remove', methods=['POST'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.STRICT)
def remove_student(anonymous_id):
    """Remove a student from proctor's ward (soft-delete)."""
    try:
        db = get_db()
        proctor_email = session.get('user_email', '')

        result = db['proctor_students'].update_one(
            {'anonymous_id': anonymous_id, 'proctor_id': proctor_email},
            {'$set': {'status': 'inactive', 'removed_at': datetime.utcnow()}}
        )

        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Student not found in your ward'}), 404

        log_activity(
            action=AuditAction.REMOVE_STUDENT,
            target_type='student',
            target_id=anonymous_id,
        )

        return jsonify({'success': True, 'message': 'Student removed from your ward'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/hod')
@login_required
def hod_dashboard():
    """HOD Executive Dashboard - Department-level analytics and oversight."""
    role = session.get('user_role')
    if role != 'hod':
        return jsonify({'error': 'Unauthorized - HOD access only'}), 403
    hod_name = session.get('user_name', 'HOD')
    hod_email = session.get('user_email', 'hod@aura.edu')
    return render_template('hod_dashboard.html', hod_name=hod_name, hod_email=hod_email)


def hod_only(f):
    """Ensure the current user is HOD."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('user_role')
        if role != 'hod':
            return jsonify({'error': 'Unauthorized - HOD access only'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------
# HOD-SPECIFIC API ENDPOINTS
# ---------------------------------------------

@proctor_bp.route('/api/hod/dashboard-stats', methods=['GET'])
@login_required
@hod_only
def hod_dashboard_stats():
    """Get HOD executive dashboard statistics â€” department-scoped."""
    try:
        db = get_db()
        _ensure_indexes(db)
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = datetime.utcnow() - timedelta(days=7)
        month_start = datetime.utcnow() - timedelta(days=30)
        department = session.get('user_department', '')
        
        # â”€â”€ RBAC: scope to department students â”€â”€
        visible_ids = get_visible_student_ids()
        scope_filter = {'anonymous_student_id': {'$in': visible_ids}} if visible_ids else {'anonymous_student_id': {'$in': []}}

        # Get department student emails for wellness queries
        dept_students = get_visible_students()
        dept_emails = [s.get('email', '') for s in dept_students]
        
        # Active students (with wellness activity in last 30 days, scoped to dept)
        if dept_emails:
            active_students = len(list(db['student_wellness'].distinct('student_id', {
                'student_id': {'$in': dept_emails},
                'timestamp': {'$gte': month_start}
            })))
        else:
            active_students = 0
        
        # Incidents (scoped)
        total_incidents = db['risk_incidents'].count_documents(scope_filter)
        unreviewed_incidents = db['risk_incidents'].count_documents({**scope_filter, 'status': 'UNREVIEWED'})
        high_risk_incidents = db['risk_incidents'].count_documents({**scope_filter, 'risk_level': 'HIGH', 'status': 'UNREVIEWED'})
        weekly_incidents = db['risk_incidents'].count_documents({**scope_filter, 'timestamp': {'$gte': week_start}})
        
        # Average wellness score (scoped to dept emails)
        avg_wellness = 0
        if dept_emails:
            recent_wellness = list(db['student_wellness'].find(
                {'data_type': 'stress', 'timestamp': {'$gte': week_start}, 'student_id': {'$in': dept_emails}},
                {'value': 1}
            ).limit(1000))
            if recent_wellness:
                total_stress = sum([w.get('value', 50) for w in recent_wellness])
                avg_stress = total_stress / len(recent_wellness)
                avg_wellness = round(100 - avg_stress, 1)
        
        # Resolution rate (scoped)
        resolved_count = db['risk_incidents'].count_documents({**scope_filter, 'status': {'$in': ['DISMISSED', 'ESCALATED', 'REMOVED']}})
        resolution_rate = round((resolved_count / total_incidents * 100) if total_incidents > 0 else 0, 1)
        
        # Proctor activity (only dept proctors)
        dept_proctors = list(db['users'].find(
            {'role': 'proctor', 'department': department},
            {'email': 1}
        )) if department else []
        dept_proctor_emails = [p['email'] for p in dept_proctors]
        proctor_actions_today = db['proctor_actions'].count_documents({
            'timestamp': {'$gte': today_start},
            'proctor_id': {'$in': dept_proctor_emails}
        }) if dept_proctor_emails else 0
        
        return jsonify({
            'success': True,
            'data': {
                'active_students': active_students,
                'total_students': len(dept_students),
                'total_incidents': total_incidents,
                'unreviewed_incidents': unreviewed_incidents,
                'high_risk_incidents': high_risk_incidents,
                'weekly_incidents': weekly_incidents,
                'avg_wellness': avg_wellness,
                'resolution_rate': resolution_rate,
                'proctor_actions_today': proctor_actions_today,
                'department': department,
                'proctor_count': len(dept_proctor_emails),
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/wellness-trends', methods=['GET'])
@login_required
@hod_only
def hod_wellness_trends():
    """Get department-wide wellness trends for charts â€” department-scoped."""
    try:
        db = get_db()
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # â”€â”€ RBAC: only department students â”€â”€
        dept_students = get_visible_students()
        dept_emails = [s.get('email', '') for s in dept_students]
        
        match_filter = {
            'data_type': 'stress',
            'timestamp': {'$gte': thirty_days_ago}
        }
        if dept_emails:
            match_filter['student_id'] = {'$in': dept_emails}
        else:
            match_filter['student_id'] = {'$in': []}
        
        pipeline = [
            {'$match': match_filter},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                'avg_stress': {'$avg': '$value'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}},
            {'$limit': 30}
        ]
        
        daily_stats = list(db['student_wellness'].aggregate(pipeline))
        
        dates = []
        wellness_values = []
        stress_values = []
        
        for stat in daily_stats:
            dates.append(stat['_id'])
            avg_stress = stat.get('avg_stress', 50)
            stress_values.append(round(avg_stress, 1))
            wellness_values.append(round(100 - avg_stress, 1))
        
        return jsonify({
            'success': True,
            'data': {
                'dates': dates,
                'wellness': wellness_values,
                'stress': stress_values
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/risk-distribution', methods=['GET'])
@login_required
@hod_only
def hod_risk_distribution():
    """Get risk level distribution â€” department-scoped."""
    try:
        db = get_db()
        
        # â”€â”€ RBAC: scope to visible students â”€â”€
        visible_ids = get_visible_student_ids()
        scope = {'anonymous_student_id': {'$in': visible_ids}} if visible_ids else {'anonymous_student_id': {'$in': []}}
        
        high_count = db['risk_incidents'].count_documents({**scope, 'risk_level': 'HIGH'})
        medium_count = db['risk_incidents'].count_documents({**scope, 'risk_level': 'MEDIUM'})
        low_count = db['risk_incidents'].count_documents({**scope, 'risk_level': 'LOW'})
        
        return jsonify({
            'success': True,
            'data': {
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
                'total': high_count + medium_count + low_count
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/proctor-performance', methods=['GET'])
@login_required
@hod_only
def hod_proctor_performance():
    """Get proctor performance metrics â€” department-scoped."""
    try:
        db = get_db()
        week_start = datetime.utcnow() - timedelta(days=7)
        department = session.get('user_department', '')
        
        # â”€â”€ RBAC: only proctors in this department â”€â”€
        dept_proctors = list(db['users'].find(
            {'role': 'proctor', 'department': department},
            {'email': 1}
        )) if department else []
        dept_proctor_emails = [p['email'] for p in dept_proctors]
        
        if not dept_proctor_emails:
            return jsonify({'success': True, 'data': []}), 200
        
        pipeline = [
            {'$match': {'timestamp': {'$gte': week_start}, 'proctor_id': {'$in': dept_proctor_emails}}},
            {'$group': {
                '_id': '$proctor_id',
                'total_actions': {'$sum': 1},
                'dismiss_count': {'$sum': {'$cond': [{'$eq': ['$action_type', 'DISMISS']}, 1, 0]}},
                'escalate_count': {'$sum': {'$cond': [{'$eq': ['$action_type', 'ESCALATE']}, 1, 0]}},
                'remove_count': {'$sum': {'$cond': [{'$eq': ['$action_type', 'REMOVE']}, 1, 0]}}
            }},
            {'$sort': {'total_actions': -1}},
            {'$limit': 10}
        ]
        
        proctor_stats = list(db['proctor_actions'].aggregate(pipeline))
        
        formatted_stats = []
        for stat in proctor_stats:
            formatted_stats.append({
                'proctor_id': stat['_id'],
                'total_actions': stat['total_actions'],
                'dismissals': stat['dismiss_count'],
                'escalations': stat['escalate_count'],
                'removals': stat['remove_count']
            })
        
        return jsonify({
            'success': True,
            'data': formatted_stats
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/recent-escalations', methods=['GET'])
@login_required
@hod_only
def hod_recent_escalations():
    """Get recent escalated incidents â€” department-scoped."""
    try:
        db = get_db()
        
        # â”€â”€ RBAC: scope to department students â”€â”€
        visible_ids = get_visible_student_ids()
        scope = {'anonymous_student_id': {'$in': visible_ids}} if visible_ids else {'anonymous_student_id': {'$in': []}}
        
        escalated = list(db['risk_incidents'].find(
            {**scope, 'status': 'ESCALATED'},
            sort=[('timestamp', -1)],
            limit=20
        ))
        
        formatted = []
        for inc in escalated:
            formatted.append({
                'incident_id': inc.get('incident_id'),
                'anonymous_student_id': inc.get('anonymous_student_id'),
                'risk_level': inc.get('risk_level'),
                'trigger_source': inc.get('trigger_source'),
                'message_excerpt': inc.get('message_excerpt', '')[:100],
                'timestamp': inc.get('timestamp').isoformat() if inc.get('timestamp') else None
            })
        
        return jsonify({
            'success': True,
            'data': formatted
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500

# ---------------------------------------------
# API: System Status
# ---------------------------------------------

@proctor_bp.route('/api/system/status', methods=['GET'])
@login_required
@proctor_only
def get_system_status():
    db = get_db()
    _ensure_indexes(db)
    status_coll = db['system_status']
    status = status_coll.find_one()
    if not status:
        status = _default_status()
        status_coll.insert_one(status)

    status['last_update'] = datetime.utcnow()
    status_coll.update_one({}, {'$set': {'last_update': status['last_update']}}, upsert=True)

    return jsonify({'success': True, 'data': {
        'status': status.get('status', 'LIVE'),
        'active_students': status.get('active_students', 0),
        'active_alerts': status.get('active_alerts', 0),
        'connection_hub_state': status.get('connection_hub_state', 'CALM'),
        'last_update': status['last_update'].isoformat(),
    }})

# ---------------------------------------------
# API: Risk Queue
# ---------------------------------------------

@proctor_bp.route('/api/risk/queue', methods=['GET'])
@login_required
@proctor_only
def get_risk_queue():
    status_filter = request.args.get('status', 'UNREVIEWED')
    risk_level = request.args.get('risk_level')
    time_range = request.args.get('time_range')
    sort_by = request.args.get('sort_by', 'timestamp')
    sort_order = request.args.get('sort_order', 'desc')
    incidents = _fetch_risk_queue(status_filter, risk_level, time_range, sort_by, sort_order)

    return jsonify({
        'success': True,
        'data': [_serialize_incident(doc) for doc in incidents],
        'count': len(incidents),
    })


@proctor_bp.route('/api/risk/queue/time/<time_range>', methods=['GET'])
@login_required
@proctor_only
def get_risk_queue_time(time_range):
    status_filter = request.args.get('status', 'UNREVIEWED')
    risk_level = request.args.get('risk_level')
    sort_by = request.args.get('sort_by', 'timestamp')
    sort_order = request.args.get('sort_order', 'desc')
    incidents = _fetch_risk_queue(status_filter, risk_level, time_range, sort_by, sort_order)

    return jsonify({
        'success': True,
        'data': [_serialize_incident(doc) for doc in incidents],
        'count': len(incidents),
        'time_range': time_range,
    })


def _fetch_risk_queue(status_filter: str, risk_level: str, time_range: str, sort_by: str, sort_order: str):
    db = get_db()
    _ensure_indexes(db)
    coll = db['risk_incidents']

    # â”€â”€ RBAC: scope to visible students â”€â”€
    visible_ids = get_visible_student_ids()
    if not visible_ids:
        return []
    query = {'anonymous_student_id': {'$in': visible_ids}}

    if status_filter and status_filter != 'ALL':
        query['status'] = status_filter
    if risk_level:
        query['risk_level'] = risk_level

    if time_range:
        time_map = {
            'hour': timedelta(hours=1),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
        }
        if time_range in time_map:
            cutoff = datetime.utcnow() - time_map[time_range]
            query['timestamp'] = {'$gte': cutoff}

    sort_field = 'timestamp' if sort_by in ['timestamp', 'risk_level'] else 'timestamp'
    sort_dir = -1 if sort_order == 'desc' else 1

    return list(coll.find(query).sort(sort_field, sort_dir).limit(200))

# ---------------------------------------------
# API: Incident Details
# ---------------------------------------------

@proctor_bp.route('/api/incidents/<incident_id>', methods=['GET'])
@login_required
@proctor_only
def get_incident_details(incident_id):
    db = get_db()
    _ensure_indexes(db)
    incident = db['risk_incidents'].find_one({'incident_id': incident_id})
    if not incident:
        return jsonify({'success': False, 'error': 'Incident not found'}), 404

    # â”€â”€ RBAC: verify access to this student's incident â”€â”€
    student_anon_id = incident.get('anonymous_student_id', '')
    if not can_access_student(student_anon_id):
        return jsonify({'success': False, 'error': 'Access denied â€” incident not in your scope'}), 403

    actions = list(db['proctor_actions'].find({'incident_id': incident_id}).sort('timestamp', -1))

    return jsonify({
        'success': True,
        'data': {
            'incident': _serialize_incident(incident),
            'actions': [_serialize_action(a) for a in actions],
        }
    })


@proctor_bp.route('/api/risk/search', methods=['GET'])
@login_required
@proctor_only
@apply_rate_limit(Limits.SEARCH)
def search_incidents():
    query_text = request.args.get('q', '')
    field = request.args.get('field', 'incident_id')

    if not query_text or len(query_text) < 3:
        return jsonify({'success': False, 'error': 'Query too short (min 3 chars)'}), 400

    allowed_fields = {
        'incident_id': 'incident_id',
        'room_name': 'room_name',
        'message_excerpt': 'message_excerpt',
    }
    field_name = allowed_fields.get(field)
    if not field_name:
        return jsonify({'success': False, 'error': 'Invalid search field'}), 400

    db = get_db()
    _ensure_indexes(db)
    coll = db['risk_incidents']

    # â”€â”€ RBAC: scope search to visible students â”€â”€
    visible_ids = get_visible_student_ids()
    search_query = {field_name: {'$regex': query_text, '$options': 'i'}}
    if visible_ids:
        search_query['anonymous_student_id'] = {'$in': visible_ids}

    incidents = list(
        coll.find(search_query)
        .sort('timestamp', -1)
        .limit(50)
    )

    return jsonify({
        'success': True,
        'count': len(incidents),
        'data': [_serialize_incident(doc) for doc in incidents],
    })

# ---------------------------------------------
# API: Actions
# ---------------------------------------------

@proctor_bp.route('/api/action/<action_type>', methods=['POST'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.MODERATE)
def handle_action(action_type):
    valid_actions = ['dismiss', 'remove', 'escalate', 'contact', 'monitor', 'close', 'review']
    if action_type not in valid_actions:
        return jsonify({'success': False, 'error': f'Invalid action. Must be: {valid_actions}'}), 400

    data = request.get_json() or {}
    incident_id = data.get('incident_id')
    reason = data.get('reason', 'FALSE_POSITIVE')
    details = data.get('details', '')

    if not incident_id:
        return jsonify({'success': False, 'error': 'Incident ID required'}), 400

    db = get_db()
    _ensure_indexes(db)
    incident = db['risk_incidents'].find_one({'incident_id': incident_id})
    if not incident:
        return jsonify({'success': False, 'error': 'Incident not found'}), 404

    # â”€â”€ RBAC: verify access to this student's incident â”€â”€
    student_anon_id = incident.get('anonymous_student_id', '')
    if not can_access_student(student_anon_id):
        return jsonify({'success': False, 'error': 'Access denied â€” incident not in your scope'}), 403

    action_map = {
        'dismiss':  ('DISMISS',  'DISMISSED',  'resolved'),
        'remove':   ('REMOVE',   'REMOVED',    'resolved'),
        'escalate': ('ESCALATE', 'ESCALATED',  'reviewing'),
        'contact':  ('CONTACT',  'REVIEWED',   'contacted'),
        'monitor':  ('MONITOR',  'REVIEWED',   'monitoring'),
        'close':    ('CLOSE',    'RESOLVED',   'resolved'),
        'review':   ('REVIEW',   'REVIEWED',   'reviewing'),
    }
    action_label, status_label, case_status = action_map[action_type]

    old_status = incident.get('status', 'UNREVIEWED')
    old_case = incident.get('case_status', 'new')

    action_doc = {
        'action_id': str(uuid.uuid4()),
        'incident_id': incident_id,
        'proctor_id': session.get('user_email', 'UNKNOWN'),
        'action_type': action_label,
        'reason_code': reason,
        'details': details or f'{action_label} action via proctor',
        'old_status': old_status,
        'new_status': status_label,
        'old_case_status': old_case,
        'new_case_status': case_status,
        'timestamp': datetime.utcnow(),
    }

    db['proctor_actions'].insert_one(action_doc)
    db['risk_incidents'].update_one(
        {'incident_id': incident_id},
        {'$set': {
            'status': status_label,
            'case_status': case_status,
        }}
    )

    incident = db['risk_incidents'].find_one({'incident_id': incident_id})

    # â”€â”€ Push real-time alert if escalation or HIGH risk â”€â”€
    if action_type == 'escalate' or incident.get('risk_level') == 'HIGH':
        try:
            from app import emit_proctor_alert
            emit_proctor_alert({
                'type': 'action_taken',
                'action': action_label,
                'risk_level': incident.get('risk_level', 'UNKNOWN'),
                'anonymous_student_id': incident.get('anonymous_student_id', ''),
                'incident_id': incident_id,
                'case_status': case_status,
                'proctor_id': session.get('user_email', 'UNKNOWN'),
                'message': f'{action_label} on {incident.get("risk_level", "")} risk incident',
                'timestamp': datetime.utcnow().isoformat(),
            })
        except Exception:
            pass

    # Centralized audit log
    action_audit_map = {
        'dismiss': AuditAction.DISMISS_INCIDENT,
        'remove': AuditAction.DISMISS_INCIDENT,
        'escalate': AuditAction.ESCALATE_INCIDENT,
        'contact': AuditAction.CONTACT_STUDENT,
        'monitor': AuditAction.MONITOR_STUDENT,
        'close': AuditAction.CLOSE_INCIDENT,
        'review': AuditAction.REVIEW_INCIDENT,
    }
    log_activity(
        action=action_audit_map.get(action_type, action_type.upper()),
        target_type='incident',
        target_id=incident_id,
        metadata={'action_label': action_label, 'new_status': status_label, 'case_status': case_status, 'anonymous_student_id': incident.get('anonymous_student_id')}
    )

    return jsonify({
        'success': True,
        'data': {
            'incident': _serialize_incident(incident),
            'action': _serialize_action(action_doc),
        }
    })


@proctor_bp.route('/api/action/bulk', methods=['POST'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.BULK)
def bulk_action():
    data = request.get_json() or {}
    incident_ids = data.get('incident_ids') or []
    action_type = data.get('action_type')
    reason = data.get('reason', 'BULK_ACTION')
    details = data.get('details', 'Bulk action via proctor dashboard')

    if action_type not in ['dismiss', 'remove', 'escalate', 'contact', 'monitor', 'close', 'review']:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    if not incident_ids:
        return jsonify({'success': False, 'error': 'No incident IDs provided'}), 400

    db = get_db()
    _ensure_indexes(db)
    coll = db['risk_incidents']

    action_map = {
        'dismiss':  ('DISMISS',  'DISMISSED',  'resolved'),
        'remove':   ('REMOVE',   'REMOVED',    'resolved'),
        'escalate': ('ESCALATE', 'ESCALATED',  'reviewing'),
        'contact':  ('CONTACT',  'REVIEWED',   'contacted'),
        'monitor':  ('MONITOR',  'REVIEWED',   'monitoring'),
        'close':    ('CLOSE',    'RESOLVED',   'resolved'),
        'review':   ('REVIEW',   'REVIEWED',   'reviewing'),
    }
    action_label, status_label, case_status = action_map[action_type]

    incidents = list(coll.find({'incident_id': {'$in': incident_ids}}))
    if not incidents:
        return jsonify({'success': False, 'error': 'No incidents found'}), 404

    actions_to_insert = []
    updated_ids = []
    for incident in incidents:
        action_doc = {
            'action_id': str(uuid.uuid4()),
            'incident_id': incident['incident_id'],
            'proctor_id': session.get('user_email', 'UNKNOWN'),
            'action_type': action_label,
            'reason_code': reason,
            'details': details,
            'timestamp': datetime.utcnow(),
        }
        actions_to_insert.append(action_doc)
        coll.update_one({'incident_id': incident['incident_id']}, {'$set': {'status': status_label, 'case_status': case_status}})
        updated_ids.append(incident['incident_id'])

    if actions_to_insert:
        db['proctor_actions'].insert_many(actions_to_insert)

    log_activity(
        action=AuditAction.BULK_ACTION,
        target_type='incident',
        target_id=None,
        metadata={'action': action_label, 'incident_count': len(updated_ids), 'incident_ids': updated_ids[:10]}
    )

    refreshed_incidents = list(coll.find({'incident_id': {'$in': updated_ids}}))

    return jsonify({
        'success': True,
        'processed': len(updated_ids),
        'incidents': [_serialize_incident(doc) for doc in refreshed_incidents],
    })

# ---------------------------------------------
# API: Audit Logs
# ---------------------------------------------

@proctor_bp.route('/api/audit/logs', methods=['GET'])
@login_required
@proctor_only
@apply_rate_limit(Limits.STANDARD)
def get_audit_logs():
    db = get_db()
    _ensure_indexes(db)
    days = request.args.get('days', 7, type=int)
    proctor_id = request.args.get('proctor_id')
    action_type = request.args.get('action_type')

    since_date = datetime.utcnow() - timedelta(days=days)

    query = {'timestamp': {'$gte': since_date}}
    if proctor_id:
        query['proctor_id'] = proctor_id
    if action_type:
        query['action_type'] = action_type

    logs = list(db['proctor_actions'].find(query).sort('timestamp', -1).limit(500))

    log_data = []
    for log in logs:
        entry = _serialize_action(log)
        entry['proctor_name'] = f"Proctor-{log.get('proctor_id', '0000')}"
        log_data.append(entry)

    return jsonify({'success': True, 'data': log_data, 'count': len(log_data)})


@proctor_bp.route('/api/audit/export/csv', methods=['GET'])
@login_required
@proctor_only
@apply_rate_limit(Limits.EXPORT)
def export_audit_csv():
    db = get_db()
    _ensure_indexes(db)
    days = request.args.get('days', 7, type=int)

    since_date = datetime.utcnow() - timedelta(days=days)

    # RBAC: scope to department proctors for HOD, or own actions for proctor
    query = {'timestamp': {'$gte': since_date}}
    role = session.get('user_role', '')
    if role == 'hod':
        dept = session.get('user_department', '')
        dept_proctors = [p['email'] for p in db['users'].find({'role': 'proctor', 'department': dept}, {'email': 1})]
        if dept_proctors:
            query['proctor_id'] = {'$in': dept_proctors}
        else:
            query['proctor_id'] = {'$in': []}
    elif role == 'proctor':
        query['proctor_id'] = session.get('user_email', '')

    logs = list(
        db['proctor_actions']
        .find(query)
        .sort('timestamp', -1)
        .limit(1000)
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Proctor ID', 'Action', 'Incident ID', 'Reason', 'Details'])

    for log in logs:
        writer.writerow([
            log.get('timestamp').isoformat() if log.get('timestamp') else '',
            log.get('proctor_id', ''),
            log.get('action_type', ''),
            log.get('incident_id', ''),
            log.get('reason_code', ''),
            log.get('details', ''),
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=audit_log_{days}d.csv'},
    )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CENTRALIZED ACTIVITY LOGS (proctor_activity_logs)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@proctor_bp.route('/api/activity-logs', methods=['GET'])
@login_required
@proctor_only
@apply_rate_limit(Limits.STANDARD)
def get_activity_logs():
    """
    Get centralized audit trail from proctor_activity_logs.
    
    Query params:
        days     â€” lookback window (default 7, max 90)
        action   â€” filter by AuditAction constant
        proctor  â€” filter by proctor email
        target   â€” filter by target_type ('student', 'incident', 'ticket')
        limit    â€” max results (default 200, max 1000)
    """
    try:
        db = get_db()
        days = min(request.args.get('days', 7, type=int), 90)
        action_filter = request.args.get('action', '')
        proctor_filter = request.args.get('proctor', '')
        target_filter = request.args.get('target', '')
        limit = min(request.args.get('limit', 200, type=int), 1000)

        since = datetime.utcnow() - timedelta(days=days)
        query = {'timestamp': {'$gte': since}}

        if action_filter:
            query['action'] = action_filter
        if proctor_filter:
            query['proctor_email'] = proctor_filter
        if target_filter:
            query['target_type'] = target_filter

        logs = list(db['proctor_activity_logs'].find(
            query,
            sort=[('timestamp', -1)]
        ).limit(limit))

        results = []
        for log in logs:
            log['_id'] = str(log['_id'])
            if isinstance(log.get('timestamp'), datetime):
                log['time_ago'] = _time_since(log['timestamp'])
                log['timestamp'] = log['timestamp'].isoformat()
            results.append(log)

        # Summary counts by action type
        pipeline = [
            {'$match': {'timestamp': {'$gte': since}}},
            {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        action_summary = {r['_id']: r['count'] for r in db['proctor_activity_logs'].aggregate(pipeline)}

        return jsonify({
            'success': True,
            'data': results,
            'count': len(results),
            'summary': action_summary,
            'period_days': days,
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/activity-logs/export/csv', methods=['GET'])
@login_required
@proctor_only
@apply_rate_limit(Limits.EXPORT)
def export_activity_logs_csv():
    """Export centralized activity logs as CSV."""
    try:
        db = get_db()
        days = min(request.args.get('days', 30, type=int), 365)
        since = datetime.utcnow() - timedelta(days=days)

        logs = list(db['proctor_activity_logs'].find(
            {'timestamp': {'$gte': since}},
            sort=[('timestamp', -1)]
        ).limit(5000))

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Timestamp', 'Proctor Email', 'Proctor Name', 'Action', 'Target Type', 'Target ID', 'IP Address', 'Metadata'])

        for log in logs:
            writer.writerow([
                log.get('timestamp').isoformat() if isinstance(log.get('timestamp'), datetime) else str(log.get('timestamp', '')),
                log.get('proctor_email', ''),
                log.get('proctor_name', ''),
                log.get('action', ''),
                log.get('target_type', ''),
                log.get('target_id', ''),
                log.get('ip_address', ''),
                str(log.get('metadata', {})),
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=activity_log_{days}d.csv'},
        )

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# ---------------------------------------------
# API: Resolution Metrics
# ---------------------------------------------

@proctor_bp.route('/api/metrics/resolution', methods=['GET'])
@login_required
@proctor_only
def get_resolution_metrics():
    """Compute resolution metrics for incidents since midnight (UTC)."""
    db = get_db()
    _ensure_indexes(db)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    incidents = list(
        db['risk_incidents']
        .find({'timestamp': {'$gte': today_start}})
        .sort('timestamp', -1)
        .limit(2000)
    )

    total_today = len(incidents)
    handled_today = sum(1 for i in incidents if i.get('status') != 'UNREVIEWED')

    # Average resolution time (minutes) based on first action per incident
    resolved_times = []
    for inc in incidents:
        if inc.get('status') != 'UNREVIEWED':
            action = db['proctor_actions'].find_one(
                {'incident_id': inc.get('incident_id')},
                sort=[('timestamp', 1)]
            )
            if action and inc.get('timestamp') and action.get('timestamp'):
                delta = action['timestamp'] - inc['timestamp']
                resolved_times.append(delta.total_seconds() / 60.0)

    avg_minutes = round((sum(resolved_times) / len(resolved_times)) if resolved_times else 0, 1)

    pending_high = db['risk_incidents'].count_documents({'status': 'UNREVIEWED', 'risk_level': 'HIGH'})

    resolution_rate = round(((handled_today / total_today) * 100) if total_today > 0 else 0, 1)

    return jsonify({
        'success': True,
        'data': {
            'handled_today': handled_today,
            'total_today': total_today,
            'resolution_rate': resolution_rate,
            'avg_resolution_minutes': avg_minutes,
            'pending_high_risk': pending_high,
        }
    })

# ---------------------------------------------
# API: Health Check
# ---------------------------------------------

@proctor_bp.route('/api/health', methods=['GET'])
@login_required
@proctor_only
def health_check():
    """Simple health endpoint for monitoring and readiness checks."""
    db = get_db()
    _ensure_indexes(db)

    try:
        pending = db['risk_incidents'].count_documents({'status': 'UNREVIEWED'})
        last_action = db['proctor_actions'].find().sort('timestamp', -1).limit(1)
        last_audit_time = None
        last_action = list(last_action)
        if last_action and last_action[0].get('timestamp'):
            last_audit_time = last_action[0]['timestamp'].isoformat()

        status_doc = db['system_status'].find_one() or _default_status()

        return jsonify({
            'status': 'healthy',
            'incidents_pending': pending,
            'last_update': status_doc.get('last_update').isoformat() if status_doc.get('last_update') else None,
            'last_audit_entry': last_audit_time,
        })
    except Exception as e:
        return jsonify({'status': 'degraded', 'error': safe_error(e, 'proctor')}), 500

# ---------------------------------------------
# Optional: seed test data
# ---------------------------------------------

def create_test_incidents():
    """Generate 25+ realistic test incidents for dashboard demonstration."""
    db = get_db()
    _ensure_indexes(db)
    
    # Realistic message templates by risk level
    high_risk_messages = [
        "I can't handle this anymore",
        "Everything feels hopeless",
        "I don't see a way out",
        "The pressure is crushing me",
        "I'm completely overwhelmed",
    ]
    
    medium_risk_messages = [
        "Feeling really stressed about upcoming exams",
        "Having trouble sleeping due to anxiety",
        "Not sure I can keep up with coursework",
        "Feeling isolated and alone",
        "Struggling to stay motivated",
    ]
    
    low_risk_messages = [
        "A bit worried about deadlines",
        "Could use some study tips",
        "Feeling a little tired lately",
        "Minor concerns about grades",
        "Need help with time management",
    ]
    
    trigger_sources = ['stress_spike', 'mood_shift', 'chat_sentiment', 'behavioral_change', 'peer_report']
    room_names = ['General Support', 'Academic Help', 'Wellness Chat', 'Study Group', 'Anonymous']
    
    incidents = []
    
    # Generate HIGH risk incidents (5)
    for i in range(5):
        incidents.append({
            'incident_id': str(uuid.uuid4()),
            'anonymous_student_id': f'hash_{uuid.uuid4().hex[:12]}',
            'risk_level': 'HIGH',
            'trend': 'RISING' if i < 3 else 'STABLE',
            'trigger_source': trigger_sources[i % len(trigger_sources)],
            'message_excerpt': high_risk_messages[i % len(high_risk_messages)],
            'room_name': room_names[i % len(room_names)],
            'timestamp': datetime.utcnow() - timedelta(minutes=5 + i * 10),
            'report_count': 3 + i,
            'status': 'UNREVIEWED',
        })
    
    # Generate MEDIUM risk incidents (12)
    for i in range(12):
        status = 'UNREVIEWED' if i < 8 else 'REVIEWED'
        incidents.append({
            'incident_id': str(uuid.uuid4()),
            'anonymous_student_id': f'hash_{uuid.uuid4().hex[:12]}',
            'risk_level': 'MEDIUM',
            'trend': ['RISING', 'STABLE', 'FALLING'][i % 3],
            'trigger_source': trigger_sources[i % len(trigger_sources)],
            'message_excerpt': medium_risk_messages[i % len(medium_risk_messages)],
            'room_name': room_names[i % len(room_names)],
            'timestamp': datetime.utcnow() - timedelta(hours=1 + i, minutes=i * 5),
            'report_count': 1 + (i % 3),
            'status': status,
        })
    
    # Generate LOW risk incidents (13)
    for i in range(13):
        status_options = ['UNREVIEWED', 'REVIEWED', 'DISMISSED']
        incidents.append({
            'incident_id': str(uuid.uuid4()),
            'anonymous_student_id': f'hash_{uuid.uuid4().hex[:12]}',
            'risk_level': 'LOW',
            'trend': ['STABLE', 'FALLING'][i % 2],
            'trigger_source': trigger_sources[i % len(trigger_sources)],
            'message_excerpt': low_risk_messages[i % len(low_risk_messages)],
            'room_name': room_names[i % len(room_names)],
            'timestamp': datetime.utcnow() - timedelta(hours=2 + i, minutes=i * 3),
            'report_count': 1,
            'status': status_options[i % 3],
        })
    
    # Insert all incidents
    for doc in incidents:
        db['risk_incidents'].update_one(
            {'incident_id': doc['incident_id']}, 
            {'$setOnInsert': doc}, 
            upsert=True
        )
    
    # Update system status
    unreviewed_count = len([i for i in incidents if i['status'] == 'UNREVIEWED'])
    db['system_status'].update_one(
        {},
        {'$set': {
            'active_alerts': unreviewed_count,
            'active_students': len(set(i['anonymous_student_id'] for i in incidents)),
            'last_update': datetime.utcnow()
        }},
        upsert=True
    )
    
    print(f"âœ… Created {len(incidents)} test incidents")
    print(f"   - HIGH risk: 5 (all unreviewed)")
    print(f"   - MEDIUM risk: 12 (8 unreviewed, 4 reviewed)")
    print(f"   - LOW risk: 13 (varied status)")
    print(f"   - Active alerts: {unreviewed_count}")
    
    return len(incidents)


@proctor_bp.route('/api/test/seed', methods=['POST'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.STRICT)
def seed_test_data():
    """API endpoint to populate test data."""
    try:
        count = create_test_incidents()
        return jsonify({'success': True, 'incidents_created': count})
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# ==========================================
# SUPPORT CENTER MANAGEMENT (Proctor view)
# ==========================================

@proctor_bp.route('/api/support/tickets', methods=['GET'])
@login_required
@proctor_only
def get_support_tickets():
    """Get all support requests for proctor review. Filterable by type and status."""
    try:
        db = get_db()
        filter_type = request.args.get('type', '')       # 'urgent', 'general', ''
        filter_status = request.args.get('status', '')    # 'pending', 'in_progress', 'resolved', ''

        query = {}
        if filter_type:
            query['type'] = filter_type
        if filter_status:
            query['status'] = filter_status

        tickets = list(db['support_requests'].find(query, sort=[('timestamp', -1)]).limit(50))

        for t in tickets:
            t['_id'] = str(t['_id'])
            if isinstance(t.get('timestamp'), datetime):
                t['time_ago'] = _time_since(t['timestamp'])
                t['timestamp'] = t['timestamp'].isoformat()

        return jsonify({'success': True, 'tickets': tickets}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/support/tickets/<ticket_id>/status', methods=['PATCH'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.MODERATE)
def update_ticket_status(ticket_id):
    """Update a support ticket's status (pending â†’ in_progress â†’ resolved)."""
    try:
        from bson import ObjectId
        db = get_db()
        data = request.get_json() or {}
        new_status = data.get('status', '')

        if new_status not in ('pending', 'in_progress', 'resolved', 'dismissed'):
            return jsonify({'error': 'Invalid status'}), 400

        result = db['support_requests'].update_one(
            {'_id': ObjectId(ticket_id)},
            {'$set': {
                'status': new_status,
                'updated_at': datetime.utcnow(),
                'updated_by': session.get('user_email', 'proctor')
            }}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Ticket not found'}), 404

        log_activity(
            action=AuditAction.UPDATE_TICKET,
            target_type='ticket',
            target_id=ticket_id,
            metadata={'new_status': new_status}
        )

        return jsonify({'success': True, 'message': f'Ticket updated to {new_status}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/support/sessions', methods=['GET'])
@login_required
@proctor_only
def get_counseling_sessions():
    """Get all counseling session bookings for proctor calendar."""
    try:
        db = get_db()
        filter_status = request.args.get('status', '')

        query = {}
        if filter_status:
            query['status'] = filter_status

        sessions_list = list(db['counseling_sessions'].find(query, sort=[('created_at', -1)]).limit(50))

        for s in sessions_list:
            s['_id'] = str(s['_id'])
            if isinstance(s.get('created_at'), datetime):
                s['created_at'] = s['created_at'].isoformat()

        return jsonify({'success': True, 'sessions': sessions_list}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/support/sessions/<session_id>/status', methods=['PATCH'])
@login_required
@proctor_only
@demo_restricted
def update_session_status(session_id):
    """Update a counseling session status (scheduled â†’ confirmed â†’ completed â†’ cancelled)."""
    try:
        from bson import ObjectId
        db = get_db()
        data = request.get_json() or {}
        new_status = data.get('status', '')

        if new_status not in ('scheduled', 'confirmed', 'completed', 'cancelled'):
            return jsonify({'error': 'Invalid status'}), 400

        result = db['counseling_sessions'].update_one(
            {'_id': ObjectId(session_id)},
            {'$set': {
                'status': new_status,
                'updated_at': datetime.utcnow(),
                'updated_by': session.get('user_email', 'proctor')
            }}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Session not found'}), 404

        return jsonify({'success': True, 'message': f'Session updated to {new_status}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/support/stats', methods=['GET'])
@login_required
@proctor_only
def get_support_stats():
    """Get support center statistics for proctor dashboard."""
    try:
        db = get_db()

        urgent_pending = db['support_requests'].count_documents({'type': 'urgent', 'status': 'pending'})
        general_pending = db['support_requests'].count_documents({'type': {'$ne': 'urgent'}, 'status': 'pending'})
        in_progress = db['support_requests'].count_documents({'status': 'in_progress'})
        resolved_today = db['support_requests'].count_documents({
            'status': 'resolved',
            'updated_at': {'$gte': datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
        })
        upcoming_sessions = db['counseling_sessions'].count_documents({'status': {'$in': ['scheduled', 'confirmed']}})

        return jsonify({
            'success': True,
            'stats': {
                'urgent_pending': urgent_pending,
                'general_pending': general_pending,
                'in_progress': in_progress,
                'resolved_today': resolved_today,
                'upcoming_sessions': upcoming_sessions
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# ==========================================
# ACADEMIC PERFORMANCE TRACKER
# ==========================================

@proctor_bp.route('/api/academics/overview', methods=['GET'])
@login_required
@proctor_only
def academics_overview():
    """Get academic performance overview for all students under this proctor."""
    try:
        db = get_db()
        proctor_email = session.get('user_email', '')

        # Fetch students assigned to this proctor
        students = list(db['proctor_students'].find(
            {'proctor_id': proctor_email, 'status': 'active'}
        ))

        results = []
        at_risk_count = 0
        improving_count = 0
        stable_count = 0

        for stu in students:
            anon_id = stu.get('anonymous_id', '')
            roll = stu.get('roll_number', '')

            # Get academic records sorted by semester
            records = list(db['academic_records'].find(
                {'student_roll': roll}
            ).sort('semester', -1).limit(8))

            current_cgpa = records[0].get('cgpa', 0) if records else 0
            prev_cgpa = records[1].get('cgpa', 0) if len(records) > 1 else current_cgpa

            cgpa_change = round(current_cgpa - prev_cgpa, 2)
            if cgpa_change < -0.3:
                perf_status = 'declining'
                at_risk_count += 1
            elif cgpa_change > 0.2:
                perf_status = 'improving'
                improving_count += 1
            else:
                perf_status = 'stable'
                stable_count += 1

            # Latest stress data for correlation
            latest_incident = db['risk_incidents'].find_one(
                {'anonymous_student_id': anon_id},
                sort=[('timestamp', -1)]
            )
            stress_level = latest_incident.get('risk_level', 'LOW') if latest_incident else 'LOW'

            # Attendance from academic records
            attendance_pct = records[0].get('attendance', 0) if records else 0

            semester_history = []
            for r in reversed(records[:6]):
                semester_history.append({
                    'semester': r.get('semester', ''),
                    'cgpa': r.get('cgpa', 0),
                    'sgpa': r.get('sgpa', 0),
                    'attendance': r.get('attendance', 0),
                    'backlogs': r.get('backlogs', 0),
                })

            results.append({
                'anonymous_id': anon_id,
                'name': stu.get('name', 'Unknown'),
                'roll_number': roll,
                'department': stu.get('department', ''),
                'semester': stu.get('semester', ''),
                'current_cgpa': current_cgpa,
                'prev_cgpa': prev_cgpa,
                'cgpa_change': cgpa_change,
                'performance_status': perf_status,
                'attendance': attendance_pct,
                'stress_level': stress_level,
                'backlogs': records[0].get('backlogs', 0) if records else 0,
                'semester_history': semester_history,
            })

        # Sort: declining first, then by CGPA ascending
        perf_order = {'declining': 0, 'stable': 1, 'improving': 2}
        results.sort(key=lambda x: (perf_order.get(x['performance_status'], 1), x['current_cgpa']))

        return jsonify({
            'success': True,
            'data': results,
            'summary': {
                'total_students': len(results),
                'at_risk': at_risk_count,
                'improving': improving_count,
                'stable': stable_count,
                'avg_cgpa': round(sum(r['current_cgpa'] for r in results) / max(len(results), 1), 2),
            }
        }), 200

    except Exception as e:
        current_app.logger.error('academics_overview error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/academics/student/<anonymous_id>', methods=['GET'])
@login_required
@proctor_only
def get_student_academics(anonymous_id):
    """Get detailed academic data for a single student."""
    try:
        db = get_db()

        student = db['proctor_students'].find_one({'anonymous_id': anonymous_id})
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        roll = student.get('roll_number', '')

        # All academic records
        records = list(db['academic_records'].find(
            {'student_roll': roll}
        ).sort('semester', 1))

        # Subject-wise marks (latest semester)
        latest_sem = records[-1].get('semester', '') if records else ''
        subjects = list(db['academic_subjects'].find(
            {'student_roll': roll, 'semester': latest_sem}
        ))
        for s in subjects:
            s['_id'] = str(s['_id'])

        # Correlate with stress data
        incidents = list(db['risk_incidents'].find(
            {'anonymous_student_id': anonymous_id},
            sort=[('timestamp', -1)]
        ).limit(20))

        high_stress_periods = sum(1 for i in incidents if i.get('risk_level') == 'HIGH')

        formatted_records = []
        for r in records:
            formatted_records.append({
                'semester': r.get('semester', ''),
                'sgpa': r.get('sgpa', 0),
                'cgpa': r.get('cgpa', 0),
                'attendance': r.get('attendance', 0),
                'backlogs': r.get('backlogs', 0),
                'credits_earned': r.get('credits_earned', 0),
                'total_credits': r.get('total_credits', 0),
            })

        return jsonify({
            'success': True,
            'data': {
                'student': {
                    'name': student.get('name', ''),
                    'roll_number': roll,
                    'department': student.get('department', ''),
                    'current_semester': student.get('semester', ''),
                },
                'records': formatted_records,
                'subjects': subjects,
                'correlation': {
                    'high_stress_incidents': high_stress_periods,
                    'total_incidents': len(incidents),
                }
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/academics/student/<anonymous_id>/record', methods=['POST'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.MODERATE)
def add_academic_record(anonymous_id):
    """Add or update an academic record for a student."""
    try:
        db = get_db()
        data = request.get_json() or {}
        proctor_email = session.get('user_email', 'UNKNOWN')

        student = db['proctor_students'].find_one({'anonymous_id': anonymous_id})
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        roll = student.get('roll_number', '')
        semester = data.get('semester', '').strip()
        sgpa = data.get('sgpa', 0)
        cgpa = data.get('cgpa', 0)
        attendance = data.get('attendance', 0)
        backlogs = data.get('backlogs', 0)
        credits_earned = data.get('credits_earned', 0)
        total_credits = data.get('total_credits', 0)

        if not semester:
            return jsonify({'success': False, 'error': 'Semester is required'}), 400

        record = {
            'student_roll': roll,
            'anonymous_id': anonymous_id,
            'semester': semester,
            'sgpa': float(sgpa),
            'cgpa': float(cgpa),
            'attendance': float(attendance),
            'backlogs': int(backlogs),
            'credits_earned': int(credits_earned),
            'total_credits': int(total_credits),
            'updated_by': proctor_email,
            'updated_at': datetime.utcnow(),
        }

        db['academic_records'].update_one(
            {'student_roll': roll, 'semester': semester},
            {'$set': record},
            upsert=True,
        )

        # Check if CGPA dropped significantly â€” auto-flag
        prev_records = list(db['academic_records'].find(
            {'student_roll': roll}
        ).sort('semester', -1).limit(2))

        if len(prev_records) >= 2:
            current = prev_records[0].get('cgpa', 0)
            previous = prev_records[1].get('cgpa', 0)
            if previous - current >= 0.5:
                # Auto-create a note about academic decline
                db['proctor_notes'].insert_one({
                    'anonymous_student_id': anonymous_id,
                    'proctor_id': proctor_email,
                    'proctor_name': session.get('user_name', 'Proctor'),
                    'note': f'âš ï¸ Academic Alert: CGPA dropped from {previous} to {current} (Î” = {round(current - previous, 2)}). Auto-flagged for monitoring.',
                    'urgent': True,
                    'flag_monitoring': True,
                    'timestamp': datetime.utcnow(),
                })

        return jsonify({
            'success': True,
            'message': f'Academic record for semester {semester} saved successfully.'
        }), 200

    except Exception as e:
        current_app.logger.error('add_academic_record error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/academics/at-risk', methods=['GET'])
@login_required
@proctor_only
def academics_at_risk():
    """Get students with declining academic performance â€” CGPA drops, high backlogs, low attendance."""
    try:
        db = get_db()
        proctor_email = session.get('user_email', '')

        students = list(db['proctor_students'].find(
            {'proctor_id': proctor_email, 'status': 'active'}
        ))

        at_risk = []
        for stu in students:
            roll = stu.get('roll_number', '')
            anon_id = stu.get('anonymous_id', '')

            records = list(db['academic_records'].find(
                {'student_roll': roll}
            ).sort('semester', -1).limit(3))

            if not records:
                continue

            current = records[0]
            cgpa = current.get('cgpa', 0)
            attendance = current.get('attendance', 0)
            backlogs = current.get('backlogs', 0)
            prev_cgpa = records[1].get('cgpa', 0) if len(records) > 1 else cgpa
            cgpa_drop = round(prev_cgpa - cgpa, 2)

            # Risk criteria
            reasons = []
            if cgpa_drop >= 0.3:
                reasons.append(f'CGPA dropped by {cgpa_drop}')
            if cgpa < 5.0:
                reasons.append(f'Low CGPA ({cgpa})')
            if attendance < 65:
                reasons.append(f'Low attendance ({attendance}%)')
            if backlogs >= 2:
                reasons.append(f'{backlogs} active backlogs')

            if reasons:
                # Get stress correlation
                latest_incident = db['risk_incidents'].find_one(
                    {'anonymous_student_id': anon_id},
                    sort=[('timestamp', -1)]
                )
                stress_level = latest_incident.get('risk_level', 'NONE') if latest_incident else 'NONE'

                at_risk.append({
                    'anonymous_id': anon_id,
                    'name': stu.get('name', 'Unknown'),
                    'roll_number': roll,
                    'department': stu.get('department', ''),
                    'semester': stu.get('semester', ''),
                    'cgpa': cgpa,
                    'cgpa_drop': cgpa_drop,
                    'attendance': attendance,
                    'backlogs': backlogs,
                    'stress_level': stress_level,
                    'risk_reasons': reasons,
                    'risk_score': len(reasons),
                })

        # Sort by number of risk reasons, then by CGPA ascending
        at_risk.sort(key=lambda x: (-x['risk_score'], x['cgpa']))

        return jsonify({
            'success': True,
            'data': at_risk,
            'count': len(at_risk),
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/academics/subjects', methods=['POST'])
@login_required
@proctor_only
@demo_restricted
def add_subject_marks(anonymous_id=None):
    """Add subject-wise marks for a student in a specific semester."""
    try:
        db = get_db()
        data = request.get_json() or {}
        anon_id = data.get('anonymous_id', anonymous_id or '').strip()
        proctor_email = session.get('user_email', 'UNKNOWN')

        student = db['proctor_students'].find_one({'anonymous_id': anon_id})
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        roll = student.get('roll_number', '')
        semester = data.get('semester', '').strip()
        subjects = data.get('subjects', [])

        if not semester or not subjects:
            return jsonify({'success': False, 'error': 'Semester and subjects are required'}), 400

        for subj in subjects:
            db['academic_subjects'].update_one(
                {'student_roll': roll, 'semester': semester, 'subject_code': subj.get('code', '')},
                {'$set': {
                    'student_roll': roll,
                    'anonymous_id': anon_id,
                    'semester': semester,
                    'subject_code': subj.get('code', ''),
                    'subject_name': subj.get('name', ''),
                    'internal_marks': subj.get('internal', 0),
                    'external_marks': subj.get('external', 0),
                    'total_marks': subj.get('total', 0),
                    'grade': subj.get('grade', ''),
                    'credits': subj.get('credits', 0),
                    'grade_points': subj.get('grade_points', 0),
                    'updated_by': proctor_email,
                    'updated_at': datetime.utcnow(),
                }},
                upsert=True,
            )

        return jsonify({
            'success': True,
            'message': f'{len(subjects)} subject(s) saved for semester {semester}.'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/academics/department-stats', methods=['GET'])
@login_required
@proctor_only
def academics_department_stats():
    """Get aggregated academic stats for the proctor's assigned students."""
    try:
        db = get_db()
        proctor_email = session.get('user_email', '')

        students = list(db['proctor_students'].find(
            {'proctor_id': proctor_email, 'status': 'active'}
        ))
        rolls = [s.get('roll_number', '') for s in students]

        if not rolls:
            return jsonify({
                'success': True,
                'data': {
                    'cgpa_distribution': {'excellent': 0, 'good': 0, 'average': 0, 'below_avg': 0, 'poor': 0},
                    'avg_cgpa': 0,
                    'avg_attendance': 0,
                    'total_backlogs': 0,
                    'pass_rate': 0,
                }
            }), 200

        # Get the latest academic record for each student
        cgpas = []
        attendances = []
        total_backlogs = 0
        pass_count = 0

        for roll in rolls:
            record = db['academic_records'].find_one(
                {'student_roll': roll},
                sort=[('semester', -1)]
            )
            if record:
                c = record.get('cgpa', 0)
                a = record.get('attendance', 0)
                b = record.get('backlogs', 0)
                cgpas.append(c)
                attendances.append(a)
                total_backlogs += b
                if c >= 4.0 and b == 0:
                    pass_count += 1

        avg_cgpa = round(sum(cgpas) / max(len(cgpas), 1), 2)
        avg_attendance = round(sum(attendances) / max(len(attendances), 1), 1)
        pass_rate = round((pass_count / max(len(cgpas), 1)) * 100, 1)

        # CGPA distribution
        excellent = sum(1 for c in cgpas if c >= 8.5)
        good = sum(1 for c in cgpas if 7.0 <= c < 8.5)
        average = sum(1 for c in cgpas if 5.5 <= c < 7.0)
        below_avg = sum(1 for c in cgpas if 4.0 <= c < 5.5)
        poor = sum(1 for c in cgpas if c < 4.0)

        return jsonify({
            'success': True,
            'data': {
                'cgpa_distribution': {
                    'excellent': excellent,
                    'good': good,
                    'average': average,
                    'below_avg': below_avg,
                    'poor': poor,
                },
                'avg_cgpa': avg_cgpa,
                'avg_attendance': avg_attendance,
                'total_backlogs': total_backlogs,
                'pass_rate': pass_rate,
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500



# ==========================================
# STUDENT GRIEVANCES (Proctor view)
# ==========================================

@proctor_bp.route('/api/grievances', methods=['GET'])
@login_required
@proctor_only
def get_student_grievances():
    """Get student grievances scoped to proctor's assigned students."""
    try:
        db = get_db()
        filter_status = request.args.get('status', '')
        limit = min(int(request.args.get('limit', 50)), 100)

        # RBAC: get emails of students visible to this proctor
        visible = get_visible_students()
        visible_emails = [s.get('email', '') for s in visible if s.get('email')]

        query = {}
        if visible_emails:
            query['user_email'] = {'$in': visible_emails}
        else:
            # Proctor with no assigned students — return empty
            return jsonify({'success': True, 'grievances': [], 'total': 0}), 200

        if filter_status:
            query['status'] = filter_status

        grievances = list(db['grievances'].find(query, sort=[('created_at', -1)]).limit(limit))

        result = []
        for g in grievances:
            g['_id'] = str(g['_id'])
            if isinstance(g.get('created_at'), datetime):
                g['time_ago'] = _time_since(g['created_at'])
                g['created_at'] = g['created_at'].isoformat()
            # Anonymize student email for proctor view
            student_email = g.get('user_email', '')
            g['anonymous_id'] = create_anonymous_id(student_email) if student_email else 'UNKNOWN'
            g.pop('user_email', None)
            result.append(g)

        return jsonify({'success': True, 'grievances': result, 'total': len(result)}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/grievances/<grievance_id>/status', methods=['PATCH'])
@login_required
@proctor_only
@demo_restricted
@apply_rate_limit(Limits.MODERATE)
def update_grievance_status(grievance_id):
    """Update a grievance status (pending → in_progress → resolved)."""
    try:
        from bson import ObjectId
        db = get_db()
        data = request.get_json() or {}
        new_status = data.get('status', '')
        resolution_note = data.get('resolution_note', '').strip()

        if new_status not in ('pending', 'in_progress', 'resolved', 'dismissed'):
            return jsonify({'error': 'Invalid status'}), 400

        update = {
            'status': new_status,
            'updated_at': datetime.utcnow(),
            'updated_by': session.get('user_email', 'proctor')
        }
        if resolution_note:
            update['resolution_note'] = resolution_note

        result = db['grievances'].update_one(
            {'_id': ObjectId(grievance_id)},
            {'$set': update}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Grievance not found'}), 404

        log_activity(
            action=AuditAction.UPDATE_TICKET,
            target_type='grievance',
            target_id=grievance_id,
            metadata={'new_status': new_status}
        )

        return jsonify({'success': True, 'message': f'Grievance updated to {new_status}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# End of file
