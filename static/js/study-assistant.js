// ============================================
// AURA STUDY ASSISTANT - PROFESSIONAL UI
// ============================================

// State Management
const studyState = {
    currentChatId: null,
    chats: [],
    theme: localStorage.getItem('aura-study-theme') || 'dark',
    focusMode: false,
    isGenerating: false
};

// Element Cache
const els = {
    messagesContainer: null,
    studyForm: null,
    studyInput: null,
    sendBtn: null,
    attachBtn: null,
    fileInput: null,
    voiceBtn: null,
    welcomeState: null,
    historyList: null,
    recentFilesList: null,
    themeToggle: null,
    focusModeToggle: null,
    newChatBtn: null
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    cacheElements();
    initTheme();
    initEventListeners();
    loadChatHistory();
    renderWelcome();
});

function cacheElements() {
    els.messagesContainer = document.getElementById('studyMessages');
    els.studyForm = document.getElementById('studyForm');
    els.studyInput = document.getElementById('studyInput');
    els.sendBtn = document.getElementById('sendBtn');
    els.attachBtn = document.getElementById('attachBtn');
    els.fileInput = document.getElementById('fileInput');
    els.voiceBtn = document.getElementById('voiceBtn');
    els.welcomeState = document.getElementById('studyWelcomeState');
    els.historyList = document.getElementById('studyHistoryList');
    els.recentFilesList = document.getElementById('recentFilesList');
    els.themeToggle = document.getElementById('themeToggle');
    els.focusModeToggle = document.getElementById('focusModeToggle');
    els.newChatBtn = document.getElementById('newStudyChat');
}

// ============================================
// THEME MANAGEMENT
// ============================================
function initTheme() {
    document.documentElement.setAttribute('data-theme', studyState.theme);
    updateThemeIcons(studyState.theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    studyState.theme = newTheme;
    localStorage.setItem('aura-study-theme', newTheme);
    updateThemeIcons(newTheme);
}

function updateThemeIcons(theme) {
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    
    if (theme === 'dark') {
        if (sunIcon) sunIcon.style.display = 'none';
        if (moonIcon) moonIcon.style.display = 'block';
    } else {
        if (sunIcon) sunIcon.style.display = 'block';
        if (moonIcon) moonIcon.style.display = 'none';
    }
}

// ============================================
// EVENT LISTENERS
// ============================================
function initEventListeners() {
    // Form submission
    if (els.studyForm) {
        els.studyForm.addEventListener('submit', handleSendMessage);
    }
    
    // Enter key
    if (els.studyInput) {
        els.studyInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage(e);
            }
        });
    }
    
    // File attachment
    if (els.attachBtn && els.fileInput) {
        els.attachBtn.addEventListener('click', () => els.fileInput.click());
        els.fileInput.addEventListener('change', handleFileUpload);
    }
    
    // Voice input
    if (els.voiceBtn) {
        els.voiceBtn.addEventListener('click', handleVoiceInput);
    }
    
    // Theme toggle
    if (els.themeToggle) {
        els.themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Focus mode
    if (els.focusModeToggle) {
        els.focusModeToggle.addEventListener('click', toggleFocusMode);
    }
    
    // New chat
    if (els.newChatBtn) {
        els.newChatBtn.addEventListener('click', startNewChat);
    }
    
    // Quick actions
    document.querySelectorAll('.quick-action-card').forEach(card => {
        card.addEventListener('click', (e) => {
            const action = e.currentTarget.getAttribute('data-action');
            handleQuickAction(action);
        });
    });
    
    // Example prompts
    document.querySelectorAll('.example-prompt').forEach(prompt => {
        prompt.addEventListener('click', (e) => {
            const text = e.currentTarget.getAttribute('data-prompt');
            els.studyInput.value = text;
            els.studyInput.focus();
        });
    });
    
    // Hub actions
    const uploadFileBtn = document.getElementById('uploadFileBtn');
    if (uploadFileBtn) {
        uploadFileBtn.addEventListener('click', () => els.fileInput.click());
    }
    
    const createQuizBtn = document.getElementById('createQuizBtn');
    if (createQuizBtn) {
        createQuizBtn.addEventListener('click', () => {
            els.studyInput.value = 'Create a quiz based on my recent study materials';
            handleSendMessage();
        });
    }
    
    // Upload modal
    setupUploadModal();
}

// ============================================
// MESSAGE HANDLING
// ============================================
async function handleSendMessage(e) {
    if (e) e.preventDefault();
    
    if (studyState.isGenerating) {
        console.warn('Already generating response');
        return;
    }
    
    const message = els.studyInput.value.trim();
    if (!message) return;
    
    // Hide welcome state
    if (els.welcomeState) {
        els.welcomeState.style.display = 'none';
    }
    
    // Add user message
    appendMessage(message, 'user');
    
    // Clear input
    els.studyInput.value = '';
    
    // Show loading
    const loadingId = showLoading();
    
    // Lock generation
    studyState.isGenerating = true;
    updateSendButtonState();
    
    try {
        // Send to backend
        const response = await fetch('/api/chat/study', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message
            })
        });
        
        const data = await response.json();
        
        // Remove loading
        removeLoadingById(loadingId);
        
        if (response.ok && data.reply) {
            appendMessage(data.reply, 'bot');
        } else {
            appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        removeLoadingById(loadingId);
        appendMessage('Sorry, something went wrong. Please try again.', 'bot');
    } finally {
        studyState.isGenerating = false;
        updateSendButtonState();
    }
}

function appendMessage(text, role) {
    if (!els.messagesContainer) return;
    
    const block = document.createElement('div');
    block.className = `message-block ${role}-msg`;
    
    // Add bot avatar
    if (role === 'bot') {
        const avatar = document.createElement('div');
        avatar.className = 'bot-avatar';
        avatar.textContent = '📚';
        block.appendChild(avatar);
    }
    
    const content = document.createElement('div');
    content.className = 'content';
    
    // Parse markdown for bot messages
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
    els.messagesContainer.appendChild(block);
    
    // Auto-scroll to bottom
    scrollToBottom();
}

function scrollToBottom() {
    if (!els.messagesContainer) return;
    
    requestAnimationFrame(() => {
        els.messagesContainer.scrollTop = els.messagesContainer.scrollHeight;
    });
    
    // Multiple attempts for markdown rendering
    setTimeout(() => {
        els.messagesContainer.scrollTop = els.messagesContainer.scrollHeight;
    }, 100);
}

function showLoading() {
    if (!els.messagesContainer) return null;
    
    const id = 'loading-' + Date.now();
    const block = document.createElement('div');
    block.id = id;
    block.className = 'message-block bot-msg';
    
    const avatar = document.createElement('div');
    avatar.className = 'bot-avatar';
    avatar.textContent = '📚';
    block.appendChild(avatar);
    
    const content = document.createElement('div');
    content.className = 'content';
    content.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
    block.appendChild(content);
    
    els.messagesContainer.appendChild(block);
    scrollToBottom();
    
    return id;
}

function removeLoadingById(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
}

function updateSendButtonState() {
    if (els.sendBtn) {
        els.sendBtn.disabled = studyState.isGenerating;
        els.sendBtn.style.opacity = studyState.isGenerating ? '0.5' : '1';
    }
}

// ============================================
// FILE HANDLING
// ============================================
async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    // Hide welcome
    if (els.welcomeState) {
        els.welcomeState.style.display = 'none';
    }
    
    // Add user message
    appendMessage(`📎 Uploaded: ${file.name}`, 'user');
    
    // Show loading
    const loadingId = showLoading();
    
    try {
        const response = await fetch('/api/chat/study/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        removeLoadingById(loadingId);
        
        if (response.ok && data.analysis) {
            appendMessage(data.analysis, 'bot');
        } else {
            appendMessage('File uploaded successfully! How would you like me to help with it?', 'bot');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        removeLoadingById(loadingId);
        appendMessage('Sorry, there was an error uploading the file.', 'bot');
    }
    
    // Clear file input
    e.target.value = '';
}

// ============================================
// VOICE INPUT
// ============================================
function handleVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Voice input is not supported in your browser');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    
    recognition.onstart = () => {
        els.voiceBtn.style.color = 'var(--accent-purple)';
    };
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        els.studyInput.value = transcript;
        els.studyInput.focus();
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        alert('Voice input error: ' + event.error);
    };
    
    recognition.onend = () => {
        els.voiceBtn.style.color = '';
    };
    
    recognition.start();
}

// ============================================
// FOCUS MODE
// ============================================
function toggleFocusMode() {
    studyState.focusMode = !studyState.focusMode;
    
    const toggleSwitch = document.querySelector('.toggle-switch');
    if (toggleSwitch) {
        toggleSwitch.classList.toggle('active', studyState.focusMode);
    }
    
    // Hide/show sidebars
    const leftSidebar = document.querySelector('.study-sidebar-left');
    const rightSidebar = document.querySelector('.study-sidebar-right');
    
    if (studyState.focusMode) {
        if (leftSidebar) leftSidebar.style.display = 'none';
        if (rightSidebar) rightSidebar.style.display = 'none';
        
        // Adjust input wrapper
        if (els.messagesContainer) {
            document.querySelector('.input-area-wrapper').style.left = '0';
            document.querySelector('.input-area-wrapper').style.right = '0';
        }
    } else {
        if (leftSidebar) leftSidebar.style.display = 'flex';
        if (rightSidebar) rightSidebar.style.display = 'flex';
        
        // Reset input wrapper
        document.querySelector('.input-area-wrapper').style.left = '260px';
        document.querySelector('.input-area-wrapper').style.right = '300px';
    }
}

// ============================================
// CHAT HISTORY
// ============================================
function loadChatHistory() {
    const savedChats = localStorage.getItem('aura-study-chats');
    if (savedChats) {
        studyState.chats = JSON.parse(savedChats);
        renderChatHistory();
    }
}

function renderChatHistory() {
    if (!els.historyList) return;
    
    // Keep first 3 items, clear rest
    while (els.historyList.children.length > 3) {
        els.historyList.removeChild(els.historyList.lastChild);
    }
    
    // Add recent chats
    studyState.chats.slice(0, 5).forEach(chat => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
            <span class="history-icon">📝</span>
            <span class="history-text">${chat.title}</span>
        `;
        item.addEventListener('click', () => loadChat(chat.id));
        els.historyList.appendChild(item);
    });
}

function startNewChat() {
    studyState.currentChatId = null;
    
    if (els.messagesContainer) {
        els.messagesContainer.innerHTML = '';
    }
    
    if (els.welcomeState) {
        els.welcomeState.style.display = 'block';
        els.messagesContainer.appendChild(els.welcomeState);
    }
    
    if (els.studyInput) {
        els.studyInput.value = '';
        els.studyInput.focus();
    }
}

function loadChat(chatId) {
    const chat = studyState.chats.find(c => c.id === chatId);
    if (!chat) return;
    
    studyState.currentChatId = chatId;
    
    if (els.messagesContainer) {
        els.messagesContainer.innerHTML = '';
        chat.messages.forEach(msg => {
            appendMessage(msg.text, msg.role);
        });
    }
}

// ============================================
// QUICK ACTIONS
// ============================================
function handleQuickAction(action) {
    let prompt = '';
    
    switch(action) {
        case 'summarize':
            prompt = 'Please summarize the key points from the document';
            els.fileInput.click();
            return;
        case 'flashcards':
            prompt = 'Generate flashcards from this content';
            break;
        case 'explain':
            prompt = 'Explain this concept in simple terms';
            break;
    }
    
    if (prompt) {
        els.studyInput.value = prompt;
        els.studyInput.focus();
    }
}

// ============================================
// UPLOAD MODAL
// ============================================
function setupUploadModal() {
    const modal = document.getElementById('uploadModal');
    const openBtn = document.getElementById('uploadFileBtn');
    const closeBtn = document.getElementById('closeUploadModal');
    const uploadZone = document.getElementById('uploadZone');
    const modalFileInput = document.getElementById('modalFileInput');
    
    if (openBtn && modal) {
        openBtn.addEventListener('click', () => {
            modal.style.display = 'flex';
        });
    }
    
    if (closeBtn && modal) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    if (uploadZone && modalFileInput) {
        uploadZone.addEventListener('click', () => {
            modalFileInput.click();
        });
        
        modalFileInput.addEventListener('change', (e) => {
            handleFileUpload(e);
            modal.style.display = 'none';
        });
        
        // Drag and drop
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.style.borderColor = 'var(--accent-purple)';
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.style.borderColor = '';
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.style.borderColor = '';
            
            if (e.dataTransfer.files.length > 0) {
                modalFileInput.files = e.dataTransfer.files;
                handleFileUpload({ target: modalFileInput });
                modal.style.display = 'none';
            }
        });
    }
}

// ============================================
// WELCOME STATE
// ============================================
function renderWelcome() {
    // Welcome state is in HTML, just ensure it's visible
    if (els.welcomeState && els.messagesContainer) {
        if (els.messagesContainer.children.length === 0 || 
            els.messagesContainer.children.length === 1) {
            els.welcomeState.style.display = 'block';
        }
    }
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K: Toggle theme
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleTheme();
    }
    
    // Ctrl/Cmd + F: Toggle focus mode
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        toggleFocusMode();
    }
    
    // Ctrl/Cmd + N: New chat
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        startNewChat();
    }
});

console.log('📚 AURA Study Assistant Initialized');
