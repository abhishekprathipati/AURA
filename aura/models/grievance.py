from typing import Dict, Any
from datetime import datetime

class GrievanceModel:
    collection_name = 'grievances'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'user_email': str,
            'subject': str,
            'description': str,
            'status': str,  # pending|in_progress|resolved
            'created_at': datetime,
            'resolved_at': datetime,  # optional
            'resolved_by': str,  # proctor email
            'proctor_note': str,  # optional
        }

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        if doc.get('status') not in ('pending', 'in_progress', 'resolved'):
            raise ValueError('status must be pending, in_progress, or resolved')
