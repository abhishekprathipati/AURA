# 🧠 AURA Ultra-Pro Wellness Command Center

## Overview
The Ultra-Pro Student Wellness Dashboard transforms AURA into a full-screen command center that monitors stress, tracks habits, and provides instant mental health tools with a premium, data-driven interface.

## Design Philosophy
- **Glassmorphism Aesthetic**: Dark mode with purple/cyan gradient accents
- **Bento-Grid Layout**: Interactive tiles for quick access to wellness activities
- **Real-time Monitoring**: Live stress gauge with dynamic color gradients
- **Command Center Feel**: Premium tech aesthetic similar to Google Gemini or fintech apps

## Key Features

### 1. Central Metric Hub - Stress Level Monitor
- **Dynamic SVG Gauge**: Semi-circular gauge (0-100) with smooth animations
- **Color-Coded Status**: 
  - Green (0-30): Excellent & Balanced
  - Yellow (30-60): Moderate - Stay Balanced
  - Red (60-100): High - Take Action
- **Live Indicator**: Pulsing dot showing real-time updates
- **Metrics Row**: 
  - Today's Peak stress
  - Average stress
  - Trend indicator (Rising/Falling/Stable)

### 2. Floating Navigation Bar
- **Semi-transparent**: Glassmorphism with backdrop blur
- **Smart Tabs**: Dashboard, Activities, Insights views
- **Zen Mode Toggle**: Distraction-free mode
- **Theme Switcher**: Dark/Light mode toggle
- **User Profile**: Quick access with avatar

### 3. Bento-Grid Activity Cards
Interactive tiles with hover animations:
- **Mental Support** (Large tile): AI chatbot with conversation preview
- **Virtual Break Room**: Creative relaxation activities
- **Scream Meter**: Vocal stress release tool
- **Box Breathing**: 4-4-4-4 breathing technique with animated preview
- **Study Assistant**: Academic support AI
- **Mind Games**: Brain training exercises

### 4. Wellness Insights Panel
Quick snapshot metrics:
- **Current Mood**: Latest mood with trend indicator
- **AI Insights**: Smart analysis of wellness patterns
- **Wellness Streak**: Consecutive days of activity
- **Activities Completed**: Total engagement count

### 5. Quick Action Pills
Header buttons for instant access:
- **Quick Breathing**: Direct link to breathing exercises
- **Virtual Break**: Immediate relaxation tools

### 6. Grievance Modal
- Overlay modal for submitting concerns
- Clean form with subject and description
- AJAX submission without page reload

## Technical Stack

### Frontend
- **HTML5**: Semantic structure with accessibility features
- **CSS3**: 
  - CSS Variables for theming
  - Glassmorphism effects with `backdrop-filter`
  - CSS Grid for bento layout
  - Smooth animations and transitions
  - Responsive design (mobile-first)
- **JavaScript**:
  - Vanilla JS (no dependencies)
  - Real-time API integration
  - SVG gauge manipulation
  - Theme persistence (localStorage)
  - Keyboard shortcuts (Ctrl+K, Ctrl+Z)

### Backend
- **Flask**: Python web framework
- **MongoDB**: Database for stress/mood tracking
- **RESTful API**: JSON endpoints for data exchange

## File Structure

```
AURA/
├── templates/
│   └── student_dashboard_pro.html    # Ultra-Pro dashboard HTML
├── static/
│   ├── css/
│   │   └── dashboard-pro.css         # Glassmorphism styles
│   └── js/
│       └── dashboard-pro.js          # Dashboard engine
└── routes/
    └── student.py                     # Backend routes & API
```

## API Endpoints

### GET `/student/dashboard/pro`
Renders the Ultra-Pro dashboard page

### GET `/api/student/stress-level`
Returns current stress data with metrics:
```json
{
  "stress_level": 45,
  "peak": 72,
  "average": 52,
  "trend": "down"
}
```

### GET `/api/student/dashboard-data`
Returns comprehensive dashboard data:
```json
{
  "mood": "Calm",
  "ai_insight": "Positive",
  "streak": 3,
  "activities_count": 15
}
```

### POST `/api/student/grievance`
Submits a grievance with subject and description

## Usage

### Accessing the Dashboard
1. Navigate to `/student/dashboard/pro`
2. Or click "✨ Pro Mode" button from regular dashboard

### Keyboard Shortcuts
- `Ctrl/Cmd + K`: Toggle theme (Dark/Light)
- `Ctrl/Cmd + Z`: Toggle Zen Mode
- `Esc`: Close modal

### Theme Switching
- Click the sun/moon icon in navigation
- Theme preference persists across sessions
- Smooth transition between light and dark modes

### Zen Mode
- Removes navigation distractions
- Focus on core metrics and activities
- Toggle state persists

## Customization

### Color Scheme
Edit CSS variables in `dashboard-pro.css`:
```css
:root[data-theme='dark'] {
    --accent-purple: #8b5cf6;
    --accent-cyan: #06b6d4;
    --accent-pink: #ec4899;
    /* ... */
}
```

### Stress Gauge Colors
Modify the SVG gradient in HTML:
```html
<linearGradient id="gaugeGradient">
    <stop offset="0%" stop-color="#10b981"/>   <!-- Green -->
    <stop offset="50%" stop-color="#f59e0b"/>  <!-- Yellow -->
    <stop offset="100%" stop-color="#ef4444"/> <!-- Red -->
</linearGradient>
```

### Bento Grid Layout
Adjust grid columns in CSS:
```css
.bento-grid {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
}
```

## Responsive Breakpoints

- **Desktop**: > 1024px - Full bento grid
- **Tablet**: 768px - 1024px - Adjusted columns
- **Mobile**: < 768px - Single column stack

## Browser Compatibility

- Chrome 91+ ✅
- Firefox 90+ ✅
- Safari 14+ ✅
- Edge 91+ ✅

**Note**: Glassmorphism effects require `backdrop-filter` support. Falls back gracefully on older browsers.

## Performance Optimizations

1. **CSS Optimization**:
   - Hardware-accelerated transforms
   - Will-change hints for animations
   - Minimal repaints

2. **JavaScript**:
   - Debounced event handlers
   - RequestAnimationFrame for smooth animations
   - Lazy loading of heavy components

3. **API Calls**:
   - Batched requests
   - Client-side caching
   - Automatic retry on failure

## Future Enhancements

- [ ] **Scream Meter Implementation**: Web Audio API for vocal stress measurement
- [ ] **Activity History Graph**: Chart.js integration for trend visualization
- [ ] **Push Notifications**: Service Worker for wellness reminders
- [ ] **Offline Support**: Progressive Web App capabilities
- [ ] **Voice Commands**: Web Speech API integration
- [ ] **Biometric Integration**: Heart rate monitoring (if available)
- [ ] **Social Features**: Share achievements with peers
- [ ] **Gamification**: Badges and rewards system

## Troubleshooting

### Stress Gauge Not Updating
- Check browser console for API errors
- Verify MongoDB connection
- Ensure user has stress data in database

### Theme Not Persisting
- Check localStorage permissions
- Verify JavaScript console for errors
- Clear browser cache and try again

### Glassmorphism Not Working
- Update to modern browser with `backdrop-filter` support
- Check if browser has hardware acceleration enabled

## Credits

**Design Inspired By**:
- Google Gemini UI
- Apple's Human Interface Guidelines
- Fintech dashboard aesthetics

**Technologies**:
- Flask + MongoDB
- Inter Font Family (Google Fonts)
- CSS Grid & Flexbox
- SVG Graphics

## License

Part of the AURA Mental Wellness Platform.
Built with 💜 by Team AURA.

---

**Last Updated**: January 3, 2026
**Version**: 1.0.0
