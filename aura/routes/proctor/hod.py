from flask import Blueprint, jsonify, request, render_template, session, Response, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime, timedelta
import uuid
import io
import csv
from aura.utils.auth_helpers import login_required, demo_restricted, role_required
from aura.utils.database import get_db
from aura.utils.audit_logger import log_activity, AuditAction
from aura.utils.rate_limit import apply_rate_limit, Limits
from aura.utils.access_control import (
    get_visible_student_ids, get_visible_students, get_incident_filter,
    can_access_student, create_anonymous_id, get_current_user,
)
from aura.utils.helpers import safe_error
from aura.routes.proctor import (
    proctor_bp, proctor_only, hod_only,
    _ensure_indexes, _time_since, _trend_icon, _risk_color,
    _severity_score, _serialize_incident, _serialize_action, _default_status,
)

@proctor_bp.route('/hod')
@login_required
def hod_dashboard():
    """HOD Executive Dashboard - Department-level analytics and oversight."""
    role = session.get('user_role')
    if role != 'hod':
        return jsonify({'error': 'Unauthorized - HOD access only'}), 403
    hod_name = session.get('user_name', 'HOD')
    hod_email = session.get('user_email', 'hod@aura.edu')
    hod_department = session.get('user_department', 'AIML')
    return render_template('hod_dashboard.html', hod_name=hod_name, hod_email=hod_email, hod_department=hod_department)


# ---------------------------------------------
# HOD-SPECIFIC API ENDPOINTS
# ---------------------------------------------

@proctor_bp.route('/api/hod/dashboard-stats', methods=['GET'])
@login_required
@hod_only
def hod_dashboard_stats():
    """Get HOD executive dashboard statistics — department-scoped."""
    try:
        db = get_db()
        _ensure_indexes(db)
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = datetime.utcnow() - timedelta(days=7)
        month_start = datetime.utcnow() - timedelta(days=30)
        department = session.get('user_department', '')
        
        # ── RBAC: scope to department students ──
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
    """Get department-wide wellness trends for charts — department-scoped."""
    try:
        db = get_db()
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # ── RBAC: only department students ──
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
    """Get risk level distribution — department-scoped."""
    try:
        db = get_db()
        
        # ── RBAC: scope to visible students ──
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
    """Get proctor performance metrics — department-scoped."""
    try:
        db = get_db()
        week_start = datetime.utcnow() - timedelta(days=7)
        department = session.get('user_department', '')
        
        # ── RBAC: only proctors in this department ──
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
    """Get recent escalated incidents — department-scoped."""
    try:
        db = get_db()
        
        # ── RBAC: scope to department students ──
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


@proctor_bp.route('/api/hod/risk-oversight', methods=['GET'])
@login_required
@hod_only
def hod_risk_oversight():
    """Combined feed of high-priority and escalated incidents for HOD monitoring."""
    try:
        db = get_db()
        visible_ids = get_visible_student_ids()
        if not visible_ids:
            return jsonify({'success': True, 'data': []}), 200
            
        # 1. Unreviewed High/Medium
        # 2. Escalated (Regardless of risk level)
        query = {
            'anonymous_student_id': {'$in': visible_ids},
            '$or': [
                {'status': 'ESCALATED'},
                {'risk_level': {'$in': ['HIGH', 'MEDIUM']}, 'status': 'UNREVIEWED'}
            ]
        }
        
        incidents = list(db['risk_incidents'].find(
            query,
            sort=[('timestamp', -1)],
            limit=30
        ))
        
        formatted = []
        for inc in incidents:
            formatted.append({
                'id': str(inc['_id']),
                'incident_id': inc.get('incident_id'),
                'anonymous_student_id': inc.get('anonymous_student_id'),
                'risk_level': inc.get('risk_level'),
                'trigger_source': inc.get('trigger_source'),
                'status': inc.get('status'),
                'message_excerpt': inc.get('message_excerpt', '')[:100],
                'timestamp': inc.get('timestamp').isoformat() if inc.get('timestamp') else None,
                'is_escalated': inc.get('status') == 'ESCALATED'
            })
            
        return jsonify({
            'success': True,
            'data': formatted,
            'count': len(formatted)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/students', methods=['GET'])
@login_required
@hod_only
def hod_list_students():
    """List all students in the HOD's department for oversight."""
    try:
        db = get_db()
        dept_students = get_visible_students()
        
        formatted = []
        for s in dept_students:
            formatted.append({
                'name': s.get('name', 'N/A'),
                'roll_number': s.get('roll_number', 'N/A'),
                'department': s.get('department', 'N/A'),
                'risk_level': s.get('risk_level', 'LOW'),
                'anonymous_id': s.get('anonymous_id', ''),
                'proctor_id': s.get('proctor_id', 'Unassigned'),
                'last_active': s.get('updated_at').isoformat() if s.get('updated_at') else None
            })
            
        return jsonify({
            'success': True,
            'data': formatted,
            'count': len(formatted)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/escalate-student', methods=['POST'])
@login_required
@hod_only
def hod_escalate_student():
    """HOD-level student escalation: Marks a student for urgent attention."""
    try:
        data = request.json or {}
        anon_id = data.get('anonymous_id')
        reason = data.get('reason', 'High-level executive oversight escalation')
        
        if not anon_id:
            return jsonify({'success': False, 'error': 'Student ID is required'}), 400
            
        db = get_db()
        # Ensure we have access to this student
        visible_ids = get_visible_student_ids()
        if anon_id not in visible_ids:
            return jsonify({'success': False, 'error': 'Access denied or student not in department'}), 403

        # Create/Update dummy incident for tracking escalation
        incident_id = f"HOD-ESC-{uuid.uuid4().hex[:6].upper()}"
        escalation_doc = {
            'incident_id': incident_id,
            'anonymous_student_id': anon_id,
            'risk_level': 'HIGH',
            'trigger_source': 'HOD_ESCALATION',
            'status': 'ESCALATED',
            'case_status': 'assigned',
            'assigned_to': 'COUNSELOR_POOL',
            'message_excerpt': reason,
            'timestamp': datetime.utcnow(),
            'auto_triggered': False
        }
        
        db['risk_incidents'].insert_one(escalation_doc)
        
        # Sync student risk level
        db['proctor_students'].update_one(
            {'anonymous_id': anon_id},
            {'$set': {'risk_level': 'HIGH', 'updated_at': datetime.utcnow()}}
        )
        
        log_activity(AuditAction.ESCALATE_INCIDENT, target_type='student', target_id=anon_id, metadata={'reason': reason})
        
        return jsonify({'success': True, 'message': f'Student {anon_id} escalated to counselor.'}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/message-proctor', methods=['POST'])
@login_required
@hod_only
def hod_message_proctor():
    """Send an oversight message/notification from HOD to a proctor."""
    try:
        data = request.json or {}
        proctor_id = data.get('proctor_id')
        anon_id = data.get('anonymous_id')
        message = data.get('message')
        
        if not all([proctor_id, message]):
            return jsonify({'success': False, 'error': 'Proctor ID and message are required'}), 400
            
        db = get_db()
        department = session.get('user_department', '')
        hod_email = session.get('user_email', 'HOD')

        # Security: verify proctor exists and belongs to this HOD's department
        target_proctor = db['users'].find_one({'email': proctor_id, 'role': 'proctor', 'department': department})
        if not target_proctor:
            return jsonify({'success': False, 'error': 'Unauthorized - Proctor not found in your department'}), 403
        
        comm_doc = {
            'comm_id': str(uuid.uuid4()),
            'from': hod_email,
            'to': proctor_id,
            'student_context': anon_id,
            'message': message,
            'read': False,
            'timestamp': datetime.utcnow()
        }
        
        db['hod_communications'].insert_one(comm_doc)
        log_activity(AuditAction.CONTACT_STUDENT, target_type='proctor', target_id=proctor_id, metadata={'student': anon_id})
        
        return jsonify({'success': True, 'message': f'Message sent to proctor {proctor_id}.'}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# ---------------------------------------------
# API: System Status
# ---------------------------------------------


# ---------------------------------------------
# API: Proctor Management
# ---------------------------------------------

@proctor_bp.route('/api/hod/department-proctors', methods=['GET'])
@login_required
@hod_only
def hod_list_proctors():
    """List all proctors assigned to the HOD's department."""
    try:
        db = get_db()
        department = session.get('user_department', '')
        if not department:
            return jsonify({'success': False, 'error': 'No department associated with shift'}), 400
            
        proctors = list(db['users'].find(
            {'role': 'proctor', 'department': department},
            {'_id': 0, 'password': 0}
        ))
        
        return jsonify({'success': True, 'data': proctors}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/manage-proctors', methods=['POST'])
@login_required
@hod_only
def hod_add_proctor():
    """Add a new proctor to the department."""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()
        password = data.get('password', '').strip()
        
        department = session.get('user_department')
        user_email = session.get('user_email', '')
        db = get_db()
        
        # Fallback to fetch from DB if session lacks department
        if not department:
            hod_user = db['users'].find_one({'email': user_email})
            if hod_user and 'department' in hod_user:
                department = hod_user['department']
                
        if not department:
            return jsonify({'success': False, 'error': 'Could not determine your department.'}), 400
        
        if not email or not name or not password:
            return jsonify({'success': False, 'error': 'Missing required fields (Email, Name, or Password).'}), 400
            
        if db['users'].find_one({'email': email}):
            return jsonify({'success': False, 'error': 'User with this email already exists'}), 400
            
        from aura.utils.auth_helpers import hash_password
        from aura.models.user import UserModel
        
        # Add to users collection
        new_user = {
            'user_id': UserModel.generate_user_id(),
            'email': email,
            'name': name,
            'hashed_password': hash_password(password),
            'must_change_password': True,
            'role': 'proctor',
            'department': department,
            'phone': '', # Default empty if not provided
            'created_at': datetime.utcnow(),
            'created_by': user_email,
            'status': 'active',
            'is_demo': False
        }
        db['users'].insert_one(new_user)
        
        # Ensure proctor profile collection exists for assignments
        db['proctors'].update_one({'email': email}, {'$setOnInsert': {
            'email': email,
            'name': name,
            'department': department,
            'phone': '',
            'assigned_students': [],
            'created_at': datetime.utcnow(),
        }}, upsert=True)
        
        log_activity(AuditAction.ADD_PROCTOR, target_type='proctor', target_id=email, metadata={'department': department, 'added_by': user_email})
        
        return jsonify({'success': True, 'message': f'Proctor {name} successfully added to {department}.'}), 201
    except Exception as e:
        import logging
        logging.error(f"Error adding proctor: {e}", exc_info=True)
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


@proctor_bp.route('/api/hod/manage-proctors/<email>', methods=['DELETE'])
@login_required
@hod_only
def hod_remove_proctor(email):
    """Remove a proctor from the department."""
    try:
        department = session.get('user_department', '')
        db = get_db()
        
        # Security & Cleanup: verify proctor belongs to this HOD's department
        target = db['users'].find_one({'email': email, 'role': 'proctor'})
        if not target or target.get('department') != department:
            return jsonify({'success': False, 'error': 'Unauthorized or proctor not found in your department'}), 403
            
        # 1. Remove from users (Auth)
        db['users'].delete_one({'email': email})
        
        # 2. Remove from proctors (Profile)
        db['proctors'].delete_one({'email': email})
        
        # 3. Handle assigned students (Unassign to prevent ghost links)
        db['proctor_students'].update_many(
            {'proctor_id': email},
            {'$set': {'proctor_id': 'Unassigned', 'updated_at': datetime.utcnow()}}
        )
        
        log_activity(AuditAction.CONFIG_CHANGE, f"HOD removed proctor {email}")
        
        return jsonify({'success': True, 'message': 'Proctor removed and students unassigned.'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# ---------------------------------------------
# API: CSV Export
# ---------------------------------------------

@proctor_bp.route('/api/hod/export-analytics', methods=['GET'])
@login_required
@hod_only
def hod_export_analytics():
    """Export department-wide risk analytics as CSV."""
    try:
        db = get_db()
        visible_ids = get_visible_student_ids()
        department = session.get('user_department', 'AURA')
        
        incidents = list(db['risk_incidents'].find(
            {'anonymous_student_id': {'$in': visible_ids}},
            sort=[('timestamp', -1)]
        ))
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Incident ID', 'Student ID', 'Risk Level', 'Source', 'Status', 'Timestamp', 'Summary'])
        
        for inc in incidents:
            writer.writerow([
                inc.get('incident_id'),
                inc.get('anonymous_student_id'),
                inc.get('risk_level'),
                inc.get('trigger_source'),
                inc.get('status'),
                inc.get('timestamp').strftime('%Y-%m-%d %H:%M:%S') if inc.get('timestamp') else '',
                inc.get('message_excerpt', '')[:200]
            ])
            
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=hod_analytics_{department}_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------
# API: Community Feedback (Suggestions & Grievances)
# ---------------------------------------------

@proctor_bp.route('/api/hod/community-feedback', methods=['GET'])
@login_required
@hod_only
def hod_community_feedback():
    """Get department-scoped parent suggestions and student grievances."""
    try:
        db = get_db()
        department = session.get('user_department', '')
        if not department:
            return jsonify({'success': False, 'error': 'No department associated with session'}), 400

        # 1. Fetch department students for scoping
        dept_students = list(db['users'].find(
            {'role': 'student', 'department': department},
            {'roll_number': 1, 'email': 1, 'name': 1, '_id': 0}
        ))
        
        student_emails = [s.get('email') for s in dept_students if s.get('email')]
        student_rolls = [s.get('roll_number') for s in dept_students if s.get('roll_number')]
        
        student_lookup = {s.get('email'): s.get('name', 'Student') for s in dept_students if s.get('email')}
        roll_lookup = {s.get('roll_number'): s.get('name', 'Student') for s in dept_students if s.get('roll_number')}

        # 2. Fetch Parent Suggestions
        parent_sugs = list(db['parent_suggestions'].find(
            {'student_roll': {'$in': student_rolls}},
            sort=[('created_at', -1)],
            limit=20
        ))
        
        # 3. Fetch Parent Complaints
        parent_complaints = list(db['parent_complaints'].find(
            {'student_roll': {'$in': student_rolls}},
            sort=[('created_at', -1)],
            limit=20
        ))
        
        # 4. Fetch Student Grievances
        student_grievances = list(db['grievances'].find(
            {'user_email': {'$in': student_emails}},
            sort=[('created_at', -1)],
            limit=20
        ))

        feedback = []
        
        # Format Suggestions
        for sug in parent_sugs:
            feedback.append({
                'id': str(sug['_id']),
                'type': 'SUGGESTION',
                'source': 'Parent',
                'author': sug.get('parent_name', 'Parent'),
                'student': roll_lookup.get(sug.get('student_roll'), 'Unknown'),
                'title': sug.get('title', 'No Title'),
                'text': sug.get('description', ''),
                'status': sug.get('status', 'pending'),
                'timestamp': sug.get('created_at').isoformat() if sug.get('created_at') else None
            })

        # Format Complaints
        for cmp in parent_complaints:
            feedback.append({
                'id': str(cmp['_id']),
                'type': 'COMPLAINT',
                'source': 'Parent',
                'author': cmp.get('parent_name', 'Parent'),
                'student': roll_lookup.get(cmp.get('student_roll'), 'Unknown'),
                'title': cmp.get('subject', 'No Subject'),
                'text': cmp.get('description', ''),
                'status': cmp.get('status', 'pending'),
                'priority': cmp.get('priority', 'medium'),
                'timestamp': cmp.get('created_at').isoformat() if cmp.get('created_at') else None
            })
            
        # Format Grievances
        for grv in student_grievances:
            feedback.append({
                'id': str(grv['_id']),
                'type': 'GRIEVANCE',
                'source': 'Student',
                'author': student_lookup.get(grv.get('user_email'), 'Student'),
                'student': student_lookup.get(grv.get('user_email'), 'Student'),
                'title': grv.get('subject', 'No Subject'),
                'text': grv.get('description', ''),
                'status': grv.get('status', 'pending'),
                'timestamp': grv.get('created_at').isoformat() if grv.get('created_at') else None
            })

        # Sort combined feed by timestamp descending (safety fallback for missing dates)
        feedback.sort(key=lambda x: x.get('timestamp') or datetime.min.isoformat(), reverse=True)

        return jsonify({
            'success': True,
            'data': feedback[:30]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500
