import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from services.risk_service import predict_risk_level
from services.prediction_service import forecast_stress
from services.burnout_service import analyze_burnout_risk

# --- Mock Data Helpers ---

def create_mock_logs(scores, timestamps=None):
    if timestamps is None:
        now = datetime.utcnow()
        timestamps = [now - timedelta(days=i) for i in range(len(scores))]
    return [
        {'stress_score': score, 'timestamp': ts, 'user_email': 'test@example.com'}
        for score, ts in zip(scores, timestamps)
    ]

# --- 1. Risk Service Tests (Z-Score Anomaly) ---

@patch('services.risk_service.get_db')
def test_risk_level_anomaly_detection(mock_get_db):
    """Verify that a sharp spike triggers CRITICAL even if below static threshold."""
    # Baseline: Low stress for 5 days (mean 20, std 0) -> then a spike to 65
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    history = create_mock_logs([20, 20, 20, 20, 20])
    mock_db['stress_logs'].find.return_value.sort.return_value.limit.return_value = history
    
    # Stress score 65 would normally be HIGH_RISK, 
    # but with a baseline of 20, it should trigger CRITICAL as an anomaly.
    risk = predict_risk_level(65, "I am feeling very different today", "test@example.com")
    assert risk == "CRITICAL_RISK"

@patch('services.risk_service.get_db')
def test_risk_level_static_threshold(mock_get_db):
    """Verify static thresholds still work correctly."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db['stress_logs'].find.return_value.sort.return_value.limit.return_value = []
    
    # 90 is always Critical
    assert predict_risk_level(90, "Normal message", "test@example.com") == "CRITICAL_RISK"
    # 45 is Moderate
    assert predict_risk_level(45, "Normal message", "test@example.com") == "MODERATE_RISK"

# --- 2. Prediction Service Tests (Linear Trend) ---

@patch('services.prediction_service.get_db')
def test_forecast_rising_trend(mock_get_db):
    """Verify rising trend projection."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Rising stress: 20, 30, 40, 50 over 4 days
    now = datetime.utcnow()
    logs = create_mock_logs([20, 30, 40, 50], [now - timedelta(days=3), now - timedelta(days=2), now - timedelta(days=1), now])
    mock_db['stress_logs'].find.return_value.sort.return_value = logs
    
    result = forecast_stress("test@example.com")
    assert result['trend'] == 'rising'
    assert result['forecast'][0]['score'] > 50  # Next day should be > last recorded score

@patch('services.prediction_service.get_db')
def test_forecast_declining_trend(mock_get_db):
    """Verify declining trend projection."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Falling stress: 80, 70, 60 over 3 days
    now = datetime.utcnow()
    logs = create_mock_logs([80, 70, 60], [now - timedelta(days=2), now - timedelta(days=1), now])
    mock_db['stress_logs'].find.return_value.sort.return_value = logs
    
    result = forecast_stress("test@example.com")
    assert result['trend'] == 'declining'
    assert result['forecast'][0]['score'] < 60

# --- 3. Burnout Service Tests ---

@patch('services.burnout_service.get_db')
def test_burnout_categorization_high_risk(mock_get_db):
    """Verify burnout detection with multiple factors (Anomaly + Sustained)."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Sustained high stress (all > 65)
    history = create_mock_logs([80, 85, 90, 85, 80])
    mock_db['stress_logs'].find.return_value.sort.return_value = history
    
    # Latest score is 80 (first item in history). 
    # Sustained high (+45) + latest > 70 (+15) = 60 (High)
    result = analyze_burnout_risk("test@example.com")
    assert result['risk_level'] == 'high'
    assert any("Sustained high stress" in f for f in result['factors'])

@patch('services.burnout_service.get_db')
def test_burnout_low_risk_baseline(mock_get_db):
    """Verify low risk when state matches baseline."""
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Stable moderate stress
    history = create_mock_logs([40, 42, 38, 41, 40])
    mock_db['stress_logs'].find.return_value.sort.return_value = history
    
    result = analyze_burnout_risk("test@example.com")
    assert result['risk_level'] == 'low'
    assert result['score'] < 30
