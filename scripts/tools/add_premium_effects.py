"""Add ultra-premium visual effects to student dashboard."""
import pathlib

css_path = pathlib.Path(r"d:\AURA\static\css\student_dashboard.css")
css = css_path.read_text(encoding='utf-8')

premium_css = """

/* ═══════════════════════════════════════════════════════════════
   ULTRA-PREMIUM VISUAL EFFECTS - TOP 0.0000001%
   ═══════════════════════════════════════════════════════════════ */

/* ──────── Animated Gradient Mesh Background ──────── */
@keyframes gradientShift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

@keyframes float {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    33% { transform: translateY(-20px) rotate(3deg); }
    66% { transform: translateY(-10px) rotate(-3deg); }
}

@keyframes shimmerSlide {
    0% { transform: translateX(-100%) translateY(-100%) rotate(30deg); }
    100% { transform: translateX(100%) translateY(100%) rotate(30deg); }
}

@keyframes glow {
    0%, 100% { box-shadow: 0 0 20px rgba(107,115,255,0.3), 0 0 40px rgba(159,122,234,0.2); }
    50% { box-shadow: 0 0 30px rgba(107,115,255,0.5), 0 0 60px rgba(159,122,234,0.3); }
}

@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes scaleIn {
    from {
        opacity: 0;
        transform: scale(0.9);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}

@keyframes borderGlow {
    0%, 100% { border-color: rgba(var(--primary-rgb), 0.3); }
    50% { border-color: rgba(var(--primary-rgb), 0.6); }
}

/* ──────── Premium Dashboard Container ──────── */
.dashboard {
    position: relative;
    overflow: hidden;
}

.dashboard::before {
    content: "";
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 20% 50%, rgba(107,115,255,0.03) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(159,122,234,0.03) 0%, transparent 50%);
    animation: gradientShift 20s ease infinite;
    pointer-events: none;
    z-index: 0;
}

.dashboard > * {
    position: relative;
    z-index: 1;
}

/* ──────── 3D Card Tilt Effect ──────── */
.card-3d-tilt {
    transform-style: preserve-3d;
    transition: transform 0.1s ease-out, box-shadow 0.3s ease;
    will-change: transform;
}

.card-3d-tilt:hover {
    box-shadow: 
        0 20px 40px rgba(0,0,0,0.1),
        0 0 0 1px rgba(var(--primary-rgb), 0.05),
        inset 0 1px 0 rgba(255,255,255,0.1);
}

/* ──────── Premium Glassmorphism ──────── */
.glass-effect {
    background: rgba(255, 255, 255, 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    box-shadow: 
        0 8px 32px rgba(0,0,0,0.08),
        inset 0 1px 1px rgba(255,255,255,0.9),
        inset 0 -1px 1px rgba(0,0,0,0.03);
}

[data-theme="dark"] .glass-effect {
    background: rgba(30, 30, 46, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 
        0 8px 32px rgba(0,0,0,0.4),
        inset 0 1px 1px rgba(255,255,255,0.1),
        inset 0 -1px 1px rgba(0,0,0,0.2);
}

/* ──────── Shimmer Overlay Effect ──────── */
.shimmer-effect {
    position: relative;
    overflow: hidden;
}

.shimmer-effect::after {
    content: "";
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(
        120deg,
        transparent,
        rgba(255,255,255,0.3) 50%,
        transparent
    );
    animation: shimmerSlide 3s ease-in-out infinite;
    pointer-events: none;
}

[data-theme="dark"] .shimmer-effect::after {
    background: linear-gradient(
        120deg,
        transparent,
        rgba(255,255,255,0.1) 50%,
        transparent
    );
}

/* ──────── Floating Animation ──────── */
.float-animation {
    animation: float 6s ease-in-out infinite;
}

/* ──────── Staggered Entrance Animations ──────── */
.fade-in-up {
    animation: slideInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) backwards;
}

.scale-in {
    animation: scaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
}

/* Stagger delays */
.stagger-1 { animation-delay: 0.05s; }
.stagger-2 { animation-delay: 0.1s; }
.stagger-3 { animation-delay: 0.15s; }
.stagger-4 { animation-delay: 0.2s; }
.stagger-5 { animation-delay: 0.25s; }
.stagger-6 { animation-delay: 0.3s; }
.stagger-7 { animation-delay: 0.35s; }
.stagger-8 { animation-delay: 0.4s; }

/* ──────── Premium Glow Effects ──────── */
.glow-effect {
    position: relative;
}

.glow-effect::before {
    content: "";
    position: absolute;
    inset: -2px;
    border-radius: inherit;
    padding: 2px;
    background: linear-gradient(135deg, rgba(107,115,255,0.5), rgba(159,122,234,0.5));
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
}

.glow-effect:hover::before {
    opacity: 1;
}

/* ──────── Magnetic Button Effect ──────── */
.magnetic-btn {
    transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* ──────── Advanced Shadows ──────── */
.shadow-premium {
    box-shadow: 
        0 1px 3px rgba(0,0,0,0.02),
        0 4px 8px rgba(0,0,0,0.03),
        0 12px 24px rgba(0,0,0,0.04),
        0 24px 48px rgba(0,0,0,0.05);
}

.shadow-premium-hover {
    transition: box-shadow 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.shadow-premium-hover:hover {
    box-shadow: 
        0 2px 6px rgba(0,0,0,0.03),
        0 8px 16px rgba(0,0,0,0.05),
        0 20px 40px rgba(0,0,0,0.07),
        0 40px 80px rgba(0,0,0,0.09);
}

/* ──────── Gradient Text Effect ──────── */
.gradient-text {
    background: linear-gradient(135deg, #6b73ff 0%, #9f7aea 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    background-size: 200% auto;
    animation: gradientShift 3s ease infinite;
}

/* ──────── Premium Card Enhancements ──────── */
.premium-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    position: relative;
    overflow: hidden;
}

.premium-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, 
        transparent, 
        rgba(var(--primary-rgb), 0.5), 
        transparent);
    opacity: 0;
    transition: opacity 0.3s;
}

.premium-card:hover::before {
    opacity: 1;
}

.premium-card:hover {
    transform: translateY(-4px);
    border-color: rgba(var(--primary-rgb), 0.2);
}

/* ──────── Ripple Effect ──────── */
@keyframes ripple {
    to {
        transform: scale(4);
        opacity: 0;
    }
}

.ripple-container {
    position: relative;
    overflow: hidden;
}

.ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(var(--primary-rgb), 0.3);
    transform: scale(0);
    animation: ripple 0.6s ease-out;
    pointer-events: none;
}

/* ──────── Particle Decoration ──────── */
@keyframes particle-float {
    0%, 100% { transform: translate(0, 0) rotate(0deg); opacity: 0.3; }
    25% { transform: translate(10px, -10px) rotate(90deg); opacity: 0.5; }
    50% { transform: translate(0, -20px) rotate(180deg); opacity: 0.3; }
    75% { transform: translate(-10px, -10px) rotate(270deg); opacity: 0.5; }
}

.particle-bg {
    position: absolute;
    width: 4px;
    height: 4px;
    background: linear-gradient(135deg, rgba(107,115,255,0.3), rgba(159,122,234,0.3));
    border-radius: 50%;
    pointer-events: none;
    animation: particle-float 8s ease-in-out infinite;
}

/* ──────── Enhanced Quick Actions ──────── */
.qa-card {
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    position: relative;
}

.qa-card::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(135deg, rgba(107,115,255,0.1), rgba(159,122,234,0.1));
    opacity: 0;
    transition: opacity 0.3s;
}

.qa-card:hover::after {
    opacity: 1;
}

/* ──────── Enhanced Sidebar Buttons ──────── */
.sidebar-btn {
    position: relative;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.sidebar-btn::before {
    content: "";
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 3px;
    height: 0%;
    background: linear-gradient(180deg, #6b73ff, #9f7aea);
    border-radius: 0 3px 3px 0;
    transition: height 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.sidebar-btn:hover::before {
    height: 70%;
}

/* ──────── Today's Summary Enhanced ──────── */
.sidebar-summary-card {
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
}

.sidebar-summary-card::before {
    content: "";
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(107,115,255,0.05) 0%, transparent 70%);
    animation: gradientShift 10s ease infinite;
    pointer-events: none;
}

.stat-value {
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    display: inline-block;
}

.stat-value:hover {
    transform: scale(1.15);
}

/* ──────── Premium Tab Buttons ──────── */
.dash-tab {
    position: relative;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.dash-tab::after {
    content: "";
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%) scaleX(0);
    width: 80%;
    height: 3px;
    background: linear-gradient(90deg, #6b73ff, #9f7aea);
    border-radius: 3px 3px 0 0;
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.dash-tab.active::after,
.dash-tab:hover::after {
    transform: translateX(-50%) scaleX(1);
}

/* ──────── Smooth Transitions ──────── */
* {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ──────── Reduce motion for accessibility ──────── */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
"""

css += premium_css
css_path.write_text(css, encoding='utf-8')
print("✨ Ultra-premium CSS effects added!")
