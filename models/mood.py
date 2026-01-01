from typing import Dict, Any
from datetime import datetime

class MoodModel:
    collection_name = 'moods'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'user_email': str,
            'mood': str,  # stressed/sad/anxious/happy/calm/etc
            'intensity': int,  # 1-10
            'created_at': datetime,
        }

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        intensity = doc.get('intensity')
        if not isinstance(intensity, int) or not (1 <= intensity <= 10):
            raise ValueError('intensity must be an int between 1 and 10')
