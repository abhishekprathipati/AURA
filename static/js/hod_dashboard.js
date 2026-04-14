// ═══ STATE ═══
const DASHBOARD_STATE = {
    stats: {},
    riskOversight: [],
    proctors: [],
    students: [],
    trends: {},
    currentTheme: localStorage.getItem('aura-theme') || 'light'
};

// ═══ THEME ═══
function initTheme() {
    document.documentElement.setAttribute('data-theme', DASHBOARD_STATE.currentTheme);
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = DASHBOARD_STATE.currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

function toggleTheme() {
    DASHBOARD_STATE.currentTheme = DASHBOARD_STATE.currentTheme === 'light' ? 'dark' : 'light';
    localStorage.setItem('aura-theme', DASHBOARD_STATE.currentTheme);
    initTheme();
    showToast(`Switched to ${DASHBOARD_STATE.currentTheme} mode`);
}

// ═══ UTILS ═══
function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = `toast show ${type}`;
    setTimeout(() => t.classList.remove('show'), 3000);
}

function animateCount(el, target, suffix = '') {
    if (!el) return;
    let current = 0;
    const targetVal = parseFloat(target) || 0;
    const duration = 1000;
    const step = targetVal / (duration / 16);
    const timer = setInterval(() => {
        current += step;
        if (current >= targetVal) {
            el.textContent = (targetVal % 1 === 0 ? targetVal : targetVal.toFixed(1)) + suffix;
            clearInterval(timer);
        } else {
            el.textContent = (current % 1 === 0 ? Math.floor(current) : current.toFixed(1)) + suffix;
        }
    }, 16);
}

// ═══ DATA FETCHING ═══
async function loadDashboard() {
    try {
        const endpoints = [
            '/proctor/api/hod/dashboard-stats',
            '/proctor/api/hod/risk-oversight',
            '/proctor/api/hod/risk-distribution',
            '/proctor/api/hod/wellness-trends',
            '/proctor/api/hod/proctor-performance',
            '/proctor/api/hod/students',
            '/proctor/api/hod/department-proctors'
        ];

        const [stats, riskBox, distribution, trends, performance, students, proctors] = await Promise.all(
            endpoints.map(e => fetch(e).then(r => r.json()))
        );

        if (stats.success) renderStats(stats.data);
        if (riskBox.success) renderRiskOversight(riskBox.data);
        if (distribution.success) renderDistribution(distribution.data);
        if (trends.success) renderTrends(trends.data);
        if (performance.success) renderProctorPerformance(performance.data);
        if (students.success) {
            DASHBOARD_STATE.students = students.data;
            renderStudents(students.data);
        }
        if (proctors.success) renderProctors(proctors.data);

    } catch (err) {
        console.error('HOD Sync Error:', err);
    }
}

// ═══ RENDERERS ═══
function renderStats(data) {
    animateCount(document.getElementById('wellnessScore'), data.avg_wellness, '%');
    animateCount(document.getElementById('totalStudents'), data.total_students);
    animateCount(document.getElementById('proctorActions'), data.proctor_actions_today);
    animateCount(document.getElementById('highRiskCount'), data.high_risk_incidents);
    
    const critCard = document.getElementById('criticalCard');
    if (critCard) {
        if (data.high_risk_incidents > 0) critCard.classList.add('has-critical');
        else critCard.classList.remove('has-critical');
    }
}

function renderRiskOversight(data) {
    const body = document.getElementById('riskOversightBody');
    const count = document.getElementById('riskOversightCount');
    if (!body) return;
    
    count.textContent = data.length;
    
    if (data.length === 0) {
        body.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 40px; color: var(--text-muted)">No active critical alerts.</td></tr>';
        return;
    }

    body.innerHTML = data.map(inc => {
        const time = new Date(inc.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const riskClass = inc.risk_level === 'HIGH' ? 'high' : 'medium';
        const statusClass = inc.status === 'ESCALATED' ? 'high' : '';
        
        return `
            <tr class="fade-in">
                <td><strong>${esc(inc.anonymous_student_id)}</strong></td>
                <td><span class="tag ${riskClass}">${esc(inc.risk_level)}</span></td>
                <td><span style="font-size: 0.8rem; color: var(--text-muted)">${esc(inc.trigger_source)}</span></td>
                <td><span class="tag ${statusClass}">${esc(inc.status)}</span></td>
                <td style="color: var(--text-muted)">${time}</td>
            </tr>
        `;
    }).join('');
}

function renderStudents(data) {
    const body = document.getElementById('studentHubBody');
    if (!body) return;

    if (data.length === 0) {
        body.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 40px;">No students records found.</td></tr>';
        return;
    }

    body.innerHTML = data.map(s => `
        <tr>
            <td><code>${esc(s.anonymous_id)}</code></td>
            <td><strong>${esc(s.name)}</strong></td>
            <td>${esc(s.department)}</td>
            <td><span class="proctor-name">${esc(s.proctor_id)}</span></td>
            <td><span class="tag ${s.risk_level.toLowerCase()}">${esc(s.risk_level)}</span></td>
        </tr>
    `).join('');
}

function filterStudents() {
    const q = document.getElementById('studentSearch').value.toLowerCase();
    const filtered = DASHBOARD_STATE.students.filter(s => 
        s.name.toLowerCase().includes(q) || s.roll_number.toLowerCase().includes(q) || s.anonymous_id.toLowerCase().includes(q)
    );
    renderStudents(filtered);
}

function renderProctorPerformance(data) {
    const container = document.getElementById('proctorPerformanceTable');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-muted)">No active performance metrics.</div>';
        return;
    }

    container.innerHTML = `
        <table class="aura-table">
            <thead><tr><th>Proctor</th><th>Actions</th><th>Ratio</th></tr></thead>
            <tbody>
                ${data.map(p => {
                    const ratio = Math.round((p.escalations / (p.total_actions || 1)) * 100);
                    return `
                        <tr>
                            <td><strong>${esc(p.proctor_id)}</strong></td>
                            <td>${p.total_actions}</td>
                            <td><span class="tag">${ratio}% Esc.</span></td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

function renderProctors(data) {
    const container = document.getElementById('proctorListContainer');
    if (!container) return;

    if (data.length === 0) {
        container.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-muted)">No proctors assigned to department.</div>';
        return;
    }

    container.innerHTML = data.map(p => `
        <div class="proctor-item">
            <div class="proctor-info">
                <span class="p-name">${esc(p.name)}</span>
                <span class="p-email">${esc(p.email)}</span>
            </div>
            <button class="remove-btn" onclick="removeProctor('${p.email}')">
                <i class="fas fa-trash-alt"></i>
            </button>
        </div>
    `).join('');
}

// ═══ PROCTOR ACTIONS ═══
function showAddProctorModal() {
    document.getElementById('proctorModal').classList.add('visible');
}

function hideModal(id) {
    document.getElementById(id).classList.remove('visible');
}

async function submitProctor(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('pName').value,
        email: document.getElementById('pEmail').value,
        password: document.getElementById('pPass').value
    };

    try {
        const res = await fetch('/proctor/api/hod/manage-proctors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.success) {
            showToast('Proctor account created successfully!');
            hideModal('proctorModal');
            loadDashboard();
            e.target.reset();
        } else {
            showToast(data.error || 'Failed to create proctor account', 'error');
        }
    } catch (err) {
        showToast('System error. Please try again.', 'error');
    }
}

// ═══ UI NAVIGATION ═══
function switchTab(evt, tabId) {
    const tabContents = document.getElementsByClassName("tab-content");
    for (let i = 0; i < tabContents.length; i++) {
        tabContents[i].classList.remove("active");
    }

    const tabLinks = document.getElementsByClassName("tab-link");
    for (let i = 0; i < tabLinks.length; i++) {
        tabLinks[i].classList.remove("active");
    }

    document.getElementById(tabId).classList.add("active");
    evt.currentTarget.classList.add("active");

    // Toggle Search visibility (only for Roster)
    const searchGroup = document.getElementById('rosterSearchGroup');
    if (searchGroup) {
        searchGroup.style.display = (tabId === 'student-roster') ? 'block' : 'none';
    }
    
    // Resize charts if necessary
    if (trendChart) trendChart.windowResizeHandler();
    if (healthChart) healthChart.windowResizeHandler();
}

async function removeProctor(email) {
    if (!confirm(`Are you sure you want to revoke access for ${email}?`)) return;

    try {
        const res = await fetch(`/proctor/api/hod/manage-proctors/${email}`, {
            method: 'DELETE',
            headers: { 'X-CSRF-Token': getCsrfToken() }
        });
        if (res.ok) {
            showToast('Proctor access revoked.');
            loadDashboard();
        }
    } catch (err) {
        showToast('Failed to remove proctor.', 'error');
    }
}

// ═══ CHART RENDERERS ═══
let trendChart = null;
function renderTrends(data) {
    const el = document.querySelector('#trendChart');
    if (!el) return;
    const isDark = DASHBOARD_STATE.currentTheme === 'dark';
    const accentColor = '#6366f1';

    const options = {
        series: [{ name: 'Wellness Index', data: data.wellness }],
        chart: { type: 'area', height: 350, toolbar: { show: false }, zoom: { enabled: false } },
        colors: [accentColor],
        fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0.05 } },
        dataLabels: { enabled: false },
        stroke: { curve: 'smooth', width: 4 },
        xaxis: { categories: data.dates, labels: { style: { colors: isDark ? '#94a3b8' : '#64748b' } } },
        yaxis: { max: 100, min: 0, labels: { style: { colors: isDark ? '#94a3b8' : '#64748b' } } },
        grid: { borderColor: isDark ? 'rgba(148, 163, 184, 0.05)' : 'rgba(100, 116, 139, 0.1)' }
    };

    if (trendChart) trendChart.updateOptions(options);
    else { trendChart = new ApexCharts(el, options); trendChart.render(); }
}

let healthChart = null;
function renderDistribution(data) {
    const el = document.querySelector('#healthChart');
    if (!el) return;

    const options = {
        series: [data.low, data.medium, data.high],
        chart: { type: 'donut', height: 320 },
        labels: ['Stable Focus', 'Caution required', 'Critical Attention'],
        colors: ['#10b981', '#f59e0b', '#ef4444'],
        plotOptions: { pie: { donut: { size: '78%', labels: { show: true, total: { show: true, label: 'TOTAL STUDENTS', fontSize: '11px', fontWeight: 800, color: '#64748b' } } } } },
        legend: { show: false },
        stroke: { width: 0 }
    };

    if (healthChart) healthChart.updateOptions(options);
    else { healthChart = new ApexCharts(el, options); healthChart.render(); }
    
    const container = document.getElementById('riskBarsContainer');
    if (container) {
        container.innerHTML = `
            ${renderRiskPill('Critical Priority', data.high, data.total, '#ef4444')}
            ${renderRiskPill('Management Required', data.medium, data.total, '#f59e0b')}
            ${renderRiskPill('Stable/Routine', data.low, data.total, '#10b981')}
        `;
    }
}

function renderRiskPill(label, count, total, color) {
    const pct = (count / (total || 1) * 100);
    return `
        <div class="risk-bar-item">
            <div class="risk-bar-label">${label}</div>
            <div class="risk-bar-track">
                <div class="risk-bar-fill" style="width:${pct}%; background:${color}"></div>
            </div>
            <div class="risk-bar-val">${count}</div>
        </div>
    `;
}

function getCsrfToken() {
    return ""; // Token is managed server-side for this implementation
}

function refreshData() {
    loadDashboard();
    showToast('Dashboard synchronized');
}

// ═══ INIT ═══
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadDashboard();
    document.getElementById('themeToggle')?.addEventListener('click', toggleTheme);
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString([], { weekday: 'long', day: 'numeric', month: 'long' });
    setInterval(loadDashboard, 120000);
});
