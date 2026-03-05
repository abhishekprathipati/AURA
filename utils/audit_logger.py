"""
═══════════════════════════════════════════════════════════════
AURA — Centralized Audit Logger
═══════════════════════════════════════════════════════════════
Provides non-blocking audit logging for all proctor actions.

Collection: proctor_activity_logs

Every write action a proctor performs is logged here with:
  - who (proctor email)
  - what (action type)
  - on what (target type + ID)
  - when (UTC timestamp)
  - from where (IP + user agent)
  - extra context (metadata dict)

This is separate from `proctor_actions` (incident-specific trail).
This collection captures *everything* — student management,
incident workflow, notes, grievances, login activity, etc.

Usage:
    from utils.audit_logger import log_activity

    log_activity(
        action='ADD_STUDENT',
        target_type='student',
        target_id=anonymous_id,
        metadata={'email': email, 'department': dept}
    )
═══════════════════════════════════════════════════════════════
"""

from datetime import datetime
from flask import request, session, has_request_context
from utils.database import get_db


# ═══════════════════════════════════════════════
# Action constants (for consistent filtering)
# ═══════════════════════════════════════════════

class AuditAction:
    """Enum-like constants for audit action types."""
    # Student management
    ADD_STUDENT       = 'ADD_STUDENT'
    REMOVE_STUDENT    = 'REMOVE_STUDENT'

    # Incident workflow
    REVIEW_INCIDENT   = 'REVIEW_INCIDENT'
    DISMISS_INCIDENT  = 'DISMISS_INCIDENT'
    ESCALATE_INCIDENT = 'ESCALATE_INCIDENT'
    CLOSE_INCIDENT    = 'CLOSE_INCIDENT'
    CONTACT_STUDENT   = 'CONTACT_STUDENT'
    MONITOR_STUDENT   = 'MONITOR_STUDENT'
    CASE_STATUS_CHANGE = 'CASE_STATUS_CHANGE'
    ASSIGN_COUNSELOR  = 'ASSIGN_COUNSELOR'
    BULK_ACTION       = 'BULK_ACTION'

    # Notes
    ADD_NOTE          = 'ADD_NOTE'

    # Grievance / support
    UPDATE_TICKET     = 'UPDATE_TICKET'

    # Session
    LOGIN             = 'LOGIN'
    LOGOUT            = 'LOGOUT'


# ═══════════════════════════════════════════════
# Core logging function
# ═══════════════════════════════════════════════

def log_activity(action, target_type=None, target_id=None, metadata=None, proctor_email=None):
    """
    Insert a single audit log entry into proctor_activity_logs.

    Non-blocking: if logging fails, it prints an error but never
    crashes the calling endpoint.

    Args:
        action:        One of AuditAction constants (string)
        target_type:   'student' | 'incident' | 'ticket' | 'note' | None
        target_id:     anonymous_id, incident_id, ticket_id, etc.
        metadata:      dict with any extra context
        proctor_email: override for non-request contexts (e.g. scripts)
    """
    try:
        db = get_db()
        if db is None:
            return

        # Resolve proctor identity
        email = proctor_email or ''
        name = ''
        ip = ''
        ua = ''

        if has_request_context():
            email = email or session.get('user_email', '')
            name = session.get('user_name', '')
            ip = request.remote_addr or ''
            ua = request.headers.get('User-Agent', '')[:300]

        doc = {
            'proctor_email': email,
            'proctor_name': name,
            'action': action,
            'target_type': target_type,
            'target_id': str(target_id) if target_id else None,
            'metadata': metadata or {},
            'ip_address': ip,
            'user_agent': ua,
            'timestamp': datetime.utcnow(),
        }

        db['proctor_activity_logs'].insert_one(doc)

    except Exception as e:
        # Never crash the caller — audit is a side-effect
        import logging
        logging.getLogger('aura.audit').warning('Logging failed: %s', e)


# ═══════════════════════════════════════════════
# Index setup (call once on app startup)
# ═══════════════════════════════════════════════

def ensure_audit_indexes(db=None):
    """Create indexes for fast audit queries. Safe to call multiple times."""
    try:
        if db is None:
            db = get_db()
        if db is None:
            return

        col = db['proctor_activity_logs']
        col.create_index('timestamp')
        col.create_index('proctor_email')
        col.create_index('action')
        col.create_index([('proctor_email', 1), ('timestamp', -1)])
        col.create_index([('action', 1), ('timestamp', -1)])
    except Exception as e:
        import logging
        logging.getLogger('aura.audit').warning('Index creation warning: %s', e)
