from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_helpers import login_required
from utils.database import get_db
from models.mood import MoodModel
from models.stress import StressModel
from models.grievance import GrievanceModel
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_helpers import login_required
from utils.database import get_db
# We will temporarily comment out these imports to stop the 500 Error
# from models.grievance import GrievanceModel
# from services.stress_service import calculate_daily_stress
from models.mood import MoodModel
from models.stress import StressModel
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_helpers import login_required
from utils.database import get_db
from models.mood import MoodModel
from models.stress import StressModel
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