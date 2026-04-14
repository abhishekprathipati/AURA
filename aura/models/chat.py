from typing import Dict, Any
from datetime import datetime

class ChatModel:
    collection_name = 'chats'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'user_email': str,
            'message': str,
            'response': str,
            'type': str,  # mental|study
            'created_at': datetime,
        }

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        if doc.get('type') not in ('mental', 'study'):
            raise ValueError('type must be mental or study')
