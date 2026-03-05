# AURA Stress Calculation Engine — Technical Documentation

**Version:** 3.1  
**Module:** `services/stress_service.py`  
**Last Updated:** February 2026

---

## 1. Overview

AURA calculates stress using a **weighted multi-signal behavioral model** combining mood input, conversational sentiment analysis, engagement activity, emotional volatility, time-based context, and trend momentum. Each signal is normalized to a 0–100 scale. The model applies **adaptive weight redistribution** when data is sparse, **EMA smoothing** to prevent oscillation, **logistic compression** for bounded nonlinear stabilization, and returns a **confidence score** reflecting data availability and signal consistency.

---

## 2. Formal Mathematical Model

### 2.1 Overall Stress Score

The composite stress score at time *t* is computed through a three-stage pipeline:

**Stage 0 — Sparse-Data Detection (§3.5):**

If only ≤1 behavioral signal has data (e.g., mood-only), the engine enters **sparse mode**: the mood score is used directly, EMA inertia is reduced to 30/70, and logistic compression is skipped.

**Stage 1 — EMA Smoothing:**

$$S_t^{\text{ema}} = \alpha \cdot S_{t-1} + (1 - \alpha) \cdot \hat{S}_t$$

**Stage 2 — Logistic Compression (§2.10, normal mode only):**

$$S_t = \frac{100}{1 + e^{-k(S_t^{\text{ema}} - \mu)}}$$

where:

- $S_t$ = final bounded stress score at time $t$
- $S_t^{\text{ema}}$ = EMA-smoothed score
- $S_{t-1}$ = previously persisted score
- $\hat{S}_t$ = raw weighted combination of signals at time $t$
- $\alpha = 0.6$ normal mode, $0.3$ sparse mode (EMA smoothing coefficient)
- $k = 0.08$ (logistic steepness)
- $\mu = 50.0$ (inflection point)

### 2.2 Raw Score Computation

$$\hat{S}_t = \sum_{i=1}^{n} w_i^{*} \cdot x_i$$

where:

- $x_i \in [0, 100]$ = normalized signal value for signal $i$
- $w_i^{*}$ = adaptive weight for signal $i$ (see §2.3)
- $n = 6$ (number of signals)

### 2.3 Adaptive Weight Redistribution

Let $D \subseteq \{1, \dots, n\}$ be the set of signals with available data, and $M = \{1, \dots, n\} \setminus D$ the missing set.

For signals with data ($i \in D$):

$$w_i^{*} = w_i + \frac{w_i}{\sum_{j \in D} w_j} \cdot \sum_{k \in M} w_k$$

For signals without data ($i \in M$):

$$w_i^{*} = 0$$

This guarantees $\sum_{i=1}^{n} w_i^{*} = 1$ and prevents phantom neutral anchoring.

### 2.4 Signal Definitions

| Signal $x_i$ | Base Weight $w_i$ | Domain | Source |
|:---:|:---:|:---:|:---|
| $x_1$ (Mood) | 0.35 | Self-report + temporal decay | moods collection |
| $x_2$ (Sentiment) | 0.25 | NLP + burst detection | chats (mental) |
| $x_3$ (Activity) | 0.15 | Yerkes-Dodson inverted-U | Cross-collection count |
| $x_4$ (Volatility) | 0.10 | $\sigma$ of mood scores | moods (48h window) |
| $x_5$ (Time bias) | 0.05 | IST clock mapping | System clock |
| $x_6$ (Trend) | 0.10 | Half-comparison direction | stress (7d window) |

### 2.5 Temporal Decay (Signal 1)

For mood entries older than $\tau_0 = 6$ hours within a $T = 24$ hour window:

$$x_1 = b \cdot (1 - \delta) + 50 \cdot \delta$$

where $b$ = base mood score and $\delta = \min\left(1,\; \frac{t_{age} - \tau_0}{T - \tau_0}\right)$.

### 2.6 Anti-Manipulation (Signal 2)

Burst detection threshold: $\geq 4$ messages within 300 seconds.

During burst, the $i$-th most recent message weight is attenuated:

$$w_{\text{chat},i} = e^{-0.15i} \cdot \sqrt{\frac{i + 1}{4}} \quad \text{for } i \in \{0,1,2,3\}$$

This produces weights $\{0.5, 0.71, 0.87, 1.0\}$ — suppressing repeated spam.

### 2.7 Inverted-U Activity Curve (Signal 3)

Based on the Yerkes-Dodson law, activity stress follows an inverted-U:

$$x_3 = f_{\text{YD}}(a) = \begin{cases} 75 & a = 0 \\ 20 & 5 \leq a \leq 8 \\ \text{monotonically increasing} & a > 8 \end{cases}$$

where $a$ = total cross-collection action count in 48 hours.

### 2.8 Z-Score Anomaly Detection

A spike is flagged when the current score deviates significantly from the recent distribution:

$$z = \frac{S_t - \mu_{7d}}{\sigma_{7d}} > 2.0$$

where $\mu_{7d}$ and $\sigma_{7d}$ are computed from the last 20 readings within 7 days. Falls back to $|S_t - S_{t-1}| > 20$ when $n < 5$.

### 2.9 Confidence Score

$$C = \underbrace{\frac{|D|}{n} \cdot 0.4}_{\text{data availability}} + \underbrace{\frac{\min(r, 10)}{10} \cdot 0.35}_{\text{sample size}} + \underbrace{\left(0.25 - \frac{\sigma_x}{30} \cdot 0.20\right)}_{\text{consistency}}$$

where $r$ = readings in 7 days, $\sigma_x$ = std. dev. of signal values, each factor clamped individually. Zero-data guard: $C = 0.05$ when $|D| = 0$.

### 2.10 Nonlinear Stabilization (Logistic Compression)

After EMA smoothing, the score passes through a logistic sigmoid:

$$S_{\text{final}} = \frac{100}{1 + e^{-k(S_{\text{ema}} - \mu)}}$$

where $k = 0.08$ (steepness) and $\mu = 50.0$ (inflection midpoint).

**Properties:**

| Input ($S_{\text{ema}}$) | Output ($S_{\text{final}}$) | Effect |
|:---:|:---:|:---|
| 0 | 1.8 | Soft floor — prevents exact zero |
| 25 | 11.9 | Low-stress compression |
| 50 | 50.0 | Identity at midpoint |
| 75 | 88.1 | High-stress amplification |
| 90 | 96.1 | Approaching soft ceiling |
| 100 | 98.2 | Soft ceiling — never reaches 100 |

**Derivative at midpoint:** $S'(\mu) = k \cdot 100 / 4 = 2.0$ — the maximum discrimination gradient is at 50, where clinical ambiguity is highest.

**Rationale:**
1. **Bounded psychological realism** — Stress is fundamentally bounded; a person cannot be "more than maximally stressed." The logistic enforces this without hard clipping.
2. **Mid-range amplification** — The steepest gradient around $\mu = 50$ increases discrimination precisely where clinical ambiguity is greatest.
3. **Monotonicity preservation** — The sigmoid is strictly monotonically increasing, so ordinal ranking of scores is preserved.
4. **Smooth gradient** — Unlike hard `clamp(0, 100)`, the logistic provides a $C^{\infty}$ smooth compression with no discontinuities.

The `pre_logistic` score is persisted in every database record for auditing and inverse recovery.

---

## 3. Signal Definitions (Detailed)

### Signal 1 — Mood (Base Weight: 35%)

| Source | Method |
|--------|--------|
| `moods` collection | Latest mood entry within 24h |
| `student_wellness` (`data_type: mood`) | Fallback if primary missing |

- Maps mood string (`happy`, `sad`, `anxious`, etc.) to a base stress value via `MOOD_STRESS_MAP`.
- **Intensity modulation:** If the user provides intensity (1–10), the base value is shifted ±30% proportionally.
- **Temporal decay:** Mood entries older than 6 hours decay linearly toward neutral (50) over the remaining 18h window. This prevents stale mood data from dominating.

**Formula:**
```
base = MOOD_STRESS_MAP[mood_key]
if intensity: base += base × ((intensity - 5) / 5) × 0.3
if age > 6h: base = base × (1 - decay) + 50 × decay
    where decay = min(1, (age_hours - 6) / 18)
```

### Signal 2 — Chat Sentiment (Base Weight: 25%)

| Source | Method |
|--------|--------|
| `chats` collection (`type: mental`) | Last 10 messages, exponential decay |

- Uses stored `sentiment` field (from `extract_sentiment()`) as primary signal.
- Falls back to `_score_text_sentiment()` — keyword-based NLP that scans for negative/positive/intensifier words.
- **Exponential decay:** Most recent message has weight 1.0; weight decays by `e^(-0.15 × index)`.
- **Anti-manipulation:** Detects burst patterns (≥4 messages in <5 minutes). During burst, applies `√(i/4)` diminishing returns to recent messages, preventing a user from spamming negative messages to artificially inflate the score.

**Formula:**
```
score_i = sentiment_map[stored] or keyword_score(text)
weight_i = e^(-0.15 × i)
if burst: weight_i *= √((i+1) / 4) for i < 4
result = Σ(score_i × weight_i) / Σ(weight_i)
```

### Signal 3 — Activity (Base Weight: 15%)

| Source | Method |
|--------|--------|
| `stress`, `moods`, `chats`, `student_wellness` | Count all entries in 48h |

Uses an **inverted-U (Yerkes-Dodson) curve**:

| Actions in 48h | Stress Score | Interpretation |
|:-:|:-:|:--|
| 0 | 75 | Disengaged |
| 1–2 | 60 | Low engagement |
| 3–5 | 40 | Below optimal |
| **5–8** | **20** | **Sweet spot** |
| 9–12 | 30 | Slightly above optimal |
| 13–18 | 45 | Possible anxiety-driven |
| 19–25 | 60 | Likely anxiety-driven |
| 25+ | 72 | Hyperactive anxiety signal |

**Justification:** Linear models (`more activity = less stress`) fail to capture anxiety-driven hyperactivity. The Yerkes-Dodson law from psychology establishes that performance (and well-being) follows an inverted-U with respect to arousal/engagement.

### Signal 4 — Volatility (Base Weight: 10%)

| Source | Method |
|--------|--------|
| `moods` collection | All entries in 48h |

- Requires **≥3 samples**. With fewer, returns `0.0` (stable) to avoid artificial std_dev inflation.
- Computes `σ` (standard deviation) of mapped mood scores.
- Adds bonus if max swing > 40 points.

**Formula:**
```
if n < 3: return 0
σ = std_dev(mood_scores)
max_swing = max(scores) - min(scores)
volatility = min(90, 20 + σ × 2.5)
if max_swing > 40: volatility = min(95, volatility + 15)
```

### Signal 5 — Time Bias (Base Weight: 5%)

| Source | Method |
|--------|--------|
| System clock | IST-adjusted hour |

| IST Hour | Score |
|:-:|:-:|
| 23:00–04:00 | 75 |
| 04:00–06:00 | 60 |
| 22:00–23:00 | 55 |
| 06:00–22:00 | 30 |

**Justification:** Late-night platform usage correlates with disrupted sleep patterns, which is a known stress amplifier. The low weight (5%) ensures it influences but never dominates.

### Signal 6 — Trend Momentum (Base Weight: 10%)

| Source | Method |
|--------|--------|
| `stress` collection | All readings in 7 days |

- Splits readings into first-half and second-half.
- Computes average of each half.
- Maps the direction to a score centered on 50.

**Formula:**
```
if n < 2: return 50 (neutral)
trend_direction = second_half_avg - first_half_avg
trend_score = clamp(50 + trend_direction, 0, 100)
```

---

## 3. Adaptive Weight Redistribution

When a signal **lacks data** (`has_data = False`), its weight is redistributed proportionally across signals that have data. This prevents phantom neutral values (50) from anchoring the final score.

**Example:**
```
If mood has no data (weight 0.35 lost):
  sentiment: 0.25 → 0.25 + 0.35 × (0.25/0.65) = 0.3846
  activity:  0.15 → 0.15 + 0.35 × (0.15/0.65) = 0.2308
  ...and so on
```

---

## 3.5 Sparse-Data Bypass

**Problem:** When a student has minimal data (e.g. just logged a mood for the first time), the pipeline can produce counter-intuitive results:

1. Adaptive redistribution concentrates weight on the few available signals (including always-on `time_bias`)
2. EMA with high inertia (60%) anchors to stale/inflated previous scores
3. Logistic compression centered at μ=50 pulls uncertain readings toward mid-range

This means logging "Calm" can cause a jump **upward** — mathematically valid but UX-inappropriate.

**Solution:** When ≤1 *behavioral* signal has data (excluding `time_bias`, which is clock-based, not user behavior), the engine enters **sparse mode**:

| Behavior | Normal Mode | Sparse Mode |
|:---|:---|:---|
| Score computation | Weighted combination of all signals | Mood score used directly |
| EMA inertia | 60% previous / 40% new | 30% previous / 70% new |
| Logistic compression | Applied (k=0.08, μ=50) | Skipped |

**Result:** Calm mood → low stress (immediately intuitive). As the student accumulates more data, the full multi-signal pipeline activates automatically.

The `sparse_mode` flag is persisted in every DB record for auditing.

---

## 4. EMA Stabilization

**Formula (normal mode):** `final = previous_score × 0.6 + computed_score × 0.4`
**Formula (sparse mode):** `final = previous_score × 0.3 + computed_score × 0.7`

**Why two modes?**
- **Normal (0.6/0.4):** Prevents dramatic oscillation from single-input noise. Standard in production wellness systems.
- **Sparse (0.3/0.7):** When only 1 behavioral signal has data, the new input should have immediate effect. A calm mood should make the score drop, not be anchored to a stale previous value.

**Trade-off acknowledged:** If a student genuinely improves dramatically, the normal-mode system will lag by 1–2 readings. This is acceptable for wellness modeling where false spikes are more harmful than delayed recognition of improvement. In sparse mode, the lag is eliminated.

The `raw_score` (pre-smoothing) is persisted in every DB record for auditing.

---

## 4.5 Nonlinear Stabilization (Logistic Compression)

After EMA smoothing but before label assignment, the score passes through a bounded logistic sigmoid:

**Formula:** `final = 100 / (1 + exp(-0.08 * (ema_score - 50)))`

**Parameters:**
- $k = 0.08$ — steepness coefficient. Chosen to produce a soft ceiling at ~98 and soft floor at ~2 while maintaining near-linear behavior in the 30–70 range.
- $\mu = 50.0$ — inflection midpoint. At this point, $S_{\text{final}} = S_{\text{ema}} = 50$ (identity).

**Why logistic and not linear clipping?**

A hard `clamp(0, 100)` creates discontinuities in the gradient at the boundaries. The logistic provides a $C^{\infty}$ smooth compression that:

1. **Amplifies mid-range discrimination** — The steepest gradient ($S' = 2.0$) is at 50, where clinical interpretation is most ambiguous. Scores near 50 are spread apart, improving label boundary precision.
2. **Compresses extremes** — Very high (>90) and very low (<10) scores are compressed toward the boundaries, reflecting that the distinction between "score 95 vs 100" is clinically meaningless while "score 45 vs 55" is diagnostically significant.
3. **Provides soft ceiling/floor** — The output asymptotically approaches but never reaches 0 or 100, preventing false certainty at the boundaries.

**Evaluation impact (from the quantitative evaluation):**
- Raw variance: 581.5 → EMA variance: 22.0 → Logistic variance: 45.8
- Total variance reduction (raw → logistic): **92.1%**
- The logistic stage slightly increases variance compared to pure EMA (due to mid-range amplification) but provides bounded output and superior discrimination.

The `pre_logistic` score is persisted alongside the final score for auditing and inverse recovery.

---

## 5. Spike Detection (Z-Score Anomaly)

Instead of a naive `>20pt jump` check, spikes are detected using **z-score analysis**:

```
z = (current_score - mean_7d) / σ_7d
spike = z > 2.0
```

- Uses last 20 readings from the past 7 days.
- If fewer than 5 readings exist, falls back to simple `>20pt delta`.
- A z-score > 2.0 means the reading is in the top ~2.3% of the student's recent distribution — a statistically significant anomaly.

---

## 6. Institutional Alert Logic

**Multi-condition trigger** (replaces simple `score > 80`):

```
Alert if:
  (score > 75 AND trend == 'up' AND volatility_signal > 55)
  OR score > 90 (safety net)
```

**Justification:** Single-dimension thresholds cause false positives. A score of 78 with stable trend and low volatility may indicate a student who consistently operates at elevated stress but is coping. Combining score + direction + emotional instability identifies students who are genuinely deteriorating.

---

## 7. Confidence Score

Range: **0.00 – 1.00**, clamped.

| Factor | Max Weight | Derivation |
|--------|:-:|:--|
| Data availability | 0.40 | % of signals with `has_data = True` |
| Sample size | 0.35 | `min(readings_7d, 10) / 10` |
| Signal consistency | 0.25 | Inverse of inter-signal σ |

**Zero-data guard:** If no data sources present at all, returns `0.05` (near-zero confidence).

**Use:** Displayed to the student as a confidence badge. Low confidence (<50%) shown in amber, signaling "the system needs more data to be accurate."

---

## 8. Anti-Manipulation

**Threat:** A student sends 10 extremely negative messages in 60 seconds to inflate sentiment.

**Defense:** Burst detection (≥4 messages in <5 minutes) triggers diminishing returns:
```
During burst, weight_i *= √((i + 1) / 4) for the 4 most recent messages
```
This means the first burst message gets weight × 0.5, the fourth gets weight × 1.0. Repeated signals contribute progressively less, preventing score manipulation while still reflecting genuine distress.

---

## 9. Weight Justification

| Signal | Weight | Rationale |
|--------|:------:|:----------|
| Mood | 35% | Direct self-report; highest ecological validity |
| Sentiment | 25% | Implicit signal from natural conversation; second-strongest behavioral indicator |
| Activity | 15% | Engagement pattern; informative but indirect |
| Volatility | 10% | Important for instability detection but noisy in small samples |
| Trend | 10% | Directional momentum; useful but derived from the score itself (circular risk if overweighted) |
| Time | 5% | Contextual modifier; should never dominate |

Weights sum to **1.00**. Adaptive redistribution preserves this invariant.

---

## 10. Data Flow

```
User Action (mood/chat/check-in)
       ↓
Signal Functions → (score, has_data) tuples
       ↓
Adaptive Weight Redistribution
       ↓
Weighted Sum → Raw Score (0-100)
       ↓
EMA Smoothing (0.6 prev + 0.4 new) → Final Score
       ↓
Z-Score Spike Detection
       ↓
Confidence Calculation
       ↓
Explainability (dominant_factor + explanation)
       ↓
Persist to DB → Return JSON to API
       ↓
Multi-Condition Alert Check
```

---

## 11. API Response Schema

```json
{
  "score": 62,
  "label": "Elevated",
  "trend": "up",
  "signals": {
    "mood": 72.0,
    "sentiment": 65.3,
    "activity": 40.0,
    "volatility": 55.0,
    "time_bias": 30.0,
    "trend": 58.0
  },
  "spike_detected": false,
  "insight": "Your recent mood is driving stress up. Stress has been trending upward.",
  "confidence": 0.72,
  "dominant_factor": "mood",
  "explanation": "Recent mood input is the primary stress driver.",
  "updated_at": "2026-02-13T10:30:00Z"
}
```

---

## 12. Ethical Disclaimer

AURA provides **wellness estimation support only** and does not constitute medical or psychological diagnosis. The stress score is a behavioral approximation derived from user-provided data and platform activity. It should not be used as a sole basis for clinical decisions.

Institutional alerts are designed as early-warning signals for proctors/counselors and should always be followed by human evaluation. All emotional data is persisted with consent-based governance and is not shared outside the institution.

---

## 13. Limitations & Future Work

- **No ML dependency:** Entirely rule-based. Intentional — avoids black-box criticism for academic/institutional context.
- **EMA lag:** Genuine rapid improvement is reflected with 1-2 reading delay. Acceptable trade-off for oscillation prevention.
- **Time bias assumes IST:** Hardcoded +5:00 offset. Should be user-timezone-aware in production.
- **Future candidates:** Per-student adaptive thresholds, clustering-based peer comparison, long-term trend forecasting.
---

## 14. Simulation & Validation

A **synthetic simulation runner** (`tools/simulate.py`) validates the engine against 10 behavioral archetypes:

| Profile | Description | Expected Score Range |
|---------|-------------|---------------------|
| `calm_student` | Happy moods, positive chats, stable history | 10–42 |
| `high_stress` | Anxious/depressed moods, negative chats, rising history | 55–95 |
| `night_owl` | Normal moods, late-night activity | 20–60 |
| `spam_manipulator` | 6 positive-burst messages in 3min after negative baseline | 35–80 |
| `ghost_student` | Zero data across all signals | 25–75 (conf < 0.15) |
| `volatile_student` | Wildly fluctuating moods (happy→panic→calm→angry) | 25–70 |
| `recovering` | Declining stress history over 7 days | 15–50 |
| `data_rich` | 12 moods, 5 chats, 14 readings, 3 wellness entries | 15–55 (conf > 0.50) |
| `extreme_crisis` | Every signal maxed (panic, suicidal chats, hyperactivity) | 70–100 |
| `fresh_student` | Single mood entry only | 20–65 (conf < 0.35) |

### Running the Simulation

```bash
python -m tools.simulate              # All profiles
python -m tools.simulate --profile calm high_stress  # Specific profiles
python -m tools.simulate --keep-data  # Skip cleanup (debug)
python -m tools.simulate --list       # List profiles
```

### What It Validates

- Score within expected range per archetype
- Label correctness (Relaxed/Manageable/Elevated/High/Critical)
- Confidence bounds (zero-data → 0.05, data-rich → 0.90+)
- Dominant factor attribution
- Spike detection behavior
- Signal normalization (all values 0–100)
- API response field completeness
- Anti-manipulation effectiveness (spam profile)
- Adaptive weight redistribution (ghost profile)
- Graceful degradation with minimal data (fresh profile)

---

## 16. Quantitative Evaluation Results

Evaluation framework: `tools/evaluate.py` — runs 5 test suites comparing AURA v3 against a mood-only baseline.

### 16.1 Manipulation Resistance

| Metric | Value |
|--------|------:|
| Naive avg sentiment (no burst detection) | 36.2 |
| AURA v3 sentiment (burst-adjusted) | 33.2 |
| Burst suppression | 22.2% |
| V3 mood signal (ground truth) | 92.0 |
| Mood-only baseline score | 78 |
| AURA v3 final score | 63 |

The mood signal (92) correctly dominates over the manipulated sentiment signal (33). Burst detection suppresses the attempted positive-spam by 22.2%.

### 16.2 EMA Stability

Input: 10 alternating happy/stressed moods.

| Metric | Raw (inferred) | EMA-smoothed |
|--------|:-:|:-:|
| Variance | 443.6 | 58.8 |
| Range (max−min) | 47 | 26 |
| **Variance reduction** | — | **86.7%** |

EMA smoothing eliminates 87% of oscillation variance while preserving signal direction.

### 16.3 Crisis Sensitivity

Starting from calm baseline (5 readings at score=25), progressive crisis injection:

| Reading | Score | Threshold |
|:---:|:---:|:---|
| 1 | 42 | — |
| 2 | 52 | — |
| 3 | 57 | **Elevated (≥55)** |
| 4 | 63 | — |
| 5 | 68 | **High (≥65)** |
| 6 | 72 | — |

The engine reaches Elevated within **3 readings** and High within **5 readings**, demonstrating appropriate sensitivity balanced against EMA dampening.

### 16.4 Confidence Calibration

| Level | Data | Docs | Confidence |
|:---:|:---|:---:|:---:|
| L0 | Zero data | 0 | 0.15 |
| L1 | 1 mood | 1 | 0.30 |
| L2 | 1 mood + 1 chat | 2 | 0.35 |
| L3 | 3 moods + 2 chats | 5 | 0.47 |
| L4 | 4 moods + 3 chats + 5 history | 12 | 0.69 |
| L5 | 8 moods + 5 chats + 8 history + 3 wellness | 24 | 0.77 |

Confidence is **monotonically increasing** (verified) with a span of 0.62 across the data volume gradient.

### 16.5 Baseline Comparison (Mood-Only vs AURA v3)

| Scenario | Baseline | V3 | Δ | V3 Conf | Key Finding |
|:---|:---:|:---:|:---:|:---:|:---|
| Calm student | 15 | 29 | +14 | 0.53 | V3 incorporates time_bias |
| Genuinely stressed | 72 | 70 | −2 | 0.53 | Strong alignment (validates mood signal) |
| Spam-positive after stress | 78 | 58 | −20 | 0.45 | V3 resists manipulation |
| No data at all | 50 | 75 | +25 | 0.15 | V3 flags low confidence |
| Wildly swinging moods | 15 | 43 | +28 | 0.57 | V3 captures volatility baseline misses |
| Recovering (previously high) | 20 | 31 | +11 | 0.64 | V3 captures trend direction |

### 16.6 Summary Comparison

| Criterion | Mood-Only Baseline | AURA v3 |
|:---|:---|:---|
| Signals used | 1 (mood) | 6 (multi-signal) |
| Adaptive weighting | No | Yes |
| Temporal smoothing | None | EMA (α=0.6) |
| Nonlinear stabilization | None | Logistic (k=0.08, μ=50) |
| Manipulation resistance | None | Burst detection |
| Anomaly detection | None | Z-score (>2σ) |
| Confidence scoring | None | 3-factor (0–1) |
| Data sparsity handling | Default 50 | Adaptive redistribution |
| Score stability (EMA var red.) | — | 96% |
| Score stability (total var red.) | — | 92% |
| Crisis response (to High) | 1 reading | 4 readings |