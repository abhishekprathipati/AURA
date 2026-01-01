// AURA Smart Quick Actions - Contextual AI-Driven Suggestions
let smartActionsEnabled = true;
let lastStressCheck = 0;

/**
 * Initialize smart actions system
 */
function initSmartActions() {
    // Check stress levels periodically
    setInterval(checkStressLevels, 60000); // Every minute
    
    // Check time-based suggestions
    updateTimeBasedSuggestions();
    setInterval(updateTimeBasedSuggestions, 300000); // Every 5 minutes
    
    // Monitor user activity
    monitorUserActivity();
}

/**
 * Check current stress levels and trigger interventions
 */
async function checkStressLevels() {
    try {
        const response = await fetch('/student/api/stress/today');
        const data = await response.json();
        const stress = data.score || 50;
        
        // High stress intervention (>80)
        if (stress > 80 && Date.now() - lastStressCheck > 1800000) { // 30 min cooldown
            lastStressCheck = Date.now();
            showStressIntervention(stress);
        }
        
        // Medium stress suggestion (60-80)
        else if (stress > 60 && Math.random() > 0.7) {
            showStressSuggestion(stress);
        }
    } catch (err) {
        console.warn('Smart actions: stress check failed', err);
    }
}

/**
 * Show stress intervention popup
 */
function showStressIntervention(stressLevel) {
    const popup = document.createElement('div');
    popup.className = 'smart-intervention-popup';
    popup.innerHTML = `
        <div class="intervention-content">
            <div class="intervention-icon">⚠️</div>
            <h3>High Stress Detected</h3>
            <p>Your stress level is at ${stressLevel}/100. Taking a short break can help.</p>
            <div class="intervention-actions">
                <button class="intervention-btn primary" onclick="navigateToRelax()">
                    🧘 Take 2-Min Break
                </button>
                <button class="intervention-btn secondary" onclick="dismissIntervention()">
                    Later
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(popup);
    
    // Haptic feedback
    if (navigator.vibrate) {
        navigator.vibrate([100, 50, 100, 50, 100]);
    }
    
    // Auto-dismiss after 15 seconds
    setTimeout(() => {
        if (popup.parentNode) {
            popup.classList.add('fade-out');
            setTimeout(() => popup.remove(), 300);
        }
    }, 15000);
}

/**
 * Navigate to relaxation zone
 */
function navigateToRelax() {
    // Log intervention acceptance
    logSmartAction('stress_intervention_accepted');
    window.location.href = '/student/relax';
}

/**
 * Dismiss intervention popup
 */
function dismissIntervention() {
    const popup = document.querySelector('.smart-intervention-popup');
    if (popup) {
        popup.classList.add('fade-out');
        setTimeout(() => popup.remove(), 300);
    }
    logSmartAction('stress_intervention_dismissed');
}

/**
 * Show gentle stress suggestion
 */
function showStressSuggestion(stressLevel) {
    showToast(`💙 Stress at ${stressLevel}/100. Consider a quick breathing exercise?`, 8000);
}

/**
 * Update quick action buttons based on time of day
 */
function updateTimeBasedSuggestions() {
    const hour = new Date().getHours();
    const quickActionsContainer = document.querySelector('.quick-actions-container');
    
    if (!quickActionsContainer) return;
    
    // Late night (10 PM - 5 AM): Sleep hygiene
    if (hour >= 22 || hour < 5) {
        updateQuickAction('study', {
            text: 'Sleep Hygiene Tips 😴',
            action: 'sleep_hygiene',
            icon: '🌙'
        });
    }
    
    // Early morning (5 AM - 9 AM): Morning routine
    else if (hour >= 5 && hour < 9) {
        updateQuickAction('mood_check', {
            text: 'Morning Motivation ☀️',
            action: 'morning_motivation',
            icon: '🌅'
        });
    }
    
    // Afternoon (2 PM - 4 PM): Energy boost
    else if (hour >= 14 && hour < 16) {
        updateQuickAction('stretch', {
            text: 'Energy Boost 🔋',
            action: 'energy_boost',
            icon: '⚡'
        });
    }
    
    // Evening (6 PM - 10 PM): Wind down
    else if (hour >= 18 && hour < 22) {
        updateQuickAction('breathing', {
            text: 'Wind Down Routine 🌆',
            action: 'wind_down',
            icon: '🌇'
        });
    }
}

/**
 * Update a specific quick action button
 */
function updateQuickAction(oldAction, newConfig) {
    const btn = document.querySelector(`[data-quick-action="${oldAction}"]`);
    if (!btn) return;
    
    btn.innerHTML = `${newConfig.icon} ${newConfig.text}`;
    btn.dataset.quickAction = newConfig.action;
    btn.classList.add('smart-suggestion');
    
    // Add pulsing animation
    btn.style.animation = 'smartPulse 2s ease-in-out infinite';
}

/**
 * Monitor user activity and provide contextual help
 */
function monitorUserActivity() {
    let idleTime = 0;
    let lastActivity = Date.now();
    
    // Reset idle timer on any activity
    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
        document.addEventListener(event, () => {
            idleTime = 0;
            lastActivity = Date.now();
        }, true);
    });
    
    // Check idle time every 30 seconds
    setInterval(() => {
        idleTime += 30;
        
        // If idle for 5 minutes on dashboard
        if (idleTime >= 300 && window.location.pathname.includes('/dashboard')) {
            showIdleSuggestion();
            idleTime = 0; // Reset to avoid repeated suggestions
        }
    }, 30000);
}

/**
 * Show suggestion when user is idle
 */
function showIdleSuggestion() {
    const suggestions = [
        { text: 'Take a mindful moment?', action: 'relax', icon: '🧘' },
        { text: 'Log how you\'re feeling?', action: 'mood', icon: '📝' },
        { text: 'Need study help?', action: 'study', icon: '📚' }
    ];
    
    const suggestion = suggestions[Math.floor(Math.random() * suggestions.length)];
    
    const toast = document.createElement('div');
    toast.className = 'smart-toast';
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">${suggestion.icon}</span>
            <span class="toast-text">${suggestion.text}</span>
            <button class="toast-btn" onclick="handleIdleSuggestion('${suggestion.action}')">
                Go
            </button>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
                ✕
            </button>
        </div>
    `;
    
    document.body.appendChild(toast);
    setTimeout(() => {
        if (toast.parentNode) toast.remove();
    }, 10000);
}

/**
 * Handle idle suggestion action
 */
function handleIdleSuggestion(action) {
    document.querySelector('.smart-toast')?.remove();
    
    const routes = {
        'relax': '/student/relax',
        'mood': '/student/dashboard',
        'study': '/student/chat/study'
    };
    
    if (routes[action]) {
        window.location.href = routes[action];
    }
}

/**
 * Log smart action for analytics
 */
function logSmartAction(action) {
    try {
        fetch('/student/api/smart_action_log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action,
                timestamp: new Date().toISOString()
            })
        }).catch(() => {}); // Silent fail
    } catch (err) {
        // Ignore logging errors
    }
}

/**
 * Show toast notification
 */
function showToast(message, duration = 5000) {
    const toast = document.createElement('div');
    toast.className = 'smart-toast simple';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.85);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 10000;
        animation: slideInUp 0.3s ease;
        max-width: 350px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;
    
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideOutDown 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSmartActions);
} else {
    initSmartActions();
}

// Export functions for global use
window.navigateToRelax = navigateToRelax;
window.dismissIntervention = dismissIntervention;
window.handleIdleSuggestion = handleIdleSuggestion;
