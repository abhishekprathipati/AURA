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

        # â”€â”€ Support ticket signals inferred from incidents â”€â”€
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


