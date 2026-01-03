# 📚 AURA Professional Study Assistant

## Overview
The Professional Study Assistant transforms AURA's study chatbot into a premium, three-column architecture interface with glassmorphism, professional spacing, and high-fidelity UI matching modern productivity apps.

## Design Specifications

### Three-Column Architecture

```
┌──────────────┬─────────────────────────────┬──────────────┐
│  LEFT        │       CENTER                │    RIGHT     │
│  SIDEBAR     │    CHAT VIEWPORT            │   STUDY HUB  │
│  (260px)     │      (Flexible)             │   (300px)    │
├──────────────┼─────────────────────────────┼──────────────┤
│              │                             │              │
│ 📚 AURA      │  Study Assistant  [Focus]   │  Study Hub   │
│ + New Chat   │  ─────────────────────────  │              │
│              │                             │  Quick       │
│ Recent:      │  Welcome back!              │  Actions:    │
│ 📝 Physics   │  What are you learning?     │  📤 Upload   │
│ ✏️ Essay     │                             │  ✅ Quiz     │
│ 📄 Mock Exam │  ✨ Summarize PDF           │              │
│              │  🎴 Flashcards              │  Recent      │
│              │  💡 Explain Concept         │  Files:      │
│              │                             │  📄 quantum  │
│              │  ────────────────────────   │  🖼️ history  │
│              │                             │              │
│              │  [Floating Input Pill]      │  Study Stats │
│              │  📎 Type message... 🎙️ ➤   │  Questions:  │
│              │  Disclaimer text            │  127         │
└──────────────┴─────────────────────────────┴──────────────┘
```

### Professional Spacing
- **Message Gap**: 2rem (32px) between message blocks for clarity
- **Sidebar Padding**: 20px 16px for comfortable spacing
- **Input Pill**: Floating with neon glow effect
- **Responsive**: Collapses to single column on mobile

## Key Features

### 1. Left Sidebar - Chat History
- **AURA Logo**: Gradient icon with branding
- **+ New Chat Button**: Purple accent, full-width
- **Recent Conversations**: 
  - Emoji icons for visual identification
  - Truncated text with ellipsis
  - Hover states for interactivity
  - Active state highlighting

### 2. Center Viewport - Main Chat
#### Top Navigation
- **Title**: "Study Assistant"
- **Focus Mode Toggle**: Switch for distraction-free mode
- **Theme Switcher**: Dark/Light mode toggle
- **User Profile**: Display student name
- **Back Button**: Return to dashboard

#### Welcome State
- **Greeting**: "Welcome back! What are you learning today?"
- **Quick Action Cards**:
  - ✨ Summarize PDF
  - 🎴 Generate Flashcards
  - 💡 Explain Concept
- **Example Prompts**: Clickable suggestions

#### Messages
- **User Messages**: 
  - Right-aligned purple gradient bubbles
  - 70% max-width for readability
  - Rounded corners (20px 20px 6px 20px)
- **Bot Messages**:
  - Left-aligned with avatar (📚)
  - Glassmorphism background
  - 80% max-width
  - Markdown support
  - Syntax highlighting for code

#### Floating Input Pill
- **Premium Design**: Glassmorphism with neon glow
- **Features**:
  - 📎 File attachment button
  - Text input with placeholder
  - 🎙️ Voice input button
  - ➤ Send button (circular, purple)
- **Disclaimer**: "AURA can help with studies, but always double-check your work"
- **Glow Effect**: `box-shadow: 0 0 48px rgba(139, 92, 246, 0.4)`

### 3. Right Sidebar - Study Hub
#### Quick Actions
- **Upload File**: Direct file upload
- **Create Quiz**: Generate quiz from materials

#### Recent Files
- **File Items**:
  - Icon (📄 for PDF, 🖼️ for images)
  - File name (truncated)
  - Timestamp ("2 hours ago", "Yesterday")
  - Hover effects

#### Study Stats
- **Metrics**:
  - Questions Asked: 127
  - Files Analyzed: 23
  - Study Streak: 🔥 5 days

## Technical Implementation

### Files Created
```
AURA/
├── templates/
│   └── study_assistant_pro.html    # Three-column HTML structure
├── static/
│   ├── css/
│   │   └── study-assistant.css     # Glassmorphism + responsive styles
│   └── js/
│       └── study-assistant.js      # Interactive features
└── routes/
    └── student.py                   # Added /chat/study/pro route
```

### CSS Features
- **Glassmorphism**: `backdrop-filter: blur(20px) saturate(180%)`
- **Dark/Light Themes**: CSS variables for easy switching
- **Smooth Animations**: Fade-in, slide-in effects
- **Professional Shadows**: Layered shadow system
- **Responsive Grid**: Collapses at 1200px and 900px breakpoints

### JavaScript Capabilities
- **Real-time Chat**: AJAX-based message handling
- **File Upload**: Drag & drop + click to upload
- **Voice Input**: Web Speech API integration
- **Theme Persistence**: LocalStorage for preferences
- **Focus Mode**: Hide sidebars for concentration
- **Keyboard Shortcuts**:
  - `Ctrl+K`: Toggle theme
  - `Ctrl+F`: Toggle focus mode
  - `Ctrl+N`: New chat
  - `Enter`: Send message

## API Endpoints

### GET `/student/chat/study/pro`
Renders the professional study assistant interface

### POST `/api/chat/study`
Handles chat messages
```json
Request:
{
  "message": "Explain quantum mechanics"
}

Response:
{
  "reply": "Quantum mechanics is..."
}
```

### POST `/api/chat/study/upload`
Handles file uploads
```json
Response:
{
  "analysis": "I've analyzed your document. Here are the key points..."
}
```

## Usage

### Accessing the Study Assistant
1. Navigate to `/student/chat/study/pro`
2. Or from dashboard: Click "Study Assistant" then "Pro Mode"

### Uploading Files
1. Click 📎 attach button
2. Or drag & drop into upload zone
3. Supports: PDF, DOC, DOCX, TXT, Images

### Using Voice Input
1. Click 🎙️ microphone button
2. Speak your question
3. Text appears in input field

### Focus Mode
1. Click "Focus Mode" toggle
2. Sidebars hide, chat expands
3. Distraction-free studying

### Quick Actions
- **Summarize PDF**: Upload file for automatic summarization
- **Generate Flashcards**: Create study flashcards from content
- **Explain Concept**: Get detailed explanations

## Color Palette

### Dark Theme (Default)
```
Primary Background:   #1a1d2e  ▓▓▓▓▓
Secondary Background: #232738  ▓▓▓▓
Tertiary Background:  #2d3148  ▓▓▓

Accent Purple:        #8b5cf6  ████
Accent Blue:          #3b82f6  ████
Accent Cyan:          #06b6d4  ████

Text Primary:         #ffffff  ████
Text Secondary:       #b4b8d0  ▓▓▓▓
Text Muted:           #6b7093  ▓▓▓
```

### Light Theme
```
Primary Background:   #f8f9fa  ░░░░░
Secondary Background: #ffffff  ░░░░
Tertiary Background:  #e9ecef  ░░░

Accent Purple:        #7c3aed  ████

Text Primary:         #1a1d2e  ████
Text Secondary:       #4a4e6e  ▓▓▓▓
Text Muted:           #8a8eae  ▓▓▓
```

## Message Formatting

### User Message
```html
<div class="message-block user-msg">
  <div class="content">
    User's message text
  </div>
</div>
```

### Bot Message with Avatar
```html
<div class="message-block bot-msg">
  <div class="bot-avatar">📚</div>
  <div class="content">
    <p>Bot response with <code>code</code></p>
    <ul>
      <li>Bullet points</li>
    </ul>
  </div>
</div>
```

## Responsive Breakpoints

| Breakpoint | Left Sidebar | Center | Right Sidebar | Input Position |
|------------|--------------|--------|---------------|----------------|
| > 1200px   | 260px full   | Flex   | 300px         | 260px - 300px  |
| 900-1200px | 60px icons   | Flex   | 300px         | 60px - 300px   |
| < 900px    | Hidden       | Full   | Hidden        | 0 - 0 (full)   |

## Accessibility Features
- **High Contrast**: White text on dark backgrounds
- **Keyboard Navigation**: Full keyboard support
- **ARIA Labels**: Screen reader friendly
- **Focus Indicators**: Clear focus states
- **Semantic HTML**: Proper heading hierarchy

## Performance Optimizations
- **Lazy Loading**: Messages render on demand
- **Debounced Events**: Prevent excessive API calls
- **RequestAnimationFrame**: Smooth scrolling
- **CSS Hardware Acceleration**: GPU-powered transforms

## Browser Compatibility
- Chrome 91+ ✅
- Firefox 90+ ✅
- Safari 14+ ✅
- Edge 91+ ✅

**Note**: Glassmorphism requires `backdrop-filter` support

## Future Enhancements
- [ ] **PDF Viewer**: In-app PDF display
- [ ] **Collaborative Study**: Multi-user sessions
- [ ] **Quiz Generation**: Auto-create quizzes from content
- [ ] **Spaced Repetition**: Smart flashcard scheduling
- [ ] **Export Options**: Save conversations as PDF
- [ ] **Code Execution**: Run code snippets
- [ ] **LaTeX Support**: Mathematical equations
- [ ] **Diagram Recognition**: Analyze uploaded diagrams

## Comparison: Original vs Pro

| Feature | Original | Pro |
|---------|----------|-----|
| Layout | 2-column | 3-column |
| Message Spacing | 15px | 32px (2rem) |
| Input | Inline | Floating pill |
| Glassmorphism | Basic | Advanced |
| File Upload | Basic | Drag & drop |
| Voice Input | ❌ | ✅ |
| Focus Mode | ❌ | ✅ |
| Theme Toggle | ❌ | ✅ |
| Stats Dashboard | ❌ | ✅ |
| Keyboard Shortcuts | ❌ | ✅ |

## Credits

**Design Inspired By**:
- ChatGPT UI patterns
- Google Gemini interface
- Notion's clean aesthetic
- Discord's three-column layout

**Technologies**:
- Flask backend
- Vanilla JavaScript (no dependencies)
- CSS Grid & Flexbox
- Marked.js for Markdown parsing

---

**Last Updated**: January 3, 2026
**Version**: 1.0.0
**Part of**: AURA Mental Wellness Platform
