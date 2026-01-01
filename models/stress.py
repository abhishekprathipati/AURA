from typing import Optional, Dict, Any
from datetime import datetime

class StressModel:
    collection_name = 'stress'

    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            'user_email': str,
            'score': int,  # 0-100
            'source': str,
            'created_at': datetime,
        }

    @staticmethod
    def validate(doc: Dict[str, Any]) -> None:
        if not isinstance(doc.get('user_email'), str):
            raise ValueError('user_email must be a string')
        score = doc.get('score')
        if not isinstance(score, int) or not (0 <= score <= 100):
            raise ValueError('score must be an int between 0 and 100')
        if not isinstance(doc.get('source'), str):
            raise ValueError('source must be a string')

    @staticmethod
    def index_specs():
        return [
            ('user_email', {'unique': False}),
            ('created_at', {'unique': False}),
        ]

    @staticmethod
    def calculate_stress(mood: str, recent_chats, activity_level: int = 5) -> int:
        """Compute stress score 0-100 using mood, chat sentiment proxy, and activity level."""
        mood_weight = 0.4
        chat_weight = 0.3
        activity_weight = 0.3

        mood_map = {
            'happy': 25,
            'calm': 30,
            'sad': 60,
            'anxious': 70,
            'stressed': 80,
        }
        mood_score = mood_map.get(mood, 50)

        # Simple sentiment proxy: shorter, positive-ish messages reduce stress; otherwise neutral.
        neg_words = {'stressed', 'anxious', 'anxiety', 'overwhelmed', 'tired', 'sad', 'panic'}
        pos_words = {'confident', 'prepared', 'ready', 'good', 'calm', 'okay'}
        chat_scores = []
        for chat in recent_chats or []:
            text = (chat.get('message') or '') + ' ' + (chat.get('response') or '')
            text_lower = text.lower()
            negatives = sum(w in text_lower for w in neg_words)
            positives = sum(w in text_lower for w in pos_words)
            score = 60 + 10 * negatives - 10 * positives
            chat_scores.append(score)
        chat_score = sum(chat_scores) / len(chat_scores) if chat_scores else 50

        # Activity: expected 0-10 (higher = healthier) → lower stress
        activity_level = max(0, min(10, activity_level or 0))
        activity_score = 100 - (activity_level * 10)

        raw = (mood_score * mood_weight) + (chat_score * chat_weight) + (activity_score * activity_weight)
        return max(0, min(100, int(round(raw))))
