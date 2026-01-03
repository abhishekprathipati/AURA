# AURA Theme System & UI Polish

Complete theming system with light/dark mode support, request locking, and polished micro-interactions.

## Features Implemented

### 1. **Core Theming with CSS Variables**
- Light and dark themes with separate color palettes
- All colors defined as CSS custom properties
- Smooth theme transitions (0.25s)
- System preference detection with localStorage persistence

**CSS Variables:**
```css
/* Light Theme (Default) */
--bg-primary: #ffffff
--bg-surface: #f8f9fa
--bg-elevated: #ffffff
--text-main: #1f1f1f
--text-muted: #70757a
--border-color: #dfe1e5
--accent: #6c63ff
--accent-light: rgba(108, 99, 255, 0.16)
--pill-shadow: 0 1px 6px rgba(32, 33, 36, 0.28)

/* Dark Theme */
--bg-primary: #131314
--bg-surface: #1e1f20
--bg-elevated: #1a1b1c
--text-main: #e3e3e3
--text-muted: #9aa0a6
--border-color: #444746
--accent: #8b84ff
--accent-light: rgba(139, 132, 255, 0.16)
--pill-shadow: 0 1px 6px rgba(0, 0, 0, 0.5)
```

### 2. **High-Contrast Input Field**
- Explicit text color via `color: var(--text-main)`
- Proper placeholder contrast with `--text-muted`
- Professional accent cursor: `caret-color: var(--accent)`
- Focus state with input ring
- Fixed width input pill (92% width, max 800px)

### 3. **Working Theme Toggle**
- Button in top nav with sun/moon SVG icons
- Persisted to localStorage with key `aura-ui-theme`
- Auto-detects system theme preference (prefers-color-scheme)
- Smooth icon transition
- Accessible with ARIA labels

### 4. **Request Locking**
- Global `isGenerating` flag prevents duplicate API calls
- Send button disabled and grayed out during request
- Input field disabled during processing
- `aria-busy` attribute for accessibility
- Proper unlock in finally block

### 5. **Polished Micro-Interactions**
- **Loading dots**: Animated pulse with staggered timing
- **Button hover**: `transform: translateY(-2px)` with shadow
- **Button active**: `transform: translateY(0)` return
- **Theme toggle**: `scale(1.05)` on hover, `scale(0.95)` on active
- **Message fade-in**: Smooth entry animation
- **Auto-scroll**: Smooth scroll to latest message

### 6. **Zen Mode Toggle**
- Full-width chat (sidebar hidden)
- Persistent via localStorage
- Smooth transition
- Button text changes: "Zen Mode" ↔ "Exit Zen"

## Files Created/Modified

### New Files
1. **[static/css/theme-system.css](static/css/theme-system.css)**
   - Complete theme system with CSS variables
   - Light/dark color palettes
   - All UI component theming
   - Responsive media queries
   - Zen mode styles

2. **[static/js/theme-engine.js](static/js/theme-engine.js)**
   - Theme initialization and persistence
   - Icon swapping (sun/moon SVGs)
   - System preference detection
   - Global API: `window.AURA_Theme`
   - Custom event emission: `themechange`

3. **[static/js/chat-engine.js](static/js/chat-engine.js)**
   - Complete chat logic with request locking
   - Message rendering and history
   - Zen mode management
   - LocalStorage chat persistence
   - Quick chip handlers
   - Element caching for performance

### Modified Files
1. **[templates/mental_chatbot.html](templates/mental_chatbot.html)**
   - Added theme-system.css link
   - Updated header with proper theme toggle button
   - Linked external JavaScript files
   - Cleaned up inline scripts

2. **[static/css/mental-chatbot.css](static/css/mental-chatbot.css)**
   - Replaced hardcoded colors with CSS variables
   - Maintains all existing styling
   - Now fully theme-aware

## Usage

### JavaScript API

```javascript
// Initialize (auto-init on DOMContentLoaded)
window.AURA_Theme.init();

// Apply theme
window.AURA_Theme.apply('dark'); // 'light' | 'dark'

// Get current theme
const current = window.AURA_Theme.current; // 'light' | 'dark'

// Set theme (shorthand)
window.AURA_Theme.set('dark');

// Listen for theme changes
window.addEventListener('themechange', (e) => {
  console.log('New theme:', e.detail.theme);
});
```

### CSS Variables Usage

In any CSS file:

```css
.my-element {
  background: var(--bg-primary);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  box-shadow: var(--pill-shadow);
}
```

## Verification Checklist

- ✅ Input text is readable in both themes
- ✅ Input placeholder has proper contrast
- ✅ Caret color matches accent
- ✅ Theme toggle persists via localStorage
- ✅ Send button disables during request
- ✅ Multiple requests prevented by isGenerating lock
- ✅ Messages centered with max-width 800px
- ✅ Loading dots animate smoothly
- ✅ Theme changes emit custom event
- ✅ System preference detected on first load
- ✅ Zen mode hides sidebar and expands chat
- ✅ All micro-interactions smooth and responsive
- ✅ Responsive design works on mobile

## Color Palettes

### Light Theme
- Primary Background: Clean white (#ffffff)
- Surface: Light gray (#f8f9fa)
- Text Main: Dark gray (#1f1f1f)
- Accent: Vibrant purple (#6c63ff)

### Dark Theme
- Primary Background: Deep black (#131314)
- Surface: Charcoal (#1e1f20)
- Text Main: Light gray (#e3e3e3)
- Accent: Soft purple (#8b84ff)

## Performance Notes

- CSS transitions: 0.25s ease (smooth but not slow)
- Element caching reduces DOM queries
- Smooth scroll uses requestAnimationFrame
- Loading animation: 1s infinite (efficient)
- No inline styles except for theme toggle button (will move to CSS)

## Future Enhancements

1. **Compact localStorage-based recent chats**
   - Store first 5 words + icon
   - Render sidebar items from localStorage

2. **Typewriter effect for bot replies**
   - Character-by-character reveal
   - Optional streaming mode

3. **Additional themes**
   - Warm theme (sunset palette)
   - Cool theme (ocean palette)
   - High contrast accessibility theme

4. **Gesture support**
   - Swipe left/right for theme toggle (mobile)
   - Long press for quick settings

## Browser Support

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support (iOS 13+)
- CSS Variables: IE 11 not supported (graceful fallback to light theme)

## Notes

- Theme preference stored in `localStorage` with key `aura-ui-theme`
- Zen mode stored with key `aura-zen-mode`
- Chat history stored with key `aura_mental_chats`
- All transitions are GPU-accelerated where possible
- Dark mode uses color-mix() for accent-light calculations
