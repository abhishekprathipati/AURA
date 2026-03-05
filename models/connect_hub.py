"""
Connect Hub Models — MongoDB schema definitions for the social wellness module.

Collections:
    connections     — Peer-to-peer connection requests/statuses
    groups          — Study / relaxation / peer-support group rooms
    events          — Structured wellness activities (webinars, meditation, workshops)
    resources       — Shared learning & wellness resources with likes
    hub_activity    — User heartbeat for "active now" tracking
    peer_messages   — Direct 1-to-1 chat messages
    group_messages  — Group chat messages
    hub_feed        — Community activity feed (joins, creates, milestones)
    hub_notifications — Per-user notification queue
"""

from typing import Dict, Any, List
from datetime import datetime


class ConnectionModel:
    """Peer connection request schema."""
    collection_name = 'connections'

    STATUSES = ('pending', 'accepted', 'rejected')

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'user_email': str,         # sender
            'connected_to': str,       # recipient
            'status': str,             # pending | accepted | rejected
            'created_at': datetime,
            'updated_at': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            ('user_email', 1),
            ('connected_to', 1),
            [('user_email', 1), ('connected_to', 1)],  # compound unique
            ('status', 1),
        ]

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        if not doc.get('user_email') or not doc.get('connected_to'):
            raise ValueError('Both user_email and connected_to are required')
        if doc['user_email'] == doc['connected_to']:
            raise ValueError('Cannot connect to yourself')
        if doc.get('status') not in ConnectionModel.STATUSES:
            raise ValueError(f'Status must be one of {ConnectionModel.STATUSES}')


class GroupModel:
    """Wellness & study group schema."""
    collection_name = 'groups'

    TYPES = ('study', 'relaxation', 'peer_support')
    MAX_MEMBERS = 20

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'group_id': str,           # UUID
            'name': str,
            'description': str,
            'type': str,               # study | relaxation | peer_support
            'created_by': str,         # email
            'members': list,           # list of emails
            'member_count': int,
            'created_at': datetime,
            'updated_at': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            ('group_id', 1),
            ('type', 1),
            ('members', 1),
            ('created_at', -1),
        ]

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        if not doc.get('name') or len(doc['name'].strip()) < 3:
            raise ValueError('Group name must be at least 3 characters')
        if len(doc.get('name', '')) > 60:
            raise ValueError('Group name must be at most 60 characters')
        if doc.get('type') not in GroupModel.TYPES:
            raise ValueError(f'Group type must be one of {GroupModel.TYPES}')
        if len(doc.get('description', '')) > 500:
            raise ValueError('Description must be at most 500 characters')


class EventModel:
    """Structured wellness events schema."""
    collection_name = 'events'

    TYPES = ('webinar', 'meditation', 'workshop')

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'event_id': str,           # UUID
            'title': str,
            'description': str,
            'date': datetime,
            'duration_minutes': int,
            'type': str,               # webinar | meditation | workshop
            'created_by': str,         # email (admin/proctor)
            'participants': list,      # list of emails
            'max_participants': int,
            'created_at': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            ('event_id', 1),
            ('date', 1),
            ('type', 1),
            ('participants', 1),
        ]

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        if not doc.get('title') or len(doc['title'].strip()) < 3:
            raise ValueError('Event title must be at least 3 characters')
        if len(doc.get('title', '')) > 100:
            raise ValueError('Event title must be at most 100 characters')
        if doc.get('type') not in EventModel.TYPES:
            raise ValueError(f'Event type must be one of {EventModel.TYPES}')


class ResourceModel:
    """Shared resource schema."""
    collection_name = 'resources'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'resource_id': str,        # UUID
            'title': str,
            'link': str,
            'description': str,
            'uploaded_by': str,        # email
            'tags': list,              # list of strings
            'likes': int,
            'liked_by': list,          # list of emails (prevent double-like)
            'created_at': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            ('resource_id', 1),
            ('tags', 1),
            ('created_at', -1),
            ('likes', -1),
        ]

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        if not doc.get('title') or len(doc['title'].strip()) < 3:
            raise ValueError('Resource title must be at least 3 characters')
        if len(doc.get('title', '')) > 120:
            raise ValueError('Resource title must be at most 120 characters')
        link = doc.get('link', '')
        if link and not (link.startswith('http://') or link.startswith('https://')):
            raise ValueError('Resource link must start with http:// or https://')
        if len(doc.get('tags', [])) > 10:
            raise ValueError('Maximum 10 tags allowed')


class HubActivityModel:
    """Heartbeat tracking for "active now" counts."""
    collection_name = 'hub_activity'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'user_email': str,
            'last_active': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            ('user_email', 1),
            ('last_active', 1),
        ]


# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class PeerMessageModel:
    """Direct 1-to-1 chat messages between connected peers."""
    collection_name = 'peer_messages'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'from_email': str,
            'to_email': str,
            'message': str,
            'seen': bool,
            'created_at': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            [('from_email', 1), ('to_email', 1), ('created_at', -1)],
            [('to_email', 1), ('seen', 1)],
        ]


class GroupMessageModel:
    """Group chat messages."""
    collection_name = 'group_messages'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'group_id': str,
            'sender_email': str,
            'sender_name': str,
            'message': str,
            'created_at': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            [('group_id', 1), ('created_at', -1)],
        ]


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTIVITY FEED + NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class HubFeedModel:
    """Community activity feed events (public, no PII)."""
    collection_name = 'hub_feed'

    ACTIONS = (
        'joined_group', 'created_group', 'created_event',
        'rsvp_event', 'shared_resource', 'new_connection',
    )

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'actor_name': str,          # display name (first name only)
            'action': str,
            'target': str,              # e.g. group name, event title
            'created_at': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            ('created_at', -1),
        ]


class HubNotificationModel:
    """Per-user notification queue."""
    collection_name = 'hub_notifications'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'user_email': str,
            'type': str,               # connection_request | connection_accepted | group_invite | event_reminder | message
            'title': str,
            'body': str,
            'read': bool,
            'link': str,               # e.g. tab to open
            'created_at': datetime,
        }

    @staticmethod
    def indexes() -> list:
        return [
            [('user_email', 1), ('read', 1), ('created_at', -1)],
        ]
