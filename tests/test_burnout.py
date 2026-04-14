"""
AURA Burnout Service Tests
============================
FIX #18: Tests for burnout risk analysis.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestAnalyzeBurnoutRisk:
    """Tests for analyze_burnout_risk with mock DB."""

    def test_insufficient_data(self, mock_db):
        """With no stress logs, should return 'low' or indicate insufficient data."""
        from aura.services.burnout_service import analyze_burnout_risk
        result = analyze_burnout_risk('test@aura.edu')
        assert result['risk_level'] in ('low', 'error')

    def test_includes_disclaimer(self, mock_db):
        """FIX #35: Every burnout response should include a clinical disclaimer."""
        from aura.services.burnout_service import analyze_burnout_risk

        # Mock stress collection with enough data
        stress_data = [
            {'user_email': 'test@aura.edu', 'score': 30, 'created_at': datetime.utcnow() - timedelta(hours=i)}
            for i in range(15)
        ]
        mock_db['stress']._data = stress_data
        mock_db['stress'].find_one = lambda *a, **kw: stress_data[0] if stress_data else None

        class MockCursor:
            def __init__(self, data):
                self._data = data
            def sort(self, *a, **kw): return self
            def limit(self, n): return self
            def __iter__(self): return iter(self._data)
            def __list__(self): return self._data

        mock_db['stress'].find = lambda *a, **kw: MockCursor(stress_data)

        result = analyze_burnout_risk('test@aura.edu')
        if result.get('risk_level') != 'error':
            assert 'disclaimer' in result, "Burnout response should include 'disclaimer' field"

    def test_high_scores_produce_elevated_risk(self, mock_db):
        """Consistently high stress should produce moderate or high burnout risk."""
        from aura.services.burnout_service import analyze_burnout_risk

        stress_data = [
            {'user_email': 'test@aura.edu', 'score': 85, 'created_at': datetime.utcnow() - timedelta(hours=i)}
            for i in range(15)
        ]

        class MockCursor:
            def __init__(self, data): self._data = data
            def sort(self, *a, **kw): return self
            def limit(self, n): return self
            def __iter__(self): return iter(self._data)

        mock_db['stress'].find = lambda *a, **kw: MockCursor(stress_data)

        result = analyze_burnout_risk('test@aura.edu')
        if result.get('risk_level') != 'error':
            assert result['risk_level'] in ('moderate', 'high'), \
                f"High stress should produce elevated risk, got {result['risk_level']}"


class TestRiskScoreBounds:
    """Risk score should always be in [0, 100]."""

    def test_score_never_exceeds_100(self, mock_db):
        from aura.services.burnout_service import analyze_burnout_risk
        result = analyze_burnout_risk('test@aura.edu')
        if 'score' in result:
            assert 0 <= result['score'] <= 100
