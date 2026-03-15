from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_helpers import login_required, demo_restricted, is_demo_account, DEMO_CHAT_LIMIT, DEMO_GAME_TIME_LIMIT
from utils.database import get_db
from utils.access_control import create_anonymous_id
from utils.helpers import safe_error, contains_blocked_content
from models.mood import MoodModel
from models.stress import StressModel
from models.grievance import GrievanceModel
from services.stress_service import calculate_dynamic_stress, get_stress_history as fetch_stress_history, get_weekly_stats
from datetime import datetime, timedelta
from bson import ObjectId
from collections import OrderedDict
import uuid
import hashlib

# Create the Blueprint
student_bp = Blueprint('student', __name__)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def bucket_by_day(history):
    """
    Bucket stress history by calendar day, keeping latest entry per day.
    
    Args:
        history: list of dicts with {timestamp, score}
    
    Returns:
        list with one entry per day (latest wins), ordered by date
    """
    buckets = OrderedDict()
    
    for item in sorted(history, key=lambda x: x["timestamp"]):
        # Extract date (ignoring time)
        dt = datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00'))
        day = dt.date()
        buckets[day] = item  # Overwrite = keep latest
    
    return list(buckets.values())


# ==========================================
# PHASE 4: GOVERNANCE ARCHITECTURE
# ==========================================
# Three-layer separation:
# 1. STUDENT LAYER: Personal wellness (mood, stress, trends)
# 2. SIGNAL PIPELINE: Hidden evaluation (backend-only, never shown to student)
# 3. PROCTOR LAYER: Anonymous incidents (created by signal pipeline)
#
# KEY PRINCIPLE: One-way data flow
# Student actions → Wellness entries → Signal evaluation (hidden) → Risk incidents → Proctor queue
#
# Student NEVER sees: Risk labels, signal logic, monitoring language, proctor activity
# Proctor NEVER sees: Student identity (only anonymous ID)

# ==========================================
# 1. PAGE ROUTES (Navigation)
# ==========================================

@student_bp.route('/dashboard')
@login_required
def dashboard():
    # Helper variable show_nav=False hides the top bar in base.html logic
    return render_template('student_dashboard.html', show_nav=False)

@student_bp.route('/chat/mental')
@login_required
def mental_chatbot():
    return render_template('mental_chatbot.html', show_nav=True,
                           is_demo=is_demo_account(),
                           demo_chat_limit=DEMO_CHAT_LIMIT,
                           demo_chat_used=session.get('demo_chat_count', 0))

@student_bp.route('/chat/study')
@login_required
def study_chatbot():
    return render_template('study_chatbot.html', show_nav=True,
                           is_demo=is_demo_account(),
                           demo_chat_limit=DEMO_CHAT_LIMIT,
                           demo_chat_used=session.get('demo_chat_count', 0))

@student_bp.route('/relax')
@login_required
def relax():
    return render_template('relax.html', show_nav=True,
                           is_demo=is_demo_account(),
                           demo_time_limit=DEMO_GAME_TIME_LIMIT)

@student_bp.route('/activities')
@login_required
def activities():
    return render_template('activities.html', show_nav=True,
                           is_demo=is_demo_account(),
                           demo_time_limit=DEMO_GAME_TIME_LIMIT)

@student_bp.route('/games')
@login_required
def games():
    return render_template('games.html', show_nav=True,
                           is_demo=is_demo_account(),
                           demo_time_limit=DEMO_GAME_TIME_LIMIT)

@student_bp.route('/_unregister_sw')
@login_required
def unregister_sw():
    return render_template('unregister_sw.html')

# ==========================================
# PHASE 4: CORE WELLNESS API (Student-facing, no risk labels)
# ==========================================

@student_bp.route('/api/wellness/current', methods=['GET'])
@login_required
def get_current_wellness():
    """
    STUDENT-FACING ENDPOINT
    Returns personal wellness data WITH live-computed stress.
    Student never sees "risk level", "alert", or monitoring language.
    """
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401
        
        db = get_db()
        
        # Get latest mood entry
        mood_coll = db['student_wellness']
        latest_mood = mood_coll.find_one(
            {'student_id': user_email, 'data_type': 'mood'},
            sort=[('timestamp', -1)]
        )
        
        # Calculate mood trend (no risk labels - just neutral descriptors)
        mood_trends = list(mood_coll.find(
            {'student_id': user_email, 'data_type': 'mood'},
            sort=[('timestamp', -1)],
            limit=5
        ))
        
        mood_value = latest_mood.get('value', 3) if latest_mood else 3
        mood_trend = 'stable'
        if len(mood_trends) >= 2:
            if mood_trends[0]['value'] > mood_trends[-1]['value']:
                mood_trend = 'improving'
            elif mood_trends[0]['value'] < mood_trends[-1]['value']:
                mood_trend = 'declining'
        
        # Neutral mood labels (never alarming)
        mood_labels = {1: 'Very Low', 2: 'Low', 3: 'Neutral', 4: 'Good', 5: 'Excellent'}
        
        # Live-compute stress using the dynamic engine
        stress_result = calculate_dynamic_stress(user_email)
        
        # Get check-in count for today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        checkins_today = mood_coll.count_documents({
            'student_id': user_email,
            'timestamp': {'$gte': today_start}
        })
        
        return jsonify({
            'mood': {
                'value': mood_value,
                'trend': mood_trend,
                'label': mood_labels.get(mood_value, 'Neutral')
            },
            'stress': {
                'value': stress_result['score'],
                'trend': stress_result['trend'],
                'label': stress_result['label'],
                'signals': stress_result['signals'],
                'spike_detected': stress_result['spike_detected'],
                'insight': stress_result['insight'],
                'confidence': stress_result.get('confidence', 0),
                'dominant_factor': stress_result.get('dominant_factor', ''),
                'explanation': stress_result.get('explanation', ''),
            },
            'checkins_today': checkins_today,
            'last_checkin': stress_result['updated_at']
        }), 200
        
    except Exception as e:
        print(f"[ERROR] get_current_wellness: {str(e)}")
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/wellness/activities', methods=['GET'])
@login_required
def get_wellness_activities():
    """Return activity summary for the student: today count, week count,
    weekly average stress, and percent change vs previous week.
    """
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401

        db = get_db()
        coll = db['student_wellness']

        now = datetime.utcnow()
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_week = now - timedelta(days=7)
        start_prev_week = now - timedelta(days=14)
        end_prev_week = now - timedelta(days=7)

        # Counts (any wellness entry)
        today_count = coll.count_documents({
            'student_id': user_email,
            'timestamp': {'$gte': start_today}
        })

        week_count = coll.count_documents({
            'student_id': user_email,
            'timestamp': {'$gte': start_week}
        })

        # Weekly average of stress values
        week_stress = list(coll.find({
            'student_id': user_email,
            'data_type': 'stress',
            'timestamp': {'$gte': start_week}
        }))
        weekly_avg_val = int(sum([d.get('value', 0) for d in week_stress]) / len(week_stress)) if week_stress else 0

        prev_week_stress = list(coll.find({
            'student_id': user_email,
            'data_type': 'stress',
            'timestamp': {'$gte': start_prev_week, '$lt': end_prev_week}
        }))
        prev_week_avg_val = int(sum([d.get('value', 0) for d in prev_week_stress]) / len(prev_week_stress)) if prev_week_stress else 0

        # Percent change vs previous week
        if prev_week_avg_val > 0:
            change_ratio = (weekly_avg_val - prev_week_avg_val) / prev_week_avg_val
            pct = int(change_ratio * 100)
            weekly_change = f"+{pct}%" if pct > 0 else f"{pct}%"
        else:
            weekly_change = "0%"

        return jsonify({
            'today': today_count,
            'week': week_count,
            'weekly_average': weekly_avg_val,
            'weekly_change': weekly_change
        }), 200
    except Exception as e:
        print(f"[ERROR] get_wellness_activities: {str(e)}")
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/wellness/checkin', methods=['POST'])
@login_required
@demo_restricted
def submit_wellness_checkin():
    """
    STUDENT-FACING ENDPOINT
    Student submits mood + stress + optional notes.
    TRIGGERS: Hidden signal evaluation (backend-only).
    Student receives: Positive confirmation ONLY.
    """
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json() or {}
        mood = int(data.get('mood', 3))
        stress = int(data.get('stress', 50))
        notes = data.get('notes', '').strip()
        
        # Validation
        if not (1 <= mood <= 5):
            return jsonify({'error': 'Mood must be 1-5'}), 400
        if not (0 <= stress <= 100):
            return jsonify({'error': 'Stress must be 0-100'}), 400
        
        db = get_db()
        
        # Store wellness entries for BOTH mood and stress (separate docs)
        now_ts = datetime.utcnow()
        mood_entry = {
            'student_id': user_email,
            'data_type': 'mood',
            'value': mood,
            'notes': notes,
            'timestamp': now_ts,
            'source': 'student_checkin'
        }
        stress_entry = {
            'student_id': user_email,
            'data_type': 'stress',
            'value': stress,
            'notes': notes,
            'timestamp': now_ts,
            'source': 'student_checkin'
        }
        db['student_wellness'].insert_many([mood_entry, stress_entry])

        # Bridge write: also update moods + stress collections so the
        # stress engine (which reads from moods/stress, not student_wellness) picks this up
        mood_labels = {1: 'very_low', 2: 'low', 3: 'neutral', 4: 'happy', 5: 'excited'}
        db['moods'].insert_one({
            'user_email': user_email,
            'mood': mood_labels.get(mood, 'neutral'),
            'intensity': mood * 2,   # convert 1-5 scale to 2-10 scale
            'source': 'wellness_checkin',
            'created_at': now_ts
        })
        db['stress'].insert_one({
            'user_email': user_email,
            'score': stress,
            'source': 'wellness_checkin',
            'created_at': now_ts
        })
        
        # TRIGGER: Hidden signal pipeline (student never sees this)
        print(f"[SIGNAL PIPELINE] New check-in from {user_email}: mood={mood}, stress={stress}")
        evaluate_risk_signals(user_email, {'mood': mood, 'stress': stress, 'notes': notes})
        
        # RESPONSE: Positive, non-threatening confirmation
        return jsonify({
            'success': True,
            'message': 'Check-in saved. Keep taking care of yourself!',
            'mood': mood,
            'stress': stress
        }), 200
        
    except Exception as e:
        print(f"[ERROR] submit_wellness_checkin: {str(e)}")
        return jsonify({'error': safe_error(e, 'student_api')}), 500


# ==========================================
# SUPPORT CENTER — Urgent Help & Scheduling
# ==========================================

@student_bp.route('/api/support/urgent', methods=['POST'])
@login_required
@demo_restricted
def urgent_support():
    """
    STUDENT-FACING: Immediate crisis help request.
    Creates HIGH-priority incident in proctor queue + support_requests log.
    """
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401

        db = get_db()
        anonymous_id = create_anonymous_student_id(user_email)

        # Log support request
        db['support_requests'].insert_one({
            'student_id': user_email,
            'type': 'urgent',
            'notes': 'Student requested immediate crisis assistance',
            'timestamp': datetime.utcnow(),
            'status': 'pending',
            'priority': 'high'
        })

        # Create HIGH-priority proctor incident
        create_proctor_incident(
            user_email,
            'urgent_help',
            'HIGH',
            'Student pressed Urgent Help — immediate assistance needed'
        )

        print(f"[URGENT HELP] Crisis request from {anonymous_id}")

        return jsonify({
            'success': True,
            'message': 'Help is on the way. A counselor has been notified immediately.'
        }), 200

    except Exception as e:
        print(f"[ERROR] urgent_support: {str(e)}")
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/support/schedule', methods=['POST'])
@login_required
@demo_restricted
def schedule_session():
    """
    STUDENT-FACING: Book a 1-on-1 counseling session.
    Saves session booking to DB and creates a notification for proctor.
    """
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json() or {}
        session_date = data.get('date', '')
        session_time = data.get('time', '')
        session_type = data.get('type', 'general')
        session_notes = data.get('notes', '').strip()

        if not session_date or not session_time:
            return jsonify({'error': 'Date and time are required'}), 400

        db = get_db()
        anonymous_id = create_anonymous_student_id(user_email)

        booking = {
            'student_id': user_email,
            'anonymous_id': anonymous_id,
            'date': session_date,
            'time': session_time,
            'type': session_type,
            'notes': session_notes,
            'status': 'scheduled',
            'created_at': datetime.utcnow()
        }
        result = db['counseling_sessions'].insert_one(booking)

        # Create low-priority notification for proctor
        create_proctor_incident(
            user_email,
            'session_booking',
            'LOW',
            f'Session booked: {session_date} at {session_time} ({session_type})'
        )

        print(f"[SESSION BOOKED] {anonymous_id} → {session_date} {session_time}")

        return jsonify({
            'success': True,
            'message': f'Session booked for {session_date} at {session_time}. You will receive a confirmation.',
            'booking_id': str(result.inserted_id)
        }), 200

    except Exception as e:
        print(f"[ERROR] schedule_session: {str(e)}")
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/support/sessions', methods=['GET'])
@login_required
def get_my_sessions():
    """Get student's upcoming counseling sessions."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401

        db = get_db()
        sessions_list = list(db['counseling_sessions'].find(
            {'student_id': user_email},
            sort=[('created_at', -1)]
        ).limit(10))

        for s in sessions_list:
            s['_id'] = str(s['_id'])

        return jsonify({'success': True, 'sessions': sessions_list}), 200

    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/support/request', methods=['POST'])
@login_required
@demo_restricted
def request_support():
    """
    STUDENT-FACING ENDPOINT
    Student EXPLICITLY requests support (student-initiated, not automatic).
    This creates an IMMEDIATE incident in proctor queue.
    Student receives: Confirmation they will receive help.
    """
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json() or {}
        notes = data.get('notes', '').strip()
        
        db = get_db()
        
        # Store support request (student-initiated bridge)
        support_request = {
            'student_id': user_email,
            'notes': notes,
            'timestamp': datetime.utcnow(),
            'status': 'pending'
        }
        
        db['support_requests'].insert_one(support_request)
        
        # TRIGGER: Create immediate incident (student knows about this)
        anonymous_id = create_anonymous_student_id(user_email)
        print(f"[SUPPORT REQUEST] From {anonymous_id}: {notes}")

        result_id = create_proctor_incident(
            user_email,
            'support_request',
            'MEDIUM',
            notes or 'Student requested support'
        )

        return jsonify({
            'success': True,
            'message': 'Support request sent. A proctor will reach out soon.',
            'incident_id': str(result_id) if result_id else None
        }), 200
        
    except Exception as e:
        print(f"[ERROR] request_support: {str(e)}")
        return jsonify({'error': safe_error(e, 'student_api')}), 500


# ==========================================
# PHASE 4: HIDDEN SIGNAL PIPELINE (Backend-only)
# ==========================================

def evaluate_risk_signals(student_id, wellness_entry):
    """
    HIDDEN FROM STUDENT
    Evaluates three signal types to determine if incident should be created.
    This function runs backend-only - zero exposure to student UI.
    
    Signal Types:
    1. Stress spike: >30 point jump in 48h
    2. Low mood pattern: 3+ consecutive entries with mood ≤2
    3. Distress language: stress ≥85 + keywords in notes
    """
    try:
        db = get_db()
        
        # Signal 1: Stress spike (>30 pts in 48h = HIGH risk)
        stress_spike = check_stress_spike(student_id, wellness_entry.get('stress', 0))
        if stress_spike:
            print(f"[SIGNAL PIPELINE] STRESS SPIKE detected for {student_id}")
            create_proctor_incident(
                student_id,
                'stress_spike',
                'HIGH',
                f"Stress spike detected: {wellness_entry.get('stress', 0)}/100"
            )
        
        # Signal 2: Sustained low mood (3+ entries ≤2 = MEDIUM risk)
        low_mood_pattern = check_low_mood_pattern(student_id)
        if low_mood_pattern:
            print(f"[SIGNAL PIPELINE] LOW MOOD PATTERN detected for {student_id}")
            create_proctor_incident(
                student_id,
                'low_mood_pattern',
                'MEDIUM',
                "Pattern detected: Sustained low mood over 48 hours"
            )
        
        # Signal 3: Distress language (stress ≥85 + keywords = HIGH risk)
        distress_language = check_distress_language(student_id, wellness_entry.get('stress', 0), wellness_entry.get('notes', ''))
        if distress_language:
            print(f"[SIGNAL PIPELINE] DISTRESS LANGUAGE detected for {student_id}")
            create_proctor_incident(
                student_id,
                'distress_language',
                'HIGH',
                "Distress indicators in check-in: High stress + concerning language"
            )

        # Signal 4: Critical stress auto-escalation (stress > 85 = AUTO urgent support)
        current_stress = wellness_entry.get('stress', 0)
        if current_stress > 85:
            auto_escalated = auto_escalate_critical_stress(student_id, current_stress, db)
            if auto_escalated:
                print(f"[SIGNAL PIPELINE] AUTO-ESCALATION triggered for {student_id} (stress={current_stress})")
        
    except Exception as e:
        print(f"[ERROR] evaluate_risk_signals: {str(e)}")


def check_stress_spike(student_id, current_stress):
    """Signal 1: Stress spike (>30 pt jump in 48h)"""
    try:
        db = get_db()
        coll = db['student_wellness']
        
        # Get last stress reading from 48h ago
        two_days_ago = datetime.utcnow() - timedelta(hours=48)
        older_stress = coll.find_one(
            {'student_id': student_id, 'data_type': 'stress', 'timestamp': {'$lt': two_days_ago}},
            sort=[('timestamp', -1)]
        )
        
        if not older_stress:
            return False
        
        delta = current_stress - older_stress.get('value', 0)
        return delta > 30
        
    except Exception as e:
        print(f"[ERROR] check_stress_spike: {str(e)}")
        return False


def check_low_mood_pattern(student_id):
    """Signal 2: Sustained low mood (3+ entries ≤2 in 48h)"""
    try:
        db = get_db()
        coll = db['student_wellness']
        
        two_days_ago = datetime.utcnow() - timedelta(hours=48)
        recent_moods = list(coll.find(
            {'student_id': student_id, 'data_type': 'mood', 'timestamp': {'$gte': two_days_ago}},
            sort=[('timestamp', -1)],
            limit=5
        ))
        
        low_count = sum(1 for m in recent_moods if m.get('value', 3) <= 2)
        return low_count >= 3
        
    except Exception as e:
        print(f"[ERROR] check_low_mood_pattern: {str(e)}")
        return False


def check_distress_language(student_id, stress_level, notes):
    """Signal 3: Distress language (stress ≥85 + keywords)"""
    try:
        if stress_level < 85:
            return False
        
        if not notes:
            return False
        
        # Keyword matching for distress indicators
        distress_keywords = [
            'help', 'crisis', 'desperate', 'hopeless', 'overwhelmed', 'can\'t take',
            'breaking', 'falling apart', 'panic', 'terrified', 'suicidal', 'harm',
            'emergency', 'urgent', 'dying', 'death'
        ]
        
        notes_lower = notes.lower()
        return any(keyword in notes_lower for keyword in distress_keywords)
        
    except Exception as e:
        print(f"[ERROR] check_distress_language: {str(e)}")
        return False


def create_anonymous_student_id(student_email):
    """
    Convert student email to anonymous ID — delegates to centralized helper.
    Format: STU_{hash:05d}
    """
    return create_anonymous_id(student_email)


def auto_escalate_critical_stress(student_id, stress_value, db):
    """
    Signal 4: AUTO-ESCALATION for critical stress (> 85).
    Creates an urgent support ticket + HIGH proctor incident automatically.
    
    Cooldown: Will NOT re-trigger if an auto-escalation was created within the
    last 6 hours for the same student — prevents alert spam.
    
    This is the bridge between the stress engine and the support center.
    The student does NOT see this happen — it's purely backend.
    """
    try:
        anonymous_id = create_anonymous_student_id(student_id)

        # ── Cooldown check: skip if escalated within last 6 hours ──
        six_hours_ago = datetime.utcnow() - timedelta(hours=6)
        recent_escalation = db['support_requests'].find_one({
            'student_id': student_id,
            'type': 'auto_urgent',
            'timestamp': {'$gte': six_hours_ago}
        })
        if recent_escalation:
            print(f"[AUTO-ESCALATION] Cooldown active for {anonymous_id}, skipping (last: {recent_escalation['timestamp']})")
            return False

        # ── 1. Create urgent support ticket (visible to proctor) ──
        db['support_requests'].insert_one({
            'student_id': student_id,
            'type': 'auto_urgent',
            'notes': f'SYSTEM AUTO-ESCALATION: Stress level {stress_value}/100 exceeded critical threshold (85). Immediate wellness check recommended.',
            'timestamp': datetime.utcnow(),
            'status': 'pending',
            'priority': 'high',
            'auto_triggered': True,
            'stress_value': stress_value
        })

        # ── 2. Create HIGH proctor incident ──
        incident_id = str(uuid.uuid4())
        db['risk_incidents'].insert_one({
            'incident_id': incident_id,
            'anonymous_student_id': anonymous_id,
            'student_email': None,
            'incident_type': 'critical_stress_auto',
            'risk_level': 'HIGH',
            'priority': 'HIGH',
            'trigger_source': 'stress_engine_auto_escalation',
            'timestamp': datetime.utcnow(),
            'status': 'UNREVIEWED',
            'details': f'Stress engine auto-escalation: Student stress at {stress_value}/100 (threshold: 85). No manual request — system detected critical level.',
            'message_excerpt': f'AUTO: Stress {stress_value}/100 — critical threshold exceeded',
            'action_count': 0,
            'last_action': None,
            'audit_trail': [],
            'resolved_by': None,
            'resolved_at': None,
            'auto_triggered': True
        })

        print(f"[AUTO-ESCALATION] Created urgent ticket + incident for {anonymous_id} | stress={stress_value}")

        # ── 3. Push real-time alert to proctor dashboard ──
        try:
            from app import emit_proctor_alert
            emit_proctor_alert({
                'type': 'critical_auto_escalation',
                'risk_level': 'HIGH',
                'anonymous_student_id': anonymous_id,
                'incident_id': incident_id,
                'message': f'AUTO-ESCALATION: Stress {stress_value}/100 exceeded critical threshold',
                'stress_value': stress_value,
                'timestamp': datetime.utcnow().isoformat(),
            })
        except Exception as se:
            print(f"[SOCKET] Proctor alert emit failed: {se}")

        return True

    except Exception as e:
        print(f"[ERROR] auto_escalate_critical_stress: {str(e)}")
        return False


def create_proctor_incident(student_id, trigger_type, priority, details):
    """
    HIDDEN FROM STUDENT
    Creates anonymous incident in proctor queue.
    Student identity is never exposed - only anonymous ID is used.
    """
    try:
        db = get_db()
        
        anonymous_id = create_anonymous_student_id(student_id)
        incident_id = str(uuid.uuid4())
        
        incident = {
            'incident_id': incident_id,
            'anonymous_student_id': anonymous_id,
            'student_email': None,  # Never store real identity
            'incident_type': trigger_type,
            'risk_level': priority,  # Proctor expects 'risk_level' field
            'priority': priority,
            'trigger_source': f'signal_pipeline_{trigger_type}',
            'timestamp': datetime.utcnow(),
            'status': 'UNREVIEWED',  # Proctor expects 'UNREVIEWED' status
            'details': details,
            'message_excerpt': details[:200],
            'action_count': 0,
            'last_action': None,
            'audit_trail': [],
            'resolved_by': None,
            'resolved_at': None
        }
        
        result = db['risk_incidents'].insert_one(incident)
        
        print(f"[SIGNAL PIPELINE] Created {priority} incident | ID: {incident_id} | Type: {trigger_type} | Student: {anonymous_id}")
        
        return result.inserted_id
        
    except Exception as e:
        print(f"[ERROR] create_proctor_incident: {str(e)}")
        return None


# ==========================================
# 2. API ROUTES (Data)
# ==========================================

@student_bp.route('/api/mood/today', methods=['GET'])
@login_required
def mood_today():
    """Check if user has set mood today"""
    try:
        user_email = session.get('user_email')
        db = get_db()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        latest_mood = db[MoodModel.collection_name].find_one(
            {'user_email': user_email, 'created_at': {'$gte': today_start}},
            sort=[('created_at', -1)]
        )
        
        if latest_mood:
            return jsonify({
                'has_mood_today': True,
                'mood': latest_mood.get('mood', 'calm')
            })
        else:
            return jsonify({'has_mood_today': False})
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/mood', methods=['POST'])
@login_required
@demo_restricted
def update_mood():
    """Update user's mood and trigger stress recalculation."""
    try:
        user_email = session.get('user_email')
        data = request.get_json() or {}
        mood = data.get('mood', 'calm').lower()
        
        db = get_db()
        db[MoodModel.collection_name].insert_one({
            'user_email': user_email,
            'mood': mood,
            'created_at': datetime.utcnow()
        })
        
        # Recalculate stress since mood is a primary signal
        stress_result = calculate_dynamic_stress(user_email)
        
        return jsonify({
            'success': True,
            'mood': mood,
            'stress': {
                'value': stress_result['score'],
                'label': stress_result['label'],
                'trend': stress_result['trend'],
                'insight': stress_result['insight'],
            }
        })
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/student/profile', methods=['GET'])
@login_required
def get_student_profile():
    """Get student profile information"""
    try:
        return jsonify({
            'name': session.get('user_name', 'Student'),
            'email': session.get('user_email', 'student@example.com'),
            'roll_number': session.get('user_roll', 'N/A'),
            'role': session.get('user_role', 'student')
        })
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/student/change-password', methods=['POST'])
@login_required
@demo_restricted
def change_password():
    """Allow a logged-in student to update their password."""
    try:
        from utils.auth_helpers import verify_password, hash_password
        data = request.get_json() or {}
        current_pw = data.get('current_password', '')
        new_pw = data.get('new_password', '')

        if not current_pw or not new_pw:
            return jsonify({'success': False, 'error': 'Both current and new password are required.'}), 400
        if len(new_pw) < 6:
            return jsonify({'success': False, 'error': 'New password must be at least 6 characters.'}), 400

        db = get_db()
        user_email = session.get('user_email')
        user = db['users'].find_one({'email': user_email})
        if not user:
            return jsonify({'success': False, 'error': 'User not found.'}), 404

        if not verify_password(user['hashed_password'], current_pw):
            return jsonify({'success': False, 'error': 'Current password is incorrect.'}), 403

        db['users'].update_one(
            {'email': user_email},
            {'$set': {'hashed_password': hash_password(new_pw)}}
        )
        return jsonify({'success': True, 'message': 'Password updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': safe_error(e, 'change_password')}), 500


@student_bp.route('/api/activities/count', methods=['GET'])
@login_required
def activities_count():
    """Get count of user activities"""
    try:
        user_email = session.get('user_email')
        db = get_db()
        
        # Count total activities (stress checks, mood checks, etc.)
        stress_count = db[StressModel.collection_name].count_documents({'user_email': user_email})
        mood_count = db[MoodModel.collection_name].count_documents({'user_email': user_email})
        
        total_count = stress_count + mood_count
        
        return jsonify({'count': total_count})
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/journal', methods=['POST'])
@login_required
@demo_restricted
def save_journal():
    """Save a daily reflection journal entry."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json() or {}
        entry = (data.get('entry') or '').strip()

        if not entry:
            return jsonify({'error': 'Entry cannot be empty'}), 400

        db = get_db()
        today = datetime.utcnow().strftime('%Y-%m-%d')

        # Upsert: one journal entry per day
        db['student_journals'].update_one(
            {'student_id': user_email, 'date': today},
            {'$set': {
                'student_id': user_email,
                'date': today,
                'entry': entry[:2000],
                'updated_at': datetime.utcnow()
            }},
            upsert=True
        )

        return jsonify({'success': True, 'message': 'Journal saved!'})
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/journal/today', methods=['GET'])
@login_required
def get_journal_today():
    """Get today's journal entry."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401

        db = get_db()
        today = datetime.utcnow().strftime('%Y-%m-%d')

        entry = db['student_journals'].find_one(
            {'student_id': user_email, 'date': today}
        )

        if entry:
            return jsonify({
                'has_entry': True,
                'entry': entry.get('entry', ''),
                'date': today
            })
        return jsonify({'has_entry': False, 'date': today})
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/wellness/goals', methods=['GET'])
@login_required
def get_wellness_goals():
    """Get wellness goal completion status for today."""
    try:
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not authenticated'}), 401

        db = get_db()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Check daily check-in completion
        has_checkin = db['student_wellness'].count_documents({
            'student_id': user_email,
            'timestamp': {'$gte': today_start}
        }) > 0 or db[MoodModel.collection_name].count_documents({
            'user_email': user_email,
            'created_at': {'$gte': today_start}
        }) > 0

        # Check breathing/exercise
        has_breathing = db[StressModel.collection_name].count_documents({
            'user_email': user_email,
            'source': {'$regex': 'breathing|stretch|wind_down'},
            'created_at': {'$gte': today_start}
        }) > 0

        return jsonify({
            'checkin': has_checkin,
            'breathing': has_breathing,
            'study': False,
            'relax': False,
        })
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/stress/today', methods=['GET'])
@login_required
def stress_today():
    """Get today's stress — computed live from all signals."""
    try:
        user_email = session.get('user_email')
        result = calculate_dynamic_stress(user_email)
        return jsonify({
            'score': result['score'],
            'label': result['label'],
            'trend': result['trend'],
            'insight': result['insight'],
            'spike_detected': result['spike_detected'],
            'signals': result['signals'],
            'confidence': result.get('confidence', 0),
            'dominant_factor': result.get('dominant_factor', ''),
            'explanation': result.get('explanation', ''),
            'updated_at': result['updated_at'],
        })
    except Exception as e:
        print(f'[ERROR] stress_today: {e}')
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/student/stress-level', methods=['GET'])
@login_required
def get_stress_level():
    """Get current stress level — computed live with weekly stats."""
    try:
        user_email = session.get('user_email')
        result = calculate_dynamic_stress(user_email)
        stats = get_weekly_stats(user_email)
        
        return jsonify({
            'stress_level': result['score'],
            'label': result['label'],
            'peak': stats['peak'],
            'average': stats['average'],
            'low': stats['low'],
            'trend': result['trend'],
            'signals': result['signals'],
            'spike_detected': result['spike_detected'],
            'insight': result['insight'],
            'confidence': result.get('confidence', 0),
            'dominant_factor': result.get('dominant_factor', ''),
            'explanation': result.get('explanation', ''),
            'weekly_change': stats['change_pct'],
            'weekly_direction': stats['change_direction'],
            'readings_count': stats['readings_count'],
            'updated_at': result['updated_at'],
        })
    except Exception as e:
        print(f'[ERROR] get_stress_level: {e}')
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/student/dashboard-data', methods=['GET'])
@login_required
def get_dashboard_data():
    """Get comprehensive dashboard data for Pro Dashboard"""
    try:
        user_email = session.get('user_email')
        db = get_db()
        
        # Get latest mood
        mood_coll = db[MoodModel.collection_name]
        latest_mood = mood_coll.find_one(
            {'user_email': user_email},
            sort=[('created_at', -1)]
        )
        mood = latest_mood.get('mood', 'Calm') if latest_mood else 'Calm'
        
        # Calculate wellness streak
        stress_coll = db[StressModel.collection_name]
        streak = calculate_wellness_streak(user_email, stress_coll)
        
        # Get activities count
        activities_count = stress_coll.count_documents({'user_email': user_email})
        
        # Generate AI insight based on recent data
        ai_insight = generate_ai_insight(user_email, stress_coll, mood)
        
        return jsonify({
            'mood': mood.capitalize(),
            'ai_insight': ai_insight,
            'streak': streak,
            'activities_count': activities_count
        })
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


def calculate_wellness_streak(user_email, stress_coll):
    """Calculate consecutive days with wellness activity"""
    try:
        # Get distinct days with stress records
        pipeline = [
            {'$match': {'user_email': user_email}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}}
            }},
            {'$sort': {'_id': -1}},
            {'$limit': 30}
        ]
        
        days = [r['_id'] for r in stress_coll.aggregate(pipeline)]
        
        if not days:
            return 0
        
        # Count consecutive days from today
        streak = 1
        
        for i in range(len(days) - 1):
            current_date = datetime.strptime(days[i], '%Y-%m-%d').date()
            next_date = datetime.strptime(days[i + 1], '%Y-%m-%d').date()
            
            if (current_date - next_date).days == 1:
                streak += 1
            else:
                break
        
        return streak
    except:
        return 1


def generate_ai_insight(user_email, stress_coll, mood):
    """Generate simple AI insight based on recent patterns"""
    try:
        # Get last 7 days average
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_readings = list(stress_coll.find({
            'user_email': user_email,
            'created_at': {'$gte': week_ago}
        }))
        
        if not recent_readings:
            return 'Getting Started'
        
        avg_stress = sum([r.get('score', 50) for r in recent_readings]) / len(recent_readings)
        
        if avg_stress < 30:
            return 'Excellent'
        elif avg_stress < 50:
            return 'Positive'
        elif avg_stress < 70:
            return 'Moderate'
        else:
            return 'Needs Attention'
    except Exception:
        return 'Positive'


@student_bp.route('/api/grievance', methods=['POST'])
@login_required
@demo_restricted
def submit_grievance():
    """Submit a student grievance to the proctor queue."""
    try:
        user_email = session.get('user_email')
        data = request.get_json(force=True) or {}
        subject = (data.get('subject') or '').strip()
        description = (data.get('description') or '').strip()

        if not subject or not description:
            return jsonify({'error': 'Subject and description are required'}), 400

        db = get_db()
        db[GrievanceModel.collection_name].insert_one({
            'user_email': user_email,
            'subject': subject[:200],
            'description': description[:2000],
            'status': 'pending',
            'created_at': datetime.utcnow(),
        })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/stress_history', methods=['GET'])
@login_required
def stress_history():
    """Return stress history for the logged-in user, bucketed by day."""
    try:
        user_email = session.get('user_email')
        days = int(request.args.get('days', 7))
        days = max(1, min(90, days))  # Clamp 1-90
        
        history = fetch_stress_history(user_email, days)
        
        # Also include weekly stats for context
        stats = get_weekly_stats(user_email)

        return jsonify({
            'history': history,
            'stats': stats,
        })
    except Exception as e:
        print(f'[ERROR] stress_history: {e}')
        return jsonify({'error': safe_error(e, 'student_api')}), 500


@student_bp.route('/api/quick_actions', methods=['POST'])
@login_required
@demo_restricted
def quick_actions():
    """Handle quick actions like breathing, mood_check, stretch.
    Logs the action and returns appropriate message with stress reduction.
    """
    try:
        data = request.get_json() or {}
        action = (data.get('action') or '').lower()
        messages = {
            'breathing': 'Great! Try a 1-minute box breathing now. In 4, hold 4, out 4.',
            'mood_check': 'Mood check logged. Remember to be kind to yourself!',
            'stretch': 'Stand up, roll your shoulders, and stretch for 30 seconds.',
            'energy_boost': 'Time for an energy boost! Do 10 jumping jacks or walk around.',
            'morning_motivation': 'Start your day with intention and positivity!',
            'sleep_hygiene': 'Wind down: no screens 30 min before bed, keep it cool and dark.',
            'wind_down': 'Time to relax. Deep breathing and gentle stretches help.',
        }
        msg = messages.get(action, 'Action noted. Keep going!')

        # Log action and reduce stress score
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'Not logged in'}), 401
            
        db = get_db()
        coll = db[StressModel.collection_name]
        
        # Get current stress and reduce it based on action effectiveness
        current_stress = list(coll.find({'user_email': user_email}).sort('created_at', -1).limit(1))
        base_stress = current_stress[0]['score'] if current_stress else 50
        
        # Different actions reduce stress by different amounts
        stress_reduction = {
            'breathing': 8,
            'mood_check': 3,
            'stretch': 5,
            'energy_boost': 7,
            'morning_motivation': 4,
            'sleep_hygiene': 6,
            'wind_down': 10,
        }
        
        reduction = stress_reduction.get(action, 3)
        new_stress = max(0, base_stress - reduction)
        
        coll.insert_one({
            'user_email': user_email,
            'score': new_stress,
            'source': f'quick_action:{action}',
            'created_at': datetime.utcnow(),
        })

        # Derive label from the new score
        if new_stress <= 25:   ql = 'Relaxed'
        elif new_stress <= 45: ql = 'Manageable'
        elif new_stress <= 65: ql = 'Elevated'
        elif new_stress <= 80: ql = 'High'
        else:                  ql = 'Critical'

        # Build insight based on action
        action_insights = {
            'breathing': 'Deep breathing activates your parasympathetic nervous system, reducing stress hormones.',
            'stretch': 'Physical movement releases tension and boosts endorphins.',
            'hydration': 'Staying hydrated supports cognitive function and reduces fatigue.',
            'walk': 'A short walk improves circulation and clears mental fog.',
            'music': 'Music therapy can lower cortisol levels and improve mood.',
            'journaling': 'Writing helps process emotions and gain perspective.',
        }

        return jsonify({
            'message': msg,
            'stress_score': new_stress,
            'label': ql,
            'trend': 'down' if reduction > 0 else 'stable',
            'insight': action_insights.get(action, 'Taking a break helps your body and mind recover.'),
        })
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


# ==========================================
# CONNECTION HUB - TOPIC-BASED CHAT ROOMS
# ==========================================

# Predefined rooms
PREDEFINED_ROOMS = [
    {'_id': 'campus_life', 'title': 'Campus Life'},
    {'_id': 'exam_stress', 'title': 'Exam Stress'},
    {'_id': 'placements', 'title': 'Placements & Internships'},
    {'_id': 'tech_projects', 'title': 'Tech & Projects'},
    {'_id': 'random_talk', 'title': 'Random Talk'},
    {'_id': 'late_night', 'title': 'Late Night Chat'},
]

# Profanity filter — delegates to shared utility in utils.helpers
def contains_profanity(message):
    return contains_blocked_content(message)

def rate_limit_check(user_id):
    """Check if user can send message (1 per 3 seconds)"""
    try:
        db = get_db()
        coll = db['message_timestamps']
        
        user_last_msg = coll.find_one({'user_id': user_id}, sort=[('timestamp', -1)])
        if not user_last_msg:
            return True
        
        time_diff = datetime.utcnow() - user_last_msg['timestamp']
        if time_diff.total_seconds() < 3:
            return False
        return True
    except:
        return True

@student_bp.route('/api/connection/rooms', methods=['GET'])
@login_required
def get_connection_rooms():
    """Get all available connection hub rooms"""
    try:
        return jsonify({
            'rooms': PREDEFINED_ROOMS,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500

@student_bp.route('/api/connection/rooms/<room_id>/messages', methods=['GET'])
@login_required
def get_room_messages(room_id):
    """Get messages from a specific room (last 50 messages)"""
    try:
        db = get_db()
        coll = db['room_messages']
        
        messages = list(coll.find(
            {'room_id': room_id}
        ).sort('created_at', -1).limit(50))
        
        # Reverse to get chronological order
        messages.reverse()
        
        # Format for response
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'id': str(msg.get('_id', '')),
                'display_name': msg.get('display_name', 'Anonymous Student'),
                'message': msg.get('message', ''),
                'timestamp': msg.get('created_at', '').isoformat() if msg.get('created_at') else '',
            })
        
        return jsonify({
            'messages': formatted_messages,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500

@student_bp.route('/api/connection/rooms/<room_id>/send', methods=['POST'])
@login_required
@demo_restricted
def send_room_message(room_id):
    """Send a message to a room"""
    try:
        user_id = session.get('user_email', 'unknown')
        message_text = request.json.get('message', '').strip()
        
        # Validation
        if not message_text:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        if len(message_text) > 500:
            return jsonify({'error': 'Message too long (max 500 chars)'}), 400
        
        # Rate limit check
        if not rate_limit_check(user_id):
            return jsonify({'error': 'Please wait before sending another message'}), 429
        
        # Profanity check
        if contains_profanity(message_text):
            return jsonify({'error': 'Message contains inappropriate content'}), 400
        
        # Insert message
        db = get_db()
        coll = db['room_messages']
        
        coll.insert_one({
            'room_id': room_id,
            'user_id': user_id,
            'display_name': 'Anonymous Student',
            'message': message_text,
            'created_at': datetime.utcnow(),
        })
        
        # Update rate limit timestamp
        ts_coll = db['message_timestamps']
        ts_coll.update_one(
            {'user_id': user_id},
            {'$set': {'timestamp': datetime.utcnow()}},
            upsert=True
        )
        
        return jsonify({
            'message': 'Message sent successfully',
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


# ==========================================
# CONNECTION HUB - MODERATION: Report Message
# ==========================================

@student_bp.route('/api/connection/messages/<message_id>/report', methods=['POST'])
@login_required
@demo_restricted
def report_message(message_id):
    """Report a message for proctor review"""
    try:
        user_email = session.get('user_email')
        db = get_db()
        
        # Validate message_id format
        try:
            obj_id = ObjectId(message_id)
        except:
            return jsonify({'error': 'Invalid message ID'}), 400
        
        # Mark message as reported
        result = db['room_messages'].update_one(
            {'_id': obj_id},
            {'$set': {
                'reported': True,
                'reported_by': user_email,
                'report_time': datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            return jsonify({
                'status': 'success',
                'message': 'Message reported to proctors.'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Message not found.'
            }), 404
    except Exception as e:
        return jsonify({'error': safe_error(e, 'student_api')}), 500


# ==========================================
# ACADEMIC PERFORMANCE — Student-facing
# ==========================================

def _seed_demo_academics(db, roll_number):
    """Seed sample academic data for demo student if none exists."""
    if db['academic_records'].count_documents({'student_roll': roll_number}) > 0:
        return  # already seeded

    semesters = [
        {'semester': 'Sem 1', 'sgpa': 8.2, 'cgpa': 8.2, 'attendance': 88, 'backlogs': 0, 'credits_earned': 22, 'total_credits': 22},
        {'semester': 'Sem 2', 'sgpa': 7.8, 'cgpa': 8.0, 'attendance': 82, 'backlogs': 0, 'credits_earned': 24, 'total_credits': 24},
        {'semester': 'Sem 3', 'sgpa': 8.5, 'cgpa': 8.17, 'attendance': 90, 'backlogs': 0, 'credits_earned': 22, 'total_credits': 22},
        {'semester': 'Sem 4', 'sgpa': 7.4, 'cgpa': 7.98, 'attendance': 76, 'backlogs': 1, 'credits_earned': 20, 'total_credits': 22},
        {'semester': 'Sem 5', 'sgpa': 8.8, 'cgpa': 8.14, 'attendance': 92, 'backlogs': 0, 'credits_earned': 24, 'total_credits': 24},
        {'semester': 'Sem 6', 'sgpa': 8.1, 'cgpa': 8.13, 'attendance': 85, 'backlogs': 0, 'credits_earned': 22, 'total_credits': 22},
    ]
    for s in semesters:
        s['student_roll'] = roll_number
    db['academic_records'].insert_many(semesters)

    # Subject-wise marks for latest semester
    subjects = [
        {'subject': 'Machine Learning',      'code': 'CS601', 'internal': 38, 'external': 52, 'total': 90, 'grade': 'O',  'credits': 4},
        {'subject': 'Computer Networks',     'code': 'CS602', 'internal': 32, 'external': 40, 'total': 72, 'grade': 'A',  'credits': 4},
        {'subject': 'Cloud Computing',       'code': 'CS603', 'internal': 36, 'external': 48, 'total': 84, 'grade': 'A+', 'credits': 3},
        {'subject': 'Software Engineering',  'code': 'CS604', 'internal': 28, 'external': 38, 'total': 66, 'grade': 'B+', 'credits': 3},
        {'subject': 'Data Analytics Lab',    'code': 'CS605', 'internal': 40, 'external': 45, 'total': 85, 'grade': 'A+', 'credits': 4},
        {'subject': 'Mini Project',          'code': 'CS606', 'internal': 42, 'external': 50, 'total': 92, 'grade': 'O',  'credits': 4},
    ]
    for sub in subjects:
        sub['student_roll'] = roll_number
        sub['semester'] = 'Sem 6'
    db['academic_subjects'].insert_many(subjects)


@student_bp.route('/api/student/academics', methods=['GET'])
@login_required
def get_my_academics():
    """
    STUDENT-FACING
    Returns academic records (semester-wise CGPA/SGPA/attendance/backlogs)
    and subject-wise marks for the latest semester.
    Seeds sample data for demo accounts if none exists.
    """
    try:
        db = get_db()
        user_email = session.get('user_email', '')
        roll_number = session.get('user_roll', '')

        if not roll_number:
            # Fallback: try to find roll from users collection
            user = db['users'].find_one({'email': user_email})
            roll_number = user.get('roll_number', '') if user else ''

        if not roll_number:
            return jsonify({
                'success': True,
                'data': {'records': [], 'subjects': [], 'summary': {}},
                'message': 'No roll number found'
            })

        # Seed demo data if needed
        if is_demo_account():
            _seed_demo_academics(db, roll_number)

        # Fetch semester records
        records = list(db['academic_records'].find(
            {'student_roll': roll_number}
        ).sort('semester', 1))

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

        # Fetch subject-wise marks for latest semester
        latest_sem = records[-1].get('semester', '') if records else ''
        subjects = list(db['academic_subjects'].find(
            {'student_roll': roll_number, 'semester': latest_sem}
        ))
        formatted_subjects = []
        for s in subjects:
            formatted_subjects.append({
                'subject': s.get('subject', ''),
                'code': s.get('code', ''),
                'internal': s.get('internal', 0),
                'external': s.get('external', 0),
                'total': s.get('total', 0),
                'grade': s.get('grade', ''),
                'credits': s.get('credits', 0),
            })

        # Calculate summary
        total_credits_earned = sum(r.get('credits_earned', 0) for r in records)
        total_credits_available = sum(r.get('total_credits', 0) for r in records)
        current_cgpa = records[-1].get('cgpa', 0) if records else 0
        current_sgpa = records[-1].get('sgpa', 0) if records else 0
        avg_attendance = round(sum(r.get('attendance', 0) for r in records) / max(len(records), 1), 1)
        total_backlogs = sum(r.get('backlogs', 0) for r in records)

        summary = {
            'current_cgpa': current_cgpa,
            'current_sgpa': current_sgpa,
            'current_semester': latest_sem,
            'total_credits': f'{total_credits_earned}/{total_credits_available}',
            'avg_attendance': avg_attendance,
            'total_backlogs': total_backlogs,
            'total_semesters': len(records),
        }

        return jsonify({
            'success': True,
            'data': {
                'records': formatted_records,
                'subjects': formatted_subjects,
                'summary': summary,
            }
        })

    except Exception as e:
        print(f'[ERROR] get_my_academics: {e}')
        return jsonify({'error': safe_error(e, 'student_api')}), 500