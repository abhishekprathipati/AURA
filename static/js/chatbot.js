// Chat interface functionality: send, receive, display, quick actions
// NO ES modules - standalone implementation

const LS_CHATS = 'aura_chats';
const LS_RECENT_FILES = 'aura_recent_files';
const MOOD_LOG_KEY = 'aura_mood_log';

let currentChatId = null;
let moodChart = null;
let studyStressNoted = false;

// LocalStorage helpers
function uid() { return 'c_' + Math.random().toString(36).slice(2) + Date.now().toString(36); }

function getChats() {
  const raw = localStorage.getItem(LS_CHATS);
  const parsed = raw ? JSON.parse(raw) : [];
  return parsed.map((c) => ({ kind: 'study', ...c }));
}

function saveChats(chats) { localStorage.setItem(LS_CHATS, JSON.stringify(chats)); }

function createChat(title = 'Untitled Chat', kind = 'study') {
  const chat = { id: uid(), title, kind, messages: [], files: [], createdAt: Date.now() };
  const chats = getChats();
  chats.unshift(chat);
  saveChats(chats);
  return chat;
}

function addMessage(chatId, role, text) {
  const chats = getChats();
  const chat = chats.find(c => c.id === chatId);
  if (!chat) return;
  chat.messages.push({ role, text, ts: Date.now() });
  saveChats(chats);
}

function getChat(chatId) { return getChats().find(c => c.id === chatId); }

function listChatsByKind(kind) { return getChats().filter(c => c.kind === kind); }

// DOM selectors
const chatBox = () => document.getElementById('chatBox');
const chatInput = () => document.querySelector('[data-chat-input]');
const chatForm = () => document.querySelector('[data-chat-form]');
const stressIndicator = () => document.querySelector('[data-stress-indicator]');
const historyList = () => document.querySelector('[data-history-list]');
const localHistoryList = () => document.querySelector('[data-local-history]');
const feedbackStatsList = () => document.querySelector('[data-feedback-stats]');
const newChatBtn = () => document.getElementById('newChatBtn');

function ensureMentalChat() {
    const existing = listChatsByKind('mental')[0];
    if (existing) { currentChatId = existing.id; return existing; }
    const chat = createChat('Mental Wellness', 'mental');
    currentChatId = chat.id;
    return chat;
}

function appendMessage(role, text, timestamp = null, persist = true) {
    const cont = chatBox();
    if (!cont) return;

    const ts = timestamp ? new Date(timestamp) : new Date();

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role === 'user' ? 'chat-user' : 'chat-bot'}`;
    bubble.dataset.role = role;
    bubble.dataset.ts = ts.toISOString();

    const content = document.createElement('div');
    content.className = 'bubble-content';
    content.textContent = text;

    const time = document.createElement('div');
    time.className = 'bubble-time';
    time.textContent = ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    bubble.appendChild(content);
    bubble.appendChild(time);

    if (role === 'bot') {
        const actions = document.createElement('div');
        actions.className = 'bubble-actions';
        actions.innerHTML = `
            <button class="bubble-action-btn" data-action="copy">Copy</button>
            <button class="bubble-action-btn" data-action="thumbs-up">👍</button>
            <button class="bubble-action-btn" data-action="thumbs-down">👎</button>
        `;
        bubble.appendChild(actions);
    }
    cont.appendChild(bubble);
    setTimeout(() => { 
        if (cont) cont.scrollTop = cont.scrollHeight; 
    }, 10);

    if (persist) {
        ensureMentalChat();
        addMessage(currentChatId, role, text);
    }
}

function showTyping() {
    const cont = chatBox();
    if (!cont) return;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bot typing-indicator';
    bubble.innerHTML = `<div class="typing"><span></span><span></span><span></span></div>`;
    bubble.id = 'typing-indicator';
    cont.appendChild(bubble);
    setTimeout(() => { 
        if (cont) cont.scrollTop = cont.scrollHeight; 
    }, 10);
}

function removeTyping() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
}

function updateStressIndicator(sentiment) {
    const ind = stressIndicator();
    if (!ind) return;
    const levels = {
        anxious: { color: '#f39c12', label: 'Anxious', level: 3 },
        negative: { color: '#e74c3c', label: 'Stressed', level: 3 },
        neutral: { color: '#95a5a6', label: 'Neutral', level: 1 },
        positive: { color: '#27ae60', label: 'Calm', level: 0 },
    };
    const levelInfo = levels[sentiment] || levels.neutral;
    ind.style.setProperty('--indicator-color', levelInfo.color);
    const label = document.querySelector('[data-indicator-label]');
    if (label) label.textContent = levelInfo.label;

    if (levelInfo.level >= 3) {
        injectStressTipChip();
    }

    logMood(levelInfo.label, levelInfo.level);
}

function injectStressTipChip() {
    const row = document.querySelector('.chip-container');
    if (!row || document.getElementById('stress-tip-chip')) return;
    const btn = document.createElement('button');
    btn.className = 'chip';
    btn.id = 'stress-tip-chip';
    btn.dataset.quickResponse = '1';
    btn.dataset.moodLevel = '3';
    btn.textContent = 'Try Pomodoro + breaks';
    row.prepend(btn);
}

function logMood(label, level) {
    const raw = localStorage.getItem(MOOD_LOG_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    arr.push({ ts: Date.now(), label, level });
    localStorage.setItem(MOOD_LOG_KEY, JSON.stringify(arr.slice(-200)));
    renderMoodChart();
}

function buildMoodSeries() {
    const raw = localStorage.getItem(MOOD_LOG_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    const now = Date.now();
    const days = Array.from({ length: 7 }, (_, i) => {
        const dayStart = new Date(now - (6 - i) * 86400000);
        dayStart.setHours(0,0,0,0);
        return dayStart.getTime();
    });
    const labels = days.map(d => new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
    const values = days.map((d, idx) => {
        const next = idx === days.length - 1 ? d + 86400000 : days[idx + 1];
        const slice = arr.filter(a => a.ts >= d && a.ts < next);
        if (!slice.length) return 0;
        const avg = slice.reduce((s, a) => s + (a.level || 0), 0) / slice.length;
        return Math.round(avg * 100) / 100;
    });
    return { labels, values };
}

function renderMoodChart() {
    const ctx = document.getElementById('moodTrendChart');
    if (!ctx || typeof Chart === 'undefined') return;
    const { labels, values } = buildMoodSeries();
    if (moodChart) {
        moodChart.data.labels = labels;
        moodChart.data.datasets[0].data = values;
        moodChart.update();
        return;
    }
    moodChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Stress level',
                data: values,
                borderColor: '#7c3aed',
                backgroundColor: 'rgba(124,58,237,0.12)',
                tension: 0.35,
                fill: true,
                pointRadius: 4,
            }],
        },
        options: {
            scales: { y: { beginAtZero: true, max: 4, ticks: { stepSize: 1 } } },
            plugins: { legend: { display: false } },
            responsive: true,
            maintainAspectRatio: false,
        },
    });
}

function handleChipClick(btn) {
    const text = btn.textContent.trim();
    const level = parseInt(btn.dataset.moodLevel || '1', 10);
    const input = chatInput();
    const form = chatForm();
    if (input) input.value = text;
    logMood(text, level);

    if (!studyStressNoted && level >= 3 && hasRecentIntenseStudy()) {
        appendMessage('bot', "I noticed you've been studying hard lately. No wonder you're stressed—let's take a 5-minute breathing break.", null, true);
        studyStressNoted = true;
    }
    if (form && typeof form.requestSubmit === 'function') {
        form.requestSubmit();
    } else if (form) {
        form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }
}

function hasRecentIntenseStudy() {
    const now = Date.now();
    const twoHours = 2 * 60 * 60 * 1000;
    const studyChats = getChats().filter((c) => (c.kind === 'study') && c.createdAt && (now - c.createdAt) <= twoHours);
    return studyChats.length >= 3;
}

async function sendMessage(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    const input = chatInput();
    if (!input || !input.value.trim()) return;

    ensureMentalChat();
    const message = input.value.trim();
    input.value = '';
    
    console.log('[mental] Sending message:', message);

    appendMessage('user', message, null, true);
    showTyping();

    try {
        const res = await fetch('/api/chat/mental', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ message }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        removeTyping();
        appendMessage('bot', data.ai_response, data.timestamp, true);
        updateStressIndicator(data.sentiment);
    } catch (err) {
        removeTyping();
        appendMessage('bot', `I had trouble responding. Please try again. (${err.message})`, null, true);
        console.error('Chat error:', err);
    }

    input.focus();
    renderUnifiedHistory();
    renderLocalHistory();
}

function renderUnifiedHistory() {
    const list = historyList();
    if (!list) return;
    const chats = getChats();
    list.innerHTML = '';
    chats.forEach((c) => {
        const li = document.createElement('li');
        li.className = 'card-list-item';
        li.textContent = c.title || 'Untitled';
        li.addEventListener('click', () => loadChatFromStorage(c.id));
        list.appendChild(li);
    });
    if (!list.children.length) {
        list.innerHTML = '<li class="card-list-item">No history yet</li>';
    }
}

function renderLocalHistory() {
    const list = localHistoryList();
    if (!list) return;
    const chats = listChatsByKind('mental');
    list.innerHTML = '';
    chats.forEach((c) => {
        const li = document.createElement('li');
        li.className = 'card-list-item';
        li.textContent = c.title || 'Untitled';
        li.addEventListener('click', () => loadChatFromStorage(c.id));
        list.appendChild(li);
    });
    if (!list.children.length) {
        list.innerHTML = '<li class="card-list-item">No history yet</li>';
    }
}

function renderFeedbackStats() {
    const list = feedbackStatsList();
    if (!list) return;
    const log = JSON.parse(localStorage.getItem('aura_feedback_log') || '[]');
    const up = log.filter(l => l.action === 'thumbs-up').length;
    const down = log.filter(l => l.action === 'thumbs-down').length;
    list.innerHTML = '';
    if (log.length) {
        list.innerHTML = `
          <li class="card-list-item"><strong>👍</strong> ${up}</li>
          <li class="card-list-item"><strong>👎</strong> ${down}</li>
        `;
    } else {
        list.innerHTML = '<li class="card-list-item">No feedback yet</li>';
    }
}

function loadChatFromStorage(chatId) {
    const chat = getChat(chatId);
    if (!chat) return;
    currentChatId = chatId;
    const cont = chatBox();
    if (cont) cont.innerHTML = '';
    (chat.messages || []).forEach((m) => {
        const role = m.role === 'bot' || m.role === 'aura' ? 'bot' : 'user';
        appendMessage(role, m.text, m.ts, false);
    });
}

function handleBubbleActions(e) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const bubble = btn.closest('.chat-bubble');
    if (!bubble) return;
    const textNode = bubble.querySelector('.bubble-content');
    const text = textNode ? textNode.textContent : '';
    const action = btn.dataset.action;
    if (action === 'copy' && navigator.clipboard) {
        navigator.clipboard.writeText(text).catch(() => {});
    }
    if (action === 'thumbs-up' || action === 'thumbs-down') {
        const log = JSON.parse(localStorage.getItem('aura_feedback_log') || '[]');
        log.push({ ts: Date.now(), action, text });
        localStorage.setItem('aura_feedback_log', JSON.stringify(log.slice(-200)));
        renderFeedbackStats();
        sendFeedbackToBackend(action, text);
    }
}

async function sendFeedbackToBackend(action, text) {
    try {
        await fetch('/api/chat/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ action, text }),
        });
    } catch (err) {
        console.warn('Feedback send failed', err);
    }
}

function init() {
    ensureMentalChat();
    renderUnifiedHistory();
    renderLocalHistory();
    loadChatFromStorage(currentChatId);

    const form = chatForm();
    if (form) form.addEventListener('submit', sendMessage);

    const newBtn = newChatBtn();
    if (newBtn) newBtn.addEventListener('click', () => {
        const c = createChat('New Chat', 'mental');
        currentChatId = c.id;
        const cont = chatBox();
        if (cont) cont.innerHTML = '';
        renderUnifiedHistory();
        renderLocalHistory();
        chatInput()?.focus();
    });

    attachQuickResponses();
    document.addEventListener('click', handleBubbleActions);
    renderMoodChart();
    renderFeedbackStats();
    chatInput()?.focus();
}

window.addEventListener('DOMContentLoaded', init);

function hasRecentIntenseStudy() {
    const now = Date.now();
    const twoHours = 2 * 60 * 60 * 1000;
    const studyChats = getChats().filter((c) => (c.kind === 'study') && c.createdAt && (now - c.createdAt) <= twoHours);
    return studyChats.length >= 3;
}

function attachQuickResponses() {
    const row = document.querySelector('.chip-container');
    if (!row) return;
    row.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-quick-response]');
        if (!btn) return;
        handleChipClick(btn);
    });
}

function attachClearHistory() {
    const clearBtn = document.querySelector('[data-clear-history]');
    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            if (confirm('Clear chat history? This cannot be undone.')) {
                try {
                    await fetch('/api/chat/clear', { method: 'POST', credentials: 'include' });
                    const cont = chatBox();
                    if (cont) cont.innerHTML = '';
                    chatInput().focus();
                } catch (err) {
                    console.warn('Clear failed', err);
                }
            }
        });
    }
}

async function sendMessage(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    const input = chatInput();
    if (!input || !input.value.trim()) return;

    ensureMentalChat();
    const message = input.value.trim();
    input.value = '';

    appendMessage('user', message, null, true);
    showTyping();

    try {
        const res = await fetch('/api/chat/mental', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ message }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        removeTyping();
        appendMessage('bot', data.ai_response, data.timestamp, true);
        updateStressIndicator(data.sentiment);
    } catch (err) {
        removeTyping();
        appendMessage('bot', `I had trouble responding. Please try again. (${err.message})`, null, true);
        console.error('Chat error:', err);
    }

    input.focus();
    renderUnifiedHistory();
    renderLocalHistory();
}

function exportChat() {
    const container = chatBox();
    if (!container) return;
    const items = container.querySelectorAll('.chat-bubble');
    const lines = [];
    items.forEach((el) => {
        const role = el.dataset.role === 'user' ? 'Student' : 'AURA';
        const ts = el.dataset.ts ? new Date(el.dataset.ts) : new Date();
        const time = ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const textNode = el.querySelector('.bubble-content');
        const text = textNode ? textNode.textContent : '';
        lines.push(`[${time}] ${role}: ${text.trim()}`);
    });
    const content = lines.join('\n');
    downloadText(`AURA_Transcript_${new Date().toISOString().slice(0,10)}.txt`, content || 'No conversation yet.');
}

function downloadText(filename, text) {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

function renderUnifiedHistory() {
    const list = historyList();
    if (!list) return;
    const chats = getChats();
    list.innerHTML = '';
    chats.forEach((c) => {
        const li = document.createElement('li');
        li.className = 'card-list-item';
        li.textContent = c.title || 'Untitled';
        li.addEventListener('click', () => loadChatFromStorage(c.id));
        list.appendChild(li);
    });
    if (!list.children.length) {
        list.innerHTML = '<li class="card-list-item">No history yet</li>';
    }
}

function renderLocalHistory() {
    const list = localHistoryList();
    if (!list) return;
    const chats = listChatsByKind('mental');
    list.innerHTML = '';
    chats.forEach((c) => {
        const li = document.createElement('li');
        li.className = 'card-list-item';
        li.textContent = c.title || 'Untitled';
        li.addEventListener('click', () => loadChatFromStorage(c.id));
        list.appendChild(li);
    });
    if (!list.children.length) {
        list.innerHTML = '<li class="card-list-item">No history yet</li>';
    }
}

function loadChatFromStorage(chatId) {
    const chat = getChat(chatId);
    if (!chat) return;
    currentChatId = chatId;
    const cont = chatBox();
    if (cont) cont.innerHTML = '';
    (chat.messages || []).forEach((m) => {
        const role = m.role === 'bot' || m.role === 'aura' ? 'bot' : 'user';
        appendMessage(role, m.text, m.ts, false);
    });
}

function handleBubbleActions(e) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const bubble = btn.closest('.chat-bubble');
    if (!bubble) return;
    const textNode = bubble.querySelector('.bubble-content');
    const text = textNode ? textNode.textContent : '';
    const action = btn.dataset.action;
    if (action === 'copy' && navigator.clipboard) {
        navigator.clipboard.writeText(text).catch(() => {});
    }
    if (action === 'thumbs-up' || action === 'thumbs-down') {
        const log = JSON.parse(localStorage.getItem('aura_feedback_log') || '[]');
        log.push({ ts: Date.now(), action, text });
        localStorage.setItem('aura_feedback_log', JSON.stringify(log.slice(-200)));
        renderFeedbackStats();
        sendFeedbackToBackend(action, text);
    }
}

function renderFeedbackStats() {
    const list = feedbackStatsList();
    if (!list) return;
    const log = JSON.parse(localStorage.getItem('aura_feedback_log') || '[]');
    const up = log.filter(l => l.action === 'thumbs-up').length;
    const down = log.filter(l => l.action === 'thumbs-down').length;
    list.innerHTML = '';
    if (log.length) {
        list.innerHTML = `
          <li class="card-list-item"><strong>👍</strong> ${up}</li>
          <li class="card-list-item"><strong>👎</strong> ${down}</li>
        `;
    } else {
        list.innerHTML = '<li class="card-list-item">No feedback yet</li>';
    }
}

function init() {
    console.log('[mental] init() called');
    ensureMentalChat();
    renderUnifiedHistory();
    renderLocalHistory();
    loadChatFromStorage(currentChatId);

    const form = chatForm();
    console.log('[mental] form element:', form);
    if (form) {
        form.addEventListener('submit', sendMessage);
        console.log('[mental] form listener attached');
    }

    const newBtn = newChatBtn();
    if (newBtn) newBtn.addEventListener('click', () => {
        const c = createChat('New Chat', 'mental');
        currentChatId = c.id;
        const cont = chatBox();
        if (cont) cont.innerHTML = '';
        renderUnifiedHistory();
        renderLocalHistory();
        chatInput()?.focus();
    });

    attachQuickResponses();
    attachClearHistory();
    const exportBtn = document.getElementById('exportChatBtn');
    if (exportBtn) exportBtn.addEventListener('click', exportChat);

    document.addEventListener('click', handleBubbleActions);

    renderMoodChart();
    renderFeedbackStats();
    chatInput()?.focus();
    console.log('[mental] init() complete');
}

window.addEventListener('DOMContentLoaded', init);
