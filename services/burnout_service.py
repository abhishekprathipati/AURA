import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from utils.database import get_db

logger = logging.getLogger(__name__)

def analyze_burnout_risk(user_email: str) -> Dict[str, Any]:
    """
    Evaluates behavioral patterns to detect signs of academic burnout or mental fatigue.
    
    Criteria:
    1. Anomaly Detection: Stress score > 1.5 standard deviations from personal mean.
    2. Sustained high stress (>70) for 3+ consecutive logs.
    3. Late-night activity patterns.
    4. Sentiment drift towards negativity.
    """
    try:
        db = get_db()
        if db is None:
            return {'risk_level': 'unknown', 'score': 0}

        # 1. Fetch historical data (last 21 days for baseline)
        cutoff = datetime.utcnow() - timedelta(days=21)
        all_logs = list(db['stress'].find({
            'user_email': user_email,
            'created_at': {'$gte': cutoff}
        }).sort('created_at', -1))

        if not all_logs:
            return {'risk_level': 'low', 'score': 0, 'status': 'No recent data'}

        # 2. Personal Baseline Calculation
        all_scores = [log.get('score', 50) for log in all_logs]
        personal_mean = sum(all_scores) / len(all_scores)
        
        # Standard Deviation
        variance = sum((s - personal_mean) ** 2 for s in all_scores) / len(all_scores)
        std_dev = variance ** 0.5

        # 3. Anomaly Detection (recent check-in)
        latest_score = all_scores[0]
        z_score = (latest_score - personal_mean) / std_dev if std_dev > 0 else 0
        is_anomaly = z_score > 1.5

        # 4. Sustained High Stress check (last 5)
        # TODO #35 (AI/ML): Arbitrary Thresholds - Clinical Validation Needed
        #   The threshold of >65 for "sustained high stress" is empirically chosen
        #   and has NOT been validated against clinical burnout assessments.
        #
        #   Issues with current approach:
        #   1. No clinical basis for the 65 threshold (not from MBI or other validated scales)
        #   2. "3+ consecutive logs" is arbitrary - burnout develops over weeks, not days
        #   3. Individual baselines vary - 65 might be normal for some users
        #   4. No distinction between acute stress episodes and chronic burnout
        #
        #   Recommendations for clinical validation:
        #   - Partner with mental health researchers to validate thresholds
        #   - Correlate with validated instruments (Maslach Burnout Inventory)
        #   - Implement personalized thresholds based on user baseline
        #   - Add temporal analysis (sustained over weeks, not just readings)
        #   - Consider multi-dimensional burnout (exhaustion, cynicism, inefficacy)
        #   - IMPORTANT: Add disclaimer that this is NOT a clinical diagnostic tool
        recent_scores = all_scores[:5]
        sustained_high = all(s > 65 for s in recent_scores) if len(recent_scores) >= 3 else False

        # 5. Night Owl Analysis (last 7 days)
        week_cutoff = datetime.utcnow() - timedelta(days=7)
        week_logs = [l for l in all_logs if l['created_at'] >= week_cutoff]
        late_night_logs = sum(1 for l in week_logs if l['created_at'].hour >= 23 or l['created_at'].hour <= 4)
        late_night_ratio = late_night_logs / len(week_logs) if week_logs else 0

        # 6. Sentiment Drift
        trend_up = False
        if len(recent_scores) >= 3:
            trend_up = recent_scores[0] > recent_scores[2]

        # 7. Composite Risk Score
        risk_score = 0
        factors = []

        if is_anomaly:
            risk_score += 30
            factors.append(f"Significant stress spike (+{round(z_score, 1)}σ from baseline)")
        
        if sustained_high:
            risk_score += 45 # Increased weight
            factors.append("Sustained high stress levels")
        if latest_score > 80: # Instantaneous critical check
            risk_score += 25
            factors.append("Critical instantaneous stress")
        elif latest_score > 70:
            risk_score += 15
            factors.append("High instantaneous stress")

        if late_night_ratio > 0.4:
            risk_score += 20
            factors.append("Irregular late-night activity")
        
        if trend_up:
            risk_score += 10
            factors.append("Increasing stress trend")

        # 8. Categorization
        risk_level = "low"
        intervention = "Your emotional state is within your normal range."
        
        if risk_score >= 60:
            risk_level = "high"
            intervention = "High burnout risk. Your stress is significantly higher than your personal baseline. Take a 24-hour restorative break."
        elif risk_score >= 30:
            risk_level = "moderate"
            intervention = "Moderate fatigue detected. Consider a 15-minute mindfulness session to recalibrate."

        return {
            'risk_level': risk_level,
            'score': min(100, risk_score),
            'factors': factors,
            'intervention': intervention,
            'baseline_mean': round(personal_mean, 1),
            'current_z_score': round(z_score, 2),
            'last_analyzed': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Burnout analysis error: %s", e, exc_info=True)
        return {'risk_level': 'error', 'score': 0}
