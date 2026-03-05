# AURA Project - References & Resources

## Project Overview
**AURA** - AI-Powered Student Wellness Monitoring System
A comprehensive platform for tracking student mental health, stress levels, and academic performance with proactive intervention capabilities.

---

## Technology Stack

### Backend Framework
- **Flask** (Python Web Framework)
  - Documentation: https://flask.palletsprojects.com/
  - Official Repository: https://github.com/pallets/flask
  - Used for: RESTful API endpoints, routing, session management

- **Python 3.x**
  - Documentation: https://www.python.org/doc/
  - Package Manager: pip

### Database
- **MongoDB**
  - Documentation: https://docs.mongodb.com/
  - Official Site: https://www.mongodb.com/
  - Used for: Student records, wellness metrics, intervention tracking
  - Driver: PyMongo (https://pymongo.readthedocs.io/)

### Frontend Technologies
- **HTML5 / CSS3 / JavaScript (ES6+)**
  - MDN Web Docs: https://developer.mozilla.org/
  - Used for: Responsive dashboard UI, real-time interactions

- **ApexCharts** (Data Visualization)
  - Documentation: https://apexcharts.com/
  - GitHub: https://github.com/apexcharts/apexcharts.js
  - Used for: Stress trend charts, risk distribution graphs, wellness index visualizations

### UI/Design Libraries
- **Font Awesome Icons** (v6.4.0)
  - Website: https://fontawesome.com/
  - Documentation: https://fontawesome.com/docs
  - Used for: Dashboard icons and visual indicators

- **Google Fonts - Inter**
  - Font: https://fonts.google.com/specimen/Inter
  - Used for: Typography and professional typography

### AI/ML Services
- **Google Generative AI (Gemini)**
  - Documentation: https://ai.google.dev/
  - Python SDK: https://github.com/google/generative-ai-python
  - Used for: AI-powered student wellness insights and recommendations

- **OpenAI API**
  - Documentation: https://platform.openai.com/docs/
  - Used for: Fallback AI provider, natural language processing

### Authentication & Security
- **Flask-Login** / **Flask-Session**
  - Used for: User authentication and session management
  - Documentation: https://flask-login.readthedocs.io/

- **Werkzeug**
  - Used for: Password hashing and security utilities
  - Documentation: https://werkzeug.palletsprojects.com/

---

## Project Structure

```
d:\AURA\
├── app.py                      # Main Flask application entry point
├── config.py                   # Configuration settings
├── run.py                      # Application runner
├── models/                     # Database models
│   ├── user.py                # User model
│   ├── student.py             # Student model
│   ├── mood.py                # Mood tracking model
│   ├── stress.py              # Stress metrics model
│   ├── chat.py                # Chat history model
│   └── grievance.py           # Grievance tracking model
├── routes/                    # Flask routes/blueprints
│   ├── auth.py               # Authentication routes
│   ├── student.py            # Student dashboard routes
│   ├── proctor.py            # Proctor & HOD routes
│   └── chat.py               # Chat endpoints
├── services/                 # Business logic services
│   ├── ai_service.py         # AI integration service
│   └── stress_service.py     # Stress analysis service
├── utils/                    # Utility functions
│   ├── database.py           # Database connection & operations
│   ├── validators.py         # Input validation
│   ├── auth_helpers.py       # Authentication utilities
│   ├── alerts.py             # Alert generation
│   ├── rate_limit.py         # Rate limiting
│   └── helpers.py            # General helpers
├── templates/               # Jinja2 HTML templates
│   ├── base.html            # Base template
│   ├── login.html           # Login page
│   ├── proctor_dashboard.html   # Faculty monitoring dashboard
│   ├── hod_dashboard.html       # Executive analytics dashboard
│   ├── student_dashboard.html   # Student home
│   ├── study_chatbot.html       # Study assistant
│   └── [other templates]
├── static/                  # Static assets
│   ├── css/                 # Stylesheets
│   ├── js/                  # JavaScript files
│   └── images/              # Images and assets
└── instance/               # Instance folder (configs, databases)
```

---

## Key Features & Components

### 1. **Proctor Dashboard** (`proctor_dashboard.html`)
**Purpose:** Faculty-level student monitoring and intervention

**Features:**
- High-priority student alerts with stress scores
- Student watchlist with 7-day trend analysis
- Grievance management system
- Intervention notes and action tracking
- Real-time stress analytics charts
- Quick action buttons for counselor assignment

**Technologies:**
- ApexCharts for stress trend visualization
- Toast notifications for user feedback
- Responsive grid layout with sidebar controls

### 2. **HOD Dashboard** (`hod_dashboard.html`)
**Purpose:** Executive-level department analytics and oversight

**Features:**
- Department-wide KPI metrics (wellness index, enrollment, interventions, stress)
- Department health overview with donut charts
- Risk distribution analysis with horizontal bar charts
- Intervention effectiveness tracking
- Priority alerts sidebar
- Action items management

**Technologies:**
- Advanced ApexCharts visualizations (donut, bar charts)
- Executive-style dark header with role badges
- Strategic metrics and trend indicators

### 3. **Student Dashboard** (`student_dashboard.html`)
**Purpose:** Student self-monitoring and wellness tracking

**Features:**
- Personal mood logging
- Stress level tracking
- Mood trend charts
- Wellness recommendations
- Peer comparison (anonymized)
- Study resources and support links

### 4. **Study Chatbot** (`study_chatbot.html`)
**Purpose:** AI-powered academic support

**Features:**
- Conversational AI tutoring using Google Gemini / OpenAI
- Subject-specific help
- Study tips and exam preparation
- Integration with course materials

### 5. **Mental Health Chatbot** (`mental_chatbot.html`)
**Purpose:** AI-powered wellness support

**Features:**
- Mental health awareness conversations
- Stress management tips
- Emotional support
- Confidential wellness advice

---

## API Endpoints

### Authentication Routes (`/auth`)
- `POST /login` - User login
- `GET /logout` - User logout
- `POST /register` - User registration

### Student Routes (`/student`)
- `GET /student/dashboard` - Student home page
- `POST /student/mood` - Log mood entry
- `POST /student/stress` - Log stress level
- `GET /student/profile/<id>` - Student profile

### Proctor Routes (`/proctor`)
- `GET /proctor/dashboard` - Proctor monitoring console
- `GET /proctor/hod` - HOD executive dashboard
- `GET /api/proctor/students` - Get student list
- `POST /api/proctor/intervention` - Record intervention

### Chat Routes (`/chat`)
- `POST /chat/send` - Send message to chatbot
- `GET /chat/history` - Get chat history
- `GET /api/chat/context` - Get conversation context

---

## Database Models

### User Model
```python
{
  _id: ObjectId,
  username: String,
  email: String,
  password_hash: String,
  user_role: String (student|proctor|hod|counselor),
  department: String (AIML),
  created_at: DateTime,
  last_login: DateTime
}
```

### Student Model
```python
{
  _id: ObjectId,
  user_id: ObjectId,
  name: String,
  roll_number: String,
  year: Integer (1-4),
  department: String (AIML),
  gpa: Float,
  mood_history: Array,
  stress_scores: Array,
  intervention_history: Array,
  grievances: Array
}
```

### Stress Model
```python
{
  _id: ObjectId,
  student_id: ObjectId,
  score: Integer (0-100),
  timestamp: DateTime,
  factors: Array (academic, social, personal),
  notes: String
}
```

### Mood Model
```python
{
  _id: ObjectId,
  student_id: ObjectId,
  mood: String (happy, sad, anxious, stressed, neutral),
  energy_level: Integer (1-5),
  timestamp: DateTime,
  notes: String
}
```

### Grievance Model
```python
{
  _id: ObjectId,
  student_id: ObjectId,
  title: String,
  description: String,
  category: String,
  status: String (pending, in_progress, resolved),
  assigned_to: ObjectId,
  created_at: DateTime,
  resolved_at: DateTime
}
```

### Chat Model
```python
{
  _id: ObjectId,
  user_id: ObjectId,
  messages: Array[
    { role: String, content: String, timestamp: DateTime }
  ],
  session_id: String,
  conversation_type: String (academic, wellness)
}
```

---

## Configuration & Environment

### `config.py` Variables
```python
FLASK_ENV = "production"  # or "development"
DEBUG = False
SECRET_KEY = "your-secret-key"
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "aura_db"
GEMINI_API_KEY = "your-gemini-key"
OPENAI_API_KEY = "your-openai-key"
SESSION_TIMEOUT = 3600  # seconds
```

### Required Environment Variables
- `FLASK_APP` = app.py
- `FLASK_ENV` = production/development
- `MONGODB_CONNECTION_STRING`
- `GOOGLE_GENAI_API_KEY`
- `OPENAI_API_KEY`

---

## Dependencies

### Python Packages (requirements.txt)
```
Flask>=2.3.0
Flask-Login>=0.6.0
Flask-Session>=0.5.0
pymongo>=4.0.0
python-dotenv>=0.21.0
google-generativeai>=0.3.0
openai>=0.27.0
werkzeug>=2.3.0
requests>=2.28.0
```

### Frontend Dependencies (CDN)
```html
<!-- ApexCharts -->
<script src="https://cdn.jsdelivr.net/npm/apexcharts@3.35.0/dist/apexcharts.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/apexcharts@3.35.0/dist/apexcharts.css">

<!-- Font Awesome Icons -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
```

---

## Design & UI References

### Color Palette (AIML Themed)
```css
Primary: #6366f1 (Indigo)
Primary Dark: #4f46e5
Accent: #8b5cf6 (Purple)
Critical: #ef4444 (Red)
High Risk: #f97316 (Orange)
Medium Risk: #eab308 (Yellow)
Low Risk: #10b981 (Green)
```

### Typography
- **Font Family:** Inter (Google Fonts)
- **Sizes:** 
  - Headers: 1.5rem - 3rem
  - Body: 0.875rem - 1rem
  - Labels: 0.75rem - 0.875rem

### Responsive Breakpoints
- Desktop: 1400px+
- Tablet: 768px - 1399px
- Mobile: < 768px

### Design System
- Border Radius: 6px (sm), 10px (md), 16px (lg), 24px (xl)
- Box Shadows: Multiple levels (sm, md, lg, xl, 2xl)
- Spacing: 0.25rem increments (space-1 to space-12)

---

## Best Practices & Standards

### Security
1. **Password Security:** Use Werkzeug's `generate_password_hash()` and `check_password_hash()`
2. **Session Management:** Use Flask-Session with secure cookies
3. **Input Validation:** Validate all user inputs in `utils/validators.py`
4. **Rate Limiting:** Implement rate limits on sensitive endpoints
5. **HTTPS:** Always use HTTPS in production
6. **API Keys:** Store in environment variables, never in code

### Database
1. **Connection Pooling:** Use MongoDB connection pooling
2. **Indexing:** Create indexes on frequently queried fields (student_id, user_id)
3. **Data Validation:** Validate at both application and database levels
4. **Backups:** Regular automated backups of MongoDB

### Frontend
1. **Responsive Design:** Mobile-first approach
2. **Accessibility:** WCAG 2.1 Level AA compliance
3. **Performance:** Minimize CSS/JS, optimize images
4. **Progressive Enhancement:** Graceful degradation for older browsers

### API Design
1. **RESTful:** Follow REST conventions for endpoints
2. **Versioning:** Version API endpoints (`/api/v1/...`)
3. **Error Handling:** Consistent error response format
4. **Documentation:** Document all endpoints with request/response examples

---

## Academic & Research References

### Student Wellness & Mental Health
1. **American College Health Association (ACHA)**
   - Website: https://www.acha.org/
   - Mental health assessment tools and benchmarks

2. **Substance Abuse and Mental Health Services Administration (SAMHSA)**
   - Website: https://www.samhsa.gov/
   - Evidence-based practices for student wellness

3. **American Psychological Association (APA)**
   - Website: https://www.apa.org/
   - Stress management and student mental health research

4. **Journal of American College Health**
   - Published research on college student wellness
   - Stress assessment methodologies

### Educational Technology
1. **EDUCAUSE**
   - Website: https://www.educause.edu/
   - Higher ed technology best practices

2. **ACM Learning @ Scale**
   - Research on educational AI and learning analytics
   - Website: https://learningatscale.acm.org/

### Data Visualization
1. **Visualization Design Lab** (University of Washington)
   - Best practices for data visualization in dashboards
   - Website: https://www.interactive-matter.eu/

---

## External Services & APIs

### Google Generative AI (Gemini)
```python
# API Documentation: https://ai.google.dev/
# Python Library: google-generativeai

import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("prompt")
```

### OpenAI API
```python
# API Documentation: https://platform.openai.com/docs/
# Python Library: openai

import openai
openai.api_key = OPENAI_API_KEY
response = openai.ChatCompletion.create(...)
```

---

## Deployment References

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask app
python app.py

# Access at: http://127.0.0.1:5000
```

### Production Deployment
- **Web Server:** Gunicorn or uWSGI
- **Reverse Proxy:** Nginx or Apache
- **Database:** MongoDB Atlas or self-hosted
- **Hosting:** AWS, Azure, Heroku, or PythonAnywhere
- **SSL/TLS:** Let's Encrypt certificates

---

## Performance Optimization

### Frontend Optimization
1. **Lazy Loading:** Load charts only when visible
2. **Code Splitting:** Separate CSS for different pages
3. **Image Optimization:** Use compressed, appropriately-sized images
4. **Caching:** Implement browser caching headers

### Backend Optimization
1. **Database Indexing:** Index frequently queried fields
2. **Query Optimization:** Use projections to limit returned fields
3. **Caching Layer:** Redis for session/data caching
4. **API Rate Limiting:** Prevent abuse and improve stability

### Monitoring & Analytics
- **Error Tracking:** Sentry (https://sentry.io/)
- **Performance Monitoring:** New Relic or Datadog
- **User Analytics:** Google Analytics or Mixpanel
- **Logging:** Centralized logging with ELK stack

---

## Testing References

### Unit Testing
- **Framework:** pytest (https://pytest.org/)
- **Mocking:** unittest.mock or pytest-mock

### Integration Testing
- **Database Testing:** mongomock for MongoDB mocking
- **API Testing:** pytest with requests library

### E2E Testing
- **Browser Testing:** Selenium or Playwright

---

## Version Control & Documentation

### Git Repository
- Recommended: GitHub, GitLab, or Bitbucket
- Branch Strategy: Git Flow (main, develop, feature branches)
- Commit Messages: Follow Conventional Commits

### Documentation
- **Code Documentation:** Docstrings in Python (PEP 257)
- **API Documentation:** Swagger/OpenAPI with Flasgger
- **Project Wiki:** GitHub Wiki or Confluence
- **README:** Clear setup and usage instructions

---

## Useful Tools & Resources

### Development Tools
- **IDE:** Visual Studio Code, PyCharm
- **API Testing:** Postman, Insomnia
- **Database GUI:** MongoDB Compass
- **Version Control:** Git + GitHub Desktop

### Monitoring & Logging
- **Log Aggregation:** ELK Stack, Splunk
- **Error Tracking:** Sentry, Rollbar
- **Performance:** New Relic, Datadog

### Learning Resources
- **Flask Tutorial:** https://flask.palletsprojects.com/tutorial/
- **MongoDB University:** https://university.mongodb.com/
- **Web Design Trends:** https://dribbble.com/, https://awwwards.com/

---

## Contact & Support

### Community Resources
- **Stack Overflow:** Tag questions with [flask], [mongodb], [python]
- **GitHub Issues:** Report bugs and feature requests
- **Official Documentation:** Always check official docs first

### Project Maintainers
- Document contact information and contribution guidelines
- Set up CONTRIBUTING.md for developers

---

## License & Attribution

### Software Licenses
- **Flask:** BSD 3-Clause License
- **MongoDB:** SSPL / Community License
- **ApexCharts:** Freeware (with premium options)
- **Font Awesome:** CC BY 4.0 License (Free version)

### Attribution Requirements
Include proper attribution for all third-party libraries and services used.

---

**Last Updated:** January 28, 2026
**Project Status:** Active Development
**Version:** 3.5.0
