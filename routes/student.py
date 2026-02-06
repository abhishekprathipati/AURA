from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_helpers import login_required
from utils.database import get_db
from models.mood import MoodModel
from models.stress import StressModel
from models.grievance import GrievanceModel
from datetime import datetime, timedelta
from bson import ObjectId
from collections import OrderedDict
import hashlib
import uuid

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
    return render_template('mental_chatbot.html', show_nav=True)

@student_bp.route('/chat/study')
@login_required
def study_chatbot():
    return render_template('study_chatbot.html', show_nav=True)

@student_bp.route('/relax')
@login_required
def relax():
    return render_template('relax.html', show_nav=True)

@student_bp.route('/activities')
@login_required
def activities():
    return render_template('activities.html', show_nav=True)

@student_bp.route('/games')
@login_required
def games():
    return render_template('games.html', show_nav=True)

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
    Returns personal wellness data WITHOUT any risk classification.
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
        
        # Get latest stress entry
        stress_coll = db['student_wellness']
        latest_stress = stress_coll.find_one(
            {'student_id': user_email, 'data_type': 'stress'},
            sort=[('timestamp', -1)]
        )
        
        stress_value = latest_stress.get('value', 50) if latest_stress else 50
        stress_trend = 'stable'
        
        # Neutral stress labels (no alarm language)
        stress_labels = {
            (0, 30): 'Relaxed',
            (31, 50): 'Manageable',
            (51, 70): 'Elevated',
            (71, 100): 'High'
        }
        stress_label = next((v for (k, l), v in stress_labels.items() if k <= stress_value <= l), 'Manageable')
        
        # Get check-in count for today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        checkins_today = stress_coll.count_documents({
            'student_id': user_email,
            'timestamp': {'$gte': today_start}
        })
        
        return jsonify({
            'mood': {
                'value': mood_value,
                'trend': mood_trend,
                'label': mood_labels.get(mood_value, 'Neutral')  # NO RISK LABELS
            },
            'stress': {
                'value': stress_value,
                'trend': stress_trend,
                'label': stress_label  # NO RISK LABELS
            },
            'checkins_today': checkins_today,
            'last_checkin': latest_stress.get('timestamp', '').isoformat() if latest_stress else None
        }), 200
        
    except Exception as e:
        print(f"[ERROR] get_current_wellness: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


@student_bp.route('/api/wellness/checkin', methods=['POST'])
@login_required
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
        return jsonify({'error': str(e)}), 500


@student_bp.route('/api/support/request', methods=['POST'])
@login_required
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
        incident_id = str(uuid.uuid4())
        print(f"[SUPPORT REQUEST] From {anonymous_id}: {notes}")
        
        incident = {
            'incident_id': incident_id,
            'anonymous_student_id': anonymous_id,
            'student_email': None,  # Never store real identity
            'incident_type': 'support_request',
            'risk_level': 'MEDIUM',  # Proctor expects 'risk_level' field
            'priority': 'MEDIUM',
            'trigger_source': 'student_support_request',
            'timestamp': datetime.utcnow(),
            'status': 'UNREVIEWED',  # Proctor expects 'UNREVIEWED' status
            'details': notes,
            'message_excerpt': notes[:200],
            'action_count': 0,
            'last_action': None,
            'audit_trail': [],
            'resolved_by': None,
            'resolved_at': None
        }
        
        result = db['risk_incidents'].insert_one(incident)
        
        return jsonify({
            'success': True,
            'message': 'Support request sent. A proctor will reach out soon.',
            'incident_id': str(result.inserted_id)
        }), 200
        
    except Exception as e:
        print(f"[ERROR] request_support: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
    Convert student email to anonymous ID.
    Format: STU_{hash:05d}
    Example: STU_34821
    """
    hash_value = int(hashlib.md5(student_email.encode()).hexdigest(), 16) % 100000
    return f"STU_{hash_value:05d}"


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
        return jsonify({'error': str(e)}), 500


@student_bp.route('/api/mood', methods=['POST'])
@login_required
def update_mood():
    """Update user's mood"""
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
        
        return jsonify({'success': True, 'mood': mood})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


@student_bp.route('/api/stress/today', methods=['GET'])
@login_required
def stress_today():
    try:
        user_email = session.get('user_email')
        db = get_db()
        since = datetime.utcnow() - timedelta(hours=24)
        latest = db[StressModel.collection_name].find_one(
            {'user_email': user_email, 'created_at': {'$gte': since}}, 
            sort=[('created_at', -1)]
        )
        score = latest.get('score', 50) if latest else 50
        return jsonify({'score': score})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@student_bp.route('/api/student/stress-level', methods=['GET'])
@login_required
def get_stress_level():
    """Get current stress level with additional metrics for Pro Dashboard"""
    try:
        user_email = session.get('user_email')
        db = get_db()
        coll = db[StressModel.collection_name]
        
        # Get latest stress level
        latest = coll.find_one(
            {'user_email': user_email}, 
            sort=[('created_at', -1)]
        )
        current_stress = latest.get('score', 50) if latest else 50
        
        # Get today's readings for peak and average
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_readings = list(coll.find({
            'user_email': user_email,
            'created_at': {'$gte': today_start}
        }))
        
        peak = max([r['score'] for r in today_readings]) if today_readings else current_stress
        average = int(sum([r['score'] for r in today_readings]) / len(today_readings)) if today_readings else current_stress
        
        # Calculate trend (compare last 2 readings)
        recent = list(coll.find({'user_email': user_email}).sort('created_at', -1).limit(2))
        trend = 'stable'
        if len(recent) == 2:
            diff = recent[0]['score'] - recent[1]['score']
            if diff > 5:
                trend = 'up'
            elif diff < -5:
                trend = 'down'
        
        return jsonify({
            'stress_level': current_stress,
            'peak': peak,
            'average': average,
            'trend': trend
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        today = datetime.utcnow().date()
        
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
        
        avg_stress = sum([r['score'] for r in recent_readings]) / len(recent_readings)
        
        if avg_stress < 30:
            return 'Excellent'
        elif avg_stress < 50:
            return 'Positive'
        elif avg_stress < 70:
            return 'Moderate'
        else:
            return 'Needs Attention'
    except:
        return 'Positive'


@student_bp.route('/api/grievance', methods=['POST'])
@login_required
def submit_grievance():
    # Simple endpoint to prevent 404s on the dashboard
    try:
        # Simple endpoint to prevent 404s on the dashboard
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@student_bp.route('/api/stress_history', methods=['GET'])
@login_required
def stress_history():
    """Return last 7 days stress history for the logged-in user, bucketed by day."""
    try:
        user_email = session.get('user_email')
        db = get_db()
        coll = db[StressModel.collection_name]
        since = datetime.utcnow() - timedelta(days=7)

        # Fetch all stress entries from last 7 days
        cursor = coll.find(
            {'user_email': user_email, 'created_at': {'$gte': since}},
            {'_id': 0, 'created_at': 1, 'score': 1}
        ).sort('created_at', 1)
        
        raw_history = []
        for doc in cursor:
            raw_history.append({
                'timestamp': doc['created_at'].isoformat() + 'Z',
                'score': int(doc.get('score', 50))
            })
        
        # Bucket by day - keep latest entry per day
        bucketed = bucket_by_day(raw_history)

        return jsonify({'history': bucketed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@student_bp.route('/api/quick_actions', methods=['POST'])
@login_required
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

        return jsonify({'message': msg, 'stress_score': new_stress})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

# Basic profanity filter
BLOCKED_WORDS = [
    'abuse', 'hate', 'spam', 'inappropriate', 'offensive',
    'harassment', 'violence', 'threat', 'kill', 'harm'
]

def contains_profanity(message):
    """Check if message contains blocked words"""
    message_lower = message.lower()
    for word in BLOCKED_WORDS:
        if word in message_lower:
            return True
    return False

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
        return jsonify({'error': str(e)}), 500

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
        return jsonify({'error': str(e)}), 500

@student_bp.route('/api/connection/rooms/<room_id>/send', methods=['POST'])
@login_required
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
        return jsonify({'error': str(e)}), 500


# ==========================================
# CONNECTION HUB - MODERATION: Report Message
# ==========================================

@student_bp.route('/api/connection/messages/<message_id>/report', methods=['POST'])
@login_required
def report_message(message_id):
    """Report a message for proctor review"""
    try:
        user_id = session.get('user_id')
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
                'reported_by': user_id,
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
        return jsonify({'error': str(e)}), 500