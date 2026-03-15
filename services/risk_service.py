import logging

log = logging.getLogger(__name__)

LOW_RISK = "LOW_RISK"
MODERATE_RISK = "MODERATE_RISK"
HIGH_RISK = "HIGH_RISK"
CRITICAL_RISK = "CRITICAL_RISK"

CRISIS_KEYWORDS = [
    "i feel hopeless",
    "i want to give up",
    "nothing matters",
    "i can't continue",
    "i hate my life",
    "suicide",
    "kill myself",
    "end my life"
]

def predict_risk_level(stress_score: int, message: str) -> str:
    """Predict mental health risk level based on stress score and crisis keywords."""
    msg_lower = message.lower()
    
    # 1. Check for crisis language (override score if detected)
    for kw in CRISIS_KEYWORDS:
        if kw in msg_lower:
            log.warning(f"Crisis keyword detected in message: '{kw}'")
            return CRITICAL_RISK
            
    # 2. Map stress score to risk level
    if stress_score > 85:
        return CRITICAL_RISK
    elif stress_score >= 65: # 65-85
        return HIGH_RISK
    elif stress_score >= 40: # 40-64
        return MODERATE_RISK
    else: # < 40
        return LOW_RISK
