"""
Connect Hub v2 — Elite-Mode Routes & API
==========================================

Modules:
    1. Peer Network        — connections, suggestions, profiles
    2. Group Sessions      — CRUD, membership, group chat
    3. Events              — RSVP, .ics, reminders
    4. Resources           — share, like, tag-filter
    5. Direct Chat         — 1-to-1 messaging (polling)
    6. Group Chat          — per-group messaging (polling)
    7. Activity Feed       — live community pulse
    8. Notifications       — per-user notification queue
    9. Stats & Recs        — stress-aware intelligence
   10. Seed Data           — auto-populate on first visit

All endpoints require @login_required.
"""

from flask import Blueprint, jsonify, request, session, render_template, current_app, Response
from utils.auth_helpers import login_required, demo_restricted
from utils.database import get_db
from utils.helpers import contains_blocked_content
from datetime import datetime, timedelta
from bson import ObjectId
import uuid
import re

connect_bp = Blueprint('connect', __name__)

# ── Constants ────────────────────────────────────────────────────────────────

# ── Helpers ──────────────────────────────────────────────────────────────────

def _sanitize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r'^https?://', url):
        return ''
    if re.search(r'(javascript|data|vbscript):', url, re.I):
        return ''
    return url[:2048]


def _paginate(cursor, page: int, per_page: int = 20):
    page = max(1, page)
    return cursor.skip((page - 1) * per_page).limit(per_page)


def _heartbeat(db, email: str):
    db['hub_activity'].update_one(
        {'user_email': email},
        {'$set': {'user_email': email, 'last_active': datetime.utcnow()}},
        upsert=True,
    )


def _user_stress(db, email: str) -> dict:
    reading = db['stress'].find_one({'user_email': email}, sort=[('created_at', -1)])
    if reading:
        return {
            'score': reading.get('score', 50),
            'trend': reading.get('trend', 'stable'),
            'confidence': reading.get('confidence', 0.5),
        }
    return {'score': 50, 'trend': 'stable', 'confidence': 0.1}


def _stress_label(score) -> str:
    score = float(score) if score else 50
    if score <= 25: return 'Relaxed'
    if score <= 45: return 'Manageable'
    if score <= 65: return 'Elevated'
    if score <= 80: return 'High'
    return 'Critical'


def _user_display_name(db, email: str) -> str:
    u = db['users'].find_one({'email': email}, {'name': 1})
    if u and u.get('name', '').strip():
        parts = u['name'].split()
        return parts[0] if parts else email.split('@')[0]
    return email.split('@')[0] or 'User'


def _full_name(db, email: str) -> str:
    u = db['users'].find_one({'email': email}, {'name': 1})
    return u.get('name', email.split('@')[0]) if u else email.split('@')[0]


def _is_online(db, email: str) -> bool:
    a = db['hub_activity'].find_one({'user_email': email})
    if a and a.get('last_active'):
        return (datetime.utcnow() - a['last_active']).total_seconds() < 600
    return False


def _log_hub_engagement(db, email: str, action: str):
    db['student_wellness'].insert_one({
        'student_id': email, 'data_type': 'hub_engagement',
        'value': action, 'timestamp': datetime.utcnow(), 'source': 'connect_hub',
    })


def _post_feed(db, actor_email: str, action: str, target: str = ''):
    name = _user_display_name(db, actor_email)
    db['hub_feed'].insert_one({
        'actor_name': name, 'actor_email': actor_email,
        'action': action, 'target': target, 'created_at': datetime.utcnow(),
    })


def _notify(db, email: str, ntype: str, title: str, body: str = '', link: str = ''):
    db['hub_notifications'].insert_one({
        'user_email': email, 'type': ntype, 'title': title,
        'body': body, 'read': False, 'link': link, 'created_at': datetime.utcnow(),
    })

def _profanity_check(text: str) -> bool:
    return contains_blocked_content(text)


def _chat_rate_ok(db, email: str) -> bool:
    last = db['message_timestamps'].find_one({'user_id': email})
    if not last:
        return True
    return (datetime.utcnow() - last['timestamp']).total_seconds() >= 2


def _record_chat_ts(db, email: str):
    db['message_timestamps'].update_one(
        {'user_id': email}, {'$set': {'timestamp': datetime.utcnow()}}, upsert=True)


def _are_connected(db, a: str, b: str) -> bool:
    return db['connections'].find_one({
        '$or': [
            {'user_email': a, 'connected_to': b, 'status': 'accepted'},
            {'user_email': b, 'connected_to': a, 'status': 'accepted'},
        ]
    }) is not None


# ── Page Route ───────────────────────────────────────────────────────────────

@connect_bp.route('/hub')
@connect_bp.route('/hub/<path:subpath>')
@login_required
def connect_hub_page(subpath=None):
    _ensure_seed()
    return render_template('connect_hub.html')


# ═══════════════════════════════════════════════════════════════════════════════
#  SEED DATA — auto-populate on first visit so hub never looks empty
# ═══════════════════════════════════════════════════════════════════════════════

_seed_done = False

def _ensure_seed():
    """
    Production-ready seed data generator for Connect Hub.
    Creates realistic peer users, connections, groups, events, resources, and interactions.
    """
    global _seed_done
    if _seed_done:
        return
    _seed_done = True
    try:
        db = get_db()
        # Only seed if hub is empty
        if db['groups'].count_documents({}) > 0:
            return
        
        now = datetime.utcnow()
        from werkzeug.security import generate_password_hash
        
        # ── 1. Create realistic peer users ──
        seed_peers = [
            {'name': 'Arjun Kumar', 'email': 'arjun.kumar@student.edu', 'dept': 'Computer Science', 'year': 3, 'stress': 62, 'trend': 'stable'},
            {'name': 'Priya Sharma', 'email': 'priya.sharma@student.edu', 'dept': 'Computer Science', 'year': 2, 'stress': 45, 'trend': 'decreasing'},
            {'name': 'Sneha Patel', 'email': 'sneha.patel@student.edu', 'dept': 'Biology', 'year': 4, 'stress': 71, 'trend': 'increasing'},
            {'name': 'Meera Reddy', 'email': 'meera.reddy@student.edu', 'dept': 'Electrical Engineering', 'year': 3, 'stress': 58, 'trend': 'stable'},
            {'name': 'Kavya Singh', 'email': 'kavya.singh@student.edu', 'dept': 'Mechanical Engineering', 'year': 2, 'stress': 39, 'trend': 'stable'},
            {'name': 'Ravi Verma', 'email': 'ravi.verma@student.edu', 'dept': 'Mathematics', 'year': 3, 'stress': 55, 'trend': 'decreasing'},
            {'name': 'Anjali Gupta', 'email': 'anjali.gupta@student.edu', 'dept': 'Computer Science', 'year': 4, 'stress': 68, 'trend': 'increasing'},
            {'name': 'Rohit Rao', 'email': 'rohit.rao@student.edu', 'dept': 'Physics', 'year': 2, 'stress': 42, 'trend': 'stable'},
            {'name': 'Divya Nair', 'email': 'divya.nair@student.edu', 'dept': 'Biology', 'year': 3, 'stress': 64, 'trend': 'increasing'},
            {'name': 'Vikram Joshi', 'email': 'vikram.joshi@student.edu', 'dept': 'Electrical Engineering', 'year': 4, 'stress': 73, 'trend': 'stable'},
            {'name': 'Neha Kapoor', 'email': 'neha.kapoor@student.edu', 'dept': 'Computer Science', 'year': 2, 'stress': 38, 'trend': 'decreasing'},
            {'name': 'Amit Desai', 'email': 'amit.desai@student.edu', 'dept': 'Mechanical Engineering', 'year': 3, 'stress': 51, 'trend': 'stable'},
            {'name': 'Pooja Iyer', 'email': 'pooja.iyer@student.edu', 'dept': 'Mathematics', 'year': 4, 'stress': 66, 'trend': 'increasing'},
            {'name': 'Karan Mehta', 'email': 'karan.mehta@student.edu', 'dept': 'Physics', 'year': 2, 'stress': 44, 'trend': 'stable'},
            {'name': 'Sanya Bansal', 'email': 'sanya.bansal@student.edu', 'dept': 'Biology', 'year': 3, 'stress': 59, 'trend': 'decreasing'},
        ]
        
        created_users = []
        for peer in seed_peers:
            # Create user account
            user_exists = db['users'].find_one({'email': peer['email']})
            if not user_exists:
                db['users'].insert_one({
                    'email': peer['email'],
                    'name': peer['name'],
                    'password': generate_password_hash('demo123'),  # Default demo password
                    'role': 'student',
                    'department': peer['dept'],
                    'year': peer['year'],
                    'created_at': now - timedelta(days=30),
                })
            
            # Create stress reading
            db['stress'].insert_one({
                'user_email': peer['email'],
                'score': peer['stress'],
                'trend': peer['trend'],
                'confidence': 0.75 + (0.15 * (peer['stress'] / 100)),
                'created_at': now - timedelta(hours=2),
            })
            
            # Create hub activity (mark some as online)
            is_online = len(created_users) % 3 == 0  # Make every 3rd user online
            if is_online:
                db['hub_activity'].insert_one({
                    'user_email': peer['email'],
                    'last_active': now - timedelta(minutes=2),
                })
            
            created_users.append(peer['email'])
        
        # ── 2. Create peer connections ──
        # Connect the logged-in user to some seed peers
        current_user = session.get('user_email', '')
        connections_for_user = ['arjun.kumar@student.edu', 'priya.sharma@student.edu', 
                                'meera.reddy@student.edu', 'ravi.verma@student.edu']
        
        for peer_email in connections_for_user:
            if peer_email in created_users and current_user:
                db['connections'].insert_one({
                    'user_email': current_user,
                    'connected_to': peer_email,
                    'status': 'accepted',
                    'created_at': now - timedelta(days=7),
                })
        
        # Create connections between seed users
        peer_connections = [
            ('arjun.kumar@student.edu', 'anjali.gupta@student.edu'),
            ('priya.sharma@student.edu', 'neha.kapoor@student.edu'),
            ('sneha.patel@student.edu', 'divya.nair@student.edu'),
            ('meera.reddy@student.edu', 'vikram.joshi@student.edu'),
            ('kavya.singh@student.edu', 'amit.desai@student.edu'),
            ('ravi.verma@student.edu', 'pooja.iyer@student.edu'),
        ]
        
        for user1, user2 in peer_connections:
            db['connections'].insert_one({
                'user_email': user1,
                'connected_to': user2,
                'status': 'accepted',
                'created_at': now - timedelta(days=5),
            })

        # ── 3. Create groups with members ──
        seed_groups = [
            {'name': 'AI Study Circle', 'description': 'Discuss ML, deep learning, and AI papers together.', 'type': 'study', 
             'members': ['arjun.kumar@student.edu', 'anjali.gupta@student.edu', 'neha.kapoor@student.edu']},
            {'name': 'Exam Prep Squad', 'description': 'Collaborate on upcoming exam preparation.', 'type': 'study',
             'members': ['priya.sharma@student.edu', 'ravi.verma@student.edu', 'karan.mehta@student.edu']},
            {'name': 'Mindful Moments', 'description': 'Daily meditation and breathing exercises.', 'type': 'relaxation',
             'members': ['sneha.patel@student.edu', 'divya.nair@student.edu', 'sanya.bansal@student.edu']},
            {'name': 'Stress Busters', 'description': 'Share strategies and support each other through tough times.', 'type': 'peer_support',
             'members': ['meera.reddy@student.edu', 'vikram.joshi@student.edu', 'pooja.iyer@student.edu']},
            {'name': 'Code & Chill', 'description': 'Casual coding sessions with zero pressure.', 'type': 'relaxation',
             'members': ['arjun.kumar@student.edu', 'neha.kapoor@student.edu', 'rohit.rao@student.edu']},
            {'name': 'Campus Wellness Club', 'description': 'Mental health awareness and peer support forum.', 'type': 'peer_support',
             'members': ['kavya.singh@student.edu', 'amit.desai@student.edu', 'sanya.bansal@student.edu']},
            {'name': 'Physics Problem Solving', 'description': 'Work through challenging physics problems together.', 'type': 'study',
             'members': ['rohit.rao@student.edu', 'karan.mehta@student.edu']},
        ]
        
        group_ids = {}
        for g in seed_groups:
            gid = str(uuid.uuid4())
            group_ids[g['name']] = gid
            if current_user and g['type'] in ['study', 'peer_support']:
                g['members'].append(current_user)
            db['groups'].insert_one({
                'group_id': gid, 'name': g['name'],
                'description': g['description'], 'type': g['type'],
                'created_by': g['members'][0] if g['members'] else 'system@aura',
                'members': g['members'], 'member_count': len(g['members']),
                'created_at': now - timedelta(days=10), 'updated_at': now - timedelta(hours=3),
            })
        
        # ── 4. Add group messages ──
        if 'AI Study Circle' in group_ids:
            gid = group_ids['AI Study Circle']
            group_msgs = [
                {'sender': 'arjun.kumar@student.edu', 'msg': 'Anyone read the new Attention is All You Need paper?', 'ago': 120},
                {'sender': 'anjali.gupta@student.edu', 'msg': 'Yes! The transformer architecture is fascinating', 'ago': 115},
                {'sender': 'neha.kapoor@student.edu', 'msg': 'Can we discuss it in tomorrow\'s session?', 'ago': 110},
            ]
            for m in group_msgs:
                db['group_messages'].insert_one({
                    'group_id': gid, 'sender_email': m['sender'],
                    'sender_name': _user_display_name(db, m['sender']),
                    'message': m['msg'], 'created_at': now - timedelta(minutes=m['ago']),
                })

        # ── 5. Create events with participants ──
        seed_events = [
            {'title': 'Guided Meditation Session', 'type': 'meditation', 'days': 2, 'dur': 30,
             'desc': 'Join us for a calming 30-minute guided meditation.',
             'participants': ['sneha.patel@student.edu', 'divya.nair@student.edu', 'kavya.singh@student.edu']},
            {'title': 'Stress Management Workshop', 'type': 'workshop', 'days': 5, 'dur': 60,
             'desc': 'Learn proven techniques to manage academic stress.',
             'participants': ['meera.reddy@student.edu', 'pooja.iyer@student.edu']},
            {'title': 'Study Techniques Webinar', 'type': 'webinar', 'days': 7, 'dur': 45,
             'desc': 'Evidence-based study methods presented by faculty.',
             'participants': ['arjun.kumar@student.edu', 'priya.sharma@student.edu', 'ravi.verma@student.edu']},
            {'title': 'Yoga & Breathing', 'type': 'meditation', 'days': 3, 'dur': 45,
             'desc': 'Gentle yoga session suitable for all levels.',
             'participants': ['sanya.bansal@student.edu', 'amit.desai@student.edu']},
            {'title': 'Peer Support Circle', 'type': 'peer_support', 'days': 4, 'dur': 60,
             'desc': 'Safe space to share experiences and support each other.',
             'participants': ['vikram.joshi@student.edu', 'karan.mehta@student.edu']},
        ]
        
        for ev in seed_events:
            if current_user and ev['type'] in ['meditation', 'workshop']:
                ev['participants'].append(current_user)
            db['events'].insert_one({
                'event_id': str(uuid.uuid4()), 'title': ev['title'],
                'description': ev['desc'], 'date': now + timedelta(days=ev['days']),
                'duration_minutes': ev['dur'], 'type': ev['type'],
                'created_by': ev['participants'][0] if ev['participants'] else 'system@aura',
                'participants': ev['participants'], 'max_participants': 50,
                'created_at': now - timedelta(days=2),
            })

        # ── 6. Create resources with likes ──
        seed_resources = [
            {'title': 'Pomodoro Timer Guide', 'link': 'https://todoist.com/productivity-methods/pomodoro-technique', 
             'tags': ['study', 'productivity'], 'desc': 'Boost focus with 25-minute work sessions',
             'likes': ['arjun.kumar@student.edu', 'priya.sharma@student.edu', 'ravi.verma@student.edu']},
            {'title': 'Headspace Basics', 'link': 'https://www.headspace.com/meditation/meditation-for-beginners', 
             'tags': ['wellness', 'meditation'], 'desc': 'Introduction to mindfulness meditation',
             'likes': ['sneha.patel@student.edu', 'kavya.singh@student.edu']},
            {'title': 'Khan Academy CS', 'link': 'https://www.khanacademy.org/computing', 
             'tags': ['study', 'cs'], 'desc': 'Free computer science courses and tutorials',
             'likes': ['neha.kapoor@student.edu', 'anjali.gupta@student.edu']},
            {'title': 'Breathing Exercise App', 'link': 'https://apps.apple.com/app/breathe-calm-anxiety-relief/id1285982210',
             'tags': ['wellness', 'stress'], 'desc': 'Quick breathing techniques for stress relief',
             'likes': ['meera.reddy@student.edu', 'divya.nair@student.edu', 'sanya.bansal@student.edu']},
            {'title': 'Study Music Playlist', 'link': 'https://open.spotify.com/playlist/37i9dQZF1DX8NTLI2TtZa6',
             'tags': ['study', 'focus'], 'desc': 'Lo-fi beats for concentration',
             'likes': ['rohit.rao@student.edu', 'karan.mehta@student.edu']},
            {'title': 'Mental Health Toolkit', 'link': 'https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health',
             'tags': ['wellness', 'mental-health'], 'desc': 'Resources from NIMH for mental wellness',
             'likes': ['vikram.joshi@student.edu', 'pooja.iyer@student.edu', 'amit.desai@student.edu']},
        ]
        
        for r in seed_resources:
            if current_user:
                r['likes'].append(current_user)
            db['resources'].insert_one({
                'resource_id': str(uuid.uuid4()), 'title': r['title'],
                'link': r['link'], 'description': r['desc'],
                'uploaded_by': r['likes'][0] if r['likes'] else 'system@aura',
                'tags': r['tags'], 'likes': len(r['likes']), 'liked_by': r['likes'],
                'created_at': now - timedelta(hours=24),
            })

        # ── 7. Create activity feed ──
        feed_items = [
            {'actor': 'arjun.kumar@student.edu', 'action': 'created_group', 'target': 'AI Study Circle', 'ago': 10},
            {'actor': 'priya.sharma@student.edu', 'action': 'joined_group', 'target': 'Exam Prep Squad', 'ago': 8},
            {'actor': 'sneha.patel@student.edu', 'action': 'created_event', 'target': 'Guided Meditation Session', 'ago': 6},
            {'actor': 'ravi.verma@student.edu', 'action': 'shared_resource', 'target': 'Pomodoro Timer Guide', 'ago': 5},
            {'actor': 'meera.reddy@student.edu', 'action': 'joined_event', 'target': 'Stress Management Workshop', 'ago': 4},
            {'actor': 'kavya.singh@student.edu', 'action': 'shared_resource', 'target': 'Breathing Exercise App', 'ago': 3},
            {'actor': 'anjali.gupta@student.edu', 'action': 'created_group', 'target': 'Code & Chill', 'ago': 2},
            {'actor': 'neha.kapoor@student.edu', 'action': 'joined_group', 'target': 'AI Study Circle', 'ago': 1},
        ]
        
        for fi in feed_items:
            db['hub_feed'].insert_one({
                'actor_name': _user_display_name(db, fi['actor']),
                'actor_email': fi['actor'], 'action': fi['action'], 'target': fi['target'],
                'created_at': now - timedelta(hours=fi['ago']),
            })
        
        # ── 8. Create sample DM messages ──
        if current_user:
            dm_peer = 'arjun.kumar@student.edu'
            if dm_peer in created_users:
                sample_messages = [
                    {'from': dm_peer, 'to': current_user, 'msg': 'Hey! How are you managing with the exam prep?', 'ago': 45},
                    {'from': current_user, 'to': dm_peer, 'msg': 'It\'s challenging but managing. How about you?', 'ago': 40},
                    {'from': dm_peer, 'to': current_user, 'msg': 'Same here. Want to join our study group session tomorrow?', 'ago': 35},
                ]
                for m in sample_messages:
                    db['peer_messages'].insert_one({
                        'from_email': m['from'], 'to_email': m['to'],
                        'message': m['msg'], 'seen': True,
                        'created_at': now - timedelta(minutes=m['ago']),
                    })
        
        current_app.logger.info("✓ Connect Hub seed data created successfully")

    except Exception as e:
        current_app.logger.warning("Hub seed warning: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. PEER NETWORK
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/connect/peers')
@login_required
def get_peers():
    db = get_db()
    email = session['user_email']
    _heartbeat(db, email)

    connections = list(db['connections'].find({
        '$or': [
            {'user_email': email, 'status': 'accepted'},
            {'connected_to': email, 'status': 'accepted'},
        ]
    }).sort('updated_at', -1))

    peers = []
    for conn in connections:
        pe = conn['connected_to'] if conn['user_email'] == email else conn['user_email']
        u = db['users'].find_one({'email': pe}, {'hashed_password': 0})
        if not u:
            continue
        stress = _user_stress(db, pe)
        unread = db['peer_messages'].count_documents({
            'from_email': pe, 'to_email': email, 'seen': False
        })
        peers.append({
            'email': pe,
            'name': u.get('name', pe.split('@')[0]),
            'department': u.get('department', ''),
            'stress_level': _stress_label(stress['score']),
            'stress_score': stress['score'],
            'online': _is_online(db, pe),
            'unread': unread,
            'connected_at': conn.get('updated_at', conn['created_at']).isoformat(),
        })
    return jsonify({'peers': peers, 'total': len(peers)})


@connect_bp.route('/api/connect/requests')
@login_required
def get_pending_requests():
    db = get_db()
    email = session['user_email']
    incoming = list(db['connections'].find({'connected_to': email, 'status': 'pending'}).sort('created_at', -1))
    outgoing = list(db['connections'].find({'user_email': email, 'status': 'pending'}).sort('created_at', -1))

    def _enrich(conns, field):
        out = []
        for c in conns:
            pe = c[field]
            u = db['users'].find_one({'email': pe}, {'hashed_password': 0})
            out.append({
                'id': str(c['_id']), 'email': pe,
                'name': _full_name(db, pe),
                'department': u.get('department', '') if u else '',
                'created_at': c['created_at'].isoformat(),
            })
        return out

    return jsonify({
        'incoming': _enrich(incoming, 'user_email'),
        'outgoing': _enrich(outgoing, 'connected_to'),
    })


@connect_bp.route('/api/connect/request', methods=['POST'])
@login_required
@demo_restricted
def send_connection_request():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    target = (data.get('email') or '').strip().lower()

    if not target:
        return jsonify({'error': 'Email is required'}), 400
    if target == email:
        return jsonify({'error': 'Cannot connect to yourself'}), 400
    if not db['users'].find_one({'email': target}):
        return jsonify({'error': 'User not found'}), 404

    existing = db['connections'].find_one({
        '$or': [{'user_email': email, 'connected_to': target},
                {'user_email': target, 'connected_to': email}]
    })
    if existing:
        s = existing['status']
        if s == 'accepted': return jsonify({'error': 'Already connected'}), 409
        if s == 'pending': return jsonify({'error': 'Request already pending'}), 409
        if s == 'rejected':
            db['connections'].update_one({'_id': existing['_id']}, {'$set': {
                'user_email': email, 'connected_to': target,
                'status': 'pending', 'updated_at': datetime.utcnow()}})
            _notify(db, target, 'connection_request',
                    f'{_user_display_name(db, email)} wants to connect', link='peers')
            return jsonify({'message': 'Re-sent'})

    db['connections'].insert_one({
        'user_email': email, 'connected_to': target,
        'status': 'pending', 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow(),
    })
    _notify(db, target, 'connection_request',
            f'{_user_display_name(db, email)} wants to connect', link='peers')
    return jsonify({'message': 'Request sent'}), 201


@connect_bp.route('/api/connect/respond', methods=['POST'])
@login_required
@demo_restricted
def respond_to_connection():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    rid = data.get('request_id', '')
    action = data.get('action', '').lower()
    if action not in ('accept', 'reject'):
        return jsonify({'error': 'Action must be accept or reject'}), 400
    try:
        conn = db['connections'].find_one({'_id': ObjectId(rid), 'connected_to': email, 'status': 'pending'})
    except Exception:
        return jsonify({'error': 'Invalid ID'}), 400
    if not conn:
        return jsonify({'error': 'Not found'}), 404

    ns = 'accepted' if action == 'accept' else 'rejected'
    db['connections'].update_one({'_id': conn['_id']}, {'$set': {'status': ns, 'updated_at': datetime.utcnow()}})
    if ns == 'accepted':
        _log_hub_engagement(db, email, 'peer_connection')
        _log_hub_engagement(db, conn['user_email'], 'peer_connection')
        _post_feed(db, email, 'new_connection', _user_display_name(db, conn['user_email']))
        _notify(db, conn['user_email'], 'connection_accepted',
                f'{_user_display_name(db, email)} accepted your request', link='peers')
    return jsonify({'message': f'Connection {ns}', 'status': ns})


@connect_bp.route('/api/connect/suggestions')
@login_required
def get_suggestions():
    """AI-powered peer matching: stress correlation, trend alignment, shared groups,
       engagement compatibility, department affinity, mood pattern matching."""
    db = get_db()
    email = session['user_email']
    user = db['users'].find_one({'email': email})
    if not user:
        return jsonify({'suggestions': []})

    my_stress = _user_stress(db, email)
    my_dept = user.get('department', '')
    my_score, my_trend = my_stress['score'], my_stress['trend']

    # Gather user's group memberships for interest overlap
    my_groups = set()
    for g in db['groups'].find({'members': email}, {'group_id': 1, 'type': 1}):
        my_groups.add(g['group_id'])
    my_group_types = set()
    for g in db['groups'].find({'members': email}, {'type': 1}):
        my_group_types.add(g.get('type', ''))

    # Existing connections / pending
    existing = set()
    for c in db['connections'].find({'$or': [{'user_email': email}, {'connected_to': email}]}):
        existing.add(c.get('user_email', '')); existing.add(c.get('connected_to', ''))
    existing.discard(email)

    candidates = list(db['users'].find({
        'email': {'$ne': email, '$nin': list(existing)}, 'role': 'student',
    }, {'hashed_password': 0}).limit(60))

    suggestions = []
    for c in candidates:
        ce = c['email']
        cs = _user_stress(db, ce)
        cd = c.get('department', '')
        ai_score = 0; reasons = []

        # 1. Stress proximity (0-3 pts)
        diff = abs(my_score - cs['score'])
        if diff <= 10: ai_score += 3; reasons.append('Similar stress level')
        elif diff <= 20: ai_score += 1.5

        # 2. Trend alignment (0-2 pts): same direction = solidarity
        if my_trend == cs['trend'] and my_trend != 'stable':
            ai_score += 2; reasons.append(f'Both stress trending {my_trend}')
        elif my_trend == 'up' and cs['trend'] == 'down':
            ai_score += 1; reasons.append('Complementary support')

        # 3. Department affinity (0-2 pts)
        if my_dept and cd and my_dept.lower() == cd.lower():
            ai_score += 2; reasons.append('Same department')

        # 4. Shared group types = shared interests (0-2 pts)
        c_group_types = set()
        for g in db['groups'].find({'members': ce}, {'type': 1}):
            c_group_types.add(g.get('type', ''))
        overlap = my_group_types & c_group_types
        if overlap:
            ai_score += min(len(overlap), 2); reasons.append('Shared interests')

        # 5. Engagement compatibility (0-1 pt): both active or both new
        c_activity = db['hub_activity'].find_one({'user_email': ce})
        c_msg_count = c_activity.get('message_count', 0) if c_activity else 0
        my_activity = db['hub_activity'].find_one({'user_email': email})
        my_msg_count = my_activity.get('message_count', 0) if my_activity else 0
        if abs(c_msg_count - my_msg_count) < 10:
            ai_score += 1; reasons.append('Similar engagement')

        # 6. Online bonus (0-1 pt)
        online = _is_online(db, ce)
        if online: ai_score += 1

        # 7. High-stress solidarity bonus (0-1 pt)
        if my_score > 60 and cs['score'] > 60:
            ai_score += 1
            if 'Similar stress level' not in reasons:
                reasons.append('May benefit from mutual support')

        if ai_score >= 1:
            suggestions.append({
                'email': ce, 'name': c.get('name', ce.split('@')[0]),
                'department': cd, 'stress_level': _stress_label(cs['score']),
                'online': online, 'match_score': round(ai_score, 1), 'reasons': reasons[:4],
            })
    suggestions.sort(key=lambda x: (-x['match_score'], -x['online']))
    return jsonify({'suggestions': suggestions[:12]})


@connect_bp.route('/api/connect/remove', methods=['POST'])
@login_required
@demo_restricted
def remove_connection():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    pe = (data.get('email') or '').strip().lower()
    if not pe: return jsonify({'error': 'Email required'}), 400
    r = db['connections'].delete_one({'$or': [
        {'user_email': email, 'connected_to': pe, 'status': 'accepted'},
        {'user_email': pe, 'connected_to': email, 'status': 'accepted'},
    ]})
    if r.deleted_count == 0: return jsonify({'error': 'Not found'}), 404
    return jsonify({'message': 'Removed'})


# ═══════════════════════════════════════════════════════════════════════════════
#  2. GROUPS
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/groups')
@login_required
def get_groups():
    db = get_db()
    email = session['user_email']
    _heartbeat(db, email)
    gt = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    query = {}
    if gt in ('study', 'relaxation', 'peer_support'): query['type'] = gt

    groups = list(_paginate(db['groups'].find(query).sort('created_at', -1), page, 20))
    result = []
    for g in groups:
        last_msg = db['group_messages'].find_one({'group_id': g['group_id']}, sort=[('created_at', -1)])
        result.append({
            'group_id': g['group_id'], 'name': g['name'],
            'description': g.get('description', ''), 'type': g['type'],
            'created_by': g['created_by'],
            'member_count': g.get('member_count', len(g.get('members', []))),
            'max_members': 20,
            'is_member': email in g.get('members', []),
            'last_message': last_msg.get('message', '')[:60] if last_msg else '',
            'last_message_by': last_msg.get('sender_name', '') if last_msg else '',
            'created_at': g['created_at'].isoformat(),
        })
    total = db['groups'].count_documents(query)
    return jsonify({'groups': result, 'total': total, 'page': page})


@connect_bp.route('/api/groups/create', methods=['POST'])
@login_required
@demo_restricted
def create_group():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    desc = (data.get('description') or '').strip()
    gtype = (data.get('type') or '').strip().lower()

    if not name or len(name) < 3: return jsonify({'error': 'Name min 3 chars'}), 400
    if len(name) > 60: return jsonify({'error': 'Name too long'}), 400
    if _profanity_check(name) or _profanity_check(desc):
        return jsonify({'error': 'Inappropriate content in name or description'}), 400
    if gtype not in ('study', 'relaxation', 'peer_support'):
        stress = _user_stress(db, email)
        gtype = 'relaxation' if stress['score'] > 75 else 'peer_support' if stress['score'] > 50 else 'study'
    if len(desc) > 500: return jsonify({'error': 'Description too long'}), 400
    if db['groups'].find_one({'name': {'$regex': f'^{re.escape(name)}$', '$options': 'i'}}):
        return jsonify({'error': 'Name already exists'}), 409

    gid = str(uuid.uuid4()); now = datetime.utcnow()
    db['groups'].insert_one({
        'group_id': gid, 'name': name, 'description': desc, 'type': gtype,
        'created_by': email, 'members': [email], 'member_count': 1,
        'created_at': now, 'updated_at': now,
    })
    _log_hub_engagement(db, email, 'group_created')
    _post_feed(db, email, 'created_group', name)
    return jsonify({'message': 'Group created', 'group_id': gid, 'type': gtype}), 201


@connect_bp.route('/api/groups/join', methods=['POST'])
@login_required
@demo_restricted
def join_group():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    gid = data.get('group_id', '')
    if not gid: return jsonify({'error': 'Group ID required'}), 400
    g = db['groups'].find_one({'group_id': gid})
    if not g: return jsonify({'error': 'Not found'}), 404
    if email in g.get('members', []): return jsonify({'error': 'Already member'}), 409
    if len(g.get('members', [])) >= 20: return jsonify({'error': 'Full'}), 409
    result = db['groups'].update_one(
        {'group_id': gid, 'members': {'$ne': email}, '$expr': {'$lt': [{'$size': '$members'}, 20]}},
        {'$addToSet': {'members': email}, '$set': {'updated_at': datetime.utcnow()}}
    )
    if result.modified_count == 0: return jsonify({'error': 'Already member or full'}), 409
    # Sync member_count from actual array
    g2 = db['groups'].find_one({'group_id': gid})
    if g2:
        db['groups'].update_one({'group_id': gid}, {'$set': {'member_count': len(g2.get('members', []))}})
    _log_hub_engagement(db, email, 'group_joined')
    _post_feed(db, email, 'joined_group', g['name'])
    return jsonify({'message': f'Joined "{g["name"]}"'})


@connect_bp.route('/api/groups/leave', methods=['POST'])
@login_required
@demo_restricted
def leave_group():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    gid = data.get('group_id', '')
    if not gid: return jsonify({'error': 'Group ID required'}), 400
    g = db['groups'].find_one({'group_id': gid})
    if not g: return jsonify({'error': 'Not found'}), 404
    if email not in g.get('members', []): return jsonify({'error': 'Not a member'}), 400
    db['groups'].update_one({'group_id': gid}, {
        '$pull': {'members': email},
        '$set': {'updated_at': datetime.utcnow()},
    })
    # Sync member_count from actual array
    g2 = db['groups'].find_one({'group_id': gid})
    if g2:
        db['groups'].update_one({'group_id': gid}, {'$set': {'member_count': len(g2.get('members', []))}})
    return jsonify({'message': f'Left "{g["name"]}"'})


@connect_bp.route('/api/groups/<group_id>/members')
@login_required
def group_members(group_id):
    db = get_db()
    g = db['groups'].find_one({'group_id': group_id})
    if not g: return jsonify({'error': 'Not found'}), 404
    members = []
    for me in g.get('members', []):
        members.append({'email': me, 'name': _full_name(db, me), 'online': _is_online(db, me)})
    return jsonify({'members': members})


# ═══════════════════════════════════════════════════════════════════════════════
#  3. EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/events')
@login_required
def get_events():
    db = get_db()
    email = session['user_email']
    _heartbeat(db, email)
    et = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    query = {'date': {'$gte': datetime.utcnow()}}
    if et in ('webinar', 'meditation', 'workshop'): query['type'] = et
    events = list(_paginate(db['events'].find(query).sort('date', 1), page, 20))
    result = []
    for ev in events:
        result.append({
            'event_id': ev['event_id'], 'title': ev['title'],
            'description': ev.get('description', ''), 'date': ev['date'].isoformat(),
            'duration_minutes': ev.get('duration_minutes', 60), 'type': ev['type'],
            'participant_count': len(ev.get('participants', [])),
            'max_participants': ev.get('max_participants', 100),
            'is_registered': email in ev.get('participants', []),
        })
    total = db['events'].count_documents(query)
    return jsonify({'events': result, 'total': total, 'page': page})


@connect_bp.route('/api/events/create', methods=['POST'])
@login_required
@demo_restricted
def create_event():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    desc = (data.get('description') or '').strip()[:500]
    et = (data.get('type') or '').strip().lower()
    date_str = data.get('date', '')
    dur = data.get('duration_minutes', 60)

    if not title or len(title) < 3: return jsonify({'error': 'Title min 3 chars'}), 400
    if et not in ('webinar', 'meditation', 'workshop'): return jsonify({'error': 'Invalid type'}), 400
    if _profanity_check(title) or _profanity_check(desc):
        return jsonify({'error': 'Inappropriate content in title or description'}), 400
    try: event_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception: return jsonify({'error': 'Invalid date'}), 400
    if event_date < datetime.utcnow(): return jsonify({'error': 'Must be future'}), 400

    eid = str(uuid.uuid4())
    db['events'].insert_one({
        'event_id': eid, 'title': title, 'description': desc,
        'date': event_date, 'duration_minutes': min(max(15, int(dur)), 480),
        'type': et, 'created_by': email, 'participants': [email],
        'max_participants': 100, 'created_at': datetime.utcnow(),
    })
    _log_hub_engagement(db, email, 'event_created')
    _post_feed(db, email, 'created_event', title)
    return jsonify({'message': 'Event created', 'event_id': eid}), 201


@connect_bp.route('/api/events/rsvp', methods=['POST'])
@login_required
@demo_restricted
def rsvp_event():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    eid = data.get('event_id', '')
    if not eid: return jsonify({'error': 'ID required'}), 400
    ev = db['events'].find_one({'event_id': eid})
    if not ev: return jsonify({'error': 'Not found'}), 404
    if email in ev.get('participants', []): return jsonify({'error': 'Already registered'}), 409
    if len(ev.get('participants', [])) >= ev.get('max_participants', 100):
        return jsonify({'error': 'Full'}), 409
    db['events'].update_one({'event_id': eid}, {'$addToSet': {'participants': email}})
    _log_hub_engagement(db, email, 'event_rsvp')
    _post_feed(db, email, 'rsvp_event', ev['title'])
    return jsonify({'message': f'Registered for "{ev["title"]}"'})


@connect_bp.route('/api/events/cancel', methods=['POST'])
@login_required
@demo_restricted
def cancel_rsvp():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    eid = data.get('event_id', '')
    if not eid: return jsonify({'error': 'ID required'}), 400
    ev = db['events'].find_one({'event_id': eid})
    if not ev: return jsonify({'error': 'Not found'}), 404
    if email not in ev.get('participants', []): return jsonify({'error': 'Not registered'}), 400
    db['events'].update_one({'event_id': eid}, {'$pull': {'participants': email}})
    return jsonify({'message': 'Cancelled'})


@connect_bp.route('/api/events/<event_id>/ics')
@login_required
def export_ics(event_id):
    db = get_db()
    ev = db['events'].find_one({'event_id': event_id})
    if not ev: return jsonify({'error': 'Not found'}), 404
    dt_s = ev['date']
    dt_e = dt_s + timedelta(minutes=ev.get('duration_minutes', 60))
    # Sanitize for ICS: strip CRLF to prevent injection of iCalendar components
    safe_title = re.sub(r'[\r\n]+', ' ', ev['title'])[:200]
    safe_desc  = re.sub(r'[\r\n]+', ' ', ev.get('description', ''))[:200]
    ics = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//AURA//ConnectHub//EN\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{ev['event_id']}@aura\r\nDTSTART:{dt_s.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        f"DTEND:{dt_e.strftime('%Y%m%dT%H%M%SZ')}\r\nSUMMARY:{safe_title}\r\n"
        f"DESCRIPTION:{safe_desc}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    return Response(ics, mimetype='text/calendar',
                    headers={'Content-Disposition': f'attachment; filename={event_id}.ics'})


@connect_bp.route('/api/events/delete-all', methods=['POST'])
@login_required
@demo_restricted
def delete_all_events():
    db = get_db()
    email = session['user_email']
    result = db['events'].delete_many({})
    _log_hub_engagement(db, email, 'events_cleared')
    return jsonify({'message': f'Deleted {result.deleted_count} events'}), 200


# ═══════════════════════════════════════════════════════════════════════════════
#  4. RESOURCES
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/resources')
@login_required
def get_resources():
    db = get_db()
    email = session['user_email']
    _heartbeat(db, email)
    tag = request.args.get('tag', '')
    sort_by = request.args.get('sort', 'recent')
    page = request.args.get('page', 1, type=int)
    query = {}
    if tag: query['tags'] = tag.lower()
    sf = ('likes', -1) if sort_by == 'popular' else ('created_at', -1)
    resources = list(_paginate(db['resources'].find(query).sort(*sf), page, 20))
    result = []
    for r in resources:
        result.append({
            'resource_id': r['resource_id'], 'title': r['title'],
            'link': r.get('link', ''), 'description': r.get('description', ''),
            'uploaded_by': r['uploaded_by'], 'tags': r.get('tags', []),
            'likes': r.get('likes', 0), 'liked_by_me': email in r.get('liked_by', []),
            'created_at': r['created_at'].isoformat(),
        })
    total = db['resources'].count_documents(query)
    return jsonify({'resources': result, 'total': total, 'page': page})


@connect_bp.route('/api/resources', methods=['POST'])
@login_required
@demo_restricted
def share_resource():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    link = _sanitize_url(data.get('link') or '')
    desc = (data.get('description') or '').strip()[:500]
    tags = data.get('tags', [])
    if not title or len(title) < 3: return jsonify({'error': 'Title min 3 chars'}), 400
    if not link: return jsonify({'error': 'Valid URL required'}), 400
    if _profanity_check(title) or _profanity_check(desc):
        return jsonify({'error': 'Inappropriate content in title or description'}), 400
    clean_tags = [t.strip().lower()[:30] for t in tags if t.strip()][:10]
    rid = str(uuid.uuid4())
    db['resources'].insert_one({
        'resource_id': rid, 'title': title, 'link': link, 'description': desc,
        'uploaded_by': email, 'tags': clean_tags, 'likes': 0, 'liked_by': [],
        'created_at': datetime.utcnow(),
    })
    _log_hub_engagement(db, email, 'resource_shared')
    _post_feed(db, email, 'shared_resource', title)
    return jsonify({'message': 'Shared', 'resource_id': rid}), 201


@connect_bp.route('/api/resources/like', methods=['POST'])
@login_required
@demo_restricted
def like_resource():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    rid = data.get('resource_id', '')
    if not rid: return jsonify({'error': 'ID required'}), 400
    r = db['resources'].find_one({'resource_id': rid})
    if not r: return jsonify({'error': 'Not found'}), 404
    if email in r.get('liked_by', []):
        db['resources'].update_one({'resource_id': rid}, {'$pull': {'liked_by': email}})
        r2 = db['resources'].find_one({'resource_id': rid})
        new_likes = len(r2.get('liked_by', [])) if r2 else 0
        db['resources'].update_one({'resource_id': rid}, {'$set': {'likes': new_likes}})
        return jsonify({'likes': new_likes, 'liked': False})
    else:
        db['resources'].update_one({'resource_id': rid}, {'$addToSet': {'liked_by': email}})
        r2 = db['resources'].find_one({'resource_id': rid})
        new_likes = len(r2.get('liked_by', [])) if r2 else 0
        db['resources'].update_one({'resource_id': rid}, {'$set': {'likes': new_likes}})
        return jsonify({'likes': new_likes, 'liked': True})


# ═══════════════════════════════════════════════════════════════════════════════
#  5. DIRECT CHAT (Peer-to-Peer — polling)
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/chat/dm/<peer_email>')
@login_required
def get_dm_messages(peer_email):
    db = get_db()
    email = session['user_email']
    _heartbeat(db, email)
    if not _are_connected(db, email, peer_email):
        return jsonify({'error': 'Not connected'}), 403

    db['peer_messages'].update_many(
        {'from_email': peer_email, 'to_email': email, 'seen': False},
        {'$set': {'seen': True}})

    msgs = list(db['peer_messages'].find({
        '$or': [{'from_email': email, 'to_email': peer_email},
                {'from_email': peer_email, 'to_email': email}]
    }).sort('created_at', -1).limit(50))
    msgs.reverse()

    return jsonify({'messages': [{
        'id': str(m['_id']), 'from': m['from_email'], 'to': m['to_email'],
        'message': m['message'], 'mine': m['from_email'] == email,
        'seen': m.get('seen', False), 'time': m['created_at'].isoformat(),
    } for m in msgs]})


@connect_bp.route('/api/chat/dm/<peer_email>/send', methods=['POST'])
@login_required
@demo_restricted
def send_dm(peer_email):
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    text = (data.get('message') or '').strip()
    if not text: return jsonify({'error': 'Empty'}), 400
    if len(text) > 500: return jsonify({'error': 'Too long'}), 400
    if not _are_connected(db, email, peer_email): return jsonify({'error': 'Not connected'}), 403
    if _profanity_check(text): return jsonify({'error': 'Inappropriate content'}), 400
    if not _chat_rate_ok(db, email): return jsonify({'error': 'Slow down'}), 429

    db['peer_messages'].insert_one({
        'from_email': email, 'to_email': peer_email,
        'message': text, 'seen': False, 'created_at': datetime.utcnow(),
    })
    _record_chat_ts(db, email)
    _log_hub_engagement(db, email, 'dm_sent')
    _notify(db, peer_email, 'message',
            f'Message from {_user_display_name(db, email)}',
            body=text[:80], link='peers')
    return jsonify({'message': 'Sent'})


@connect_bp.route('/api/chat/dm/unread')
@login_required
def dm_unread_counts():
    db = get_db()
    email = session['user_email']
    pipeline = [
        {'$match': {'to_email': email, 'seen': False}},
        {'$group': {'_id': '$from_email', 'count': {'$sum': 1}}},
    ]
    counts = {r['_id']: r['count'] for r in db['peer_messages'].aggregate(pipeline)}
    return jsonify({'unread': counts})


# ═══════════════════════════════════════════════════════════════════════════════
#  6. GROUP CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/chat/group/<group_id>')
@login_required
def get_group_messages(group_id):
    db = get_db()
    email = session['user_email']
    _heartbeat(db, email)
    g = db['groups'].find_one({'group_id': group_id})
    if not g: return jsonify({'error': 'Not found'}), 404
    if email not in g.get('members', []): return jsonify({'error': 'Not a member'}), 403
    msgs = list(db['group_messages'].find({'group_id': group_id}).sort('created_at', -1).limit(50))
    msgs.reverse()
    return jsonify({'messages': [{
        'id': str(m['_id']), 'sender': m['sender_email'],
        'sender_name': m.get('sender_name', m['sender_email'].split('@')[0]),
        'message': m['message'], 'mine': m['sender_email'] == email,
        'time': m['created_at'].isoformat(),
    } for m in msgs], 'group_name': g['name']})


@connect_bp.route('/api/chat/group/<group_id>/send', methods=['POST'])
@login_required
@demo_restricted
def send_group_message(group_id):
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    text = (data.get('message') or '').strip()
    if not text: return jsonify({'error': 'Empty'}), 400
    if len(text) > 500: return jsonify({'error': 'Too long'}), 400
    g = db['groups'].find_one({'group_id': group_id})
    if not g: return jsonify({'error': 'Not found'}), 404
    if email not in g.get('members', []): return jsonify({'error': 'Not a member'}), 403
    if _profanity_check(text): return jsonify({'error': 'Inappropriate'}), 400
    if not _chat_rate_ok(db, email): return jsonify({'error': 'Slow down'}), 429

    db['group_messages'].insert_one({
        'group_id': group_id, 'sender_email': email,
        'sender_name': _user_display_name(db, email),
        'message': text, 'created_at': datetime.utcnow(),
    })
    _record_chat_ts(db, email)
    _log_hub_engagement(db, email, 'group_chat')
    return jsonify({'message': 'Sent'})


# ═══════════════════════════════════════════════════════════════════════════════
#  7. ACTIVITY FEED
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/connect-hub/feed')
@login_required
def get_feed():
    db = get_db()
    items = list(db['hub_feed'].find().sort('created_at', -1).limit(20))
    verbs = {
        'joined_group': 'joined', 'created_group': 'created group',
        'created_event': 'created event', 'rsvp_event': 'registered for',
        'shared_resource': 'shared', 'new_connection': 'connected with',
    }
    icons = {
        'joined_group': '👥', 'created_group': '🆕', 'created_event': '📅',
        'rsvp_event': '✋', 'shared_resource': '📚', 'new_connection': '🤝',
    }
    feed = []
    for i in items:
        v = verbs.get(i['action'], i['action'])
        feed.append({
            'icon': icons.get(i['action'], '🔔'),
            'text': f"{i['actor_name']} {v} {i.get('target','')}".strip(),
            'time': i['created_at'].isoformat(), 'action': i['action'],
        })
    return jsonify({'feed': feed})


# ═══════════════════════════════════════════════════════════════════════════════
#  8. NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/connect-hub/notifications')
@login_required
def get_notifications():
    db = get_db()
    email = session['user_email']
    notifs = list(db['hub_notifications'].find({'user_email': email}).sort('created_at', -1).limit(20))
    return jsonify({
        'notifications': [{
            'id': str(n['_id']), 'type': n['type'], 'title': n['title'],
            'body': n.get('body', ''), 'read': n.get('read', False),
            'link': n.get('link', ''), 'time': n['created_at'].isoformat(),
        } for n in notifs],
        'unread_count': db['hub_notifications'].count_documents({'user_email': email, 'read': False}),
    })


@connect_bp.route('/api/connect-hub/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    db = get_db()
    email = session['user_email']
    data = request.get_json(silent=True) or {}
    nid = data.get('id')
    if nid == 'all':
        db['hub_notifications'].update_many({'user_email': email, 'read': False}, {'$set': {'read': True}})
    elif nid:
        try:
            db['hub_notifications'].update_one({'_id': ObjectId(nid), 'user_email': email}, {'$set': {'read': True}})
        except Exception as e:
            current_app.logger.warning(f"Failed to mark notification as read: {e}")
    return jsonify({'message': 'OK'})


# ═══════════════════════════════════════════════════════════════════════════════
#  9. STATS + RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@connect_bp.route('/api/connect-hub/stats')
@login_required
def hub_stats():
    db = get_db()
    email = session['user_email']
    _heartbeat(db, email)
    ten_min = datetime.utcnow() - timedelta(minutes=10)
    return jsonify({
        'active_now': db['hub_activity'].count_documents({'last_active': {'$gte': ten_min}}),
        'groups': db['groups'].count_documents({}),
        'events': db['events'].count_documents({'date': {'$gte': datetime.utcnow()}}),
        'connected_users': db['connections'].count_documents({
            '$or': [{'user_email': email, 'status': 'accepted'},
                    {'connected_to': email, 'status': 'accepted'}]}),
        'pending_requests': db['connections'].count_documents({'connected_to': email, 'status': 'pending'}),
        'my_groups': db['groups'].count_documents({'members': email}),
        'total_resources': db['resources'].count_documents({}),
        'unread_notifications': db['hub_notifications'].count_documents({'user_email': email, 'read': False}),
    })


@connect_bp.route('/api/connect-hub/recommendations')
@login_required
def get_recommendations():
    """AI-powered contextual recommendations: stress-aware, engagement-decay detection,
       temporal pattern analysis, mood-correlated event suggestions."""
    db = get_db()
    email = session['user_email']
    stress = _user_stress(db, email)
    score, trend, conf = stress['score'], stress['trend'], stress['confidence']
    recs = []

    # ── 1. High-stress → peer support groups ──
    if score > 70:
        for g in db['groups'].find({'type': 'peer_support', 'members': {'$ne': email},
                                     '$expr': {'$lt': [{'$size': '$members'}, 20]}}).limit(3):
            recs.append({'type': 'group', 'priority': 'high', 'title': f'Join "{g["name"]}"',
                         'description': 'Peer support is most effective during high-stress periods.',
                         'action': 'join_group', 'action_data': {'group_id': g['group_id']}, 'icon': 'users'})

    # ── 2. Trending up or moderate stress → calming events ──
    if trend == 'up' or score > 55:
        for ev in db['events'].find({'date': {'$gte': datetime.utcnow()}, 'participants': {'$ne': email},
                                      'type': {'$in': ['meditation', 'workshop']}}).sort('date', 1).limit(3):
            recs.append({'type': 'event', 'priority': 'medium', 'title': f'Attend "{ev["title"]}"',
                         'description': f'{ev["type"].title()} · {ev["date"].strftime("%b %d, %I:%M %p")}',
                         'action': 'rsvp_event', 'action_data': {'event_id': ev['event_id']}, 'icon': 'calendar'})

    # ── 3. Low confidence → encourage engagement ──
    if conf < 0.4:
        recs.append({'type': 'engagement', 'priority': 'low', 'title': 'Connect with more peers',
                     'description': 'Building your network improves AURA\'s ability to support you.',
                     'action': 'view_suggestions', 'action_data': {}, 'icon': 'heart'})

    # ── 4. Moderate stress → relaxation groups ──
    if 50 < score <= 70:
        for g in db['groups'].find({'type': 'relaxation', 'members': {'$ne': email}}).limit(2):
            recs.append({'type': 'group', 'priority': 'medium', 'title': f'Try "{g["name"]}"',
                         'description': 'Guided relaxation for stress management.',
                         'action': 'join_group', 'action_data': {'group_id': g['group_id']}, 'icon': 'wind'})

    # ── 5. Engagement decay: no DMs in 3+ days → nudge ──
    three_days = datetime.utcnow() - timedelta(days=3)
    last_msg = db['peer_messages'].find_one(
        {'$or': [{'from_email': email}, {'to_email': email}]},
        sort=[('created_at', -1)])
    if not last_msg or last_msg.get('created_at', datetime.min) < three_days:
        connected = db['connections'].find_one({
            '$or': [{'user_email': email, 'status': 'accepted'},
                    {'connected_to': email, 'status': 'accepted'}]})
        if connected:
            peer = connected.get('connected_to') if connected.get('user_email') == email else connected.get('user_email')
            peer_name = _user_display_name(db, peer)
            recs.append({'type': 'reconnect', 'priority': 'medium',
                         'title': f'Reconnect with {peer_name}',
                         'description': 'Regular check-ins strengthen peer networks.',
                         'action': 'view_suggestions', 'action_data': {}, 'icon': 'heart'})

    # ── 6. Study groups for stable/low-stress users ──
    if score <= 45 and trend in ('stable', 'down'):
        for g in db['groups'].find({'type': 'study', 'members': {'$ne': email},
                                     '$expr': {'$lt': [{'$size': '$members'}, 20]}}).limit(2):
            recs.append({'type': 'group', 'priority': 'low', 'title': f'Study: "{g["name"]}"',
                         'description': 'Good time to build academic connections while stress is low.',
                         'action': 'join_group', 'action_data': {'group_id': g['group_id']}, 'icon': 'users'})

    # ── 7. Upcoming events within 24h → urgency boost ──
    tomorrow = datetime.utcnow() + timedelta(hours=24)
    soon_events = list(db['events'].find({
        'date': {'$gte': datetime.utcnow(), '$lte': tomorrow},
        'participants': {'$ne': email},
    }).sort('date', 1).limit(2))
    for ev in soon_events:
        # Don't duplicate if already in list
        if not any(r.get('action_data', {}).get('event_id') == ev['event_id'] for r in recs):
            recs.append({'type': 'event', 'priority': 'high', 'title': f'Starting soon: "{ev["title"]}"',
                         'description': f'In {max(1, int((ev["date"] - datetime.utcnow()).total_seconds() / 3600))}h · {ev.get("participant_count", 0)} attending',
                         'action': 'rsvp_event', 'action_data': {'event_id': ev['event_id']}, 'icon': 'calendar'})

    po = {'high': 0, 'medium': 1, 'low': 2}
    recs.sort(key=lambda r: po.get(r['priority'], 3))
    return jsonify({'recommendations': recs[:6], 'stress_score': score, 'stress_trend': trend, 'confidence': conf})
