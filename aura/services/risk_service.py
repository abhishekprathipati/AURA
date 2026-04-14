import logging
import re
from datetime import datetime, timedelta
from aura.utils.database import get_db
from aura.utils.crisis_keywords import CRISIS_PATTERNS as _CRISIS_PATTERNS

log = logging.getLogger(__name__)

LOW_RISK = "LOW_RISK"
MODERATE_RISK = "MODERATE_RISK"
HIGH_RISK = "HIGH_RISK"
CRITICAL_RISK = "CRITICAL_RISK"

# Crisis patterns imported from utils.crisis_keywords (single source of truth, #45)
# Includes English, Hindi/Hinglish, and Spanish patterns (#36)

def predict_risk_level(stress_score: int, message: str, user_email: str = None) -> str:
    """Predict mental health risk level based on stress score, keywords, and personal baseline."""

    # 1. Check for crisis language using word boundaries (case-insensitive)
    for pattern in _CRISIS_PATTERNS:
        if pattern.search(message):
            log.warning("Crisis keyword detected for %s: '%s'", user_email or 'unknown', pattern.pattern)
            return CRITICAL_RISK

    # 2. Personalized Baseline Anomaly Detection
    is_anomaly = False
    if user_email:
        try:
            db = get_db()
            cutoff = datetime.utcnow() - timedelta(days=21)
            history = list(db['stress'].find(
                {'user_email': user_email, 'created_at': {'$gte': cutoff}},
                {'score': 1}
            ).sort('created_at', -1).limit(30))

            if len(history) >= 5:
                scores = [h.get('score', 50) for h in history]
                mean = sum(scores) / len(scores)
                variance = sum((s - mean) ** 2 for s in scores) / len(scores)
                std_dev = variance ** 0.5

                if std_dev > 0:
                    z_score = (stress_score - mean) / std_dev
                    if z_score > 1.8:  # Significant spike from baseline
                        is_anomaly = True
                        log.info("Personalized risk anomaly: %s z-score=%.2f", user_email, z_score)
                elif stress_score > mean + 15:  # Significant jump from flat baseline
                    is_anomaly = True
                    log.info("Personalized risk anomaly (flat baseline): %s jump=%d", user_email, stress_score - mean)
        except Exception as e:
            log.error("Risk baseline calc error: %s", e)

    # 3. Map stress score to risk level
    if stress_score > 85 or (is_anomaly and stress_score > 60):
        return CRITICAL_RISK
    elif stress_score >= 65 or is_anomaly:
        return HIGH_RISK
    elif stress_score >= 40:  # 40-64
        return MODERATE_RISK
    else:  # < 40
        return LOW_RISK
