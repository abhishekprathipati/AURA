// ============================================
// AURA ULTRA PRO DASHBOARD - JAVASCRIPT ENGINE
// ============================================

// State Management
const dashboardState = {
    currentStress: 0,
    stressHistory: [],
    theme: localStorage.getItem('aura-theme') || 'dark',
    zenMode: false
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initDateTime();
    initStressGauge();
    initEventListeners();
    loadDashboardData();
    initQuickActions();
    initGrievanceModal();
});

// ============================================
// THEME MANAGEMENT
// ============================================
function initTheme() {
    const theme = dashboardState.theme;
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcons(theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    dashboardState.theme = newTheme;
    localStorage.setItem('aura-theme', newTheme);
    updateThemeIcons(newTheme);
}

function updateThemeIcons(theme) {
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    
    if (theme === 'dark') {
        if (sunIcon) sunIcon.style.display = 'none';
        if (moonIcon) moonIcon.style.display = 'block';
    } else {
        if (sunIcon) sunIcon.style.display = 'block';
        if (moonIcon) moonIcon.style.display = 'none';
    }
}

// ============================================
// DATE/TIME DISPLAY
// ============================================
function initDateTime() {
    updateDateTime();
    setInterval(updateDateTime, 60000); // Update every minute
}

function updateDateTime() {
    const dateTimeEl = document.getElementById('currentDateTime');
    if (!dateTimeEl) return;
    
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    dateTimeEl.textContent = now.toLocaleDateString('en-US', options);
}

// ============================================
// STRESS GAUGE SYSTEM
// ============================================
function initStressGauge() {
    // Fetch real stress level from backend
    fetchStressLevel();
    
    // Update every 30 seconds
    setInterval(fetchStressLevel, 30000);
}

async function fetchStressLevel() {
    try {
        const response = await fetch('/api/student/stress-level');
        const data = await response.json();
        
        if (data.stress_level !== undefined) {
            updateStressGauge(data.stress_level);
            updateStressMetrics(data);
        }
    } catch (error) {
        console.error('Error fetching stress level:', error);
        // Use demo data if API fails
        const demoStress = Math.floor(Math.random() * 100);
        updateStressGauge(demoStress);
    }
}

function updateStressGauge(value) {
    // Clamp value between 0 and 100
    value = Math.max(0, Math.min(100, value));
    
    // Update state
    dashboardState.currentStress = value;
    dashboardState.stressHistory.push({
        value: value,
        timestamp: Date.now()
    });
    
    // Keep only last 20 readings
    if (dashboardState.stressHistory.length > 20) {
        dashboardState.stressHistory.shift();
    }
    
    // Update SVG gauge
    const gaugeFill = document.getElementById('gaugeFill');
    const gaugeValueText = document.getElementById('gaugeValueText');
    
    if (gaugeFill && gaugeValueText) {
        // Calculate stroke-dashoffset (arc is 220 units long)
        const maxOffset = 220;
        const offset = maxOffset - (value / 100) * maxOffset;
        
        // Animate gauge
        gaugeFill.style.strokeDashoffset = offset;
        
        // Animate number
        animateValue(gaugeValueText, parseInt(gaugeValueText.textContent) || 0, value, 1000);
    }
    
    // Update status
    updateGaugeStatus(value);
}

function animateValue(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16); // 60fps
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.round(current);
    }, 16);
}

function updateGaugeStatus(value) {
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    
    if (!statusIndicator || !statusText) return;
    
    let status, color;
    
    if (value < 30) {
        status = 'Excellent - Low Stress';
        color = '#10b981'; // Green
    } else if (value < 60) {
        status = 'Moderate - Stay Balanced';
        color = '#f59e0b'; // Yellow
    } else {
        status = 'High - Take Action';
        color = '#ef4444'; // Red
    }
    
    statusText.textContent = status;
    statusIndicator.style.background = color;
    statusIndicator.style.boxShadow = `0 0 12px ${color}`;
}

function updateStressMetrics(data) {
    // Update peak stress
    const peakEl = document.getElementById('peakStress');
    if (peakEl && data.peak !== undefined) {
        peakEl.textContent = data.peak;
    }
    
    // Update average stress
    const avgEl = document.getElementById('avgStress');
    if (avgEl && data.average !== undefined) {
        avgEl.textContent = data.average;
    }
    
    // Update trend
    const trendEl = document.getElementById('trendIndicator');
    if (trendEl && data.trend !== undefined) {
        const trendIcon = trendEl.querySelector('svg path');
        if (data.trend === 'up') {
            trendEl.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M7 14l5-5 5 5H7z"/></svg> Rising';
            trendEl.style.color = '#ef4444';
        } else if (data.trend === 'down') {
            trendEl.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M7 10l5 5 5-5H7z"/></svg> Falling';
            trendEl.style.color = '#10b981';
        } else {
            trendEl.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M5 12h14"/></svg> Stable';
            trendEl.style.color = '#6b6b84';
        }
    }
}

// ============================================
// DASHBOARD DATA LOADING
// ============================================
async function loadDashboardData() {
    try {
        const response = await fetch('/api/student/dashboard-data');
        const data = await response.json();
        
        // Update mood
        const moodEl = document.getElementById('moodValue');
        if (moodEl && data.mood) {
            moodEl.textContent = data.mood;
        }
        
        // Update AI insights
        const aiEl = document.getElementById('aiInsightValue');
        if (aiEl && data.ai_insight) {
            aiEl.textContent = data.ai_insight;
        }
        
        // Update streak
        const streakEl = document.getElementById('streakValue');
        if (streakEl && data.streak !== undefined) {
            streakEl.textContent = data.streak === 1 ? '1 Day' : `${data.streak} Days`;
        }
        
        // Update activities count
        const activitiesEl = document.getElementById('activitiesCount');
        if (activitiesEl && data.activities_count !== undefined) {
            activitiesEl.textContent = data.activities_count;
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        // Use defaults if API fails
        setDefaultDashboardData();
    }
}

function setDefaultDashboardData() {
    const defaults = {
        mood: 'Calm',
        aiInsight: 'Positive',
        streak: 1,
        activitiesCount: 12
    };
    
    const moodEl = document.getElementById('moodValue');
    if (moodEl) moodEl.textContent = defaults.mood;
    
    const aiEl = document.getElementById('aiInsightValue');
    if (aiEl) aiEl.textContent = defaults.aiInsight;
    
    const streakEl = document.getElementById('streakValue');
    if (streakEl) streakEl.textContent = `${defaults.streak} Day`;
    
    const activitiesEl = document.getElementById('activitiesCount');
    if (activitiesEl) activitiesEl.textContent = defaults.activitiesCount;
}

// ============================================
// EVENT LISTENERS
// ============================================
function initEventListeners() {
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Zen mode toggle
    const zenToggle = document.getElementById('zenToggle');
    if (zenToggle) {
        zenToggle.addEventListener('click', toggleZenMode);
    }
    
    // Navigation tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            const view = e.currentTarget.getAttribute('data-view');
            switchView(view);
        });
    });
}

function toggleZenMode() {
    dashboardState.zenMode = !dashboardState.zenMode;
    document.body.classList.toggle('zen-mode', dashboardState.zenMode);
    
    const zenToggle = document.getElementById('zenToggle');
    if (zenToggle) {
        zenToggle.style.background = dashboardState.zenMode ? 
            'rgba(139, 92, 246, 0.3)' : '';
    }
}

function switchView(view) {
    // Update active tab
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.getAttribute('data-view') === view) {
            tab.classList.add('active');
        }
    });
    
    // Handle view switching (can be expanded)
    console.log('Switching to view:', view);
}

// ============================================
// QUICK ACTIONS
// ============================================
function initQuickActions() {
    document.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const action = e.currentTarget.getAttribute('data-action');
            executeQuickAction(action);
        });
    });
}

function executeQuickAction(action) {
    switch(action) {
        case 'breathing':
            window.location.href = '/student/relax#breathing';
            break;
        case 'break':
            window.location.href = '/student/relax';
            break;
        default:
            console.log('Unknown action:', action);
    }
}

// ============================================
// GRIEVANCE MODAL
// ============================================
function initGrievanceModal() {
    const openBtn = document.getElementById('openGrievanceForm');
    const closeBtn = document.getElementById('closeGrievanceModal');
    const cancelBtn = document.getElementById('cancelGrievance');
    const modal = document.getElementById('grievanceModal');
    const form = document.getElementById('grievanceForm');
    
    if (openBtn && modal) {
        openBtn.addEventListener('click', () => {
            modal.style.display = 'flex';
        });
    }
    
    if (closeBtn && modal) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    if (cancelBtn && modal) {
        cancelBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    // Close on outside click
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    // Handle form submission
    if (form) {
        form.addEventListener('submit', handleGrievanceSubmit);
    }
}

async function handleGrievanceSubmit(e) {
    e.preventDefault();
    
    const subjectEl = document.getElementById('grievanceSubject');
    const descriptionEl = document.getElementById('grievanceDescription');
    const submitBtn = e.target.querySelector('.btn-primary');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    
    const subject = subjectEl.value.trim();
    const description = descriptionEl.value.trim();
    
    if (!subject || !description) {
        alert('Please fill in all fields');
        return;
    }
    
    // Show loading state
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline-block';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/student/grievance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                subject: subject,
                description: description
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Grievance submitted successfully!');
            subjectEl.value = '';
            descriptionEl.value = '';
            document.getElementById('grievanceModal').style.display = 'none';
        } else {
            alert(data.error || 'Failed to submit grievance');
        }
    } catch (error) {
        console.error('Error submitting grievance:', error);
        alert('An error occurred. Please try again.');
    } finally {
        // Reset button state
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
        submitBtn.disabled = false;
    }
}

// ============================================
// BENTO CARD INTERACTIONS
// ============================================
document.querySelectorAll('.bento-card').forEach(card => {
    card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-4px) scale(1.02)';
    });
    
    card.addEventListener('mouseleave', () => {
        card.style.transform = '';
    });
});

// ============================================
// UTILITY FUNCTIONS
// ============================================
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 32px;
        padding: 16px 24px;
        background: rgba(139, 92, 246, 0.95);
        color: white;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        z-index: 3000;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K: Toggle theme
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleTheme();
    }
    
    // Ctrl/Cmd + Z: Toggle zen mode
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        toggleZenMode();
    }
    
    // Escape: Close modal
    if (e.key === 'Escape') {
        const modal = document.getElementById('grievanceModal');
        if (modal && modal.style.display === 'flex') {
            modal.style.display = 'none';
        }
    }
});

console.log('🧠 AURA Ultra Pro Dashboard Initialized');
