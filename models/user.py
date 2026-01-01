from typing import Dict, Any
from datetime import datetime
import hashlib

class UserModel:
    collection_name = 'users'

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'email': str,
            'hashed_password': str,  # hashed
            'name': str,
            'role': str,  # student|proctor|hod
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
        if role not in ('student', 'proctor', 'hod'):
            raise ValueError('role must be one of student|proctor|hod')
