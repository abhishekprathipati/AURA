from datetime import datetime
from collections import Counter
from aura.utils.database import get_db
import logging

log = logging.getLogger(__name__)

def update_emotion_memory(user_email: str):
    """Update rolling emotion memory for the user based on last 20 chat messages."""
    try:
        db = get_db()
        if db is None:
            return
            
        chats_coll = db['chats']
        
        # Fetch last 20 mental chats for this user
        recent_chats = list(
            chats_coll.find({'user_email': user_email, 'type': 'mental'})
            .sort('created_at', -1)
            .limit(20)
        )
        
        if not recent_chats:
            return
            
        total_stress = 0
        valid_stress_count = 0
        emotions = []
        
        for chat in recent_chats:
            stress = chat.get('stress_score')
            emotion = chat.get('sentiment')
            
            if isinstance(stress, (int, float)):
                total_stress += stress
                valid_stress_count += 1
                
            if isinstance(emotion, str) and emotion.strip():
                emotions.append(emotion.strip())
                
        # Calculate average stress
        average_stress = round(total_stress / valid_stress_count) if valid_stress_count > 0 else 50
        
        # Calculate dominant emotion
        dominant_emotion = "Neutral"
        if emotions:
            counter = Counter(emotions)
            dominant_emotion = counter.most_common(1)[0][0]
            
        # Upsert memory record
        memory_coll = db['emotion_memory']
        now = datetime.utcnow()
        
        memory_doc = {
            'user_email': user_email,
            'average_stress': average_stress,
            'dominant_emotion': dominant_emotion,
            'last_updated': now
        }
        
        memory_coll.update_one(
            {'user_email': user_email},
            {'$set': memory_doc},
            upsert=True
        )

        log.info("Updated emotion memory for %s: %d stress, %s", user_email, average_stress, dominant_emotion)

    except Exception as e:
        log.error("Failed to update emotion memory: %s", e)

def get_emotion_memory(user_email: str) -> dict:
    """Fetch the current emotion memory for a user."""
    try:
        db = get_db()
        if db is not None:
            memory = db['emotion_memory'].find_one({'user_email': user_email}, {'_id': 0})
            if memory:
                return memory
    except Exception as e:
        log.error("Failed to fetch emotion memory: %s", e)
    return {"average_stress": 50, "dominant_emotion": "Neutral"}
