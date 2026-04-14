import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from aura.utils.database import get_db

logger = logging.getLogger(__name__)

# FIX #32: Replaced simple linear regression with Holt's exponential smoothing.
# This captures momentum and recent-trend changes better than y=mx+b while
# still being pure Python (no external deps like Prophet or statsmodels).


def _holt_forecast(y_vals: List[float], alpha: float = 0.4, beta: float = 0.2,
                   steps: int = 3) -> List[float]:
    """Holt's double exponential smoothing (additive trend, no seasonality).

    Args:
        y_vals: Historical score values (oldest → newest).
        alpha: Data smoothing factor (0 < α < 1). Higher = more recent-weighted.
        beta: Trend smoothing factor (0 < β < 1). Higher = trend reacts faster.
        steps: How many periods to forecast.

    Returns:
        List of forecasted values for the next `steps` periods.
    """
    if len(y_vals) < 2:
        return [y_vals[-1]] * steps if y_vals else [50.0] * steps

    # Initialise level and trend
    level = y_vals[0]
    trend = y_vals[1] - y_vals[0]

    for y in y_vals:
        prev_level = level
        level = alpha * y + (1 - alpha) * (prev_level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend

    # Forecast
    forecasts = []
    for h in range(1, steps + 1):
        forecasts.append(level + h * trend)
    return forecasts


def forecast_stress(user_email: str, days_ahead: int = 3) -> Dict[str, Any]:
    """
    Project future stress levels based on the last 14 days of history.
    Uses Holt's exponential smoothing for better trend capture than linear regression.

    Returns:
        Dict with 'forecast': list of {date, score} and 'confidence'.
    """
    try:
        db = get_db()
        if db is None:
            return {'forecast': [], 'confidence': 0, 'trend': 'stable'}

        # 1. Fetch history (last 14 days)
        cutoff = datetime.utcnow() - timedelta(days=14)
        logs = list(db['stress'].find({
            'user_email': user_email,
            'created_at': {'$gte': cutoff}
        }).sort('created_at', 1))

        if len(logs) < 3:
            return {
                'forecast': [],
                'confidence': 0,
                'trend': 'insufficient_data',
                'reason': 'Need at least 3 check-ins to generate a forecast.'
            }

        # 2. Extract scores
        y_vals = [log.get('score', 50) for log in logs]
        now = datetime.utcnow()

        # 3. Exponential smoothing forecast
        raw_forecast = _holt_forecast(y_vals, alpha=0.4, beta=0.2, steps=days_ahead)

        forecast = []
        for i, proj in enumerate(raw_forecast, start=1):
            future_date = now + timedelta(days=i)
            final_score = min(100, max(0, int(round(proj))))
            forecast.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'day': future_date.strftime('%a'),
                'score': final_score
            })

        # 4. Determine trend from smoothed slope
        if len(y_vals) >= 2:
            recent_diff = y_vals[-1] - y_vals[-2]
        else:
            recent_diff = 0

        trend = 'stable'
        if recent_diff > 2:
            trend = 'rising'
        elif recent_diff < -2:
            trend = 'declining'

        # 5. Confidence based on data density
        data_density = min(1.0, len(logs) / 10.0)
        confidence = int(data_density * 100)

        return {
            'forecast': forecast,
            'confidence': confidence,
            'trend': trend,
            'method': 'holt_exponential_smoothing',
            'last_recorded_score': y_vals[-1]
        }

    except Exception as e:
        logger.error("Stress forecasting error: %s", e, exc_info=True)
        return {'forecast': [], 'confidence': 0, 'trend': 'error'}

