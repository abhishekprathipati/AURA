from datetime import datetime, timedelta
from typing import Optional
from utils.database import get_db
from models.mood import MoodModel
from models.stress import StressModel
from models.chat import ChatModel
from utils.alerts import send_institutional_alert


MOOD_BASELINE = {
    'happy': 20,
    'calm': 30,
    'normal': 40,
    'sad': 65,
    'anxious': 70,
    'stressed': 75,
    'angry': 80,
}

SENTIMENT_SCORE = {
    'positive': 30,
    'neutral': 50,
    'negative': 75,
    'anxious': 85,
}


def calculate_daily_stress(user_email: str) -> int:
    """Compute a 0-100 stress score using latest mood and recent chat sentiment.

    Weighted average: mood 0.6 + sentiment 0.4. Saves a record and triggers alerts.
    """
    db = get_db()
    moods = db[MoodModel.collection_name]
    chats = db[ChatModel.collection_name]
    stress_coll = db[StressModel.collection_name]

    # Latest mood in last 24h
    since = datetime.utcnow() - timedelta(hours=24)
    latest_mood = moods.find_one({'user_email': user_email, 'created_at': {'$gte': since}}, sort=[('created_at', -1)])
    mood_key = (latest_mood or {}).get('mood', 'normal')
    mood_score = MOOD_BASELINE.get(mood_key, 50)

    # Average sentiment over last 5 chats
    recent_chats = list(chats.find({'user_email': user_email, 'type': 'mental'}).sort('created_at', -1).limit(5))
    if recent_chats:
        scores = [SENTIMENT_SCORE.get(c.get('sentiment', 'neutral'), 50) for c in recent_chats]
        sentiment_avg = int(round(sum(scores) / len(scores)))
    else:
        sentiment_avg = 50

    final_score = int(round(mood_score * 0.6 + sentiment_avg * 0.4))

    stress_doc = {
        'user_email': user_email,
        'score': final_score,
        'source': 'daily_aggregate',
        'created_at': datetime.utcnow(),
    }
    stress_coll.insert_one(stress_doc)

    if final_score > 80:
        send_institutional_alert(user_email, final_score)

    return final_score
