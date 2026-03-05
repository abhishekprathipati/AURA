# Parent Portal Implementation

## Overview
Complete parent login and dashboard system where parents can monitor student wellness, raise complaints, provide suggestions, and view department updates.

## Features Implemented

### 1. Parent Registration
- **File**: `templates/parent_register.html`
- **Route**: `/parent/register` (GET/POST)
- Features:
  - Link parent account to student via roll number
  - Parent details: name, email, phone, relationship
  - Password validation with confirmation
  - Student verification before registration
  - Prevents duplicate parent accounts

### 2. Parent Login
- **File**: `templates/parent_login.html`
- **Route**: `/parent/login` (GET/POST)
- Features:
  - Login with student roll number + parent password
  - Session-based authentication
  - Redirect to dashboard on success
  - Links to student/HOD login portals
  - Link to registration for new parents

### 3. Parent Dashboard
- **File**: `templates/parent_dashboard.html`
- **JavaScript**: `static/js/parent_dashboard.js`
- **Route**: `/parent/dashboard`

#### Dashboard Sections:

**A. Student Academic Performance**
- Stress level tracking with area chart
- Mood distribution with donut chart
- Historical wellness data visualization
- Tab switching between stress and mood views

**B. Complaint System**
- Submit complaints with categories:
  - Academic
  - Infrastructure
  - Faculty
  - Hostel
  - Other
- Priority levels: Low, Medium, High
- View complaint history with status tracking
- Status indicators: Pending, In Progress, Resolved

**C. Suggestions Box**
- Submit improvement suggestions
- Categories:
  - Academic Improvement
  - Facilities
  - Extracurricular
  - Student Wellness
  - Other
- Track suggestion submissions

**D. Announcements Feed**
- Department achievements
- Placement updates
- General announcements
- Filter by type (All, Achievements, Placements)
- Relative timestamps (Just now, 5m ago, 2h ago)

## API Endpoints

### Authentication
- `GET/POST /parent/register` - Parent registration
- `GET/POST /parent/login` - Parent login
- `GET /parent/logout` - Logout and clear session

### Dashboard Data
- `GET /parent/api/student/performance` - Student stress/mood data
- `POST /parent/api/complaint/submit` - Submit new complaint
- `GET /parent/api/complaints/list` - Get parent's complaints
- `POST /parent/api/suggestion/submit` - Submit suggestion
- `GET /parent/api/announcements` - Get achievements/placements

## Database Collections

### `parents`
```javascript
{
  student_roll: String,
  parent_name: String,
  parent_email: String,
  parent_phone: String,
  password: String (hashed),
  relationship: String, // father/mother/guardian
  created_at: Date,
  last_login: Date
}
```

### `parent_complaints`
```javascript
{
  student_roll: String,
  parent_name: String,
  category: String,
  subject: String,
  description: String,
  priority: String,
  status: String, // pending/in-progress/resolved
  created_at: Date,
  updated_at: Date,
  responses: Array
}
```

### `parent_suggestions`
```javascript
{
  student_roll: String,
  parent_name: String,
  title: String,
  description: String,
  category: String,
  status: String,
  upvotes: Number,
  created_at: Date
}
```

### `announcements`
```javascript
{
  type: String, // achievements/placements/general
  title: String,
  content: String,
  department: String,
  created_at: Date
}
```

## Session Management

Parent session stores:
- `parent_logged_in`: Boolean
- `student_roll`: String
- `parent_name`: String
- `parent_email`: String

## Security Features

1. **Password Hashing**: Werkzeug security with `generate_password_hash`
2. **Session Authentication**: `@parent_login_required` decorator
3. **Student Verification**: Validates student exists before registration
4. **Duplicate Prevention**: One parent account per student
5. **Input Validation**: Required fields and format checking

## UI/UX Features

1. **Gradient Design**: Purple gradient theme matching AURA branding
2. **Responsive Layout**: Works on desktop and mobile
3. **Interactive Charts**: ApexCharts for data visualization
4. **Form Validation**: Client-side and server-side validation
5. **Real-time Alerts**: Success/error notifications
6. **Tab Navigation**: Easy switching between dashboard sections
7. **Smooth Animations**: Hover effects and transitions
8. **Status Badges**: Color-coded status indicators

## How to Use

### For Parents:

1. **Register Account**:
   - Visit `/parent/register`
   - Enter student's roll number
   - Fill parent details and create password
   - System verifies student exists

2. **Login**:
   - Visit `/parent/login`
   - Enter student roll number and password
   - Access dashboard automatically

3. **Monitor Student**:
   - View stress levels and mood patterns
   - Track wellness trends over time
   - Identify concerning patterns

4. **Raise Complaints**:
   - Submit concerns about student experience
   - Track complaint status
   - Receive updates on resolution

5. **Provide Suggestions**:
   - Share improvement ideas
   - Contribute to institutional development

6. **Stay Informed**:
   - View department achievements
   - Track placement opportunities
   - Read general announcements

## Integration Points

The parent portal integrates with:
- Student wellness tracking (`student_analytics`, `mood_logs`)
- User management (`users` collection)
- Announcement system
- Complaint tracking system

## Future Enhancements

Possible additions:
- Email notifications for complaint updates
- Parent-teacher meeting scheduler
- Student attendance tracking
- Academic grades/marks view
- Fee payment integration
- Direct messaging with HOD/faculty
- Complaint response system for administrators

## Files Created

1. `models/parent.py` - Parent data model
2. `routes/parent.py` - Parent routes and API
3. `templates/parent_register.html` - Registration page
4. `templates/parent_login.html` - Login page
5. `templates/parent_dashboard.html` - Dashboard UI
6. `static/js/parent_dashboard.js` - Dashboard functionality

## Testing the System

1. Start the Flask app: `python run.py`
2. Navigate to `/parent/register`
3. Register with an existing student roll number
4. Login at `/parent/login`
5. Explore all dashboard features

## Notes

- Sample data is generated for announcements if database is empty
- Charts show historical data when available
- All forms have validation and error handling
- Responsive design adapts to screen size
- Session expires on logout
