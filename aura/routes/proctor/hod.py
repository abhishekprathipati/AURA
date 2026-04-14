from flask import Blueprint, jsonify, request, render_template, session, Response, current_app
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


# ---------------------------------------------
# API: System Status
# ---------------------------------------------
