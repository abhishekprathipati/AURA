// Mood Handler - Dynamic UI Theme Switcher for AURA

/**
 * Updates the user's mood and applies the corresponding theme
 * @param {string} mood - e.g. 'happy', 'stressed', 'anxious', 'calm', 'sad'
 */
async function updateMood(mood) {
    try {
        // Send mood to backend
        const response = await fetch('/student/api/mood', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mood: mood })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        
        // Store theme in localStorage for persistence
        localStorage.setItem('aura_theme', mood);
        
        // Apply theme immediately
        applyAuraTheme(mood);
        
        // Update wellness streak
        if (window.updateWellnessStreak) {
            window.updateWellnessStreak();
        }
        
        // Hide modal
        const modal = document.getElementById('moodModal');
        if (modal) modal.style.display = 'none';
        
        // No redirect: stay on dashboard for all moods
        
    } catch (error) {
        console.error('Mood update failed:', error);
        alert('Unable to update mood. Please try again.');
    }
}

/**
 * Applies the theme by updating the body class
 * @param {string} mood - 'happy', 'stressed', 'anxious', 'calm', 'sad', 'angry'
 */
function applyAuraTheme(mood) {
    const body = document.body;
    // Remove any class starting with 'theme-'
    const toRemove = [];
    body.classList.forEach(cls => { if (cls.startsWith('theme-')) toRemove.push(cls); });
    toRemove.forEach(cls => body.classList.remove(cls));
    // Add new theme class
    body.classList.add(`theme-${mood}`);

    // Trigger breathing animation
    body.classList.add('theme-transitioning');
    setTimeout(() => body.classList.remove('theme-transitioning'), 600);

    // Haptic feedback for mobile devices
    if (navigator.vibrate) {
        // Different vibration patterns based on mood
        const vibrationPatterns = {
            happy: [50, 50, 50],
            calm: [100],
            stressed: [30, 30, 30, 30],
            anxious: [20, 20, 20, 20, 20],
            angry: [100, 50, 100],
            sad: [150]
        };
        navigator.vibrate(vibrationPatterns[mood] || [50]);
    }

    // Persist for reloads
    localStorage.setItem('aura_theme', mood);

    // Mark active mood card
    document.querySelectorAll('.mood-card').forEach(card => {
        card.classList.remove('active-mood-card');
    });
    const activeCard = Array.from(document.querySelectorAll('.mood-card')).find(card => {
        const text = card.querySelector('h3')?.textContent?.toLowerCase();
        return text === mood;
    });
    if (activeCard) activeCard.classList.add('active-mood-card');

    // Notify other widgets (e.g., charts) of accent change
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--aura-accent').trim();
    const evt = new CustomEvent('aura-theme-change', { detail: { mood: mood, accent } });
    window.dispatchEvent(evt);
}

/**
 * Checks if user has set mood today and shows modal if not
 */
async function checkDailyMood() {
    try {
        const response = await fetch('/student/api/mood/today');
        const data = await response.json();
        
        if (!data.has_mood_today) {
            // Show modal
            const modal = document.getElementById('moodModal');
            if (modal) modal.style.display = 'flex';
        } else if (data.mood) {
            // Apply saved mood theme
            applyAuraTheme(data.mood);
        }
    } catch (error) {
        console.error('Failed to check daily mood:', error);
    }
}

/**
 * Initialize theme on page load
 */
window.addEventListener('DOMContentLoaded', () => {
    // Check for saved theme in localStorage
    const savedTheme = localStorage.getItem('aura_theme');
    
    if (savedTheme) {
        applyAuraTheme(savedTheme);
    }
    
    // Check if on student dashboard
    if (window.location.pathname.includes('/dashboard')) {
        checkDailyMood();
    }

    // Enable keyboard navigation for mood cards
    document.querySelectorAll('.mood-card').forEach(card => {
        card.setAttribute('tabindex', '0'); // Make focusable
        card.setAttribute('role', 'button'); // Semantic role
        card.setAttribute('aria-label', `Select ${card.querySelector('h3')?.textContent} mood`);
        
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.click(); // Trigger the existing theme logic
            }
        });
    });
});

// Expose globally for inline onclick handlers
window.updateMood = updateMood;
window.applyAuraTheme = applyAuraTheme;
// backward compatibility
window.applyTheme = applyAuraTheme;
