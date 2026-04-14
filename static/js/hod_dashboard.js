// ═══ STATE ═══
const DASHBOARD_STATE = {
    stats: {},
    riskOversight: [],
    proctors: [],
    trends: {},
    currentTheme: localStorage.getItem('aura-theme') || 'light'
};

// ═══ THEME LOGIC ═══
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
    showToast(`Switched to ${DASHBOARD_STATE.currentTheme} mode`, 'success');
}

// ═══ UTILS ═══
function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast show';
    setTimeout(() => t.classList.remove('show'), 3000);
}

function animateCount(el, target, suffix = '') {
    if (!el) return;
    let current = 0;
    const duration = 1000;
    const step = target / (duration / 16);
    const timer = setInterval(() => {
        current += step;
        if (current >= target) {
            el.textContent = target + suffix;
            clearInterval(timer);
        } else {
            el.textContent = Math.floor(current) + suffix;
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
            '/proctor/api/hod/proctor-performance'
        ];

        const [stats, riskBox, distribution, trends, proctors] = await Promise.all(
            endpoints.map(e => fetch(e).then(r => r.json()))
        );

        if (stats.success) renderStats(stats.data);
        if (riskBox.success) renderRiskOversight(riskBox.data);
        if (distribution.success) renderDistribution(distribution.data);
        if (trends.success) renderTrends(trends.data);
        if (proctors.success) renderProctors(proctors.data);

    } catch (err) {
        console.error('HOD Load Error:', err);
        showToast('Sync error. Retrying...');
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
        body.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 40px; color: var(--muted)">No critical alerts requiring immediate oversight.</td></tr>';
        return;
    }

    body.innerHTML = data.map(inc => {
        const time = new Date(inc.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return `
            <tr class="fade-in">
                <td><strong>${esc(inc.anonymous_student_id)}</strong></td>
                <td><span class="badge high">${esc(inc.risk_level)}</span></td>
                <td><span style="font-size: 0.8rem; color: var(--muted)">${esc(inc.trigger_source)}</span></td>
                <td><span class="badge ${inc.is_escalated ? 'escalated' : ''}">${esc(inc.status)}</span></td>
                <td>${time}</td>
            </tr>
        `;
    }).join('');
}

let trendChart = null;
function renderTrends(data) {
    const el = document.querySelector('#trendChart');
    if (!el) return;
    
    const options = {
        series: [{ name: 'Wellness', data: data.wellness }],
        chart: { type: 'area', height: 280, toolbar: { show: false }, zoom: { enabled: false } },
        colors: ['#6366f1'],
        fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.3, opacityTo: 0.05 } },
        dataLabels: { enabled: false },
        stroke: { curve: 'smooth', width: 3 },
        xaxis: { categories: data.dates, labels: { style: { colors: '#94a3b8' } } },
        yaxis: { max: 100, labels: { style: { colors: '#94a3b8' } } },
        grid: { borderColor: 'rgba(148, 163, 184, 0.1)' }
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
        chart: { type: 'donut', height: 240 },
        labels: ['Low', 'Medium', 'High'],
        colors: ['#10b981', '#f59e0b', '#ef4444'],
        plotOptions: { pie: { donut: { size: '75%' } } },
        legend: { position: 'bottom' }
    };

    if (healthChart) healthChart.updateOptions(options);
    else { healthChart = new ApexCharts(el, options); healthChart.render(); }
    
    // Risk Bars
    const container = document.getElementById('riskBarsContainer');
    if (container) {
        container.innerHTML = `
            <div style="margin-top:20px; display:flex; flex-direction:column; gap:12px">
                ${renderRiskBar('High Risk', data.high, data.total, '#ef4444')}
                ${renderRiskBar('Medium Risk', data.medium, data.total, '#f59e0b')}
                ${renderRiskBar('Low Risk', data.low, data.total, '#10b981')}
            </div>
        `;
    }
}

function renderRiskBar(label, count, total, color) {
    const pct = (count / total * 100) || 0;
    return `
        <div class="risk-bar-item" style="display:flex; align-items:center; gap:12px">
            <div style="font-size:0.75rem; font-weight:700; min-width:80px">${label}</div>
            <div style="flex:1; height:6px; background:var(--surface-muted); border-radius:3px; overflow:hidden">
                <div style="width:${pct}%; height:100%; background:${color}"></div>
            </div>
            <div style="font-size:0.75rem; font-weight:800">${count}</div>
        </div>
    `;
}

function renderProctors(data) {
    const el = document.getElementById('proctorTable');
    if (!el) return;
    
    if (data.length === 0) {
        el.innerHTML = '<div style="padding:40px; text-align:center; color:var(--muted)">No proctor data found.</div>';
        return;
    }

    el.innerHTML = `
        <table class="tbl">
            <thead><tr><th>Proctor</th><th>Actions</th></tr></thead>
            <tbody>
                ${data.map(p => `
                    <tr>
                        <td><strong>${esc(p.proctor_id)}</strong></td>
                        <td><span class="badge escalated">${p.total_actions}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function refreshData() {
    loadDashboard();
    showToast('Refreshing system data...');
}

// ═══ INIT ═══
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadDashboard();
    
    document.getElementById('themeToggle')?.addEventListener('click', toggleTheme);
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
    
    setInterval(loadDashboard, 60000); // 1-minute refresh
});
