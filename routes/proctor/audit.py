from flask import Blueprint, jsonify, request, render_template, session, Response, current_app
from bson import ObjectId
from datetime import datetime, timedelta
import uuid
import io
import csv
from utils.auth_helpers import login_required, demo_restricted, role_required
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

    # RBAC: scope audit logs based on role
    current_user = get_current_user()
    user_role = current_user.get('role', 'proctor') if current_user else 'proctor'
    if user_role != 'hod':
        # Non-HOD proctors can only see their own actions
        query['proctor_id'] = session.get('user_email', '')
    elif proctor_id:
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
    
    current_app.logger.info("✅ Created %s test incidents", len(incidents))
    current_app.logger.info("   - HIGH risk: 5 (all unreviewed)")
    current_app.logger.info("   - MEDIUM risk: 12 (8 unreviewed, 4 reviewed)")
    current_app.logger.info("   - LOW risk: 13 (varied status)")
    current_app.logger.info("   - Active alerts: %s", unreviewed_count)
    
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

