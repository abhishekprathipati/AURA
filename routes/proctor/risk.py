from flask import Blueprint, jsonify, request, render_template, session, Response, current_app
from bson import ObjectId
from datetime import datetime, timedelta
import uuid
import io
import csv
import re
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

    last_update = status.get('last_update') or datetime.utcnow()
    
    return jsonify({'success': True, 'data': {
        'status': status.get('status', 'LIVE'),
        'active_students': status.get('active_students', 0),
        'active_alerts': status.get('active_alerts', 0),
        'connection_hub_state': status.get('connection_hub_state', 'CALM'),
        'last_update': last_update.isoformat(),
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

    sort_field = sort_by if sort_by in ['timestamp', 'risk_level'] else 'timestamp'
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

    # ── RBAC: scope search to visible students ──
    visible_ids = get_visible_student_ids()
    if not visible_ids:
        return jsonify({'success': True, 'count': 0, 'data': []})
    # Escape regex special characters to prevent ReDoS attacks
    safe_query = re.escape(query_text)
    search_query = {field_name: {'$regex': safe_query, '$options': 'i'}}
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
@csrf_protected
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
@csrf_protected
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
    if len(incident_ids) > 50:
        return jsonify({'success': False, 'error': 'Maximum 50 incidents per bulk action'}), 400

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

    # RBAC: only process incidents the proctor has access to
    visible_ids = get_visible_student_ids()
    rbac_filter = {'incident_id': {'$in': incident_ids}}
    if visible_ids:
        rbac_filter['anonymous_student_id'] = {'$in': visible_ids}
    incidents = list(coll.find(rbac_filter))
    if not incidents:
        return jsonify({'success': False, 'error': 'No accessible incidents found'}), 404

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

