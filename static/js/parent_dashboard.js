// Parent Dashboard JavaScript

let currentAnnouncementFilter = 'all';
let stressChart, moodChart;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadPerformanceData();
    loadWellnessSummary();
    loadComplaints();
    loadAnnouncements();
    loadActivityLog();
    loadNotifications();
});

// Logout function
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/parent/logout';
    }
}

// Switch performance tabs
function switchTab(tab) {
    const tabs = document.querySelectorAll('.tabs .tab');
    const contents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(t => t.classList.remove('active'));
    contents.forEach(c => c.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(`${tab}-content`).classList.add('active');
}

// Load comprehensive wellness summary
async function loadWellnessSummary() {
    try {
        const response = await fetch('/parent/api/student/wellness-summary');
        if (!response.ok) throw new Error('Failed to load wellness summary');
        
        const data = await response.json();
        
        // Update wellness status display
        const statusEl = document.getElementById('wellnessStatus');
        if (statusEl) {
            const statusColors = {
                'good': '#10b981',
                'moderate': '#f59e0b',
                'needs_attention': '#ef4444'
            };
            statusEl.style.color = statusColors[data.wellness_status] || '#6b7280';
            statusEl.textContent = data.wellness_status === 'good' ? 'Good' : 
                                  data.wellness_status === 'moderate' ? 'Moderate' : 'Needs Attention';
        }
        
        // Update stress average
        const stressAvgEl = document.getElementById('avgStress');
        if (stressAvgEl) stressAvgEl.textContent = `${data.avg_stress || 0}/100`;
        
        // Update mood average
        const moodAvgEl = document.getElementById('avgMood');
        if (moodAvgEl) {
            const moodLabels = {1: 'Very Low', 2: 'Low', 3: 'Neutral', 4: 'Good', 5: 'Excellent'};
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
    }
}

// Load student performance data
async function loadPerformanceData() {
    try {
        const response = await fetch('/parent/api/student/performance');
        if (!response.ok) throw new Error('Failed to load performance data');
        
        const data = await response.json();
        
        // Render stress chart
        renderStressChart(data.stress_history || []);
        
        // Render mood chart
        renderMoodChart(data.mood_history || []);
        
    } catch (error) {
        console.error('Error loading performance:', error);
        showAlert('complaintAlert', 'Failed to load performance data', 'error');
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
        
        listEl.innerHTML = activities.slice(0, 10).map(a => `
            <div class="activity-item" style="padding:12px; border-bottom:1px solid #e5e7eb;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="badge badge-${a.type}">${a.type.toUpperCase()}</span>
                    <span style="font-size:12px; color:#9ca3af;">${formatDate(a.timestamp)}</span>
                </div>
                <div style="margin-top:8px; color:#374151;">${a.description}</div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading activity log:', error);
    }
}

// Load notifications
async function loadNotifications() {
    try {
        const response = await fetch('/parent/api/notifications');
        if (!response.ok) throw new Error('Failed to load notifications');
        
        const notifications = await response.json();
        const listEl = document.getElementById('notificationsList');
        const badgeEl = document.getElementById('notificationBadge');
        
        if (badgeEl) {
            const unreadCount = notifications.filter(n => !n.read).length;
            badgeEl.textContent = unreadCount;
            badgeEl.style.display = unreadCount > 0 ? 'inline' : 'none';
        }
        
        if (listEl) {
            if (notifications.length === 0) {
                listEl.innerHTML = '<div class="empty-state">No notifications</div>';
            } else {
                listEl.innerHTML = notifications.map(n => `
                    <div class="notification-item ${n.read ? 'read' : 'unread'}" 
                         style="padding:12px; border-bottom:1px solid #e5e7eb; ${n.read ? '' : 'background:#f0f9ff;'}">
                        <div style="font-weight:600; color:#1f2937;">${n.title}</div>
                        <div style="color:#6b7280; font-size:14px; margin-top:4px;">${n.message}</div>
                        <div style="font-size:12px; color:#9ca3af; margin-top:8px;">${formatDate(n.created_at)}</div>
                    </div>
                `).join('');
            }
        }
        
    } catch (error) {
        console.error('Error loading notifications:', error);
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
            max: 10,
            labels: {
                style: { fontSize: '12px' }
            }
        },
        tooltip: {
            y: {
                formatter: (val) => `${val}/10`
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

// Submit complaint form
document.getElementById('complaintForm').addEventListener('submit', async (e) => {
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
        document.getElementById('complaintForm').reset();
        loadComplaints();
        
    } catch (error) {
        console.error('Error submitting complaint:', error);
        showAlert('complaintAlert', 'Failed to submit complaint. Please try again.', 'error');
    }
});

// Load complaints list
async function loadComplaints() {
    try {
        const response = await fetch('/parent/api/complaints/list');
        if (!response.ok) throw new Error('Failed to load complaints');
        
        const complaints = await response.json();
        const listEl = document.getElementById('complaintList');
        
        if (complaints.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No complaints submitted yet</div>';
            return;
        }
        
        listEl.innerHTML = complaints.map(c => `
            <div class="complaint-item">
                <h5>${c.subject}</h5>
                <p>${c.description}</p>
                <p><strong>Category:</strong> ${c.category} | <strong>Priority:</strong> ${c.priority}</p>
                <div class="status status-${c.status}">${c.status.toUpperCase()}</div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading complaints:', error);
    }
}

// Submit suggestion form
document.getElementById('suggestionForm').addEventListener('submit', async (e) => {
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
        document.getElementById('suggestionForm').reset();
        
    } catch (error) {
        console.error('Error submitting suggestion:', error);
        showAlert('suggestionAlert', 'Failed to submit suggestion. Please try again.', 'error');
    }
});

// Switch announcement filter
function switchAnnouncement(filter) {
    currentAnnouncementFilter = filter;
    
    const tabs = document.querySelectorAll('.announcement-list').parentNode.querySelectorAll('.tab');
    tabs.forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    
    loadAnnouncements();
}

// Load announcements
async function loadAnnouncements() {
    try {
        const response = await fetch('/parent/api/announcements');
        if (!response.ok) throw new Error('Failed to load announcements');
        
        let announcements = await response.json();
        
        // Filter announcements
        if (currentAnnouncementFilter !== 'all') {
            announcements = announcements.filter(a => a.type === currentAnnouncementFilter);
        }
        
        const listEl = document.getElementById('announcementList');
        
        if (announcements.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No announcements available</div>';
            return;
        }
        
        listEl.innerHTML = announcements.map(a => `
            <div class="announcement-item">
                <h4>${a.title}</h4>
                <p>${a.content}</p>
                <div class="meta">
                    <span class="badge badge-${a.type}">${a.type.toUpperCase()}</span>
                    <span>${formatDate(a.date)}</span>
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
