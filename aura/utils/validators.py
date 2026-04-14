"""
Input validation helpers for proctor API endpoints.
"""
import re
from datetime import datetime


def validate_incident_action(data):
    """Validate incident action payload."""
    required = ['incident_id', 'action_type']
    for field in required:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    action_type = data['action_type'].upper()
    if action_type not in ['DISMISS', 'REMOVE', 'ESCALATE']:
        return False, f"Invalid action_type: {action_type}"
    
    # Validate UUID format
    uuid_pattern = re.compile(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
        re.IGNORECASE
    )
    if not uuid_pattern.match(data['incident_id']):
        return False, "Invalid incident_id (must be UUID)"
    
    return True, "Validation passed"


def validate_bulk_action(data):
    """Validate bulk action payload."""
    if 'incident_ids' not in data or not isinstance(data['incident_ids'], list):
        return False, "incident_ids must be a list"
    
    if len(data['incident_ids']) == 0:
        return False, "incident_ids cannot be empty"
    
    if len(data['incident_ids']) > 100:
        return False, "Cannot process more than 100 incidents at once"
    
    action_type = data.get('action_type', '').upper()
    if action_type not in ['DISMISS', 'REMOVE', 'ESCALATE']:
        return False, f"Invalid action_type: {action_type}"
    
    return True, "Validation passed"


def validate_search_query(query, field):
    """Validate search parameters."""
    if not query or len(query) < 3:
        return False, "Search query must be at least 3 characters"
    
    if len(query) > 200:
        return False, "Search query too long (max 200 chars)"
    
    allowed_fields = ['incident_id', 'room_name', 'message_excerpt']
    if field not in allowed_fields:
        return False, f"Invalid search field: {field}"
    
    # Basic injection prevention: only alphanumeric, spaces, hyphens
    if not re.match(r'^[\w\s\-]+$', query):
        return False, "Invalid characters in search query"
    
    return True, "Validation passed"
