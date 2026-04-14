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

