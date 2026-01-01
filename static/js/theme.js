// Theme switching with localStorage persistence
const THEME_KEY = 'aura-theme';

const moodToTheme = {
    happy: 'happy',
    stressed: 'stressed',
    sad: 'sad',
    anxious: 'anxious',
    calm: 'calm',
};

function applyTheme(theme) {
    // Prefer the chromotherapy engine if available
    if (typeof window.applyAuraTheme === 'function') {
        window.applyAuraTheme(theme);
    } else {
        const body = document.body;
        const toRemove = [];
        body.classList.forEach(cls => { if (cls.startsWith('theme-')) toRemove.push(cls); });
        toRemove.forEach(cls => body.classList.remove(cls));
        body.classList.add(`theme-${theme}`);
        localStorage.setItem(THEME_KEY, theme);
        // Contrast Guard: auto-flip text color if accent is light
        setTimeout(() => {
            const accent = getComputedStyle(document.documentElement).getPropertyValue('--theme-accent').trim();
            if (accent) {
                // Convert hex to RGB and check brightness
                let rgb = accent.startsWith('#') ? hexToRgb(accent) : null;
                if (rgb) {
                    const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
                    document.querySelectorAll('.glass-card, .pill-btn, .btn').forEach(el => {
                        if (brightness > 200) {
                            el.classList.add('contrast-guard');
                        } else {
                            el.classList.remove('contrast-guard');
                        }
                    });
                }
            }
        }, 50);
    }
}

function hexToRgb(hex) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.split('').map(x => x + x).join('');
    const num = parseInt(hex, 16);
    return {
        r: (num >> 16) & 255,
        g: (num >> 8) & 255,
        b: num & 255
    };
}

function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || 'calm';
    applyTheme(saved);
}

function setMood(mood) {
    const theme = moodToTheme[mood] || 'calm';
    applyTheme(theme);
    const moodButtons = document.querySelectorAll('[data-mood-btn]');
    moodButtons.forEach(btn => {
        if (btn.dataset.mood === mood) btn.classList.add('active');
        else btn.classList.remove('active');
    });
}

// Attach handlers after DOM load
window.addEventListener('DOMContentLoaded', () => {
    initTheme();
});

// Expose globally if needed
window.applyTheme = applyTheme;
window.setMood = setMood;

