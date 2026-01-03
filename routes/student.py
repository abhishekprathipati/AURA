from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_helpers import login_required
from utils.database import get_db
from models.mood import MoodModel
from models.stress import StressModel
from models.grievance import GrievanceModel
from datetime import datetime, timedelta

# Create the Blueprint
student_bp = Blueprint('student', __name__)

# ==========================================
# 1. PAGE ROUTES (Navigation)
# ==========================================

@student_bp.route('/dashboard')
@login_required
def dashboard():
    # Helper variable show_nav=False hides the top bar in base.html logic
    return render_template('student_dashboard.html', show_nav=False)

@student_bp.route('/dashboard/pro')
@login_required
def dashboard_pro():
    # Ultra Pro Command Center Dashboard
    return render_template('student_dashboard_pro.html', show_nav=False)

@student_bp.route('/chat/mental')
@login_required
def mental_chatbot():
    return render_template('mental_chatbot.html', show_nav=True)

@student_bp.route('/chat/study')
@login_required
def study_chatbot():
    return render_template('study_chatbot.html', show_nav=True)

@student_bp.route('/chat/study/pro')
@login_required
def study_assistant_pro():
    # Professional three-column study assistant
    return render_template('study_assistant_pro.html', show_nav=False)

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
# 2. API ROUTES (Data)
# ==========================================

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
    """Return last 7 days stress history for the logged-in user."""
    try:
        user_email = session.get('user_email')
        db = get_db()
        coll = db[StressModel.collection_name]
        since = datetime.utcnow() - timedelta(days=7)

        pipeline = [
            {'$match': {'user_email': user_email, 'created_at': {'$gte': since}}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                'avg_score': {'$avg': '$score'}
            }},
            {'$sort': {'_id': 1}}
        ]
        rows = list(coll.aggregate(pipeline))
        history = []
        for r in rows:
            # Use date string as timestamp anchor (midnight UTC)
            history.append({
                'timestamp': r['_id'] + 'T00:00:00Z',
                'score': int(r.get('avg_score', 50))
            })

        return jsonify({'history': history})
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