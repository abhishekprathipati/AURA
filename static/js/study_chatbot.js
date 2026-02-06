// ============================================
// AURA STUDY CHAT ENGINE - ULTRA PRO v2
// Advanced features, better UI, smooth scrolling
// ============================================

// Request lock to prevent multiple simultaneous API calls
let isStudyBotActive = false;
let requestAbortController = null;
let currentFileMeta = null;
let conversationHistory = [];
let currentStreamingMessage = null;

// Element cache
const studyEls = {
  chatMessages: null,
  chatForm: null,
  userInput: null,
  sendBtn: null,
  historyList: null,
  welcomeState: null,
  newChatBtn: null,
  attachBtn: null,
  fileInput: null,
  focusToggle: null,
  actionButtons: [],
  commandCenter: null,
};

// Chat state
let currentStudyChatId = null;
let studyChats = [];
const LS_STUDY_CHATS = 'aura_study_chats_v2';

// ============================================
// INITIALIZATION
// ============================================
function initStudyChat() {
  cacheStudyElements();
  loadStudyChats();
  renderStudyHistory();
  setupStudyEventListeners();
  setupKeyboardShortcuts();
  
  // Ensure scroll container is properly initialized
  if (studyEls.chatMessages) {
    studyEls.chatMessages.scrollTop = studyEls.chatMessages.scrollHeight;
    console.log('✅ Study Chat v2 initialized');
  }
  
  // Add smooth entrance animation
  document.body.classList.add('loaded');
}

function cacheStudyElements() {
  studyEls.chatMessages = document.getElementById('study-messages');
  studyEls.chatForm = document.getElementById('studyChatForm');
  studyEls.userInput = document.getElementById('studyChatInput');
  studyEls.sendBtn = document.getElementById('study-send-btn');
  studyEls.historyList = document.getElementById('study-history-list');
  studyEls.welcomeState = document.getElementById('studyWelcomeState');
  studyEls.newChatBtn = document.getElementById('newStudyChatBtn');
  studyEls.attachBtn = document.getElementById('attachFileBtn');
  studyEls.fileInput = document.getElementById('fileUpload');
  studyEls.focusToggle = document.getElementById('focusModeToggle');
  studyEls.actionButtons = Array.from(document.querySelectorAll('[data-study-action]'));
  studyEls.commandCenter = document.querySelector('.command-center');
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupStudyEventListeners() {
  // Send button handler
  if (studyEls.sendBtn) {
    studyEls.sendBtn.addEventListener('click', (e) => {
      e.preventDefault();
      handleStudySendMessage();
    });
  }

  // Form submit handler
  if (studyEls.chatForm) {
    studyEls.chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      e.stopPropagation();
      handleStudySendMessage();
      return false;
    });
  }

  // Input handlers with auto-grow
  if (studyEls.userInput) {
    const resizeTextarea = () => {
      studyEls.userInput.style.height = '44px';
      const newHeight = Math.min(studyEls.userInput.scrollHeight, 150);
      studyEls.userInput.style.height = `${newHeight}px`;
    };

    studyEls.userInput.addEventListener('input', () => {
      resizeTextarea();
      updateSendButtonState();
    });

    studyEls.userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        e.stopPropagation();
        handleStudySendMessage();
        return false;
      }
    });
    
    // Focus animation
    studyEls.userInput.addEventListener('focus', () => {
      studyEls.chatForm?.classList.add('focused');
    });
    
    studyEls.userInput.addEventListener('blur', () => {
      studyEls.chatForm?.classList.remove('focused');
    });
  }
  
  // New chat button
  if (studyEls.newChatBtn) {
    studyEls.newChatBtn.addEventListener('click', startNewStudyChat);
  }
  
  // File upload
  const fileUploadBtn = document.getElementById('attachFileBtn');
  const fileUploadInput = document.getElementById('fileUpload');
  
  if (fileUploadBtn && fileUploadInput) {
    fileUploadBtn.addEventListener('click', (e) => {
      e.preventDefault();
      fileUploadInput.click();
    });
  }
  
  if (fileUploadInput) {
    fileUploadInput.addEventListener('change', handleFileUpload);
  }

  // Focus Mode toggle
  if (studyEls.focusToggle) {
    studyEls.focusToggle.addEventListener('change', (e) => {
      const container = document.querySelector('.study-container');
      if (container) {
        container.classList.toggle('focus-mode', e.target.checked);
      }
    });
  }

  // Action buttons (Summarize, Quiz, Flashcards)
  studyEls.actionButtons.forEach((btn) => {
    const action = btn.getAttribute('data-study-action');
    btn.addEventListener('click', () => {
      if (!action) return;
      
      // Add click animation
      btn.classList.add('clicked');
      setTimeout(() => btn.classList.remove('clicked'), 200);
      
      switch(action) {
        case 'summarize': summarizeFile(); break;
        case 'quiz': generateQuiz(); break;
        case 'flashcards': createFlashcards(); break;
        case 'explain': explainConcept(); break;
        case 'notes': generateNotes(); break;
      }
    });
  });

  // Hub upload button
  const hubUploadBtn = document.getElementById('hubUploadBtn');
  if (hubUploadBtn && fileUploadInput) {
    hubUploadBtn.addEventListener('click', () => fileUploadInput.click());
  }
  
  // Quick chips
  document.querySelectorAll('.quick-chip, .example-prompt').forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt && studyEls.userInput) {
        studyEls.userInput.value = prompt;
        studyEls.userInput.focus();
        updateSendButtonState();
      }
    });
  });
  
  // Drag and drop file upload
  setupDragAndDrop();
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + N = New chat
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
      e.preventDefault();
      startNewStudyChat();
    }
    
    // Ctrl/Cmd + U = Upload file
    if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
      e.preventDefault();
      studyEls.fileInput?.click();
    }
    
    // Escape = Cancel current request
    if (e.key === 'Escape' && isStudyBotActive && requestAbortController) {
      requestAbortController.abort();
      addStudyMessage('system', 'Request cancelled');
      setStudyBusyState(false);
    }
    
    // Focus input with /
    if (e.key === '/' && document.activeElement !== studyEls.userInput) {
      e.preventDefault();
      studyEls.userInput?.focus();
    }
  });
}

// ============================================
// DRAG AND DROP
// ============================================
function setupDragAndDrop() {
  const dropZone = studyEls.chatMessages || document.body;
  
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
  });
  
  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
      dropZone.classList.add('drag-over');
    });
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
      dropZone.classList.remove('drag-over');
    });
  });
  
  dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer?.files;
    if (files?.length > 0 && studyEls.fileInput) {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(files[0]);
      studyEls.fileInput.files = dataTransfer.files;
      handleFileUpload({ target: studyEls.fileInput });
    }
  });
}

// ============================================
// FILE UPLOAD HANDLING
// ============================================
async function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  console.log('File selected:', file.name, file.type, file.size);
  
  // Validate file size (max 20MB)
  if (file.size > 20 * 1024 * 1024) {
    addStudyMessage('error', 'File too large. Maximum size is 20MB.');
    return;
  }

  hideWelcomeState();
  
  // Show upload progress
  const progressId = showUploadProgress(file.name);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/study/upload', {
      method: 'POST',
      body: formData
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Upload failed`);
    }

    currentFileMeta = {
      id: data.file_id || data.filename,
      name: data.original_filename || file.name,
      size: file.size,
      type: file.type
    };

    // Remove progress and show success
    removeUploadProgress(progressId);
    
    const successMsg = addStudyMessage('ai', `
### File Uploaded Successfully

**${currentFileMeta.name}** is ready for analysis.

**What would you like to do?**
- **Summarize** - Get key points and concepts
- **Quiz** - Test your understanding  
- **Flashcards** - Create study cards
- **Ask Questions** - Chat about the content

*Type your question or click a command above.*
    `);

    // Update UI
    updateFileIndicator(currentFileMeta.name);
    addFileToActiveList(currentFileMeta.name);
    
    smoothScrollToBottom();

  } catch (error) {
    console.error('Upload error:', error);
    removeUploadProgress(progressId);
    addStudyMessage('error', `Upload failed: ${error.message}`);
  } finally {
    if (studyEls.fileInput) {
      studyEls.fileInput.value = '';
    }
  }
}

function showUploadProgress(fileName) {
  const progressId = 'upload-' + Date.now();
  const progressDiv = document.createElement('div');
  progressDiv.id = progressId;
  progressDiv.className = 'message system-message upload-progress';
  progressDiv.innerHTML = `
    <div class="upload-progress-content">
      <div class="upload-spinner"></div>
      <div class="upload-info">
        <span class="upload-filename">${fileName}</span>
        <span class="upload-status">Uploading...</span>
      </div>
    </div>
    <div class="upload-bar">
      <div class="upload-bar-fill"></div>
    </div>
  `;
  
  studyEls.chatMessages?.appendChild(progressDiv);
  smoothScrollToBottom();
  
  // Animate progress bar
  setTimeout(() => {
    const fill = progressDiv.querySelector('.upload-bar-fill');
    if (fill) fill.style.width = '90%';
  }, 100);
  
  return progressId;
}

function removeUploadProgress(progressId) {
  const el = document.getElementById(progressId);
  if (el) {
    el.classList.add('fade-out');
    setTimeout(() => el.remove(), 300);
  }
}

function updateFileIndicator(fileName) {
  if (studyEls.userInput) {
    studyEls.userInput.placeholder = `Ask about "${fileName}"...`;
  }
  
  // Add file badge to input area
  let badge = document.querySelector('.file-badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.className = 'file-badge';
    studyEls.chatForm?.prepend(badge);
  }
  badge.innerHTML = `<span class="file-badge-icon">📄</span> ${fileName} <button class="file-badge-remove" onclick="clearCurrentFile()">×</button>`;
}

function clearCurrentFile() {
  currentFileMeta = null;
  const badge = document.querySelector('.file-badge');
  if (badge) badge.remove();
  if (studyEls.userInput) {
    studyEls.userInput.placeholder = 'Ask a question or upload a file...';
  }
}

function addFileToActiveList(fileName) {
  const fileList = document.getElementById('fileList');
  if (!fileList) return;

  // Remove duplicates
  const existing = fileList.querySelector(`[data-filename="${fileName}"]`);
  if (existing) existing.remove();

  const fileItem = document.createElement('div');
  fileItem.className = 'file-item';
  fileItem.setAttribute('data-filename', fileName);
  fileItem.innerHTML = `
    <span class="file-icon">📄</span>
    <span class="file-name">${fileName}</span>
    <span class="file-status">Ready</span>
  `;
  fileList.prepend(fileItem);

  // Limit list
  while (fileList.children.length > 5) {
    fileList.removeChild(fileList.lastChild);
  }
}

// ============================================
// UI STATE HELPERS
// ============================================
function setStudyBusyState(isBusy, label = '') {
  isStudyBotActive = isBusy;
  
  if (studyEls.sendBtn) {
    studyEls.sendBtn.disabled = isBusy;
    studyEls.sendBtn.classList.toggle('loading', isBusy);
    studyEls.sendBtn.innerHTML = isBusy ? '<span class="btn-spinner"></span>' : '🚀';
  }
  
  if (studyEls.userInput) {
    studyEls.userInput.disabled = isBusy;
  }
  
  studyEls.actionButtons.forEach((btn) => {
    btn.disabled = isBusy;
    btn.classList.toggle('disabled', isBusy);
  });
  
  // Show/hide stop button
  const stopBtn = document.getElementById('stopGenerationBtn');
  if (stopBtn) {
    stopBtn.style.display = isBusy ? 'flex' : 'none';
  }
}

function updateSendButtonState() {
  if (studyEls.sendBtn && studyEls.userInput) {
    const hasText = studyEls.userInput.value.trim().length > 0;
    studyEls.sendBtn.classList.toggle('active', hasText);
  }
}

// ============================================
// SEND MESSAGE
// ============================================
async function handleStudySendMessage(e) {
  if (e) e.preventDefault();
  
  if (isStudyBotActive) {
    console.warn('Study bot is processing');
    return;
  }
  
  const userText = studyEls.userInput?.value.trim();
  if (!userText) {
    studyEls.userInput?.focus();
    shakeInput();
    return;
  }
  
  // Setup
  setStudyBusyState(true);
  hideWelcomeState();
  
  // Add user message with animation
  addStudyMessage('user', userText);
  
  // Clear input
  studyEls.userInput.value = '';
  studyEls.userInput.style.height = '44px';
  updateSendButtonState();
  
  // Show typing indicator
  const typingId = addTypingIndicator();
  
  try {
    requestAbortController = new AbortController();
    
    const formData = new FormData();
    formData.append('prompt', userText);
    
    // Add conversation history for context
    formData.append('conversation_history', JSON.stringify(conversationHistory.slice(-10)));
    
    if (currentFileMeta?.id) {
      formData.append('file_id', currentFileMeta.id);
    }
    
    console.log('Sending to /api/study/analyze');
    
    const response = await fetch('/api/study/analyze', {
      method: 'POST',
      body: formData,
      signal: requestAbortController.signal
    });
    
    removeTypingIndicator(typingId);
    
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    
    if (data.answer) {
      // Add AI response with typing effect
      await addStudyMessageWithTyping('ai', data.answer);
      
      // Update conversation history
      conversationHistory.push(
        { role: 'user', content: userText },
        { role: 'assistant', content: data.answer }
      );
      
      // Save to local storage
      saveStudyMessage(userText, data.answer);
      
      // Show action buttons after response
      showPostResponseActions();
    } else {
      throw new Error('No response received');
    }
    
  } catch (error) {
    removeTypingIndicator(typingId);
    
    if (error.name === 'AbortError') {
      addStudyMessage('system', 'Request cancelled');
    } else {
      console.error('Error:', error);
      addStudyMessage('error', `${error.message || 'Something went wrong. Please try again.'}`);
    }
  } finally {
    setStudyBusyState(false);
    requestAbortController = null;
  }
}

function shakeInput() {
  studyEls.chatForm?.classList.add('shake');
  setTimeout(() => studyEls.chatForm?.classList.remove('shake'), 500);
}

// ============================================
// MESSAGE RENDERING
// ============================================
function addStudyMessage(role, text) {
  if (!studyEls.chatMessages) {
    console.error('Chat messages container not found!');
    return null;
  }
  
  console.log(`Adding ${role} message:`, text.substring(0, 50) + '...');
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}-message`;
  messageDiv.setAttribute('data-role', role);
  
  // Add timestamp
  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  
  const avatar = role === 'user' ? '👤' : role === 'ai' ? '🤖' : role === 'system' ? 'ℹ️' : '⚠️';
  
  if (role === 'ai' && typeof marked !== 'undefined') {
    const parsed = marked.parse(text);
    messageDiv.innerHTML = `
      <div class="message-avatar">${avatar}</div>
      <div class="message-content">
        <div class="message-body">${parsed}</div>
        <div class="message-footer">
          <span class="message-time">${timestamp}</span>
          <div class="message-actions">
            <button class="msg-action-btn" onclick="copyMessage(this)" title="Copy">📋</button>
            <button class="msg-action-btn" onclick="regenerateResponse(this)" title="Regenerate">🔄</button>
          </div>
        </div>
      </div>
    `;
  } else if (role === 'user') {
    messageDiv.innerHTML = `
      <div class="message-content">
        <div class="message-body">${escapeHtml(text)}</div>
        <span class="message-time">${timestamp}</span>
      </div>
      <div class="message-avatar">${avatar}</div>
    `;
  } else {
    // System or error message
    messageDiv.innerHTML = `
      <div class="message-avatar">${avatar}</div>
      <div class="message-content">
        <div class="message-body">${escapeHtml(text)}</div>
      </div>
    `;
  }

  // Add entrance animation
  messageDiv.classList.add('message-enter');
  studyEls.chatMessages.appendChild(messageDiv);
  
  // Trigger animation
  requestAnimationFrame(() => {
    messageDiv.classList.add('message-enter-active');
  });
  
  smoothScrollToBottom();
  
  console.log('Message added successfully');
  return messageDiv;
}

async function addStudyMessageWithTyping(role, text) {
  if (!studyEls.chatMessages) {
    console.error('Chat messages container not found!');
    return null;
  }
  
  console.log(`Adding AI message with typing:`, text.substring(0, 100) + '...');
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}-message`;
  messageDiv.setAttribute('data-role', role);
  
  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const avatar = '🤖';
  
  messageDiv.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-content">
      <div class="message-body"></div>
      <div class="message-footer">
        <span class="message-time">${timestamp}</span>
        <div class="message-actions">
          <button class="msg-action-btn" onclick="copyMessage(this)" title="Copy">📋</button>
          <button class="msg-action-btn" onclick="regenerateResponse(this)" title="Regenerate">🔄</button>
        </div>
      </div>
    </div>
  `;
  
  messageDiv.classList.add('message-enter');
  studyEls.chatMessages.appendChild(messageDiv);
  
  const bodyEl = messageDiv.querySelector('.message-body');
  
  // Parse markdown and render
  if (typeof marked !== 'undefined') {
    try {
      const parsed = marked.parse(text);
      bodyEl.innerHTML = parsed;
      console.log('Markdown parsed successfully');
    } catch (e) {
      console.error('Markdown parse error:', e);
      bodyEl.textContent = text;
    }
    
    // Highlight code blocks
    messageDiv.querySelectorAll('pre code').forEach(block => {
      block.classList.add('hljs');
    });
  } else {
    console.warn('marked.js not available, using plain text');
    bodyEl.textContent = text;
  }
  
  // Trigger animation
  requestAnimationFrame(() => {
    messageDiv.classList.add('message-enter-active');
  });
  
  smoothScrollToBottom();
  
  console.log('AI message added successfully');
  return messageDiv;
}

function addTypingIndicator() {
  const typingId = 'typing-' + Date.now();
  const typingDiv = document.createElement('div');
  typingDiv.id = typingId;
  typingDiv.className = 'message ai-message typing-indicator';
  typingDiv.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="message-content">
      <div class="typing-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  `;
  
  studyEls.chatMessages?.appendChild(typingDiv);
  smoothScrollToBottom();
  
  return typingId;
}

function removeTypingIndicator(typingId) {
  const el = document.getElementById(typingId);
  if (el) {
    el.classList.add('fade-out');
    setTimeout(() => el.remove(), 200);
  }
}

// ============================================
// MESSAGE ACTIONS
// ============================================
function copyMessage(btn) {
  const content = btn.closest('.message-content')?.querySelector('.message-body');
  if (content) {
    const text = content.innerText || content.textContent;
    navigator.clipboard.writeText(text).then(() => {
      btn.textContent = '✅';
      setTimeout(() => btn.textContent = '📋', 2000);
    });
  }
}

function regenerateResponse(btn) {
  const messageDiv = btn.closest('.message');
  const prevMessage = messageDiv?.previousElementSibling;
  
  if (prevMessage?.getAttribute('data-role') === 'user') {
    const userText = prevMessage.querySelector('.message-body')?.textContent;
    if (userText) {
      messageDiv.remove();
      studyEls.userInput.value = userText;
      handleStudySendMessage();
    }
  }
}

function showPostResponseActions() {
  // Show flashcards button
  const flashcardsBtn = document.getElementById('chipFlashcards');
  if (flashcardsBtn) {
    flashcardsBtn.style.display = 'inline-flex';
  }
}

// ============================================
// SCROLL HELPER
// ============================================
function smoothScrollToBottom() {
  if (!studyEls.chatMessages) return;
  
  const el = studyEls.chatMessages;
  
  const doScroll = () => {
    el.scrollTo({
      top: el.scrollHeight,
      behavior: 'smooth'
    });
  };
  
  // Multiple scroll attempts for dynamic content
  doScroll();
  setTimeout(doScroll, 50);
  setTimeout(doScroll, 150);
  setTimeout(doScroll, 300);
  
  requestAnimationFrame(() => {
    el.scrollTop = el.scrollHeight;
  });
}

// ============================================
// WELCOME STATE
// ============================================
function hideWelcomeState() {
  if (studyEls.welcomeState) {
    studyEls.welcomeState.classList.add('hidden');
    setTimeout(() => {
      studyEls.welcomeState.style.display = 'none';
    }, 300);
  }
  
  // Move command center to top if not in focus mode
  if (studyEls.commandCenter) {
    studyEls.commandCenter.classList.add('minimized');
  }
}

function showWelcomeState() {
  if (studyEls.welcomeState) {
    studyEls.welcomeState.style.display = 'flex';
    studyEls.welcomeState.classList.remove('hidden');
  }
  
  if (studyEls.commandCenter) {
    studyEls.commandCenter.classList.remove('minimized');
  }
}

// ============================================
// CHAT HISTORY
// ============================================
function loadStudyChats() {
  try {
    const stored = localStorage.getItem(LS_STUDY_CHATS);
    studyChats = stored ? JSON.parse(stored) : [];
  } catch (err) {
    console.error('Error loading chats:', err);
    studyChats = [];
  }
}

function saveStudyChats() {
  try {
    localStorage.setItem(LS_STUDY_CHATS, JSON.stringify(studyChats));
  } catch (err) {
    console.error('Error saving chats:', err);
  }
}

function saveStudyMessage(userMsg, aiMsg) {
  if (!currentStudyChatId) {
    currentStudyChatId = Date.now().toString();
    const chatTitle = userMsg.slice(0, 40) + (userMsg.length > 40 ? '...' : '');
    studyChats.unshift({
      id: currentStudyChatId,
      title: chatTitle,
      createdAt: Date.now(),
      messages: []
    });
  }
  
  const chat = studyChats.find(c => c.id === currentStudyChatId);
  if (chat) {
    chat.messages.push({ role: 'user', text: userMsg, time: Date.now() });
    chat.messages.push({ role: 'ai', text: aiMsg, time: Date.now() });
    chat.updatedAt = Date.now();
    saveStudyChats();
    renderStudyHistory();
  }
}

function startNewStudyChat() {
  currentStudyChatId = null;
  conversationHistory = [];
  currentFileMeta = null;
  
  // Clear messages but keep command center
  if (studyEls.chatMessages) {
    const commandCenter = studyEls.chatMessages.querySelector('.command-center');
    const welcomeState = studyEls.chatMessages.querySelector('.welcome-state');
    
    studyEls.chatMessages.innerHTML = '';
    
    if (commandCenter) {
      commandCenter.classList.remove('minimized');
      studyEls.chatMessages.appendChild(commandCenter);
    }
    if (welcomeState) {
      welcomeState.style.display = 'flex';
      welcomeState.classList.remove('hidden');
      studyEls.chatMessages.appendChild(welcomeState);
    }
  }
  
  // Reset file indicator
  clearCurrentFile();
  
  // Focus input
  studyEls.userInput?.focus();
  
  renderStudyHistory();
}

function renderStudyHistory() {
  if (!studyEls.historyList) return;
  
  if (studyChats.length === 0) {
    studyEls.historyList.innerHTML = `
      <div class="history-empty">
        <span class="empty-icon">💬</span>
        <span>No study sessions yet</span>
        <span class="empty-hint">Start a conversation!</span>
      </div>
    `;
    return;
  }
  
  studyEls.historyList.innerHTML = '';
  
  // Group by date
  const today = new Date().toDateString();
  const yesterday = new Date(Date.now() - 86400000).toDateString();
  
  let currentGroup = '';
  
  studyChats.slice(0, 15).forEach(chat => {
    const chatDate = new Date(chat.createdAt).toDateString();
    let groupLabel = '';
    
    if (chatDate === today) groupLabel = 'Today';
    else if (chatDate === yesterday) groupLabel = 'Yesterday';
    else groupLabel = new Date(chat.createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    
    // Add group header if new group
    if (groupLabel !== currentGroup) {
      currentGroup = groupLabel;
      const groupHeader = document.createElement('div');
      groupHeader.className = 'history-group-header';
      groupHeader.textContent = groupLabel;
      studyEls.historyList.appendChild(groupHeader);
    }
    
    const item = document.createElement('div');
    item.className = `history-item ${chat.id === currentStudyChatId ? 'active' : ''}`;
    
    const msgCount = Math.floor((chat.messages?.length || 0) / 2);
    
    item.innerHTML = `
      <span class="history-icon">💬</span>
      <div class="history-content">
        <span class="history-title">${escapeHtml(chat.title || 'New chat')}</span>
        <span class="history-meta">${msgCount} message${msgCount !== 1 ? 's' : ''}</span>
      </div>
      <button class="history-delete" onclick="deleteChat('${chat.id}', event)" title="Delete">🗑️</button>
    `;
    
    item.addEventListener('click', (e) => {
      if (!e.target.closest('.history-delete')) {
        loadStudyChat(chat.id);
      }
    });
    
    studyEls.historyList.appendChild(item);
  });
}

function loadStudyChat(chatId) {
  const chat = studyChats.find(c => c.id === chatId);
  if (!chat) return;
  
  currentStudyChatId = chatId;
  conversationHistory = [];
  
  hideWelcomeState();
  
  // Clear and reload
  if (studyEls.chatMessages) {
    studyEls.chatMessages.innerHTML = '';
  }
  
  chat.messages.forEach(msg => {
    addStudyMessage(msg.role, msg.text);
    
    // Rebuild conversation history
    conversationHistory.push({
      role: msg.role === 'user' ? 'user' : 'assistant',
      content: msg.text
    });
  });
  
  renderStudyHistory();
}

function deleteChat(chatId, event) {
  event.stopPropagation();
  
  if (!confirm('Delete this chat?')) return;
  
  studyChats = studyChats.filter(c => c.id !== chatId);
  saveStudyChats();
  
  if (currentStudyChatId === chatId) {
    startNewStudyChat();
  } else {
    renderStudyHistory();
  }
}

// ============================================
// STUDY ACTIONS
// ============================================
async function summarizeFile() {
  if (isStudyBotActive) return;
  
  if (!currentFileMeta?.id) {
    addStudyMessage('system', 'Please upload a document first.');
    setTimeout(() => studyEls.fileInput?.click(), 300);
    return;
  }
  
  hideWelcomeState();
  setStudyBusyState(true);
  
  const typingId = addTypingIndicator();
  
  try {
    const response = await fetch('/study/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: currentFileMeta.id })
    });
    
    const data = await response.json();
    removeTypingIndicator(typingId);
    
    if (!response.ok) throw new Error(data.error || 'Summarization failed');
    
    await addStudyMessageWithTyping('ai', data.summary || 'Could not generate summary.');
    
    // Save to history
    saveStudyMessage(`Summarize: ${currentFileMeta.name}`, data.summary);
    
  } catch (error) {
    removeTypingIndicator(typingId);
    addStudyMessage('error', `${error.message}`);
  } finally {
    setStudyBusyState(false);
  }
}

async function generateQuiz() {
  if (isStudyBotActive) return;
  
  if (!currentFileMeta?.id) {
    addStudyMessage('system', 'Please upload a document first.');
    setTimeout(() => studyEls.fileInput?.click(), 300);
    return;
  }
  
  hideWelcomeState();
  setStudyBusyState(true);
  
  const typingId = addTypingIndicator();
  
  try {
    const response = await fetch('/study/quiz', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: currentFileMeta.id })
    });
    
    const data = await response.json();
    removeTypingIndicator(typingId);
    
    if (!response.ok) throw new Error(data.error || 'Quiz generation failed');
    
    await addStudyMessageWithTyping('ai', data.quiz || 'Could not generate quiz.');
    
    saveStudyMessage(`Quiz: ${currentFileMeta.name}`, data.quiz);
    
  } catch (error) {
    removeTypingIndicator(typingId);
    addStudyMessage('error', `${error.message}`);
  } finally {
    setStudyBusyState(false);
  }
}

async function createFlashcards() {
  if (isStudyBotActive) return;
  
  hideWelcomeState();
  setStudyBusyState(true);
  
  const typingId = addTypingIndicator();
  
  try {
    const formData = new FormData();
    formData.append('prompt', 'Create 10 concise flashcards for studying key concepts from the document. Format each as:\n\n**Term/Question**: [term]\n**Definition/Answer**: [definition]\n\n---');
    if (currentFileMeta?.id) formData.append('file_id', currentFileMeta.id);
    
    const response = await fetch('/api/study/analyze', { method: 'POST', body: formData });
    const data = await response.json();
    
    removeTypingIndicator(typingId);
    
    if (!response.ok) throw new Error(data.error || 'Flashcard generation failed');
    
    await addStudyMessageWithTyping('ai', data.answer || 'Could not generate flashcards.');
    
    saveStudyMessage('Generate flashcards', data.answer);
    
  } catch (error) {
    removeTypingIndicator(typingId);
    addStudyMessage('error', `${error.message}`);
  } finally {
    setStudyBusyState(false);
  }
}

async function explainConcept() {
  const concept = prompt('What concept would you like explained?');
  if (!concept) return;
  
  studyEls.userInput.value = `Explain this concept in simple terms: ${concept}`;
  handleStudySendMessage();
}

async function generateNotes() {
  if (!currentFileMeta?.id) {
    addStudyMessage('system', 'Please upload a document first.');
    setTimeout(() => studyEls.fileInput?.click(), 300);
    return;
  }
  
  studyEls.userInput.value = 'Generate comprehensive study notes from this document with key points, definitions, and important concepts organized by topic.';
  handleStudySendMessage();
}

// ============================================
// UTILITIES
// ============================================
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ============================================
// GLOBAL EXPORTS
// ============================================
window.initStudyChat = initStudyChat;
window.handleStudySendMessage = handleStudySendMessage;
window.startNewStudyChat = startNewStudyChat;
window.summarizeFile = summarizeFile;
window.generateQuiz = generateQuiz;
window.createFlashcards = createFlashcards;
window.copyMessage = copyMessage;
window.regenerateResponse = regenerateResponse;
window.deleteChat = deleteChat;
window.clearCurrentFile = clearCurrentFile;

// ============================================
// AUTO-INIT
// ============================================
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initStudyChat);
} else {
  initStudyChat();
}
