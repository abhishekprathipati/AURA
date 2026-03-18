import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from utils.database import get_db

logger = logging.getLogger(__name__)

# TODO #32 (AI/ML): Simple Linear Regression Limitations
#   Current implementation uses basic linear regression (y = mx + b) for forecasting.
#   This approach has significant limitations:
#
#   1. Assumes linear trend - doesn't capture cyclical patterns (weekly, exam periods)
#   2. No seasonality modeling (stress varies by academic calendar)
#   3. Sensitive to outliers (one bad day skews the entire forecast)
#   4. Ignores external factors (upcoming exams, holidays, etc.)
#   5. No confidence intervals or uncertainty quantification
#
#   Recommended improvements:
#   - Use Prophet (Facebook) for time series with seasonality
#   - Implement ARIMA/SARIMA for more robust forecasting
#   - Add exponential smoothing (Holt-Winters) for trend + seasonality
#   - Consider LSTM/GRU neural networks for complex patterns
#   - Include external regressors (calendar events, assignment deadlines)
#   - Add ensemble methods combining multiple forecasters
#   - Implement proper cross-validation for model selection

def forecast_stress(user_email: str, days_ahead: int = 3) -> Dict[str, Any]:
    """
    Project future stress levels based on the last 14 days of history.
    Uses a simple linear trend projection (y = mx + b).
    
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
            # Not enough data to forecast
            return {
                'forecast': [],
                'confidence': 0,
                'trend': 'insufficient_data',
                'reason': 'Need at least 3 check-ins to generate a forecast.'
            }

        # 2. Prepare data for linear regression
        # X = days from now (negative), Y = score
        now = datetime.utcnow()
        x_vals = []
        y_vals = []

        for log in logs:
            days_diff = (log['created_at'] - now).total_seconds() / 86400.0
            x_vals.append(days_diff)
            y_vals.append(log.get('score', 50))

        # 3. Simple Linear Regression (y = mx + b)
        n = len(x_vals)
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)

        # Formula for slope (m) and intercept (b)
        denominator = (n * sum_x2 - sum_x**2)
        if abs(denominator) < 1e-6:
            # Avoid division by zero if all x are identical (shouldn't happen with timestamps)
            slope = 0
            intercept = sum_y / n
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n

        # 4. Generate forecast
        forecast = []
        last_score = y_vals[-1]
        
        for i in range(1, days_ahead + 1):
            future_date = now + timedelta(days=i)
            # Projected score based on trend
            proj_score = slope * i + intercept
            
            # Clamp value
            final_score = min(100, max(0, int(round(proj_score))))
            
            forecast.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'day': future_date.strftime('%a'),
                'score': final_score
            })

        # 5. Determine trend and confidence
        trend = 'stable'
        if slope > 0.5: trend = 'rising'
        elif slope < -0.5: trend = 'declining'
        
        # Confidence based on data density and fit (MSE)
        # Using a simple heuristic for now
        data_density = min(1.0, len(logs) / 10.0)
        confidence = int(data_density * 100)

        return {
            'forecast': forecast,
            'confidence': confidence,
            'trend': trend,
            'slope': round(slope, 2),
            'last_recorded_score': last_score
        }

    except Exception as e:
        logger.error("Stress forecasting error: %s", e, exc_info=True)
        return {'forecast': [], 'confidence': 0, 'trend': 'error'}
