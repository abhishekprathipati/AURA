from flask import Blueprint, jsonify, request, render_template, session, Response, current_app
from functools import wraps
from datetime import datetime, timedelta
import uuid
import io
import csv
from utils.auth_helpers import login_required
from utils.database import get_db

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


def _ensure_indexes(db):
    db['risk_incidents'].create_index('incident_id', unique=True)
    db['risk_incidents'].create_index('status')
    db['risk_incidents'].create_index('risk_level')
    db['risk_incidents'].create_index('timestamp')

    db['proctor_actions'].create_index('action_id', unique=True)
    db['proctor_actions'].create_index('incident_id')
    db['proctor_actions'].create_index('proctor_id')
    db['proctor_actions'].create_index('timestamp')

    db['system_status'].create_index('status')


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
        'RISING': '↑',
        'FALLING': '↓',
        'STABLE': '→',
    }.get(trend, '→')


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
        'message_excerpt': doc.get('message_excerpt'),
        'room_name': doc.get('room_name'),
        'timestamp': doc.get('timestamp').isoformat() if doc.get('timestamp') else None,
        'report_count': doc.get('report_count', 1),
        'status': doc.get('status', 'UNREVIEWED'),
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
        'timestamp': doc.get('timestamp').isoformat() if doc.get('timestamp') else None,
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


@proctor_bp.route('/api/student/<anonymous_id>/details', methods=['GET'])
@login_required
@proctor_only
def get_student_details(anonymous_id):
    """Get detailed information about an anonymous student."""
    try:
        db = get_db()
        
        # Get all incidents for this anonymous student
        incidents = list(db['risk_incidents'].find(
            {'anonymous_student_id': anonymous_id},
            sort=[('timestamp', -1)]
        ))
        
        # Get actions taken on these incidents
        incident_ids = [inc.get('incident_id') for inc in incidents]
        actions = list(db['proctor_actions'].find(
            {'incident_id': {'$in': incident_ids}},
            sort=[('timestamp', -1)]
        ))
        
        # Calculate stats
        total_incidents = len(incidents)
        high_risk_count = sum(1 for i in incidents if i.get('risk_level') == 'HIGH')
        unreviewed_count = sum(1 for i in incidents if i.get('status') == 'UNREVIEWED')
        
        return jsonify({
            'success': True,
            'data': {
                'anonymous_id': anonymous_id,
                'total_incidents': total_incidents,
                'high_risk_count': high_risk_count,
                'unreviewed_count': unreviewed_count,
                'incidents': [_serialize_incident(i) for i in incidents[:20]],
                'actions': [_serialize_action(a) for a in actions[:20]]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@proctor_bp.route('/api/dashboard/summary', methods=['GET'])
@login_required
@proctor_only
def get_dashboard_summary():
    """Get comprehensive dashboard summary for proctor view."""
    try:
        db = get_db()
        _ensure_indexes(db)
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = datetime.utcnow() - timedelta(days=7)
        
        # Count incidents by status
        unreviewed = db['risk_incidents'].count_documents({'status': 'UNREVIEWED'})
        reviewed = db['risk_incidents'].count_documents({'status': 'REVIEWED'})
        dismissed = db['risk_incidents'].count_documents({'status': 'DISMISSED'})
        escalated = db['risk_incidents'].count_documents({'status': 'ESCALATED'})
        
        # Count by risk level
        high_risk = db['risk_incidents'].count_documents({'risk_level': 'HIGH', 'status': 'UNREVIEWED'})
        medium_risk = db['risk_incidents'].count_documents({'risk_level': 'MEDIUM', 'status': 'UNREVIEWED'})
        low_risk = db['risk_incidents'].count_documents({'risk_level': 'LOW', 'status': 'UNREVIEWED'})
        
        # Today's activity
        incidents_today = db['risk_incidents'].count_documents({'timestamp': {'$gte': today_start}})
        actions_today = db['proctor_actions'].count_documents({'timestamp': {'$gte': today_start}})
        
        # Weekly trend
        incidents_this_week = db['risk_incidents'].count_documents({'timestamp': {'$gte': week_start}})
        
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
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
    """Get HOD executive dashboard statistics."""
    try:
        db = get_db()
        _ensure_indexes(db)
        
        # Calculate date ranges
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = datetime.utcnow() - timedelta(days=7)
        month_start = datetime.utcnow() - timedelta(days=30)
        
        # Total active students (students with any wellness activity in last 30 days)
        active_students = len(list(db['student_wellness'].distinct('student_id', {
            'timestamp': {'$gte': month_start}
        })))
        
        # Total incidents
        total_incidents = db['risk_incidents'].count_documents({})
        unreviewed_incidents = db['risk_incidents'].count_documents({'status': 'UNREVIEWED'})
        high_risk_incidents = db['risk_incidents'].count_documents({'risk_level': 'HIGH', 'status': 'UNREVIEWED'})
        
        # Weekly incidents
        weekly_incidents = db['risk_incidents'].count_documents({'timestamp': {'$gte': week_start}})
        
        # Calculate average wellness score
        recent_wellness = list(db['student_wellness'].find(
            {'data_type': 'stress', 'timestamp': {'$gte': week_start}},
            {'value': 1}
        ).limit(1000))
        
        avg_wellness = 0
        if recent_wellness:
            total_stress = sum([w.get('value', 50) for w in recent_wellness])
            avg_stress = total_stress / len(recent_wellness)
            avg_wellness = round(100 - avg_stress, 1)  # Invert stress to wellness
        
        # Resolution rate
        resolved_count = db['risk_incidents'].count_documents({'status': {'$in': ['DISMISSED', 'ESCALATED', 'REMOVED']}})
        resolution_rate = round((resolved_count / total_incidents * 100) if total_incidents > 0 else 0, 1)
        
        # Proctor activity
        proctor_actions_today = db['proctor_actions'].count_documents({'timestamp': {'$gte': today_start}})
        
        return jsonify({
            'success': True,
            'data': {
                'active_students': active_students,
                'total_incidents': total_incidents,
                'unreviewed_incidents': unreviewed_incidents,
                'high_risk_incidents': high_risk_incidents,
                'weekly_incidents': weekly_incidents,
                'avg_wellness': avg_wellness,
                'resolution_rate': resolution_rate,
                'proctor_actions_today': proctor_actions_today
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@proctor_bp.route('/api/hod/wellness-trends', methods=['GET'])
@login_required
@hod_only
def hod_wellness_trends():
    """Get department-wide wellness trends for charts."""
    try:
        db = get_db()
        
        # Get daily averages for the past 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        pipeline = [
            {'$match': {
                'data_type': 'stress',
                'timestamp': {'$gte': thirty_days_ago}
            }},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                'avg_stress': {'$avg': '$value'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}},
            {'$limit': 30}
        ]
        
        daily_stats = list(db['student_wellness'].aggregate(pipeline))
        
        # Format for chart
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
        return jsonify({'success': False, 'error': str(e)}), 500


@proctor_bp.route('/api/hod/risk-distribution', methods=['GET'])
@login_required
@hod_only
def hod_risk_distribution():
    """Get risk level distribution for pie charts."""
    try:
        db = get_db()
        
        high_count = db['risk_incidents'].count_documents({'risk_level': 'HIGH'})
        medium_count = db['risk_incidents'].count_documents({'risk_level': 'MEDIUM'})
        low_count = db['risk_incidents'].count_documents({'risk_level': 'LOW'})
        
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
        return jsonify({'success': False, 'error': str(e)}), 500


@proctor_bp.route('/api/hod/proctor-performance', methods=['GET'])
@login_required
@hod_only
def hod_proctor_performance():
    """Get proctor performance metrics."""
    try:
        db = get_db()
        week_start = datetime.utcnow() - timedelta(days=7)
        
        # Get all proctor actions in the past week
        pipeline = [
            {'$match': {'timestamp': {'$gte': week_start}}},
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
        return jsonify({'success': False, 'error': str(e)}), 500


@proctor_bp.route('/api/hod/recent-escalations', methods=['GET'])
@login_required
@hod_only
def hod_recent_escalations():
    """Get recent escalated incidents for HOD review."""
    try:
        db = get_db()
        
        escalated = list(db['risk_incidents'].find(
            {'status': 'ESCALATED'},
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
        return jsonify({'success': False, 'error': str(e)}), 500

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

    query = {}
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

    incidents = list(
        coll.find({field_name: {'$regex': query_text, '$options': 'i'}})
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
def handle_action(action_type):
    if action_type not in ['dismiss', 'remove', 'escalate']:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400

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

    action_map = {
        'dismiss': ('DISMISS', 'DISMISSED'),
        'remove': ('REMOVE', 'REMOVED'),
        'escalate': ('ESCALATE', 'ESCALATED'),
    }
    action_label, status_label = action_map[action_type]

    action_doc = {
        'action_id': str(uuid.uuid4()),
        'incident_id': incident_id,
        'proctor_id': session.get('user_email', 'UNKNOWN'),
        'action_type': action_label,
        'reason_code': reason,
        'details': details,
        'timestamp': datetime.utcnow(),
    }

    db['proctor_actions'].insert_one(action_doc)
    db['risk_incidents'].update_one({'incident_id': incident_id}, {'$set': {'status': status_label}})

    incident = db['risk_incidents'].find_one({'incident_id': incident_id})

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
def bulk_action():
    data = request.get_json() or {}
    incident_ids = data.get('incident_ids') or []
    action_type = data.get('action_type')
    reason = data.get('reason', 'BULK_ACTION')
    details = data.get('details', 'Bulk action via proctor dashboard')

    if action_type not in ['dismiss', 'remove', 'escalate']:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    if not incident_ids:
        return jsonify({'success': False, 'error': 'No incident IDs provided'}), 400

    db = get_db()
    _ensure_indexes(db)
    coll = db['risk_incidents']

    action_map = {
        'dismiss': ('DISMISS', 'DISMISSED'),
        'remove': ('REMOVE', 'REMOVED'),
        'escalate': ('ESCALATE', 'ESCALATED'),
    }
    action_label, status_label = action_map[action_type]

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
        coll.update_one({'incident_id': incident['incident_id']}, {'$set': {'status': status_label}})
        updated_ids.append(incident['incident_id'])

    if actions_to_insert:
        db['proctor_actions'].insert_many(actions_to_insert)

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
def export_audit_csv():
    db = get_db()
    _ensure_indexes(db)
    days = request.args.get('days', 7, type=int)

    since_date = datetime.utcnow() - timedelta(days=days)
    logs = list(
        db['proctor_actions']
        .find({'timestamp': {'$gte': since_date}})
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
        return jsonify({'status': 'degraded', 'error': str(e)}), 500

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
    
    print(f"✅ Created {len(incidents)} test incidents")
    print(f"   - HIGH risk: 5 (all unreviewed)")
    print(f"   - MEDIUM risk: 12 (8 unreviewed, 4 reviewed)")
    print(f"   - LOW risk: 13 (varied status)")
    print(f"   - Active alerts: {unreviewed_count}")
    
    return len(incidents)


@proctor_bp.route('/api/test/seed', methods=['POST'])
@login_required
@proctor_only
def seed_test_data():
    """API endpoint to populate test data."""
    try:
        count = create_test_incidents()
        return jsonify({'success': True, 'incidents_created': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# End of file
