// ============================================================
// AURA MENTAL CHAT ENGINE v3 — Ultra Pro
// Features: history context, word-reveal, message actions,
//           mood shortcuts, zen mode, keyboard shortcuts
// ============================================================
(function () {
'use strict';

// ── State ──────────────────────────────────────────────────
let isGenerating = false;
let abortCtrl    = null;
let currentId    = null;
let localHistory = [];   // [{role:'user'|'assistant', content:'...'}]
let chats        = [];
const LS_KEY     = 'aura_mental_chats_v3';

// ── Element cache ───────────────────────────────────────────
const el = {};

// ── Marked.js config ───────────────────────────────────────
function configureMd() {
  if (typeof marked === 'undefined') return;
  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false,
  });
}

// ── Init ───────────────────────────────────────────────────
function initChat() {
  configureMd();
  cacheElements();
  loadChats();
  renderHistory();
  attachEventListeners();
  restoreZenMode();
  setupScrollDetection();
}

function cacheElements() {
  el.layout      = document.getElementById('mcLayout');
  el.messages    = document.getElementById('mcMessages');
  el.welcome     = document.getElementById('mcWelcome');
  el.input       = document.getElementById('mcInput');
  el.sendBtn     = document.getElementById('mcSend');
  el.inputPill   = document.getElementById('mcInputPill');
  el.historyList = document.getElementById('mcHistoryList');
  el.newChat     = document.getElementById('mcNewChat');
  el.zenBtn      = document.getElementById('mcZenBtn');
  el.statusDot   = document.getElementById('mcStatusDot');
  el.scrollBtn   = document.getElementById('mcScrollBtn');
  el.chips       = document.getElementById('mcChips');
  el.moodBtns    = document.querySelectorAll('.mc-mood-btn');
}

// ── Event listeners ─────────────────────────────────────────
function attachEventListeners() {
  // Send button
  el.sendBtn?.addEventListener('click', onSend);

  // Textarea: Enter to send, Shift+Enter for newline, auto-grow
  el.input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  });

  el.input?.addEventListener('input', () => {
    autoGrow();
    updateSendState();
  });

  el.input?.addEventListener('focus', () => el.inputPill?.classList.add('focused'));
  el.input?.addEventListener('blur',  () => el.inputPill?.classList.remove('focused'));

  // New chat
  el.newChat?.addEventListener('click', startNewChat);

  // Zen mode
  el.zenBtn?.addEventListener('click', toggleZen);

  // Mood soft-prompt buttons
  el.moodBtns?.forEach(btn => {
    btn.addEventListener('click', () => {
      const mood = btn.dataset.mood || '';
      const label = btn.querySelector('span')?.parentElement?.textContent?.trim() || mood;
      if (el.input) {
        el.input.value = `I'm feeling ${label.toLowerCase()} right now`;
        el.input.focus();
        autoGrow();
        updateSendState();
      }
    });
  });

  // Welcome chips
  el.chips?.querySelectorAll('.mc-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.dataset.prompt;
      if (prompt && el.input) {
        el.input.value = prompt;
        autoGrow();
        updateSendState();
        el.input.focus();
        setTimeout(onSend, 80);
      }
    });
  });

  // Scroll button
  el.scrollBtn?.addEventListener('click', scrollToBottom);

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const tag = document.activeElement?.tagName;
    // / to focus input (when not already in input)
    if (e.key === '/' && tag !== 'TEXTAREA' && tag !== 'INPUT') {
      e.preventDefault();
      el.input?.focus();
    }
    // Ctrl+Z for zen mode
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
      // only if not textarea
      if (tag !== 'TEXTAREA' && tag !== 'INPUT') {
        e.preventDefault();
        toggleZen();
      }
    }
    // Ctrl+N new chat
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
      e.preventDefault();
      startNewChat();
    }
    // Escape cancel
    if (e.key === 'Escape' && isGenerating && abortCtrl) {
      abortCtrl.abort();
    }
  });
}

// ── Auto-resize textarea ────────────────────────────────────
function autoGrow() {
  if (!el.input) return;
  el.input.style.height = 'auto';
  el.input.style.height = Math.min(el.input.scrollHeight, 140) + 'px';
}

function updateSendState() {
  const hasText = (el.input?.value?.trim().length || 0) > 0;
  if (el.sendBtn) el.sendBtn.disabled = isGenerating && !hasText;
}

// ── Scroll detection (show/hide scroll button) ──────────────
function setupScrollDetection() {
  if (!el.messages) return;
  el.messages.addEventListener('scroll', () => {
    const { scrollTop, scrollHeight, clientHeight } = el.messages;
    const atBottom = scrollHeight - scrollTop - clientHeight < 80;
    el.scrollBtn?.classList.toggle('hidden', atBottom);
  });
}

function scrollToBottom(smooth = true) {
  if (!el.messages) return;
  el.messages.scrollTo({ top: el.messages.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
}

// ── Send message ────────────────────────────────────────────
async function onSend() {
  if (isGenerating) return;
  const text = el.input?.value?.trim();
  if (!text) { shakeInput(); return; }

  // Hide welcome
  hideWelcome();

  // Create chat session on first message
  if (!currentId) {
    currentId = createChatId();
    chats.unshift({
      id: currentId,
      title: text.slice(0, 44) + (text.length > 44 ? '…' : ''),
      messages: [],
      createdAt: Date.now(),
    });
    savePersistence();
    renderHistory();
  }

  // Append user bubble
  appendMessage('user', text);

  // Push to local history
  localHistory.push({ role: 'user', content: text });

  // Clear input
  el.input.value = '';
  el.input.style.height = 'auto';

  // Set busy
  setBusy(true);

  // Add typing indicator
  const typingEl = addTypingIndicator();

  try {
    abortCtrl = new AbortController();

    const response = await fetch('/api/chat/mental', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        conversation_id: currentId,
        // Send last 10 turns as client-side context injection
        conversation_history: localHistory.slice(-10),
      }),
      signal: abortCtrl.signal,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      if (response.status === 403 && (errData.demo_limited || errData.demo_restricted)) {
        removeEl(typingEl);
        appendMessage('bot', '⚠️ ' + (errData.message || 'Demo limit reached. Register for unlimited access.'));
        setBusy(false);
        return;
      }
      throw new Error(errData.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    removeEl(typingEl);

    const reply = data.ai_response || data.reply || data.message || 'No response received.';

    // Reveal AI reply with word-by-word animation
    await appendMessageReveal('bot', reply);

    // Update local history
    localHistory.push({ role: 'assistant', content: reply });

    // Persist
    const chat = chats.find(c => c.id === currentId);
    if (chat) {
      chat.messages.push({ role: 'user', text, ts: Date.now() });
      chat.messages.push({ role: 'bot',  text: reply, ts: Date.now() });
      savePersistence();
    }

  } catch (err) {
    removeEl(typingEl);
    if (err.name !== 'AbortError') {
      appendMessage('bot', 'Something went wrong. Please try again.');
    }
  } finally {
    setBusy(false);
    abortCtrl = null;
  }
}

function shakeInput() {
  el.inputPill?.classList.add('shake');
  setTimeout(() => el.inputPill?.classList.remove('shake'), 500);
}

// ── Busy state ──────────────────────────────────────────────
function setBusy(busy) {
  isGenerating = busy;
  if (el.sendBtn) el.sendBtn.disabled = busy;
  if (el.statusDot) {
    el.statusDot.classList.toggle('thinking', busy);
  }
}

// ── Welcome state ───────────────────────────────────────────
function hideWelcome() {
  if (el.welcome && !el.welcome.classList.contains('gone')) {
    el.welcome.style.transition = 'opacity .25s, transform .25s';
    el.welcome.style.opacity = '0';
    el.welcome.style.transform = 'translateY(-12px)';
    setTimeout(() => {
      if (el.welcome) {
        el.welcome.style.display = 'none';
        el.welcome.classList.add('gone');
      }
    }, 250);
  }
}

function showWelcome() {
  if (el.welcome) {
    el.welcome.style.display = 'flex';
    el.welcome.style.opacity = '1';
    el.welcome.style.transform = 'none';
    el.welcome.classList.remove('gone');
  }
}

// ── Message rendering ───────────────────────────────────────
function appendMessage(role, text) {
  if (!el.messages) return null;
  const ts = now();

  if (role === 'user') {
    const div = document.createElement('div');
    div.className = 'mc-msg user';
    div.innerHTML = `
      <div class="mc-bubble-wrap">
        <div class="mc-bubble">${escHtml(text)}</div>
        <div class="mc-ts">${ts}</div>
      </div>`;
    el.messages.appendChild(div);
    scheduleScroll();
    return div;
  }

  if (role === 'bot') {
    return _appendBotBubble(renderMd(text), ts);
  }

  // system/error
  const div = document.createElement('div');
  div.className = `mc-msg ai`;
  div.innerHTML = `
    <div class="mc-avatar">ℹ️</div>
    <div class="mc-bubble-wrap">
      <div class="mc-bubble" style="border-left-color: var(--warn)">${escHtml(text)}</div>
    </div>`;
  el.messages.appendChild(div);
  scheduleScroll();
  return div;
}

function _appendBotBubble(html, ts) {
  const div = document.createElement('div');
  div.className = 'mc-msg ai';
  div.innerHTML = `
    <div class="mc-avatar">🧠</div>
    <div class="mc-bubble-wrap">
      <div class="mc-bubble">${html}</div>
      <div class="mc-msg-footer">
        <span class="mc-ts">${ts}</span>
        <div class="mc-msg-actions">
          <button class="mc-action-btn" title="Copy" onclick="(function(b){
            const t = b.closest('.mc-bubble-wrap').querySelector('.mc-bubble').innerText;
            navigator.clipboard.writeText(t).then(()=>{b.textContent='✅';setTimeout(()=>b.textContent='📋',2000)});
          })(this)">📋</button>
          <button class="mc-action-btn" title="Helpful" onclick="(function(b){
            b.style.color='#4ade80'; b.textContent='👍';
          })(this)">👍</button>
          <button class="mc-action-btn" title="Not helpful" onclick="(function(b){
            b.style.color='#f87171'; b.textContent='👎';
          })(this)">👎</button>
          <button class="mc-action-btn" title="Bookmark" onclick="(function(b){
            b.textContent = b.textContent==='🔖' ? '📌' : '🔖';
            b.style.color = b.textContent==='📌' ? '#fbbf24' : '';
          })(this)">🔖</button>
        </div>
      </div>
    </div>`;
  el.messages.appendChild(div);
  scheduleScroll();
  return div;
}

// Word-by-word reveal animation for AI responses
async function appendMessageReveal(role, text) {
  if (role !== 'bot') { appendMessage(role, text); return; }

  const ts = now();
  const div = document.createElement('div');
  div.className = 'mc-msg ai';
  div.innerHTML = `
    <div class="mc-avatar">🧠</div>
    <div class="mc-bubble-wrap">
      <div class="mc-bubble mc-reveal-target"></div>
      <div class="mc-msg-footer">
        <span class="mc-ts">${ts}</span>
        <div class="mc-msg-actions">
          <button class="mc-action-btn" title="Copy" onclick="(function(b){
            const t = b.closest('.mc-bubble-wrap').querySelector('.mc-bubble').innerText;
            navigator.clipboard.writeText(t).then(()=>{b.textContent='✅';setTimeout(()=>b.textContent='📋',2000)});
          })(this)">📋</button>
          <button class="mc-action-btn" title="Helpful" onclick="(function(b){
            b.style.color='#4ade80'; b.textContent='👍';
          })(this)">👍</button>
          <button class="mc-action-btn" title="Not helpful" onclick="(function(b){
            b.style.color='#f87171'; b.textContent='👎';
          })(this)">👎</button>
          <button class="mc-action-btn" title="Bookmark" onclick="(function(b){
            b.textContent = b.textContent==='🔖' ? '📌' : '🔖';
            b.style.color = b.textContent==='📌' ? '#fbbf24' : '';
          })(this)">🔖</button>
        </div>
      </div>
    </div>`;
  el.messages.appendChild(div);

  const target = div.querySelector('.mc-reveal-target');
  scheduleScroll();

  // Render markdown and animate word by word
  const parsed = renderMd(text);

  // Fast path: just set content if short
  if (text.length < 80) {
    target.innerHTML = parsed;
    scheduleScroll();
    return div;
  }

  // Reveal approach: build DOM incrementally from raw text
  // Parse to HTML first then reveal word by word via opacity trick
  target.style.opacity = '0';
  target.innerHTML = parsed;

  // Quick fade in for structured markdown
  let opacity = 0;
  const step = () => {
    opacity = Math.min(1, opacity + 0.06);
    target.style.opacity = opacity;
    if (opacity < 1) requestAnimationFrame(step);
    else { target.style.opacity = ''; }
    scheduleScroll();
  };
  requestAnimationFrame(step);

  return div;
}

// ── Typing indicator ────────────────────────────────────────
function addTypingIndicator() {
  const div = document.createElement('div');
  div.className = 'mc-msg ai thinking';
  div.innerHTML = `
    <div class="mc-avatar">🧠</div>
    <div class="mc-bubble-wrap">
      <div class="mc-bubble" style="padding: 12px 18px">
        <div class="mc-typing-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>`;
  el.messages.appendChild(div);
  scheduleScroll();
  return div;
}

// ── Scroll helper ───────────────────────────────────────────
function scheduleScroll() {
  requestAnimationFrame(() => {
    if (!el.messages) return;
    const { scrollTop, scrollHeight, clientHeight } = el.messages;
    const nearBottom = scrollHeight - scrollTop - clientHeight < 200;
    if (nearBottom) {
      el.messages.scrollTop = el.messages.scrollHeight;
    }
  });
}

// ── Utilities ───────────────────────────────────────────────
function renderMd(text) {
  if (typeof marked !== 'undefined') {
    try { return marked.parse(text); }
    catch { return escHtml(text); }
  }
  return escHtml(text);
}

function escHtml(t) {
  const d = document.createElement('div');
  d.textContent = t;
  return d.innerHTML;
}

function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function createChatId() {
  return 'mc_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 6);
}

function removeEl(el) {
  if (el?.parentNode) {
    el.style.opacity = '0';
    el.style.transition = 'opacity .15s';
    setTimeout(() => el.remove(), 150);
  }
}

// ── Chat persistence ────────────────────────────────────────
function loadChats() {
  try {
    chats = JSON.parse(localStorage.getItem(LS_KEY) || '[]');
  } catch { chats = []; }
}

function savePersistence() {
  try {
    // Keep only last 30 chats, messages trimmed to 40 each
    const trimmed = chats.slice(0, 30).map(c => ({
      ...c,
      messages: (c.messages || []).slice(-40),
    }));
    localStorage.setItem(LS_KEY, JSON.stringify(trimmed));
  } catch { /* storage full */ }
}

function startNewChat() {
  currentId    = null;
  localHistory = [];

  if (el.messages) {
    el.messages.innerHTML = '';
    if (el.welcome) {
      el.messages.appendChild(el.welcome);
    }
  }
  showWelcome();
  el.input?.focus();
  renderHistory();
}

function loadChatById(id) {
  const chat = chats.find(c => c.id === id);
  if (!chat) return;

  currentId    = id;
  localHistory = [];
  hideWelcome();

  if (el.messages) el.messages.innerHTML = '';

  (chat.messages || []).forEach(m => {
    appendMessage(m.role === 'bot' ? 'bot' : 'user', m.text);
    localHistory.push({
      role: m.role === 'bot' ? 'assistant' : 'user',
      content: m.text,
    });
  });

  renderHistory();
  setTimeout(() => scrollToBottom(false), 80);
}

function deleteChat(id) {
  chats = chats.filter(c => c.id !== id);
  savePersistence();
  if (currentId === id) startNewChat();
  else renderHistory();
}

// ── History rendering ───────────────────────────────────────
function renderHistory() {
  if (!el.historyList) return;

  if (!chats.length) {
    el.historyList.innerHTML = '<div class="mc-history-empty">No conversations yet.<br>Start one below!</div>';
    return;
  }

  el.historyList.innerHTML = '';

  const todayStr     = new Date().toDateString();
  const yesterdayStr = new Date(Date.now() - 86400000).toDateString();
  let lastGroup = '';

  chats.slice(0, 20).forEach(chat => {
    const d = new Date(chat.createdAt);
    const ds = d.toDateString();
    let group = ds === todayStr ? 'Today'
             : ds === yesterdayStr ? 'Yesterday'
             : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

    if (group !== lastGroup) {
      lastGroup = group;
      const lbl = document.createElement('div');
      lbl.className = 'mc-history-group-label';
      lbl.textContent = group;
      el.historyList.appendChild(lbl);
    }

    const count = Math.floor((chat.messages?.length || 0) / 2);

    const item = document.createElement('div');
    item.className = `mc-history-item${chat.id === currentId ? ' active' : ''}`;
    item.innerHTML = `
      <span class="mc-history-icon">💬</span>
      <div class="mc-history-content">
        <span class="mc-history-title">${escHtml(chat.title || 'Conversation')}</span>
        <span class="mc-history-meta">${count} exchange${count !== 1 ? 's' : ''}</span>
      </div>
      <button class="mc-history-del" title="Delete" onclick="event.stopPropagation(); window._mcDeleteChat('${chat.id}')">🗑</button>`;

    item.addEventListener('click', (e) => {
      if (!e.target.closest('.mc-history-del')) loadChatById(chat.id);
    });

    el.historyList.appendChild(item);
  });
}

// ── Zen mode ────────────────────────────────────────────────
function toggleZen() {
  const on = el.layout?.classList.toggle('zen');
  if (el.zenBtn) {
    el.zenBtn.textContent = on ? '← Exit Zen' : 'Zen Mode';
    el.zenBtn.classList.toggle('active', on);
  }
  localStorage.setItem('aura_mc_zen', on ? '1' : '0');
}

function restoreZenMode() {
  if (localStorage.getItem('aura_mc_zen') === '1') toggleZen();
}

// ── Global exports (for inline onclick handlers) ────────────
window.initChat = initChat;
window._mcDeleteChat = deleteChat;

// ── Auto-init ───────────────────────────────────────────────
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initChat);
} else {
  initChat();
}

})(); // end IIFE
