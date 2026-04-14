"""
Student Service layer for extracting Database queries from standard routes.
"""
from datetime import datetime, timedelta
from aura.utils.database import get_db
from aura.models.stress import StressModel
from aura.models.mood import MoodModel

def record_wellness_checkin(user_email: str, mood: int, stress: int, notes: str) -> None:
    """
    Submits a wellness checkin for a student. Writes to `moods` and `stress`.
    """
    db = get_db()
    now_ts = datetime.utcnow()

    # Map 1-5 scale mood to text labels
    mood_labels = {1: 'very_low', 2: 'low', 3: 'neutral', 4: 'happy', 5: 'excited'}
    mood_label = mood_labels.get(mood, 'neutral')

    # 1. Store mood entry (scale intensity to 2-10 for backward compatibility if needed)
    db[MoodModel.collection_name].insert_one({
        'user_email': user_email,
        'mood': mood_label,
        'intensity': mood * 2,
        'notes': notes,
        'source': 'wellness_checkin',
        'created_at': now_ts
    })

    # 2. Store stress entry (single canonical source)
    db[StressModel.collection_name].insert_one({
        'user_email': user_email,
        'score': stress,
        'notes': notes,
        'source': 'wellness_checkin',
        'created_at': now_ts
    })

def get_current_wellness_summary(user_email: str) -> dict:
    """
    Retrieves the student's current wellness data derived from standard collections.
    Returns: { 'mood_value', 'mood_trend', 'mood_label', 'checkins_today' }
    """
    db = get_db()
    
    # Translate our text mood back to a 1-5 scale for UI compat
    label_to_val = {'very_low': 1, 'low': 2, 'neutral': 3, 'happy': 4, 'excited': 5}
    reverse_labels = {1: 'Very Low', 2: 'Low', 3: 'Neutral', 4: 'Good', 5: 'Excellent'}
    
    mood_coll = db[MoodModel.collection_name]
    recent_moods = list(mood_coll.find(
        {'user_email': user_email},
        sort=[('created_at', -1)],
        limit=5
    ))
    
    mood_value = 3
    if recent_moods:
        mood_value = label_to_val.get(recent_moods[0].get('mood', 'neutral'), 3)
        
    mood_trend = 'stable'
    if len(recent_moods) >= 2:
        oldest_val = label_to_val.get(recent_moods[-1].get('mood', 'neutral'), 3)
        if oldest_val < mood_value:
            mood_trend = 'improving'
        elif oldest_val > mood_value:
            mood_trend = 'declining'
            
    # Count today's checkins based on stress collection
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    checkins_today = db[StressModel.collection_name].count_documents({
        'user_email': user_email,
        'created_at': {'$gte': today_start}
    })
    
    return {
        'mood_value': mood_value,
        'mood_trend': mood_trend,
        'mood_label': reverse_labels.get(mood_value, 'Neutral'),
        'checkins_today': checkins_today
    }

def get_wellness_activities_summary(user_email: str) -> dict:
    """
    Retrieves activity summary for the student based purely on stress logs.
    """
    db = get_db()
    stress_coll = db[StressModel.collection_name]
    
    now = datetime.utcnow()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = now - timedelta(days=7)
    start_prev_week = now - timedelta(days=14)
    end_prev_week = now - timedelta(days=7)

    today_count = stress_coll.count_documents({
        'user_email': user_email,
        'created_at': {'$gte': start_today}
    })
    week_count = stress_coll.count_documents({
        'user_email': user_email,
        'created_at': {'$gte': start_week}
    })
    
    week_stress = list(stress_coll.find({
        'user_email': user_email,
        'created_at': {'$gte': start_week}
    }))
    weekly_avg_val = int(sum([d.get('score', 0) for d in week_stress]) / len(week_stress)) if week_stress else 0
    
    prev_week_stress = list(stress_coll.find({
        'user_email': user_email,
        'created_at': {'$gte': start_prev_week, '$lt': end_prev_week}
    }))
    prev_week_avg_val = int(sum([d.get('score', 0) for d in prev_week_stress]) / len(prev_week_stress)) if prev_week_stress else 0
    
    if prev_week_avg_val > 0:
        change_ratio = (weekly_avg_val - prev_week_avg_val) / prev_week_avg_val
        pct = int(change_ratio * 100)
        weekly_change = f"+{pct}%" if pct > 0 else f"{pct}%"
    else:
        weekly_change = "0%"

    return {
        'today_count': today_count,
        'week_count': week_count,
        'weekly_avg_val': weekly_avg_val,
        'weekly_change': weekly_change
    }
