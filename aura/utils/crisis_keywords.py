"""
AURA Crisis Keywords — Single Source of Truth
=============================================
FIX #45: Consolidated crisis keyword lists used by both risk_service.py
and ai_service.py to prevent divergence.

FIX #36: Includes multilingual crisis expressions (Hindi, Spanish,
Hinglish) in addition to English patterns.
"""
import re
from typing import List

# ── English crisis patterns (word-boundary matching) ─────────────────────────
CRISIS_KEYWORDS_EN = [
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
    r"\bno point in living\b",
    r"\bwant to die\b",
    r"\bhurt myself\b",
    r"\bkill u\b",
    r"\bkill you\b",
]

# ── Hindi / Hinglish crisis patterns (#36) ───────────────────────────────────
CRISIS_KEYWORDS_HI = [
    r"\bmarna chahta\b",            # want to die
    r"\bmarna chahti\b",            # want to die (feminine)
    r"\bjina nahi chahta\b",        # don't want to live
    r"\bjina nahi chahti\b",        # don't want to live (feminine)
    r"\bkoi umeed nahi\b",          # no hope
    r"\bzindagi se tang\b",         # fed up with life
    r"\bkhatam karna\b",           # want to end it
    r"\bkhudkushi\b",               # suicide (Hindi)
    r"\baatmahatya\b",              # suicide (formal Hindi)
    r"\bmar jana chahta\b",         # want to die
    r"\bjeene ka mann nahi\b",      # don't feel like living
]

# ── Spanish crisis patterns (#36) ────────────────────────────────────────────
CRISIS_KEYWORDS_ES = [
    r"\bquiero morir\b",            # I want to die
    r"\bsuicidio\b",                # suicide
    r"\bno quiero vivir\b",         # I don't want to live
    r"\bhacerme daño\b",            # hurt myself
    r"\bsin esperanza\b",           # without hope
    r"\bno vale la pena\b",         # not worth it
    r"\bterminar con todo\b",       # end it all
    r"\bme quiero matar\b",         # I want to kill myself
]

# ── Combined list ────────────────────────────────────────────────────────────
ALL_CRISIS_KEYWORDS: List[str] = (
    CRISIS_KEYWORDS_EN + CRISIS_KEYWORDS_HI + CRISIS_KEYWORDS_ES
)

# Pre-compiled patterns for performance (case-insensitive)
CRISIS_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in ALL_CRISIS_KEYWORDS]

# Plain keyword list for simple substring matching (used by AI service crisis interceptor)
CRISIS_PLAIN_KEYWORDS = [
    'suicide', 'kill myself', 'kill u', 'kill you', 'want to die',
    'end my life', 'hurt myself', 'hopeless', 'nothing matters',
    'want to give up', 'khudkushi', 'aatmahatya', 'quiero morir', 'suicidio',
]


def contains_crisis_language(text: str) -> bool:
    """Check if text contains any crisis language using compiled regex patterns.

    Returns True if any crisis pattern matches (case-insensitive, word-boundary).
    """
    if not text:
        return False
    for pattern in CRISIS_PATTERNS:
        if pattern.search(text):
            return True
    return False
