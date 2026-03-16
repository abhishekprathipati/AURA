import logging
import re
from datetime import datetime, timedelta
from utils.database import get_db

log = logging.getLogger(__name__)

LOW_RISK = "LOW_RISK"
MODERATE_RISK = "MODERATE_RISK"
HIGH_RISK = "HIGH_RISK"
CRITICAL_RISK = "CRITICAL_RISK"

# Crisis keywords with word boundary matching to prevent false positives
# e.g., "kill" won't match "skill", "skilled", etc.
CRISIS_KEYWORDS = [
    r"\bi feel hopeless\b",
    r"\bi want to give up\b",
    r"\bnothing matters\b",
    r"\bi can'?t continue\b",
    r"\bi hate my life\b",
    r"\bsuicide\b",
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bbetter off dead\b",
    r"\bdon'?t want to wake up\b",
    r"\bhurting myself\b",
    r"\bself[- ]?harm\b",
    r"\bharm myself\b",
    r"\bleave this world\b",
    r"\bno point in living\b"
]

# Pre-compile patterns for performance
_CRISIS_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in CRISIS_KEYWORDS]

def predict_risk_level(stress_score: int, message: str, user_email: str = None) -> str:
    """Predict mental health risk level based on stress score, keywords, and personal baseline."""

    # 1. Check for crisis language using word boundaries (case-insensitive)
    for pattern in _CRISIS_PATTERNS:
        if pattern.search(message):
            log.warning(f"Crisis keyword detected for {user_email or 'unknown'}: '{pattern.pattern}'")
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
                        log.info(f"Personalized risk anomaly: {user_email} z-score={z_score:.2f}")
                elif stress_score > mean + 15: # Significant jump from flat baseline
                    is_anomaly = True
                    log.info(f"Personalized risk anomaly (flat baseline): {user_email} jump={stress_score - mean}")
        except Exception as e:
            log.error(f"Risk baseline calc error: {e}")

    # 3. Map stress score to risk level
    if stress_score > 85 or (is_anomaly and stress_score > 60):
        return CRITICAL_RISK
    elif stress_score >= 65 or is_anomaly:
        return HIGH_RISK
    elif stress_score >= 40: # 40-64
        return MODERATE_RISK
    else: # < 40
        return LOW_RISK
