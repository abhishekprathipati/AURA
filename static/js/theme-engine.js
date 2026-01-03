// ============================================
// AURA THEME ENGINE - Light & Dark Mode
// ============================================

const THEME_KEY = 'aura-ui-theme';
const SYSTEM_THEME_KEY = 'aura-system-theme';

// SVG Icon Paths
const SUN_SVG_PATH = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20" aria-hidden="true">
  <circle cx="12" cy="12" r="5"/>
  <path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m2.97 2.97l4.24 4.24M1 12h6m6 0h6M4.22 19.78l4.24-4.24m2.97-2.97l4.24-4.24M19.78 19.78l-4.24-4.24m-2.97-2.97l-4.24-4.24"/>
</svg>`;

const MOON_SVG_PATH = `<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20" aria-hidden="true">
  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
</svg>`;

// Initialize theme system
function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  // Default to dark theme if no preference saved
  const theme = saved || 'dark';
  
  applyTheme(theme);
  setupThemeToggle();
  setupAutoTheme();
}

// Get system preference (light/dark)
function getSystemTheme() {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

// Apply theme to document
function applyTheme(theme) {
  // Validate theme
  if (theme !== 'light' && theme !== 'dark') {
    theme = 'light';
  }
  
  // Set on root element
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  
  // Update toggle button icon if it exists
  updateThemeIcon(theme);
  
  // Emit custom event for other components
  window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
}

// Update the theme toggle icon
function updateThemeIcon(theme) {
  const themeToggle = document.getElementById('theme-toggle');
  if (!themeToggle) return;
  
  const icon = themeToggle.querySelector('.theme-icon');
  if (!icon) return;
  
  icon.innerHTML = theme === 'light' ? MOON_SVG_PATH : SUN_SVG_PATH;
}

// Setup theme toggle button listener
function setupThemeToggle() {
  const themeToggle = document.getElementById('theme-toggle');
  if (!themeToggle) return;
  
  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';
    applyTheme(next);
  });
}

// Listen to system theme changes
function setupAutoTheme() {
  if (!window.matchMedia) return;
  
  const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
  
  // Modern browsers
  if (darkModeQuery.addEventListener) {
    darkModeQuery.addEventListener('change', (e) => {
      // Only auto-switch if user hasn't manually set a preference
      const saved = localStorage.getItem(THEME_KEY);
      if (!saved) {
        applyTheme(e.matches ? 'dark' : 'light');
      }
    });
  }
}

// Expose globally for external use
window.AURA_Theme = {
  init: initTheme,
  apply: applyTheme,
  get current() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  },
  set(theme) {
    applyTheme(theme);
  },
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTheme);
} else {
  initTheme();
}
