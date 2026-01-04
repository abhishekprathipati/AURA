  // ============================================
// AURA STUDY CHAT ENGINE - ULTRA PRO
// ============================================

// Request lock to prevent multiple simultaneous API calls
let isStudyBotActive = false;
let requestAbortController = null;

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
};

// Chat state
let currentStudyChatId = null;
let studyChats = [];
const LS_STUDY_CHATS = 'aura_study_chats';
let uploadedFile = null;

// ============================================
// INITIALIZATION
// ============================================
function initStudyChat() {
  cacheStudyElements();
  loadStudyChats();
  renderStudyHistory();
  setupStudyEventListeners();
  
  // Ensure scroll container is properly initialized
  if (studyEls.chatMessages) {
    studyEls.chatMessages.scrollTop = studyEls.chatMessages.scrollHeight;
  }
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

  // Input Enter key handler - PREVENTS PAGE JUMP
  if (studyEls.userInput) {
    studyEls.userInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); // STOPS THE UPWARD JUMP
        handleStudySendMessage();
      }
    });
  }
  
  // New chat button
  if (studyEls.newChatBtn) {
    studyEls.newChatBtn.addEventListener('click', startNewStudyChat);
  }
  
  // File upload trigger
  const fileUploadBtn = document.getElementById('attachFileBtn');
  const fileUploadInput = document.getElementById('fileUpload');
  
  if (fileUploadBtn && fileUploadInput) {
    fileUploadBtn.addEventListener('click', () => {
      fileUploadInput.click();
    });
  }
  
  // File upload handler - ADVANCED UPLOAD LOGIC
  if (fileUploadInput) {
    fileUploadInput.addEventListener('change', handleFileUpload);
  }
  
  // Quick chip handlers
  const quickChips = document.querySelectorAll('.quick-chip');
  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt && studyEls.userInput) {
        studyEls.userInput.value = prompt;
        studyEls.userInput.focus();
      }
    });
  });
  
  // Example prompt handlers
  const examplePrompts = document.querySelectorAll('.example-prompt');
  examplePrompts.forEach(prompt => {
    prompt.addEventListener('click', () => {
      const promptText = prompt.getAttribute('data-prompt');
      if (promptText && studyEls.userInput) {
        studyEls.userInput.value = promptText;
        studyEls.userInput.focus();
      }
    });
  });
  
  // Quick action card handlers
  const quickActionCards = document.querySelectorAll('.quick-action-card');
  quickActionCards.forEach(card => {
    card.addEventListener('click', () => {
      const action = card.getAttribute('data-action');
      if (!action || !studyEls.userInput) return;
      
      let prompt = '';
      switch(action) {
        case 'summarize':
          prompt = 'Please summarize the uploaded PDF document';
          if (studyEls.fileInput) studyEls.fileInput.click();
          break;
        case 'flashcards':
          prompt = 'Generate flashcards for studying the key concepts';
          break;
        case 'explain':
          prompt = 'Explain this concept in simple terms: ';
          break;
      }
      
      studyEls.userInput.value = prompt;
      studyEls.userInput.focus();
    });
  });
}

// ============================================
// FILE UPLOAD HANDLING - ADVANCED LOGIC
// ============================================
async function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  uploadedFile = file;
  console.log('📎 File selected:', file.name);

  // Show visual feedback in chat
  addStudyMessage('system', `Uploading: ${file.name}...`);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/upload_study_file', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed with status ${response.status}`);
    }
    
    const data = await response.json();
    
    // Success feedback
    addStudyMessage('bot', `✅ File "${file.name}" ready for analysis. Ask me anything about it!`);
    console.log('✅ File upload successful');
    
    // Update UI to show file is ready
    if (studyEls.userInput) {
      studyEls.userInput.placeholder = `📎 ${file.name} - Ask your question...`;
    }
    
    // Add file to active files list
    addFileToActivelist(file.name);
    
  } catch (error) {
    console.error('❌ Upload error:', error);
    addStudyMessage('error', "Upload failed. Please try again with a different file.");
  }
}

// Helper: Add file to active files list
function addFileToActivelist(fileName) {
  const fileList = document.getElementById('fileList');
  if (!fileList) return;
  
  const fileItem = document.createElement('div');
  fileItem.className = 'file-item';
  fileItem.innerHTML = `<span>📄 ${fileName}</span>`;
  fileList.appendChild(fileItem);
}

// ============================================
// SEND MESSAGE WITH REQUEST LOCK
// ============================================
async function handleStudySendMessage(e) {
  if (e) e.preventDefault();
  
  // CRITICAL: Request lock - prevent overlapping requests
  if (isStudyBotActive) {
    console.warn('⚠️ Study bot is processing. Please wait.');
    return;
  }
  
  const userText = studyEls.userInput.value.trim();
  if (!userText) {
    studyEls.userInput.focus();
    return;
  }
  
  // Activate lock and update UI state
  isStudyBotActive = true;
  if (studyEls.sendBtn) {
    studyEls.sendBtn.disabled = true;
    studyEls.sendBtn.style.opacity = '0.5';
  }
  if (studyEls.userInput) {
    studyEls.userInput.placeholder = '⏳ AURA is analyzing...';
  }
  
  // Hide welcome state
  if (studyEls.welcomeState) {
    studyEls.welcomeState.style.display = 'none';
  }
  
  // Add user message
  addStudyMessage('user', userText);
  studyEls.userInput.value = '';
  
  // Reset file upload placeholder
  if (studyEls.userInput) {
    studyEls.userInput.placeholder = 'Ask a question, upload a file...';
  }
  
  // Show typing indicator
  const typingId = addStudyTypingIndicator();
  
  try {
    // Create AbortController for cancellation support
    requestAbortController = new AbortController();
    
    const formData = new FormData();
    formData.append('prompt', userText);
    
    if (uploadedFile) {
      formData.append('file', uploadedFile);
      console.log('📎 Uploading file:', uploadedFile.name);
    }
    
    console.log('🚀 Sending request to /api/study/analyze');
    console.log('📝 Prompt:', userText);
    
    const response = await fetch('/api/study/analyze', {
      method: 'POST',
      body: formData,
      signal: requestAbortController.signal
    });
    
    removeStudyTypingIndicator(typingId);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('❌ API Error:', errorData);
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('✅ API Response:', data);
    
    // API returns 'answer' field
    if (data.answer) {
      addStudyMessage('ai', data.answer);
      // Save to chat history
      saveStudyMessage(userText, data.answer);
    } else if (data.error) {
      throw new Error(data.error);
    } else {
      throw new Error('No response from AI');
    }
    
  } catch (error) {
    removeStudyTypingIndicator(typingId);
    
    if (error.name === 'AbortError') {
      console.log('Request was cancelled');
      addStudyMessage('ai', '⚠️ Request was cancelled.');
    } else {
      console.error('Error sending message:', error);
      const errorMsg = error.message || 'Sorry, I encountered an error. Please try again.';
      addStudyMessage('ai', `❌ Error: ${errorMsg}`);
    }
  } finally {
    // Release lock and restore UI state
    isStudyBotActive = false;
    if (studyEls.sendBtn) {
      studyEls.sendBtn.disabled = false;
      studyEls.sendBtn.style.opacity = '1';
    }
    if (studyEls.userInput) {
      studyEls.userInput.placeholder = 'Ask a question, upload a file...';
    }
    requestAbortController = null;
    uploadedFile = null;
    if (studyEls.fileInput) studyEls.fileInput.value = '';
  }
}

// ============================================
// TYPEWRITER EFFECT FOR AI RESPONSES
// ============================================
async function typeWriterEffect(text, role = 'ai') {
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message', `${role}-message`);
  
  // For markdown content
  if (role === 'ai' && typeof marked !== 'undefined') {
    const htmlContent = marked.parse(text);
    messageDiv.innerHTML = htmlContent;
  } else {
    messageDiv.textContent = '';
  }
  
  studyEls.chatMessages.appendChild(messageDiv);
  
  // Typewriter animation for plain text
  if (role === 'ai' && typeof marked === 'undefined') {
    for (let i = 0; i < text.length; i++) {
      messageDiv.textContent += text.charAt(i);
      smoothScrollToBottom(studyEls.chatMessages);
      await new Promise(resolve => setTimeout(resolve, 15)); // 15ms per character
    }
  } else {
    smoothScrollToBottom(studyEls.chatMessages);
  }
}

// ============================================
// MESSAGE RENDERING
// ============================================
function addStudyMessage(role, text) {
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message');
  messageDiv.classList.add(role === 'user' ? 'user-message' : 'ai-message');
  
  if (role === 'ai' && typeof marked !== 'undefined') {
    messageDiv.innerHTML = marked.parse(text);
  } else {
    messageDiv.textContent = text;
  }
  
  studyEls.chatMessages.appendChild(messageDiv);
  smoothScrollToBottom(studyEls.chatMessages);
}

function addStudyTypingIndicator() {
  const typingId = 'typing-' + Date.now();
  const typingDiv = document.createElement('div');
  typingDiv.id = typingId;
  typingDiv.classList.add('message', 'ai-message', 'typing-indicator');
  typingDiv.innerHTML = `
    <div class="typing">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  
  studyEls.chatMessages.appendChild(typingDiv);
  smoothScrollToBottom(studyEls.chatMessages);
  
  return typingId;
}

function removeStudyTypingIndicator(typingId) {
  const typingDiv = document.getElementById(typingId);
  if (typingDiv) typingDiv.remove();
}

function smoothScrollToBottom(container) {
  if (!container) return;
  
  const target = container.scrollHeight - container.clientHeight;
  const start = container.scrollTop;
  const distance = target - start;
  const duration = 300;
  let startTime = null;
  
  function animation(currentTime) {
    if (!startTime) startTime = currentTime;
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Easing function
    const easeProgress = progress * (2 - progress);
    
    container.scrollTop = start + (distance * easeProgress);
    
    if (progress < 1) {
      requestAnimationFrame(animation);
    }
  }
  
  requestAnimationFrame(animation);
}

// ============================================
// CHAT HISTORY MANAGEMENT
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
    const chatTitle = userMsg.slice(0, 50) + (userMsg.length > 50 ? '...' : '');
    studyChats.unshift({
      id: currentStudyChatId,
      title: chatTitle,
      messages: []
    });
  }
  
  const chat = studyChats.find(c => c.id === currentStudyChatId);
  if (chat) {
    chat.messages.push({ role: 'user', text: userMsg });
    chat.messages.push({ role: 'ai', text: aiMsg });
    saveStudyChats();
    renderStudyHistory();
  }
}

function startNewStudyChat() {
  currentStudyChatId = null;
  
  // Clear messages
  if (studyEls.chatMessages) {
    studyEls.chatMessages.innerHTML = '';
  }
  
  // Show welcome state
  if (studyEls.welcomeState) {
    studyEls.welcomeState.style.display = 'flex';
  }
  
  // Clear input
  if (studyEls.userInput) {
    studyEls.userInput.value = '';
    studyEls.userInput.focus();
  }
  
  // Clear file upload
  uploadedFile = null;
  if (studyEls.fileInput) studyEls.fileInput.value = '';
  
  renderStudyHistory();
}

function renderStudyHistory() {
  if (!studyEls.historyList) return;
  
  if (studyChats.length === 0) {
    studyEls.historyList.innerHTML = '<div class="history-empty">No conversations yet</div>';
    return;
  }
  
  studyEls.historyList.innerHTML = '';
  
  studyChats.forEach(chat => {
    const item = document.createElement('div');
    item.classList.add('history-item');
    if (chat.id === currentStudyChatId) {
      item.classList.add('active');
    }
    
    item.innerHTML = `
      <span class="history-item-icon">💬</span>
      <span class="history-item-text">${chat.title}</span>
    `;
    
    item.addEventListener('click', () => loadStudyChat(chat.id));
    studyEls.historyList.appendChild(item);
  });
}

function loadStudyChat(chatId) {
  const chat = studyChats.find(c => c.id === chatId);
  if (!chat) return;
  
  currentStudyChatId = chatId;
  
  // Hide welcome
  if (studyEls.welcomeState) {
    studyEls.welcomeState.style.display = 'none';
  }
  
  // Clear and reload messages
  if (studyEls.chatMessages) {
    studyEls.chatMessages.innerHTML = '';
  }
  
  chat.messages.forEach(msg => {
    addStudyMessage(msg.role, msg.text);
  });
  
  renderStudyHistory();
}

// ============================================
// STUDY HUB QUICK ACTIONS
// ============================================
function triggerSummarize() {
  if (studyEls.userInput) {
    studyEls.userInput.value = 'Please summarize the uploaded PDF document, highlighting key concepts and main points.';
    studyEls.userInput.focus();
    document.getElementById('fileUpload')?.click();
  }
}

function triggerQuiz() {
  if (studyEls.userInput) {
    studyEls.userInput.value = 'Generate 5 multiple-choice questions based on this material to test my understanding.';
    studyEls.userInput.focus();
  }
}

function triggerFlashcards() {
  if (studyEls.userInput) {
    studyEls.userInput.value = 'Create flashcard-style study materials with key terms and definitions from this content.';
    studyEls.userInput.focus();
  }
}

// Export functions for global access
window.triggerSummarize = triggerSummarize;
window.triggerQuiz = triggerQuiz;
window.triggerFlashcards = triggerFlashcards;
window.initStudyChat = initStudyChat;
window.handleStudySendMessage = handleStudySendMessage;
window.startNewStudyChat = startNewStudyChat;

// ============================================
// TYPING INDICATOR ANIMATION
// ============================================
const typingStyles = document.createElement('style');
typingStyles.textContent = `
.typing {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
}

.typing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typing-bounce 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(1) {
  animation-delay: 0s;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing-bounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
}
`;
document.head.appendChild(typingStyles);

// ============================================
// EXPORT FOR GLOBAL ACCESS
// ============================================
window.initStudyChat = initStudyChat;
window.handleStudySendMessage = handleStudySendMessage;
window.startNewStudyChat = startNewStudyChat;
