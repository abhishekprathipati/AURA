"""
AURA — Shared utilities
"""
import logging
import os
import re

log = logging.getLogger(__name__)

# Whether to expose internal error details to API clients
_DEBUG_ERRORS = os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes', 'on')

# ── Content filter (single source of truth) ──────────────────────────
BLOCKED_WORDS = [
    'abuse', 'hate', 'spam', 'inappropriate', 'offensive',
    'harassment', 'violence', 'threat', 'kill', 'harm',
]
_BLOCKED_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(w) for w in BLOCKED_WORDS) + r')\b',
    re.IGNORECASE,
)


def contains_blocked_content(text: str) -> bool:
    """Return True if *text* contains a blocked word (word-boundary match)."""
    return bool(_BLOCKED_RE.search(text or ''))


def safe_error(exc: Exception, context: str = '') -> str:
    """Return a sanitised error message for API responses.

    In debug mode returns the actual exception text (capped at 200 chars).
    In production returns a generic message — the real error is logged server-side.
    """
    log.error("[%s] %s", context or 'error', exc, exc_info=True)
    if _DEBUG_ERRORS:
        return str(exc)[:200]
    return 'An internal error occurred. Please try again.'


def example_helper():
    return "helper-ready"
