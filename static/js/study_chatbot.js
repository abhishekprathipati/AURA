// Study Assistant using same proven pattern as Mental Chatbot
const studyMessages = () => document.querySelector('[data-study-messages]');
const studyInput = () => document.querySelector('[data-study-input]');
const studyForm = () => document.querySelector('[data-study-form]');
const studyFile = () => document.querySelector('[data-study-file]');
const STUDY_CONV_ID_KEY = 'aura_study_conversation_id';
let studyHistory = [];

console.log('[study] v15 script loaded - initializing');

// Toast notifications for UX feedback
function showToast(msg, duration = 3000) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; 
        background: rgba(0,0,0,0.8); color: #fff; 
        padding: 12px 16px; border-radius: 6px; 
        z-index: 9999; max-width: 300px; font-size: 14px;
        animation: slideInUp 0.3s ease;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}

function getStudyConversationId() {
    let id = localStorage.getItem(STUDY_CONV_ID_KEY);
    if (!id) {
        id = 'study_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem(STUDY_CONV_ID_KEY, id);
    }
    return id;
}

function addStudyMessage(role, text) {
    const cont = studyMessages();
    if (!cont) {
        console.error('[study] messages container not found');
        return;
    }

    const msg = document.createElement('div');
    msg.classList.add('message');
    msg.classList.add(role === 'user' ? 'user-message' : 'ai-message');
    if (role !== 'user' && window.marked) {
        const html = marked.parse(text || '');
        msg.innerHTML = `<div class="bot-bubble-content">${html}</div>`;
    } else {
        msg.innerHTML = `<p>${escapeHtml(text)}</p>`;
    }
    msg.dataset.role = role;
    msg.dataset.ts = new Date().toISOString();

    cont.appendChild(msg);
    cont.scrollTop = cont.scrollHeight;
    console.log(`[study] added ${role} message`);

    // push to in-memory history (last 50 max)
    studyHistory.push({ role, text });
    if (studyHistory.length > 50) studyHistory = studyHistory.slice(-50);
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}

function showStudyTyping() {
    const cont = studyMessages();
    if (!cont) return;
    const bubble = document.createElement('div');
    bubble.className = 'message ai-message typing-indicator';
    bubble.innerHTML = `<div class="typing"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>`;
    bubble.id = 'study-typing-indicator';
    cont.appendChild(bubble);
    cont.scrollTop = cont.scrollHeight;
    console.log('[study] showing typing indicator');
}

function removeStudyTyping() {
    const typing = document.getElementById('study-typing-indicator');
    if (typing) typing.remove();
}

function updateFileInputLabel(input) {
    const fileLabel = document.getElementById('file-label');
    if (!fileLabel) return;
    if (input.files.length > 0) {
        fileLabel.innerText = `📄 ${input.files[0].name}`;
    } else {
        fileLabel.innerText = '📎 Choose File';
    }
}

async function submitStudyAnalysis(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    
    console.log('[study] form submitted');
    showToast('📤 Submitting...', 5000);

    const fileInput = studyFile();
    const textInput = studyInput();
    
    if (!fileInput || !textInput) {
        console.error('[study] input elements not found');
        showToast('❌ Form elements not found', 3000);
        return;
    }

    const file = fileInput.files[0];
    const question = textInput.value.trim();

    if (!file && !question) {
        addStudyMessage('ai', 'Please attach a PDF/image or ask a question.');
        showToast('⚠️ Please provide a file or question', 3000);
        return;
    }

    // Show user message
    if (question) addStudyMessage('user', question);
    if (file && !question) addStudyMessage('user', `📎 Analyzing: ${file.name}`);
    if (file && question) addStudyMessage('user', `❓ ${question}\n📎 File: ${file.name}`);

    // Show typing indicator
    showStudyTyping();

    // Text-only: use unified /api/chat endpoint
    if (!file && question) {
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    message: question,
                    context: studyHistory.slice(-10).map(m => ({ role: m.role, content: m.text })),
                    conversation_id: getStudyConversationId(),
                    kind: 'study'
                })
            });
            removeStudyTyping();
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            addStudyMessage('ai', data.ai_response || 'No response from AI.');
            showToast('✅ Response received', 3000);
            textInput.value = '';
            textInput.focus();
            return;
        } catch (err) {
            removeStudyTyping();
            console.error('[study] text-only error', err);
            addStudyMessage('ai', `⚠️ Error: ${err.message}`);
            showToast(`⚠️ Network error: ${err.message}`, 5000);
            return;
        }
    }

    // File upload: use specialized /api/study/analyze endpoint
    // Build FormData
    const form = new FormData();
    if (file) form.append('file', file);
    if (question) form.append('prompt', question);
    // Attach memory + metadata
    form.append('conversation_history', JSON.stringify(studyHistory.slice(-10).map(m => ({ role: m.role, content: m.text }))));
    form.append('conversation_id', getStudyConversationId());

    console.log('[study] sending to backend', {
        hasFile: !!file,
        fileName: file?.name,
        questionLength: question.length,
    });

    try {
        const res = await fetch('/api/study/analyze', {
            method: 'POST',
            credentials: 'include',
            body: form,
        });

        removeStudyTyping();

        const text = await res.text();
        let data = {};
        try { data = JSON.parse(text); } catch (e) { data = { raw: text }; }

        console.log('[study] backend response', { status: res.status, data });

        if (!res.ok) {
            const msg = data.error || data.raw || `Request failed (status ${res.status}).`;
            const dbg = data.debug ? ` | Debug: ${JSON.stringify(data.debug)}` : '';
            addStudyMessage('ai', `❌ ${msg}${dbg}`);
            showToast(`❌ Error: ${msg}`, 5000);
            return;
        }

        // Success - show AI response (Markdown rendered if available)
        addStudyMessage('ai', data.answer || data.error || data.raw || 'No response from AI.');
        showToast('✅ Response received', 3000);

        // Clear inputs
        textInput.value = '';
        fileInput.value = '';
        document.getElementById('file-label').innerText = '📎 Choose File';
        textInput.focus();
    } catch (err) {
        removeStudyTyping();
        console.error('[study] fetch error', err);
        addStudyMessage('ai', `⚠️ Error: ${err.message}`);
        showToast(`⚠️ Network error: ${err.message}`, 5000);
    }
}


// Setup event listeners on DOM ready
window.addEventListener('DOMContentLoaded', () => {
    console.log('[study] DOM ready - wiring listeners');

    // Wire form submission
    const form = studyForm();
    if (form) {
        console.log('[study] ✅ found form, attaching submit listener');
        form.addEventListener('submit', submitStudyAnalysis);
    } else {
        console.error('[study] ❌ form not found');
    }

    // Defensive: ensure Analyze button triggers submission even if browser validation blocks
    const analyzeBtn = document.querySelector('[data-study-analyze]') || document.getElementById('study-analyze-btn');
    if (analyzeBtn && form) {
        analyzeBtn.addEventListener('click', (e) => {
            // Prevent any default native validation popup; we handle validation in JS
            e.preventDefault();
            submitStudyAnalysis(e);
        });
        console.log('[study] ✅ analyze button wired');
    }

    // Wire file input change
    const fileInput = studyFile();
    if (fileInput) {
        console.log('[study] ✅ found file input, attaching change listener');
        fileInput.addEventListener('change', (e) => updateFileInputLabel(e.target));
    } else {
        console.error('[study] ❌ file input not found');
    }

    // Focus text input
    const textInput = studyInput();
    if (textInput) textInput.focus();

    console.log('[study] ✅ all listeners wired - ready!');
});
