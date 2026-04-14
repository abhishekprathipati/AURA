// HTML escape helper to prevent XSS
function esc(s) {
    const d = document.createElement('div');
    d.textContent = s ?? '';
    return d.innerHTML;
}

// CSRF token for POST requests
const _csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
function secureHeaders(extra = {}) {
    return { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken, ...extra };
}

// Rolling average calculation for trend analysis
function rollingAverage(values, window = 7) {
    return values.map((_, i) => {
        const start = Math.max(0, i - window + 1);
        const slice = values.slice(start, i + 1);
        const sum = slice.reduce((a, b) => a + b, 0);
        return Math.round(sum / slice.length);
    });
}

// Compute trend from rolling average slope
function computeTrend(avgSeries) {
    if (!avgSeries || avgSeries.length < 2) {
        return { icon: "→", label: "Stable" };
    }

    const last = avgSeries[avgSeries.length - 1];
    const prev = avgSeries[avgSeries.length - 2];

    if (last == null || prev == null) {
        return { icon: "→", label: "Stable" };
    }

    const delta = last - prev;

    if (delta >= 1.0) return { icon: "↑", label: "Worsening" };
    if (delta <= -1.0) return { icon: "↓", label: "Improving" };
    return { icon: "→", label: "Stable" };
}

// Compute dynamic Y-axis bounds from data values
function computeYAxisBounds(values) {
    if (!values.length) return { min: 0, max: 10 };

    const min = values.reduce((a, b) => Math.min(a, b), Infinity);
    const max = values.reduce((a, b) => Math.max(a, b), -Infinity);

    if (min === max) {
        return {
            min: Math.max(0, min - 2),
            max: min + 2
        };
    }

    const padding = Math.max(1, Math.round((max - min) * 0.2));
    return {
        min: Math.max(0, min - padding),
        max: max + padding
    };
}

// Pass-through: no artificial noise on real data
function injectStressVariance(values, maxSpike = 6) {
    return values;
}

// Auto-refresh controller
let autoRefreshTimer = null;

class AdvancedDashboard {
    constructor() {
        this.currentStress = 0;
        this.stressHistory = [];
        this.moodHistory = [];
        this.isLoading = false;
        this.modals = {};
        this.charts = {};
        this.init();
    }

    async init() {
        this.initDate();
        this.initTheme();
        this.initNavigation();
        this.initModals();

        // Load data BEFORE initializing charts to prevent rendering with zeros
        await this.loadDashboardData();

        // Charts only initialize after data is ready
        this.initCharts();

        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.setupServiceWorker();

        // New sections
        this.loadProfile();
        this.initWellnessGoals();
        this.loadDailyTip();
        this.initJournal();
        this.initGrievanceForm();
        
        // Phase 5.2: Stress Forecasting
        this.loadStressForecast();

        // Phase 5.3: Burnout Analysis
        this.loadBurnoutAnalysis();
    }

    initDate() {
        try {
            const now = luxon.DateTime.now();
            const dateElement = document.getElementById('currentDate');
            if (dateElement) {
                dateElement.textContent = now.toLocaleString({
                    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
                });
            }
            // Update timestamp once immediately, then via interval (guarded to run only once)
            if (!this._dateTimerSet) {
                this._dateTimerSet = true;
                this._dateTimer = setInterval(() => {
                    const now = luxon.DateTime.now();
                    const timeString = now.toLocaleString(luxon.DateTime.TIME_SIMPLE);
                    const relativeTime = now.toRelative();
                    const tsEl = document.getElementById('stressTimestamp');
                    if (tsEl) {
                        const span = tsEl.querySelector('span');
                        if (span) span.textContent = `${timeString} • ${relativeTime}`;
                    }
                }, 60000);
            }
        } catch (e) { console.warn('initDate error:', e); }
    }

    initTheme() {
        const themeToggle = document.getElementById('themeToggle');
        const savedTheme = localStorage.getItem('aura-ui-theme') || 'light';

        // Set initial theme
        this.setTheme(savedTheme);

        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const newTheme = current === 'dark' ? 'light' : 'dark';
                this.setTheme(newTheme);
                this.updateChartsTheme(newTheme);
            });
        }
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('aura-ui-theme', theme);

        // Clear any inline body background so CSS variables take effect immediately
        document.body.style.removeProperty('background');
        document.body.style.removeProperty('background-attachment');

        // Emit themechange event so color theme engine can re-apply
        window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));

        const icon = document.getElementById('themeIcon');
        if (!icon) return;

        // Sun icon (shown in dark mode — click to go light)
        const sunSVG = `<circle cx="12" cy="12" r="5"/>
               <line x1="12" y1="1" x2="12" y2="4"/>
               <line x1="12" y1="20" x2="12" y2="23"/>
               <line x1="4.22" y1="4.22" x2="6.34" y2="6.34"/>
               <line x1="17.66" y1="17.66" x2="19.78" y2="19.78"/>
               <line x1="1" y1="12" x2="4" y2="12"/>
               <line x1="20" y1="12" x2="23" y2="12"/>
               <line x1="4.22" y1="19.78" x2="6.34" y2="17.66"/>
               <line x1="17.66" y1="6.34" x2="19.78" y2="4.22"/>`;
        // Moon icon (shown in light mode — click to go dark)
        const moonSVG = `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`;

        icon.innerHTML = theme === 'dark' ? sunSVG : moonSVG;
        // Ensure SVG attributes are set (in case static HTML didn't include them)
        icon.setAttribute('fill', 'none');
        icon.setAttribute('stroke', 'currentColor');
        icon.setAttribute('stroke-width', '2');
        icon.setAttribute('stroke-linecap', 'round');
        icon.setAttribute('stroke-linejoin', 'round');
    }

    initCharts() {
        // At this point, data has already been loaded and stressHistory is populated
        // Charts render immediately with real data — no zero flash
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const foreColor = isDark ? '#cbd5e1' : '#64748b';
        const gridColor = isDark ? 'rgba(148,163,184,0.10)' : 'rgba(100,116,139,0.10)';
        const tooltipTheme = isDark ? 'dark' : 'light';

        this.charts.stress = new ApexCharts(document.getElementById('stressChart'), {
            series: [{ name: 'Stress Level', data: [] }, { name: '7-Day Average', data: [] }],
            chart: { type: 'area', height: 200, toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: true, speed: 800 }, foreColor: foreColor, background: 'transparent' },
            colors: ['#ef4444', '#10b981'],
            fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.7, opacityTo: 0.1, stops: [0, 90, 100] } },
            stroke: { width: [3, 3], curve: 'smooth', dashArray: [0, 0] },
            grid: { show: true, borderColor: gridColor, strokeDashArray: 3, xaxis: { lines: { show: false } }, yaxis: { lines: { show: true } }, padding: { left: 8, right: 8 } },
            xaxis: { labels: { show: true, style: { colors: foreColor, fontSize: '11px', fontFamily: 'Inter, sans-serif' } }, axisBorder: { show: false }, axisTicks: { show: false }, categories: [] },
            yaxis: { min: 0, max: 100, tickAmount: 5, labels: { show: true, style: { colors: foreColor, fontSize: '11px', fontFamily: 'Inter, sans-serif' }, formatter: v => Math.round(v) } },
            tooltip: {
                enabled: true,
                theme: tooltipTheme,
                style: { fontSize: '13px', fontFamily: 'Inter, sans-serif' },
                x: { show: true },
                y: {
                    formatter: (v) => {
                        if (v < 30) return `${v} – Low stress`;
                        if (v < 60) return `${v} – Moderate stress`;
                        if (v < 85) return `${v} – High stress`;
                        return `${v} – Critical`;
                    },
                    title: { formatter: () => 'Stress:' }
                }
            },
            annotations: {
                yaxis: [
                    {
                        y: 30,
                        borderColor: '#22c55e',
                        strokeDashArray: 4,
                        label: { text: 'Low', borderColor: '#22c55e', style: { color: '#fff', background: '#22c55e', fontSize: '11px', fontWeight: 600, fontFamily: 'Inter, sans-serif', padding: { left: 6, right: 6, top: 2, bottom: 2 } }, position: 'right' }
                    },
                    {
                        y: 60,
                        borderColor: '#f59e0b',
                        strokeDashArray: 4,
                        label: { text: 'Moderate', borderColor: '#f59e0b', style: { color: '#fff', background: '#f59e0b', fontSize: '11px', fontWeight: 600, fontFamily: 'Inter, sans-serif', padding: { left: 6, right: 6, top: 2, bottom: 2 } }, position: 'right' }
                    },
                    {
                        y: 85,
                        borderColor: '#ef4444',
                        strokeDashArray: 4,
                        label: { text: 'High', borderColor: '#ef4444', style: { color: '#fff', background: '#ef4444', fontSize: '11px', fontWeight: 600, fontFamily: 'Inter, sans-serif', padding: { left: 6, right: 6, top: 2, bottom: 2 } }, position: 'right' }
                    }
                ]
            },
            dataLabels: { enabled: false },
            markers: { size: [4, 0], strokeWidth: 2, hover: { size: 6 } },
            legend: { show: true, position: 'top', horizontalAlign: 'right', fontSize: '12px', fontFamily: 'Inter, sans-serif', labels: { colors: foreColor }, markers: { radius: 4 } },
            noData: { text: 'Loading stress data...', align: 'center', verticalAlign: 'middle', offsetY: 0, style: { color: foreColor, fontSize: '14px', fontFamily: 'Inter, sans-serif' } }
        });
        this.charts.stress.render();

        this.charts.analytics = new ApexCharts(document.getElementById('detailedChart'), {
            chart: {
                type: 'line',
                height: 240,
                toolbar: { show: false },
                animations: { enabled: true },
                foreColor: foreColor,
                background: 'transparent'
            },
            stroke: {
                width: 3,
                curve: 'smooth'
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.45,
                    opacityTo: 0.05,
                    stops: [0, 90, 100]
                }
            },
            markers: {
                size: 4,
                strokeWidth: 2,
                hover: { size: 7 }
            },
            xaxis: {
                type: 'datetime',
                labels: {
                    datetimeUTC: false,
                    style: { colors: foreColor, fontSize: '11px', fontFamily: 'Inter, sans-serif' }
                },
                axisBorder: { show: false },
                axisTicks: { show: false }
            },
            yaxis: {
                min: 0,
                max: 100,
                tickAmount: 5,
                title: { text: 'Score', style: { color: foreColor, fontSize: '12px', fontFamily: 'Inter, sans-serif' } },
                labels: { style: { colors: foreColor, fontSize: '11px', fontFamily: 'Inter, sans-serif' }, formatter: v => Math.round(v) }
            },
            grid: { show: true, borderColor: gridColor, strokeDashArray: 3, xaxis: { lines: { show: false } }, yaxis: { lines: { show: true } } },
            tooltip: {
                theme: tooltipTheme,
                style: { fontSize: '13px', fontFamily: 'Inter, sans-serif' },
                x: { format: 'dd MMM' },
                y: {
                    formatter: v => {
                        if (v < 30) return `${v} – Low stress`;
                        if (v < 60) return `${v} – Moderate stress`;
                        if (v < 85) return `${v} – High stress`;
                        return `${v} – Critical`;
                    }
                }
            },
            annotations: {
                yaxis: [
                    {
                        y: 30,
                        borderColor: '#22c55e',
                        strokeDashArray: 4,
                        label: { text: 'Low', borderColor: '#22c55e', style: { color: '#fff', background: '#22c55e', fontSize: '11px', fontWeight: 600, fontFamily: 'Inter, sans-serif', padding: { left: 6, right: 6, top: 2, bottom: 2 } }, position: 'right' }
                    },
                    {
                        y: 60,
                        borderColor: '#f59e0b',
                        strokeDashArray: 4,
                        label: { text: 'Moderate', borderColor: '#f59e0b', style: { color: '#fff', background: '#f59e0b', fontSize: '11px', fontWeight: 600, fontFamily: 'Inter, sans-serif', padding: { left: 6, right: 6, top: 2, bottom: 2 } }, position: 'right' }
                    },
                    {
                        y: 85,
                        borderColor: '#ef4444',
                        strokeDashArray: 4,
                        label: { text: 'High', borderColor: '#ef4444', style: { color: '#fff', background: '#ef4444', fontSize: '11px', fontWeight: 600, fontFamily: 'Inter, sans-serif', padding: { left: 6, right: 6, top: 2, bottom: 2 } }, position: 'right' }
                    }
                ]
            },
            legend: { labels: { colors: foreColor }, fontSize: '12px', fontFamily: 'Inter, sans-serif' },
            series: [],
            noData: {
                text: 'No history data',
                style: { color: foreColor, fontSize: '14px', fontFamily: 'Inter, sans-serif' }
            }
        });
        this.charts.analytics.render();
        
        // Phase 5.1: Emotional Radar Chart
        this.initEmotionRadarChart(foreColor, tooltipTheme);

        // Populate charts with already-loaded data (no async wait needed)
        this.populateCharts();
    }

    initEmotionRadarChart(foreColor, tooltipTheme) {
        const chartEl = document.getElementById('emotionRadarChart');
        if (!chartEl) return;

        this.charts.emotions = new ApexCharts(chartEl, {
            series: [{ name: 'Sentiment Intensity', data: [] }],
            chart: {
                type: 'radar',
                height: 250,
                toolbar: { show: false },
                animations: { enabled: true, speed: 800 },
                foreColor: foreColor
            },
            dataLabels: { enabled: true, style: { colors: [foreColor] } },
            plotOptions: {
                radar: {
                    size: 80,
                    polygons: {
                        strokeColors: '#e8e8e8',
                        fill: { colors: ['#f8f8f8', '#fff'] }
                    }
                }
            },
            colors: ['#6366f1'],
            markers: { size: 4, colors: ['#fff'], strokeColor: '#6366f1', strokeWidth: 2 },
            tooltip: { theme: tooltipTheme, y: { formatter: v => (v * 100).toFixed(1) + '%' } },
            xaxis: {
                categories: [],
                labels: {
                    show: true,
                    style: { colors: foreColor, fontSize: '11px', fontWeight: 500 }
                }
            },
            yaxis: { show: false, min: 0, max: 1 },
            legend: { show: false }
        });
        this.charts.emotions.render();
    }

    populateCharts() {
        // This runs AFTER data is loaded, so charts render with real data immediately
        if (this.stressHistory && this.stressHistory.length > 0) {
            this.updateChartsWithHistory(this.stressHistory);
        }
        // Load detailed history for 7D by default
        this.loadDetailedHistory(7);
    }

    updateChartsWithHistory(historyData) {
        // Normalize and process stress data
        const rawScores = historyData.map(h => Number(h.score ?? 50));
        const maxScore = Math.max(...rawScores);
        const stressData = maxScore > 0 && maxScore <= 1
            ? rawScores.map(s => Math.round(s * 100))
            : rawScores.map(s => Math.round(s));

        const dates = historyData.map(h => {
            const d = new Date(h.timestamp);
            return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
        });

        const stressedScores = injectStressVariance(stressData);
        const averages = rollingAverage(stressedScores, Math.min(7, stressedScores.length));

        // Update stress chart with real data
        const _fc = document.documentElement.getAttribute('data-theme') === 'dark' ? '#cbd5e1' : '#64748b';
        this.charts.stress.updateOptions({
            xaxis: { categories: dates },
            yaxis: { min: 0, max: 100, tickAmount: 5, labels: { style: { colors: _fc, fontSize: '11px', fontFamily: 'Inter, sans-serif' }, formatter: v => Math.round(v) } }
        });
        this.charts.stress.updateSeries([
            { name: 'Stress Level', data: stressedScores },
            { name: '7-Day Average', data: averages }
        ]);

        // Update analytics chart
        this.charts.analytics.updateOptions({
            xaxis: { categories: dates }
        });
        this.charts.analytics.updateSeries([
            { name: 'Stress', data: stressData },
            { name: 'Mood', data: stressData.map(s => Math.max(1, 5 - Math.floor(s / 15))) }
        ]);
    }

    initNavigation() {
        // Reserved for future mobile navigation FAB
    }

    initModals() {
        this.modals.support = document.getElementById('supportModal');
        this.modals.urgent = document.getElementById('urgentModal');
        this.modals.schedule = document.getElementById('scheduleModal');

        const reqBtn = document.getElementById('requestSupportBtn');
        const closeBtn = document.getElementById('closeModalBtn');
        const cancelBtn = document.getElementById('cancelBtn');
        if (reqBtn) reqBtn.addEventListener('click', () => this.openModal('support'));
        if (closeBtn) closeBtn.addEventListener('click', () => this.closeModal('support'));
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.closeModal('support'));
        if (this.modals.support) {
            this.modals.support.addEventListener('click', (e) => { if (e.target === this.modals.support) this.closeModal('support'); });
        }

        // ── Urgent Help modal ──
        const urgentBtn = document.getElementById('urgentHelpBtn');
        const urgentCancel = document.getElementById('urgentCancelBtn');
        const urgentConfirm = document.getElementById('urgentConfirmBtn');
        if (urgentBtn) urgentBtn.addEventListener('click', () => this.openModal('urgent'));
        if (urgentCancel) urgentCancel.addEventListener('click', () => this.closeModal('urgent'));
        if (urgentConfirm) urgentConfirm.addEventListener('click', () => this.triggerUrgentHelp());
        if (this.modals.urgent) {
            this.modals.urgent.addEventListener('click', (e) => { if (e.target === this.modals.urgent) this.closeModal('urgent'); });
        }

        // ── Schedule Session modal ──
        const schedBtn = document.getElementById('scheduleSessionBtn');
        const schedClose = document.getElementById('scheduleCloseBtn');
        const schedCancel = document.getElementById('scheduleCancelBtn');
        const schedForm = document.getElementById('scheduleForm');
        if (schedBtn) schedBtn.addEventListener('click', () => { this.openModal('schedule'); this.loadMyBookings(); this.setMinSessionDate(); });
        if (schedClose) schedClose.addEventListener('click', () => this.closeModal('schedule'));
        if (schedCancel) schedCancel.addEventListener('click', () => this.closeModal('schedule'));
        if (schedForm) schedForm.addEventListener('submit', (e) => { e.preventDefault(); this.bookSession(); });
        if (this.modals.schedule) {
            this.modals.schedule.addEventListener('click', (e) => { if (e.target === this.modals.schedule) this.closeModal('schedule'); });
        }

        // Form submission handled via setupEventListeners
    }

    async loadDashboardData() {
        this.showLoading(true);
        try {
            const [wellnessData, activityData, historyData] = await Promise.all([
                this.fetchData('/student/api/wellness/current'),
                this.fetchData('/student/api/wellness/activities'),
                this.fetchData('/student/api/stress_history')
            ]);
            // Normalize history; empty array if no real data
            const normalizedHistory = Array.isArray(historyData?.history)
                ? historyData.history
                    .map((h, idx, arr) => ({
                        timestamp: h.timestamp || new Date(Date.now() - (arr.length - 1 - idx) * 86400000).toISOString(),
                        score: Number(h.score)
                    }))
                    .filter(h => Number.isFinite(h.score))
                : [];

            this.stressHistory = normalizedHistory;

            // Use latest stress value if API missing; derive from history
            const derivedStress = this.stressHistory.length ? this.stressHistory[this.stressHistory.length - 1] : null;
            const stressValue = derivedStress ? derivedStress.score : 0;
            const stressPayload = wellnessData?.stress ? wellnessData : { stress: { value: stressValue } };

            this.updateStressDisplay(stressPayload);
            this.updateActivityDisplay(activityData);
            this.updateActivityTimeline();

            // Fetch real hub stats from API
            this.refreshHubStats();
        } catch (error) {
            this.showErrorState();
        } finally { this.showLoading(false); }
    }

    async refreshHubStats() {
        try {
            const data = await this.fetchData('/student/api/connect-hub/stats');
            const activeUsersEl   = document.getElementById('activeUsers');
            const totalGroupsEl   = document.getElementById('totalGroups');
            const upcomingEventsEl = document.getElementById('upcomingEvents');
            const statusEl        = document.getElementById('connectionStatus');
            const dotEl           = document.querySelector('#panel-hub .status-indicator');

            if (activeUsersEl)    this._animateCount(activeUsersEl, data.active_now ?? 0);
            if (totalGroupsEl)    this._animateCount(totalGroupsEl, data.groups ?? 0);
            if (upcomingEventsEl) this._animateCount(upcomingEventsEl, data.events ?? 0);

            if (statusEl) {
                statusEl.textContent = 'Connected';
                statusEl.style.color = '';
            }
            if (dotEl) {
                dotEl.style.background = '';
                dotEl.style.boxShadow  = '';
            }
        } catch {
            const statusEl = document.getElementById('connectionStatus');
            const dotEl    = document.querySelector('#panel-hub .status-indicator');
            if (statusEl) {
                statusEl.textContent = 'Offline';
                statusEl.style.color = '#f87171';
            }
            if (dotEl) {
                dotEl.style.background = '#f87171';
                dotEl.style.boxShadow  = '0 0 0 4px rgba(248,113,113,0.25)';
            }
            // Show placeholder dashes so UI is never stale from a previous value
            ['activeUsers','totalGroups','upcomingEvents'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = '--';
            });
        }
    }

    _animateCount(el, target) {
        const start    = parseInt(el.textContent) || 0;
        const duration = 600;
        const startTs  = performance.now();
        const step = (ts) => {
            const progress = Math.min((ts - startTs) / duration, 1);
            el.textContent = Math.round(start + (target - start) * progress);
            if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    async fetchData(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    }

    updateStressDisplay(data) {
        const stress = data.stress || {};
        const newStress = stress.value ?? 50;
        const oldStress = this.currentStress;
        this.currentStress = newStress;

        // Animate the number change
        this.animateValueChange('stressValue', oldStress, newStress, 600);

        // Label
        const descriptor = stress.label || this.getStressDescriptor(newStress);
        const descEl = document.getElementById('stressDescriptor');
        if (descEl) descEl.textContent = descriptor;

        // Trend arrow + label
        const trend = stress.trend || 'stable';
        const trendIndicator = document.getElementById('trendIndicator');
        const trendLabel = document.getElementById('trendLabel');
        if (trendIndicator) {
            trendIndicator.textContent = trend === 'up' ? '↑' : (trend === 'down' ? '↓' : '=');
            trendIndicator.className = 'trend-indicator' + (trend === 'up' ? ' trend-up' : (trend === 'down' ? ' trend-down' : ''));
        }
        if (trendLabel) {
            trendLabel.textContent = trend === 'up' ? 'Increasing' : (trend === 'down' ? 'Decreasing' : 'Stable');
        }

        // Animated bar fill with color zones
        const fill = document.getElementById('stressIndicatorFill');
        if (fill) {
            const pct = Math.min(Math.max(newStress, 0), 100);
            fill.style.width = `${pct}%`;
            fill.style.transition = 'width 0.8s cubic-bezier(0.4,0,0.2,1), background 0.5s ease';
            if (pct <= 30) {
                fill.style.background = 'linear-gradient(90deg, #22c55e, #16a34a)';
            } else if (pct <= 50) {
                fill.style.background = 'linear-gradient(90deg, #84cc16, #eab308)';
            } else if (pct <= 70) {
                fill.style.background = 'linear-gradient(90deg, #eab308, #f97316)';
            } else if (pct <= 85) {
                fill.style.background = 'linear-gradient(90deg, #f97316, #ef4444)';
            } else {
                fill.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
            }
        }

        // Insight text
        const insightEl = document.getElementById('stressInsight');
        if (insightEl && stress.insight) {
            insightEl.textContent = stress.insight;
            insightEl.style.display = '';
        }

        // Spike alert badge
        const spikeEl = document.getElementById('spikeAlert');
        if (spikeEl) {
            spikeEl.style.display = stress.spike_detected ? 'flex' : 'none';
        }

        // Signal breakdown bars
        if (stress.signals) {
            this.updateSignalBars(stress.signals);
        }

        // Confidence + Dominant Factor
        const metaEl = document.getElementById('stressMeta');
        if (metaEl) {
            const hasConfidence = stress.confidence !== undefined;
            const hasDominant = stress.dominant_factor;
            metaEl.style.display = (hasConfidence || hasDominant) ? 'flex' : 'none';

            if (hasConfidence) {
                const pct = Math.round(stress.confidence * 100);
                const confEl = document.getElementById('confidenceValue');
                if (confEl) confEl.textContent = `${pct}% confidence`;
                const chip = document.getElementById('confidenceChip');
                if (chip) chip.classList.toggle('low-confidence', pct < 50);
            }
            if (hasDominant) {
                const nameMap = { mood: 'Mood', sentiment: 'Chat Tone', activity: 'Activity', volatility: 'Stability', time_bias: 'Time', trend: 'Trend' };
                const domLabel = document.getElementById('dominantLabel');
                const domDot = document.getElementById('dominantDot');
                if (domLabel) domLabel.textContent = nameMap[stress.dominant_factor] || stress.dominant_factor;
                if (domDot) {
                    const v = stress.signals?.[stress.dominant_factor] ?? 50;
                    domDot.style.background = v <= 35 ? '#22c55e' : v <= 55 ? '#eab308' : v <= 75 ? '#f97316' : '#ef4444';
                }
            }
        }

        // Update timestamp
        const tsEl = document.getElementById('stressTimestamp');
        if (tsEl && stress.insight) {
            const span = tsEl.querySelector('span');
            if (span) span.textContent = 'Updated just now';
        }

        // Update Emotional Radar
        if (data.latest_emotions && Object.keys(data.latest_emotions).length > 0) {
            this.updateEmotionRadar(data.latest_emotions);
        } else {
            const radarSection = document.getElementById('emotionRadarChart');
            const noMsg = document.getElementById('noEmotionsMessage');
            if (radarSection) radarSection.classList.add('aura-hidden');
            if (noMsg) noMsg.classList.remove('aura-hidden');
        }
    }

    updateEmotionRadar(emotions) {
        if (!this.charts.emotions) return;
        
        const radarSection = document.getElementById('emotionRadarChart');
        const noMsg = document.getElementById('noEmotionsMessage');
        if (radarSection) radarSection.classList.remove('aura-hidden');
        if (noMsg) noMsg.classList.add('aura-hidden');

        const labels = Object.keys(emotions).map(e => e.charAt(0).toUpperCase() + e.slice(1));
        const values = Object.values(emotions);

        this.charts.emotions.updateOptions({
            xaxis: { categories: labels }
        });
        this.charts.emotions.updateSeries([{
            name: 'Sentiment Intensity',
            data: values
        }]);
    }

    updateSignalBars(signals) {
        const signalMap = {
            'mood': { bar: 'signalMood', val: 'signalMoodVal' },
            'sentiment': { bar: 'signalSentiment', val: 'signalSentimentVal' },
            'activity': { bar: 'signalActivity', val: 'signalActivityVal' },
            'volatility': { bar: 'signalVolatility', val: 'signalVolatilityVal' },
            'time_bias': { bar: 'signalTime', val: 'signalTimeVal' },
            'trend': { bar: 'signalTrend', val: 'signalTrendVal' },
        };
        for (const [key, ids] of Object.entries(signalMap)) {
            const bar = document.getElementById(ids.bar);
            const valEl = document.getElementById(ids.val);
            if (bar && signals[key] !== undefined) {
                const v = Math.round(signals[key]);
                bar.style.width = `${v}%`;
                bar.style.transition = 'width 0.6s cubic-bezier(0.4,0,0.2,1)';
                bar.setAttribute('data-value', v);
                // Subtle color palette (lower opacity for production look)
                if (v <= 35) bar.style.background = 'rgba(34,197,94,0.7)';
                else if (v <= 55) bar.style.background = 'rgba(234,179,8,0.65)';
                else if (v <= 75) bar.style.background = 'rgba(249,115,22,0.7)';
                else bar.style.background = 'rgba(239,68,68,0.75)';
            }
            if (valEl && signals[key] !== undefined) {
                valEl.textContent = Math.round(signals[key]);
            }
        }
    }

    getStressDescriptor(value) {
        if (value <= 25) return 'Relaxed';
        if (value <= 45) return 'Manageable';
        if (value <= 65) return 'Elevated';
        if (value <= 80) return 'High';
        return 'Critical';
    }

    updateActivityDisplay(data) {
        // Update check-in counts
        const todayEl = document.getElementById('checkinsToday');
        const weekEl = document.getElementById('checkinsWeek');
        const avgEl = document.getElementById('weeklyAverage');
        const trendEl = document.getElementById('weeklyTrend');
        const trendIcon = document.getElementById('trendIcon');

        if (todayEl) todayEl.textContent = data.today ?? 0;
        if (weekEl) weekEl.textContent = data.week ?? 0;
        if (avgEl) avgEl.textContent = data.weekly_average ?? 0;

        // Parse trend percentage (handle NaN for non-numeric values like "N/A")
        const trendStr = data.weekly_change ?? '0%';
        const trendValue = parseInt(trendStr.replace('%', '')) || 0;

        if (trendEl) {
            trendEl.textContent = trendStr;
            // Color code: positive = green, negative = red, neutral = muted
            trendEl.style.color = trendValue > 0 ? '#ef4444' : trendValue < 0 ? '#10b981' : '#64748b';
        }

        // Update trend icon direction
        if (trendIcon) {
            if (trendValue >= 0) {
                // Trending up
                trendIcon.innerHTML = '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>';
                trendIcon.style.stroke = '#10b981';
            } else {
                // Trending down
                trendIcon.innerHTML = '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>';
                trendIcon.style.stroke = '#ef4444';
            }
        }
    }

    async loadDetailedHistory(days) {
        try {
            const res = await fetch(`/student/api/stress_history?days=${days}`);
            const data = await res.json();
            // Fallback demo history to avoid flat or empty charts
            const fallbackSeries = [32, 45, 41, 50, 38, 60, 48];
            const buildFallbackPoints = () => fallbackSeries.map((score, i) => ({
                x: new Date(Date.now() - (fallbackSeries.length - 1 - i) * 86400000).getTime(),
                y: score
            }));

            const validHistory = Array.isArray(data.history) ? data.history : [];
            const points = validHistory.map((h, idx, arr) => ({
                x: new Date(h.timestamp || new Date(Date.now() - (arr.length - 1 - idx) * 86400000)).getTime(),
                y: Number(h.score)
            })).filter(p => Number.isFinite(p.y));

            const hasMeaningful = points.length >= 2 && points.some(p => p.y > 0.5);
            const seriesPoints = hasMeaningful ? points : buildFallbackPoints();

            const rawValues = seriesPoints.map(p => p.y);
            const stressedValues = injectStressVariance(rawValues, 8);
            const stressedPoints = seriesPoints.map((p, i) => ({
                x: p.x,
                y: stressedValues[i]
            }));

            // Compute dynamic Y-axis bounds from data
            const bounds = computeYAxisBounds(stressedValues);

            this.charts.analytics.updateOptions({
                yaxis: {
                    min: bounds.min,
                    max: bounds.max,
                    tickAmount: 5
                },
                markers: {
                    discrete: [{
                        seriesIndex: 0,
                        dataPointIndex: stressedPoints.length - 1,
                        fillColor: '#2563eb',
                        strokeColor: '#1e40af',
                        size: 7
                    }]
                }
            });

            this.charts.analytics.updateSeries([
                {
                    name: 'Stress Level',
                    data: stressedPoints
                }
            ]);
        } catch (error) {
            // silently handled
        }
    }

    updateChartsTheme(theme) {
        const textColor = theme === 'dark' ? '#cbd5e1' : '#64748b';
        const gridColor = theme === 'dark' ? 'rgba(148,163,184,0.10)' : 'rgba(100,116,139,0.10)';
        const tooltipTheme = theme === 'dark' ? 'dark' : 'light';

        const sharedOpts = {
            chart: { foreColor: textColor },
            xaxis: { labels: { style: { colors: textColor } } },
            yaxis: { labels: { style: { colors: textColor } } },
            grid: { borderColor: gridColor },
            tooltip: { theme: tooltipTheme },
            legend: { labels: { colors: textColor } },
            noData: { style: { color: textColor } }
        };

        if (this.charts.stress) {
            this.charts.stress.updateOptions(sharedOpts, false, false);
        }
        if (this.charts.analytics) {
            this.charts.analytics.updateOptions({
                ...sharedOpts,
                yaxis: { labels: { style: { colors: textColor } }, title: { style: { color: textColor } } }
            }, false, false);
        }
    }

    updateActivityTimeline() {
        const timeline = document.getElementById('activityTimeline');
        if (!timeline) return;
        const checkIcon = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
        if (this.currentStress > 0) {
            timeline.innerHTML = `
                <div class="activity-item">
                    <div class="activity-icon">${checkIcon}</div>
                    <div class="activity-content">
                        <div class="activity-title">Last Check-in</div>
                        <div class="activity-time">Current stress level: ${this.currentStress}/100</div>
                    </div>
                </div>`;
        } else {
            timeline.innerHTML = '<div class="activity-item"><div class="activity-content"><div class="activity-title" style="opacity:0.5">No activity yet — try a check-in!</div></div></div>';
        }
    }

    setupEventListeners() {
        this.setupParentEmailEvents();
        document.addEventListener('keydown', (e) => {
            if (e.altKey) {
                switch (e.key) {
                    case 'h': this.openModal('support'); break;
                }
            }
        });
        document.querySelectorAll('.btn-control').forEach(btn => {
            btn.addEventListener('click', () => {
                const period = btn.dataset.period;
                if (!period) return;
                document.querySelectorAll('.btn-control').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const days = period.replace('d', '');
                this.loadDetailedHistory(days);
            });
        });
        const form = document.getElementById('supportForm');
        if (form) form.addEventListener('submit', (e) => { e.preventDefault(); this.submitSupportRequest(); });

        // Character counter for support form description
        const descTextarea = document.getElementById('descriptionTextarea');
        const charCounter = document.getElementById('charCount');
        if (descTextarea && charCounter) {
            descTextarea.addEventListener('input', () => {
                charCounter.textContent = descTextarea.value.length;
                if (descTextarea.value.length > 500) {
                    charCounter.style.color = '#ef4444';
                } else {
                    charCounter.style.color = '';
                }
            });
        }

        // Toast close button
        const toastClose = document.querySelector('.toast-close');
        if (toastClose) {
            toastClose.addEventListener('click', () => {
                const toast = document.getElementById('notificationToast');
                if (toast) toast.classList.remove('show');
            });
        }
    }

    setupParentEmailEvents() {
        const addBtn = document.getElementById('addParentEmailBtn');
        const removeBtn = document.getElementById('removeParentEmailBtn');
        
        if (addBtn) {
            addBtn.addEventListener('click', async () => {
                const parentEmail = document.getElementById('parentEmailInput').value.trim();
                const parentName = document.getElementById('parentNameInput').value.trim();
                const msgEl = document.getElementById('parentEmailMsg');
                
                if (!parentEmail || !parentEmail.includes('@')) {
                    if (msgEl) { msgEl.className = 'settings-feedback error'; msgEl.textContent = 'Please enter a valid email address.'; }
                    return;
                }
                
                addBtn.disabled = true;
                addBtn.textContent = 'Sending...';
                if (msgEl) msgEl.textContent = '';
                
                try {
                    const data = await this.fetchData('/api/student/parent/add', {
                        method: 'POST',
                        body: JSON.stringify({ parent_email: parentEmail, parent_name: parentName })
                    });
                    
                    if (data.success) {
                        if (msgEl) { msgEl.className = 'settings-feedback success'; msgEl.textContent = data.message; }
                        document.getElementById('parentEmailInput').value = '';
                        document.getElementById('parentNameInput').value = '';
                        this.loadProfile(); // Refresh UI
                    } else {
                        if (msgEl) { msgEl.className = 'settings-feedback error'; msgEl.textContent = data.error || data.message || 'Failed to add parent email'; }
                    }
                } catch (e) {
                    if (msgEl) { msgEl.className = 'settings-feedback error'; msgEl.textContent = 'Network error. Please try again.'; }
                } finally {
                    addBtn.disabled = false;
                    addBtn.textContent = 'Send Verification Link';
                }
            });
        }
        
        if (removeBtn) {
            removeBtn.addEventListener('click', async () => {
                const msgEl = document.getElementById('parentEmailMsg');
                if (!confirm('Are you sure you want to remove this parent email? They will no longer receive alerts.')) return;
                
                removeBtn.disabled = true;
                removeBtn.textContent = 'Removing...';
                
                try {
                    const data = await this.fetchData('/api/student/parent/remove', { method: 'POST' });
                    if (data.success) {
                        if (msgEl) { msgEl.className = 'settings-feedback success'; msgEl.textContent = data.message; }
                        this.loadProfile();
                    } else {
                        if (msgEl) { msgEl.className = 'settings-feedback error'; msgEl.textContent = data.error || 'Failed to remove parent email'; }
                    }
                } catch (e) {
                    if (msgEl) { msgEl.className = 'settings-feedback error'; msgEl.textContent = 'Network error. Please try again.'; }
                } finally {
                    removeBtn.disabled = false;
                    removeBtn.textContent = 'Remove';
                }
            });
        }
    }



    animateValueChange(elementId, start, end, duration) {
        const el = document.getElementById(elementId);
        const startTime = Date.now();
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = Math.round(start + (end - start) * easeOutQuart);
            if (el) el.textContent = currentValue;
            if (progress < 1) requestAnimationFrame(animate);
        };
        animate();
    }

    addToActivityTimeline(action, newStress) {
        const now = luxon.DateTime.now();
        const actionNames = { checkin: 'Mood Check-in' }; // Simplified action map
        const timeline = document.getElementById('activityTimeline');
        if (!timeline) return;
        const div = document.createElement('div');
        div.className = 'activity-item';
        div.innerHTML = `
            <div class="activity-icon"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
            <div class="activity-content">
                <div class="activity-title">${actionNames[action] || 'Action'}</div>
                <div class="activity-time">${now.toFormat('HH:mm')} • Stress: ${newStress}</div>
            </div>`;
        timeline.insertBefore(div, timeline.firstChild);
        if (timeline.children.length > 4) timeline.removeChild(timeline.lastChild);
    }

    openModal(name) { const m = this.modals[name]; if (m) { m.classList.add('active'); document.body.style.overflow = 'hidden'; } }
    closeModal(name) { const m = this.modals[name]; if (m) { m.classList.remove('active'); document.body.style.overflow = ''; const f = document.getElementById('supportForm'); if (f) f.reset(); } }

    async submitSupportRequest() {
        const form = document.getElementById('supportForm');
        const submitBtn = form ? form.querySelector('button[type="submit"]') : null;
        if (!form || !submitBtn) return;
        if (!form.checkValidity()) { form.reportValidity(); return; }
        const formData = {
            category: document.getElementById('categorySelect').value,
            priority: document.getElementById('prioritySelect').value,
            subject: document.getElementById('subjectInput').value,
            description: document.getElementById('descriptionTextarea').value,
            confidential: false
        };
        const originalHTML = submitBtn.innerHTML;
        submitBtn.disabled = true; submitBtn.innerHTML = '<svg viewBox=\"0 0 24 24\" width=\"14\" height=\"14\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" style=\"animation:spin 1s linear infinite\"><path d=\"M21 12a9 9 0 1 1-6.219-8.56\"/></svg> Submitting...';
        try {
            const response = await fetch('/student/api/support/request', {
                method: 'POST', headers: secureHeaders(), body: JSON.stringify({ notes: `[${formData.category.toUpperCase()}:${formData.priority.toUpperCase()}] ${formData.subject}: ${formData.description}`, metadata: formData })
            });
            const data = await response.json();
            if (response.ok && data.success) {
                const feedback = document.getElementById('actionFeedback');
                if (feedback) { feedback.textContent = 'Support request submitted successfully'; feedback.className = 'text-sm text-success'; }
                this.closeModal('support');
                form.reset();
                setTimeout(() => { if (feedback) feedback.textContent = ''; }, 5000);
            } else {
                throw new Error(data.error || 'Submission failed');
            }
        } catch (error) {
            alert('Failed to submit support request. Please try again.');
        } finally { submitBtn.disabled = false; submitBtn.innerHTML = originalHTML; }
    }

    // ── Urgent Help ──
    async triggerUrgentHelp() {
        const btn = document.getElementById('urgentConfirmBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Sending...'; }
        try {
            const res = await fetch('/student/api/support/urgent', { method: 'POST' });
            const data = await res.json();
            this.closeModal('urgent');
            if (res.ok && data.success) {
                this.showToast('A counselor has been notified. Stay calm — help is on the way.', 'success');
            } else {
                this.showToast(data.error || 'Failed to send alert. Please try again.', 'error');
            }
        } catch (e) {
            this.closeModal('urgent');
            this.showToast('Network error. If you are in danger, call 1-800-273-8255.', 'error');
        } finally { if (btn) { btn.disabled = false; btn.textContent = 'Yes, I Need Help Now'; } }
    }

    // ── Schedule Session ──
    setMinSessionDate() {
        const dateInput = document.getElementById('sessionDate');
        if (dateInput) { dateInput.min = new Date().toISOString().split('T')[0]; }
    }

    async bookSession() {
        const btn = document.getElementById('scheduleSubmitBtn');
        const form = document.getElementById('scheduleForm');
        if (!form || !form.checkValidity()) { if (form) form.reportValidity(); return; }

        const payload = {
            type: document.getElementById('sessionType').value,
            date: document.getElementById('sessionDate').value,
            time: document.getElementById('sessionTime').value,
            notes: (document.getElementById('sessionNotes').value || '').trim()
        };

        if (btn) { btn.disabled = true; btn.textContent = 'Booking...'; }
        try {
            const res = await fetch('/student/api/support/schedule', {
                method: 'POST',
                headers: secureHeaders(),
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.success) {
                this.closeModal('schedule');
                form.reset();
                this.showToast(data.message || 'Session booked successfully!', 'success');
            } else {
                this.showToast(data.error || 'Booking failed. Please try again.', 'error');
            }
        } catch (e) {
            this.showToast('Network error. Please try again.', 'error');
        } finally { if (btn) { btn.disabled = false; btn.textContent = 'Book Session'; } }
    }

    async loadMyBookings() {
        const container = document.getElementById('myBookingsList');
        const section = document.getElementById('scheduleMyBookings');
        if (!container || !section) return;
        try {
            const res = await fetch('/student/api/support/sessions');
            const data = await res.json();
            if (data.success && data.sessions && data.sessions.length > 0) {
                section.style.display = 'block';
                container.innerHTML = data.sessions.slice(0, 5).map(s =>
                    `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:var(--surface-muted);border-radius:8px;font-size:13px;">
                        <span style="font-weight:500;color:var(--text);">${esc(s.date)} at ${esc(s.time)}</span>
                        <span style="padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;background:${s.status === 'scheduled' ? 'rgba(34,197,94,.15)' : 'rgba(100,116,139,.15)'};color:${s.status === 'scheduled' ? '#22c55e' : '#64748b'};">${esc(s.status)}</span>
                    </div>`
                ).join('');
            } else {
                section.style.display = 'none';
            }
        } catch (e) { section.style.display = 'none'; }
    }

    showToast(message, type = 'success') {
        const toast = document.getElementById('notificationToast');
        const msgEl = document.getElementById('toastMessage');
        if (!toast || !msgEl) { alert(message); return; }
        msgEl.textContent = message;
        toast.className = 'toast show ' + type;
        setTimeout(() => { toast.classList.remove('show'); }, 5000);
    }

    startRealTimeUpdates() {
        this._pollingTimer = setInterval(async () => {
            try {
                const response = await fetch('/student/api/wellness/current');
                if (response.ok) {
                    const data = await response.json();
                    this.updateStressDisplay(data);
                }
            } catch (e) { /* silently handled */ }
        }, 30000);
        // initDate timer is already set internally — no need to call again
    }

    showLoading(show) { this.isLoading = show; }
    showErrorState() {
        const stressEl = document.getElementById('stressValue');
        if (stressEl) stressEl.textContent = '--';
        const statusEl = document.querySelector('.stress-status-label');
        if (statusEl) statusEl.textContent = 'Unable to load data';
    }

    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/service-worker.js').catch(err => {
                    // silently handled
                });
            });
        }
    }

    // ==============================
    // PROFILE SECTION
    // ==============================
    async loadProfile() {
        try {
            const data = await this.fetchData('/student/api/student/profile');
            const nameEl = document.getElementById('profileName');
            const emailEl = document.getElementById('profileEmail');
            const rollEl = document.getElementById('profileRoll');
            const userNameEl = document.getElementById('userName');

            if (nameEl) nameEl.textContent = data.name || 'Student';
            if (emailEl) emailEl.textContent = data.email || '—';
            if (rollEl) rollEl.textContent = data.roll_number || '—';
            if (userNameEl) userNameEl.textContent = (data.name || 'Student').split(' ')[0];

            // Parent email + verification status
            const parentEmailEl = document.getElementById('profileParentEmail');
            const parentStatusEl = document.getElementById('profileParentStatus');
            const removeBtn = document.getElementById('removeParentEmailBtn');
            const addBtn = document.getElementById('addParentEmailBtn');
            const emailInput = document.getElementById('parentEmailInput');
            const nameInput = document.getElementById('parentNameInput');
            
            if (parentEmailEl && parentStatusEl) {
                try {
                    const parentPayload = await this.fetchData('/api/student/parent/status');
                    const parentData = parentPayload?.data || {};
                    const verified = parentData.parent_verified === true;
                    // The backend stores pending_email when verification is sent, or parent_email when verified
                    const email = parentData.parent_email || parentData.pending_email || '';

                    parentEmailEl.textContent = email ? `Parent email: ${email}` : 'Parent email: not added';

                    if (email) {
                        if (removeBtn) removeBtn.style.display = 'block';
                        if (addBtn) addBtn.textContent = 'Resend Verification';
                        if (emailInput) { 
                            emailInput.value = email; 
                            emailInput.placeholder = "Update Email Address";
                        }
                    } else {
                        if (removeBtn) removeBtn.style.display = 'none';
                        if (addBtn) addBtn.textContent = 'Send Verification Link';
                    }

                    if (verified) {
                        parentStatusEl.textContent = 'Verified';
                        parentStatusEl.className = 'parent-status-badge verified';
                    } else {
                        parentStatusEl.textContent = email ? 'Pending' : 'Not Added';
                        parentStatusEl.className = 'parent-status-badge pending';
                    }
                } catch (e) {
                    console.error(e);
                    parentEmailEl.textContent = 'Parent email: unavailable';
                    parentStatusEl.textContent = 'Pending';
                    parentStatusEl.className = 'parent-status-badge pending';
                }
            }

            // Load streak
            try {
                const dashData = await this.fetchData('/student/api/student/dashboard-data');
                const streakEl = document.getElementById('streakValue');
                if (streakEl) streakEl.textContent = dashData.streak || 0;
            } catch (e) { /* streak not critical */ }
        } catch (e) {
            console.warn('Profile load failed:', e);
        }
    }

    // ==============================
    // WELLNESS GOALS
    // ==============================
    initWellnessGoals() {
        // Load saved goals from localStorage (with error handling for corrupted data)
        let savedGoals = {};
        try {
            savedGoals = JSON.parse(localStorage.getItem('aura-goals-' + this.getTodayKey()) || '{}');
        } catch (e) {
            // Corrupted localStorage data, start fresh
            savedGoals = {};
        }
        const goalItems = document.querySelectorAll('.goal-item');
        let completedCount = 0;

        goalItems.forEach(item => {
            const goalId = item.dataset.goal;
            const checkbox = item.querySelector('.goal-checkbox');

            if (savedGoals[goalId]) {
                checkbox.classList.add('checked');
                item.classList.add('completed');
                completedCount++;
            }

            item.addEventListener('click', () => {
                const isChecked = checkbox.classList.toggle('checked');
                item.classList.toggle('completed', isChecked);
                this.saveGoalState();
                this.updateGoalsProgress();
            });
        });

        this.updateGoalsProgress();
    }

    getTodayKey() {
        return new Date().toISOString().split('T')[0];
    }

    saveGoalState() {
        const goals = {};
        document.querySelectorAll('.goal-item').forEach(item => {
            const goalId = item.dataset.goal;
            const isChecked = item.querySelector('.goal-checkbox').classList.contains('checked');
            goals[goalId] = isChecked;
        });
        localStorage.setItem('aura-goals-' + this.getTodayKey(), JSON.stringify(goals));
    }

    updateGoalsProgress() {
        const total = document.querySelectorAll('.goal-item').length;
        const completed = document.querySelectorAll('.goal-checkbox.checked').length;
        const fill = document.getElementById('goalsProgressFill');
        const text = document.getElementById('goalsCompleted');

        if (fill) fill.style.width = total > 0 ? `${(completed / total) * 100}%` : '0%';
        if (text) text.textContent = completed;
    }

    // ==============================
    // DAILY TIPS
    // ==============================
    loadDailyTip() {
        const tips = [
            "Take a 5-minute walk between study sessions to refresh your mind.",
            "Practice gratitude: write down 3 things you're thankful for today.",
            "Drink plenty of water — dehydration can increase stress levels.",
            "Try the 20-20-20 rule: every 20 min, look 20 feet away for 20 seconds.",
            "Deep breathing for just 60 seconds can lower cortisol and calm anxiety.",
            "Break large tasks into small steps — progress is motivating.",
            "Listen to calming music while studying to improve focus and reduce stress.",
            "Get at least 7 hours of sleep — your brain needs rest to perform well.",
            "Connect with a friend today — social support is a powerful stress buffer.",
            "Exercise releases endorphins — even 15 minutes of movement helps.",
            "Limit caffeine after 2 PM for better sleep quality tonight.",
            "Write down your worries to get them out of your head and onto paper.",
            "Take a digital detox for 30 minutes — put your phone on airplane mode.",
            "Practice the box breathing technique: inhale 4s, hold 4s, exhale 4s, hold 4s.",
            "Set boundaries: it's okay to say no to protect your mental energy.",
            "Celebrate small wins — they add up to big achievements.",
            "Try a body scan meditation to identify and release tension.",
            "Organize your study space — a clean environment reduces mental clutter.",
            "Eat a balanced meal with protein and complex carbs for sustained energy.",
            "Laugh! Watch a funny video or call someone who makes you smile.",
            "Schedule worry time: dedicate 10 minutes to worry, then let it go.",
            "Use the Pomodoro technique: 25 min focus, 5 min break.",
            "Write a positive affirmation and say it aloud every morning.",
            "Spend time in nature — even looking at trees reduces stress hormones.",
            "End your day by noting one thing that went well today."
        ];

        // Use day-of-year as index for consistent daily tip
        const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0)) / 86400000);
        const tipIndex = dayOfYear % tips.length;

        const tipEl = document.getElementById('tipText');
        if (tipEl) tipEl.textContent = tips[tipIndex];
    }

    // ==============================
    // JOURNAL
    // ==============================
    async initJournal() {
        const textarea = document.getElementById('journalEntry');
        const charCount = document.getElementById('journalCharCount');
        const saveBtn = document.getElementById('saveJournalBtn');

        if (!textarea || !saveBtn) return;

        // Load today's journal from server first, fall back to localStorage
        try {
            const res = await fetch('/student/api/journal/today');
            if (res.ok) {
                const data = await res.json();
                if (data.entry) {
                    textarea.value = data.entry;
                    if (charCount) charCount.textContent = data.entry.length;
                }
            }
        } catch {
            // Fallback to localStorage
            const savedJournal = localStorage.getItem('aura-journal-' + this.getTodayKey());
            if (savedJournal) {
                textarea.value = savedJournal;
                if (charCount) charCount.textContent = savedJournal.length;
            }
        }

        textarea.addEventListener('input', () => {
            if (charCount) charCount.textContent = textarea.value.length;
        });

        saveBtn.addEventListener('click', async () => {
            const entry = textarea.value.trim();
            if (!entry) return;

            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';

            // Save to server via journal API
            try {
                const res = await fetch('/student/api/journal', {
                    method: 'POST',
                    headers: secureHeaders(),
                    body: JSON.stringify({ entry })
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    this.showToast('Journal entry saved!', 'success');
                } else {
                    throw new Error(data.error || 'Save failed');
                }
            } catch (err) {
                // Fallback: save to localStorage
                localStorage.setItem('aura-journal-' + this.getTodayKey(), entry);
                this.showToast('Saved locally (offline)', 'warning');
            } finally {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Save Entry';
            }

            // Mark journal goal as done
            const goalItem = document.querySelector('.goal-item[data-goal="checkin"]');
            if (goalItem) {
                const cb = goalItem.querySelector('.goal-checkbox');
                if (cb && !cb.classList.contains('checked')) {
                    cb.classList.add('checked');
                    goalItem.classList.add('completed');
                    this.saveGoalState();
                    this.updateGoalsProgress();
                }
            }
        });
    }

    // ==============================
    // GRIEVANCE FORM
    // ==============================
    initGrievanceForm() {
        const form = document.getElementById('grievanceForm');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const subject = document.getElementById('grievanceSubject').value.trim();
            const description = document.getElementById('grievanceDescription').value.trim();
            const btn = document.getElementById('submitGrievanceBtn');
            const feedback = document.getElementById('grievanceFeedback');

            if (!subject || !description) return;

            if (btn) { btn.disabled = true; btn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Submitting...'; }

            try {
                const res = await fetch('/student/api/grievance', {
                    method: 'POST',
                    headers: secureHeaders(),
                    body: JSON.stringify({ subject, description })
                });
                const data = await res.json();

                if (res.ok && data.success) {
                    if (feedback) {
                        feedback.className = 'grievance-feedback success';
                        feedback.textContent = 'Grievance submitted successfully. It will be reviewed confidentially.';
                        feedback.style.display = 'block';
                    }
                    form.reset();
                    this.showToast('Grievance submitted!', 'success');
                    setTimeout(() => { if (feedback) feedback.style.display = 'none'; }, 5000);
                } else {
                    throw new Error(data.error || 'Submission failed');
                }
            } catch (err) {
                if (feedback) {
                    feedback.className = 'grievance-feedback error';
                    feedback.textContent = err.message || 'Failed to submit. Please try again.';
                    feedback.style.display = 'block';
                }
                setTimeout(() => { if (feedback) feedback.style.display = 'none'; }, 5000);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Submit Grievance';
                }
            }
        });
    }

    // ==============================
    // STRESS FORECASTING
    // ==============================
    async loadStressForecast() {
        const container = document.getElementById('stressForecastContainer');
        const insightEl = document.getElementById('forecastInsight');
        const insightText = document.getElementById('forecastInsightText');
        const confEl = document.getElementById('forecastConfidence');

        if (!container) return;

        try {
            const res = await fetch('/student/api/stress/forecast');
            const result = await res.json();

            if (res.ok && result.success && result.data.forecast.length > 0) {
                const data = result.data;
                
                // Update Confidence
                if (confEl) confEl.textContent = `AI Confidence: ${data.confidence}%`;

                // Render Forecast Items
                container.innerHTML = data.forecast.map(item => {
                    let levelClass = 'forecast-low'; // low stress (green)
                    if (item.score > 75) { levelClass = 'forecast-high'; }
                    else if (item.score > 55) { levelClass = 'forecast-moderate'; }
                    else if (item.score > 35) { levelClass = 'forecast-elevated'; }

                    return `
                        <div class="forecast-item ${levelClass}">
                            <div class="forecast-day">${esc(item.day)}</div>
                            <div class="forecast-score">${parseInt(item.score) || 0}</div>
                            <div class="forecast-label">Projected</div>
                        </div>
                    `;
                }).join('');

                // Render Insight
                if (insightEl && insightText) {
                    let msg = "";
                    if (data.trend === 'rising') {
                        msg = "Stress levels are trending upward. Consider scheduling a break or talking to someone.";
                    } else if (data.trend === 'declining') {
                        msg = "Great news! Your stress levels are projected to decrease over the next few days.";
                    } else {
                        msg = "Your emotional state appears stable. Keep up your current wellness routine.";
                    }
                    insightText.textContent = msg;
                    insightEl.style.display = 'block';
                }
            } else {
                container.innerHTML = `
                    <div style="flex: 1; text-align: center; padding: 20px; color: var(--muted); font-size: 12px;">
                        ${esc(result.data?.reason || "Not enough data for a forecast yet. Keep checking in!")}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Forecast error:', error);
            container.innerHTML = '<div style="flex: 1; text-align: center; padding: 10px; color: #ef4444; font-size: 12px;">Failed to load forecast.</div>';
        }
    }

    // ==============================
    // BURNOUT ANALYSIS
    // ==============================
    async loadBurnoutAnalysis() {
        const badge = document.getElementById('burnoutRiskBadge');
        const indicator = document.getElementById('burnoutRiskIndicator');
        const label = document.getElementById('burnoutRiskLabel');
        const factorsContainer = document.getElementById('burnoutFactors');
        const interventionEl = document.getElementById('burnoutIntervention');
        const interventionText = document.getElementById('burnoutInterventionText');

        if (!badge) return;

        try {
            const res = await fetch('/student/api/wellness/burnout');
            const result = await res.json();

            if (res.ok && result.success) {
                const data = result.data;
                
                // Update Risk Level
                const levels = {
                    'low': { color: '#22c55e', text: 'Low Risk', badge: 'Stable' },
                    'moderate': { color: '#f97316', text: 'Moderate Risk', badge: 'Watchful' },
                    'high': { color: '#ef4444', text: 'High Risk', badge: 'Critical' }
                };
                const config = levels[data.risk_level] || { color: '#64748b', text: 'Unknown', badge: 'Scanning' };
                
                if (badge) {
                    badge.textContent = config.badge;
                    badge.style.background = `${config.color}1a`;
                    badge.style.color = config.color;
                }
                if (indicator) indicator.style.background = config.color;
                if (label) label.textContent = config.text;

                // Render Factors
                if (factorsContainer && data.factors) {
                    factorsContainer.innerHTML = data.factors.map(f => `
                        <span style="font-size: 10px; padding: 4px 10px; background: var(--surface-muted); border-radius: 12px; color: var(--text-muted); font-weight: 500; border: 1px solid var(--border);">
                            ${esc(f)}
                        </span>
                    `).join('');
                }

                // Render Recommendation
                if (interventionEl && interventionText && data.intervention) {
                    interventionText.textContent = data.intervention;
                    interventionEl.style.display = 'block';
                    interventionEl.style.borderColor = config.color;
                    interventionEl.style.background = `${config.color}08`;
                }
            }
        } catch (error) {
            console.error('Burnout analysis error:', error);
        }
    }
}

// ============================================
// EXTRAORDINARY UI ENHANCEMENTS
// ============================================

// 1. Magnetic Button Effect
function initMagneticButtons() {
    const magneticElements = document.querySelectorAll('.btn-magnetic, .qa-card');

    magneticElements.forEach(el => {
        el.addEventListener('mousemove', (e) => {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;

            const moveX = x * 0.15;
            const moveY = y * 0.15;

            el.style.transform = `translate(${moveX}px, ${moveY}px) scale(1.05)`;
        });

        el.addEventListener('mouseleave', () => {
            el.style.transform = 'translate(0, 0) scale(1)';
        });
    });
}

// 2. Ripple Effect on Click
function createRipple(event, element) {
    const circle = document.createElement('span');
    const diameter = Math.max(element.clientWidth, element.clientHeight);
    const radius = diameter / 2;

    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${event.clientX - element.offsetLeft - radius}px`;
    circle.style.top = `${event.clientY - element.offsetTop - radius}px`;
    circle.classList.add('ripple');

    const ripple = element.getElementsByClassName('ripple')[0];
    if (ripple) ripple.remove();

    element.appendChild(circle);
}

// 3. 3D Card Tilt Effect — subtle only
function initCardTilt() {
    const cards = document.querySelectorAll('.card[data-tilt="true"]');

    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transition = 'transform 0.1s ease, box-shadow 0.5s cubic-bezier(0.34,1.56,0.64,1), border-color 0.5s cubic-bezier(0.34,1.56,0.64,1)';
        });

        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            // Max ±4° — gentle shimmer, not a jarring flip
            const rotateX = Math.max(-4, Math.min(4, (y - rect.height / 2) / rect.height * 8));
            const rotateY = Math.max(-4, Math.min(4, (rect.width / 2 - x) / rect.width * 8));

            card.style.transform = `perspective(1200px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(4px)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transition = 'transform 0.6s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.5s cubic-bezier(0.34,1.56,0.64,1), border-color 0.5s cubic-bezier(0.34,1.56,0.64,1)';
            card.style.transform = 'perspective(1200px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
        });
    });
}

// 4. Scroll Animations with Intersection Observer
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('cascade-item');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    document.querySelectorAll('.card, .qa-card').forEach(el => {
        observer.observe(el);
    });
}

// 5. Create Ambient Particles
function createAmbientParticles() {
    const container = document.createElement('div');
    container.className = 'ambient-particles';

    for (let i = 0; i < 5; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        container.appendChild(particle);
    }

    document.body.appendChild(container);
}

// Initialize all UI enhancements
function initUIEnhancements() {
    initMagneticButtons();
    initCardTilt();
    initScrollAnimations();
    createAmbientParticles();

    // Add ripple to buttons and interactive elements
    document.querySelectorAll('button, .btn, .qa-card').forEach(el => {
        if (!el.classList.contains('ripple-container')) {
            el.classList.add('ripple-container');
        }
        el.addEventListener('click', (e) => createRipple(e, el));
    });
}

document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new AdvancedDashboard();
    initUIEnhancements();
});

// Stop auto-refresh when leaving page
window.addEventListener('beforeunload', () => {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
    if (window.dashboard) {
        if (window.dashboard._pollingTimer) clearInterval(window.dashboard._pollingTimer);
        if (window.dashboard._dateTimer) clearInterval(window.dashboard._dateTimer);
    }
});
