from flask import Blueprint, render_template, jsonify, session, request
from utils.auth_helpers import login_required, role_required
from utils.database import get_db
from models.stress import StressModel
from models.mood import MoodModel
from models.grievance import GrievanceModel
from datetime import datetime, timedelta

proctor_bp = Blueprint('proctor', __name__)

@proctor_bp.route('/dashboard')
@login_required
@role_required('proctor')
def dashboard():
    return render_template('proctor_dashboard.html')

@proctor_bp.route('/hod')
@login_required
@role_required('hod')
def hod_dashboard():
    return render_template('hod_dashboard.html')


@proctor_bp.route('/api/proctor/students', methods=['GET'])
@login_required
@role_required('proctor')
def api_students():
    """Fetch all students with latest mood and 7-day stress trend."""
    try:
        db = get_db()
        users = db['users']
        stress_coll = db[StressModel.collection_name]
        moods_coll = db[MoodModel.collection_name]
        # Privacy: Only return students assigned to the logged-in proctor
        current_proctor = session.get('user_email')
        students = list(users.find({'role': 'student', 'proctor_email': current_proctor}))
        result = []
        
        for s in students:
            email = s.get('email')
            name = s.get('name', 'Unknown')
            
            # Latest mood
            latest_mood = moods_coll.find_one({'user_email': email}, sort=[('created_at', -1)])
            mood = (latest_mood or {}).get('mood', 'normal')
            
            # Last 7 days stress
            since = datetime.utcnow() - timedelta(days=7)
            stress_records = list(stress_coll.find({'user_email': email, 'created_at': {'$gte': since}}).sort('created_at', 1))
            trend = [r.get('score', 50) for r in stress_records] if stress_records else [50]
            avg = int(sum(trend) / len(trend))
            
            result.append({
                'email': email,
                'name': name,
                'mood': mood,
                'avg_stress': avg,
                'trend': trend
            })
        
        return jsonify({'students': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@proctor_bp.route('/api/hod/wellness', methods=['GET'])
@login_required
@role_required('hod')
def api_hod_wellness():
    """Department-wide stress trend aggregation for last 30 days."""
    try:
        db = get_db()
        stress_coll = db[StressModel.collection_name]
        since = datetime.utcnow() - timedelta(days=30)
        
        # Aggregate stress by date
        pipeline = [
            {'$match': {'created_at': {'$gte': since}}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                'avg_score': {'$avg': '$score'}
            }},
            {'$sort': {'_id': 1}}
        ]
        result = list(stress_coll.aggregate(pipeline))
        
        dates = [r['_id'] for r in result]
        scores = [int(r['avg_score']) for r in result]
        
        return jsonify({'dates': dates, 'scores': scores})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proctor_bp.route('/api/proctor/grievances', methods=['GET'])
@login_required
@role_required('proctor')
def list_grievances():
    try:
        db = get_db()
        coll = db[GrievanceModel.collection_name]
        items = list(coll.find({'status': {'$in': ['pending', 'in_progress']}}).sort('created_at', -1))
        # Convert ObjectId and datetime to string
        result = []
        for g in items:
            result.append({
                'id': str(g.get('_id')),
                'user_email': g.get('user_email'),
                'subject': g.get('subject'),
                'description': g.get('description'),
                'status': g.get('status'),
                'created_at': g.get('created_at').isoformat() if g.get('created_at') else None,
                'proctor_note': g.get('proctor_note'),
            })
        return jsonify({'grievances': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proctor_bp.route('/api/proctor/grievances/<gid>/resolve', methods=['POST'])
@login_required
@role_required('proctor')
def resolve_grievance(gid):
    try:
        db = get_db()
        coll = db[GrievanceModel.collection_name]
        note = (getattr(request, 'json', {}) or {}).get('note', '') if hasattr(request, 'json') else ''
        coll.update_one({'_id': gid}, {'$set': {
            'status': 'resolved',
            'resolved_at': datetime.utcnow(),
            'resolved_by': session.get('user_email'),
            'proctor_note': note,
        }})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proctor_bp.route('/student/<email>')
@login_required
@role_required('proctor')
def student_detail_page(email):
    """Render the student detail page for a given student email."""
    return render_template('student_detail.html', student_email=email)


@proctor_bp.route('/api/proctor/student/<email>', methods=['GET'])
@login_required
@role_required('proctor')
def api_student_detail(email):
    """Return profile, stress history, last 10 chats, and grievances for a student."""
    try:
        db = get_db()
        users = db['users']
        stress_coll = db[StressModel.collection_name]
        chats_coll = db['chats']
        grv_coll = db[GrievanceModel.collection_name]

        profile = users.find_one({'email': email}, {'hashed_password': 0})
        if not profile:
            return jsonify({'error': 'Student not found'}), 404

        # Privacy: ensure proctor is assigned to this student (HOD can access any)
        user_role = session.get('user_role')
        if user_role != 'hod':
            current_proctor = session.get('user_email')
            if profile.get('proctor_email') != current_proctor:
                return jsonify({'error': 'Forbidden'}), 403

        # Stress history: last 30 days daily average
        since = datetime.utcnow() - timedelta(days=30)
        pipeline = [
            {'$match': {'user_email': email, 'created_at': {'$gte': since}}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                'avg_score': {'$avg': '$score'}
            }},
            {'$sort': {'_id': 1}}
        ]
        hist_rows = list(stress_coll.aggregate(pipeline))
        stress_history = [{'date': r['_id'], 'score': int(r['avg_score'])} for r in hist_rows]

        # Recent 10 chats (mental)
        chats = list(chats_coll.find({'user_email': email, 'type': 'mental'}).sort('created_at', -1).limit(10))
        chats_fmt = [{
            'message': c.get('message'),
            'response': c.get('response'),
            'sentiment': c.get('sentiment'),
            'created_at': (c.get('created_at') or '').isoformat() if c.get('created_at') else ''
        } for c in chats]

        # All grievances for the student
        grievances = list(grv_coll.find({'user_email': email}).sort('created_at', -1))
        grv_fmt = [{
            'subject': g.get('subject'),
            'description': g.get('description'),
            'status': g.get('status'),
            'created_at': (g.get('created_at') or '').isoformat() if g.get('created_at') else '',
            'resolved_at': (g.get('resolved_at') or '').isoformat() if g.get('resolved_at') else '',
        } for g in grievances]

        # Fetch proctor notes (optional)
        notes = list(db['proctor_notes'].find({'user_email': email}).sort('created_at', -1))
        notes_fmt = []
        for n in notes:
            proctor_doc = users.find_one({'email': n.get('proctor_email')}, {'name': 1}) or {}
            notes_fmt.append({
                'note': n.get('note'),
                'urgent': bool(n.get('urgent', False)),
                'created_at': (n.get('created_at') or '').isoformat() if n.get('created_at') else '',
                'proctor_email': n.get('proctor_email'),
                'proctor_name': proctor_doc.get('name', n.get('proctor_email'))
            })

        return jsonify({
            'profile': {
                'email': profile.get('email'),
                'name': profile.get('name'),
                'role': profile.get('role'),
                'created_at': profile.get('created_at'),
            },
            'stress_history': stress_history,
            'chats': chats_fmt,
            'grievances': grv_fmt,
            'notes': notes_fmt,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proctor_bp.route('/api/proctor/student/<email>/notes', methods=['POST'])
@login_required
@role_required('proctor')
def api_add_proctor_note(email):
    """Save a proctor note for the student."""
    try:
        data = request.get_json() or {}
        note = (data.get('note') or '').strip()
        if not note:
            return jsonify({'error': 'Note required'}), 400
        # Optional urgent flag
        urgent = bool(data.get('urgent', False))
        # Privacy: ensure proctor is assigned to this student
        db = get_db()
        users = db['users']
        profile = users.find_one({'email': email})
        if not profile:
            return jsonify({'error': 'Student not found'}), 404
        current_proctor = session.get('user_email')
        if profile.get('proctor_email') != current_proctor:
            return jsonify({'error': 'Forbidden'}), 403
        db['proctor_notes'].insert_one({
            'user_email': email,
            'note': note,
            'urgent': urgent,
            'created_at': datetime.utcnow(),
            'proctor_email': session.get('user_email')
        })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
