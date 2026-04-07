// ============================================
// AURA STUDY CHAT ENGINE - ULTRA PRO v2
// Advanced features, better UI, smooth scrolling
// ============================================
(function () {
'use strict';

// Request lock to prevent multiple simultaneous API calls
let isStudyBotActive = false;
let studyAbortController = null;
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
      studyEls.userInput.style.height = '24px';
      const newHeight = Math.min(studyEls.userInput.scrollHeight, 140);
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
        case 'summarize':  summarizeFile();    break;
        case 'quiz':       generateQuiz();     break;
        case 'flashcards': createFlashcards(); break;
        case 'explain':    explainConcept();   break;
        case 'notes':      generateNotes();    break;
        case 'mindmap':    generateMindMap();  break;
        case 'timeline':   generateTimeline(); break;
        default:
          addStudyMessage('system', `"${action}" is coming soon!`);
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
    if (e.key === 'Escape' && isStudyBotActive && studyAbortController) {
      studyAbortController.abort();
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
    updateFileIndicator(currentFileMeta.name, currentFileMeta.size);
    addFileToActiveList(currentFileMeta.name);
    
    smoothScrollToBottom();

  } catch (error) {
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

function updateFileIndicator(fileName, fileSize) {
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
  badge.innerHTML = `<span class="file-badge-icon">📄</span> ${escapeHtml(fileName)} <button class="file-badge-remove" onclick="clearCurrentFile()">×</button>`;

  // Update sidebar status card
  const emptyEl  = document.getElementById('scFileStatusEmpty');
  const loadedEl = document.getElementById('scFileStatusLoaded');
  const nameEl   = document.getElementById('scFileStatusName');
  const sizeEl   = document.getElementById('scFileStatusSize');
  if (emptyEl)  emptyEl.style.display  = 'none';
  if (loadedEl) loadedEl.style.display = 'flex';
  if (nameEl)   nameEl.textContent     = fileName;
  if (sizeEl && fileSize) {
    const kb = fileSize > 1024 * 1024
      ? (fileSize / (1024 * 1024)).toFixed(1) + ' MB'
      : Math.round(fileSize / 1024) + ' KB';
    sizeEl.textContent = kb;
  }
}

function clearCurrentFile() {
  currentFileMeta = null;
  const badge = document.querySelector('.file-badge');
  if (badge) badge.remove();
  if (studyEls.userInput) {
    studyEls.userInput.placeholder = 'Ask a question, explain a concept, or upload a file…';
  }
  // Reset sidebar status card
  const emptyEl  = document.getElementById('scFileStatusEmpty');
  const loadedEl = document.getElementById('scFileStatusLoaded');
  if (emptyEl)  emptyEl.style.display  = 'flex';
  if (loadedEl) loadedEl.style.display = 'none';
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
    studyEls.sendBtn.innerHTML = isBusy
      ? '<span class="btn-spinner" style="display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite"></span>'
      : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/></svg>';
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
  studyEls.userInput.style.height = '24px';
  updateSendButtonState();
  
  // Show typing indicator
  const typingId = addTypingIndicator();
  
  try {
    studyAbortController = new AbortController();
    
    const formData = new FormData();
    formData.append('prompt', userText);
    
    // Add conversation history for context
    formData.append('conversation_history', JSON.stringify(conversationHistory.slice(-10)));
    
    if (currentFileMeta?.id) {
      formData.append('file_id', currentFileMeta.id);
    }
    
    const response = await fetch('/api/study/analyze', {
      method: 'POST',
      body: formData,
      signal: studyAbortController.signal
    });
    
    removeTypingIndicator(typingId);
    
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
      // Handle demo limit specifically
      if (response.status === 403 && (data.demo_limited || data.demo_restricted)) {
        const limitMsg = data.message || 'Demo limit reached. Register a real account for unlimited access.';
        addStudyMessage('error', '⚠️ ' + limitMsg);
        setStudyBusyState(false);
        return;
      }
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    
    if (data.answer) {
      // Add AI response with typing effect
      const msgDiv = await addStudyMessageWithTyping('ai', data.answer);

      // Update conversation history
      conversationHistory.push(
        { role: 'user', content: userText },
        { role: 'assistant', content: data.answer }
      );

      // Save to local storage
      saveStudyMessage(userText, data.answer);

      // Auto-detect quiz content and add interactive CTA
      const parsedQs = parseQuizQuestions(data.answer);
      if (parsedQs.length >= 2 && msgDiv) {
        requestAnimationFrame(() => maybeAddQuizCTA(msgDiv, data.answer, parsedQs));
      }

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
      addStudyMessage('error', `${error.message || 'Something went wrong. Please try again.'}`);
    }
  } finally {
    setStudyBusyState(false);
    studyAbortController = null;
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
    return null;
  }
  
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

  // Trigger animation + post-render (LaTeX, code, flashcard CTA)
  requestAnimationFrame(() => {
    messageDiv.classList.add('message-enter-active');
    if (role === 'ai') {
      renderLatexAndCode(messageDiv);
      maybeAddFlashcardCTA(messageDiv, text);
    }
  });

  smoothScrollToBottom();

  return messageDiv;
}

async function addStudyMessageWithTyping(role, text) {
  if (!studyEls.chatMessages) {
    return null;
  }
  
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
    } catch (e) {
      bodyEl.textContent = text;
    }
    
    // Highlight code blocks
    messageDiv.querySelectorAll('pre code').forEach(block => {
      block.classList.add('hljs');
    });
  } else {
    bodyEl.textContent = text;
  }

  // Post-render: LaTeX math + code syntax highlighting + flashcard CTA
  requestAnimationFrame(() => {
    renderLatexAndCode(messageDiv);
    maybeAddFlashcardCTA(messageDiv, text);
  });

  // Trigger animation
  requestAnimationFrame(() => {
    messageDiv.classList.add('message-enter-active');
  });
  
  smoothScrollToBottom();
  
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

  requestAnimationFrame(() => {
    studyEls.chatMessages.scrollTop = studyEls.chatMessages.scrollHeight;
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
    studyChats = [];
  }
}

function saveStudyChats() {
  try {
    localStorage.setItem(LS_STUDY_CHATS, JSON.stringify(studyChats));
  } catch (err) {
    // silently handled
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
    // Fallback: summarize the conversation context
    studyEls.userInput.value = 'Please summarize all the key points and main concepts from our conversation so far. Organize it clearly with headings.';
    handleStudySendMessage();
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

  hideWelcomeState();
  setStudyBusyState(true);

  const typingId = addTypingIndicator();

  // Structured MCQ prompt — works with or without a file
  const quizPrompt = [
    'Generate a 8-question multiple-choice quiz' +
    (currentFileMeta ? ` based on the uploaded document "${currentFileMeta.name}"` : ' on the topic we have been discussing or a general knowledge topic of your choice') + '.',
    '',
    'For EACH question use EXACTLY this format (do not deviate):',
    '',
    '**Q1.** [Question text]',
    'A) [Option A]',
    'B) [Option B]',
    'C) [Option C]',
    'D) [Option D]',
    '**Correct**: [A/B/C/D]',
    '**Explanation**: [One sentence explanation]',
    '',
    '---',
    '',
    'Number questions Q1 through Q8. Every question MUST have exactly 4 options (A–D), a **Correct** line, and an **Explanation** line.',
  ].join('\n');

  try {
    const formData = new FormData();
    formData.append('prompt', quizPrompt);
    formData.append('conversation_history', JSON.stringify(conversationHistory.slice(-6)));
    if (currentFileMeta?.id) formData.append('file_id', currentFileMeta.id);

    const response = await fetch('/api/study/analyze', {
      method: 'POST',
      body: formData,
    });

    const data = await response.json().catch(() => ({}));
    removeTypingIndicator(typingId);

    if (!response.ok) throw new Error(data.error || 'Quiz generation failed');

    const rawText = data.answer || '';
    const questions = parseQuizQuestions(rawText);

    if (questions.length > 0) {
      // Show a brief "Quiz ready!" message instead of the raw text wall
      const summaryLines = [`**Quiz ready!** Generated **${questions.length} questions**.`];
      if (currentFileMeta) summaryLines.push(`Based on: *${currentFileMeta.name}*`);
      summaryLines.push('\nClick **Take Interactive Quiz** below to start.');

      const msgDiv = await addStudyMessageWithTyping('ai', summaryLines.join('\n'));

      // Append interactive CTA
      if (msgDiv) {
        requestAnimationFrame(() => maybeAddQuizCTA(msgDiv, rawText, questions));
      }

      // Auto-launch quiz modal after short delay
      setTimeout(() => openQuizMode(questions), 700);

      saveStudyMessage('Generate interactive quiz', summaryLines.join('\n'));
    } else {
      // Fallback: render raw text if parsing fails
      await addStudyMessageWithTyping('ai', rawText || 'Could not generate quiz.');
      saveStudyMessage('Generate quiz', rawText);
    }

  } catch (error) {
    removeTypingIndicator(typingId);
    addStudyMessage('error', error.message);
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

    const answer = data.answer || 'Could not generate flashcards.';
    await addStudyMessageWithTyping('ai', answer);

    saveStudyMessage('Generate flashcards', answer);

    // Auto-launch flashcard modal if parseable cards found
    const cards = parseFlashcards(answer);
    if (cards.length > 0) {
      setTimeout(() => openFlashcardMode(answer), 600);
    }
    
  } catch (error) {
    removeTypingIndicator(typingId);
    addStudyMessage('error', `${error.message}`);
  } finally {
    setStudyBusyState(false);
  }
}

async function explainConcept() {
  const typed = studyEls.userInput?.value.trim();
  if (typed) {
    // If user has something typed, explain that
    studyEls.userInput.value = `Explain "${typed}" in simple, clear terms with real-world examples. Cover: what it is, how it works, why it matters, and any common misconceptions.`;
  } else {
    // Prompt user to type something
    if (studyEls.userInput) {
      studyEls.userInput.focus();
      studyEls.userInput.placeholder = '✏️ Type a concept or topic to explain, then press Enter...';
      setTimeout(() => {
        if (studyEls.userInput) {
          studyEls.userInput.placeholder = 'Ask a question, explain a concept, or upload a file…';
        }
      }, 4000);
    }
    return;
  }
  handleStudySendMessage();
}

async function generateMindMap() {
  const prompt = currentFileMeta?.id
    ? `Create a detailed mind map of the key concepts from the uploaded document "${currentFileMeta.name}". Use markdown with headings and nested bullet points to show hierarchical relationships. Include: main topic, major branches, sub-topics, and key connections.`
    : `Create a structured mind map of the topic we have been discussing. Use markdown headings (##, ###) and nested bullet points to show all key concepts, relationships, and connections clearly.`;

  studyEls.userInput.value = prompt;
  handleStudySendMessage();
}

async function generateTimeline() {
  const prompt = currentFileMeta?.id
    ? `Create a chronological timeline from the uploaded document "${currentFileMeta.name}". Format each entry as:\n**[Date/Period]** — [Event/Development]\n- Context: ...\n- Significance: ...\n\nCover all major events, milestones, and developments in order.`
    : `Create a chronological timeline of key events and developments from what we have been discussing. Format each entry as: **[Date/Period]** — [Description with context and significance].`;

  studyEls.userInput.value = prompt;
  handleStudySendMessage();
}

async function generateNotes() {
  const prompt = currentFileMeta?.id
    ? `Generate comprehensive study notes from the uploaded document "${currentFileMeta.name}". Organize by topics with: key definitions, important concepts, formulas/rules, examples, and summary points. Use clear headings and bullet points.`
    : `Generate comprehensive study notes on the topic we have been discussing. Organize by main topics with key definitions, concepts, examples, and a summary. Use clear headings and bullet points.`;

  studyEls.userInput.value = prompt;
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
// LATEX + CODE RENDERING
// ============================================

/**
 * Render LaTeX math and syntax-highlight code blocks
 * inside a message element. Called after each AI response.
 */
function renderLatexAndCode(messageEl) {
  if (!messageEl) return;

  // ── KaTeX: render $...$ and $$...$$ ─────────────────────
  if (typeof renderMathInElement !== 'undefined') {
    try {
      renderMathInElement(messageEl, {
        delimiters: [
          { left: '$$', right: '$$', display: true  },
          { left: '$',  right: '$',  display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true  },
        ],
        throwOnError: false,
        errorColor: '#f87171',
      });
    } catch (e) {
      // KaTeX not ready yet, silently skip
    }
  }

  // ── highlight.js: syntax-highlight all code blocks ───────
  if (typeof hljs !== 'undefined') {
    messageEl.querySelectorAll('pre code').forEach(block => {
      // Skip if already highlighted
      if (block.dataset.highlighted) return;
      hljs.highlightElement(block);
      block.dataset.highlighted = 'yes';

      // Add copy button to parent <pre>
      const pre = block.parentElement;
      if (pre && !pre.querySelector('.code-copy-btn')) {
        const btn = document.createElement('button');
        btn.className = 'code-copy-btn';
        btn.textContent = 'Copy';
        btn.addEventListener('click', () => {
          navigator.clipboard.writeText(block.innerText || block.textContent).then(() => {
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
          });
        });
        pre.style.position = 'relative';
        pre.appendChild(btn);
      }
    });
  }
}

// ============================================
// FLASHCARD MODAL CONTROLLER
// ============================================

let fcCards  = [];
let fcIdx    = 0;
let fcScore  = { got: 0, again: 0 };

/**
 * Parse flashcard pairs from an AI response.
 * Supports multiple formats including inline formats like:
 *   - 1. Term/Question: X Definition/Answer: Y
 *   - **Term/Question**: X **Definition/Answer**: Y
 *   - Term: X | Definition: Y
 */
function parseFlashcards(text) {
  const cards = [];
  
  // Normalize text
  let normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  
  // STRATEGY 1: Split by numbered items first, then extract term/definition from each
  // Pattern: "4. Term/Question: X Definition/Answer: Y"
  // We need to find where each numbered item starts
  
  // Insert newlines before each numbered pattern to make splitting easier
  const withBreaks = normalizedText.replace(/(\d+)\.\s+(?:Term|Question)/gi, '\n$1. Term/Question');
  const blocks = withBreaks.split(/\n/).filter(b => b.trim());
  
  for (const block of blocks) {
    // Skip if doesn't contain both term and definition
    if (!(/(?:Term|Question)/i.test(block) && /(?:Definition|Answer)/i.test(block))) continue;
    
    // Extract using split on Definition/Answer
    const parts = block.split(/(?:Definition|Answer)(?:\/(?:Answer|Definition))?[:\s]+/i);
    if (parts.length >= 2) {
      // First part contains the term/question
      let front = parts[0].replace(/^\d+\.\s*/, '').replace(/(?:\*\*)?(?:Term|Question)(?:\/(?:Question|Term))?(?:\*\*)?[:\s]*/i, '').replace(/\*\*/g, '').trim();
      // Second part (and beyond) is the definition/answer
      let back = parts.slice(1).join(' ').replace(/\*\*/g, '').trim();
      
      // Remove any trailing numbered item that might have been caught
      back = back.replace(/\s+\d+\.\s*(?:Term|Question).*$/i, '').trim();
      
      if (front && back && front.length < 500 && back.length < 2000) {
        cards.push({ front, back });
      }
    }
  }
  
  if (cards.length > 0) return cards;
  
  // STRATEGY 2: Use regex to find all Term/Question...Definition/Answer pairs
  // Handle continuous text where cards run into each other
  const cardRegex = /(?:\d+\.\s*)?(?:\*\*)?(?:Term|Question)(?:\/(?:Question|Term))?(?:\*\*)?[:\s]+(.+?)(?:\*\*)?(?:Definition|Answer)(?:\/(?:Answer|Definition))?(?:\*\*)?[:\s]+(.+?)(?=(?:\d+\.\s*)?(?:\*\*)?(?:Term|Question)|$)/gis;
  
  let match;
  while ((match = cardRegex.exec(normalizedText)) !== null) {
    let front = match[1].replace(/\*\*/g, '').trim();
    let back = match[2].replace(/\*\*/g, '').trim();
    
    if (front && back && front.length < 500 && back.length < 2000) {
      cards.push({ front, back });
    }
  }
  
  if (cards.length > 0) return cards;
  
  // STRATEGY 3: Split by horizontal rule (---)
  const hrBlocks = normalizedText.split(/\n-{3,}\n/);
  for (const block of hrBlocks) {
    const termMatch = block.match(/\*\*(?:Term|Question)[^*]*\*\*[:\s]*([\s\S]+?)(?=\*\*(?:Definition|Answer)|$)/i);
    const defMatch = block.match(/\*\*(?:Definition|Answer)[^*]*\*\*[:\s]*([\s\S]+?)$/i);
    if (termMatch && defMatch) {
      const front = termMatch[1].trim().replace(/\*\*/g, '');
      const back = defMatch[1].trim().replace(/\*\*/g, '');
      if (front && back) cards.push({ front, back });
    }
  }
  
  if (cards.length > 0) return cards;
  
  // STRATEGY 4: Line-by-line pattern matching for multiline format
  const lines = normalizedText.split('\n').filter(l => l.trim());
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Check if single line contains both term and definition
    const singleLineMatch = line.match(/(?:\d+\.\s*)?(?:\*\*)?(?:Term|Question)[^:]*(?:\*\*)?[:\s]+(.+?)\s+(?:\*\*)?(?:Definition|Answer)[^:]*(?:\*\*)?[:\s]+(.+)/i);
    if (singleLineMatch) {
      const front = singleLineMatch[1].replace(/\*\*/g, '').trim();
      const back = singleLineMatch[2].replace(/\*\*/g, '').trim();
      if (front && back) cards.push({ front, back });
      continue;
    }
    
    // Check if this line is Term and next line is Definition
    if (/(?:Term|Question)/i.test(line) && lines[i + 1] && /(?:Definition|Answer)/i.test(lines[i + 1])) {
      const front = line.replace(/^(?:\d+\.\s*)?(?:\*\*)?(?:Term|Question)[^:]*(?:\*\*)?[:\s]*/i, '').replace(/\*\*/g, '').trim();
      const back = lines[i + 1].replace(/^(?:\*\*)?(?:Definition|Answer)[^:]*(?:\*\*)?[:\s]*/i, '').replace(/\*\*/g, '').trim();
      if (front && back) {
        cards.push({ front, back });
        i++; // Skip next line
      }
    }
  }
  
  return cards;
}

function openFlashcardMode(text) {
  const cards = parseFlashcards(text);
  if (cards.length === 0) {
    addStudyMessage('system', 'No flashcard pairs found. Ask for flashcards in "Term: … / Definition: …" format.');
    return;
  }

  fcCards = cards;
  fcIdx   = 0;
  fcScore = { got: 0, again: 0 };

  const overlay  = document.getElementById('fcOverlay');
  const card     = document.getElementById('fcCard');
  const front    = document.getElementById('fcFront');
  const back     = document.getElementById('fcBack');
  const progress = document.getElementById('fcProgress');
  const flipBtn  = document.getElementById('fcFlip');
  const passBtn  = document.getElementById('fcPass');
  const failBtn  = document.getElementById('fcFail');
  const closeBtn = document.getElementById('fcClose');

  if (!overlay) return;

  function showCard(i) {
    const c = fcCards[i];
    if (!c) return;
    card.classList.remove('flipped');
    front.textContent   = c.front;
    back.textContent    = c.back;
    progress.textContent = `Card ${i + 1} of ${fcCards.length}`;
  }

  function nextCard() {
    if (fcIdx + 1 >= fcCards.length) {
      // Session complete
      const pct = Math.round((fcScore.got / fcCards.length) * 100);
      front.textContent = `Session complete! 🎉`;
      back.textContent  = `Score: ${fcScore.got}/${fcCards.length} (${pct}%)`;
      card.classList.remove('flipped');
      progress.textContent = 'Done';
      passBtn.disabled = true;
      failBtn.disabled = true;
      return;
    }
    fcIdx++;
    showCard(fcIdx);
  }

  flipBtn.onclick  = () => card.classList.toggle('flipped');
  card.onclick     = (e) => { if (!e.target.closest('.fc-controls')) card.classList.toggle('flipped'); };
  passBtn.onclick  = () => { fcScore.got++;   nextCard(); };
  failBtn.onclick  = () => { fcScore.again++; nextCard(); };
  closeBtn.onclick = () => {
    overlay.classList.remove('active');
    passBtn.disabled = false;
    failBtn.disabled = false;
  };

  showCard(0);
  overlay.classList.add('active');
}

/**
 * Detect whether a response contains flashcard content and
 * optionally append a CTA button to enter flashcard mode.
 */
function maybeAddFlashcardCTA(messageDiv, text) {
  const hasFlashcards = /\*\*(Term|Question|Definition|Answer)/i.test(text) ||
                        /---/.test(text) && /\*\*/.test(text);
  if (!hasFlashcards) return;

  const footer = messageDiv?.querySelector('.message-footer');
  if (!footer) return;

  const cta = document.createElement('button');
  cta.className = 'fc-cta';
  cta.innerHTML = '🎴 Enter Flashcard Mode';
  cta.addEventListener('click', () => openFlashcardMode(text));
  footer.insertAdjacentElement('afterend', cta);
}


// ============================================
// INTERACTIVE QUIZ ENGINE
// ============================================

let qzQuestions = [];
let qzIdx       = 0;
let qzScore     = 0;

/**
 * Parse structured MCQ quiz text into question objects.
 * Expected AI format:
 *   **Q1.** Question text
 *   A) Option text
 *   B) ...  C) ...  D) ...
 *   **Correct**: B
 *   **Explanation**: Why B is correct
 *   ---
 */
function parseQuizQuestions(text) {
  const questions = [];

  // Split on separators (--- or ### Q) between questions
  const blocks = text.split(/\n[-─]{2,}\n|\n(?=\*\*Q\d)/);

  blocks.forEach(block => {
    if (!block.trim()) return;

    // Extract question text
    const qMatch = block.match(/\*\*Q\d+\.\*\*\s*([\s\S]+?)(?=\n[A-D]\))/i);
    if (!qMatch) return;

    const questionText = qMatch[1].trim().replace(/\*\*/g, '');

    // Extract options A-D
    const opts = {};
    ['A','B','C','D'].forEach(letter => {
      const re = new RegExp(`^${letter}\\)\\s*(.+)`, 'm');
      const m = block.match(re);
      if (m) opts[letter] = m[1].trim();
    });

    if (Object.keys(opts).length < 2) return;

    // Extract correct answer
    const corrMatch = block.match(/\*\*Correct\*\*[:\s]+([A-D])/i);
    if (!corrMatch) return;
    const correct = corrMatch[1].toUpperCase();

    // Extract explanation
    const expMatch = block.match(/\*\*Explanation\*\*[:\s]*([\s\S]+?)(?=\n\*\*Q|\n---|$)/i);
    const explanation = expMatch ? expMatch[1].trim().replace(/\*\*/g, '') : '';

    questions.push({ questionText, opts, correct, explanation });
  });

  return questions;
}

/**
 * Launch the interactive quiz modal with given questions array.
 */
function openQuizMode(questions) {
  if (!questions || questions.length === 0) return;

  qzQuestions = questions;
  qzIdx       = 0;
  qzScore     = 0;

  const overlay    = document.getElementById('qzOverlay');
  const card       = document.getElementById('qzCard');
  const resultsDiv = document.getElementById('qzResults');

  if (!overlay) return;

  // Hide results, show card
  card.style.display       = '';
  resultsDiv.style.display = 'none';
  resultsDiv.classList.remove('show');

  renderQzQuestion(0);
  overlay.classList.add('active');

  // Wire static buttons
  document.getElementById('qzClose').onclick       = closeQuizModal;
  document.getElementById('qzNext').onclick        = advanceQuiz;
  document.getElementById('qzRetry').onclick       = () => openQuizMode(qzQuestions);
  document.getElementById('qzResultsClose').onclick = closeQuizModal;
}

function closeQuizModal() {
  const overlay = document.getElementById('qzOverlay');
  if (overlay) overlay.classList.remove('active');
}

function renderQzQuestion(i) {
  const q = qzQuestions[i];
  if (!q) return;

  const total       = qzQuestions.length;
  const pct         = (i / total) * 100;

  // Update header meta
  document.getElementById('qzProgressText').textContent = `Q${i+1} of ${total}`;
  document.getElementById('qzScoreBadge').textContent   = `Score: ${qzScore}`;
  document.getElementById('qzProgressFill').style.width = `${pct}%`;
  document.getElementById('qzQLabel').textContent       = `Question ${i+1} of ${total}`;
  document.getElementById('qzQuestion').textContent     = q.questionText;

  // Hide feedback + next
  const feedback = document.getElementById('qzFeedback');
  const nextBtn  = document.getElementById('qzNext');
  feedback.className = 'qz-feedback';
  feedback.style.display = '';
  nextBtn.style.display  = 'none';

  // Update next button label for last question
  nextBtn.textContent = (i + 1 >= total) ? 'See Results 🎯' : 'Next Question →';

  // Render options
  const optionsEl = document.getElementById('qzOptions');
  optionsEl.innerHTML = '';

  ['A','B','C','D'].forEach(letter => {
    if (!q.opts[letter]) return;

    const btn = document.createElement('button');
    btn.className = 'qz-option';
    btn.innerHTML = `
      <span class="qz-opt-letter">${letter}</span>
      <span class="qz-opt-text">${escapeHtml(q.opts[letter])}</span>
    `;

    btn.addEventListener('click', () => handleOptionClick(letter, q));
    optionsEl.appendChild(btn);
  });
}

function handleOptionClick(selected, q) {
  const optionsEl = document.getElementById('qzOptions');
  const feedback  = document.getElementById('qzFeedback');
  const nextBtn   = document.getElementById('qzNext');
  const isCorrect = selected === q.correct;

  // Disable all options
  optionsEl.querySelectorAll('.qz-option').forEach((btn, idx) => {
    const letter = ['A','B','C','D'][idx];
    btn.disabled = true;

    if (letter === q.correct) {
      btn.classList.add('correct');
    } else if (letter === selected && !isCorrect) {
      btn.classList.add('wrong');
    } else {
      btn.classList.add('dimmed');
    }
  });

  if (isCorrect) qzScore++;

  // Update score badge
  document.getElementById('qzScoreBadge').textContent = `Score: ${qzScore}`;

  // Show feedback
  feedback.innerHTML = `
    <span class="qz-feedback-icon">${isCorrect ? '✅' : '❌'}</span>
    <div class="qz-feedback-text">
      <strong>${isCorrect ? 'Correct!' : `Wrong — correct answer: ${q.correct}) ${escapeHtml(q.opts[q.correct] || '')}`}</strong>
      ${q.explanation ? escapeHtml(q.explanation) : ''}
    </div>
  `;
  feedback.className = `qz-feedback show ${isCorrect ? 'correct-fb' : 'wrong-fb'}`;

  // Show next button
  nextBtn.style.display = 'block';
}

function advanceQuiz() {
  qzIdx++;
  if (qzIdx >= qzQuestions.length) {
    showQuizResults();
  } else {
    renderQzQuestion(qzIdx);
  }
}

function showQuizResults() {
  const card       = document.getElementById('qzCard');
  const resultsDiv = document.getElementById('qzResults');
  const total      = qzQuestions.length;
  const pct        = Math.round((qzScore / total) * 100);

  // Progress bar to 100%
  document.getElementById('qzProgressFill').style.width = '100%';
  document.getElementById('qzProgressText').textContent = 'Complete!';

  // Results text
  document.getElementById('qzResultsScore').textContent = `${qzScore} / ${total}`;

  let icon, title, sub;
  if (pct === 100)      { icon = '🏆'; title = 'Perfect Score!';    sub = 'Outstanding! You nailed every question.'; }
  else if (pct >= 80)   { icon = '🎉'; title = 'Excellent!';         sub = `You got ${pct}% — great understanding!`; }
  else if (pct >= 60)   { icon = '👍'; title = 'Good Job!';           sub = `${pct}% — keep studying to improve.`; }
  else if (pct >= 40)   { icon = '📖'; title = 'Keep Studying';       sub = `${pct}% — review the material again.`; }
  else                  { icon = '💪'; title = 'Keep Practicing!';    sub = `${pct}% — don't give up, review the topic.`; }

  document.getElementById('qzResultsIcon').textContent  = icon;
  document.getElementById('qzResultsTitle').textContent = title;
  document.getElementById('qzResultsSub').textContent   = sub;

  card.style.display = 'none';
  resultsDiv.style.display = 'flex';
  resultsDiv.classList.add('show');

  // Animate bar
  requestAnimationFrame(() => {
    setTimeout(() => {
      document.getElementById('qzResultsBar').style.width = `${pct}%`;
    }, 100);
  });
}

/**
 * Detect quiz content in a message and append "Take Interactive Quiz" CTA.
 */
function maybeAddQuizCTA(messageDiv, text, questions) {
  if (!questions || questions.length === 0) return;

  const footer = messageDiv?.querySelector('.message-footer');
  if (!footer) return;

  const cta = document.createElement('button');
  cta.className = 'qz-cta';
  cta.innerHTML = '📝 Take Interactive Quiz';
  cta.addEventListener('click', () => openQuizMode(questions));
  footer.insertAdjacentElement('afterend', cta);
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
window.openFlashcardMode = openFlashcardMode;
window.renderLatexAndCode = renderLatexAndCode;
window.openQuizMode = openQuizMode;
window.closeQuizModal = closeQuizModal;
window.parseQuizQuestions = parseQuizQuestions;

// ============================================
// AUTO-INIT
// ============================================
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initStudyChat);
} else {
  initStudyChat();
}

})(); // end IIFE
