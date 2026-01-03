# 🎨 AURA Theme System - Quick Start Guide

## What's Been Implemented

Your AURA mental health chatbot now has a **production-ready theme system** with light/dark modes, high-contrast inputs, request locking, and polished micro-interactions.

## 📦 New Files Added

### CSS
- **`static/css/theme-system.css`** (650+ lines)
  - Complete theme system with CSS variables
  - Light and dark color palettes
  - All UI components styled with variables
  - Zen mode and responsive design

### JavaScript
- **`static/js/theme-engine.js`** (100+ lines)
  - Theme initialization and persistence
  - Sun/moon icon SVGs
  - System theme preference detection
  - Global API: `window.AURA_Theme`

- **`static/js/chat-engine.js`** (400+ lines)
  - Complete chat logic with request locking
  - Message rendering and localStorage persistence
  - Zen mode toggle with localStorage
  - Quick chip handlers

### Documentation
- **`THEME_SYSTEM_DOCS.md`** - Complete feature documentation
- **`QUICKSTART.md`** - This file

## 🚀 How to Use

### 1. **Start Your Server**
```bash
python run.py
```

### 2. **Navigate to Mental Chat**
```
http://localhost:5000/student/chat/mental
```

### 3. **Test the Features**

#### Theme Toggle
- Click the sun/moon icon in the top right
- Try switching between light and dark modes
- Refresh the page - your preference is saved!

#### Request Locking
- Type a message and click send
- Try clicking send again quickly - it won't send twice
- Notice the button is disabled while waiting for response

#### Zen Mode
- Click "Zen Mode" to hide the sidebar and expand to full width
- Click "Exit Zen" to restore sidebar
- Your preference is saved

#### Input Field
- Notice the input field has high contrast in both themes
- Text is readable with proper colors
- Cursor color matches the accent color

#### Loading Animation
- When sending a message, you'll see animated dots
- Smooth, professional micro-interaction
- Only shows while waiting for AI response

## 🎨 Color Variables

All colors are defined in `theme-system.css` using CSS variables:

**Light Theme:**
```
--bg-primary: #ffffff        (Main background)
--bg-surface: #f8f9fa        (Surface layer)
--bg-elevated: #ffffff       (Elevated components)
--text-main: #1f1f1f         (Primary text)
--text-muted: #70757a        (Secondary text)
--border-color: #dfe1e5      (Borders)
--accent: #6c63ff            (Primary action color - purple)
```

**Dark Theme:**
```
--bg-primary: #131314        (Main background)
--bg-surface: #1e1f20        (Surface layer)
--bg-elevated: #1a1b1c       (Elevated components)
--text-main: #e3e3e3         (Primary text)
--text-muted: #9aa0a6        (Secondary text)
--border-color: #444746      (Borders)
--accent: #8b84ff            (Primary action color - light purple)
```

## 📊 Request Locking Implementation

The system prevents accidental double-submissions:

```javascript
let isGenerating = false;  // Global lock

async function handleSendMessage(e) {
  if (isGenerating) return;  // Already processing
  
  isGenerating = true;       // Lock
  updateSendButtonState();   // Disable button
  
  try {
    // Send request...
    await fetch('/student/chat/mental/send', {...});
  } finally {
    isGenerating = false;    // Unlock
    updateSendButtonState(); // Re-enable button
  }
}
```

## 🎯 High-Contrast Input

The input field uses proper contrast in both themes:

```css
#user-input {
  color: var(--text-main);           /* Readable text */
  caret-color: var(--accent);        /* Accent cursor */
  background: transparent;           /* Fits theme */
}

#user-input::placeholder {
  color: var(--text-muted);          /* Muted placeholder */
  opacity: 0.8;                      /* Subtle but visible */
}
```

## 🔌 JavaScript API

Use these in your code:

```javascript
// Apply a theme
window.AURA_Theme.apply('dark');    // or 'light'
window.AURA_Theme.set('light');     // shorthand

// Get current theme
const theme = window.AURA_Theme.current;

// Listen for changes
window.addEventListener('themechange', (e) => {
  console.log('Theme changed to:', e.detail.theme);
});
```

## 🎭 File Modifications

### Updated Files

**`templates/mental_chatbot.html`**
- Added link to `theme-system.css`
- Updated header with proper theme toggle button
- Linked external JavaScript files
- Removed inline scripts

**`static/css/mental-chatbot.css`**
- Replaced 10+ hardcoded colors with CSS variables
- Maintains all existing styling
- Now fully responsive to theme changes

## ✅ Testing Checklist

- [ ] Theme toggle button works
- [ ] Dark theme applies correctly
- [ ] Light theme applies correctly
- [ ] Theme persists after refresh
- [ ] Input field is readable in both themes
- [ ] Send button disables during request
- [ ] Loading dots animate
- [ ] Zen mode hides sidebar
- [ ] Zen mode preference persists
- [ ] Message history is maintained
- [ ] Quick chips work correctly
- [ ] No console errors

## 🛠️ Customization

### Change Accent Color

Edit `static/css/theme-system.css`:

```css
/* Light Theme */
:root[data-theme='light'] {
  --accent: #6c63ff;           /* Change this to your color */
}

/* Dark Theme */
:root[data-theme='dark'] {
  --accent: #8b84ff;           /* Change this to your color */
}
```

### Add Custom Colors

Add new CSS variables:

```css
:root[data-theme='light'] {
  --accent: #6c63ff;
  --success: #34a853;          /* New */
  --warning: #fbbc04;          /* New */
  --error: #ea4335;            /* New */
}
```

Then use them:
```css
.success-message {
  color: var(--success);
}
```

### Change Theme Transition Speed

Edit `theme-system.css`:

```css
* {
  transition: background-color 0.25s ease, /* Change 0.25s */
              border-color 0.25s ease,
              color 0.25s ease;
}
```

## 📱 Responsive Design

The system is fully responsive:

- **Desktop**: Sidebar + Chat area
- **Tablet**: Sidebar optional
- **Mobile**: Full-width chat (sidebar hidden by default)

## 🐛 Troubleshooting

**Theme not persisting?**
- Check browser localStorage is enabled
- Clear browser cache
- Check browser console for errors

**Input field not visible?**
- Verify CSS variables are defined
- Check contrast in theme palette
- Inspect element to see computed styles

**Request sent twice?**
- Ensure `isGenerating` lock is working
- Check send button disabled state
- Verify `finally` block executes

**Zen mode not working?**
- Check localStorage key: `aura-zen-mode`
- Verify CSS class: `.zen-mode`
- Check container element exists

## 📖 More Documentation

See **`THEME_SYSTEM_DOCS.md`** for:
- Complete feature list
- CSS variables reference
- Performance notes
- Browser support
- Future enhancement ideas

## 🎓 Next Steps

1. **Verify everything works** - Test theme toggle, request locking, Zen mode
2. **Customize colors** - Adjust accent color to match your brand
3. **Test on mobile** - Ensure responsive design works
4. **Add more themes** - Create warm/cool/high-contrast themes (optional)
5. **Monitor performance** - Check browser DevTools for smooth animations

---

**Built with ❤️ for AURA Mental Health Support**

Questions? Check the console for errors or review the inline comments in the JS files.
