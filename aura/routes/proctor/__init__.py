from flask import Blueprint, jsonify, request, render_template, session, Response, current_app
from bson import ObjectId
from functools import wraps
from datetime import datetime, timedelta
import uuid
import io
import csv
from aura.utils.auth_helpers import login_required, demo_restricted, role_required
from aura.utils.database import get_db
from aura.utils.audit_logger import log_activity, AuditAction
from aura.utils.rate_limit import apply_rate_limit, Limits
from aura.utils.access_control import (
    get_visible_student_ids, get_visible_students, get_incident_filter,
    can_access_student, create_anonymous_id, get_current_user,
)
from aura.utils.helpers import safe_error

proctor_bp = Blueprint('proctor', __name__)

# Helper to access limiter from app context
def _get_limiter():
    try:
        return current_app.limiter
    except (RuntimeError, AttributeError):
        return None

# ---------------------------------------------
# Helpers
# ---------------------------------------------

def proctor_only(f):
    """Ensure the current user is a proctor or HOD."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('user_role')
        if role not in ['proctor', 'hod']:
            return jsonify({'error': 'Unauthorized access'}), 403
        return f(*args, **kwargs)
    return decorated_function


def hod_only(f):
    """Ensure the current user is HOD."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('user_role')
        if role != 'hod':
            return jsonify({'error': 'Unauthorized - HOD access only'}), 403
        return f(*args, **kwargs)
    return decorated_function


_indexes_ensured = False

def _ensure_indexes(db):
    """Create indexes once per process lifetime (idempotent guard)."""
    global _indexes_ensured
    if _indexes_ensured:
        return
    db['risk_incidents'].create_index('incident_id', unique=True)
    db['risk_incidents'].create_index('status')
    db['risk_incidents'].create_index('risk_level')
    db['risk_incidents'].create_index('timestamp')

    db['proctor_actions'].create_index('action_id', unique=True)
    db['proctor_actions'].create_index('incident_id')
    db['proctor_actions'].create_index('proctor_id')
    db['proctor_actions'].create_index('timestamp')

    db['system_status'].create_index('status')
    _indexes_ensured = True


def _time_since(ts: datetime) -> str:
    now = datetime.utcnow()
    diff = now - ts
    if diff.days > 0:
        return f"{diff.days}d"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600}h"
    if diff.seconds > 60:
        return f"{diff.seconds // 60}m"
    return "Just now"


def _trend_icon(trend: str) -> str:
    return {
        'RISING': 'â†‘',
        'FALLING': 'â†“',
        'STABLE': 'â†’',
    }.get(trend, 'â†’')


def _risk_color(risk_level: str) -> str:
    return {
        'HIGH': '#dc3545',
        'MEDIUM': '#ffc107',
        'LOW': '#198754',
    }.get(risk_level, '#6c757d')


def _severity_score(risk_level: str) -> int:
    return {
        'HIGH': 3,
        'MEDIUM': 2,
        'LOW': 1,
    }.get(risk_level, 0)


def _serialize_incident(doc: dict) -> dict:
    return {
        'incident_id': doc.get('incident_id'),
        'anonymous_student_id': doc.get('anonymous_student_id'),
        'risk_level': doc.get('risk_level'),
        'trend': doc.get('trend'),
        'trend_icon': _trend_icon(doc.get('trend')),
        'risk_color': _risk_color(doc.get('risk_level')),
        'severity_score': _severity_score(doc.get('risk_level')),
        'trigger_source': doc.get('trigger_source'),
        'incident_type': doc.get('incident_type'),
        'message_excerpt': doc.get('message_excerpt'),
        'details': doc.get('details'),
        'room_name': doc.get('room_name'),
        'timestamp': doc.get('timestamp').isoformat() if doc.get('timestamp') else None,
        'report_count': doc.get('report_count', 1),
        'status': doc.get('status', 'UNREVIEWED'),
        'case_status': doc.get('case_status', 'new'),
        'assigned_to': doc.get('assigned_to'),
        'auto_triggered': doc.get('auto_triggered', False),
        'time_since_trigger': _time_since(doc.get('timestamp')) if doc.get('timestamp') else None,
    }


def _serialize_action(doc: dict) -> dict:
    return {
        'action_id': doc.get('action_id'),
        'incident_id': doc.get('incident_id'),
        'proctor_id': doc.get('proctor_id'),
        'action_type': doc.get('action_type'),
        'reason_code': doc.get('reason_code'),
        'details': doc.get('details'),
        'old_status': doc.get('old_status'),
        'new_status': doc.get('new_status'),
        'old_case_status': doc.get('old_case_status'),
        'new_case_status': doc.get('new_case_status'),
        'timestamp': doc.get('timestamp').isoformat() if doc.get('timestamp') else None,
        'time_since': _time_since(doc.get('timestamp')) if doc.get('timestamp') else None,
    }


def _default_status():
    return {
        'status': 'LIVE',
        'active_students': 0,
        'active_alerts': 0,
        'connection_hub_state': 'CALM',
        'last_update': datetime.utcnow(),
    }

# ---------------------------------------------
# Dashboard Route
# ---------------------------------------------


# ── Register sub-module routes ────────────────────────────────────────────
# These must be imported AFTER proctor_bp is defined to avoid circular imports.
from aura.routes.proctor import (  # noqa: E402, F401
    students, cases, hod, risk, audit, support, academics
)
