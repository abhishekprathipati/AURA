# AURA - AI-Powered University Wellness & Academic Support Platform

> For a one-page evaluator summary, see [HANDOUT.md](HANDOUT.md).

## 🎯 Project Overview

**AURA** (AI-based University Response & Analytics) is a comprehensive mental health and academic support system designed for Aditya College of Engineering and Technology. The platform leverages cutting-edge AI technology to provide personalized support to students while giving faculty real-time insights into student wellbeing.

### 🌟 Key Features

1. **Mood-Based Adaptive UI** - Dynamic theme system that responds to student emotions
2. **AI Mental Health Chatbot** - Powered by Google Gemini for empathetic conversations
3. **Multimodal Study Assistant** - Analyzes PDFs and images to help with academics
4. **Stress Analytics & Alerts** - Automated stress calculation with institutional notifications
5. **Proctor Dashboard** - Student watchlist with 7-day stress trends
6. **HOD Dashboard** - Department-wide wellness analytics
7. **Grievance System** - Student issue reporting and resolution workflow
8. **Angry Mood Activities** - Interactive Scream Meter and Box Breathing exercises

---

## 🏗️ Technical Architecture

### Backend Stack
- **Framework**: Flask (Python 3.12)
- **Database**: MongoDB (PyMongo)
- **AI Engine**: Google Gemini 2.5 Flash
  - Text generation for mental health conversations
  - Vision capabilities for document and image analysis
- **Authentication**: Session-based with bcrypt password hashing
- **Email**: Flask-Mail for alert notifications
- **Environment**: python-dotenv for configuration

### Frontend Stack
- **Templates**: Jinja2 HTML templates with base inheritance
- **Styling**: Custom CSS with CSS variables for themes
- **JavaScript**: Modular ES6 scripts
- **Charts**: Chart.js for data visualization
- **APIs**: Web Audio API for Scream Meter

### AI Integration Details

#### 1. Mental Health Chatbot
- **Model**: `gemini-2.5-flash`
- **Context Management**: Last 5 conversation turns for continuity
- **Safety**: Custom system prompts for empathetic, professional responses
- **Sentiment Analysis**: Keyword-based extraction (positive/negative/neutral)
- **Persistence**: All chats stored in MongoDB with timestamps

#### 2. Study Assistant (Multimodal)
- **Supported Formats**: Images (JPEG, PNG) and PDFs
- **Vision Processing**: Gemini's vision capabilities for image analysis
- **PDF Handling**: File upload to Gemini with mime type inference
- **Use Cases**: Homework help, concept explanations, study material summaries

### Database Schema

#### Collections

1. **users**
   ```json
   {
     "email": "student@example.com",
     "name": "Student Name",
     "password": "bcrypt_hash",
     "role": "student|proctor|hod",
     "created_at": "ISODate"
   }
   ```

2. **chats**
   ```json
   {
     "user_email": "student@example.com",
     "message": "User message",
     "response": "AI response",
     "sentiment": "positive|negative|neutral",
     "created_at": "ISODate"
   }
   ```

3. **moods**
   ```json
   {
     "user_email": "student@example.com",
     "mood": "happy|stressed|angry|sad|anxious|calm",
     "created_at": "ISODate"
   }
   ```

4. **stress**
   ```json
   {
     "user_email": "student@example.com",
     "score": 0-100,
     "mood_score": 0-100,
     "chat_score": 0-100,
     "created_at": "ISODate"
   }
   ```

5. **grievances**
   ```json
   {
     "user_email": "student@example.com",
     "subject": "Issue title",
     "description": "Detailed description",
     "status": "pending|in_progress|resolved",
     "created_at": "ISODate",
     "resolved_at": "ISODate",
     "resolved_by": "proctor@example.com",
     "proctor_note": "Resolution notes"
   }
   ```

6. **alerts**
   ```json
   {
     "user_email": "student@example.com",
     "alert_type": "high_stress",
     "message": "Alert details",
     "stress_score": 85,
     "created_at": "ISODate",
     "notified": ["proctor@example.com", "parent@example.com"]
   }
   ```

---

## 🧠 Stress Calculation Algorithm

AURA uses a multi-factor algorithm to calculate daily stress scores:

```python
stress_score = (mood_baseline * 0.4) + (chat_sentiment_avg * 0.6)
```

### Mood Baselines
- **happy/calm**: 20 (low stress)
- **anxious**: 50 (moderate)
- **sad**: 60 (elevated)
- **stressed**: 70 (high)
- **angry**: 80 (very high)

### Chat Sentiment Impact
- Analyzes last 5 conversations
- **Positive sentiment**: 20 points
- **Neutral sentiment**: 50 points
- **Negative sentiment**: 80 points

### Alert Triggering
- **Threshold**: Stress score > 80
- **Actions**:
  1. Log to alerts collection
  2. Email notification to proctor
  3. Optional parent notification
  4. Dashboard flag for immediate attention

---

## 📊 MongoDB Aggregation Pipelines

### 1. Proctor Student Watchlist
```javascript
// 7-day stress trend per student
db.stress.find({
  user_email: email,
  created_at: { $gte: last_7_days }
}).sort({ created_at: 1 })
```

### 2. HOD Department Wellness
```javascript
db.stress.aggregate([
  { $match: { created_at: { $gte: last_30_days } } },
  {
    $group: {
      _id: { $dateToString: { format: '%Y-%m-%d', date: '$created_at' } },
      avg_score: { $avg: '$score' }
    }
  },
  { $sort: { _id: 1 } }
])
```

---

## 🎨 Mood-Based Theme System

AURA dynamically changes the UI based on student mood using CSS variables:

### Theme Variables
```css
:root {
  --bg: background-color
  --panel: card-background
  --text: text-color
  --muted: secondary-text
  --accent: primary-accent
  --accent-2: secondary-accent
  --btn-text: button-text
  --shadow: box-shadow
}
```

### Available Themes
1. **Normal/Happy** - Bright blues, positive energy
2. **Stressed** - Calming lavender, reduced contrast
3. **Angry** - Muted warm tones, less stimulation
4. **Sad** - Cool grays, minimal distraction
5. **Anxious** - Warm oranges, grounding effect
6. **Calm** - Soft purples, balanced design

---

## 🎮 Phase 5: Angry Mood Activities

### Scream Meter
- **Technology**: Web Audio API
- **Features**:
  - Real-time microphone input analysis
  - Vertical progress bar visualization
  - Volume-based stress release tracking
  - Celebration animation at 90% threshold
  - Confetti effects
- **Flow**: Scream → Release → Celebrate → Transition to breathing

### Box Breathing Exercise
- **Pattern**: 4-4-4-4 (Inhale-Hold-Exhale-Hold)
- **Visualization**: Animated circle with scale transitions
- **Cycles**: 5 complete cycles (80 seconds total)
- **Benefits**: Activates parasympathetic nervous system, reduces cortisol

---

## 🔐 Security Features

### Authentication & Authorization
1. **@login_required** - Protects all student routes
2. **@role_required('proctor')** - Proctor-only endpoints
3. **@role_required('hod')** - HOD-only endpoints
4. **Session Management** - Server-side session storage
5. **Password Security** - bcrypt hashing with salt

### Protected Routes
- `/proctor/dashboard` - Proctor access only
- `/proctor/hod` - HOD access only
- `/api/proctor/students` - Proctor access only
- `/api/hod/wellness` - HOD access only
- All `/student/*` routes require login

---

## 📱 Mobile Responsiveness

AURA is fully responsive with breakpoints:

### Mobile (<768px)
- Single column layouts
- Full-width buttons
- Compact cards
- Optimized chart sizes
- Stacked navigation

### Tablet (768px-1024px)
- Two-column grids
- Balanced spacing
- Responsive tables

### Desktop (>1024px)
- Multi-column layouts
- Full-featured charts
- Side-by-side comparisons

---

## 🚀 Deployment Guide

### Prerequisites
1. Python 3.12+
2. MongoDB 4.4+
3. Google Gemini API Key

### Environment Variables (.env)
```bash
# Database
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=aura_db

# Security
SECRET_KEY=your-secret-key-here

# AI
GEMINI_API_KEY=your-gemini-api-key

# Email (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Installation Steps

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd AURA
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Start MongoDB**
   ```bash
   # Ensure MongoDB is running on localhost:27017
   mongod
   ```

6. **Create Test User** (Optional)
   ```bash
   python create_test_user.py
   ```

7. **Run Application**
   ```bash
   python app.py
   ```

8. **Access Application**
   - Navigate to http://localhost:5000
   - Login with test credentials

---

## 🧪 Testing Checklist

### 1. Security Testing
- [ ] Try accessing `/proctor/dashboard` as a student → Should redirect
- [ ] Try accessing `/proctor/hod` without HOD role → Should redirect
- [ ] Verify @role_required decorators on all protected routes

### 2. Alert Testing
- [ ] Set mood to "Stressed"
- [ ] Chat with bot using negative words: "depressed", "hopeless", "terrible"
- [ ] Check MongoDB alerts collection for new entries
- [ ] Verify stress score > 80 triggers alert

### 3. AI Testing
- [ ] Mental chatbot responds with empathy
- [ ] Study bot accepts PDF uploads
- [ ] Image analysis works with screenshots
- [ ] Conversation history persists across sessions

### 4. Mobile Testing
- [ ] Open on mobile device or Chrome DevTools
- [ ] Verify stress gauge displays correctly
- [ ] Check chatbot is usable on small screens
- [ ] Ensure buttons are touch-friendly

### 5. Dashboard Testing
- [ ] Proctor dashboard shows all students
- [ ] 7-day sparklines render correctly
- [ ] HOD dashboard shows 30-day trend
- [ ] Charts load without errors

---

## 📈 Key Metrics & Analytics

### Student-Level Metrics
- Daily stress score (0-100)
- Mood selection frequency
- Chat conversation count
- Sentiment trend over time
- Grievance submission rate

### Department-Level Metrics
- Average daily stress across all students
- 30-day wellness trend
- High-risk student count (stress > 80)
- Grievance resolution rate
- Chatbot engagement metrics

---

## 🎓 Academic Context

**Institution**: Aditya College of Engineering and Technology  
**Purpose**: Mental health monitoring and academic support  
**Target Users**: 
- Students (primary)
- Proctors (mentors/advisors)
- HOD (Head of Department)

### Use Cases
1. **Student struggling with exam stress** → AI chatbot + breathing exercises
2. **Proctor noticing pattern** → Watchlist alerts + direct intervention
3. **HOD reviewing department health** → Trend analysis + policy decisions
4. **Academic confusion** → Multimodal study bot for instant help

---

## 🔮 Future Enhancements

1. **Peer Support Groups** - Connect students with similar challenges
2. **Appointment Scheduling** - Book sessions with campus counselor
3. **Resource Library** - Self-help articles and videos
4. **Anonymous Forums** - Safe space for discussions
5. **ML-Powered Predictions** - Early intervention for at-risk students
6. **Voice Chat** - Hands-free interaction with AI
7. **Gamification** - Rewards for consistent self-care
8. **Parent Portal** - Limited access for parental involvement

---

## 📝 File Structure
```
AURA/
├── app.py                      # Flask application entry point
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in repo)
├── models/                     # Database models
│   ├── __init__.py
│   ├── user.py
│   ├── chat.py
│   ├── mood.py
│   ├── stress.py
│   └── grievance.py
├── routes/                     # API endpoints
│   ├── __init__.py
│   ├── auth.py                # Login/logout
│   ├── student.py             # Student routes
│   ├── chat.py                # Chatbot APIs
│   └── proctor.py             # Proctor/HOD routes
├── services/                   # Business logic
│   ├── __init__.py
│   ├── ai_service.py          # Gemini integration
│   └── stress_service.py      # Stress calculation
├── utils/                      # Helper functions
│   ├── __init__.py
│   ├── database.py            # MongoDB connection
│   ├── auth_helpers.py        # Authentication decorators
│   ├── alerts.py              # Email notifications
│   └── helpers.py
├── templates/                  # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── student_dashboard.html
│   ├── mental_chatbot.html
│   ├── study_chatbot.html
│   ├── activities.html        # Scream Meter + Breathing
│   ├── proctor_dashboard.html
│   └── hod_dashboard.html
└── static/                     # Static assets
    ├── css/
    │   └── style.css          # Themed styling
    ├── js/
    │   ├── main.js
    │   ├── chatbot.js
    │   ├── study_chatbot.js
    │   ├── mood_handler.js
    │   ├── stress_gauge.js
    │   └── dashboard.js
    └── images/
```

---

## 👥 Team & Credits

**Developed by**: [Your Name/Team Name]  
**Institution**: Aditya College of Engineering and Technology  
**AI Powered by**: Google Gemini  
**Framework**: Flask  
**Database**: MongoDB

---

## 📄 License

This project is developed for educational purposes at Aditya College of Engineering and Technology.

---

## 🤝 Contributing

This is an academic project. For questions or collaboration:
- Email: [your-email]
- GitHub: [your-github]

---

## 🐛 Known Issues & Limitations

1. **Gemini API Deprecation Warning**: Current SDK will be deprecated. Migration to `google.genai` recommended.
2. **Email Configuration**: Requires Gmail app password for notifications.
3. **Sentiment Analysis**: Basic keyword matching; could be improved with ML.
4. **Proctor Assignment**: Currently shows all students; needs filtering by assigned students.

---

## 📚 References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [MongoDB PyMongo](https://pymongo.readthedocs.io/)
- [Google Gemini API](https://ai.google.dev/docs)
- [Chart.js](https://www.chartjs.org/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

---

**Last Updated**: December 18, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
