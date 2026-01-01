import { createChat, addMessage, addFile, getChats, getChat, listRecentFiles } from './storage.js';

let currentChatId = null;
const els = {
  messages: null,
  form: null,
  input: null,
  file: null,
  historyList: null,
  recentFiles: null,
  newChatBtn: null,
};

function elMessage(role, text){
  const div = document.createElement('div');
  div.className = `message ${role === 'user' ? 'user' : 'aura'}`;
  
  // Parse text for file attachments (format: "FILE::{name}::{size}::{type}")
  if (text.startsWith('FILE::')) {
    const [, name, size, type] = text.split('::');
    const icon = type.includes('pdf') ? '📄' : type.includes('image') ? '🖼️' : '📎';
    const card = document.createElement('div');
    card.className = 'file-attachment-card';
    card.innerHTML = `
      <span class="file-icon">${icon}</span>
      <div style="flex:1">
        <div class="file-name">${name}</div>
        <div class="file-size">${Math.round(parseInt(size||0)/1024)} KB</div>
      </div>
    `;
    div.appendChild(card);
  } else {
    div.textContent = text;
  }
  return div;
}

function renderMessages(chat){
  els.messages.innerHTML = '';
  chat.messages.forEach(m => els.messages.appendChild(elMessage(m.role, m.text)));
  scrollToBottom();
}

function scrollToBottom(){
  setTimeout(() => { els.messages.scrollTo({ top: els.messages.scrollHeight, behavior: 'smooth' }); }, 10);
}

async function sendToBackend(promptText, file){
  const thinking = document.createElement('div');
  thinking.className = 'typing';
  thinking.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  els.messages.appendChild(thinking);
  scrollToBottom();

  try {
    const fd = new FormData();
    
    // Build conversation history for context
    const chat = getChat(currentChatId);
    const history = (chat?.messages || []).map(m => `${m.role === 'user' ? 'User' : 'AURA'}: ${m.text}`).join('\n');
    if (history) fd.append('conversation_history', history);
    
    if (promptText) fd.append('prompt', promptText);
    if (file) fd.append('file', file);

    const res = await fetch('/api/study/analyze', { method: 'POST', body: fd });
    const raw = await res.text();
    let data = {}; try { data = JSON.parse(raw); } catch { data = { raw }; }

    thinking.remove();

    if (!res.ok) {
      const msg = data.error || data.raw || `Request failed (${res.status})`;
      const reply = `❌ ${msg}`;
      addMessage(currentChatId, 'aura', reply);
      els.messages.appendChild(elMessage('aura', reply));
      scrollToBottom();
      return;
    }

    const reply = data.answer || data.raw || 'No response from AI.';
    addMessage(currentChatId, 'aura', reply);
    els.messages.appendChild(elMessage('aura', reply));
    scrollToBottom();
  } catch (err) {
    thinking.remove();
    const reply = `⚠️ Network error: ${err.message}`;
    addMessage(currentChatId, 'aura', reply);
    els.messages.appendChild(elMessage('aura', reply));
    scrollToBottom();
  }
}

function onSubmit(e){
  e.preventDefault();
  const text = els.input.value.trim();
  const file = els.file.files[0] || null;
  if (!text && !file) return;

  if (!currentChatId) { const c = createChat(text || (file ? file.name : 'New Chat'), 'study'); currentChatId = c.id; }

  if (file){
    addFile(currentChatId, { name: file.name, size: file.size, type: file.type, ts: Date.now() });
    // Render file attachment in chat
    const fileMeta = `FILE::${file.name}::${file.size}::${file.type}`;
    addMessage(currentChatId, 'user', fileMeta);
    els.messages.appendChild(elMessage('user', fileMeta));
    scrollToBottom();
  }

  if (text){
    addMessage(currentChatId, 'user', text);
    els.messages.appendChild(elMessage('user', text));
    scrollToBottom();
  }

  // Send to backend (handles both text-only, file-only, or both)
  sendToBackend(text, file);

  els.input.value = '';
  els.file.value = '';
  updateSidebar();
}

function updateSidebar(){
  // History
  const chats = getChats();
  els.historyList.innerHTML = '';
  chats.forEach(c => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="item-title">${c.title}</span><span class="item-meta">${new Date(c.createdAt).toLocaleString()}</span>`;
    li.addEventListener('click', () => loadChat(c.id));
    els.historyList.appendChild(li);
  });

  // Recent files
  const files = listRecentFiles();
  els.recentFiles.innerHTML = '';
  files.forEach(f => {
    const li = document.createElement('li');
    const sizeKb = Math.round((f.size||0)/1024);
    li.innerHTML = `
      <div class="item-row">
        <div>
          <span class="item-title">${f.name}</span>
          <span class="item-meta">${sizeKb} KB</span>
        </div>
        <button class="quick-summary" data-file-name="${f.name}" data-file-size="${f.size||0}" data-file-type="${f.type||''}">Quick Summary</button>
      </div>`;
    li.querySelector('.quick-summary').addEventListener('click', (evt) => {
      evt.stopPropagation();
      quickSummary(f);
    });
    li.addEventListener('click', () => {
      const c = createChat(f.name, 'study');
      currentChatId = c.id;
      renderMessages(c);
      updateSidebar();
    });
    els.recentFiles.appendChild(li);
  });
}

function loadChat(chatId){
  const chat = getChat(chatId);
  if (!chat) return;
  currentChatId = chat.id;
  renderMessages(chat);
}

function newChat(){
  const c = createChat('New Chat', 'study');
  currentChatId = c.id;
  renderMessages(c);
  updateSidebar();
}

function quickSummary(file){
  // Ensure there is a chat context for this file
  if (!currentChatId) {
    const c = createChat(file.name, 'study');
    currentChatId = c.id;
    renderMessages(c);
  }
  const prompt = `Summarize ${file.name} for me.`;
  addMessage(currentChatId, 'user', prompt);
  els.messages.appendChild(elMessage('user', prompt));
  scrollToBottom();
  sendToBackend(prompt, null);
}

export function initChat(){
  els.messages = document.getElementById('messages');
  els.form = document.getElementById('chat-form');
  els.input = document.getElementById('chat-input');
  els.file = document.getElementById('file-input');
  els.historyList = document.getElementById('history-list');
  els.recentFiles = document.getElementById('recent-files');
  els.newChatBtn = document.getElementById('new-chat-btn');

  els.form.addEventListener('submit', onSubmit);
  els.newChatBtn.addEventListener('click', newChat);

  updateSidebar();
}
