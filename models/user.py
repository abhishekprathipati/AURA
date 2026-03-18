# TODO: ARCHITECTURE #8 - Email used as primary identifier
#   Currently, the application uses email as the primary identifier for users
#   throughout the codebase (session['user_email'], foreign keys in other collections,
#   audit logs, etc.). This has several drawbacks:
#
#   1. Privacy: Emails are PII and shouldn't be used as primary keys
#   2. Mutability: Users may want to change their email address
#   3. Performance: String comparisons are slower than UUID/ObjectId comparisons
#   4. Security: Leaking user identifiers (in URLs, logs) exposes email addresses
#
#   MIGRATION PLAN:
#   1. Add a 'user_id' field (UUID or MongoDB ObjectId) to the users collection
#   2. Create a migration script to generate user_ids for existing users
#   3. Update all foreign key references (chats, moods, stress, etc.) to use user_id
#   4. Update session management to use user_id instead of user_email
#   5. Keep email as a unique index for login lookup, but not as the identifier
#   6. Update API responses to return user_id instead of email where appropriate
#
#   This is a significant architectural change that requires careful planning
#   and a phased migration approach to avoid breaking existing functionality.

from typing import Dict, Any
from datetime import datetime

class UserModel:
    collection_name = 'users'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'email': str,
            'hashed_password': str,  # hashed
            'name': str,
            'role': str,  # student|proctor|hod|admin
            'department': str,  # required for RBAC scoping
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
