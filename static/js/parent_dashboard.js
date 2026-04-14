// Parent Dashboard JavaScript
(function () {
'use strict';

let currentAnnouncementFilter = 'all';
let stressChart, moodChart, academicTrendChart;

/* ── XSS helper ─────────────────────────────────────────── */
function esc(str) {
    if (str == null) return '';
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(String(str)));
    return d.innerHTML;
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadAcademicPerformance();
    loadWellnessSummary();
    loadComplaints();
    loadAnnouncements();
    loadActivityLog();
    loadNotifications();
    bindForms();

    // CSP-compliant event wiring for nav
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', window.logout);

    const bellBtn = document.getElementById('notifBellBtn');
    if (bellBtn) bellBtn.addEventListener('click', window.toggleNotifications);

    const closeBtn = document.getElementById('notifCloseBtn');
    if (closeBtn) closeBtn.addEventListener('click', window.toggleNotifications);

    // Announcement tab delegation
    const tabsContainer = document.getElementById('announcementTabs');
    if (tabsContainer) {
        tabsContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('.tab');
            if (!btn) return;
            const filter = btn.dataset.filter || 'all';
            tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            window.switchAnnouncement(filter, null);
        });
    }

    // Auto-refresh every 5 minutes
    setInterval(() => {
        loadWellnessSummary();
        loadActivityLog();
        loadNotifications();
    }, 300000);
});

// Logout function
window.logout = function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/parent/logout';
    }
};

// Load academic performance data
async function loadAcademicPerformance() {
    try {
        const response = await fetch('/parent/api/student/academics');
        if (!response.ok) throw new Error('Failed to load academic data');
        
        const result = await response.json();
        
        if (!result.success || !result.data.summary) {
            console.log('No academic data available');
            return;
        }
        
        const { summary, records } = result.data;
        
        // Update semester badge
        const semEl = document.getElementById('currentSemester');
        if (semEl) semEl.textContent = summary.current_semester || '—';
        
        // Update metric cards
        const cgpaEl = document.getElementById('metricCgpa');
        const sgpaEl = document.getElementById('metricSgpa');
        const attEl = document.getElementById('metricAttendance');
        const creditsEl = document.getElementById('metricCredits');
        
        if (cgpaEl) cgpaEl.textContent = summary.current_cgpa ? summary.current_cgpa.toFixed(2) : '—';
        if (sgpaEl) sgpaEl.textContent = summary.current_sgpa ? summary.current_sgpa.toFixed(2) : '—';
        if (attEl) attEl.textContent = summary.attendance ? `${summary.attendance.toFixed(1)}%` : '—';
        if (creditsEl) creditsEl.textContent = summary.credits_earned && summary.total_credits 
            ? `${summary.credits_earned}/${summary.total_credits}` 
            : '—';
        
        // Render trend chart if we have semester records
        if (records && records.length > 0) {
            renderAcademicTrendChart(records);
        }
        
    } catch (error) {
        console.error('Error loading academic performance:', error);
        const cgpaEl = document.getElementById('metricCgpa');
        if (cgpaEl) cgpaEl.textContent = 'Error';
        const sgpaEl = document.getElementById('metricSgpa');
        if (sgpaEl) sgpaEl.textContent = 'Error';
        const attEl = document.getElementById('metricAttendance');
        if (attEl) attEl.textContent = 'Error';
        const creditsEl = document.getElementById('metricCredits');
        if (creditsEl) creditsEl.textContent = 'Error';
    }
}

// Render academic trend chart
function renderAcademicTrendChart(records) {
    const chartEl = document.getElementById('academicTrendChart');
    if (!chartEl || records.length === 0) return;
    
    const options = {
        series: [
            {
                name: 'CGPA',
                data: records.map(r => r.cgpa || 0)
            },
            {
                name: 'SGPA',
                data: records.map(r => r.sgpa || 0)
            },
            {
                name: 'Attendance %',
                data: records.map(r => r.attendance || 0)
            }
        ],
        chart: {
            type: 'line',
            height: 260,
            fontFamily: 'Inter, sans-serif',
            toolbar: { show: false },
            background: 'transparent',
            animations: {
                enabled: true,
                easing: 'easeinout',
                speed: 600
            }
        },
        colors: ['#667eea', '#8b5cf6', '#10b981'],
        stroke: {
            curve: 'smooth',
            width: [3, 3, 2]
        },
        fill: {
            type: 'gradient',
            gradient: {
                shade: 'light',
                type: 'vertical',
                shadeIntensity: 0.3,
                opacityFrom: 0.7,
                opacityTo: 0.2
            }
        },
        dataLabels: {
            enabled: false
        },
        markers: {
            size: 5,
            hover: {
                size: 7
            }
        },
        xaxis: {
            categories: records.map(r => r.semester || ''),
            labels: {
                style: {
                    colors: '#6b7280',
                    fontSize: '12px',
                    fontWeight: 600
                }
            },
            axisBorder: { show: false },
            axisTicks: { show: false }
        },
        yaxis: [
            {
                seriesName: 'CGPA',
                min: 5,
                max: 10,
                tickAmount: 5,
                labels: {
                    style: {
                        colors: '#667eea',
                        fontSize: '11px',
                        fontWeight: 600
                    },
                    formatter: val => val.toFixed(1)
                }
            },
            {
                seriesName: 'CGPA',
                show: false,
                min: 5,
                max: 10
            },
            {
                seriesName: 'Attendance %',
                opposite: true,
                min: 0,
                max: 100,
                tickAmount: 5,
                labels: {
                    style: {
                        colors: '#10b981',
                        fontSize: '11px',
                        fontWeight: 600
                    },
                    formatter: val => val.toFixed(0) + '%'
                }
            }
        ],
        grid: {
            borderColor: '#f1f5f9',
            strokeDashArray: 3,
            xaxis: { lines: { show: false } },
            yaxis: { lines: { show: true } }
        },
        legend: {
            position: 'top',
            horizontalAlign: 'right',
            fontSize: '13px',
            fontWeight: 600,
            markers: {
                width: 12,
                height: 12,
                radius: 3
            },
            itemMargin: {
                horizontal: 12
            }
        },
        tooltip: {
            shared: true,
            intersect: false,
            y: {
                formatter: (val, opts) => {
                    const seriesIndex = opts.seriesIndex;
                    if (seriesIndex === 2) return val.toFixed(1) + '%';
                    return val.toFixed(2);
                }
            }
        }
    };
    
    if (academicTrendChart) {
        academicTrendChart.destroy();
    }
    
    academicTrendChart = new ApexCharts(chartEl, options);
    academicTrendChart.render();
}


// Load comprehensive wellness summary
async function loadWellnessSummary() {
    try {
        const response = await fetch('/parent/api/student/wellness-summary');
        if (!response.ok) throw new Error('Failed to load wellness summary');
        
        const data = await response.json();
        
        // Update wellness status badge
        const statusEl = document.getElementById('wellnessStatus');
        if (statusEl) {
            const statusMap = {
                'good':             { label: '✅ Good',             cls: '' },
                'moderate':         { label: '⚠️ Moderate',         cls: 'moderate' },
                'needs_attention':  { label: '🚨 Needs Attention',  cls: 'needs-attention' }
            };
            const mapped = statusMap[data.wellness_status] || { label: 'Unknown', cls: '' };
            statusEl.textContent = mapped.label;
            statusEl.className = 'wellness-status-badge ' + mapped.cls;
        }
        
        // Update stress average
        const stressAvgEl = document.getElementById('avgStress');
        if (stressAvgEl) stressAvgEl.textContent = `${data.avg_stress || 0}/100`;
        
        // Update mood average
        const moodAvgEl = document.getElementById('avgMood');
        if (moodAvgEl) {
            const moodLabels = {1: 'Very Low', 2: 'Low', 3: 'Neutral', 4: 'Happy', 5: 'Excited'};
            moodAvgEl.textContent = moodLabels[Math.round(data.avg_mood)] || 'Unknown';
        }
        
        // Update activity count
        const activityEl = document.getElementById('totalActivities');
        if (activityEl) activityEl.textContent = data.total_activities || 0;
        
        // Render charts with real data
        if (data.stress_history) renderStressChart(data.stress_history);
        if (data.mood_history) renderMoodChart(data.mood_history);

    } catch (error) {
        console.error('Error loading wellness summary:', error);
        const stressEl = document.getElementById('avgStress');
        if (stressEl) stressEl.textContent = 'Unable to load';
        const moodEl = document.getElementById('avgMood');
        if (moodEl) moodEl.textContent = 'Unable to load';
        const statusEl = document.getElementById('wellnessStatus');
        if (statusEl) statusEl.textContent = 'Error loading data';
    }
}

// Load activity log
async function loadActivityLog() {
    try {
        const response = await fetch('/parent/api/student/activity-log');
        if (!response.ok) throw new Error('Failed to load activity log');
        
        const activities = await response.json();
        const listEl = document.getElementById('activityLog');
        
        if (!listEl) return;
        
        if (activities.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No recent activities</div>';
            return;
        }
        
        listEl.innerHTML = activities.slice(0, 12).map(a => `
            <div class="activity-item">
                <div class="act-dot"></div>
                <div class="act-body">
                    <div class="act-desc">${esc(a.description)}</div>
                    <div class="act-time">${esc(formatDate(a.timestamp))}</div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading activity log:', error);
        const listEl = document.getElementById('activityLog');
        if (listEl) listEl.innerHTML = '<div class="empty-state">Failed to load activity</div>';
    }
}

// Load notifications
async function loadNotifications() {
    try {
        const response = await fetch('/parent/api/notifications');
        if (!response.ok) throw new Error('Failed to load notifications');
        
        const data = await response.json();
        const notifications = data.notifications || data;
        const listEl = document.getElementById('notificationsList');
        const badgeEl = document.getElementById('notificationBadge');
        
        if (badgeEl) {
            const unreadCount = notifications.filter(n => !n.read).length;
            badgeEl.textContent = unreadCount;
            badgeEl.style.display = unreadCount > 0 ? 'flex' : 'none';
        }
        
        if (listEl) {
            if (notifications.length === 0) {
                listEl.innerHTML = '<div class="empty-state">No notifications</div>';
            } else {
                listEl.innerHTML = notifications.map(n => `
                    <div class="notification-item ${n.read ? 'read' : 'unread'}" 
                         style="padding:12px; border-bottom:1px solid #e5e7eb; ${n.read ? '' : 'background:#f0f9ff;'}">
                        <div style="font-weight:600; color:#1f2937;">${esc(n.title)}</div>
                        <div style="color:#6b7280; font-size:14px; margin-top:4px;">${esc(n.message)}</div>
                        <div style="font-size:12px; color:#9ca3af; margin-top:8px;">${esc(formatDate(n.created_at))}</div>
                    </div>
                `).join('');
            }
        }
        
    } catch (error) {
        console.error('Error loading notifications:', error);
        const listEl = document.getElementById('notificationsList');
        if (listEl) listEl.innerHTML = '<div class="empty-state">Failed to load notifications</div>';
    }
}

// Render stress level chart
function renderStressChart(stressHistory) {
    if (stressChart) stressChart.destroy();
    
    const dates = stressHistory.map(s => new Date(s.date).toLocaleDateString());
    const levels = stressHistory.map(s => s.level);
    
    const options = {
        series: [{
            name: 'Stress Level',
            data: levels
        }],
        chart: {
            type: 'area',
            height: 280,
            toolbar: { show: false },
            animations: { enabled: true }
        },
        dataLabels: { enabled: false },
        stroke: {
            curve: 'smooth',
            width: 3
        },
        fill: {
            type: 'gradient',
            gradient: {
                shadeIntensity: 1,
                opacityFrom: 0.7,
                opacityTo: 0.2,
            }
        },
        colors: ['#667eea'],
        xaxis: {
            categories: dates,
            labels: {
                style: { fontSize: '12px' }
            }
        },
        yaxis: {
            min: 0,
            max: 100,
            tickAmount: 5,
            labels: {
                style: { fontSize: '12px' },
                formatter: val => Math.round(val)
            }
        },
        tooltip: {
            y: {
                formatter: (val) => `${Math.round(val)}/100`
            }
        },
        grid: {
            borderColor: '#e5e7eb',
            strokeDashArray: 4
        }
    };
    
    stressChart = new ApexCharts(document.querySelector('#stressChart'), options);
    stressChart.render();
}

// Render mood tracking chart
function renderMoodChart(moodHistory) {
    if (moodChart) moodChart.destroy();
    
    const moodCounts = {};
    moodHistory.forEach(m => {
        moodCounts[m.mood] = (moodCounts[m.mood] || 0) + 1;
    });
    
    const options = {
        series: Object.values(moodCounts),
        chart: {
            type: 'donut',
            height: 280
        },
        labels: Object.keys(moodCounts),
        colors: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a'],
        legend: {
            position: 'bottom',
            fontSize: '13px'
        },
        plotOptions: {
            pie: {
                donut: {
                    size: '65%',
                    labels: {
                        show: true,
                        total: {
                            show: true,
                            label: 'Total Entries',
                            fontSize: '14px',
                            color: '#6b7280'
                        }
                    }
                }
            }
        },
        dataLabels: {
            enabled: true,
            formatter: (val) => Math.round(val) + '%'
        }
    };
    
    moodChart = new ApexCharts(document.querySelector('#moodChart'), options);
    moodChart.render();
}

// Bind forms only when present in DOM
function bindForms() {
    const complaintForm = document.getElementById('complaintForm');
    if (complaintForm) {
        complaintForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = {
                category: document.getElementById('category').value,
                subject: document.getElementById('subject').value,
                description: document.getElementById('description').value,
                priority: document.getElementById('priority').value
            };

            try {
                const response = await fetch('/parent/api/complaint/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                if (!response.ok) throw new Error('Failed to submit complaint');

                showAlert('complaintAlert', 'Complaint submitted successfully! We will review it soon.', 'success');
                complaintForm.reset();
                loadComplaints();

            } catch (error) {
                console.error('Error submitting complaint:', error);
                showAlert('complaintAlert', 'Failed to submit complaint. Please try again.', 'error');
            }
        });
    }

    const suggestionForm = document.getElementById('suggestionForm');
    if (suggestionForm) {
        suggestionForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = {
                title: document.getElementById('suggestionTitle').value,
                category: document.getElementById('suggestionCategory').value,
                description: document.getElementById('suggestionDesc').value
            };

            try {
                const response = await fetch('/parent/api/suggestion/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                if (!response.ok) throw new Error('Failed to submit suggestion');

                showAlert('suggestionAlert', 'Thank you! Your suggestion has been submitted.', 'success');
                suggestionForm.reset();

            } catch (error) {
                console.error('Error submitting suggestion:', error);
                showAlert('suggestionAlert', 'Failed to submit suggestion. Please try again.', 'error');
            }
        });
    }
} // end bindForms

// Load complaints list (outer scope — called from DOMContentLoaded AND after submit)
async function loadComplaints() {
    try {
        const response = await fetch('/parent/api/complaints/list');
        if (!response.ok) throw new Error('Failed to load complaints');

        const complaints = await response.json();
        const listEl = document.getElementById('complaintList');

        if (!listEl) return;

        if (complaints.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No complaints submitted yet</div>';
            return;
        }

        listEl.innerHTML = complaints.map(c => `
            <div class="complaint-item">
                <h5>${esc(c.subject)}</h5>
                <p>${esc(c.description)}</p>
                <p><strong>Category:</strong> ${esc(c.category)} | <strong>Priority:</strong> ${esc(c.priority)}</p>
                <div class="status status-${esc(c.status)}">${esc(c.status).toUpperCase()}</div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading complaints:', error);
        const listEl = document.getElementById('complaintList');
        if (listEl) listEl.innerHTML = '<div class="empty-state">Failed to load complaints</div>';
    }
}

// Toggle notifications panel
window.toggleNotifications = function toggleNotifications() {
    const panel = document.getElementById('notificationsPanel');
    if (panel) panel.classList.toggle('is-open');
};

// Switch announcement filter
window.switchAnnouncement = function switchAnnouncement(filter, evt) {
    currentAnnouncementFilter = filter;

    const container = document.getElementById('announcementList');
    if (container && container.parentNode) {
        const tabs = container.parentNode.querySelectorAll('.tab');
        tabs.forEach(t => t.classList.remove('active'));
    }
    // evt may be missing when called from inline onclick — find the correct tab by filter value
    if (evt && evt.target) {
        evt.target.classList.add('active');
    } else {
        const allTabs = document.querySelectorAll('.tab[onclick*="switchAnnouncement"]');
        allTabs.forEach(t => { if (t.textContent.trim().toLowerCase().includes(filter === 'all' ? 'all' : filter)) t.classList.add('active'); });
    }

    loadAnnouncements();
};

// Load announcements
async function loadAnnouncements() {
    try {
        const response = await fetch('/parent/api/announcements');
        if (!response.ok) throw new Error('Failed to load announcements');
        
        let announcements = await response.json();
        
        // Filter announcements (match both singular/plural forms)
        if (currentAnnouncementFilter !== 'all') {
            const f = currentAnnouncementFilter;
            announcements = announcements.filter(a => a.type === f || a.type === f.replace(/s$/, '') || a.type === f + 's');
        }
        
        const listEl = document.getElementById('announcementList');
        
        if (announcements.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No announcements available</div>';
            return;
        }
        
        listEl.innerHTML = announcements.map(a => `
            <div class="announcement-item">
                <h4>${esc(a.title)}</h4>
                <p>${esc(a.content)}</p>
                <div class="meta">
                    <span class="badge badge-${esc(a.type)}">${esc(a.type).toUpperCase()}</span>
                    <span>${esc(formatDate(a.date))}</span>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading announcements:', error);
        document.getElementById('announcementList').innerHTML = 
            '<div class="empty-state">Failed to load announcements</div>';
    }
}

// Helper function to show alerts
function showAlert(elementId, message, type) {
    const alertEl = document.getElementById(elementId);
    alertEl.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    setTimeout(() => alertEl.innerHTML = '', 5000);
}

// Helper function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

})(); // end IIFE
