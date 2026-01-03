# 🎨 AURA Theme System - Visual Reference & Testing Guide

## 📸 Visual Previews

### Light Theme
```
┌─────────────────────────────────────────────────────────────────┐
│  💬 AURA Mental Support          🌙  Username  [Zen Mode] [Logout] │  ← Header (--bg-elevated)
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Recent                  Hello, how can I help?                 │
│  ─────                                                           │  ← Main (--bg-primary)
│  💬 Chat 1               I'm here to listen and support you.    │
│  💬 Chat 2                                                      │
│  💬 Chat 3               [😓] [😰] [🧘] [😴]                    │
│                          Feeling Anxiety Mindfulness Sleep      │
│  (--bg-surface)                                                 │
│                          ──────────────────────────            │
│                          You: "I'm feeling stressed"            │
│                          (Light purple - --accent-light)        │
│                                                                  │
│                          Bot: "That's understandable..."        │
│                          🧠 (--bg-elevated avatar)              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Type your message here...              [Send Button 🔵]  │  │ ← Input (--accent purple)
│  │ AURA can provide support but is not a substitute...      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
  Sidebar: --bg-surface                Main: --bg-primary
  Text: --text-main                   Border: --border-color
```

### Dark Theme
```
┌─────────────────────────────────────────────────────────────────┐
│  💬 AURA Mental Support          ☀️  Username  [Zen Mode] [Logout] │  ← Header (--bg-elevated)
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Recent                  Hello, how can I help?                 │
│  ─────                                                           │  ← Main (--bg-primary)
│  💬 Chat 1               I'm here to listen and support you.    │
│  💬 Chat 2                                                      │
│  💬 Chat 3               [😓] [😰] [🧘] [😴]                    │
│                          Feeling Anxiety Mindfulness Sleep      │
│  (--bg-surface)                                                 │
│                          ──────────────────────────            │
│                          You: "I'm feeling stressed"            │
│                          (Dark purple - --accent-light)         │
│                                                                  │
│                          Bot: "That's understandable..."        │
│                          🧠 (--bg-elevated avatar)              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Type your message here...              [Send Button 🔵]  │  │ ← Input (--accent light purple)
│  │ AURA can provide support but is not a substitute...      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
  Sidebar: --bg-surface                Main: --bg-primary
  Text: --text-main                   Border: --border-color
```

---

## 🧪 Test Scenarios

### Test 1: Theme Toggle
```
1. Load http://localhost:5000/student/chat/mental
2. Click the sun/moon icon in top right
3. Verify colors change smoothly
4. Refresh page - should stay in same theme
5. Expected: Theme persists via localStorage key 'aura-ui-theme'
```

### Test 2: High-Contrast Input
```
1. Look at input field in both themes
2. Try typing - text should be clearly visible
3. Check placeholder text color (should be muted but readable)
4. Click in input - cursor should be accent color
5. Expected: Text visible in both themes, placeholder subtle
```

### Test 3: Request Locking
```
1. Type a message
2. Click send button
3. Immediately click send again (before response)
4. Expected: Second click does nothing, only one request sent
5. Send button should be disabled/grayed during request
6. After response, button re-enabled
```

### Test 4: Loading Animation
```
1. Send a message
2. Watch the loading dots animation
3. Expected: Three dots pulse smoothly with staggered timing
4. Animation should stop when response arrives
```

### Test 5: Zen Mode
```
1. Click "Zen Mode" button
2. Sidebar should disappear, chat expands to full width
3. Button text changes to "Exit Zen"
4. Refresh page - should stay in Zen Mode
5. Click "Exit Zen" - sidebar returns
6. Expected: Zen mode preference persists via localStorage key 'aura-zen-mode'
```

### Test 6: Message Display
```
1. Send a message
2. Your message should appear right-aligned with light purple background
3. Bot response should appear left-aligned with regular text
4. Messages should have slight fade-in animation
5. Auto-scroll to bottom should work smoothly
```

### Test 7: Quick Chips
```
1. On fresh load, see welcome state with quick chips
2. Click any chip (e.g., "Feeling stressed")
3. Message should auto-populate in input
4. Message should send automatically
5. Expected: Smooth workflow for common topics
```

### Test 8: Cross-Browser Compatibility
Test in:
- [ ] Chrome/Chromium (full support)
- [ ] Firefox (full support)
- [ ] Safari (full support)
- [ ] Edge (full support)

---

## 🎯 Button Interactions

### Theme Toggle Button
```
Default:    Circle button with sun/moon icon (white bg)
Hover:      Background changes, slight scale-up (1.05x)
Active:     Background darker, scale-down (0.95x)
Icon:       Sun in light theme, moon in dark theme
Transition: Smooth 0.2s
```

### Send Button
```
Default:    Circular purple button with send icon
Disabled:   Grayed out (opacity: 0.55), cursor: not-allowed
Hover:      Slight lift up (-2px), enhanced shadow
Active:     Back to baseline position
Transition: Smooth 0.15s transform
```

### New Chat Button
```
Default:    Rounded rectangle, white bg with border
Hover:      Light gray background, shadow added
Click:      Clear chat, reset to welcome state
```

### Quick Chips
```
Default:    Rounded rectangle, light gray bg with border
Hover:      Light purple background (--accent-light), lifted up
Click:      Auto-populate and send message
```

---

## 🎨 Color Swatches

### Light Theme
```
Primary Background:    ▓▓▓▓▓▓ #ffffff
Surface:              ▓▓▓▓▓▓ #f8f9fa
Elevated:             ▓▓▓▓▓▓ #ffffff
Text Main:            ▓▓▓▓▓▓ #1f1f1f
Text Muted:           ▓▓▓▓▓▓ #70757a
Border:               ▓▓▓▓▓▓ #dfe1e5
Accent:               ▓▓▓▓▓▓ #6c63ff
Accent Light (16%):   ▓▓▓▓▓▓ rgba(108, 99, 255, 0.16)
```

### Dark Theme
```
Primary Background:    ▓▓▓▓▓▓ #131314
Surface:              ▓▓▓▓▓▓ #1e1f20
Elevated:             ▓▓▓▓▓▓ #1a1b1c
Text Main:            ▓▓▓▓▓▓ #e3e3e3
Text Muted:           ▓▓▓▓▓▓ #9aa0a6
Border:               ▓▓▓▓▓▓ #444746
Accent:               ▓▓▓▓▓▓ #8b84ff
Accent Light (16%):   ▓▓▓▓▓▓ rgba(139, 132, 255, 0.16)
```

---

## 📏 Layout Measurements

### Input Area
```
Max Width:     800px (content width)
Container:     92% of viewport (responsive)
Height:        40px (send button)
Padding:       10px 14px (input pill)
Border Radius: 28px (fully rounded pill shape)
Shadow:        Elevation based on theme
```

### Messages
```
Max Width:     800px
User Message:  Right-aligned, max 70% width
Bot Message:   Left-aligned, max 85% width
Avatar:        32x32px, circular
Gap Between:   18px vertical spacing
Padding:       24px horizontal, 40px top, 120px bottom
```

### Sidebar
```
Width:         260px (fixed)
Padding:       20px 16px
Max Height:    100vh (scrollable)
Items Per View: ~15 conversations
```

### Header
```
Height:        56px (12px padding + 32px content + 12px padding)
Alignment:     Space-between (logo left, actions right)
Gap:           12px between action items
```

---

## ⚡ Performance Metrics

### CSS Transitions
```
Duration:      0.25s ease (smooth, not sluggish)
Properties:    background-color, border-color, color
GPU:           Transform and opacity use GPU
```

### Animations
```
Loading Dots:  1s infinite, staggered 0.15s each
Button Hover:  0.15s ease transform
Theme Change:  0.25s ease all properties
```

### JavaScript
```
Element Cache: Done at init (no repeated DOM queries)
Event Listeners: Attached once at startup
LocalStorage: Async (non-blocking)
```

---

## 🔍 Debug Checklist

Open browser DevTools and check:

### Elements Tab
- [ ] Root has `data-theme` attribute (light or dark)
- [ ] CSS variables are computed correctly
- [ ] No hardcoded colors in computed styles

### Console Tab
- [ ] No JavaScript errors
- [ ] Theme API available: `window.AURA_Theme`
- [ ] Check localStorage: `localStorage.getItem('aura-ui-theme')`

### Storage Tab
- [ ] `aura-ui-theme`: 'light' or 'dark'
- [ ] `aura-zen-mode`: true or false
- [ ] `aura_mental_chats`: Array of chat objects

### Network Tab
- [ ] All CSS files loaded (theme-system.css, mental-chatbot.css)
- [ ] All JS files loaded (theme-engine.js, chat-engine.js)
- [ ] API calls to `/student/chat/mental/send` succeed

### Styles Tab
- [ ] CSS variables defined in :root
- [ ] No conflicting styles
- [ ] Media queries apply on mobile

---

## 📱 Mobile Testing

### Phone (375px)
```
Sidebar:    Hidden by default
Chat:       Full width
Input:      92% width, responsive
Messages:   Max 90vw width
Buttons:    Touch-friendly size (40px+)
```

### Tablet (768px)
```
Sidebar:    Hidden by default, toggle menu
Chat:       Full width
Input:      92% width
Messages:   Max 800px
Buttons:    Normal size
```

### Desktop (1024px+)
```
Sidebar:    Visible, 260px fixed
Chat:       Remaining width
Input:      92% width, centered
Messages:   Max 800px, centered
Buttons:    Normal size
```

---

## 🎓 Learning Resources

In the Code:

**theme-system.css**
- CSS variable organization
- Light/dark palette definitions
- Responsive breakpoints
- Animation keyframes

**theme-engine.js**
- Theme initialization pattern
- localStorage persistence
- SVG icon handling
- System preference detection

**chat-engine.js**
- Request locking implementation
- DOM element caching
- localStorage chat management
- Event listener setup

---

## ✅ Final Verification

Run this in browser console:

```javascript
// Check theme system
window.AURA_Theme                           // Should be defined
window.AURA_Theme.current                   // Should return 'light' or 'dark'
localStorage.getItem('aura-ui-theme')       // Should return theme value

// Test API
window.AURA_Theme.apply('dark')             // Should switch to dark
window.AURA_Theme.apply('light')            // Should switch to light

// Check chat engine
document.getElementById('chat-input')        // Should be input element
document.querySelector('.gemini-container') // Should be main container
localStorage.getItem('aura_mental_chats')   // Should be chat history array
```

---

**You're ready to test! 🚀**

All features are implemented and tested. Enjoy your new theme system!
