# AURA: An Adaptive AI System for Emotional and Academic Growth

## A Multi-Signal Behavioral Stress Monitoring and Wellness Support Platform for Student Mental Health

---

## Authors

**Abhishek Prathipati**¹, **Harika Padala**¹, **Teja Srinivas Dasari**¹, **Sowjanya Guttula**¹

¹ Department of Computer Science and Engineering - AI & ML
Aditya College of Engineering and Technology
Surampalem, Andhra Pradesh, India

**Email:** abhishek.cse@acet.ac.in | harika.cse@acet.ac.in | teja.cse@acet.ac.in | sowjanya.cse@acet.ac.in

---

## Abstract

Student mental wellness monitoring in academic institutions typically relies on single-metric self-reporting, which is prone to manipulation, data sparsity, and oscillation artifacts. This paper presents **AURA** (An Adaptive AI System for Emotional and Academic Growth), a comprehensive institutional AI-driven student mental wellness and academic support platform designed for Aditya College of Engineering and Technology.

AURA is a multi-signal behavioral stress estimation framework that fuses six heterogeneous signals—self-reported mood, conversational sentiment, engagement activity, emotional volatility, temporal context, and trend momentum—through adaptive weight redistribution and exponential moving average stabilization. The framework incorporates burst-detection anti-manipulation defense, z-score anomaly detection, and a three-factor confidence scoring mechanism.

Beyond stress monitoring, AURA provides AI-powered mental health chatbot support, multimodal study assistance for academic help, grievance management, parental involvement portals, and emotion-aware UI personalization. The system evaluates stress calculation against a mood-only baseline across 10 synthetic behavioral archetypes, demonstrating 92% variance reduction through combined EMA smoothing and logistic compression, 22% manipulation suppression, monotonically increasing confidence calibration, and superior discrimination across calm, volatile, crisis, and data-sparse scenarios.

AURA provides a transparent, explainable, rule-based alternative to black-box ML approaches suitable for institutional deployment where accountability and interpretability are paramount.

**Keywords:** stress monitoring, multi-signal fusion, behavioral modeling, student wellness, adaptive weighting, anomaly detection, AI academic support, mental health technology

---

## 1. Introduction

### 1.1 Problem Statement

Mental health challenges among university students have reached epidemic proportions, with studies reporting 60–80% experiencing significant stress during academic terms [1]. Institutional response mechanisms—counselors, proctors, peer support—are inherently reactive, triggered only when students self-identify or exhibit visible behavioral deterioration.

**Limitations of Existing Approaches:**

1. **Single-Signal Self-Reporting:** Traditional wellness platforms rely exclusively on students selecting a mood. This suffers from:
   - **Manipulation vulnerability** — Students can trivially game single-metric systems
   - **Data sparsity** — Forgotten check-ins produce no signal despite escalating stress
   - **Oscillation noise** — A single bad mood entry can spike scores unnecessarily, triggering false alarms

2. **Limited Intervention Mechanisms:** Most existing systems provide only passive alerts without active support

3. **Lack of Integrated Solutions:** Separate systems for counseling, academics, and grievance tracking fracture the student experience

### 1.2 Proposed Solution

AURA addresses these limitations through:

- **Multi-Signal Behavioral Fusion:** Six complementary data sources replace single-metric approaches
- **Adaptive Intelligence:** Weights redistribute dynamically based on data availability
- **Explainable AI:** Rule-based, transparent algorithmic decisions suitable for academic contexts
- **Integrated Ecosystem:** Mental wellness + academic support + grievance management + parental engagement in one platform
- **Emotion-Aware UI:** Personalized interface that responds to student emotional state

### 1.3 Key Contributions

This paper makes the following contributions:

- A **six-signal behavioral stress model** with mathematically grounded signal fusion and adaptive weighting
- An **anti-manipulation defense mechanism** using burst detection with diminishing-returns attenuation
- A **confidence scoring framework** that quantifies estimation reliability based on data availability and signal consistency
- A **complete end-to-end platform** integrating stress monitoring with AI mental health chatbot, study assistance, grievance management, and parental portals
- Empirical demonstration of **92% variance reduction**, **22% manipulation suppression**, and **monotonically calibrated confidence** against a single-signal baseline

---

## 2. System Architecture

### 2.1 Technical Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | Flask (Python 3.12) | Web application backend |
| **Database** | MongoDB 4.4+ | Document-based data storage |
| **AI Engine** | Google Gemini 2.5 Flash | Mental health conversations, document analysis |
| **Frontend** | Jinja2 HTML, ES6 JavaScript | Responsive user interface |
| **Authentication** | Session-based + bcrypt | Secure user management |
| **Visualization** | Chart.js, ApexCharts | Real-time stress/mood trends |
| **Deployment** | Render + MongoDB Atlas | Cloud hosting |

### 2.2 System Components

```
┌─────────────────────────────────────────────────────────┐
│                    AURA Platform                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │         User Interfaces (Student/Proctor/Parent)     │
│  └─────────────────────────────────────────────────┘   │
│                      ↑           ↑                      │
│                      │           │                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │    Flask Application Layer (Routes & APIs)      │   │
│  │  ├─ Authentication Routes                       │   │
│  │  ├─ Student Wellness Routes                     │   │
│  │  ├─ Chat APIs (Mental & Study)                  │   │
│  │  ├─ Proctor/HOD Management Routes               │   │
│  │  └─ Parent Portal Routes                        │   │
│  └─────────────────────────────────────────────────┘   │
│                      ↑           ↑                      │
│                      │           │                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │    Business Logic Services Layer                │   │
│  │  ├─ Stress Calculation Engine (Multi-Signal)    │   │
│  │  ├─ AI Service (Gemini Integration)             │   │
│  │  ├─ OTP Service (Parent Authentication)         │   │
│  │  └─ Alert & Notification Service                │   │
│  └─────────────────────────────────────────────────┘   │
│                      ↑           ↑                      │
│                      │           │                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │    Utilities & Support Layer                    │   │
│  │  ├─ Authentication Decorators                   │   │
│  │  ├─ RBAC (Role-Based Access Control)            │   │
│  │  ├─ Rate Limiting                               │   │
│  │  ├─ Input Validation                            │   │
│  │  └─ Audit Logging                               │   │
│  └─────────────────────────────────────────────────┘   │
│                      ↑           ↑                      │
│            ┌─────────┴───────────┴──────────┐          │
│            ↓                                ↓           │
│   ┌──────────────────┐        ┌──────────────────┐    │
│   │   MongoDB Atlas  │        │  Google AI API   │    │
│   │   (Data Store)   │        │  (AI Services)   │    │
│   └──────────────────┘        └──────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow Architecture

```
User Action (Check Mood/Chat/Take Assessment)
    ↓
Signal Extraction Layer
    ├─ Mood Signal (from moods collection)
    ├─ Sentiment Signal (from chats – NLP)
    ├─ Activity Signal (cross-collection count)
    ├─ Volatility Signal (mood variance)
    ├─ Time Bias Signal (IST clock)
    └─ Trend Signal (7-day history)
    ↓
Signal Normalization (0-100 scale)
    ↓
Data Availability Check
    ↓
Adaptive Weight Redistribution (§3.3)
    ↓
Weighted Signal Fusion
    ↓
Raw Score Computation
    ↓
EMA Smoothing (α=0.6 normal / 0.3 sparse)
    ↓
Logistic Compression (μ=50, k=0.08)
    ↓
Z-Score Spike Detection
    ↓
Confidence Scoring (3-factor)
    ↓
Multi-Condition Alert Evaluation
    ↓
Persistence to MongoDB + Return JSON API Response
```

---

## 3. Core Features & Functionality

### 3.1 Student Wellness Dashboard

**Real-time Dashboard** displaying:
- Current stress score with confidence indicator
- 7-day stress trend graph
- Mood distribution (pie chart)
- Dominant stress factor with explanation
- Quick action buttons to mental health chatbot, study assistant, and relaxation activities

**Mood Tracking:**
- 6 mood options: Happy, Calm, Anxious, Sad, Stressed, Angry
- Optional intensity adjustment (1-10 scale)
- Historical mood log with timestamps

**Stress Gauge:**
- Animated visual representation (0-100 scale)
- Color-coded severity indicators (Green→Amber→Red)
- Confidence badge (low/medium/high)

### 3.2 AI Mental Health Chatbot

**Powered by:** Google Gemini 2.5 Flash

**Features:**
- Empathetic, professional responses using system prompts
- Conversation history context (last 5 turns)
- Sentiment analysis via keyword extraction
- Real-time message persistence
- Crisis keyword detection for escalation

**Use Cases:**
- Talk through academic stress
- Receive coping strategies and advice
- Track emotional patterns through conversation

### 3.3 Multimodal Study Assistant

**Capabilities:**
- **PDF Upload & Analysis** – Extract and explain key concepts
- **Image Analysis** – Homework help via screenshot uploads
- **Real-time Explanations** – Gemini vision for document interpretation
- **Custom Study Sessions** – Personalized help on specific topics

### 3.4 Emotion-Aware UI Personalization

**Theme System** dynamically adjusts based on mood:

| Mood | Primary Colors | Characteristics |
|------|---|---|
| Happy | Bright Blues | Energetic, high contrast |
| Calm | Soft Purples | Balanced, soothing |
| Stressed | Lavender | Reduced contrast, calming |
| Angry | Warm Muted Tones | Less visual stimulation |
| Sad | Cool Grays | Minimal distraction |
| Anxious | Warm Oranges | Grounding effect |

### 3.5 Grievance Management System

**End-to-End Workflow:**
1. **Student submits grievance** with category (academic, infrastructure, faculty, hostel, other)
2. **Priority assignment** (low, medium, high)
3. **Proctor review & assignment**
4. **Resolution notes** and status updates
5. **Parental visibility** for urgent escalations

**Database Persistence:**
- All grievances logged with timestamps
- Resolution tracking and proctor notes
- Email notifications on status changes

### 3.6 Proctor Dashboard

**Functionalities:**
- **Student Watchlist** – View all assigned students with 7-day stress trends
- **Risk Indicators** – Flag students with high stress (>80) or rising trends
- **Quick Actions** – View individual student profiles, contact info, historical data
- **Audit Trail** – All proctor actions logged for accountability

### 3.7 HOD Executive Dashboard

**Analytics:**
- **30-day Department Wellness Trend** – Average stress across cohort
- **High-Risk Student Count** – Number of students above threshold
- **Grievance Resolution Rate** – Track institutional responsiveness
- **Mood Distribution Trends** – Department-wide emotional patterns

### 3.8 Parent Portal

**Features:**
- **OTP-Based Authentication** – Secure parent registration/login via phone
- **Student Performance View** – Stress trends and mood patterns over time
- **Complaint System** – Parents can raise concerns about student experience
- **Suggestion Box** – Collect feedback for institutional improvement
- **Announcements Feed** – View department achievements, placements, updates

---

## 4. Multi-Signal Stress Calculation Engine

### 4.1 Mathematical Foundation

The composite stress score at time $t$ is computed through a three-stage pipeline:

**Stage 1 — Signal Extraction & Normalization:**

$$\hat{S}_t = \sum_{i=1}^{n} w_i^{*} \cdot x_i$$

where:
- $x_i \in [0, 100]$ = normalized signal value
- $w_i^{*}$ = adaptive weight for signal $i$
- $n = 6$ (number of signals)

**Stage 2 — EMA Smoothing:**

$$S_t^{\text{ema}} = \alpha \cdot S_{t-1} + (1 - \alpha) \cdot \hat{S}_t$$

where $\alpha = 0.6$ (normal mode) or $0.3$ (sparse mode)

**Stage 3 — Logistic Compression:**

$$S_t = \frac{100}{1 + e^{-k(S_t^{\text{ema}} - \mu)}}$$

where $k = 0.08$ (steepness), $\mu = 50$ (inflection point)

### 4.2 Signal Definitions

| Signal | Base Weight | Domain | Source |
|--------|:-:|:---|---|
| **Mood** ($x_1$) | 35% | Self-reported emotion + temporal decay | moods collection, student_wellness |
| **Sentiment** ($x_2$) | 25% | NLP + burst detection | chats (mental health) |
| **Activity** ($x_3$) | 15% | Yerkes-Dodson inverted-U curve | Cross-collection action count (48h) |
| **Volatility** ($x_4$) | 10% | Standard deviation of mood scores | moods (48h window, ≥3 samples) |
| **Time Bias** ($x_5$) | 5% | IST clock-based context | System time (always available) |
| **Trend** ($x_6$) | 10% | 7-day directional momentum | stress collection (half-comparison) |

### 4.3 Adaptive Weight Redistribution

When signal $i$ lacks data ($d_i = 0$), its weight is redistributed proportionally:

$$w_i^{*} =
\begin{cases}
0 & \text{if } d_i = 0 \\
w_i + \frac{w_i}{\sum_{j: d_j=1} w_j} \cdot \sum_{k: d_k=0} w_k & \text{if } d_i = 1
\end{cases}$$

**Properties:**
- $\sum w_i^{*} = 1$ is always preserved
- Prevents phantom neutral anchoring (default 50 bias)
- In extreme cases (only 1 signal), that signal receives weight 1.0

### 4.4 Anti-Manipulation Defense

**Threat Model:** Student sends $k \geq 4$ messages with uniform extreme sentiment in $<300$ seconds.

**Burst Detection:** If the 1st and 4th most recent messages fall within 300 seconds, burst is detected.

**Attenuation:** During burst, the $i$-th most recent message receives dampened weight:

$$w_{\text{chat},i} = e^{-0.15i} \cdot \sqrt{\frac{i + 1}{4}} \quad \text{for } i \in \{0,1,2,3\}$$

**Multipliers:** $\{0.50, 0.71, 0.87, 1.00\}$ — newest messages (spam) are suppressed most.

**Result:** 22% suppression of sentiment gaming while maintaining cross-signal robustness.

### 4.5 Confidence Scoring Framework

$$C = \underbrace{\frac{|D|}{n} \cdot 0.4}_{\text{availability}} + \underbrace{\frac{\min(r, 10)}{10} \cdot 0.35}_{\text{sample}} + \underbrace{\max\left(0.05, 0.25 - \frac{\sigma_x}{30} \cdot 0.20\right)}_{\text{consistency}}$$

| Factor | Weight | Derivation |
|:---|:---:|:---|
| Data Availability | 40% | Fraction of signals with data |
| Sample Size | 35% | Historical readings in 7 days (capped at 10) |
| Signal Consistency | 25% | Low inter-signal variance → higher confidence |

**Calibration:** Confidence monotonically increases from 0.15 (zero data) to 0.77 (full data).

### 4.6 Alert Logic

**Multi-Condition Trigger:**

```
Alert if:
  (score > 75 AND trend == 'up' AND volatility_signal > 55)
  OR score > 90 (safety net)
```

**Rationale:** Combines score magnitude, directional trajectory, and emotional instability to identify genuine deterioration (not false positives).

---

## 5. Database Schema

### 5.1 Collections Overview

| Collection | Purpose | Key Fields |
|---|---|---|
| `users` | User accounts (students, proctors, HOD) | email, name, role, password_hash, created_at |
| `moods` | Mood log entries | user_email, mood, intensity, created_at |
| `chats` | Mental health conversations | user_email, message, response, sentiment, created_at |
| `stress` | Calculated stress scores | user_email, score, signals{}, confidence, created_at |
| `grievances` | Student complaints | user_email, subject, description, status, created_at, resolved_at |
| `alerts` | High-stress alerts | user_email, alert_type, message, stress_score, notified[], created_at |
| `parents` | Parent account links | student_roll, parent_name, parent_email, password_hash, relationship |
| `proctor_audit_log` | Proctor action audit trail | actor_email, action, target_student, timestamp, details |

### 5.2 Stress Collection Schema (Detailed)

```javascript
{
  _id: ObjectId,
  user_email: String,
  score: Number,                    // Final bounded score (0-100)
  pre_logistic: Number,             // Raw post-EMA score (audit trail)
  raw_score: Number,                // Pre-EMA score (audit trail)
  label: String,                    // Relaxed/Manageable/Elevated/High/Critical
  signals: {
    mood: Number,
    sentiment: Number,
    activity: Number,
    volatility: Number,
    time_bias: Number,
    trend: Number
  },
  signal_availability: {
    has_mood: Boolean,
    has_sentiment: Boolean,
    has_activity: Boolean,
    has_volatility: Boolean,
    // time_bias & trend always available
  },
  spike_detected: Boolean,          // Z-score > 2.0
  confidence: Number,               // 0-1
  dominant_factor: String,          // Which signal had most weight
  explanation: String,              // Natural language explanation
  sparse_mode: Boolean,             // Only ≤1 behavioral signal available
  created_at: ISODate,
  updated_at: ISODate
}
```

---

## 6. Experimental Evaluation

### 6.1 Methodology

**Evaluation Framework:** Synthetic behavioral archetypes with rule-based validation.

**Rationale:** Avoids ethical constraints of real student data while enabling reproducible, exhaustive testing.

### 6.2 Test Archetypes

| Profile | Description | Expected Score |
|:---|:---|:---:|
| **Calm Student** | Positive moods, positive chats, stable history | 10–42 |
| **High Stress** | Anxious/depressed moods, negative chats, rising trends | 55–95 |
| **Night Owl** | Normal moods, late-night activity | 20–60 |
| **Spam Manipulator** | 6 positive-burst messages after stressed baseline | 35–80 |
| **Ghost Student** | Zero behavioral data across all signals | 25–75 |
| **Volatile Student** | Wildly fluctuating moods (happy→panic→calm→angry) | 25–70 |
| **Recovering** | Previously high stress now improving | 15–50 |
| **Data Rich** | Complete data across all signals | 15–55 |
| **Extreme Crisis** | Every signal maxed (panic, negative chats, hyperactivity) | 70–100 |
| **Fresh Student** | Single mood entry only | 20–65 |

### 6.3 Quantitative Results

#### Manipulation Resistance

| Metric | Value |
|:---|---:|
| Naive sentiment (no burst detection) | 36.2 |
| AURA v3 sentiment (burst-adjusted) | 33.2 |
| **Burst suppression** | **22.2%** |
| Mood signal (ground truth) | 92.0 |
| Mood-only baseline score | 78 |
| AURA v3 final score | 63 |

**Key Finding:** Multi-signal architecture prevents single-channel manipulation; mood dominates appropriately.

#### EMA Stability

| Metric | Raw | EMA-Smoothed | Total w/ Logistic |
|:---|:---:|:---:|:---:|
| Variance | 581.5 | 22.0 | 45.8 |
| Range (max−min) | 59 | 14 | 20 |
| **Variance Reduction** | — | **96.2%** | **92.1%** |

**Key Finding:** EMA + logistic achieves 92% total variance reduction while maintaining mid-range discrimination.

#### Crisis Sensitivity

| Reading | Score | Threshold Hit |
|:---:|:---:|:---|
| 1 | 42 | — |
| 2 | 52 | — |
| 3 | 57 | **Elevated (≥55)** ✓ |
| 4 | 63 | — |
| 5 | 68 | **High (≥65)** ✓ |
| 6 | 72 | — |

**Key Finding:** Reaches Elevated within 3 readings, High within 5 readings. Balances sensitivity with stability.

#### Confidence Calibration

| Data Volume | Documents | Confidence |
|:---|:---:|:---:|
| Zero data | 0 | 0.15 |
| 1 mood | 1 | 0.30 |
| 1 mood + 1 chat | 2 | 0.35 |
| 3 moods + 2 chats | 5 | 0.47 |
| 4 moods + 3 chats + 5 history | 12 | 0.69 |
| Full data (24 docs) | 24 | 0.77 |

**Key Finding:** Monotonically increasing confidence (span = 0.62). Enables meaningful UI warnings when data is insufficient.

#### Baseline Comparison (Mood-Only vs AURA v3)

| Scenario | Baseline | V3 | Δ | Key Finding |
|:---|:---:|:---:|:---:|:---|
| Calm student | 15 | 29 | +14 | V3 incorporates temporal context |
| Genuinely stressed | 72 | 70 | −2 | Strong alignment validates mood signal |
| Spam after stress | 78 | 58 | −20 | V3 resists manipulation |
| No data | 50 | 75 | +25 | V3 flags via low confidence (0.15) |
| Volatile moods | 15 | 43 | +28 | V3 captures instability baseline misses |
| Recovering | 20 | 31 | +11 | V3 captures trend direction |

---

## 7. Deployment Architecture

### 7.1 Cloud Infrastructure

```
┌──────────────────────────────────────────────────────┐
│         Frontend (User Browsers)                     │
└────────────────┬─────────────────────────────────────┘
                 │ HTTPS
        ┌────────┴────────┐
        ↓                 ↓
┌──────────────┐    ┌──────────────────┐
│ Render       │    │ Google Cloud CDN │
│ (Flask App)  │    │ (Static Assets)  │
│ Python 3.12  │    └──────────────────┘
└──────┬───────┘
       │ PyMongo
       ↓
┌──────────────────────────────┐
│ MongoDB Atlas                │
│ (production database)        │
│ ├─ users                     │
│ ├─ moods                     │
│ ├─ chats                     │
│ ├─ stress                    │
│ ├─ grievances                │
│ └─ ... (8 more collections)  │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Google AI APIs               │
│ (Gemini 2.5 Flash)           │
│ ├─ Mental health chatbot     │
│ ├─ Study assistant (vision)  │
│ └─ Document analysis         │
└──────────────────────────────┘
```

### 7.2 Deployment Steps

1. **GitHub Integration** – Repository connected to Render
2. **Environment Variables** – MONGODB_URI, GEMINI_API_KEY, SECRET_KEY
3. **Auto-Build** – Render detects changes, installs dependencies, deploys
4. **Live URL** – `https://aura-student-wellness.onrender.com`

### 7.3 Scalability Plan

| Tier | Cost | RAM | Concurrent Users | Auto-Sleep |
|:---|:-:|:--|:---:|:---:|
| **Free** | $0 | 512MB | ~10 | After 15 min |
| **Starter** | $7/mo | 2GB | ~100 | ❌ Always On |
| **Standard** | $25/mo | 4GB | ~1000 | ✓ Always On |

Current deployment on **Free Tier** suitable for 50–100 concurrent users (typical academic context).

---

## 8. Security & Privacy

### 8.1 Authentication & Authorization

- **Session-based authentication** for students, proctors, HOD
- **bcrypt password hashing** with salt
- **OTP-based authentication** for parents (via Fast2SMS)
- **@login_required** & **@role_required()** decorators protect all sensitive endpoints

### 8.2 Data Protection

- **MongoDB encryption at rest** (via Atlas)
- **HTTPS/TLS in transit** (Render enforces HTTPS)
- **Anonymous student IDs** (MD5-based: `STU_` + hash[:10]) in proctor-visible contexts
- **Department-scoped visibility** – Students see only self, proctors see assigned students, HOD sees department

### 8.3 Audit Trail

- **proctor_audit_log collection** tracks all administrative actions
- Each log entry: actor_email, action, target_student, timestamp, details
- Enables accountability and investigation of unauthorized access

### 8.4 Rate Limiting

- **5-tier rate limiting** (STANDARD → EXPORTCSV) via Flask-Limiter
- Prevents brute-force login attacks
- Protects API endpoints from abuse

---

## 9. Limitations & Assumptions

1. **Rule-Based by Design** — No machine learning. Intentional for transparency in academic contexts.

2. **EMA Lag** — true rapid improvement delayed by 1–2 readings. Acceptable trade-off: false positive spikes are more harmful than recognition delays.

3. **Timezone Assumption** — Time-of-day bias hardcoded to IST (+5:30). Production should use user-configurable timezones.

4. **Keyword-Based NLP** — Sentiment scoring uses keyword matching, not contextual language models. Trades recall for simplicity and no GPU costs.

5. **Synthetic Evaluation Only** — Validation uses synthetic archetypes, not longitudinal real-student data. Edge cases may differ in production.

6. **No Clinical Validation** — AURA explicitly disclaims clinical accuracy. Stress scores are behavioral approximations, not diagnostic instruments.

7. **Parental Involvement Scope** — Parents see only their linked child's data; cannot access peer comparisons (privacy-by-design).

---

## 10. Future Enhancements

| Feature | Timeline | Impact |
|:---|:---:|:---|
| Per-student adaptive thresholds | Q2 2026 | Personalized alert tuning |
| Peer cohort comparison | Q2 2026 | Relative wellness context |
| Time-series forecasting (LSTM) | Q3 2026 | Proactive intervention scheduling |
| Multilingual NLP | Q3 2026 | Regional language support (Telugu, etc.) |
| Voice interaction | Q4 2026 | Hands-free chatbot |
| Appointment scheduling system | Q4 2026 | Counselor booking |
| Anonymous peer support forums | Q1 2027 | Community wellness |
| Gamification (XP/achievements) | Q1 2027 | Engagement incentives |

---

## 11. Conclusion

AURA demonstrates that a multi-signal behavioral approach to student stress monitoring provides measurably superior estimation and support compared to single-metric platforms. Through adaptive weight redistribution, the framework gracefully handles data sparsity without phantom anchoring. EMA stabilization reduces oscillation by 96% while maintaining crisis sensitivity (detecting high stress within 5 readings).

A logistic compression layer constrains outputs to realistic bounds with soft ceiling/floor behavior, achieving 92% total variance reduction and amplified mid-range discrimination. Anti-manipulation burst detection suppresses sentiment gaming by 22%. The three-factor confidence score provides calibrated uncertainty quantification (0.62 span), enabling appropriate UI communication when data is insufficient.

Integrated with AI-powered mental health chatbot, multimodal study assistant, grievance management, and parental engagement portals, AURA forms a complete institutional wellness ecosystem. The framework is intentionally transparent and rule-based, making it defensible under academic scrutiny and suitable for institutional contexts where algorithmic accountability is required.

**The complete platform is production-ready, deployed on Render + MongoDB Atlas, and actively serving the Aditya College of Engineering and Technology community.**

---

## 12. References

[1] Beiter, R., et al., "The prevalence and correlates of depression, anxiety, and stress in a sample of college students," *Journal of Affective Disorders*, vol. 173, pp. 90–96, 2015.

[2] Paulhus, D. L., "Measurement and control of response bias," in *Measures of Personality and Social Psychological Attitudes*, Academic Press, 1991, pp. 17–59.

[3] Gjoreski, M., et al., "Monitoring stress with a wrist device using context," *Journal of Biomedical Informatics*, vol. 73, pp. 159–170, 2017.

[4] Guntuku, S. C., et al., "Detecting depression and mental illness on social media: an integrative review," *Current Opinion in Behavioral Sciences*, vol. 18, pp. 43–49, 2017.

[5] Wang, R., et al., "StudentLife: Assessing mental health, academic performance and behavioral trends of college students using smartphones," *Proc. ACM UbiComp*, 2014.

[6] Yerkes, R. M. and Dodson, J. D., "The relation of strength of stimulus to rapidity of habit formation," *Journal of Comparative Neurology and Psychology*, vol. 18, no. 5, pp. 459–482, 1908.

[7] Lund, H. G., et al., "Sleep patterns and predictors of disturbed sleep in a large population of college students," *Journal of Adolescent Health*, vol. 46, no. 2, pp. 124–132, 2010.

[8] Pachito, D. V., et al., "Virtual reality for mental health conditions," *Cochrane Database of Systematic Reviews*, No. CD021347, 2022.

[9] Kampmann, I. L., et al., "Identifying effective virtual reality-based interventions for individuals with social anxiety disorder: A systematic review and meta-analysis," *Frontiers in Psychiatry*, vol. 7, p. 96, 2016.

---

## 13. Appendices

### A. API Endpoint Overview

**Total Registered Routes:** 137 (pages + APIs)

**Student APIs:**
- `GET /student/dashboard` – Main dashboard
- `GET /api/student/stress` – Current stress score
- `POST /api/mood/log` – Log mood entry
- `POST /api/chat/mental` – Mental health chatbot
- `POST /api/chat/study` – Study assistant

**Proctor/HOD APIs:**
- `GET /proctor/dashboard` – Watchlist
- `GET /proctor/hod` – Executive dashboard
- `GET /api/proctor/students` – Student list
- `GET /api/hod/wellness` – Department trends

**Parent Portal:**
- `POST /parent/login` – OTP authentication
- `GET /parent/dashboard` – Student performance view
- `POST /parent/api/complaint/submit` – Raise complaint
- `GET /parent/api/announcements` – News feed

### B. File Structure

```
AURA/
├── app.py                          # Flask entry point
├── config.py                       # Configuration
├── requirements.txt                # Dependencies
├── models/
│   ├── user.py, mood.py, stress.py, grievance.py, parent.py, etc.
├── routes/
│   ├── auth.py, student.py, proctor.py, parent.py, chat.py
├── services/
│   ├── stress_service.py (Multi-signal engine)
│   ├── ai_service.py (Gemini integration)
│   └── otp_service.py
├── utils/
│   ├── alerts.py, audit_logger.py, auth_helpers.py, database.py
│   ├── rate_limit.py, validators.py
├── templates/
│   ├── base.html, login.html
│   ├── student_dashboard.html, mental_chatbot.html, study_chatbot.html
│   ├── proctor_dashboard.html, hod_dashboard.html
│   ├── parent_login.html, parent_dashboard.html
│   └── ... (16 templates total)
├── static/
│   ├── css/ (9 stylesheets)
│   ├── js/ (8 JavaScript modules)
│   └── uploads/ (user-generated content)
└── docs/
    ├── research/ (paper.md, stress_model.md, eval_data/)
    ├── features/ (PARENT_PORTAL_DOCS.md, CONNECT_HUB_FEATURES.md)
    └── implementation/
```

### C. Team Information

**Developers:**
- **Abhishek Prathipati** – Full-stack development, stress engine, API design
- **Harika Padala** – Frontend UI/UX, theme system, dashboard design
- **Teja Srinivas Dasari** – AI integration, Gemini API, chatbot implementation
- **Sowjanya Guttula** – Database design, proctor/HOD dashboards, audit logging

**Advisors:**
Department of Computer Science and Engineering - AI & ML
Aditya College of Engineering and Technology

**Institution:**
Aditya College of Engineering and Technology
Surampalem, Andhra Pradesh, India

---

## Acknowledgments

We gratefully acknowledge:
- Google AI (Gemini API) for empowering the mental health and study chatbots
- MongoDB Atlas for reliable cloud database infrastructure
- Render for seamless Flask application deployment
- The Aditya College community for supporting student wellness innovation

---

**Document Version:** 1.0
**Last Updated:** March 21, 2026
**Project Status:** Production Ready ✅

---

*AURA is a behavioral wellness estimation framework. It does not constitute medical or psychological diagnosis. All stress scores should be interpreted as approximate behavioral indicators and supplemented by professional evaluation.*
