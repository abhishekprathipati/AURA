from flask import Blueprint, jsonify, request, render_template, session, Response, current_app
from bson import ObjectId
from datetime import datetime, timedelta
import uuid
import io
import csv
from utils.auth_helpers import login_required, demo_restricted, role_required, csrf_protected
from utils.database import get_db
from utils.audit_logger import log_activity, AuditAction
from utils.rate_limit import apply_rate_limit, Limits
from utils.access_control import (
    get_visible_student_ids, get_visible_students, get_incident_filter,
    can_access_student, create_anonymous_id, get_current_user,
)
from utils.helpers import safe_error
from routes.proctor import (
    proctor_bp, proctor_only, hod_only,
    _ensure_indexes, _time_since, _trend_icon, _risk_color,
    _severity_score, _serialize_incident, _serialize_action, _default_status,
)

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
@demo_restricted
@csrf_protected
@apply_rate_limit(Limits.MODERATE)
def add_student():
    """Add a new student under this proctor's ward."""
    try:
        data = request.get_json() or {}

        from utils.schemas import StudentAddRequest, ValidationError as SchemaError
        try:
            req = StudentAddRequest.model_validate(request.get_json() or {})
        except SchemaError as exc:
            return jsonify({'success': False, 'error': exc.errors()[0]['msg']}), 400

        name = req.name
        roll_number = req.roll_number
        email = req.email
        department = req.department
        parent_name = req.parent_name
        parent_phone = req.parent_phone

        proctor_id = session.get('user_email', 'UNKNOWN')

        from services.proctor_service import register_new_student
        student_data = {
            'name': name,
            'roll_number': roll_number,
            'email': email,
            'department': department,
            'parent_name': parent_name,
            'parent_phone': parent_phone,
            'semester': data.get('semester', '4'),
            'section': data.get('section', 'A'),
            'risk_level': data.get('risk_level', 'low'),
            'blood_group': data.get('blood_group', ''),
            'notes': data.get('notes', ''),
            'parent_email': data.get('parent_email', ''),
            'parent_relationship': data.get('parent_relationship', 'parent')
        }

        result = register_new_student(proctor_id, student_data)
        if not result['success']:
            return jsonify({'success': False, 'error': result['error']}), result.get('status_code', 400)
            
        temp_password = result['temp_password']
        anonymous_id = result['anonymous_id']

        log_activity(
            action=AuditAction.ADD_STUDENT,
            target_type='student',
            target_id=anonymous_id,
            metadata={'email': email, 'name': name, 'roll_number': roll_number, 'department': department}
        )

        return jsonify({
            'success': True,
            'message': f'Student {name} ({roll_number}) added successfully.',
            'student_id': result.get('student_id', anonymous_id),
            'anonymous_id': anonymous_id,
            'temp_password': temp_password,  # Shown once - share with student securely
        })
    except Exception as exc:
        current_app.logger.error('add_student error: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': safe_error(exc, 'proctor_api')}), 500


# ---------------------------------------------
# HOD: Add Proctor (can be used by HOD to onboard proctors)
# ---------------------------------------------


@proctor_bp.route('/api/proctor/add', methods=['POST'])
@login_required
@role_required('hod')
@demo_restricted
@csrf_protected
@apply_rate_limit(Limits.MODERATE)
def add_proctor():
    """HOD-only endpoint to add a proctor. Similar to add_student but
    only requires proctor name, email, phone, and department. Parent details
    are NOT required for proctors.
    """
    try:
        from utils.schemas import ProctorAddRequest, ValidationError as SchemaError
        try:
            req = ProctorAddRequest.model_validate(request.get_json() or {})
        except SchemaError as exc:
            return jsonify({'success': False, 'error': exc.errors()[0]['msg']}), 400

        name = req.name
        email = req.email
        phone = req.phone
        department = req.department

        db = get_db()
        hod_id = session.get('user_email', 'UNKNOWN')

        # Prevent duplicate or conflicting accounts by email
        existing = db['users'].find_one({'email': email})
        if existing:
            return jsonify({'success': False, 'error': f'Account with email {email} already exists.'}), 409

        from utils.auth_helpers import hash_password, generate_temp_password
        temp_password = generate_temp_password()

        proctor_record = {
            'email': email,
            'hashed_password': hash_password(temp_password),
            'must_change_password': True,
            'name': name,
            'role': 'proctor',
            'department': department,
            'phone': phone,
            'created_at': datetime.utcnow(),
            'created_by': hod_id,
            'status': 'active',
        }

        # Upsert into users collection
        db['users'].update_one({'email': email}, {'$set': proctor_record}, upsert=True)

        # Also ensure proctor profile collection exists for assignments
        db['proctors'].update_one({'email': email}, {'$setOnInsert': {
            'email': email,
            'name': name,
            'department': department,
            'phone': phone,
            'assigned_students': [],
            'created_at': datetime.utcnow(),
        }}, upsert=True)

        log_activity(
            action=AuditAction.ADD_PROCTOR,
            target_type='proctor',
            target_id=email,
            metadata={'added_by': hod_id, 'email': email, 'name': name, 'department': department}
        )

        return jsonify({'success': True, 'message': f'Proctor {name} <{email}> added successfully.', 'temp_password': temp_password}), 200

    except Exception as exc:
        current_app.logger.error('add_proctor error: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': safe_error(exc, 'proctor_api')}), 500


@proctor_bp.route('/api/hod/parent-suggestions', methods=['GET'])
@login_required
@hod_only
def hod_parent_suggestions():
    """Read-only department-scoped parent suggestions for the HOD dashboard."""
    try:
        db = get_db()
        department = session.get('user_department', '')

        dept_students = list(db['users'].find(
            {'role': 'student', 'department': department},
            {'roll_number': 1, 'name': 1, '_id': 0}
        )) if department else []

        roll_numbers = [student.get('roll_number') for student in dept_students if student.get('roll_number')]
        student_lookup = {
            student.get('roll_number'): student.get('name', 'Student')
            for student in dept_students
            if student.get('roll_number')
        }

        if not roll_numbers:
            return jsonify({'success': True, 'data': [], 'count': 0}), 200

        suggestions = list(db['parent_suggestions'].find(
            {'student_roll': {'$in': roll_numbers}},
            sort=[('created_at', -1)],
            limit=25
        ))

        formatted = []
        for suggestion in suggestions:
            roll_number = suggestion.get('student_roll')
            formatted.append({
                'id': str(suggestion.get('_id')),
                'student_roll': roll_number,
                'student_name': student_lookup.get(roll_number, 'Student'),
                'parent_name': suggestion.get('parent_name', 'Parent'),
                'title': suggestion.get('title', ''),
                'description': suggestion.get('description', ''),
                'category': suggestion.get('category', 'general'),
                'status': suggestion.get('status', 'pending'),
                'upvotes': suggestion.get('upvotes', 0),
                'created_at': suggestion.get('created_at').isoformat() if suggestion.get('created_at') else None,
                'reviewed_at': suggestion.get('reviewed_at').isoformat() if suggestion.get('reviewed_at') else None,
                'reviewed_by': suggestion.get('reviewed_by', ''),
                'review_note': suggestion.get('review_note', ''),
                'implemented_at': suggestion.get('implemented_at').isoformat() if suggestion.get('implemented_at') else None,
                'implemented_by': suggestion.get('implemented_by', ''),
                'implementation_note': suggestion.get('implementation_note', ''),
            })

        return jsonify({'success': True, 'data': formatted, 'count': len(formatted)}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/parent-suggestions/<suggestion_id>/status', methods=['PATCH'])
@login_required
@hod_only
@demo_restricted
@csrf_protected
@apply_rate_limit(Limits.MODERATE)
def update_parent_suggestion_status(suggestion_id):
    """Update a department parent suggestion to reviewed or implemented."""
    try:
        data = request.get_json() or {}
        new_status = (data.get('status') or '').strip().lower()
        note = (data.get('note') or '').strip()
        if new_status not in {'reviewed', 'implemented'}:
            return jsonify({'success': False, 'error': 'Status must be reviewed or implemented.'}), 400

        db = get_db()
        suggestion = db['parent_suggestions'].find_one({'_id': ObjectId(suggestion_id)})
        if not suggestion:
            return jsonify({'success': False, 'error': 'Suggestion not found.'}), 404

        department = session.get('user_department', '')
        student = db['users'].find_one(
            {'role': 'student', 'roll_number': suggestion.get('student_roll'), 'department': department},
            {'roll_number': 1}
        )
        if not student:
            return jsonify({'success': False, 'error': 'Access denied.'}), 403

        update_fields = {
            'status': new_status,
            'updated_at': datetime.utcnow(),
            'updated_by': session.get('user_email', ''),
        }
        if new_status == 'reviewed':
            update_fields['reviewed_at'] = datetime.utcnow()
            update_fields['reviewed_by'] = session.get('user_email', '')
            if note:
                update_fields['review_note'] = note
        if new_status == 'implemented':
            update_fields['implemented_at'] = datetime.utcnow()
            update_fields['implemented_by'] = session.get('user_email', '')
            if note:
                update_fields['implementation_note'] = note

        db['parent_suggestions'].update_one({'_id': ObjectId(suggestion_id)}, {'$set': update_fields})

        log_activity(
            action=AuditAction.UPDATE_TICKET,
            target_type='parent_suggestion',
            target_id=suggestion_id,
            metadata={'status': new_status, 'student_roll': suggestion.get('student_roll'), 'note': note}
        )

        return jsonify({'success': True, 'message': f'Suggestion marked as {new_status}.'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/proctors', methods=['GET'])
@login_required
@hod_only
def hod_manage_proctors():
    """List department proctors for HOD management view."""
    try:
        db = get_db()
        department = session.get('user_department', '')
        proctors = list(db['users'].find(
            {'role': 'proctor', 'department': department},
            {'name': 1, 'email': 1, 'phone': 1, 'department': 1, 'status': 1, 'created_at': 1, '_id': 0}
        ).sort('created_at', -1)) if department else []

        data = []
        for proctor in proctors:
            email = proctor.get('email', '')
            assigned_students = db['proctor_students'].count_documents({'proctor_id': email, 'status': 'active'})
            recent_actions = db['proctor_actions'].count_documents({
                'proctor_id': email,
                'timestamp': {'$gte': datetime.utcnow() - timedelta(days=7)}
            })
            data.append({
                'name': proctor.get('name', 'Proctor'),
                'email': email,
                'phone': proctor.get('phone', ''),
                'department': proctor.get('department', department),
                'status': proctor.get('status', 'active'),
                'created_at': proctor.get('created_at').isoformat() if proctor.get('created_at') else None,
                'assigned_students': assigned_students,
                'recent_actions': recent_actions,
            })

        return jsonify({'success': True, 'data': data, 'count': len(data)}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


