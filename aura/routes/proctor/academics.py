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


@proctor_bp.route('/api/parent-messages', methods=['GET'])
@login_required
@proctor_only
def get_parent_messages():
    """Get messages sent by parents to this proctor."""
    try:
        db = get_db()
        proctor_email = session.get('user_email', '')

        messages = list(db['proctor_messages'].find(
            {'receiver_email': proctor_email}
        ).sort('created_at', -1).limit(50))

        result = []
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            if isinstance(msg.get('created_at'), datetime):
                msg['time_ago'] = _time_since(msg['created_at'])
                msg['created_at'] = msg['created_at'].isoformat()
            result.append(msg)

        return jsonify({'success': True, 'data': result}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'proctor')}), 500


# End of file
