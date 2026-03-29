# FIX #8: Added user_id UUID field alongside email.
# UUID is auto-generated and used as the canonical internal identifier
# for SocketIO rooms, session references, and cross-collection foreign keys.
# Email remains as a unique index for login lookup only.

import uuid
from typing import Dict, Any
from datetime import datetime

class UserModel:
    collection_name = 'users'

    @staticmethod
    def generate_user_id() -> str:
        """Generate a new UUID for a user."""
        return str(uuid.uuid4())

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'user_id': str,          # UUID — canonical internal identifier
            'email': str,            # unique, used for login lookup only
            'hashed_password': str,  # hashed
            'name': str,
            'role': str,             # student|proctor|hod|admin
            'department': str,       # required for RBAC scoping
            'timezone_offset': int,  # FIX #17: per-user timezone offset in minutes from UTC
            'created_at': datetime,
        }

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        if not isinstance(doc.get('email'), str):
            raise ValueError('email must be a string')
        if not isinstance(doc.get('hashed_password'), str):
            raise ValueError('hashed_password must be a string (hashed)')
        if not isinstance(doc.get('name'), str):
            raise ValueError('name must be a string')
        role = doc.get('role')
        if role not in ('student', 'proctor', 'hod', 'admin'):
            raise ValueError('role must be one of student|proctor|hod|admin')
