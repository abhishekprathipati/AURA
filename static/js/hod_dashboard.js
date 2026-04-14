// ═══ STATE ═══
const DASHBOARD_STATE = {
    stats: {},
    riskOversight: [],
    proctors: [],
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

// ═══ API ═══
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
        console.error('HOD Sync Error:', err);
        showToast('Connection to server lost. Retrying...');
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
        body.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 60px; color: var(--text-muted); font-weight: 500;">No active critical alerts in department.</td></tr>';
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

let trendChart = null;
function renderTrends(data) {
    const el = document.querySelector('#trendChart');
    if (!el) return;
    
    const isDark = DASHBOARD_STATE.currentTheme === 'dark';
    const accentColor = '#6366f1';

    const options = {
        series: [{ name: 'Wellness Index', data: data.wellness }],
        chart: { type: 'area', height: 350, toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: true, easing: 'easeinout', speed: 800 } },
        colors: [accentColor],
        fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0.05 } },
        dataLabels: { enabled: false },
        stroke: { curve: 'smooth', width: 4 },
        xaxis: { categories: data.dates, labels: { style: { colors: isDark ? '#94a3b8' : '#64748b', fontWeight: 600 } }, axisBorder: { show: false } },
        yaxis: { max: 100, min: 0, labels: { style: { colors: isDark ? '#94a3b8' : '#64748b', fontWeight: 600 } } },
        grid: { borderColor: isDark ? 'rgba(148, 163, 184, 0.05)' : 'rgba(100, 116, 139, 0.1)', strokeDashArray: 5 }
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
    
    // Risk Bars (Fixed structure)
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

function renderProctors(data) {
    const el = document.getElementById('proctorTable');
    if (!el) return;
    
    if (data.length === 0) {
        el.innerHTML = '<div style="padding:60px; text-align:center; color:var(--text-muted); font-weight: 500;">No proctor performance metrics available.</div>';
        return;
    }

    el.innerHTML = `
        <table class="aura-table">
            <thead><tr><th>Assigned Proctor</th><th>Weekly Impacts</th></tr></thead>
            <tbody>
                ${data.map(p => `
                    <tr>
                        <td><strong>${esc(p.proctor_id)}</strong></td>
                        <td><span class="tag" style="background: var(--surface-muted); color: var(--primary); border: 1px solid var(--border)">${p.total_actions} Actions</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function refreshData() {
    loadDashboard();
    showToast('Dashboard synchronized with live hub');
}

// ═══ INIT ═══
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadDashboard();
    
    document.getElementById('themeToggle')?.addEventListener('click', toggleTheme);
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString([], { weekday: 'long', day: 'numeric', month: 'long' });
    
    // Auto-refresh every 2 minutes
    setInterval(loadDashboard, 120000);
});
