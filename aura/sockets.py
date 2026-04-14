import logging
from flask import session as s
from flask_socketio import emit, join_room, leave_room
from aura import socketio
from aura.utils.database import get_db
from aura.utils.content_filter import contains_blocked_content, sanitize_message
from aura.services.otp_timer_service import OTPTimerService
from datetime import datetime

log = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect():
    """Client connected."""
    email = s.get('user_email')
    role = s.get('user_role', '')
    if email:
        join_room(email)
        join_room('hub_global')
        if role in ('proctor', 'hod'):
            join_room('proctor_alerts')
        try:
            db = get_db()
            db['hub_activity'].update_one(
                {'user_email': email},
                {'$set': {'user_email': email, 'last_active': datetime.utcnow()}},
                upsert=True)
            emit('online_update', {'email': email, 'online': True}, room='hub_global')
        except Exception:
            pass

@socketio.on('disconnect')
def handle_disconnect():
    email = s.get('user_email')
    role = s.get('user_role', '')
    if email:
        leave_room(email)
        leave_room('hub_global')
        if role in ('proctor', 'hod'):
            leave_room('proctor_alerts')
        emit('online_update', {'email': email, 'online': False}, room='hub_global')

@socketio.on('join_group_room')
def handle_join_group(data):
    gid = data.get('group_id', '')
    if gid:
        join_room(f'group_{gid}')

@socketio.on('leave_group_room')
def handle_leave_group(data):
    gid = data.get('group_id', '')
    if gid:
        leave_room(f'group_{gid}')

@socketio.on('typing')
def handle_typing(data):
    email = s.get('user_email', '')
    name = s.get('user_name', email.split('@')[0])
    target_type = data.get('type', 'dm')
    target = data.get('target', '')
    if target_type == 'dm' and target:
        emit('typing_indicator', {'from': email, 'name': name, 'type': 'dm'}, room=target)
    elif target_type == 'group' and target:
        emit('typing_indicator', {'from': email, 'name': name, 'type': 'group', 'group_id': target}, room=f'group_{target}', include_self=False)

@socketio.on('send_dm')
def handle_send_dm(data):
    email = s.get('user_email', '')
    if not email: return
    peer = data.get('to', '')
    raw_text = (data.get('message', '') or '').strip()
    if not raw_text or len(raw_text) > 500 or not peer: return

    text = sanitize_message(raw_text)
    if text is None: return

    if contains_blocked_content(raw_text):
        emit('dm_error', {'error': 'Inappropriate content'})
        return

    db = get_db()
    conn = db['connections'].find_one({'$or': [
        {'user_email': email, 'connected_to': peer, 'status': 'accepted'},
        {'user_email': peer, 'connected_to': email, 'status': 'accepted'},
    ]})
    if not conn:
        emit('dm_error', {'error': 'Not connected'})
        return

    now = datetime.utcnow()
    db['peer_messages'].insert_one({
        'from_email': email, 'to_email': peer,
        'message': text, 'seen': False, 'created_at': now,
    })

    name = (s.get('user_name') or email.split('@')[0] or 'User').split()[0]
    payload = {
        'from': email, 'to': peer, 'message': text,
        'sender_name': name, 'mine': False, 'seen': False,
        'time': now.isoformat(),
    }
    emit('new_dm', payload, room=peer)
    emit('new_dm', {**payload, 'mine': True}, room=email)

@socketio.on('send_group_msg')
def handle_send_group_msg(data):
    email = s.get('user_email', '')
    if not email: return
    gid = data.get('group_id', '')
    raw_text = (data.get('message', '') or '').strip()
    if not raw_text or len(raw_text) > 500 or not gid: return

    text = sanitize_message(raw_text)
    if text is None: return

    if contains_blocked_content(raw_text):
        emit('group_error', {'error': 'Inappropriate content'})
        return

    db = get_db()
    g = db['groups'].find_one({'group_id': gid})
    if not g or email not in g.get('members', []):
        emit('group_error', {'error': 'Not a member'})
        return

    now = datetime.utcnow()
    name = (s.get('user_name') or email.split('@')[0] or 'User').split()[0]
    db['group_messages'].insert_one({
        'group_id': gid, 'sender_email': email,
        'sender_name': name, 'message': text, 'created_at': now,
    })

    emit('new_group_msg', {
        'group_id': gid, 'sender': email, 'sender_name': name,
        'message': text, 'time': now.isoformat(),
    }, room=f'group_{gid}')

@socketio.on('otp_countdown_start')
def handle_otp_countdown_start(data):
    phone = data.get('phone', '').strip()
    if not phone:
        emit('error', {'msg': 'Phone number required'})
        return
    room_name = f'otp_{phone[-4:] if len(phone) >= 4 else phone}'
    join_room(room_name)
    remaining = OTPTimerService.get_remaining_seconds(phone)
    emit('otp_timer_tick', {'seconds_remaining': remaining or 0, 'expired': remaining is None})

@socketio.on('otp_countdown_stop')
def handle_otp_countdown_stop(data):
    phone = data.get('phone', '').strip()
    if phone:
        room_name = f'otp_{phone[-4:] if len(phone) >= 4 else phone}'
        leave_room(room_name)

def emit_proctor_alert(alert_data):
    """Utility to emit proctor alerts."""
    try:
        socketio.emit('proctor_alert', alert_data, room='proctor_alerts')
    except Exception as e:
        log.error('Failed to emit proctor alert: %s', e)
