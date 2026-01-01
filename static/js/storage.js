// LocalStorage utilities for AURA chat
const LS_CHATS = 'aura_chats';
const LS_RECENT_FILES = 'aura_recent_files';

function uid() { return 'c_' + Math.random().toString(36).slice(2) + Date.now().toString(36); }

export function getChats() {
  const raw = localStorage.getItem(LS_CHATS);
  const parsed = raw ? JSON.parse(raw) : [];
  // Backfill kind for legacy entries
  return parsed.map((c) => ({ kind: 'study', ...c }));
}
export function saveChats(chats){ localStorage.setItem(LS_CHATS, JSON.stringify(chats)); }

export function createChat(title = 'Untitled Chat', kind = 'study'){
  const chat = { id: uid(), title, kind, messages: [], files: [], createdAt: Date.now() };
  const chats = getChats(); chats.unshift(chat); saveChats(chats); return chat;
}

export function addMessage(chatId, role, text){
  const chats = getChats();
  const chat = chats.find(c => c.id === chatId);
  if (!chat) return;
  chat.messages.push({ role, text, ts: Date.now() });
  saveChats(chats);
}

export function addFile(chatId, fileMeta){
  const chats = getChats();
  const chat = chats.find(c => c.id === chatId);
  if (!chat) return;
  chat.files.push(fileMeta);
  saveChats(chats);
  const rf = listRecentFiles(); rf.unshift(fileMeta); localStorage.setItem(LS_RECENT_FILES, JSON.stringify(rf.slice(0,50)));
}

export function getChat(chatId){ return getChats().find(c => c.id === chatId); }
export function listChatsByKind(kind){ return getChats().filter(c => c.kind === kind); }
export function listRecentFiles(){ const raw = localStorage.getItem(LS_RECENT_FILES); return raw ? JSON.parse(raw) : []; }
