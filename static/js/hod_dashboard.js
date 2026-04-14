// ═══ UTILITIES ═══
const DASHBOARD_STATE = {
    suggestions: [],
    managedProctors: [],
    suggestionSearch: '',
    suggestionStatus: 'all',
    proctorSearch: '',
    proctorFilter: 'all',
    currentTab: 'overview'
};

function esc(s) {
    if (s == null) return '';
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(String(s)));
    return d.innerHTML;
}

function showToast(msg, type = 'info') {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast ' + type + ' show';
    setTimeout(() => t.classList.remove('show'), 3000);
}

function animateCount(el, target, duration = 800) {
    if (!el) return;
    const start = parseInt(el.textContent) || 0;
    if (start === target) { el.textContent = target; return; }
    const range = target - start;
    const startTime = performance.now();
    function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(start + range * eased);
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

function applyRowDelays(container) {
    if (!container) return;
    const items = container.querySelectorAll('tr, .list-item');
    items.forEach((item, i) => { item.style.animationDelay = `${i * 0.05}s`; });
}

// ═══ NAVIGATION ═══
function switchTab(tabId) {
    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    
    document.getElementById(tabId)?.classList.add('active');
    const link = document.querySelector(`[onclick="switchTab('${tabId}')"]`);
    if (link) link.classList.add('active');
    
    document.querySelector('.header-title h2').textContent = 
        tabId === 'overview' ? 'Diagnostic Overview' :
        tabId === 'students' ? 'Student Risk Monitor' :
        tabId === 'proctors' ? 'Proctor Management' : 'Parent Improvement Hub';
    
    DASHBOARD_STATE.currentTab = tabId;
}

// ═══ CHARTS ═══
let healthChart = null;
let trendChart = null;

function initCharts() {
    // Donut Chart
    healthChart = new ApexCharts(document.querySelector('#healthChart'), {
        series: [0, 0, 0],
        chart: { type: 'donut', height: 280, animations: { enabled: true } },
        labels: ['Low Risk', 'Medium Risk', 'High Risk'],
        colors: ['#10b981', '#f59e0b', '#ef4444'],
        plotOptions: {
            pie: {
                donut: {
                    size: '72%',
                    labels: {
                        show: true,
                        total: { show: true, label: 'Health', fontSize: '14px', formatter: () => 'Index' }
                    }
                }
            }
        },
        legend: { show: false },
        stroke: { width: 3, colors: ['#fff'] }
    });
    healthChart.render();

    // Trend Line Chart
    trendChart = new ApexCharts(document.querySelector('#trendChart'), {
        series: [{ name: 'Wellness Index', data: [] }],
        chart: { type: 'area', height: 350, toolbar: { show: false }, zoom: { enabled: false } },
        colors: ['#6366f1'],
        fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.45, opacityTo: 0.05, stops: [20, 100] } },
        dataLabels: { enabled: false },
        stroke: { curve: 'smooth', width: 3 },
        xaxis: { categories: [], labels: { style: { colors: '#64748b' } } },
        yaxis: { max: 100, labels: { style: { colors: '#64748b' } } },
        grid: { borderColor: '#f1f5f9', strokeDashArray: 4 }
    });
    trendChart.render();
}

// ═══ DATA LOADING ═══
async function loadDashboard() {
    try {
        const endpoints = [
            '/proctor/api/hod/dashboard-stats',
            '/proctor/api/hod/risk-distribution',
            '/proctor/api/hod/wellness-trends',
            '/proctor/api/hod/recent-escalations',
            '/proctor/api/hod/proctor-performance',
            '/proctor/api/hod/parent-suggestions',
            '/proctor/api/hod/proctors',
            '/proctor/api/hod/students'
        ];
        
        const [stats, risk, trends, escalations, proctors, suggestions, managedProctors, students] = await Promise.all(
            endpoints.map(e => fetch(e).then(r => r.json()))
        );

        // KPI Stats
        if (stats.success) {
            const d = stats.data;
            animateCount(document.getElementById('wellnessScore'), d.avg_wellness || 0);
            animateCount(document.getElementById('totalStudents'), d.total_students || 0);
            animateCount(document.getElementById('proctorActions'), d.proctor_actions_today || 0);
            animateCount(document.getElementById('highRiskCount'), d.high_risk_incidents || 0);

            // Critical pulse for HOD oversight
            const criticalCard = document.getElementById('criticalCard');
            if (criticalCard) {
                if ((d.high_risk_incidents || 0) > 0) {
                    criticalCard.classList.add('has-critical');
                } else {
                    criticalCard.classList.remove('has-critical');
                }
            }
        }

        // Charts
        if (risk.success) {
            renderRiskBars(risk.data);
            healthChart.updateSeries([risk.data.low || 0, risk.data.medium || 0, risk.data.high || 0]);
        }

        if (trends.success) {
            trendChart.updateOptions({
                xaxis: { categories: trends.data.dates || [] },
                series: [{ name: 'Wellness Index', data: trends.data.wellness || [] }]
            });
        }

        if (escalations.success) renderEscalations(escalations.data || []);
        if (proctors.success) renderProctors(proctors.data || []);
        
        if (suggestions.success) {
            DASHBOARD_STATE.suggestions = suggestions.data || [];
            renderSuggestions();
            renderImplementationHistory();
        }

        if (managedProctors.success) {
            DASHBOARD_STATE.managedProctors = managedProctors.data || [];
            renderManageProctors();
        }

        if (students.success) {
            DASHBOARD_STATE.students = students.data || [];
            renderStudents();
        }
        
        document.querySelectorAll('.skeleton').forEach(s => s.classList.remove('skeleton'));

    } catch (err) {
        console.error('HOD Dashboard Load Error:', err);
        showToast('System synchronization delay. Retrying...', 'error');
    }
}

// ─── Render Functions ───
function renderRiskBars(data) {
    const container = document.getElementById('riskBarsContainer');
    if (!container) return;
    const total = (data.high || 0) + (data.medium || 0) + (data.low || 0);
    const max = Math.max(data.high || 0, data.medium || 0, data.low || 0, 1);

    const items = [
        { label: 'High', count: data.high || 0, color: '#ef4444' },
        { label: 'Medium', count: data.medium || 0, color: '#f59e0b' },
        { label: 'Low', count: data.low || 0, color: '#10b981' }
    ];

    container.innerHTML = items.map(item => `
        <div class="risk-bar-item">
            <div class="risk-bar-label"><span class="risk-dot" style="background:${item.color}"></span>${item.label}</div>
            <div class="risk-bar-track"><div class="risk-bar-fill" style="background:${item.color}; width:${(item.count/max*100)}%"></div></div>
            <div class="risk-bar-count">${item.count}</div>
        </div>
    `).join('') + `<div class="total-count">Total: ${total}</div>`;
}

function renderEscalations(data) {
    const el = document.getElementById('escalationsList');
    if (!el) return;
    if (!data.length) {
        el.innerHTML = '<div class="empty">No escalated incidents reviewed today.</div>';
        return;
    }
    el.innerHTML = data.map(item => `
        <div class="list-item">
            <div class="list-icon danger"><i class="fas fa-exclamation-circle"></i></div>
            <div class="list-content">
                <div class="list-title">${esc(item.trigger_source)}</div>
                <div class="list-sub">${esc(item.message_excerpt)}</div>
            </div>
            <div class="list-right"><span class="badge high">${item.risk_level}</span></div>
        </div>
    `).join('');
    applyRowDelays(el);
}

function renderProctors(data) {
    const el = document.getElementById('proctorTable');
    if (!el) return;
    if (!data.length) {
        el.innerHTML = '<div class="empty">No proctor activity logged this week.</div>';
        return;
    }
    el.innerHTML = `
        <table class="tbl">
            <thead><tr><th>Proctor</th><th>Actions</th><th>Status</th></tr></thead>
            <tbody>
                ${data.map(p => `
                    <tr>
                        <td><div class="proctor-cell"><div class="proctor-avatar">${p.proctor_id.charAt(0)}</div>${esc(p.proctor_id)}</div></td>
                        <td>${p.total_actions}</td>
                        <td><span class="badge low">Active</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    applyRowDelays(el);
}

function renderSuggestions() {
    const el = document.getElementById('suggestionsList');
    if (!el) return;
    const data = DASHBOARD_STATE.suggestions || [];
    if (!data.length) {
        el.innerHTML = '<div class="empty">No active parent suggestions.</div>';
        return;
    }
    el.innerHTML = data.map(item => `
        <div class="list-item">
            <div class="list-icon info"><i class="fas fa-lightbulb"></i></div>
            <div class="list-content">
                <div class="list-title">${esc(item.title)}</div>
                <div class="list-sub">${esc(item.description)}</div>
                <div class="mini-meta" style="margin-top:8px">
                    <span class="badge info">${esc(item.category)}</span>
                    <span class="badge low">${esc(item.status)}</span>
                </div>
            </div>
        </div>
    `).join('');
    applyRowDelays(el);
}

function renderManageProctors() {
    const el = document.getElementById('manageProctorsTable');
    if (!el) return;
    const data = DASHBOARD_STATE.managedProctors || [];
    if (!data.length) {
        el.innerHTML = '<div class="empty">No proctors registered in your department.</div>';
        return;
    }
    el.innerHTML = `
        <table class="tbl">
            <thead><tr><th>Name</th><th>Email</th><th>Load</th><th>Status</th></tr></thead>
            <tbody>
                ${data.map(p => `
                    <tr>
                        <td><div class="proctor-cell"><strong>${esc(p.name)}</strong></div></td>
                        <td>${esc(p.email)}</td>
                        <td>${p.assigned_students || 0} Students</td>
                        <td><span class="status-active">Online</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    applyRowDelays(el);
}

function refreshData() {
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i>';
    loadDashboard().finally(() => {
        if (btn) btn.innerHTML = '<i class="fas fa-sync-alt"></i>';
        showToast('System data synchronized', 'success');
    });
}

function renderStudents() {
    const el = document.getElementById('studentTableContainer');
    if (!el) return;
    const query = (document.getElementById('studentSearch')?.value || '').toLowerCase();
    const data = (DASHBOARD_STATE.students || []).filter(s => 
        !query || s.name.toLowerCase().includes(query) || s.roll_number.toLowerCase().includes(query) || s.risk_level.toLowerCase().includes(query)
    );

    if (!data.length) {
        el.innerHTML = '<div class="empty">No students found matching your search.</div>';
        return;
    }

    el.innerHTML = `
        <table class="tbl">
            <thead><tr><th>Student</th><th>Roll No.</th><th>Proctor</th><th>Risk Level</th><th>Action</th></tr></thead>
            <tbody>
                ${data.map(s => `
                    <tr>
                        <td><strong>${esc(s.name)}</strong></td>
                        <td>${esc(s.roll_number)}</td>
                        <td>${esc(s.proctor_id)}</td>
                        <td><span class="badge ${s.risk_level.toLowerCase()}">${s.risk_level}</span></td>
                        <td><button class="btn-mini review" onclick="window.location.href='/proctor/student/${s.anonymous_id}'">Inspect</button></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    applyRowDelays(el);
}

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    loadDashboard();
    
    document.getElementById('studentSearch')?.addEventListener('input', renderStudents);
    
    setInterval(loadDashboard, 60000);
});
