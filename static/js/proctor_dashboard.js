/* ═══════════════════════════════════════════════════════════════════════════
   AURA — Proctor Dashboard JavaScript
   Premium, accessible, production-ready with proper error handling
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── Configuration ──
    const CONFIG = {
        REFRESH_INTERVAL: 60000,
        TOAST_DURATION: 3500,
        COUNT_ANIM_FIRST: 800,
        COUNT_ANIM_NORMAL: 400,
        MAX_TABLE_ROWS: 15,
        MAX_LIST_ITEMS: 8,
        STAGGER_DELAY: 0.05,
        ENDPOINTS: {
            summary:    '/proctor/api/dashboard/summary',
            students:   '/proctor/api/my-students',
            riskQueue:  '/proctor/api/risk/queue',
            grievances: '/proctor/api/grievances',
            activity:   '/proctor/api/activity-logs?days=7',
            addStudent: '/proctor/api/student/add',
        }
    };

    // ── State ──
    let isFirstLoad = true;
    let refreshTimer = null;
    let isRefreshing = false;

    // ── DOM Cache ──
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ── Utility: HTML Escaping (XSS prevention) ──
    const _escDiv = document.createElement('div');
    function esc(text) {
        _escDiv.textContent = text ?? '';
        return _escDiv.innerHTML;
    }

    // ── Toast Notification ──
    function showToast(msg, type = 'info') {
        const t = $('#pd-toast');
        if (!t) return;
        t.textContent = msg;
        t.className = `pd-toast is-${type} is-visible`;
        clearTimeout(t._timer);
        t._timer = setTimeout(() => t.classList.remove('is-visible'), CONFIG.TOAST_DURATION);
    }

    // ── Count-Up Animation ──
    function animateCount(el, target, duration) {
        if (!el) return;
        const start = parseInt(el.textContent) || 0;
        if (start === target) { el.textContent = target; return; }
        const range = target - start;
        const t0 = performance.now();
        function tick(now) {
            const p = Math.min((now - t0) / duration, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(start + range * eased);
            if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    // ── Stagger Animation Delays ──
    function applyRowDelays(container) {
        if (!container) return;
        const items = container.querySelectorAll('tr, .pd-list-item');
        items.forEach((item, i) => {
            item.style.animationDelay = `${i * CONFIG.STAGGER_DELAY}s`;
        });
    }

    // ── Get Initial ──
    function getInitial(name) {
        return esc((name || 'S').charAt(0).toUpperCase());
    }

    // ── Relative Time ──
    function timeAgo(dateStr) {
        if (!dateStr) return '';
        const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return new Date(dateStr).toLocaleDateString();
    }

    // ═══ RENDER: Alerts Table ═══
    function renderAlerts(students) {
        const body = $('#pd-alertsBody');
        const badge = $('#pd-alertsBadge');
        if (!body || !badge) return;

        const high = (students || []).filter(s => (s.risk_level || '').toUpperCase() === 'HIGH' || s.status === 'needs_intervention');
        badge.textContent = high.length;

        if (!high.length) {
            body.innerHTML = `<tr><td colspan="4"><div class="pd-empty"><i class="fas fa-shield-alt" aria-hidden="true"></i><p>No high-risk alerts</p></div></td></tr>`;
            badge.classList.remove('has-items');
            return;
        }

        badge.classList.add('has-items');
        body.innerHTML = high.map(s => `
            <tr>
                <td>
                    <div class="pd-student-cell">
                        <div class="pd-avatar is-high" aria-hidden="true">${getInitial(s.name)}</div>
                        <span class="pd-student-name">${esc(s.name || 'Student')}</span>
                    </div>
                </td>
                <td><strong style="color:var(--p-danger)">${esc(String(s.current_stress || 0))}</strong></td>
                <td><span class="pd-risk-pill is-high"><i class="fas fa-arrow-up" aria-hidden="true"></i> HIGH</span></td>
                <td><button class="pd-view-btn" data-student-id="${esc(s.anonymous_id)}" aria-label="View student ${esc(s.name || '')}"><i class="fas fa-eye" aria-hidden="true"></i> View</button></td>
            </tr>
        `).join('');
        applyRowDelays(body);
    }

    // ═══ RENDER: Students Table ═══
    function renderStudents(students) {
        const body = $('#pd-studentsBody');
        const badge = $('#pd-studentsBadge');
        if (!body || !badge) return;

        const data = students || [];
        badge.textContent = data.length;

        if (!data.length) {
            body.innerHTML = `<tr><td colspan="3"><div class="pd-empty"><i class="fas fa-users" aria-hidden="true"></i><p>No students assigned</p></div></td></tr>`;
            badge.classList.remove('has-items');
            return;
        }

        badge.classList.add('has-items');
        body.innerHTML = data.slice(0, CONFIG.MAX_TABLE_ROWS).map(s => {
            const level = (s.risk_level || 'low').toLowerCase();
            return `
                <tr>
                    <td>
                        <div class="pd-student-cell">
                            <div class="pd-avatar is-${esc(level)}" aria-hidden="true">${getInitial(s.name)}</div>
                            <span class="pd-student-name">${esc(s.name || 'Student')}</span>
                        </div>
                    </td>
                    <td><span class="pd-risk-pill is-${esc(level)}">${esc(level.toUpperCase())}</span></td>
                    <td><button class="pd-view-btn" data-student-id="${esc(s.anonymous_id)}" aria-label="View student ${esc(s.name || '')}"><i class="fas fa-eye" aria-hidden="true"></i> View</button></td>
                </tr>
            `;
        }).join('');
        applyRowDelays(body);
    }

    // ═══ RENDER: Risk Queue ═══
    function renderRiskQueue(incidents) {
        const el = $('#pd-riskQueueList');
        const badge = $('#pd-riskBadge');
        if (!el || !badge) return;

        const data = incidents || [];
        badge.textContent = data.length;

        if (!data.length) {
            el.innerHTML = `<div class="pd-empty"><i class="fas fa-check-circle" aria-hidden="true"></i><p>No incidents in queue</p></div>`;
            badge.classList.remove('has-items');
            return;
        }

        badge.classList.add('has-items');
        el.innerHTML = data.slice(0, CONFIG.MAX_LIST_ITEMS).map(inc => {
            const level = (inc.risk_level || 'medium').toLowerCase();
            const isDanger = level === 'high';
            return `
                <div class="pd-list-item" role="listitem">
                    <div class="pd-list-icon" style="background:var(--p-${isDanger ? 'danger' : 'warning'}-light);color:var(--p-${isDanger ? 'danger' : 'warning'})">
                        <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
                    </div>
                    <div class="pd-list-content">
                        <div class="pd-list-title">${esc(inc.anonymous_student_id || inc.incident_type || 'Incident')}</div>
                        <div class="pd-list-sub">${esc((inc.status || 'UNREVIEWED').replace(/_/g, ' '))} &bull; ${inc.time_since_trigger || timeAgo(inc.timestamp)}</div>
                    </div>
                    <div class="pd-list-right"><span class="pd-risk-pill is-${esc(level)}">${esc(level.toUpperCase())}</span></div>
                </div>
            `;
        }).join('');
        applyRowDelays(el);
    }

    // ═══ RENDER: Grievances ═══
    function renderGrievances(tickets) {
        const el = $('#pd-grievancesList');
        const badge = $('#pd-grievanceBadge');
        if (!el || !badge) return;

        const data = tickets || [];
        const pending = data.filter(t => (t.status || 'pending') === 'pending').length;
        badge.textContent = pending || data.length;

        if (!data.length) {
            el.innerHTML = `<div class="pd-empty"><i class="fas fa-check-circle" aria-hidden="true"></i><p>No grievances submitted</p></div>`;
            badge.classList.remove('has-items');
            return;
        }

        badge.classList.add('has-items');
        el.innerHTML = data.slice(0, CONFIG.MAX_LIST_ITEMS).map(t => {
            const st = (t.status || 'pending').toLowerCase();
            const isPending = st === 'pending';
            const colorClass = isPending ? 'warning' : (st === 'resolved' ? 'success' : 'info');
            const subject = t.subject || t.description?.substring(0, 50) || 'Grievance';
            const anon = t.anonymous_id || '—';
            return `
                <div class="pd-list-item" role="listitem">
                    <div class="pd-list-icon" style="background:var(--p-${colorClass}-light);color:var(--p-${colorClass})">
                        <i class="fas fa-file-alt" aria-hidden="true"></i>
                    </div>
                    <div class="pd-list-content">
                        <div class="pd-list-title">${esc(subject)}</div>
                        <div class="pd-list-sub">${esc(anon)} &bull; ${t.time_ago || timeAgo(t.created_at)}</div>
                    </div>
                    <div class="pd-list-right"><span class="pd-risk-pill is-${esc(st)}">${esc(st.replace('_', ' ').toUpperCase())}</span></div>
                </div>
            `;
        }).join('');
        applyRowDelays(el);
    }

    // ═══ RENDER: Activity Log ═══
    const ACTIVITY_ICONS = {
        'LOGIN':              { icon: 'sign-in-alt',       bg: 'info',    color: 'info' },
        'LOGOUT':             { icon: 'sign-out-alt',      bg: 'info',    color: 'info' },
        'ADD_STUDENT':        { icon: 'user-plus',         bg: 'success', color: 'success' },
        'REMOVE_STUDENT':     { icon: 'user-minus',        bg: 'danger',  color: 'danger' },
        'REVIEW_INCIDENT':    { icon: 'search',            bg: 'primary', color: 'primary' },
        'DISMISS_INCIDENT':   { icon: 'times-circle',      bg: 'warning', color: 'warning' },
        'ESCALATE_INCIDENT':  { icon: 'arrow-up',          bg: 'danger',  color: 'danger' },
        'CLOSE_INCIDENT':     { icon: 'check-circle',      bg: 'success', color: 'success' },
        'CONTACT_STUDENT':    { icon: 'envelope',          bg: 'info',    color: 'info' },
        'MONITOR_STUDENT':    { icon: 'eye',               bg: 'warning', color: 'warning' },
        'CASE_STATUS_CHANGE': { icon: 'exchange-alt',      bg: 'warning', color: 'warning' },
        'ASSIGN_COUNSELOR':   { icon: 'user-tag',          bg: 'info',    color: 'info' },
        'BULK_ACTION':        { icon: 'layer-group',       bg: 'primary', color: 'primary' },
        'ADD_NOTE':           { icon: 'sticky-note',       bg: 'primary', color: 'primary' },
        'UPDATE_TICKET':      { icon: 'ticket-alt',        bg: 'warning', color: 'warning' },
    };

    function renderActivity(logs) {
        const el = $('#pd-activityList');
        if (!el) return;

        const data = logs || [];
        if (!data.length) {
            el.innerHTML = `<div class="pd-empty"><i class="fas fa-inbox" aria-hidden="true"></i><p>No recent activity</p></div>`;
            return;
        }

        el.innerHTML = data.slice(0, CONFIG.MAX_TABLE_ROWS).map(log => {
            const m = ACTIVITY_ICONS[log.action] || { icon: 'circle', bg: 'gray-100', color: 'gray-500' };
            const label = esc((log.action || 'ACTION').replace(/_/g, ' '));
            const meta = log.metadata?.email || log.metadata?.student_email || log.metadata?.anonymous_student_id
                ? `${esc(log.metadata.email || log.metadata.student_email || log.metadata.anonymous_student_id)} &bull; ` : '';
            return `
                <div class="pd-list-item" role="listitem">
                    <div class="pd-list-icon" style="background:var(--p-${m.bg}-light, var(--p-gray-100));color:var(--p-${m.color}, var(--p-gray-500))">
                        <i class="fas fa-${esc(m.icon)}" aria-hidden="true"></i>
                    </div>
                    <div class="pd-list-content">
                        <div class="pd-list-title">${label}</div>
                        <div class="pd-list-sub">${meta}${timeAgo(log.timestamp)}</div>
                    </div>
                </div>
            `;
        }).join('');
        applyRowDelays(el);
    }

    // ═══ SHOW ERROR STATE ═══
    function showErrorState(containerSel, message) {
        const el = $(containerSel);
        if (!el) return;
        el.innerHTML = `
            <div class="pd-error-state">
                <i class="fas fa-exclamation-circle" aria-hidden="true"></i>
                <p>${esc(message || 'Failed to load data')}</p>
                <button type="button" onclick="window.__pdRefresh()">Retry</button>
            </div>
        `;
    }

    // ═══ MAIN DATA LOADER ═══
    async function loadDashboard() {
        if (isRefreshing) return;
        isRefreshing = true;

        try {
            const results = await Promise.allSettled([
                fetch(CONFIG.ENDPOINTS.summary).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
                fetch(CONFIG.ENDPOINTS.students).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
                fetch(CONFIG.ENDPOINTS.riskQueue).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
                fetch(CONFIG.ENDPOINTS.grievances).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
                fetch(CONFIG.ENDPOINTS.activity).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
            ]);

            const [summaryRes, studentsRes, queueRes, grievancesRes, activityRes] = results;
            const animDuration = isFirstLoad ? CONFIG.COUNT_ANIM_FIRST : CONFIG.COUNT_ANIM_NORMAL;

            // Summary stats
            if (summaryRes.status === 'fulfilled') {
                const s = summaryRes.value.data || {};
                const critical = s.needs_action || 0;
                animateCount($('#pd-criticalCount'), critical, animDuration);
                animateCount($('#pd-pendingCount'), s.pending_followups || 0, animDuration);
                animateCount($('#pd-studentCount'), s.my_students || 0, animDuration);
                animateCount($('#pd-resolvedCount'), s.resolved_today || 0, animDuration);

                const dangerCard = $('.pd-stat.is-danger');
                if (dangerCard) dangerCard.classList.toggle('has-critical', critical > 0);
            } else {
                showToast('Failed to load summary', 'error');
            }

            // Students + Alerts
            if (studentsRes.status === 'fulfilled') {
                const data = studentsRes.value.data || [];
                renderAlerts(data);
                renderStudents(data);
            } else {
                showErrorState('#pd-alertsBody', 'Failed to load alerts');
                showErrorState('#pd-studentsBody', 'Failed to load students');
            }

            // Risk queue
            if (queueRes.status === 'fulfilled') {
                renderRiskQueue(queueRes.value.data || []);
            } else {
                showErrorState('#pd-riskQueueList', 'Failed to load risk queue');
            }

            // Grievances
            if (grievancesRes.status === 'fulfilled') {
                const gd = grievancesRes.value;
                renderGrievances(gd.grievances || gd.data || gd.tickets || []);
            } else {
                showErrorState('#pd-grievancesList', 'Failed to load grievances');
            }

            // Activity
            if (activityRes.status === 'fulfilled') {
                renderActivity(activityRes.value.data || []);
            } else {
                showErrorState('#pd-activityList', 'Failed to load activity');
            }

            isFirstLoad = false;
        } catch (err) {
            showToast('Network error — retrying in 60s', 'error');
        } finally {
            isRefreshing = false;
        }
    }

    // ═══ NAVIGATION ═══
    function viewStudent(id) {
        if (id) window.location.href = '/proctor/student/' + encodeURIComponent(id);
    }

    // ═══ MODAL CONTROLS ═══
    function openModal() {
        const modal = $('#pd-addModal');
        if (!modal) return;
        modal.classList.add('is-active');
        // Focus trap: focus first input
        const firstInput = modal.querySelector('input');
        if (firstInput) setTimeout(() => firstInput.focus(), 100);
    }

    function closeModal() {
        const modal = $('#pd-addModal');
        if (!modal) return;
        modal.classList.remove('is-active');
        // Return focus to trigger button
        const trigger = $('[data-action="open-modal"]');
        if (trigger) trigger.focus();
    }

    // ═══ ADD STUDENT ═══
    async function handleAddStudent(e) {
        e.preventDefault();
        const btn = e.target.querySelector('.pd-submit-btn');

        const emailInput      = $('#pd-studentEmail');
        const rollInput       = $('#pd-studentRoll');
        const nameInput       = $('#pd-studentName');
        const deptInput       = $('#pd-studentDept');
        const semInput        = $('#pd-studentSem');
        const parentNameInput = $('#pd-parentName');
        const parentPhoneInput= $('#pd-parentPhone');
        const parentEmailInput= $('#pd-parentEmail');

        if (!emailInput || !rollInput || !nameInput || !deptInput || !parentNameInput || !parentPhoneInput) {
            showToast('Form elements missing', 'error');
            return;
        }

        // Client-side validation
        const phone = parentPhoneInput.value.trim();
        if (phone && !/^\d{10}$/.test(phone)) {
            showToast('Parent phone must be 10 digits', 'error');
            parentPhoneInput.focus();
            return;
        }

        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...'; }

        try {
            const res = await fetch(CONFIG.ENDPOINTS.addStudent, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email:               emailInput.value.trim(),
                    roll_number:         rollInput.value.trim(),
                    name:                nameInput.value.trim(),
                    department:          deptInput ? deptInput.value.trim() : '',
                    semester:            semInput ? semInput.value : '4',
                    parent_name:         parentNameInput.value.trim(),
                    parent_phone:        phone,
                    parent_email:        parentEmailInput ? parentEmailInput.value.trim() : '',
                })
            });

            if (res.ok) {
                showToast('Student added successfully!', 'success');
                closeModal();
                e.target.reset();
                loadDashboard();
            } else {
                const d = await res.json().catch(() => ({}));
                showToast(d.error || 'Failed to add student', 'error');
            }
        } catch {
            showToast('Network error — please try again', 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-plus"></i> Add Student'; }
        }
    }

    // ═══ REFRESH ═══
    async function refreshData() {
        const btn = $('[data-action="refresh"]');
        if (btn) btn.classList.add('is-spinning');
        showToast('Refreshing…', 'info');
        await loadDashboard();
        if (btn) btn.classList.remove('is-spinning');
        showToast('Dashboard updated', 'success');
    }

    // ═══ KEYBOARD HANDLERS ═══
    function handleKeyboard(e) {
        // ESC closes modal
        if (e.key === 'Escape') {
            const modal = $('#pd-addModal');
            if (modal && modal.classList.contains('is-active')) {
                closeModal();
            }
        }
    }

    // ═══ EVENT DELEGATION ═══
    function handleClick(e) {
        const viewBtn = e.target.closest('.pd-view-btn');
        if (viewBtn) {
            const id = viewBtn.dataset.studentId;
            if (id) viewStudent(id);
            return;
        }

        const action = e.target.closest('[data-action]');
        if (action) {
            switch (action.dataset.action) {
                case 'refresh':    refreshData(); break;
                case 'open-modal': openModal(); break;
                case 'close-modal': closeModal(); break;
            }
        }
    }

    // Close modal on overlay click
    function handleOverlayClick(e) {
        if (e.target.classList.contains('pd-modal-overlay')) {
            closeModal();
        }
    }

    // ═══ INIT ═══
    function init() {
        // Event listeners (delegation)
        document.addEventListener('click', handleClick);
        document.addEventListener('click', handleOverlayClick);
        document.addEventListener('keydown', handleKeyboard);

        // Form submission
        const addForm = $('#pd-addForm');
        if (addForm) addForm.addEventListener('submit', handleAddStudent);

        // Load data
        loadDashboard();

        // Auto-refresh (with guard against overlap via isRefreshing flag)
        refreshTimer = setInterval(loadDashboard, CONFIG.REFRESH_INTERVAL);

        // Expose refresh for error state retry buttons
        window.__pdRefresh = refreshData;
    }

    // Boot
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
