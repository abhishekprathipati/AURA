# AURA — Project Structure Guide

> **Last updated:** March 1, 2026 — Cleanup applied, all duplicates removed, routing verified.

---

## Project Architecture

```
AURA/
├── app.py                          # Flask app — limiter, SocketIO, routes, security
├── config.py                       # SECRET_KEY, MongoDB, mail, session cookies
├── run.py                          # Entrypoint — SocketIO server on port 5000
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── PROJECT_STRUCTURE_GUIDE.md      # ← This file
│
├── models/                         # MongoDB schema helpers
│   ├── __init__.py                 #   Exports all model classes
│   ├── user.py                     #   User accounts
│   ├── chat.py                     #   Chat messages
│   ├── mood.py                     #   Student wellness entries
│   ├── stress.py                   #   Stress scores
│   ├── grievance.py                #   Grievance tickets
│   ├── parent.py                   #   Parent OTP accounts
│   └── connect_hub.py              #   Social hub (9 models)
│
├── routes/                         # Flask blueprints
│   ├── __init__.py                 #   init_routes() — registers all blueprints
│   ├── auth.py                     #   /login, /logout
│   ├── student.py                  #   /student/* — dashboard, wellness APIs, pages
│   ├── proctor.py                  #   /proctor/* — dashboard, HOD, risk, audit, APIs
│   ├── parent.py                   #   /parent/* — OTP auth, dashboard, APIs
│   ├── chat.py                     #   /api/chat/* — mental & study chat APIs
│   └── connect_hub.py              #   /student/hub/* — social wellness SPA
│
├── services/                       # Business logic
│   ├── __init__.py
│   ├── ai_service.py               #   Gemini AI + OpenAI fallback
│   ├── otp_service.py              #   Fast2SMS OTP
│   └── stress_service.py           #   EMA stress calculation engine v3
│
├── utils/                          # Shared utilities
│   ├── __init__.py
│   ├── access_control.py           #   RBAC — anonymous IDs, visibility, dept scoping
│   ├── alerts.py                   #   Alert/notification helpers
│   ├── audit_logger.py             #   Proctor action audit logging + CSV export
│   ├── auth_helpers.py             #   @login_required, @demo_restricted, hashing
│   ├── database.py                 #   MongoDB init, get_db(), demo seeding
│   ├── helpers.py                  #   safe_error() + misc
│   ├── rate_limit.py               #   5-tier rate limiting + brute-force protection
│   └── validators.py               #   Input validation
│
├── templates/                      # Jinja2 templates (16 files)
│   ├── base.html                   #   Base layout — nav, theme, service worker
│   ├── login.html                  #   Login page (student/proctor/hod)
│   ├── index.html                  #   Standalone chat UI (/ui/chat)
│   ├── student_dashboard.html      #   Student dashboard
│   ├── mental_chatbot.html         #   Mental wellness chatbot
│   ├── study_chatbot.html          #   Study assistant chatbot
│   ├── relax.html                  #   Relaxation activities
│   ├── activities.html             #   Break room, breathing exercises
│   ├── games.html                  #   8 mind games with XP
│   ├── connect_hub.html            #   Social wellness hub SPA
│   ├── unregister_sw.html          #   Service worker unregistration
│   ├── proctor_dashboard.html      #   Proctor dashboard
│   ├── hod_dashboard.html          #   HOD executive dashboard
│   ├── student_detail.html         #   Student profile (proctor view)
│   ├── parent_login.html           #   Parent OTP login/register
│   └── parent_dashboard.html       #   Parent dashboard
│
├── static/
│   ├── css/                        # Stylesheets (9 files)
│   │   ├── global.css              #   Base styles, typography
│   │   ├── style.css               #   Component styles (cards, activities)
│   │   ├── login.css               #   Login page
│   │   ├── student_dashboard.css   #   Student dashboard
│   │   ├── mental-chatbot.css      #   Mental chatbot
│   │   ├── study-assistant.css     #   Study chatbot
│   │   ├── connect_hub.css         #   Connect Hub SPA
│   │   ├── chat.css                #   Standalone chat UI
│   │   └── sidebar.css             #   Standalone chat sidebar
│   │
│   ├── js/                         # JavaScript (8 files)
│   │   ├── main.js                 #   ES module — layout, header auto-hide
│   │   ├── theme-engine.js         #   Theme switching
│   │   ├── chat-engine.js          #   Mental chatbot engine
│   │   ├── study_chatbot.js        #   Study chatbot engine
│   │   ├── student_dashboard.js    #   Student dashboard logic
│   │   ├── mood_handler.js         #   Mood tracking UI
│   │   ├── connect_hub.js          #   Connect Hub SPA logic
│   │   └── parent_dashboard.js     #   Parent dashboard logic
│   │
│   ├── uploads/                    # User-uploaded files
│   ├── images/                     # Static images
│   ├── assets/avatars/             # User avatars
│   └── service-worker.js           # PWA offline caching
│
├── scripts/
│   ├── start.bat                   # Windows startup script
│   └── tools/                      # Dev/test utilities
│       ├── __init__.py
│       ├── seed_test_data.py       #   Seed DB with test data + 43 validations
│       ├── validate_api.py         #   HTTP API validation (48 checks)
│       ├── test_rbac.py            #   RBAC integration test (41 assertions)
│       ├── test_rate_limits.py     #   Rate limiting test (21 checks)
│       ├── test_audit.py           #   Audit log API test
│       ├── stress_test_audit.py    #   Audit stress test (5K entries)
│       ├── evaluate.py             #   Stress engine evaluation framework
│       ├── simulate.py             #   Synthetic student simulation
│       ├── list_routes.py          #   List all Flask routes
│       └── reset_pwd.py            #   Reset demo passwords
│
└── docs/                           # Documentation
    ├── REFERENCES.md
    ├── archive/
    │   └── CHANGES_APPLIED.md
    ├── features/
    │   ├── CONNECT_HUB_FEATURES.md
    │   └── PARENT_PORTAL_DOCS.md
    ├── implementation/
    │   └── CONNECT_HUB_IMPLEMENTATION.md
    └── research/
        ├── paper.md
        ├── stress_model.md
        └── eval_data/              # 4 evaluation CSVs
```

---

## Route Map

| URL Pattern | Blueprint | Template / Handler |
|---|---|---|
| `GET /login` | auth | `login.html` |
| `POST /login` | auth | Authenticate → redirect |
| `GET /logout` | auth | Clear session → redirect |
| `GET /ui/chat` | app | `index.html` |
| **Student** (`/student/*`) | student | |
| `GET /student/dashboard` | student | `student_dashboard.html` |
| `GET /student/chat/mental` | student | `mental_chatbot.html` |
| `GET /student/chat/study` | student | `study_chatbot.html` |
| `GET /student/relax` | student | `relax.html` |
| `GET /student/activities` | student | `activities.html` |
| `GET /student/games` | student | `games.html` |
| `GET /student/hub` | connect | `connect_hub.html` |
| `GET /student/_unregister_sw` | student | `unregister_sw.html` |
| **Proctor** (`/proctor/*`) | proctor | |
| `GET /proctor/dashboard` | proctor | `proctor_dashboard.html` |
| `GET /proctor/hod` | proctor | `hod_dashboard.html` |
| `GET /proctor/student/<id>` | proctor | `student_detail.html` |
| **Parent** (`/parent/*`) | parent | |
| `GET /parent/login` | parent | `parent_login.html` |
| `GET /parent/register` | parent | Redirect → `/parent/login` |
| `GET /parent/dashboard` | parent | `parent_dashboard.html` |

**Total registered routes: 137** (pages + APIs)

---

## Template → Asset Map

| Template | CSS | JS |
|---|---|---|
| `base.html` | `global.css`, `style.css` | `theme-engine.js`, `main.js` (module) |
| `login.html` | `login.css` | — |
| `student_dashboard.html` | `student_dashboard.css` | `student_dashboard.js`, `mood_handler.js` |
| `mental_chatbot.html` | `mental-chatbot.css` | `chat-engine.js`, `theme-engine.js` |
| `study_chatbot.html` | `study-assistant.css` | `study_chatbot.js` |
| `connect_hub.html` | `connect_hub.css` | `connect_hub.js` |
| `parent_dashboard.html` | — | `parent_dashboard.js` |
| `proctor_dashboard.html` | inline | inline |
| `hod_dashboard.html` | inline | inline + ApexCharts CDN |
| `index.html` | `sidebar.css`, `chat.css` | `main.js` (module) |

---

## Key Design Decisions

- **No ORM** — raw PyMongo for all MongoDB access
- **Anonymous IDs** — `STU_` + MD5(email)[:10] for student privacy
- **Inline CSS/JS** — proctor & HOD dashboards are self-contained (no external CSS/JS)
- **ES module** — `main.js` uses `import` syntax, loaded as `type="module"`
- **Rate limiting** — 5 tiers via Flask-Limiter (STANDARD → EXPORT)
- **Audit trail** — all proctor actions logged to `proctor_audit_log` collection
