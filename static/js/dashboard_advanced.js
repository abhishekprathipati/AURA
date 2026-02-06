class AdvancedDashboard {
    constructor() {
        this.currentStress = 68;
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
        this.initCharts();
        this.initNavigation();
        this.initModals();
        await this.loadDashboardData();
        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.setupServiceWorker();
    }

    initDate() {
        const now = luxon.DateTime.now();
        const dateElement = document.getElementById('currentDate');
        if (dateElement) {
            dateElement.textContent = now.toLocaleString({
                weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
            });
        }
        setInterval(() => {
            const now = luxon.DateTime.now();
            const timeString = now.toLocaleString(luxon.DateTime.TIME_SIMPLE);
            const relativeTime = now.toRelative();
            const tsEl = document.getElementById('stressTimestamp');
            if (tsEl) tsEl.textContent = `${timeString} • ${relativeTime}`;
        }, 60000);
    }

    initTheme() {
        const themeToggle = document.getElementById('themeToggle');
        const savedTheme = localStorage.getItem('aura-theme') || 'light';
        
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
        localStorage.setItem('aura-theme', theme);
        
        const icon = document.getElementById('themeIcon');
        if (!icon) return;
        
        icon.innerHTML = theme === 'dark'
            ? `<circle cx="12" cy="12" r="5"/>
               <line x1="12" y1="1" x2="12" y2="4"/>
               <line x1="12" y1="20" x2="12" y2="23"/>
               <line x1="4.22" y1="4.22" x2="6.34" y2="6.34"/>
               <line x1="17.66" y1="17.66" x2="19.78" y2="19.78"/>
               <line x1="1" y1="12" x2="4" y2="12"/>
               <line x1="20" y1="12" x2="23" y2="12"/>
               <line x1="4.22" y1="19.78" x2="6.34" y2="17.66"/>
               <line x1="17.66" y1="6.34" x2="19.78" y2="4.22"/>`
            : `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`;
    }

    initCharts() {
        this.charts.stress = new ApexCharts(document.getElementById('stressChart'), {
            series: [{ name: 'Stress Level', data: [65, 62, 70, 68, 72, 68, 65] }],
            chart: { type: 'area', height: 200, toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: true, speed: 800 } },
            colors: ['#ef4444'],
            fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.7, opacityTo: 0.1, stops: [0, 90, 100] } },
            stroke: { curve: 'smooth', width: 3 },
            grid: { show: false },
            xaxis: { labels: { show: false } },
            yaxis: { labels: { show: false } },
            tooltip: { enabled: true, x: { show: false }, y: { formatter: (v) => `${v} stress`, title: { formatter: () => 'Stress:' } } },
            dataLabels: { enabled: false }
        });
        this.charts.stress.render();

        this.charts.analytics = new ApexCharts(document.getElementById('detailedChart'), {
            series: [ { name: 'Stress', data: [68, 72, 65, 70, 62, 68, 65] }, { name: 'Mood', data: [3, 3, 4, 3, 4, 3, 3] } ],
            chart: { type: 'bar', height: 240, toolbar: { show: false }, stacked: false },
            colors: ['#ef4444', '#3b82f6'],
            plotOptions: { bar: { horizontal: false, columnWidth: '70%', endingShape: 'rounded' } },
            dataLabels: { enabled: false },
            stroke: { show: true, width: 2, colors: ['transparent'] },
            xaxis: { categories: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], labels: { style: { colors: '#64748b', fontSize: '12px' } } },
            yaxis: { title: { text: 'Score', style: { color: '#64748b', fontSize: '12px' } }, labels: { style: { colors: '#64748b', fontSize: '11px' } } },
            fill: { opacity: 0.8 },
            tooltip: { y: { formatter: (val) => `${val} points` } },
            legend: { position: 'top', horizontalAlign: 'right', fontSize: '12px', markers: { radius: 12 } }
        });
        this.charts.analytics.render();
    }

    initNavigation() {
        const navFab = document.getElementById('navFab');
        const navMenu = document.getElementById('navMenu');
        if (navFab && navMenu) {
            navFab.addEventListener('click', (e) => { e.stopPropagation(); navMenu.classList.toggle('active'); });
            document.addEventListener('click', (e) => { if (!navMenu.contains(e.target) && !navFab.contains(e.target)) { navMenu.classList.remove('active'); } });
            navMenu.querySelectorAll('.nav-item').forEach(item => { item.addEventListener('click', () => navMenu.classList.remove('active')); });
        }
    }

    initModals() {
        this.modals.support = document.getElementById('supportModal');
        const reqBtn = document.getElementById('requestSupportBtn');
        const closeBtn = document.getElementById('closeModalBtn');
        const cancelBtn = document.getElementById('cancelBtn');
        if (reqBtn) reqBtn.addEventListener('click', () => this.openModal('support'));
        if (closeBtn) closeBtn.addEventListener('click', () => this.closeModal('support'));
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.closeModal('support'));
        if (this.modals.support) {
            this.modals.support.addEventListener('click', (e) => { if (e.target === this.modals.support) this.closeModal('support'); });
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
            this.updateStressDisplay(wellnessData);
            this.updateActivityDisplay(activityData);
            if (historyData?.history) this.updateChartsData(historyData.history);
            this.updateActivityTimeline();
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showErrorState();
        } finally { this.showLoading(false); }
    }

    async fetchData(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    }

    updateStressDisplay(data) {
        const stress = data.stress || {};
        this.currentStress = stress.value ?? 50;
        document.getElementById('stressValue').textContent = this.currentStress;
        const descriptor = stress.label || this.getStressDescriptor(this.currentStress);
        document.getElementById('stressDescriptor').textContent = descriptor;
        const trend = stress.trend || 'stable';
        const trendIndicator = document.getElementById('trendIndicator');
        const trendLabel = document.getElementById('trendLabel');
        if (trendIndicator) {
            trendIndicator.textContent = trend === 'up' ? '↑' : (trend === 'down' ? '↓' : '=');
        }
        if (trendLabel) {
            trendLabel.textContent = trend === 'up' ? 'Increasing' : (trend === 'down' ? 'Decreasing' : 'Stable');
        }
        const fill = document.getElementById('stressIndicatorFill');
        if (fill) fill.style.width = `${Math.min(Math.max(this.currentStress, 0), 100)}%`;
    }

    getStressDescriptor(value) { if (value <= 30) return 'Relaxed'; if (value <= 50) return 'Manageable'; if (value <= 70) return 'Elevated'; return 'High'; }


    updateActivityDisplay(data) {
        document.getElementById('checkinsToday').textContent = data.today ?? 4;
        document.getElementById('checkinsWeek').textContent = data.week ?? 28;
        const weeklyAvgEl = document.getElementById('weeklyAverage');
        if (weeklyAvgEl) weeklyAvgEl.textContent = data.weekly_average ?? 46;
        const weeklyChangeEl = document.getElementById('weeklyChange');
        if (weeklyChangeEl) weeklyChangeEl.textContent = data.weekly_change ?? '-12%';
    }

    updateChartsData(historyData) {
        if (!historyData.length) return;
        const stressData = historyData.map(h => h.score ?? 50);
        const dates = historyData.map(h => luxon.DateTime.fromISO(h.timestamp).toFormat('EEE'));
        this.charts.stress.updateSeries([{ data: stressData }]);
        if (this.charts.analytics) {
            this.charts.analytics.updateOptions({ xaxis: { categories: dates } });
            this.charts.analytics.updateSeries([
                { data: stressData },
                { data: stressData.map(s => Math.max(1, Math.min(5, Math.round((100 - s) / 20)))) }
            ]);
        }
    }

    updateChartsTheme(theme) {
        const textColor = theme === 'dark' ? '#cbd5e1' : '#64748b';
        this.charts.analytics.updateOptions({
            xaxis: { labels: { style: { colors: textColor } } },
            yaxis: { labels: { style: { colors: textColor } }, title: { style: { color: textColor } } }
        });
    }

    updateActivityTimeline() {
        const now = luxon.DateTime.now();
        const activities = [
            { icon: 'fa-heartbeat', title: 'Stress Check-in', time: now.minus({ minutes: 15 }).toFormat('HH:mm'), detail: `Stress: ${this.currentStress}` },
            { icon: 'fa-brain', title: 'Mood Assessment', time: now.minus({ hours: 2 }).toFormat('HH:mm'), detail: 'Mood: Neutral' },
            { icon: 'fa-wind', title: 'Breathing Exercise', time: now.minus({ hours: 3 }).toFormat('HH:mm'), detail: 'Duration: 3min' },
            { icon: 'fa-book', title: 'Study Session', time: now.minus({ hours: 5 }).toFormat('HH:mm'), detail: 'Duration: 45min' }
        ];
        const timeline = document.getElementById('activityTimeline');
        if (!timeline) return;
        timeline.innerHTML = activities.map(a => `
            <div class="activity-item">
                <div class="activity-icon"><i class="fas ${a.icon}"></i></div>
                <div class="activity-content">
                    <div class="activity-title">${a.title}</div>
                    <div class="activity-time">${a.time} • ${a.detail}</div>
                </div>
            </div>
        `).join('');
    }

    setupEventListeners() {
        document.querySelectorAll('.btn-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                this.handleAction(action);
            });
        });
        document.addEventListener('keydown', (e) => {
            if (e.altKey) {
                switch (e.key) {
                    case 'b': this.handleAction('breathing'); break;
                    case 's': this.handleAction('stretch'); break;
                    case 'h': this.openModal('support'); break;
                }
            }
        });
        const form = document.getElementById('supportForm');
        if (form) form.addEventListener('submit', (e) => { e.preventDefault(); this.submitSupportRequest(); });
    }

    async handleAction(action) {
        const feedback = document.getElementById('actionFeedback');
        if (feedback) { feedback.textContent = 'Processing...'; feedback.className = 'text-sm text-info'; }
        try {
            const response = await fetch('/student/api/quick_actions', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action })
            });
            const data = await response.json();
            if (response.ok) {
                const newStress = data.new_stress ?? data.stress_score ?? this.currentStress;
                if (feedback) { feedback.textContent = `Stress adjusted to ${newStress}`; feedback.className = 'text-sm text-success'; }
                this.animateValueChange('stressValue', this.currentStress, newStress, 500);
                this.currentStress = newStress;
                document.getElementById('stressDescriptor').textContent = this.getStressDescriptor(this.currentStress);
                this.addToActivityTimeline(action, newStress);
                setTimeout(() => { if (feedback) feedback.textContent = ''; }, 3000);
            } else {
                throw new Error('Action failed');
            }
        } catch (error) {
            if (feedback) { feedback.textContent = 'Action failed. Please try again.'; feedback.className = 'text-sm text-error'; }
            console.error('Action error:', error);
            setTimeout(() => { if (feedback) feedback.textContent = ''; }, 3000);
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
        const actionNames = { breathing: 'Breathing Exercise', stretch: 'Stretch Session' };
        const timeline = document.getElementById('activityTimeline');
        if (!timeline) return;
        const div = document.createElement('div');
        div.className = 'activity-item';
        div.innerHTML = `
            <div class="activity-icon"><i class="fas fa-check-circle"></i></div>
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
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
        try {
            const response = await fetch('/student/api/support/request', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ notes: `[${formData.category.toUpperCase()}:${formData.priority.toUpperCase()}] ${formData.subject}: ${formData.description}`, metadata: formData })
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
            console.error('Support request error:', error);
            alert('Failed to submit support request. Please try again.');
        } finally { submitBtn.disabled = false; submitBtn.textContent = originalText; }
    }

    startRealTimeUpdates() {
        setInterval(async () => {
            try {
                const response = await fetch('/student/api/wellness/current');
                if (response.ok) {
                    const data = await response.json();
                    this.updateStressDisplay(data);
                }
            } catch (e) { console.error('Real-time update error:', e); }
        }, 30000);
        setInterval(() => this.initDate(), 60000);
    }

    showLoading(show) { this.isLoading = show; }
    showErrorState() { console.log('Showing error state'); }

    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/service-worker.js').catch(err => {
                    console.log('ServiceWorker registration failed:', err);
                });
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => { window.dashboard = new AdvancedDashboard(); });
