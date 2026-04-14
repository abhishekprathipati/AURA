"""
AURA Content Filter Tests
============================
FIX #18: Tests for content moderation utilities.
"""
import pytest


class TestContainsBlockedContent:
    """Tests for word-boundary blocked content detection."""

    def test_blocked_word_detected(self):
        from aura.utils.content_filter import contains_blocked_content
        assert contains_blocked_content("You are a hate monger") is True
        assert contains_blocked_content("SPAM this everywhere") is True

    def test_clean_text_passes(self):
        from aura.utils.content_filter import contains_blocked_content
        assert contains_blocked_content("I love studying mathematics") is False
        assert contains_blocked_content("Let's have a great day") is False

    def test_empty_input(self):
        from aura.utils.content_filter import contains_blocked_content
        assert contains_blocked_content("") is False
        assert contains_blocked_content(None) is False

    def test_case_insensitive(self):
        from aura.utils.content_filter import contains_blocked_content
        assert contains_blocked_content("ABUSE of power") is True
        assert contains_blocked_content("Abuse") is True


class TestSanitizeMessage:
    """Tests for message sanitization."""

    def test_strips_whitespace(self):
        from aura.utils.content_filter import sanitize_message
        assert sanitize_message("  hello  ") == "hello"

    def test_escapes_html(self):
        from aura.utils.content_filter import sanitize_message
        result = sanitize_message("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_rejects_too_long(self):
        from aura.utils.content_filter import sanitize_message
        assert sanitize_message("a" * 501) is None

    def test_rejects_empty(self):
        from aura.utils.content_filter import sanitize_message
        assert sanitize_message("") is None
        assert sanitize_message("   ") is None

    def test_custom_max_length(self):
        from aura.utils.content_filter import sanitize_message
        assert sanitize_message("abc", max_length=2) is None
        assert sanitize_message("ab", max_length=2) == "ab"


class TestFilterMessage:
    """Tests for the combined filter + sanitize pipeline."""

    def test_valid_message_passes(self):
        from aura.utils.content_filter import filter_message
        text, error = filter_message("Hello, how are you?")
        assert text is not None
        assert error is None

    def test_blocked_content_rejected(self):
        from aura.utils.content_filter import filter_message
        text, error = filter_message("You are full of hate")
        assert text is None
        assert error is not None
        assert "Inappropriate" in error

    def test_empty_message_rejected(self):
        from aura.utils.content_filter import filter_message
        text, error = filter_message("")
        assert text is None
        assert "empty" in error.lower()
