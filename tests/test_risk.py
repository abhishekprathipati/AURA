"""
AURA Risk Service Tests
=========================
FIX #18: Tests for risk prediction and crisis keyword detection.
"""
import pytest


class TestPredictRiskLevel:
    """Tests for predict_risk_level function."""

    def test_low_score_low_risk(self, mock_db):
        from services.risk_service import predict_risk_level, LOW_RISK
        result = predict_risk_level(20, "I had a good day today")
        assert result == LOW_RISK

    def test_high_score_elevated_risk(self, mock_db):
        from services.risk_service import predict_risk_level, HIGH_RISK, CRITICAL_RISK
        result = predict_risk_level(85, "Everything is terrible")
        assert result in (HIGH_RISK, CRITICAL_RISK)

    def test_crisis_keywords_trigger_critical(self, mock_db):
        from services.risk_service import predict_risk_level, CRITICAL_RISK
        result = predict_risk_level(60, "I want to end my life")
        assert result == CRITICAL_RISK

    def test_moderate_score_moderate_risk(self, mock_db):
        from services.risk_service import predict_risk_level, MODERATE_RISK, LOW_RISK
        result = predict_risk_level(55, "Feeling a bit overwhelmed")
        assert result in (MODERATE_RISK, LOW_RISK)


class TestCrisisKeywords:
    """Tests for crisis language detection using shared utils."""

    def test_english_crisis_detected(self):
        from utils.crisis_keywords import contains_crisis_language
        assert contains_crisis_language("I want to kill myself") is True
        assert contains_crisis_language("suicide thoughts") is True

    def test_hindi_crisis_detected(self):
        from utils.crisis_keywords import contains_crisis_language
        assert contains_crisis_language("marna chahta hoon") is True
        assert contains_crisis_language("khudkushi") is True

    def test_spanish_crisis_detected(self):
        from utils.crisis_keywords import contains_crisis_language
        assert contains_crisis_language("quiero morir") is True
        assert contains_crisis_language("suicidio") is True

    def test_safe_text_not_flagged(self):
        from utils.crisis_keywords import contains_crisis_language
        assert contains_crisis_language("I had a great day") is False
        assert contains_crisis_language("The exam was killer difficult") is False

    def test_empty_text(self):
        from utils.crisis_keywords import contains_crisis_language
        assert contains_crisis_language("") is False
        assert contains_crisis_language(None) is False

    def test_word_boundaries_prevent_false_positives(self):
        from utils.crisis_keywords import contains_crisis_language
        # "skill" should NOT trigger "kill" pattern
        assert contains_crisis_language("I want to improve my skills") is False
