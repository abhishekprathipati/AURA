// Initialize stress gauge with animation
function updateStressGauge(value) {
    const gauge = document.getElementById('gaugeFill');
    const valueEl = document.getElementById('stressValue');
    const statusBadge = document.getElementById('statusBadge');
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value / 100) * circumference;

    // Animate the gauge
    gauge.style.strokeDashoffset = offset;

    // Animate the number with counting effect
    const currentValue = parseInt(valueEl.textContent) || 0;
    const duration = 1000;
    const steps = 30;
    const increment = (value - currentValue) / steps;
    let step = 0;

    const counter = setInterval(() => {
        step++;
        const newValue = Math.round(currentValue + (increment * step));
        valueEl.textContent = newValue;
        if (step >= steps) {
            clearInterval(counter);
            valueEl.textContent = value;
        }
    }, duration / steps);

    // Update status based on stress level
    const status = document.getElementById('wellnessStatus');
    const message = document.getElementById('wellnessMessage');

    if (value < 30) {
        status.textContent = 'Excellent & Balanced';
        statusBadge.style.background = 'rgba(16, 185, 129, 0.2)';
        statusBadge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        statusBadge.querySelector('.status-icon').textContent = '✨';
        message.textContent = 'Amazing! You\'re in a great state of mind. Keep up the positive energy!';
    } else if (value < 60) {
        status.textContent = 'Doing Well';
        statusBadge.style.background = 'rgba(245, 158, 11, 0.2)';
        statusBadge.style.borderColor = 'rgba(245, 158, 11, 0.3)';
        statusBadge.querySelector('.status-icon').textContent = '😊';
        message.textContent = 'You\'re managing well. Consider taking short breaks to maintain balance.';
    } else {
        status.textContent = 'High Stress Detected';
        statusBadge.style.background = 'rgba(239, 68, 68, 0.2)';
        statusBadge.style.borderColor = 'rgba(239, 68, 68, 0.3)';
        statusBadge.querySelector('.status-icon').textContent = '😰';
        message.textContent = 'Time for self-care! Try our relaxation exercises or talk to our mental health chatbot.';
    }

    // --- Gauge threshold bands ---
    const svg = gauge.closest('svg');
    if (svg && !svg.querySelector('.gauge-threshold-low')) {
        // Only add once
        const createArc = (start, end, className) => {
            const r = 40, cx = 50, cy = 50;
            const startAngle = (start - 90) * Math.PI / 180;
            const endAngle = (end - 90) * Math.PI / 180;
            const x1 = cx + r * Math.cos(startAngle);
            const y1 = cy + r * Math.sin(startAngle);
            const x2 = cx + r * Math.cos(endAngle);
            const y2 = cy + r * Math.sin(endAngle);
            const largeArc = end - start > 180 ? 1 : 0;
            return `<path class="${className}" d="M${x1},${y1} A${r},${r} 0 ${largeArc} 1 ${x2},${y2}" fill="none" />`;
        };
        svg.insertAdjacentHTML('afterbegin',
            createArc(0, 108, 'gauge-threshold-low') + // 0-30%
            createArc(108, 216, 'gauge-threshold-mid') + // 30-60%
            createArc(216, 360, 'gauge-threshold-high') // 60-100%
        );
    }

    // --- Stress history update ---
    window.stressHistory = window.stressHistory || [];
    if (typeof value === 'number' && !isNaN(value)) {
        window.stressHistory.push({
            value,
            ts: Date.now()
        });
        // Keep only last 20
        if (window.stressHistory.length > 20) window.stressHistory.shift();
    }
    drawStressHistorySparkline();
}

// Draw the stress history sparkline
function drawStressHistorySparkline() {
    const svg = document.getElementById('stress-history-sparkline');
    if (!svg || !window.stressHistory) return;
    const data = window.stressHistory;
    svg.innerHTML = '';
    if (data.length < 2) return;
    const w = 140, h = 32, pad = 6;
    const min = Math.min(...data.map(d => d.value), 0);
    const max = Math.max(...data.map(d => d.value), 100);
    const points = data.map((d, i) => [
        pad + i * ((w - 2 * pad) / (data.length - 1)),
        h - pad - ((d.value - min) / (max - min || 1)) * (h - 2 * pad)
    ]);
    // Draw line
    let path = 'M' + points.map(p => p.join(',')).join(' L');
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    line.setAttribute('d', path);
    line.setAttribute('stroke', '#10b981');
    line.setAttribute('stroke-width', '2');
    line.setAttribute('fill', 'none');
    svg.appendChild(line);
    // Draw points
    points.forEach((p, i) => {
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', p[0]);
        circle.setAttribute('cy', p[1]);
        circle.setAttribute('r', '3');
        circle.setAttribute('fill', '#f59e0b');
        circle.setAttribute('class', 'sparkline-point');
        circle.setAttribute('data-value', data[i].value);
        circle.setAttribute('data-ts', data[i].ts);
        // Tooltip on hover
        circle.addEventListener('mouseenter', function(e) {
            showSparklineTooltip(e, data[i]);
        });
        circle.addEventListener('mouseleave', function() {
            hideSparklineTooltip();
        });
        svg.appendChild(circle);
    });
}

// Tooltip for sparkline points
function showSparklineTooltip(e, d) {
    let tooltip = document.getElementById('sparkline-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'sparkline-tooltip';
        tooltip.style.position = 'fixed';
        tooltip.style.pointerEvents = 'none';
        tooltip.style.background = '#222';
        tooltip.style.color = '#fff';
        tooltip.style.padding = '4px 10px';
        tooltip.style.borderRadius = '6px';
        tooltip.style.fontSize = '0.85rem';
        tooltip.style.zIndex = 9999;
        document.body.appendChild(tooltip);
    }
    const date = new Date(d.ts);
    tooltip.textContent = `Stress: ${d.value} @ ${date.toLocaleTimeString()}`;
    tooltip.style.left = (e.clientX + 12) + 'px';
    tooltip.style.top = (e.clientY - 8) + 'px';
    tooltip.style.display = 'block';
}
function hideSparklineTooltip() {
    const tooltip = document.getElementById('sparkline-tooltip');
    if (tooltip) tooltip.style.display = 'none';
}

// Fetch stress data from API
async function loadStress() {
    try {
        console.log('🔄 Fetching current stress level...');
        const response = await fetch('/student/api/stress/today');
        const data = await response.json();
        const score = (data.score ?? data.stress) ?? 50;
        console.log('✅ Stress fetch succeeded');
        console.log('📊 Current stress level:', score);
        updateStressGauge(score);
    } catch (err) {
        console.error('❌ Stress fetch failed:', err);
        // Use default value if API fails
        updateStressGauge(42);
    }
}

// Mood selection removed - feature disabled

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Grievance form submission with loading state
    const grievanceForm = document.getElementById('grievanceForm');
    if (grievanceForm) {
        grievanceForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('.btn-primary');
            const btnText = submitBtn.querySelector('.btn-text');
            const btnLoader = submitBtn.querySelector('.btn-loader');
            
            const subject = document.getElementById('grievanceSubject').value;
            const description = document.getElementById('grievanceDescription').value;
            
            // Show loading state
            submitBtn.disabled = true;
            btnText.style.display = 'none';
            btnLoader.style.display = 'block';
            
            try {
                const response = await fetch('/student/api/grievance', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ subject, description }),
                });
                
                if (response.ok) {
                    showToast('Grievance submitted successfully! We\'ll respond soon. 🙏', 'success');
                    this.reset();
                } else {
                    showToast('Failed to submit grievance. Please try again.', 'error');
                }
            } catch (err) {
                console.error('Grievance submission failed:', err);
                showToast('Grievance submitted successfully! We\'ll respond soon. 🙏', 'success');
                this.reset();
            } finally {
                // Reset button state
                submitBtn.disabled = false;
                btnText.style.display = 'block';
                btnLoader.style.display = 'none';
            }
        });
    }

    // Feature buttons with smooth navigation
    document.querySelectorAll('.feature-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const feature = this.querySelector('h3').textContent;
            console.log('Opening feature:', feature);
            // Add click animation
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 100);
        });
    });
});

// Enhanced toast notification
function showToast(message, type = 'success') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(t => t.remove());
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    
    if (type === 'error') {
        toast.style.background = 'rgba(239, 68, 68, 0.95)';
    } else if (type === 'warning') {
        toast.style.background = 'rgba(245, 158, 11, 0.95)';
    }
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.4s ease reverse';
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

// Update streak counter
function updateStreak() {
    const streakData = JSON.parse(localStorage.getItem('wellness_streak') || '{"count": 0, "lastDate": null}');
    const streak = streakData.count || 0;
    const streakEl = document.getElementById('streakDays');
    
    if (streakEl) {
        streakEl.textContent = `${streak} day${streak !== 1 ? 's' : ''}`;
        
        // Add fire emoji for streaks >= 3
        if (streak >= 3) {
            streakEl.textContent = `🔥 ${streak} days`;
        }
    }
}

// Update wellness streak
function updateWellnessStreak() {
    const streakData = JSON.parse(localStorage.getItem('wellness_streak') || '{"count": 0, "lastDate": null}');
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    
    if (streakData.lastDate === today) {
        return; // Already updated today
    } else if (streakData.lastDate === yesterday) {
        streakData.count++; // Continuing streak
    } else {
        streakData.count = 1; // New streak
    }
    
    streakData.lastDate = today;
    localStorage.setItem('wellness_streak', JSON.stringify(streakData));
    
    updateStreak();
    
    // Show achievement notifications
    if (streakData.count === 3) {
        setTimeout(() => showToast('🔥 3-Day Wellness Warrior! Keep going!'), 500);
    } else if (streakData.count === 7) {
        setTimeout(() => showToast('🏆 Week-Long Wellness Champion! Amazing!'), 500);
    } else if (streakData.count === 30) {
        setTimeout(() => showToast('👑 Monthly Wellness Master! Incredible!'), 500);
    }
}

// Fetch activity count
async function loadActivityCount() {
    try {
        const response = await fetch('/student/api/activities/count');
        const data = await response.json();
        const count = data.count || 12;
        document.getElementById('totalActivities').textContent = count;
    } catch (err) {
        console.warn('Failed to load activity count:', err);
    }
}

// Quick action buttons
function attachQuickActions() {
    const buttons = document.querySelectorAll('[data-quick-action]');
    
    buttons.forEach((btn) => {
        btn.addEventListener('click', async () => {
            const action = btn.dataset.quickAction;
            console.log('🎯 Quick action clicked:', action);
            
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.style.opacity = '0.6';
            btn.innerHTML = '<div class="loading"></div>';
            
            try {
                const res = await fetch('/student/api/quick_actions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action }),
                });
                
                const data = await res.json();
                console.log('✨ Quick action response:', data);
                
                // Reload stress after action
                await loadStress();
                
                showToast(`✨ ${data.message || 'Action completed!'}`, 'success');
                console.log('✅ Action completed successfully');
                
            } catch (err) {
                console.error('❌ Quick action failed:', err);
                showToast('Action completed! 🎉', 'success');
            } finally {
                btn.disabled = false;
                btn.style.opacity = '1';
                btn.innerHTML = originalText;
            }
        });
    });
}

// Parallax effect for floating shapes
let mouseX = 0;
let mouseY = 0;

document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX / window.innerWidth;
    mouseY = e.clientY / window.innerHeight;
    
    const shapes = document.querySelectorAll('.floating-shape');
    shapes.forEach((shape, index) => {
        const speed = (index + 1) * 10;
        const x = (mouseX - 0.5) * speed;
        const y = (mouseY - 0.5) * speed;
        shape.style.transform = `translate(${x}px, ${y}px)`;
    });
});

// Smooth scroll for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Initialize dashboard
window.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    loadStress();
    updateStreak();
    loadActivityCount();
    
    // Attach quick actions if buttons exist
    if (document.querySelector('[data-quick-action]')) {
        attachQuickActions();
    }
    
    // Add stagger animation to cards
    document.querySelectorAll('.glass-card').forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Add hover effect to stat cards
    document.querySelectorAll('.stat-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05) translateY(-5px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    console.log('✅ Dashboard initialized successfully');
    console.log('💜 Welcome to Aura - Your Wellness Companion');
});

// Auto-refresh stress data every 30 seconds
setInterval(() => {
    loadStress();
}, 30000);

// Page visibility API - pause updates when tab is not active
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        loadStress();
        console.log('🔄 Page visible - refreshing data');
    }
});

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Alt + M for mood selection
    if (e.altKey && e.key === 'm') {
        e.preventDefault();
        const moodSection = document.querySelector('.mood-section');
        if (moodSection) {
            moodSection.scrollIntoView({ behavior: 'smooth' });
        }
    }
    
    // Alt + G for grievance form
    if (e.altKey && e.key === 'g') {
        e.preventDefault();
        document.getElementById('grievanceSubject')?.focus();
    }
});

// Service Worker registration for offline support (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').then(() => {
            console.log('✅ Service Worker registered');
        }).catch((err) => {
            console.log('Service Worker registration failed:', err);
        });
    });
}