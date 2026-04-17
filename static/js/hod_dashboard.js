// ═══ STATE ═══
const DASHBOARD_STATE = {
    stats: {},
    riskOversight: [],
    proctors: [],
    students: [],
    trends: {},
    currentTheme: localStorage.getItem('aura-theme') || 'light',
    filterLevel: 'ALL',
    lastHighRiskCount: 0,
    activeStudent: null,
    communityFeedback: []
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

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
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

        const [stats, riskBox, distribution, trends, performance, students, proctors, feedback] = await Promise.all(
            endpoints.concat(['/proctor/api/hod/community-feedback']).map(e => fetch(e, {credentials: 'include'}).then(async r => {
                const isJson = r.headers.get('content-type')?.includes('application/json');
                if (isJson) {
                    return r.json();
                } else {
                    console.warn(`Endpoint ${e} returned non-JSON`);
                    return { success: false, error: 'Non-JSON response' };
                }
            }).catch(err => {
                console.error(`Fetch failed for ${e}`, err);
                return { success: false };
            }))
        );

        if (stats.success) renderStats(stats.data);
        if (riskBox.success) renderRiskOversight(riskBox.data);
        if (distribution.success) renderDistribution(distribution.data);
        if (trends.success) renderTrends(trends.data);
        if (performance.success) renderProctorPerformance(performance.data);
        if (students.success) {
            DASHBOARD_STATE.students = students.data;
            renderStudents(DASHBOARD_STATE.students);
        }
        if (riskBox.success) {
            DASHBOARD_STATE.riskOversight = riskBox.data;
            renderRiskOversight(DASHBOARD_STATE.riskOversight);
        }
        if (proctors.success) renderProctors(proctors.data);
        if (feedback.success) {
            DASHBOARD_STATE.communityFeedback = feedback.data;
            renderCommunityFeedback(DASHBOARD_STATE.communityFeedback);
        }

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
    
    if (data.high_risk_incidents > DASHBOARD_STATE.lastHighRiskCount && DASHBOARD_STATE.lastHighRiskCount !== 0) {
        showToast('🚨 New Critical Alert Detected!', 'error');
    }
    DASHBOARD_STATE.lastHighRiskCount = data.high_risk_incidents;

    if (critCard) {
        if (data.high_risk_incidents > 0) critCard.classList.add('has-critical');
        else critCard.classList.remove('has-critical');
    }
}

function renderRiskOversight(data) {
    const body = document.getElementById('riskOversightBody');
    const count = document.getElementById('riskOversightCount');
    if (!body) return;
    
    let displayData = data;
    if (DASHBOARD_STATE.filterLevel !== 'ALL') {
        const checkLevel = DASHBOARD_STATE.filterLevel === 'LOW' ? 'STABLE' : DASHBOARD_STATE.filterLevel; 
        displayData = displayData.filter(inc => {
            const risk = (inc.risk_level || 'STABLE').toUpperCase();
            // Normalize LOW to STABLE for matching
            const normalizedRisk = risk === 'LOW' ? 'STABLE' : risk;
            return normalizedRisk === checkLevel;
        });
    }
    
    if (count) count.textContent = displayData.length;
    
    if (displayData.length === 0) {
        body.innerHTML = '<tr><td colspan="5"><div class="empty-state-block"><i class="fas fa-shield-alt"></i><p>No active critical alerts for this view.</p></div></td></tr>';
        return;
    }

    body.innerHTML = displayData.map(inc => {
        const time = new Date(inc.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const riskLevel = (inc.risk_level || 'STABLE').toUpperCase();
        const riskClass = riskLevel === 'HIGH' ? 'high' : (riskLevel === 'MEDIUM' ? 'medium' : 'low');
        const statusClass = inc.status === 'ESCALATED' ? 'high' : (inc.status === 'UNREVIEWED' ? 'medium' : '');
        
        return `
            <tr class="clickable-row fade-in" onclick="openStudentDetails('${esc(inc.anonymous_student_id)}')">
                <td><strong>${esc(inc.anonymous_student_id)}</strong></td>
                <td><span class="tag ${riskClass}">${esc(riskLevel)}</span></td>
                <td><span style="font-size: 0.82rem; color: var(--text-muted)">${esc(inc.trigger_source)}</span></td>
                <td><span class="tag ${statusClass}">${esc(inc.status)}</span></td>
                <td style="color: var(--text-muted); font-size: 0.82rem;">${time}</td>
            </tr>
        `;
    }).join('');
}

function renderStudents(data) {
    const body = document.getElementById('studentHubBody');
    if (!body) return;

    let displayData = data;
    if (DASHBOARD_STATE.filterLevel !== 'ALL') {
        const checkLevel = DASHBOARD_STATE.filterLevel === 'LOW' ? 'STABLE' : DASHBOARD_STATE.filterLevel;
        displayData = displayData.filter(s => {
            const risk = (s.risk_level || 'STABLE').toUpperCase();
            const normalizedRisk = risk === 'LOW' ? 'STABLE' : risk;
            return normalizedRisk === checkLevel;
        });
    }

    if (displayData.length === 0) {
        body.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 40px;">No students records found for this view.</td></tr>';
        return;
    }

    body.innerHTML = displayData.map(s => {
        const riskLevel = (s.risk_level || 'STABLE').toUpperCase();
        return `
            <tr class="clickable-row fade-in" onclick="openStudentDetails('${esc(s.anonymous_id)}')">
                <td><code>${esc(s.anonymous_id)}</code></td>
                <td><strong>${esc(s.name)}</strong></td>
                <td>${esc(s.department)}</td>
                <td><span class="proctor-name">${esc(s.proctor_id || 'unassigned')}</span></td>
                <td><span class="tag ${riskLevel.toLowerCase()}">${esc(riskLevel)}</span></td>
            </tr>
        `;
    }).join('');
}

function filterStudents() {
    const q = document.getElementById('studentSearch').value.toLowerCase();
    const filtered = DASHBOARD_STATE.students.filter(s => 
        (s.name || '').toLowerCase().includes(q) || 
        (s.roll_number || '').toLowerCase().includes(q) || 
        (s.anonymous_id || '').toLowerCase().includes(q)
    );
    renderStudents(filtered);
}

function renderCommunityFeedback(data) {
    const parentList = document.getElementById('parentFeedbackList');
    const studentList = document.getElementById('studentFeedbackList');
    if (!parentList || !studentList) return;

    const parents = (data || []).filter(item => item.source === 'Parent');
    const students = (data || []).filter(item => item.source === 'Student');

    parentList.innerHTML = parents.length ? parents.map(item => renderFeedbackItem(item)).join('') : '<div class="empty-state-block"><i class="fas fa-comments"></i><p>No parent suggestions recorded yet.</p></div>';
    studentList.innerHTML = students.length ? students.map(item => renderFeedbackItem(item)).join('') : '<div class="empty-state-block"><i class="fas fa-graduation-cap"></i><p>No student grievances or feedback recorded yet.</p></div>';
}

function renderFeedbackItem(item) {
    const date = new Date(item.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    const typeClass = item.type === 'SUGGESTION' ? 'sug-tag' : 'grv-tag';
    const sourceIcon = item.source === 'Parent' ? 'fa-user-tie' : 'fa-user-graduate';
    
    return `
        <div class="feedback-item fade-in">
            <div class="feedback-header">
                <span class="feedback-type ${typeClass}">${esc(item.type)}</span>
                <span class="feedback-source"><i class="fas ${sourceIcon}"></i> ${esc(item.source)}: ${esc(item.author)}</span>
                <span class="feedback-time">${date}</span>
            </div>
            <div class="feedback-body">
                <h4 class="feedback-title">${esc(item.title)}</h4>
                <p class="feedback-text">${esc(item.text)}</p>
            </div>
            <div class="feedback-footer">
                <span class="feedback-student">About Student: <strong>${esc(item.student)}</strong></span>
                <span class="feedback-status status-${item.status.toLowerCase()}">${esc(item.status)}</span>
            </div>
        </div>
    `;
}

function renderProctorPerformance(data) {
    const container = document.getElementById('proctorPerformanceTable');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="empty-state-block"><i class="fas fa-chart-line"></i><p>No proctor activity recorded this week.</p></div>';
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
                            <td><span class="tag ${ratio > 50 ? 'high' : ratio > 25 ? 'medium' : 'low'}">${ratio}% Esc.</span></td>
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
        container.innerHTML = '<div class="empty-state-block"><i class="fas fa-user-tie"></i><p>No proctors assigned to department.</p></div>';
        return;
    }

    container.innerHTML = data.map(p => `
        <div class="proctor-item">
            <div class="proctor-info">
                <span class="p-name">${esc(p.name)}</span>
                <span class="p-email">${esc(p.email)}</span>
            </div>
            <button class="remove-btn" onclick="removeProctor('${p.email}')" title="Remove proctor">
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
            credentials: 'include',
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
            // Log it visibly so we know what happened
            console.error("Proctor Add Error:", data.error);
        }
    } catch (err) {
        showToast('System error. Please try again.', 'error');
        console.error("System error on submitProctor", err);
    }
}

async function removeProctor(email) {
    if (!confirm(`Are you sure you want to remove proctor ${email}? They will immediately lose access to their dashboard.`)) return;

    try {
        const res = await fetch(`/proctor/api/hod/manage-proctors/${encodeURIComponent(email)}`, {
            method: 'DELETE',
            credentials: 'include',
            headers: { 'X-CSRF-Token': getCsrfToken() }
        });
        const data = await res.json();

        if (data.success) {
            showToast('Proctor removed successfully!', 'success');
            loadDashboard(); // Refresh the list
        } else {
            showToast(data.error || 'Failed to remove proctor', 'error');
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

function switchSubTab(evt, tabId) {
    const containers = document.getElementsByClassName("sub-feedback-content");
    for (let i = 0; i < containers.length; i++) {
        containers[i].classList.remove("active");
    }

    const btns = document.getElementsByClassName("sub-tab-btn");
    for (let i = 0; i < btns.length; i++) {
        btns[i].classList.remove("active");
    }

    document.getElementById(tabId).classList.add("active");
    evt.currentTarget.classList.add("active");
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
        chart: { 
            type: 'donut', 
            height: 320,
            events: {
                dataPointSelection: function(event, chartContext, config) {
                    const mappedStates = ['LOW', 'MEDIUM', 'HIGH'];
                    const level = mappedStates[config.dataPointIndex];
                    if(level) {
                        filterDashboard(level);
                        const rosterTabBtn = document.querySelectorAll('.tab-link')[1];
                        if (rosterTabBtn) switchTab({ currentTarget: rosterTabBtn }, 'student-roster');
                    }
                }
            }
        },
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
    const pct = Math.round(count / (total || 1) * 100);
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
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
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
    setInterval(loadDashboard, 30000); // Poll every 30s for real-time vibe
});

// ═══ PRODUCTIVITY & INTERACTION ═══
function filterDashboard(level) {
    DASHBOARD_STATE.filterLevel = level;
    renderRiskOversight(DASHBOARD_STATE.riskOversight);
    renderStudents(DASHBOARD_STATE.students);
    showToast(`Filtered by ${level === 'ALL' ? 'All' : level + ' Risk'}`, 'success');
}

let sortDirections = { riskOversightBody: [], studentHubBody: [] };
function sortTable(tbodyId, colIndex) {
    const tbody = document.getElementById(tbodyId);
    let rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length === 0 || rows[0].querySelector('td[colspan]')) return;

    if (!sortDirections[tbodyId]) sortDirections[tbodyId] = [];
    let isAsc = sortDirections[tbodyId][colIndex] === true;
    sortDirections[tbodyId][colIndex] = !isAsc;

    rows.sort((a, b) => {
        let valA = a.children[colIndex].textContent.trim();
        let valB = b.children[colIndex].textContent.trim();
        
        const riskWeights = { 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'STABLE': 1 };
        if (riskWeights[valA.toUpperCase()] && riskWeights[valB.toUpperCase()]) {
            valA = riskWeights[valA.toUpperCase()];
            valB = riskWeights[valB.toUpperCase()];
        } else if (!isNaN(valA) && !isNaN(valB)) {
            valA = parseFloat(valA); valB = parseFloat(valB);
        }

        if (valA < valB) return isAsc ? -1 : 1;
        if (valA > valB) return isAsc ? 1 : -1;
        return 0;
    });

    tbody.innerHTML = '';
    rows.forEach(r => tbody.appendChild(r));
    showToast('Table sorted');
}

function openStudentDetails(uid) {
    const student = DASHBOARD_STATE.students.find(s => s.anonymous_id === uid || s.uid === uid) 
                    || DASHBOARD_STATE.riskOversight.find(s => s.anonymous_student_id === uid);
                    
    if (!student) return;

    const name = student.name || 'Anonymous Student';
    const anonId = student.anonymous_id || student.anonymous_student_id || uid;

    document.getElementById('sdName').textContent = name;
    document.getElementById('sdUid').textContent = anonId;
    document.getElementById('sdDept').textContent = student.department || 'General';
    document.getElementById('sdProctor').textContent = student.proctor_id || 'Not Assigned';
    
    const risk = student.risk_level || 'STABLE';
    document.getElementById('sdRisk').className = `student-stat-val tag ${risk.toLowerCase()}`;
    document.getElementById('sdRisk').textContent = risk;

    const timeline = document.getElementById('sdTimeline');
    if (student.trigger_source) {
        timeline.innerHTML = `<strong>Latest Incident:</strong> ${student.trigger_source} <br> <small style="color: var(--text-faint)">Status: ${student.status || 'Active'}</small>`;
    } else {
        timeline.innerHTML = 'No recent critical incidents recorded.';
    }

    DASHBOARD_STATE.activeStudent = student;
    document.getElementById('studentDetailsModal').classList.add('visible');
}

async function escalateStudent() {
    const student = DASHBOARD_STATE.activeStudent;
    if (!student) return;

    if (!confirm(`Are you sure you want to escalate student ${student.anonymous_id || student.anonymous_student_id} for critical counseling?`)) return;

    try {
        const res = await fetch('/proctor/api/hod/escalate-student', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({ 
                anonymous_id: student.anonymous_id || student.anonymous_student_id,
                reason: 'HOD Executive Escalation'
            })
        });
        const data = await res.json();

        if (data.success) {
            showToast('Student escalated successfully!', 'success');
            hideModal('studentDetailsModal');
            loadDashboard();
        } else {
            showToast(data.error || 'Escalation failed', 'error');
        }
    } catch (err) {
        showToast('System error during escalation', 'error');
    }
}

async function messageProctor() {
    const student = DASHBOARD_STATE.activeStudent;
    if (!student) return;

    const proctorId = student.proctor_id;
    if (!proctorId || proctorId === 'Unassigned') {
        showToast('No proctor assigned to this student', 'error');
        return;
    }

    const msg = prompt(`Enter message for Proctor ${proctorId}:`, `Please review student ${student.anonymous_id || student.anonymous_student_id} immediately.`);
    if (!msg) return;

    try {
        const res = await fetch('/proctor/api/hod/message-proctor', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
            body: JSON.stringify({
                proctor_id: proctorId,
                anonymous_id: student.anonymous_id || student.anonymous_student_id,
                message: msg
            })
        });
        const data = await res.json();

        if (data.success) {
            showToast('Message sent to proctor', 'success');
        } else {
            showToast(data.error || 'Failed to send message', 'error');
        }
    } catch (err) {
        showToast('System error while messaging', 'error');
    }
}

function exportDashboardCSV() {
    let csvContent = "data:text/csv;charset=utf-8,UID,Name,Department,Proctor,Risk Level\n";
    let dataToExport = DASHBOARD_STATE.students;
    if (DASHBOARD_STATE.filterLevel !== 'ALL') {
        const checkLevel = DASHBOARD_STATE.filterLevel === 'LOW' ? 'STABLE' : DASHBOARD_STATE.filterLevel;
        dataToExport = dataToExport.filter(s => (s.risk_level || '').toUpperCase() === checkLevel);
    }
    
    dataToExport.forEach(s => {
        let row = `${s.anonymous_id || ''},${s.name || ''},${s.department || ''},${s.proctor_id || ''},${s.risk_level || ''}`;
        csvContent += row + "\r\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `AURA_Oversight_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Exporting Filtered CSV...', 'success');
}
