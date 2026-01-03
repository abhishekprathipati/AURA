// ============================================
// AURA MENTAL CHAT ENGINE - Request Locking
// ============================================

// Request lock to prevent multiple simultaneous API calls
let isGenerating = false;
let requestAbortController = null;

// Element cache
const els = {
  chatMessages: null,
  chatForm: null,
  userInput: null,
  sendBtn: null,
  historyList: null,
  welcomeState: null,
  newChatBtn: null,
  zenBtn: null,
  themeToggle: null,
  inputAreaWrapper: null,
};

// Chat state
let currentChatId = null;
let chats = [];
const LS_CHATS = 'aura_mental_chats';

// ============================================
// INITIALIZATION
// ============================================
function initChat() {
  cacheElements();
  loadChats();
  renderHistory();
  setupEventListeners();
  renderWelcome();
  restoreZenMode();
  
  // Ensure scroll container is properly initialized
  if (els.chatMessages) {
    // Set initial scroll position to bottom (in case of any default content)
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
  }
}

function cacheElements() {
  els.chatMessages = document.getElementById('chat-messages');
  els.chatForm = document.getElementById('chatForm');
  els.userInput = document.getElementById('chat-input') || document.getElementById('user-input');
  els.sendBtn = document.getElementById('send-btn');
  els.historyList = document.getElementById('history-list');
  els.welcomeState = document.getElementById('welcomeState');
  els.newChatBtn = document.getElementById('newChatBtn');
  els.zenBtn = document.getElementById('zenModeToggle');
  els.themeToggle = document.getElementById('theme-toggle');
  els.inputAreaWrapper = document.querySelector('.input-area-wrapper');
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
  if (els.chatForm) {
    els.chatForm.addEventListener('submit', handleSendMessage);
  }
  
  if (els.userInput) {
    els.userInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    });
  }
  
  if (els.newChatBtn) {
    els.newChatBtn.addEventListener('click', startNewChat);
  }
  
  if (els.zenBtn) {
    els.zenBtn.addEventListener('click', toggleZenMode);
  }
  
  // Listen for theme changes
  window.addEventListener('themechange', (e) => {
    console.log('Theme changed to:', e.detail.theme);
  });
}

// ============================================
// SEND MESSAGE WITH REQUEST LOCK
// ============================================
async function handleSendMessage(e) {
  if (e) e.preventDefault();
  
  // Check if already generating (request lock)
  if (isGenerating) {
    console.warn('Request already in progress, ignoring duplicate request');
    return;
  }
  
  const message = els.userInput.value.trim();
  if (!message) return;
  
  // Create new chat on first message
  if (!currentChatId) {
    const chat = createChat(message);
    currentChatId = chat.id;
  }
  
  // Hide welcome state
  if (els.welcomeState) {
    els.welcomeState.style.display = 'none';
  }
  
  // Lock request and disable UI
  isGenerating = true;
  updateSendButtonState();
  
  // Append user message
  appendMessage(message, 'user');
  addMessageToChat(currentChatId, 'user', message);
  els.userInput.value = '';
  els.userInput.focus();
  
  // Show loading indicator
  const loadingId = showLoading();
  
  try {
    const response = await fetch('/api/chat/mental', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: currentChatId,
      }),
      signal: requestAbortController?.signal,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    removeLoadingById(loadingId);
    
    const reply = data.ai_response || data.reply || data.message || 'No response from AI.';
    appendMessage(reply, 'bot');
    addMessageToChat(currentChatId, 'bot', reply);
    
  } catch (error) {
    removeLoadingById(loadingId);
    
    if (error.name === 'AbortError') {
      console.log('Request was cancelled');
    } else {
      console.error('Request error:', error);
      const errorMsg = 'Sorry, something went wrong. Please try again.';
      appendMessage(errorMsg, 'bot');
      addMessageToChat(currentChatId, 'bot', errorMsg);
    }
  } finally {
    // Unlock request
    isGenerating = false;
    updateSendButtonState();
  }
}

// Update send button disabled state
function updateSendButtonState() {
  if (els.sendBtn) {
    els.sendBtn.disabled = isGenerating;
    els.sendBtn.setAttribute('aria-busy', isGenerating);
  }
}

// ============================================
// MESSAGE RENDERING
// ============================================
function appendMessage(text, role) {
  if (!els.chatMessages) return;
  
  const block = document.createElement('div');
  block.className = `message-block ${role}-msg`;
  
  // Add bot avatar
  if (role === 'bot') {
    const avatar = document.createElement('div');
    avatar.className = 'bot-avatar';
    avatar.textContent = '🧠';
    block.appendChild(avatar);
  }
  
  const content = document.createElement('div');
  content.className = 'content';
  
  // Try to parse markdown for bot messages
  if (role === 'bot' && typeof marked !== 'undefined') {
    try {
      content.innerHTML = marked.parse(text);
    } catch (e) {
      content.textContent = text;
    }
  } else {
    content.textContent = text;
  }
  
  block.appendChild(content);
  els.chatMessages.appendChild(block);
  
  // Enhanced auto-scroll to bottom - ensures latest message is always visible
  const scrollToBottom = () => {
    if (els.chatMessages) {
      // Scroll to the absolute bottom of the container
      els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    }
  };
  
  // Immediate scroll
  scrollToBottom();
  
  // Delayed scrolls for content that takes time to render (markdown, images, etc.)
  setTimeout(scrollToBottom, 50);
  setTimeout(scrollToBottom, 150);
  setTimeout(scrollToBottom, 300);
  
  // Final scroll after all rendering complete
  requestAnimationFrame(() => {
    setTimeout(scrollToBottom, 0);
  });
}

function showLoading() {
  if (!els.chatMessages) return null;
  
  const id = 'loading-' + Date.now();
  const block = document.createElement('div');
  block.id = id;
  block.className = 'message-block bot-msg';
  
  const avatar = document.createElement('div');
  avatar.className = 'bot-avatar';
  avatar.textContent = '🧠';
  block.appendChild(avatar);
  
  const content = document.createElement('div');
  content.className = 'content';
  content.innerHTML = '<span class="loading-dots"><span></span><span></span><span></span></span>';
  block.appendChild(content);
  
  els.chatMessages.appendChild(block);
  
  // Auto-scroll to bottom - aggressive scrolling
  const scrollToBottom = () => {
    if (els.chatMessages) {
      els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    }
  };
  
  scrollToBottom();
  setTimeout(scrollToBottom, 50);
  
  return id;
}

function removeLoadingById(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ============================================
// CHAT MANAGEMENT
// ============================================
function uid() {
  return 'chat_' + Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function loadChats() {
  try {
    const raw = localStorage.getItem(LS_CHATS);
    chats = raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error('Failed to load chats:', e);
    chats = [];
  }
  return chats;
}

function saveChats() {
  localStorage.setItem(LS_CHATS, JSON.stringify(chats));
}

function createChat(title = 'New conversation') {
  const chat = {
    id: uid(),
    title: title.split(' ').slice(0, 5).join(' ') + (title.split(' ').length > 5 ? '...' : ''),
    messages: [],
    createdAt: Date.now(),
  };
  chats.unshift(chat);
  saveChats();
  renderHistory();
  return chat;
}

function getChat(chatId) {
  return chats.find(c => c.id === chatId);
}

function addMessageToChat(chatId, role, text) {
  const chat = getChat(chatId);
  if (chat) {
    chat.messages.push({ role, text, ts: Date.now() });
    saveChats();
  }
}

function loadChatById(chatId) {
  const chat = getChat(chatId);
  if (!chat) return;
  
  currentChatId = chatId;
  
  // Clear and reload messages
  if (els.chatMessages) {
    els.chatMessages.innerHTML = '';
    chat.messages.forEach(m => {
      appendMessage(m.text, m.role);
    });
    
    // Scroll to bottom after loading all messages
    setTimeout(() => {
      if (els.chatMessages) {
        els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
      }
    }, 100);
  }
  
  // Hide welcome
  if (els.welcomeState) {
    els.welcomeState.style.display = 'none';
  }
  
  renderHistory();
}

function startNewChat() {
  currentChatId = null;
  
  if (els.chatMessages) {
    els.chatMessages.innerHTML = '';
  }
  
  if (els.welcomeState) {
    els.welcomeState.style.display = 'block';
  }
  
  if (els.userInput) {
    els.userInput.value = '';
    els.userInput.focus();
  }
  
  renderHistory();
}

function renderWelcome() {
  if (!els.welcomeState) return;
  
  els.welcomeState.innerHTML = `
    <h1>Hello, how can I help?</h1>
    <p>I'm here to listen and support you. Share what's on your mind, and we'll work through it together.</p>
    <div class="quick-chips">
      <button class="quick-chip" data-prompt="I'm feeling stressed about work">
        <span class="quick-chip-icon">😓</span> Feeling stressed
      </button>
      <button class="quick-chip" data-prompt="I need help with anxiety">
        <span class="quick-chip-icon">😰</span> Anxiety help
      </button>
      <button class="quick-chip" data-prompt="I want to practice mindfulness">
        <span class="quick-chip-icon">🧘</span> Mindfulness
      </button>
      <button class="quick-chip" data-prompt="I'm having trouble sleeping">
        <span class="quick-chip-icon">😴</span> Sleep issues
      </button>
    </div>
  `;
  
  // Attach quick chip listeners
  els.welcomeState.querySelectorAll('.quick-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.getAttribute('data-prompt');
      if (els.userInput) {
        els.userInput.value = prompt;
        els.userInput.focus();
        // Trigger send
        setTimeout(() => handleSendMessage(), 50);
      }
    });
  });
}

function renderHistory() {
  if (!els.historyList) return;
  
  els.historyList.innerHTML = '';
  
  if (chats.length === 0) {
    els.historyList.innerHTML = '<div class="history-empty">No conversations yet</div>';
    return;
  }
  
  chats.slice(0, 15).forEach(chat => {
    const item = document.createElement('div');
    item.className = 'history-item' + (chat.id === currentChatId ? ' active' : '');
    item.innerHTML = `
      <span class="history-item-icon">💬</span>
      <span class="history-item-text">${escapeHtml(chat.title)}</span>
    `;
    item.addEventListener('click', () => loadChatById(chat.id));
    els.historyList.appendChild(item);
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ============================================
// ZEN MODE
// ============================================
function toggleZenMode() {
  const container = document.querySelector('.gemini-container');
  if (container) {
    container.classList.toggle('zen-mode');
    const isZen = container.classList.contains('zen-mode');
    localStorage.setItem('aura-zen-mode', isZen);
    
    if (els.zenBtn) {
      els.zenBtn.textContent = isZen ? '← Exit Zen' : 'Zen Mode';
    }
  }
}

// Restore zen mode preference
function restoreZenMode() {
  const isZen = localStorage.getItem('aura-zen-mode') === 'true';
  if (isZen) {
    toggleZenMode();
  }
}

// ============================================
// QUICK CHIPS
// ============================================
function setupQuickChips() {
  document.querySelectorAll('.quick-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.getAttribute('data-prompt');
      if (els.userInput) {
        els.userInput.value = prompt;
        els.userInput.focus();
        setTimeout(() => handleSendMessage(), 50);
      }
    });
  });
}

// ============================================
// AUTO-INIT
// ============================================
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initChat();
    restoreZenMode();
    setupQuickChips();
  });
} else {
  initChat();
  restoreZenMode();
  setupQuickChips();
}
