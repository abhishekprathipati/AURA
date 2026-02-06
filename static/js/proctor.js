// AURA Proctor Dashboard - Institutional JS
// Phase 2: trend indicators, time filters, bulk actions, search, export, notifications

const state = {
  currentIncidentId: null,
  proctorId: 'UNKNOWN',
  selected: new Set(),
  lastHighCount: 0,
};

const elements = {};

function initElements() {
  elements.systemStatus = document.getElementById('system-status');
  elements.queueContainer = document.getElementById('queue-container');
  elements.actionPanel = document.getElementById('action-panel');
  elements.incidentDetails = document.getElementById('incident-details');
  elements.auditLogContainer = document.getElementById('audit-log-container');
  elements.proctorId = document.getElementById('proctor-id');
  elements.lastUpdate = document.getElementById('last-update');
  elements.statusFilter = document.getElementById('status-filter');
  elements.riskFilter = document.getElementById('risk-filter');
  elements.timeFilter = document.getElementById('time-filter');
  elements.searchInput = document.getElementById('search-input');
  elements.searchField = document.getElementById('search-field');
  elements.searchBtn = document.getElementById('search-btn');
  elements.bulkActionBar = document.getElementById('bulk-action-bar');
  elements.bulkCount = document.getElementById('bulk-count');
  elements.clearSelection = document.getElementById('clear-selection');
  elements.notificationStack = document.getElementById('notification-stack');
  elements.logDays = document.getElementById('log-days');
  elements.exportAudit = document.getElementById('export-audit');
  elements.refreshBtn = document.getElementById('refresh-btn');
  elements.metricsRefresh = document.getElementById('metrics-refresh');
}

function showNotification(message) {
  if (!elements.notificationStack) return;
  const wrapper = document.createElement('div');
  wrapper.className = 'notification';
  wrapper.innerHTML = `<span>⚠️ ${message}</span><button aria-label="Close">×</button>`;
  wrapper.querySelector('button').addEventListener('click', () => wrapper.remove());
  elements.notificationStack.appendChild(wrapper);
  setTimeout(() => wrapper.remove(), 5000);
}

async function loadSystemStatus() {
  try {
    const res = await fetch('/proctor/api/system/status');
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Failed');
    const status = data.data;
    elements.lastUpdate.textContent = `Last update: ${new Date(status.last_update).toLocaleTimeString()}`;
    elements.systemStatus.innerHTML = `
      <div class="status-card ${status.status.toLowerCase()}">
        <div class="subtext">SYSTEM STATUS</div>
        <div class="metric-value">${status.status}</div>
      </div>
      <div class="status-card">
        <div class="subtext">ACTIVE STUDENTS</div>
        <div class="metric-value">${status.active_students}</div>
      </div>
      <div class="status-card">
        <div class="subtext">ACTIVE ALERTS</div>
        <div class="metric-value">${status.active_alerts}</div>
      </div>
      <div class="status-card ${status.connection_hub_state.toLowerCase()}">
        <div class="subtext">CONNECTION HUB</div>
        <div class="metric-value">${status.connection_hub_state}</div>
      </div>
    `;
  } catch (err) {
    console.error('System status error:', err);
    elements.systemStatus.innerHTML = '<div class="error">Error loading system status</div>';
  }
}

function buildQueueUrl() {
  const params = new URLSearchParams();
  const status = elements.statusFilter.value;
  const risk = elements.riskFilter.value;
  const time = elements.timeFilter.value;
  if (status && status !== 'ALL') params.set('status', status);
  if (risk) params.set('risk_level', risk);
  if (time) params.set('time_range', time);
  return `/proctor/api/risk/queue${params.toString() ? `?${params.toString()}` : ''}`;
}

async function loadRiskQueue({ fromSearch = false } = {}) {
  try {
    const url = buildQueueUrl();
    const res = await fetch(url);
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Failed');

    if (data.count === 0) {
      renderNoIncidents(fromSearch ? 'No matches' : 'No incidents in queue');
      return data.count;
    }

    renderRiskTable(data.data);
    return data.count;
  } catch (err) {
    console.error('Risk queue error:', err);
    elements.queueContainer.innerHTML = '<div class="error">Error loading risk queue</div>';
    return 0;
  }
}

function renderNoIncidents(message) {
  elements.queueContainer.innerHTML = `<div class="loading">${message}</div>`;
  state.selected.clear();
  updateBulkBar();
}

function renderRiskTable(incidents) {
  state.selected = new Set([...state.selected].filter((id) => incidents.some((i) => i.incident_id === id)));

  let html = `
    <table>
      <thead>
        <tr>
          <th style="width:42px;"><input type="checkbox" id="select-all"></th>
          <th>Risk</th>
          <th>Trend</th>
          <th>Student</th>
          <th>Message</th>
          <th>Trigger</th>
          <th>Time</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
  `;

  incidents.forEach((incident) => {
    const trendClass = incident.trend === 'RISING' ? 'trend-up' : incident.trend === 'FALLING' ? 'trend-down' : 'trend-stable';
    const checked = state.selected.has(incident.incident_id) ? 'checked' : '';
    html += `
      <tr data-incident-id="${incident.incident_id}" class="incident-row">
        <td><input type="checkbox" class="row-select" data-id="${incident.incident_id}" ${checked}></td>
        <td>
          <span class="risk-badge risk-${incident.risk_level.toLowerCase()}">${incident.risk_level}</span>
        </td>
        <td><span class="trend-icon ${trendClass}">${incident.trend_icon}</span></td>
        <td><code>${incident.anonymous_student_id?.substring(0, 8) || '--'}...</code></td>
        <td>${incident.message_excerpt ? incident.message_excerpt.substring(0, 60) : ''}</td>
        <td>${(incident.trigger_source || '').replace('_', ' ')}</td>
        <td>${incident.time_since_trigger || ''}</td>
        <td>${incident.status}</td>
      </tr>
    `;
  });

  html += '</tbody></table>';
  elements.queueContainer.innerHTML = html;

  const selectAll = document.getElementById('select-all');
  selectAll.addEventListener('change', (e) => {
    const checked = e.target.checked;
    document.querySelectorAll('.row-select').forEach((cb) => {
      cb.checked = checked;
      toggleSelection(cb.dataset.id, checked);
    });
    updateBulkBar();
  });

  document.querySelectorAll('.row-select').forEach((cb) => {
    cb.addEventListener('change', (e) => {
      toggleSelection(cb.dataset.id, e.target.checked);
      updateBulkBar();
    });
  });

  document.querySelectorAll('.incident-row').forEach((row) => {
    row.addEventListener('click', (e) => {
      if (e.target && e.target.classList.contains('row-select')) return;
      selectIncident(row.dataset.incidentId);
    });
  });

  updateBulkBar();
}

function toggleSelection(id, checked) {
  if (checked) {
    state.selected.add(id);
  } else {
    state.selected.delete(id);
  }
}

function clearSelection() {
  state.selected.clear();
  document.querySelectorAll('.row-select').forEach((cb) => (cb.checked = false));
  updateBulkBar();
}

function updateBulkBar() {
  const count = state.selected.size;
  elements.bulkCount.textContent = count;
  if (count > 0) {
    elements.bulkActionBar.classList.remove('hidden');
  } else {
    elements.bulkActionBar.classList.add('hidden');
  }
}

async function runSearch() {
  const query = elements.searchInput.value.trim();
  const field = elements.searchField.value;
  if (query.length < 3) {
    showNotification('Search query must be at least 3 characters');
    return;
  }
  try {
    const params = new URLSearchParams({ q: query, field });
    const res = await fetch(`/proctor/api/risk/search?${params.toString()}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Search failed');
    if (data.count === 0) {
      renderNoIncidents('No matches');
      return;
    }
    state.selected.clear();
    renderRiskTable(data.data);
  } catch (err) {
    console.error('Search error:', err);
    showNotification('Search failed');
  }
}

async function selectIncident(incidentId) {
  state.currentIncidentId = incidentId;
  try {
    const res = await fetch(`/proctor/api/incidents/${incidentId}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Failed');
    const incident = data.data.incident;

    elements.incidentDetails.innerHTML = `
      <div class="detail-block">
        <div class="subtext">INCIDENT ID</div>
        <div class="mono">${incident.incident_id}</div>
      </div>
      <div class="detail-block">
        <div class="subtext">RISK</div>
        <div><span class="risk-badge risk-${incident.risk_level.toLowerCase()}">${incident.risk_level}</span> <span class="trend-icon ${incident.trend === 'RISING' ? 'trend-up' : incident.trend === 'FALLING' ? 'trend-down' : 'trend-stable'}">${incident.trend_icon}</span></div>
      </div>
      <div class="detail-block">
        <div class="subtext">TRIGGER</div>
        <div>${(incident.trigger_source || '').replace('_', ' ').toUpperCase()}</div>
      </div>
      <div class="detail-block">
        <div class="subtext">ROOM</div>
        <div>${incident.room_name || 'Unknown'}</div>
      </div>
      <div class="detail-block">
        <div class="subtext">MESSAGE EXCERPT</div>
        <div class="excerpt">"${incident.message_excerpt || 'No message content'}"</div>
      </div>
      <div class="detail-block">
        <div class="subtext">TIMESTAMP</div>
        <div>${new Date(incident.timestamp).toLocaleString()}</div>
      </div>
      <div class="detail-block">
        <div class="subtext">REPORTS</div>
        <div>${incident.report_count} report(s)</div>
      </div>
    `;

    elements.actionPanel.classList.remove('hidden');
  } catch (err) {
    console.error('Incident load error:', err);
    elements.incidentDetails.innerHTML = '<div class="error">Error loading incident details</div>';
  }
}

async function takeAction(actionType) {
  if (!state.currentIncidentId) {
    alert('No incident selected');
    return;
  }
  if (!confirm(`Are you sure you want to ${actionType.toUpperCase()} this incident?`)) return;

  try {
    const res = await fetch(`/proctor/api/action/${actionType}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        incident_id: state.currentIncidentId,
        reason: actionType === 'dismiss' ? 'FALSE_POSITIVE' : actionType === 'remove' ? 'POLICY_VIOLATION' : 'REQUIRES_FOLLOWUP',
        details: 'Action taken via proctor dashboard'
      })
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Failed');

    elements.actionPanel.innerHTML = `
      <div class="success">Incident ${actionType.toUpperCase()}D successfully</div>
      <div style="margin-top: 16px;"><button class="btn" onclick="window.location.reload()">Refresh Dashboard</button></div>
    `;
    await loadAuditLogs();
    await loadRiskQueue();
  } catch (err) {
    console.error('Action error:', err);
    alert(`Failed to ${actionType}: ${err.message}`);
  }
}

async function performBulkAction(actionType) {
  if (state.selected.size === 0) return;
  if (!confirm(`Apply ${actionType.toUpperCase()} to ${state.selected.size} incident(s)?`)) return;

  try {
    const res = await fetch('/proctor/api/action/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        incident_ids: Array.from(state.selected),
        action_type: actionType,
        reason: 'BULK_ACTION',
        details: 'Bulk action via proctor dashboard'
      })
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Failed');
    showNotification(`Bulk ${actionType} applied to ${data.processed} incident(s)`);
    state.selected.clear();
    await loadRiskQueue();
    await loadAuditLogs();
  } catch (err) {
    console.error('Bulk action error:', err);
    showNotification('Bulk action failed');
  }
}

async function loadAuditLogs() {
  const days = elements.logDays.value;
  try {
    const res = await fetch(`/proctor/api/audit/logs?days=${days}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Failed');
    if (data.count === 0) {
      elements.auditLogContainer.innerHTML = '<div class="loading">No audit entries</div>';
      return;
    }

    let html = '';
    data.data.forEach((log) => {
      const time = new Date(log.timestamp);
      html += `
        <div class="log-entry">
          <span class="timestamp">[${time.toLocaleDateString()} ${time.toLocaleTimeString()}]</span>
          <span class="primary">${log.proctor_name}</span>
          <span>${log.action_type}</span>
          <span class="muted">${log.incident_id.substring(0, 8)}...</span>
          <span class="muted" style="font-size:11px;">(${log.reason_code})</span>
        </div>
      `;
    });
    elements.auditLogContainer.innerHTML = html;
  } catch (err) {
    console.error('Audit log error:', err);
    elements.auditLogContainer.innerHTML = '<div class="error">Error loading audit log</div>';
  }
}

async function checkNewHighRiskIncidents() {
  try {
    const res = await fetch('/proctor/api/risk/queue?status=UNREVIEWED&risk_level=HIGH');
    const data = await res.json();
    if (!data.success) return;
    const count = data.count;
    if (count > state.lastHighCount) {
      showNotification('New HIGH risk incident detected');
    }
    state.lastHighCount = count;
  } catch (err) {
    console.error('High risk check error:', err);
  }
}

function startPolling() {
  setInterval(() => {
    loadSystemStatus();
    loadRiskQueue({ fromSearch: false });
    checkNewHighRiskIncidents();
  }, 30000);
}

function wireEvents() {
  elements.statusFilter.addEventListener('change', () => loadRiskQueue());
  elements.riskFilter.addEventListener('change', () => loadRiskQueue());
  elements.timeFilter.addEventListener('change', () => loadRiskQueue());
  elements.logDays.addEventListener('change', loadAuditLogs);
  elements.refreshBtn.addEventListener('click', () => {
    loadSystemStatus();
    loadRiskQueue();
    loadAuditLogs();
  });
  elements.searchBtn.addEventListener('click', runSearch);
  elements.searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runSearch();
  });
  document.querySelectorAll('[data-action]').forEach((btn) => {
    btn.addEventListener('click', () => takeAction(btn.dataset.action));
  });
  document.querySelectorAll('[data-bulk-action]').forEach((btn) => {
    btn.addEventListener('click', () => performBulkAction(btn.dataset.bulkAction));
  });
  elements.clearSelection.addEventListener('click', clearSelection);
  elements.exportAudit.addEventListener('click', () => {
    const days = elements.logDays.value;
    window.location.href = `/proctor/api/audit/export/csv?days=${days}`;
  });
  if (elements.metricsRefresh) {
    elements.metricsRefresh.addEventListener('click', loadResolutionMetrics);
  }
}

function init() {
  initElements();
  state.proctorId = document.body.dataset.proctorId || 'UNKNOWN';
  elements.proctorId.textContent = state.proctorId;
  loadSystemStatus();
  loadRiskQueue();
  loadAuditLogs();
  loadResolutionMetrics();
  wireEvents();
  startPolling();
  setInterval(loadResolutionMetrics, 120000);
}

document.addEventListener('DOMContentLoaded', init);

// Load resolution metrics
async function loadResolutionMetrics() {
  try {
    const response = await fetch('/proctor/api/metrics/resolution');
    const data = await response.json();
    if (!data.success) return;
    const metrics = data.data;
    document.getElementById('handled-today').textContent = metrics.handled_today;
    document.getElementById('total-today').textContent = metrics.total_today;
    document.getElementById('avg-time').textContent = `${metrics.avg_resolution_minutes} min`;
    document.getElementById('pending-high').textContent = metrics.pending_high_risk;
    const progressBar = document.getElementById('resolution-progress');
    const percentage = metrics.resolution_rate || 0;
    progressBar.style.width = `${percentage}%`;
    progressBar.style.backgroundColor = percentage >= 80 ? '#198754' : percentage >= 60 ? '#ffc107' : '#dc3545';
  } catch (error) {
    console.error('Failed to load resolution metrics:', error);
  }
}
