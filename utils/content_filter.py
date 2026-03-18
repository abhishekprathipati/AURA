"""
AURA Content Filter Utility
Provides content moderation for chat messages and user-generated content.
"""
import re
from typing import Optional
from markupsafe import escape as html_escape

# Blocked words for chat content moderation
BLOCKED_WORDS = frozenset([
    'abuse',
    'hate',
    'spam',
    'inappropriate',
    'offensive',
    'harassment',
    'violence',
    'threat',
    'kill',
    'harm',
])

# Pre-compiled regex pattern for efficient matching
_BLOCKED_PATTERN = re.compile(
    r'\b(?:' + '|'.join(re.escape(w) for w in BLOCKED_WORDS) + r')\b',
    re.IGNORECASE
)


def contains_blocked_content(text: str) -> bool:
    """
    Check if text contains any blocked words.

    Args:
        text: The text to check for blocked content.

    Returns:
        True if blocked content is found, False otherwise.
    """
    if not text:
        return False
    return bool(_BLOCKED_PATTERN.search(text.lower()))


def sanitize_message(text: str, max_length: int = 500) -> Optional[str]:
    """
    Sanitize a chat message by escaping HTML and enforcing length limits.

    Args:
        text: The raw message text.
        max_length: Maximum allowed message length.

    Returns:
        Sanitized message string, or None if empty/too long.
    """
    if not text:
        return None

    # Strip whitespace
    cleaned = text.strip()

    if not cleaned or len(cleaned) > max_length:
        return None

    # Escape HTML to prevent XSS
    sanitized = str(html_escape(cleaned))

    return sanitized


def filter_message(text: str, max_length: int = 500) -> tuple[Optional[str], Optional[str]]:
    """
    Filter and sanitize a message for storage.

    Args:
        text: The raw message text.
        max_length: Maximum allowed message length.

    Returns:
        Tuple of (sanitized_message, error_message).
        If valid: (sanitized_text, None)
        If invalid: (None, error_description)
    """
    sanitized = sanitize_message(text, max_length)

    if sanitized is None:
        if not text or not text.strip():
            return None, 'Message cannot be empty'
        return None, f'Message exceeds maximum length of {max_length} characters'

    if contains_blocked_content(sanitized):
        return None, 'Inappropriate content detected'

    return sanitized, None
