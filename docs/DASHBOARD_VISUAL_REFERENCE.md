# 🎨 Ultra-Pro Dashboard Visual Reference

## Component Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│  FLOATING NAVIGATION (Glassmorphism)                            │
│  [AURA 🧠 PRO] [Dashboard] [Activities] [Insights] [Zen] [Theme]│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  HEADER                                                          │
│  Welcome back, Student                                           │
│  Your wellness command center • Friday, January 3, 2026         │
│                                    [🧘 Quick Breathing] [☕ Break]│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CENTRAL METRIC HUB - Stress Level Monitor                      │
│  ┌───────────────────────────────────────┐  [● Live]            │
│  │         ╱──────────╲                  │                      │
│  │        ╱            ╲                 │                      │
│  │       │      50      │                │                      │
│  │        ╲  STRESS    ╱                 │                      │
│  │         ╲  LEVEL   ╱                  │                      │
│  │          ╲────────╱                   │                      │
│  │    [● Moderate - Stay Balanced]      │                      │
│  └───────────────────────────────────────┘                      │
│  ┌────────┐ ┌────────┐ ┌────────┐                              │
│  │Peak: 72│ │Avg: 52 │ │↓ Falling│                             │
│  └────────┘ └────────┘ └────────┘                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  BENTO GRID - Activity Cards                                    │
│  ┌─────────────────────┐ ┌──────────┐ ┌──────────┐            │
│  │ 💬 Mental Support   │ │🎨 Break  │ │🎤 Scream │            │
│  │ AI companion ready  │ │ Room     │ │ Meter    │            │
│  │ [How are you...]    │ │Creative  │ │Release   │            │
│  │ → Start Conversation│ │→ Enter   │ │▶ Try Now │            │
│  └─────────────────────┘ └──────────┘ └──────────┘            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                       │
│  │🧘 Box    │ │📚 Study  │ │🎮 Mind   │                       │
│  │Breathing │ │Assistant │ │Games     │                       │
│  │4-4-4-4   │ │Academic  │ │Brain     │                       │
│  │▶ Begin   │ │→ Get Help│ │▶ Play    │                       │
│  └──────────┘ └──────────┘ └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  📊 WELLNESS INSIGHTS                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │🎭 Current│ │🤖 AI     │ │🔥 Wellness│ │⭐ Activities│       │
│  │Mood      │ │Insights  │ │Streak    │ │Completed │         │
│  │Calm   ↗  │ │Positive 📄│ │1 Day ⚡  │ │12      +3│         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  📝 NEED HELP?                                                   │
│  Submit a concern or grievance                                   │
│  [Submit Grievance +]                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Color Palette

### Dark Theme (Default)
```css
Background Primary:   #0a0a0f  ▓▓▓▓▓
Background Secondary: #121218  ▓▓▓▓
Background Tertiary:  #1a1a24  ▓▓▓

Accent Purple:        #8b5cf6  ████
Accent Cyan:          #06b6d4  ████
Accent Pink:          #ec4899  ████
Accent Green:         #10b981  ████
Accent Yellow:        #f59e0b  ████
Accent Red:           #ef4444  ████

Text Primary:         #ffffff  ████
Text Secondary:       #a0a0b8  ▓▓▓▓
Text Muted:           #6b6b84  ▓▓▓
```

### Light Theme
```css
Background Primary:   #f8f9fa  ░░░░░
Background Secondary: #ffffff  ░░░░
Background Tertiary:  #e9ecef  ░░░

Accent Purple:        #7c3aed  ████
Accent Cyan:          #0891b2  ████

Text Primary:         #1a1a24  ████
Text Secondary:       #4a4a5e  ▓▓▓▓
Text Muted:           #8a8a9e  ▓▓▓
```

## Component Specifications

### Floating Navigation
```
Height: 72px
Background: Glassmorphism (backdrop-filter: blur(20px))
Border: 1px solid rgba(255,255,255,0.1)
Shadow: 0 2px 8px rgba(0,0,0,0.3)
```

### Central Metric Hub
```
Padding: 32px
Border-radius: 24px
Background: Glass with blur
Gauge Size: 280px × 180px
SVG Arc Length: 220 units
Animation: 1.5s cubic-bezier
```

### Bento Cards
```
Min-Width: 280px
Padding: 24px
Border-radius: 20px
Gap: 20px
Hover Transform: translateY(-4px)
Transition: 0.3s cubic-bezier(0.4,0,0.2,1)
```

### Insight Cards
```
Padding: 20px
Border-radius: 16px
Icon Size: 48px × 48px
Gradient: 135deg angle
```

## Animation Specifications

### Pulse Animation (Live Indicator)
```css
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.5; transform: scale(0.8); }
}
Duration: 2s ease-in-out infinite
```

### Breathing Box Animation
```css
@keyframes breathe {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50%      { transform: scale(1.2); opacity: 1; }
}
Duration: 4s ease-in-out infinite
```

### Modal Slide In
```css
@keyframes modalSlideIn {
  from { opacity: 0; transform: translateY(-20px); }
  to   { opacity: 1; transform: translateY(0); }
}
Duration: 0.3s ease
```

## Stress Gauge Color Zones

```
   GREEN ZONE (0-30%)
   ════════════════════════
   Status: Excellent & Balanced
   Color: #10b981
   Message: "Amazing! Great state of mind"

   YELLOW ZONE (30-60%)
   ════════════════════════
   Status: Moderate - Stay Balanced
   Color: #f59e0b
   Message: "Managing well. Take breaks"

   RED ZONE (60-100%)
   ════════════════════════
   Status: High - Take Action
   Color: #ef4444
   Message: "Time for self-care!"
```

## Interactive States

### Button Hover
```
Transform: translateY(-2px)
Box-shadow: Elevated + Glow
Border: Accent color
Background: Glass hover
```

### Card Hover
```
Transform: translateY(-4px) scale(1.02)
Box-shadow: Large + Glow
Border: Purple accent
Overlay: 5% gradient opacity
```

### Input Focus
```
Border: Purple accent
Box-shadow: 0 0 0 3px rgba(139,92,246,0.1)
Outline: None
```

## Responsive Breakpoints

```
┌─────────────┬──────────────┬─────────────┐
│  Desktop    │   Tablet     │   Mobile    │
│  > 1024px   │  768-1024px  │  < 768px    │
├─────────────┼──────────────┼─────────────┤
│ Full Bento  │ 2-col Bento  │ 1-col Stack │
│ Grid        │ Grid         │             │
│ Nav Center  │ Nav Center   │ Nav Hidden  │
│ Gauge 280px │ Gauge 240px  │ Gauge 220px │
└─────────────┴──────────────┴─────────────┘
```

## Glassmorphism Effect

```css
background: rgba(255, 255, 255, 0.05);
backdrop-filter: blur(20px) saturate(180%);
-webkit-backdrop-filter: blur(20px) saturate(180%);
border: 1px solid rgba(255, 255, 255, 0.1);
```

## Shadow System

```
Small:  0 2px 8px rgba(0,0,0,0.3)
Medium: 0 4px 16px rgba(0,0,0,0.4)
Large:  0 8px 32px rgba(0,0,0,0.5)
Glow:   0 0 24px rgba(139,92,246,0.3)
```

## Typography Scale

```
Hero Title:      2rem   (32px)  Font-weight: 700
Section Heading: 1.5rem (24px)  Font-weight: 700
Card Title:      1.15rem(18px)  Font-weight: 700
Body Text:       0.95rem(15px)  Font-weight: 400
Small Text:      0.8rem (13px)  Font-weight: 500
```

## Icon Sizes

```
Nav Icons:       16px × 16px
Bento Icons:     48px × 48px (in 48px box)
Insight Icons:   48px × 48px (in 48px box)
Button Icons:    14px × 14px
Avatar:          32px × 32px
```

## Grid Specifications

### Bento Grid
```css
display: grid;
grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
gap: 20px;
```

### Insights Grid
```css
display: grid;
grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
gap: 16px;
```

### Stress Metrics Row
```css
display: grid;
grid-template-columns: repeat(3, 1fr);
gap: 16px;
```

---

**Reference Version**: 1.0.0
**Last Updated**: January 3, 2026
