"""
AURA Prediction Service Tests
================================
FIX #18: Tests for Holt exponential smoothing forecaster.
"""
import pytest


class TestHoltForecast:
    """Tests for the _holt_forecast helper function."""

    def test_rising_trend(self):
        from services.prediction_service import _holt_forecast
        values = [30, 40, 50, 60, 70]
        forecast = _holt_forecast(values, steps=3)
        assert len(forecast) == 3
        assert forecast[0] > values[-1], "Should forecast above the last value for rising trend"

    def test_falling_trend(self):
        from services.prediction_service import _holt_forecast
        values = [80, 70, 60, 50, 40]
        forecast = _holt_forecast(values, steps=3)
        assert forecast[0] < values[-1], "Should forecast below the last value for falling trend"

    def test_stable_trend(self):
        from services.prediction_service import _holt_forecast
        values = [50, 50, 50, 50, 50]
        forecast = _holt_forecast(values, steps=3)
        for f in forecast:
            assert abs(f - 50) < 10, f"Stable data should forecast near 50, got {f}"

    def test_single_value(self):
        from services.prediction_service import _holt_forecast
        forecast = _holt_forecast([60], steps=3)
        assert len(forecast) == 3
        assert all(f == 60 for f in forecast), "Single value should repeat"

    def test_two_values(self):
        from services.prediction_service import _holt_forecast
        forecast = _holt_forecast([40, 60], steps=2)
        assert len(forecast) == 2
        assert forecast[0] > 60, "Upward two-point should predict above"

    def test_empty_values(self):
        from services.prediction_service import _holt_forecast
        forecast = _holt_forecast([], steps=3)
        assert len(forecast) == 3


class TestForecastStress:
    """Integration test for forecast_stress with mock DB."""

    def test_insufficient_data(self, mock_db):
        from services.prediction_service import forecast_stress
        result = forecast_stress('test@aura.edu')
        assert result['trend'] == 'insufficient_data'
        assert result['confidence'] == 0
