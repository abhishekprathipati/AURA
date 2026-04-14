"""
AURA Stress Engine Tests
==========================
FIX #18: Tests for stress service core functions.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestScoreTextSentiment:
    """Tests for the keyword-based sentiment scoring."""

    def test_negative_keywords_increase_score(self):
        from aura.services.stress_service import _score_text_sentiment
        score = _score_text_sentiment("I feel very stressed and anxious about exams")
        assert score > 50, f"Negative text should score > 50, got {score}"

    def test_positive_keywords_decrease_score(self):
        from aura.services.stress_service import _score_text_sentiment
        score = _score_text_sentiment("I feel happy and grateful today, everything is wonderful")
        assert score < 50, f"Positive text should score < 50, got {score}"

    def test_neutral_text(self):
        from aura.services.stress_service import _score_text_sentiment
        score = _score_text_sentiment("I went to class today")
        assert 20 <= score <= 60, f"Neutral text should be moderate, got {score}"

    def test_empty_string(self):
        from aura.services.stress_service import _score_text_sentiment
        score = _score_text_sentiment("")
        assert score == 50, f"Empty string should return 50, got {score}"

    def test_none_input(self):
        from aura.services.stress_service import _score_text_sentiment
        score = _score_text_sentiment(None)
        assert score == 50, f"None input should return 50, got {score}"


class TestLogisticCompress:
    """Tests for the logistic compression function."""

    def test_returns_values_in_0_100_range(self):
        from aura.services.stress_service import _logistic_compress
        for val in [0, 25, 50, 75, 100, 150, -10]:
            result = _logistic_compress(val)
            assert 0 <= result <= 100, f"_logistic_compress({val}) = {result}, not in [0, 100]"

    def test_midpoint_near_50(self):
        from aura.services.stress_service import _logistic_compress
        result = _logistic_compress(50)
        assert 45 <= result <= 55, f"Midpoint should be near 50, got {result}"

    def test_monotonically_increasing(self):
        from aura.services.stress_service import _logistic_compress
        prev = _logistic_compress(0)
        for val in range(10, 110, 10):
            curr = _logistic_compress(val)
            assert curr >= prev, f"Not monotonic: {curr} < {prev} at val={val}"
            prev = curr

    def test_extreme_values_clamped(self):
        from aura.services.stress_service import _logistic_compress
        assert _logistic_compress(200) <= 100
        assert _logistic_compress(-50) >= 0


class TestSignalMood:
    """Tests for mood signal extraction."""

    def test_high_stress_mood(self, mock_db):
        from aura.services.stress_service import _signal_mood
        from datetime import datetime, timedelta
        # Pre-load the mock mood collection with stressed entries
        mock_db['moods']._data = [
            {'user_email': 'test@aura.edu', 'mood': 'stressed', 'created_at': datetime.utcnow()},
        ]
        mock_db['moods'].find_one = lambda *a, **kw: {
            'user_email': 'test@aura.edu',
            'mood': 'stressed',
            'created_at': datetime.utcnow(),
        }
        score, has_data = _signal_mood('test@aura.edu', mock_db)
        assert has_data is True
        assert score > 60, f"High-stress mood should produce score > 60, got {score}"

    def test_low_stress_mood(self, mock_db):
        from aura.services.stress_service import _signal_mood
        from datetime import datetime
        mock_db['moods'].find_one = lambda *a, **kw: {
            'user_email': 'test@aura.edu',
            'mood': 'happy',
            'created_at': datetime.utcnow(),
        }
        score, has_data = _signal_mood('test@aura.edu', mock_db)
        assert has_data is True
        assert score < 40, f"Low-stress mood should produce score < 40, got {score}"

    def test_empty_moods(self, mock_db):
        from aura.services.stress_service import _signal_mood
        # MockCollection.find_one returns None by default
        score, has_data = _signal_mood('test@aura.edu', mock_db)
        assert has_data is False


class TestSignalTimeBias:
    """Tests for time-of-day bias signal."""

    def test_returns_score_and_true(self):
        from aura.services.stress_service import _signal_time_bias
        score, has_data = _signal_time_bias()
        assert has_data is True
        assert 0 <= score <= 100

    def test_returns_numeric_score(self):
        from aura.services.stress_service import _signal_time_bias
        score, _ = _signal_time_bias()
        assert isinstance(score, (int, float))
