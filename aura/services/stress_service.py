"""AURA Stress Calculation Engine v3.1
=====================================
Production-grade, multi-signal behavioral stress model with stabilization,
confidence scoring, explainability, adaptive intelligence, and nonlinear
logistic compression for bounded psychological realism.

Signals (base weights — adaptive redistribution when data is sparse):
  1. Mood entries     (35%)  — latest mood in 24h, temporal-decay aware
  2. Chat sentiment   (25%)  — NLP sentiment with diminishing-returns anti-spam
  3. Activity         (15%)  — inverted-U (Yerkes-Dodson) engagement curve
  4. Mood volatility  (10%)  — emotional swings over 48h (min 3 samples)
  5. Time-of-day bias  (5%)  — late-night activity penalty (IST-adjusted)
  6. Trend momentum   (10%)  — half-comparison 7-day direction

Pipeline:
  1. Each signal outputs 0-100 (higher = more stressed), double-clamped.
  2. Sparse-data detection: if ≤1 behavioral signal has data, use mood directly.
  3. Adaptive weight redistribution if any signal lacks data (normal mode only).
  4. Weighted sum → EMA-smoothed (sparse: 30/70, normal: 60/40).
  5. Logistic compression: S = 100 / (1 + e^(-k(S_ema - μ))), k=0.08, μ=50 (normal mode only).
  6. Z-score anomaly detection for spikes.
  7. Multi-condition institutional alert (score > 75 AND rising AND volatile).
  8. Confidence score + explainability fields returned.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from aura.utils.database import get_db
from aura.models.mood import MoodModel
from aura.models.stress import StressModel
from aura.models.chat import ChatModel
from aura.utils.alerts import send_institutional_alert
from config import Config
import math
import logging

log = logging.getLogger(__name__)

# ── Logistic Stabilization ───────────────────────────────────────────────────
LOGISTIC_K = 0.08     # compression sensitivity
LOGISTIC_MU = 50.0    # neutral midpoint

def _logistic_compress(score: float) -> int:
    """Apply bounded logistic stabilization to enforce psychological realism.
    Maps linear 0-100 → compressed 0-100 with soft ceiling/floor.
    S_final = 100 / (1 + e^(-k*(S_ema - μ)))
    Preserves relative ordering; prevents runaway escalation."""
    exponent = -LOGISTIC_K * (score - LOGISTIC_MU)
    compressed = 100.0 / (1.0 + math.exp(exponent))
    return max(0, min(100, int(round(compressed))))


# ── Signal 1: Mood Baselines ────────────────────────────────────────────────
MOOD_STRESS_MAP = {
    'happy':    15,
    'calm':     20,
    'normal':   40,
    'neutral':  40,
    'okay':     45,
    'sad':      65,
    'anxious':  72,
    'stressed': 78,
    'angry':    80,
    'depressed': 85,
    'panic':    90,
}

# ── Signal 2: Sentiment word lists (expanded) ───────────────────────────────
NEGATIVE_WORDS = frozenset({
    'stressed', 'anxious', 'anxiety', 'overwhelmed', 'tired', 'exhausted',
    'sad', 'panic', 'depressed', 'hopeless', 'afraid', 'scared', 'worry',
    'worried', 'nervous', 'dread', 'terrible', 'horrible', 'miserable',
    'lonely', 'frustrated', 'angry', 'furious', 'crying', 'helpless',
    'worthless', 'failing', 'struggling', 'breakdown', 'insomnia',
    'nightmare', 'trauma', 'suicidal', 'hurt', 'pain', 'suffering',
})

POSITIVE_WORDS = frozenset({
    'happy', 'good', 'great', 'better', 'confident', 'calm', 'relaxed',
    'prepared', 'ready', 'optimistic', 'proud', 'grateful', 'peaceful',
    'motivated', 'excited', 'cheerful', 'content', 'hopeful', 'strong',
    'focused', 'productive', 'accomplished', 'loved', 'supported',
    'well', 'fine', 'okay', 'improving', 'energetic', 'joyful',
})

INTENSIFIERS = frozenset({
    'very', 'extremely', 'really', 'so', 'incredibly', 'absolutely',
    'completely', 'totally', 'deeply', 'severely', 'seriously',
})

# ── Weight Configuration ────────────────────────────────────────────────────
WEIGHTS = {
    'mood':       0.35,
    'sentiment':  0.25,
    'activity':   0.15,
    'volatility': 0.10,
    'time_bias':  0.05,
    'trend':      0.10,
}


def _score_text_sentiment(text: str) -> float:
    """Score a text string for stress sentiment. Returns 0-100.

    TODO #31 (AI/ML): This is a basic keyword-matching approach. For production-grade
    sentiment analysis, consider using:
      - Hugging Face transformers (e.g., 'cardiffnlp/twitter-roberta-base-sentiment')
      - spaCy with sentiment extension
      - Fine-tuned BERT/RoBERTa for mental health domain
    A proper NLP model would capture context, negations, sarcasm, and nuanced language
    that keyword lists miss (e.g., "I'm not feeling great" vs "I'm feeling great").
    """
    if not text:
        return 50.0

    words = text.lower().split()
    
    neg_hits = sum(1 for w in words if w in NEGATIVE_WORDS)
    pos_hits = sum(1 for w in words if w in POSITIVE_WORDS)
    intensifier_count = sum(1 for w in words if w in INTENSIFIERS)
    
    # Amplify if intensifiers precede negative words
    neg_score = neg_hits * 12 + (intensifier_count * 5 if neg_hits > 0 else 0)
    pos_score = pos_hits * 10 + (intensifier_count * 3 if pos_hits > 0 else 0)
    
    # Base 50, shift by sentiment balance
    raw = 50 + neg_score - pos_score
    return max(0.0, min(100.0, raw))


def _signal_mood(user_email: str, db) -> Tuple[float, bool]:
    """Signal 1: Latest mood entry in last 24h with temporal decay.
    Returns (score, has_data) so the adaptive layer knows if data existed.
    Temporal decay: mood older than 6h decays linearly toward neutral (50).
    """
    since = datetime.utcnow() - timedelta(hours=24)
    now = datetime.utcnow()
    
    # Check main moods collection
    latest = db[MoodModel.collection_name].find_one(
        {'user_email': user_email, 'created_at': {'$gte': since}},
        sort=[('created_at', -1)]
    )
    
    if latest:
        mood_key = (latest.get('mood') or 'normal').lower()
        intensity = latest.get('intensity')
        base = MOOD_STRESS_MAP.get(mood_key, 50)
        # If intensity (1-10) is available, modulate: high intensity amplifies
        if isinstance(intensity, (int, float)) and 1 <= intensity <= 10:
            factor = (intensity - 5) / 5  # -0.8 to +1.0
            base = base + (base * factor * 0.3)
        
        # Temporal decay: mood freshness fades toward neutral over 24h
        age_hours = (now - latest['created_at']).total_seconds() / 3600
        if age_hours > 6:
            decay = min(1.0, (age_hours - 6) / 18)  # 0→1 over 6h-24h
            base = base * (1 - decay) + 50.0 * decay  # decay toward neutral
        
        return max(0.0, min(100.0, base)), True
    
    # Fallback: check student_wellness collection
    latest_sw = db['student_wellness'].find_one(
        {'student_id': user_email, 'data_type': 'mood', 'timestamp': {'$gte': since}},
        sort=[('timestamp', -1)]
    )
    if latest_sw:
        val = latest_sw.get('value', 3)
        score = max(0.0, min(100.0, 100 - (val * 18)))
        age_hours = (now - latest_sw.get('timestamp', now)).total_seconds() / 3600
        if age_hours > 6:
            decay = min(1.0, (age_hours - 6) / 18)
            score = score * (1 - decay) + 50.0 * decay
        return score, True
    
    return 50.0, False  # No data → neutral


def _signal_sentiment(user_email: str, db) -> Tuple[float, bool]:
    """Signal 2: Weighted sentiment from last 10 mental chats (recent = heavier).
    Anti-manipulation: diminishing returns cap prevents sentiment-spam attacks.
    Returns (score, has_data).
    """
    chats = list(
        db[ChatModel.collection_name]
        .find({'user_email': user_email, 'type': 'mental'})
        .sort('created_at', -1)
        .limit(10)
    )
    
    if not chats:
        return 50.0, False
    
    # Anti-manipulation: detect burst (>4 messages within 5 minutes)
    if len(chats) >= 2:
        newest = chats[0].get('created_at', datetime.utcnow())
        fourth = chats[min(3, len(chats) - 1)].get('created_at', newest)
        burst_window = (newest - fourth).total_seconds()
        is_burst = burst_window < 300 and len(chats) >= 4  # 4+ msgs in 5 min
    else:
        is_burst = False
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    for i, chat in enumerate(chats):
        # Exponential decay: most recent = weight 1.0, older = less
        weight = math.exp(-0.15 * i)
        
        # During burst: apply diminishing returns (sqrt flattening)
        if is_burst and i < 4:
            weight *= math.sqrt((i + 1) / 4)  # 0.5, 0.71, 0.87, 1.0
        
        text = (chat.get('message') or '') + ' ' + (chat.get('response') or '')
        
        # Fast-track: if the chat already contains an AI-predicted stress score, use it directly (AI Therapist Architecture)
        if 'stress_score' in chat:
            score = chat['stress_score']
            # Map predicted mood directly to amplify
            stored_sentiment = chat.get('sentiment', 'neutral').lower()
            if stored_sentiment in ['anxious', 'panic', 'fear']: 
                score = max(score, 80.0)
            elif stored_sentiment in ['sad', 'depressed', 'frustrated']:
                score = max(score, 70.0)
            elif stored_sentiment in ['happy', 'calm', 'joy']:
                score = min(score, 25.0)
        else:
            # Fallback for old chats
            stored_sentiment = chat.get('sentiment', '').lower()
            if stored_sentiment == 'anxious':
                score = 80.0
            elif stored_sentiment == 'negative':
                score = 70.0
            elif stored_sentiment == 'positive':
                score = 25.0
            else:
                score = _score_text_sentiment(text)
        
        weighted_sum += score * weight
        total_weight += weight
    
    raw = weighted_sum / total_weight if total_weight > 0 else 50.0
    return max(0.0, min(100.0, raw)), True


def _signal_activity(user_email: str, db) -> Tuple[float, bool]:
    """Signal 3: Activity frequency in last 48h.
    Uses inverted-U curve: balanced activity = low stress,
    no activity OR hyperactivity = higher stress.
    Returns (score, has_data).
    """
    since = datetime.utcnow() - timedelta(hours=48)
    
    # Count stress check-ins
    stress_count = db[StressModel.collection_name].count_documents(
        {'user_email': user_email, 'created_at': {'$gte': since}}
    )
    
    # Count mood entries
    mood_count = db[MoodModel.collection_name].count_documents(
        {'user_email': user_email, 'created_at': {'$gte': since}}
    )
    
    # Count chat interactions
    chat_count = db[ChatModel.collection_name].count_documents(
        {'user_email': user_email, 'created_at': {'$gte': since}}
    )
    
    # Count wellness check-ins
    wellness_count = db['student_wellness'].count_documents(
        {'student_id': user_email, 'timestamp': {'$gte': since}}
    )
    
    total = stress_count + mood_count + chat_count + wellness_count
    has_data = total > 0
    
    # Inverted-U (Yerkes-Dodson): optimal engagement ~5-8 actions/48h
    # 0 actions → disengaged (75), ramp down to sweet spot at ~6 (20),
    # then ramp back up for hyperactivity >15 (anxiety-driven)
    if total == 0:
        return 75.0, has_data
    elif total <= 2:
        return 60.0, has_data
    elif total <= 5:
        return 40.0, has_data
    elif total <= 8:
        return 20.0, has_data   # Sweet spot — balanced engagement
    elif total <= 12:
        return 30.0, has_data   # Slightly above optimal
    elif total <= 18:
        return 45.0, has_data   # Elevated — possible anxiety-driven usage
    elif total <= 25:
        return 60.0, has_data   # High — likely anxiety-driven
    else:
        return 72.0, has_data   # Hyperactive — strong anxiety signal


def _signal_volatility(user_email: str, db) -> Tuple[float, bool]:
    """Signal 4: Mood volatility over 48h. High swings = more stress.
    Returns (0.0, False) when sample size < 3 to avoid artificial std_dev spikes.
    """
    since = datetime.utcnow() - timedelta(hours=48)
    
    moods = list(
        db[MoodModel.collection_name]
        .find({'user_email': user_email, 'created_at': {'$gte': since}})
        .sort('created_at', 1)
    )
    
    # Need at least 3 samples for statistically meaningful volatility
    if len(moods) < 3:
        return 0.0, False  # Insufficient data → assume stable
    
    scores = [MOOD_STRESS_MAP.get((m.get('mood') or 'normal').lower(), 50) for m in moods]
    
    # Calculate standard deviation of mood scores
    n = len(scores)
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / n
    std_dev = math.sqrt(variance)
    
    # Also check max swing
    max_swing = max(scores) - min(scores)
    
    # std_dev 0-30 → stress 20-90, max_swing > 40 → bonus
    volatility_score = min(90.0, 20 + std_dev * 2.5)
    if max_swing > 40:
        volatility_score = min(95.0, volatility_score + 15)
    
    return max(0.0, min(100.0, volatility_score)), True


def _signal_time_bias(user_email: str = None) -> Tuple[float, bool]:
    """Signal 5: Late-night activity penalty (11 PM - 4 AM = higher stress).
    Always has data (time always exists), returns (score, True).

    FIX #17: Reads per-user timezone_offset from their profile.
    Falls back to Config.DEFAULT_TIMEZONE_OFFSET if not set.
    """
    now = datetime.utcnow()

    # FIX #17: Try per-user timezone first, then global default
    tz_offset_minutes = Config.DEFAULT_TIMEZONE_OFFSET
    if user_email:
        try:
            db = get_db()
            if db is not None:
                user = db['users'].find_one({'email': user_email}, {'timezone_offset': 1})
                if user and user.get('timezone_offset') is not None:
                    tz_offset_minutes = user['timezone_offset']
        except Exception:
            pass  # Fall back to default on any error

    # Convert UTC to local hour based on timezone offset
    local_hour = (now.hour * 60 + now.minute + tz_offset_minutes) // 60 % 24

    if 23 <= local_hour or local_hour < 4:
        return 75.0, True
    elif 4 <= local_hour < 6:
        return 60.0, True
    elif 22 <= local_hour < 23:
        return 55.0, True
    else:
        return 30.0, True


def _signal_trend(user_email: str, db) -> Tuple[float, bool]:
    """Signal 6: 7-day weighted trend. Rising stress → higher score.
    Handles edge cases: <2 entries, identical halves, zero averages.
    Returns (score, has_data).
    """
    since = datetime.utcnow() - timedelta(days=7)
    
    entries = list(
        db[StressModel.collection_name]
        .find({'user_email': user_email, 'created_at': {'$gte': since}})
        .sort('created_at', 1)
    )
    
    if len(entries) < 2:
        return 50.0, False  # Neutral — insufficient data
    
    scores = [e.get('score', 50) for e in entries]
    
    # Compare first half vs second half average
    n = len(scores)
    mid = max(n // 2, 1)  # Ensure at least 1 entry per half
    first_half_scores = scores[:mid]
    second_half_scores = scores[mid:]
    
    first_avg = sum(first_half_scores) / len(first_half_scores) if first_half_scores else 50.0
    second_avg = sum(second_half_scores) / len(second_half_scores) if second_half_scores else 50.0
    
    trend_direction = second_avg - first_avg  # positive = worsening
    
    # Map: -30 → 20, 0 → 50, +30 → 80
    trend_score = 50 + (trend_direction * 1.0)
    return max(0.0, min(100.0, trend_score)), True


def _adaptive_weights(data_flags: Dict[str, bool]) -> Dict[str, float]:
    """Redistribute weight from signals that lack data to signals that have it.
    If mood has no data, its 0.35 is spread proportionally across other active signals.
    This prevents 'phantom neutral' signals from anchoring the score.
    """
    base = dict(WEIGHTS)  # copy
    missing = {k for k, has in data_flags.items() if not has}
    present = {k for k, has in data_flags.items() if has}

    if not missing or not present:
        return base  # All present or all missing — keep defaults

    lost_weight = sum(base[k] for k in missing)
    present_total = sum(base[k] for k in present)

    for k in missing:
        base[k] = 0.0
    for k in present:
        base[k] += lost_weight * (base[k] / present_total) if present_total > 0 else 0

    return base


def _zscore_spike(user_email: str, db, current_score: float) -> bool:
    """Statistical anomaly detection using z-score.
    A reading is a spike if it is >2 standard deviations above the recent mean.
    Falls back to >20pt delta if insufficient history for z-score.
    """
    since = datetime.utcnow() - timedelta(days=7)
    recent = list(
        db[StressModel.collection_name]
        .find({'user_email': user_email, 'created_at': {'$gte': since}})
        .sort('created_at', -1)
        .limit(20)
    )

    scores = [r.get('score', 50) for r in recent if 'score' in r]

    if len(scores) < 5:
        # Fallback: simple delta from last reading
        if scores:
            return (current_score - scores[0]) > 20
        return False

    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance) if variance > 0 else 1.0

    z = (current_score - mean) / std_dev
    return z > 2.0  # >2 standard deviations = anomaly


def calculate_dynamic_stress(user_email: str, force_refresh: bool = False) -> Dict:
    """
    Main entry point: compute stress from all signals.

    Pipeline:
      1. Compute each signal → (score, has_data)
      2. Adaptive weight redistribution for missing data
      3. Weighted combination → raw score
      4. EMA stabilization against previous reading
      5. Z-score anomaly detection for spikes
      6. Multi-condition institutional alert
      7. Confidence + explainability

    Args:
        user_email: The user's email address
        force_refresh: If True, bypass the 5-minute cache and recompute stress.
                       Use this after mood updates or when fresh data is critical.

    Returns dict with:
      score, label, trend, signals, spike_detected, insight,
      confidence, dominant_factor, explanation, updated_at
    """
    db = get_db()
    coll = db[StressModel.collection_name]

    # ── Cache: reuse recent result if < 5 min old (prevents polling flood) ──
    # Use force_refresh=True to bypass cache when fresh calculation is needed
    # (e.g., after a mood entry, during crisis assessment, or for dashboard refresh)
    if not force_refresh:
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        cached = coll.find_one(
            {'user_email': user_email, 'created_at': {'$gte': five_min_ago}, 'source': 'dynamic_engine_v3.1'},
            sort=[('created_at', -1)]
        )
    else:
        cached = None
    if cached:
        score = cached.get('score', 50)
        if score <= 25:   _label = 'Relaxed'
        elif score <= 45: _label = 'Manageable'
        elif score <= 65: _label = 'Elevated'
        elif score <= 80: _label = 'High'
        else:             _label = 'Critical'
        _dom = cached.get('dominant_signal', 'mood')
        _expl = {
            'mood':       'Recent mood input is the primary stress driver.',
            'sentiment':  'Recent conversations show increased negative tone.',
            'activity':   'Engagement level is influencing your stress reading.',
            'volatility': 'Emotional variability is driving the current score.',
            'time_bias':  'Late-night activity is contributing to elevated stress.',
            'trend':      'The weekly trend direction is the dominant signal.',
        }
        return {
            'score': score,
            'label': _label,
            'trend': cached.get('trend', 'stable'),
            'signals': cached.get('signals', {}),
            'spike_detected': cached.get('spike', False),
            'insight': cached.get('insight') or _expl.get(_dom, ''),
            'confidence': cached.get('confidence', 0.5),
            'dominant_factor': _dom,
            'explanation': _expl.get(_dom, ''),
            'updated_at': cached['created_at'].isoformat() + 'Z',
        }

    # ── 1. Compute all signals (score, has_data) ─────────────────────────
    mood_result       = _signal_mood(user_email, db)
    sentiment_result  = _signal_sentiment(user_email, db)
    activity_result   = _signal_activity(user_email, db)
    volatility_result = _signal_volatility(user_email, db)
    time_result       = _signal_time_bias()
    trend_result      = _signal_trend(user_email, db)

    signals_raw = {
        'mood':       mood_result[0],
        'sentiment':  sentiment_result[0],
        'activity':   activity_result[0],
        'volatility': volatility_result[0],
        'time_bias':  time_result[0],
        'trend':      trend_result[0],
    }

    data_flags = {
        'mood':       mood_result[1],
        'sentiment':  sentiment_result[1],
        'activity':   activity_result[1],
        'volatility': volatility_result[1],
        'time_bias':  time_result[1],
        'trend':      trend_result[1],
    }

    # ── 2. Enforce normalization ─────────────────────────────────────────
    signals = {}
    for k, v in signals_raw.items():
        clamped = max(0.0, min(100.0, float(v)))
        signals[k] = round(clamped, 1)

    # ── 2b. Sparse-data detection ────────────────────────────────────────
    # Count *behavioral* signals with real data (exclude time_bias which is
    # always-on clock data, not user behavior).
    behavioral_flags = {k: v for k, v in data_flags.items() if k != 'time_bias'}
    real_signal_count = sum(1 for v in behavioral_flags.values() if v)
    sparse_mode = real_signal_count <= 1   # only mood (or nothing) has data

    # ── 3. Adaptive weight redistribution ────────────────────────────────
    weights = _adaptive_weights(data_flags)

    # ── 4. Weighted combination ──────────────────────────────────────────
    if sparse_mode and data_flags.get('mood'):
        # Sparse-data override: mood is the only real behavioral signal.
        # Use mood score directly to prevent time_bias/activity defaults
        # from inflating the score when the user explicitly logged a mood.
        computed_score = max(0, min(100, int(round(signals['mood']))))
    else:
        raw_score = sum(signals[k] * weights.get(k, 0) for k in signals)
        computed_score = max(0, min(100, int(round(raw_score))))

    # ── 5. EMA Stabilization ────────────────────────────────────────────
    # Sparse data → lower inertia (30/70) so new mood input has more
    # immediate effect.  Normal data → standard inertia (60/40).
    ema_prev_weight = 0.3 if sparse_mode else 0.6
    ema_new_weight  = 1.0 - ema_prev_weight

    coll = db[StressModel.collection_name]
    recent_two = list(coll.find({'user_email': user_email}).sort('created_at', -1).limit(2))

    prev_score = None
    if recent_two:
        prev_score = recent_two[0].get('score')
        if isinstance(prev_score, (int, float)):
            final_score = max(0, min(100, int(round(
                prev_score * ema_prev_weight + computed_score * ema_new_weight
            ))))
        else:
            prev_score = None
            final_score = computed_score
    else:
        final_score = computed_score

    # ── 5b. Logistic Compression (nonlinear bounded stabilization) ────────
    # Skip logistic when data is sparse — the μ=50 center pulls uncertain
    # readings toward mid-range, causing counter-intuitive jumps (e.g.
    # "Calm" mood → score increases).  Logistic is only beneficial when
    # enough signals provide a confident composite.
    pre_logistic = final_score
    if not sparse_mode:
        final_score = _logistic_compress(final_score)

    # ── Label ────────────────────────────────────────────────────────────
    if final_score <= 25:
        label = 'Relaxed'
    elif final_score <= 45:
        label = 'Manageable'
    elif final_score <= 65:
        label = 'Elevated'
    elif final_score <= 80:
        label = 'High'
    else:
        label = 'Critical'

    # ── Trend (compare to previous saved score) ──────────────────────────
    trend = 'stable'
    if prev_score is not None:
        diff = final_score - prev_score
        if diff > 8:
            trend = 'up'
        elif diff < -8:
            trend = 'down'

    # ── 6. Z-score spike detection ───────────────────────────────────────
    spike_detected = _zscore_spike(user_email, db, final_score)

    # ── Confidence Score ─────────────────────────────────────────────────
    confidence = _calculate_confidence(user_email, db, signals, data_flags)

    # ── Explainability ───────────────────────────────────────────────────
    dominant_key = max(signals, key=signals.get)
    explanation_map = {
        'mood':       'Recent mood input is the primary stress driver.',
        'sentiment':  'Recent conversations show increased negative tone.',
        'activity':   'Engagement level is influencing your stress reading.',
        'volatility': 'Emotional variability is driving the current score.',
        'time_bias':  'Late-night activity is contributing to elevated stress.',
        'trend':      'The weekly trend direction is the dominant signal.',
    }

    # ── Generate contextual insight ──────────────────────────────────────
    insight = _generate_insight(signals, final_score, trend, spike_detected)

    # ── Persist ──────────────────────────────────────────────────────────
    now = datetime.utcnow()
    stress_doc = {
        'user_email': user_email,
        'score': final_score,
        'pre_logistic': pre_logistic,
        'raw_score': computed_score,
        'sparse_mode': sparse_mode,
        'source': 'dynamic_engine_v3.1',
        'signals': signals,
        'weights_used': {k: round(v, 4) for k, v in weights.items()},
        'data_flags': data_flags,
        'confidence': round(confidence, 2),
        'dominant_signal': dominant_key,
        'spike': spike_detected,
        'trend': trend,
        'insight': insight,
        'created_at': now,
    }
    coll.insert_one(stress_doc)

    try:
        db['student_wellness'].insert_one({
            'student_id': user_email,
            'data_type': 'stress',
            'value': final_score,
            'timestamp': now,
            'source': 'dynamic_engine_v3.1',
        })
    except Exception as e:
        log.warning("Failed to insert student_wellness record: %s", e)

    # ── 7. STRESS ALERT PIPELINE ───────────────────────────────────────────────
    # Threshold: score > 70 → ALWAYS send email to proctor, parent AND student.
    # This is a hard rule regardless of trend direction.
    # Additional conditions for edge cases:
    #   - CRITICAL (>85): logged as CRITICAL in DB
    #   - SPIKE: z-score anomaly also triggers alert
    #   - VOLATILITY: score>65 + high volatility also triggers
    alert_sent = False
    alert_type = None

    if final_score > 85:
        alert_type = 'CRITICAL'
    elif final_score > 70:
        alert_type = 'HIGH_STRESS'
    elif spike_detected:
        alert_type = 'SPIKE'
    elif final_score > 65 and signals.get('volatility', 0) > 50:
        alert_type = 'VOLATILITY'

    if alert_type:
        try:
            result = send_institutional_alert(user_email, final_score)
            alert_sent = result.get('success', False)
            if alert_sent:
                log.warning('%s ALERT sent for %s: score=%d (proctor=%s, parent=%s, student=%s)',
                            alert_type, user_email, final_score,
                            result.get('proctor_sent'), result.get('parent_sent'), result.get('student_sent'))
            else:
                log.error('%s ALERT failed for %s: %s', alert_type, user_email, result.get('message'))
        except Exception as e:
            log.error('Failed to send %s alert for %s: %s', alert_type, user_email, e)

    return {
        'score': final_score,
        'label': label,
        'trend': trend,
        'signals': signals,
        'spike_detected': spike_detected,
        'insight': insight,
        'confidence': round(confidence, 2),
        'dominant_factor': dominant_key,
        'explanation': explanation_map.get(dominant_key, ''),
        'updated_at': now.isoformat() + 'Z',
    }


def get_stress_history(user_email: str, days: int = 7) -> List[Dict]:
    """Fetch stress history bucketed by day."""
    db = get_db()
    coll = db[StressModel.collection_name]
    since = datetime.utcnow() - timedelta(days=days)
    
    cursor = coll.find(
        {'user_email': user_email, 'created_at': {'$gte': since}},
        {'_id': 0, 'created_at': 1, 'score': 1, 'signals': 1, 'source': 1}
    ).sort('created_at', 1)
    
    # Bucket by day, keep latest per day
    from collections import OrderedDict
    buckets = OrderedDict()
    
    for doc in cursor:
        ts = doc['created_at']
        day = ts.date()
        buckets[day] = {
            'timestamp': ts.isoformat() + 'Z',
            'score': int(doc.get('score', 50)),
            'signals': doc.get('signals'),
            'source': doc.get('source', 'unknown'),
        }
    
    return list(buckets.values())


def get_weekly_stats(user_email: str) -> Dict:
    """Compute 7-day statistics: avg, peak, low, trend direction, streak."""
    db = get_db()
    coll = db[StressModel.collection_name]
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)
    
    # This week
    this_week = list(coll.find(
        {'user_email': user_email, 'created_at': {'$gte': week_ago}},
        {'score': 1}
    ))
    this_scores = [d['score'] for d in this_week if 'score' in d]
    
    # Previous week
    prev_week = list(coll.find(
        {'user_email': user_email, 'created_at': {'$gte': prev_week_start, '$lt': week_ago}},
        {'score': 1}
    ))
    prev_scores = [d['score'] for d in prev_week if 'score' in d]
    
    this_avg = round(sum(this_scores) / len(this_scores)) if this_scores else 0
    prev_avg = round(sum(prev_scores) / len(prev_scores)) if prev_scores else 0
    
    if prev_avg > 0:
        change_pct = round(((this_avg - prev_avg) / prev_avg) * 100)
    else:
        change_pct = 0
    
    return {
        'average': this_avg,
        'peak': max(this_scores) if this_scores else 0,
        'low': min(this_scores) if this_scores else 0,
        'readings_count': len(this_scores),
        'prev_week_avg': prev_avg,
        'change_pct': change_pct,
        'change_direction': 'up' if change_pct > 5 else ('down' if change_pct < -5 else 'stable'),
    }


def _calculate_confidence(user_email: str, db, signals: Dict, data_flags: Dict[str, bool]) -> float:
    """Calculate confidence (0.0-1.0) based on data availability, sample size,
    and signal consistency. Uses data_flags from adaptive layer.
    All factors clamped individually; total clamped to [0.0, 1.0]."""
    now = datetime.utcnow()
    since_7d = now - timedelta(days=7)

    # Factor 1: Data availability (0-0.4)
    # Uses actual data_flags from signal computation
    sources_present = sum(1 for v in data_flags.values() if v)
    total_sources = max(len(data_flags), 1)
    data_score = max(0.0, min(0.4, (sources_present / total_sources) * 0.4))

    # Factor 2: Sample size (0-0.35)
    readings_7d = db[StressModel.collection_name].count_documents(
        {'user_email': user_email, 'created_at': {'$gte': since_7d}}
    )
    sample_score = max(0.0, min(0.35, (min(readings_7d, 10) / 10) * 0.35))

    # Factor 3: Signal consistency (0-0.25)
    vals = [v for v in signals.values() if isinstance(v, (int, float))]
    if len(vals) >= 2:
        mean_s = sum(vals) / len(vals)
        var_s = sum((v - mean_s) ** 2 for v in vals) / len(vals)
        std_s = math.sqrt(var_s)
        consistency = max(0.05, min(0.25, 0.25 - (std_s / 30) * 0.20))
    else:
        consistency = 0.05  # Single signal = low consistency

    # Zero-data guard: if no sources at all, confidence is near-zero
    if sources_present == 0:
        return 0.05

    return max(0.0, min(1.0, data_score + sample_score + consistency))


def _generate_insight(signals: Dict, score: int, trend: str, spike: bool) -> str:
    """Generate a human-readable insight based on signal analysis."""
    parts = []
    
    if spike:
        parts.append('⚠ Sudden stress spike detected.')
    
    # Identify dominant signal
    dominant = max(signals, key=signals.get)
    dominant_val = signals[dominant]
    
    if dominant == 'mood' and dominant_val > 65:
        parts.append('Your recent mood is driving stress up.')
    elif dominant == 'sentiment' and dominant_val > 65:
        parts.append('Your chat conversations suggest elevated concern.')
    elif dominant == 'activity' and dominant_val > 60:
        # Distinguish between disengagement and hyperactivity
        if dominant_val >= 70:
            parts.append('Your activity pattern suggests possible anxiety-driven usage or disengagement.')
        else:
            parts.append('Low engagement detected — try a quick check-in or breathing exercise.')
    elif dominant == 'volatility' and dominant_val > 65:
        parts.append('Your mood has been fluctuating significantly. Stability helps.')
    elif dominant == 'time_bias' and dominant_val > 60:
        parts.append('Late-night activity can increase stress. Consider winding down.')
    elif dominant == 'trend' and dominant_val > 65:
        parts.append('Your stress has been climbing steadily this week.')
    
    if trend == 'up' and not spike:
        parts.append('Stress has been trending upward this week.')
    elif trend == 'down':
        parts.append('Your stress is improving — keep it up!')
    
    if score <= 30:
        parts.append('You\'re in a great zone. Maintain your routine.')
    elif score <= 50:
        parts.append('Things are manageable. Stay proactive.')
    elif score > 70:
        parts.append('Consider reaching out for support or trying a relaxation exercise.')
    
    return ' '.join(parts) if parts else 'Stress is within normal range.'


# ── Legacy compatibility wrapper ─────────────────────────────────────────────
def calculate_daily_stress(user_email: str) -> int:
    """Legacy function. Now delegates to the dynamic engine."""
    result = calculate_dynamic_stress(user_email)
    return result['score']
