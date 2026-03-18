# TODO: ARCHITECTURE - As this file grows, consider splitting into:
#   - routes/parent/auth.py       - OTP-based authentication (send-otp, verify-otp, logout)
#   - routes/parent/dashboard.py  - Dashboard views and child monitoring
#   - routes/parent/api.py        - API endpoints for parent-specific data
# Use a parent/__init__.py to re-export the combined blueprint.

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from utils.auth_helpers import login_required
from utils.database import get_db, paginate_query
from utils.helpers import safe_error
from utils.rate_limit import apply_rate_limit, Limits
from models.parent import ParentModel
from models.user import UserModel
from services.otp_service import OTPService
from datetime import datetime, timedelta

parent_bp = Blueprint('parent', __name__)

# ==========================================
# PARENT AUTHENTICATION (OTP-Based)
# ==========================================

@parent_bp.route('/register', methods=['GET'])
def register():
    """Redirect to unified OTP login/register page"""
    return redirect(url_for('parent.login'))


@parent_bp.route('/login', methods=['GET'])
def login():
    """Parent login/register page (OTP-based)"""
    if session.get('parent_logged_in'):
        return redirect(url_for('parent.dashboard'))
    return render_template('parent_login.html')


@parent_bp.route('/api/send-otp', methods=['POST'])
@apply_rate_limit(Limits.STRICT)
def send_otp():
    """Step 1: Validate phone against student records and send OTP"""
    try:
        data = request.get_json() or {}
        phone = data.get('phone', '').strip()

        # Normalize phone
        phone = OTPService.normalize_phone(phone)

        # Validate phone (must be exactly 10 digits)
        if not phone or not phone.isdigit() or len(phone) != 10:
            return jsonify({'error': 'Please enter a valid 10-digit phone number'}), 400

        db = get_db()

        # Check if this phone exists in any student's academic record
        student = db['users'].find_one({'parent_phone': phone, 'role': 'student'})
        if not student:
            return jsonify({
                'error': 'This phone number is not registered in our academic records. '
                         'Please contact your ward\'s institution to update your phone number.'
            }), 404

        # Generate and send OTP
        otp, message = OTPService.send_otp(phone)
        if otp is None:
            return jsonify({'error': message}), 429

        # Mask phone for display
        masked_phone = phone[:2] + '******' + phone[-2:]

        # Check if SMS was actually sent (message will say 'via SMS' if it was)
        sms_sent = 'via SMS' in message

        response_data = {
            'success': True,
            'message': message,
            'masked_phone': masked_phone,
            'student_name': student.get('name', 'Student'),
            'student_roll': student.get('roll_number', ''),
            'sms_sent': sms_sent
        }

        # Include OTP for demo mode so frontend can display it
        if not sms_sent:
            response_data['demo_mode'] = True
            response_data['demo_otp'] = otp
            message = "SMS service is unavailable. Please check server logs for the security code (Demo Mode)."
            response_data['message'] = message

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/verify-otp', methods=['POST'])
@apply_rate_limit(Limits.STRICT)
def verify_otp():
    """Step 2: Verify OTP and auto-login or prompt registration"""
    try:
        data = request.get_json() or {}
        phone = OTPService.normalize_phone(data.get('phone', '').strip())
        otp = data.get('otp', '').strip()

        if not phone or not otp:
            return jsonify({'error': 'Phone and OTP are required'}), 400

        # Verify OTP
        success, message = OTPService.verify_otp(phone, otp)
        if not success:
            return jsonify({'error': message}), 401

        db = get_db()

        # Get the student linked to this phone
        student = db['users'].find_one({'parent_phone': phone, 'role': 'student'})
        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        # Check if parent already registered
        parent = ParentModel.find_by_phone(db, phone)

        if parent:
            # Existing parent — auto-login
            session['parent_logged_in'] = True
            session['student_roll'] = parent['student_roll']
            session['parent_name'] = parent['parent_name']
            session['parent_phone'] = parent['parent_phone']
            session['parent_email'] = parent.get('parent_email', '')
            ParentModel.update_last_login(db, parent['student_roll'])

            return jsonify({
                'success': True,
                'action': 'login',
                'message': f'Welcome back, {parent["parent_name"]}!',
                'redirect': '/parent/dashboard'
            }), 200
        else:
            # New parent — needs to complete profile
            return jsonify({
                'success': True,
                'action': 'register',
                'message': 'Phone verified! Please complete your profile.',
                'student_name': student.get('name', 'Student'),
                'student_roll': student.get('roll_number', ''),
                'department': student.get('department', '')
            }), 200

    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/complete-registration', methods=['POST'])
@apply_rate_limit(Limits.STRICT)
def complete_registration():
    """Step 3: Complete new parent registration after OTP verification"""
    try:
        data = request.get_json() or {}
        phone = OTPService.normalize_phone(data.get('phone', '').strip())
        parent_name = data.get('parent_name', '').strip()
        relationship = data.get('relationship', 'parent')

        if not phone or not parent_name:
            return jsonify({'error': 'Phone and name are required'}), 400

        if not parent_name or len(parent_name) < 2:
            return jsonify({'error': 'Please enter a valid name'}), 400

        # Security: ensure this phone was recently verified
        if not OTPService.is_phone_verified(phone):
            return jsonify({'error': 'Phone not verified. Please complete OTP verification first.'}), 403

        db = get_db()

        # Re-verify student record
        student = db['users'].find_one({'parent_phone': phone, 'role': 'student'})
        if not student:
            return jsonify({'error': 'Student record not found for this phone'}), 404

        student_roll = student.get('roll_number', '')

        # Check if parent already registered
        existing = ParentModel.find_by_phone(db, phone)
        if existing:
            return jsonify({'error': 'Parent account already exists for this number'}), 409

        # Create parent account (no password needed — OTP auth)
        ParentModel.create_parent(
            db, student_roll, parent_name, phone, relationship
        )

        # Set last_login on first registration
        ParentModel.update_last_login(db, student_roll)

        # Auto-login the new parent
        session['parent_logged_in'] = True
        session['student_roll'] = student_roll
        session['parent_name'] = parent_name
        session['parent_phone'] = phone
        session['parent_email'] = ''

        return jsonify({
            'success': True,
            'message': f'Welcome to AURA, {parent_name}! Your account is ready.',
            'redirect': '/parent/dashboard'
        }), 201

    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/logout')
def logout():
    """Parent logout"""
    session.pop('parent_logged_in', None)
    session.pop('student_roll', None)
    session.pop('parent_name', None)
    session.pop('parent_email', None)
    session.pop('parent_phone', None)
    return redirect(url_for('parent.login'))


def parent_login_required(f):
    """Decorator to require parent login"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('parent_logged_in'):
            return redirect(url_for('parent.login'))
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# PARENT DASHBOARD
# ==========================================

@parent_bp.route('/dashboard')
@parent_login_required
def dashboard():
    """Parent dashboard"""
    db = get_db()
    student_roll = session.get('student_roll')
    parent_name = session.get('parent_name')
    
    # Get student info
    student = db['users'].find_one({'roll_number': student_roll, 'role': 'student'})
    
    if not student:
        return redirect(url_for('parent.logout'))
    
    return render_template('parent_dashboard.html', 
                         show_nav=False,
                         parent={'name': parent_name},
                         student={
                             'roll_number': student.get('roll_number'),
                             'name': student.get('name', 'Student'),
                             'email': student.get('email', '')
                         })


# ==========================================
# PARENT API ENDPOINTS
# ==========================================

@parent_bp.route('/api/student/performance', methods=['GET'])
@parent_login_required
def get_student_performance():
    """Get student wellness performance data (stress + mood trends)"""
    try:
        student_roll = session.get('student_roll')
        db = get_db()

        student = db['users'].find_one({'roll_number': student_roll, 'role': 'student'})
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        student_email = student.get('email')
        week_ago = datetime.utcnow() - timedelta(days=30)

        # Read from correct collections: student_wellness (stress) and moods
        stress_records = list(db['student_wellness'].find(
            {'student_id': student_email, 'timestamp': {'$gte': week_ago}},
            sort=[('timestamp', 1)],
            limit=30
        ))

        mood_records = list(db['moods'].find(
            {'user_email': student_email, 'created_at': {'$gte': week_ago}},
            sort=[('created_at', 1)],
            limit=30
        ))

        # Format stress history (keep 0-100 scale)
        stress_history = []
        for record in stress_records:
            stress_history.append({
                'level': round(record.get('stress_score', record.get('value', 0)), 1),
                'date': record.get('timestamp', datetime.utcnow()).isoformat()
            })

        # Format mood history
        mood_map = {'angry': 1, 'sad': 2, 'neutral': 3, 'happy': 4, 'excited': 5}
        mood_history = []
        for record in mood_records:
            mood_str = str(record.get('mood', 'neutral')).lower()
            mood_history.append({
                'mood': mood_str,
                'score': mood_map.get(mood_str, 3),
                'date': record.get('created_at', datetime.utcnow()).isoformat()
            })

        # Fallback sample data if no records
        if not stress_history:
            now = datetime.utcnow()
            for i in range(7):
                stress_history.append({
                    'level': 0,
                    'date': (now - timedelta(days=6 - i)).isoformat()
                })

        if not mood_history:
            moods = ['happy', 'calm', 'neutral']
            for i, mood in enumerate(moods):
                mood_history.append({
                    'mood': mood,
                    'score': 3,
                    'date': (datetime.utcnow() - timedelta(days=i)).isoformat()
                })

        return jsonify({
            'stress_history': stress_history,
            'mood_history': mood_history
        }), 200

    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/student/academics', methods=['GET'])
@parent_login_required
def get_student_academics():
    """Get student academic records (CGPA, SGPA, Attendance, Credits)"""
    try:
        student_roll = session.get('student_roll')
        db = get_db()
        
        # Fetch semester records
        records = list(db['academic_records'].find(
            {'student_roll': student_roll}
        ).sort('semester', 1))
        
        if not records:
            return jsonify({
                'success': True,
                'data': {
                    'records': [],
                    'summary': {},
                    'message': 'No academic records found'
                }
            }), 200
        
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
        
        # Calculate summary
        latest = records[-1]
        total_credits_earned = sum(r.get('credits_earned', 0) for r in records)
        total_credits_available = sum(r.get('total_credits', 0) for r in records)
        
        summary = {
            'current_cgpa': latest.get('cgpa', 0),
            'current_sgpa': latest.get('sgpa', 0),
            'current_semester': latest.get('semester', ''),
            'attendance': latest.get('attendance', 0),
            'credits_earned': total_credits_earned,
            'total_credits': total_credits_available,
            'backlogs': latest.get('backlogs', 0),
        }
        
        return jsonify({
            'success': True,
            'data': {
                'records': formatted_records,
                'summary': summary,
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/complaint/submit', methods=['POST'])
@parent_login_required
def submit_complaint():
    """Submit a complaint or grievance"""
    try:
        data = request.get_json()
        student_roll = session.get('student_roll')
        parent_name = session.get('parent_name')
        
        category = data.get('category', 'general')
        subject = data.get('subject', '')
        description = data.get('description', '')
        priority = data.get('priority', 'medium')

        if not subject or not description:
            return jsonify({'error': 'Subject and description required'}), 400

        # Validate enum fields
        if category not in ('general', 'academic', 'welfare', 'administrative', 'other'):
            category = 'general'
        if priority not in ('low', 'medium', 'high'):
            priority = 'medium'

        # Enforce length limits
        subject = subject[:200]
        description = description[:5000]
        
        db = get_db()
        
        complaint_data = {
            'student_roll': student_roll,
            'parent_name': parent_name,
            'category': category,
            'subject': subject,
            'description': description,
            'priority': priority,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'responses': []
        }
        
        result = db['parent_complaints'].insert_one(complaint_data)
        
        return jsonify({
            'success': True,
            'message': 'Complaint submitted successfully',
            'complaint_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/complaints/list', methods=['GET'])
@parent_login_required
def get_complaints():
    """Get all complaints by this parent"""
    try:
        student_roll = session.get('student_roll')
        db = get_db()
        
        complaints = list(db['parent_complaints'].find(
            {'student_roll': student_roll},
            sort=[('created_at', -1)]
        ))
        
        return jsonify([
            {
                'id': str(c['_id']),
                'subject': c.get('subject'),
                'description': c.get('description'),
                'category': c.get('category'),
                'status': c.get('status', 'pending'),
                'priority': c.get('priority'),
                'created_at': c.get('created_at').isoformat() if c.get('created_at') else None
            }
            for c in complaints
        ]), 200
        
    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/suggestion/submit', methods=['POST'])
@parent_login_required
def submit_suggestion():
    """Submit a suggestion"""
    try:
        data = request.get_json()
        student_roll = session.get('student_roll')
        parent_name = session.get('parent_name')
        
        title = data.get('title', '')
        description = data.get('description', '')
        category = data.get('category', 'general')

        if not title or not description:
            return jsonify({'error': 'Title and description required'}), 400

        # Validate enum and enforce length limits
        if category not in ('general', 'academic', 'welfare', 'infrastructure', 'other'):
            category = 'general'
        title = title[:200]
        description = description[:5000]
        
        db = get_db()
        
        suggestion_data = {
            'student_roll': student_roll,
            'parent_name': parent_name,
            'title': title,
            'description': description,
            'category': category,
            'status': 'pending',
            'upvotes': 0,
            'created_at': datetime.utcnow()
        }
        
        result = db['parent_suggestions'].insert_one(suggestion_data)
        
        return jsonify({
            'success': True,
            'message': 'Suggestion submitted successfully',
            'suggestion_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/announcements', methods=['GET'])
@parent_login_required
def get_announcements():
    """Get department achievements and placement updates"""
    try:
        db = get_db()
        
        # Get latest announcements
        announcements = list(db['announcements'].find(
            {'type': {'$in': ['achievement', 'placement', 'general', 'achievements', 'placements']}},
            sort=[('created_at', -1)],
            limit=20
        ))
        
        # If no announcements, create sample data
        if not announcements:
            sample_announcements = [
                {
                    'type': 'achievements',
                    'title': 'National Hackathon Winner',
                    'content': 'Our students secured 1st place in the National Level Hackathon 2024 with their innovative AI project.',
                    'date': (datetime.utcnow() - timedelta(days=2)).isoformat()
                },
                {
                    'type': 'placements',
                    'title': 'Top Companies Visit Campus',
                    'content': 'Microsoft, Google, and Amazon conducted campus recruitment drives. 150+ students placed with average package of 12 LPA.',
                    'date': (datetime.utcnow() - timedelta(days=5)).isoformat()
                },
                {
                    'type': 'general',
                    'title': 'Annual Tech Fest Announcement',
                    'content': 'Registration open for TechFest 2024. Multiple events including coding, robotics, and innovation challenges.',
                    'date': (datetime.utcnow() - timedelta(days=7)).isoformat()
                }
            ]
            return jsonify(sample_announcements), 200
        
        return jsonify([
            {
                'id': str(a['_id']),
                'type': a.get('type', 'general'),
                'title': a.get('title'),
                'content': a.get('description', a.get('content', '')),
                'department': a.get('department', 'All'),
                'date': a.get('created_at', datetime.utcnow()).isoformat()
            }
            for a in announcements
        ]), 200
        
    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


# ==========================================
# ADDITIONAL PARENT API ENDPOINTS
# ==========================================

@parent_bp.route('/api/student/wellness-summary', methods=['GET'])
@parent_login_required
def get_student_wellness_summary():
    """Get comprehensive student wellness summary for parent view"""
    try:
        student_roll = session.get('student_roll')
        db = get_db()
        
        # Get student email from roll number
        student = db['users'].find_one({'roll_number': student_roll, 'role': 'student'})
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        student_email = student.get('email')
        
        # Get latest wellness data
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Stress data
        stress_records = list(db['student_wellness'].find(
            {'student_id': student_email, 'data_type': 'stress', 'timestamp': {'$gte': week_ago}},
            sort=[('timestamp', -1)]
        ))
        
        # Mood data
        mood_records = list(db['student_wellness'].find(
            {'student_id': student_email, 'data_type': 'mood', 'timestamp': {'$gte': week_ago}},
            sort=[('timestamp', -1)]
        ))
        
        # Calculate averages
        avg_stress = 0
        if stress_records:
            avg_stress = sum([r.get('value', 50) for r in stress_records]) / len(stress_records)
        
        avg_mood = 3
        if mood_records:
            avg_mood = sum([r.get('value', 3) for r in mood_records]) / len(mood_records)
        
        # Wellness status based on metrics
        wellness_status = 'good'
        if avg_stress > 70 or avg_mood < 2:
            wellness_status = 'needs_attention'
        elif avg_stress > 50 or avg_mood < 3:
            wellness_status = 'moderate'
        
        # Format stress history for chart (keep 0-100 scale)
        stress_history = []
        for record in reversed(stress_records[:14]):
            stress_history.append({
                'level': round(record.get('value', 0), 1),
                'date': record.get('timestamp').isoformat() if record.get('timestamp') else datetime.utcnow().isoformat()
            })
        
        # Format mood history
        mood_history = []
        mood_labels = {1: 'very_low', 2: 'low', 3: 'neutral', 4: 'happy', 5: 'excited'}
        for record in mood_records[:10]:
            mood_value = record.get('value', 3)
            mood_history.append({
                'mood': mood_labels.get(mood_value, 'neutral'),
                'date': record.get('timestamp').isoformat() if record.get('timestamp') else datetime.utcnow().isoformat()
            })
        
        # Activity count
        total_activities = len(stress_records) + len(mood_records)
        
        return jsonify({
            'student_name': student.get('name', 'Student'),
            'avg_stress': round(avg_stress, 1),
            'avg_mood': round(avg_mood, 1),
            'wellness_status': wellness_status,
            'stress_history': stress_history,
            'mood_history': mood_history,
            'total_activities': total_activities,
            'last_checkin': stress_records[0].get('timestamp').isoformat() if stress_records else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/student/activity-log', methods=['GET'])
@parent_login_required
def get_student_activity_log():
    """Get student activity log for parent monitoring"""
    try:
        student_roll = session.get('student_roll')
        db = get_db()
        
        # Get student email
        student = db['users'].find_one({'roll_number': student_roll, 'role': 'student'})
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        student_email = student.get('email')
        
        # Get recent activities
        activities = list(db['student_wellness'].find(
            {'student_id': student_email},
            sort=[('timestamp', -1)],
            limit=50
        ))
        
        formatted_activities = []
        for act in activities:
            activity_type = act.get('data_type', 'unknown')
            value = act.get('value', 0)
            
            if activity_type == 'stress':
                description = f"Stress check-in: {value}/100"
            elif activity_type == 'mood':
                mood_labels = {1: 'Very Low', 2: 'Low', 3: 'Neutral', 4: 'Happy', 5: 'Excited'}
                description = f"Mood: {mood_labels.get(value, 'Unknown')}"
            else:
                description = f"{activity_type.capitalize()} activity"
            
            formatted_activities.append({
                'type': activity_type,
                'description': description,
                'timestamp': act.get('timestamp').isoformat() if act.get('timestamp') else None,
                'source': act.get('source', 'manual')
            })
        
        return jsonify(formatted_activities), 200
        
    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500


@parent_bp.route('/api/notifications', methods=['GET'])
@parent_login_required
def get_parent_notifications():
    """Get notifications for parent with pagination support.

    Query params:
        page (int): Page number (1-indexed, default 1)
        per_page (int): Items per page (default 20, max 100)

    Example: /api/notifications?page=2&per_page=10
    """
    try:
        student_roll = session.get('student_roll')
        db = get_db()

        # Parse pagination parameters (#27 Scalability: Use paginate_query utility)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Build query and apply pagination
        query = {'student_roll': student_roll}
        cursor = db['parent_notifications'].find(query).sort('created_at', -1)
        notifications = list(paginate_query(cursor, page, per_page))

        # Get total for pagination metadata (optional, for UI pagination controls)
        total = db['parent_notifications'].count_documents(query)
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1

        formatted = []
        for notif in notifications:
            formatted.append({
                'id': str(notif['_id']),
                'type': notif.get('type', 'info'),
                'title': notif.get('title', ''),
                'message': notif.get('message', ''),
                'read': notif.get('read', False),
                'created_at': notif.get('created_at').isoformat() if notif.get('created_at') else None
            })
        
        # If no notifications, return sample
        if not formatted:
            formatted = [
                {
                    'id': 'sample-1',
                    'type': 'info',
                    'title': 'Welcome to AURA Parent Portal',
                    'message': 'You can now monitor your child\'s wellness and academic progress.',
                    'read': False,
                    'created_at': datetime.utcnow().isoformat()
                }
            ]

        # Return with pagination metadata
        return jsonify({
            'notifications': formatted,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }), 200

    except Exception as e:
        return jsonify({'error': safe_error(e, 'parent')}), 500
