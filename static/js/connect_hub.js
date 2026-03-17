/**
 * Connect Hub v4.0 — Structural UX Engine
 * ════════════════════════════════════════════
 * SPA pushState routing · Dynamic context headers
 * Per-section layouts  · Rich empty states
 * WebSocket real-time  · View lifecycle management
 */
;(function () {
    'use strict';

    /* ═══════════════════════════════════════════════════════════════
       CONFIG
       ═══════════════════════════════════════════════════════════════ */
    const CFG = {
        BASE:             '/student/hub',
        STAT_INTERVAL:    30000,
        TYPING_DEBOUNCE:  2000,
        SEARCH_DEBOUNCE:  300,
        SKELETON_N:       5,
        FALLBACK_POLL:    6000,
    };

    /* ═══════════════════════════════════════════════════════════════
       ROUTE → VIEW MAP (defines the information architecture)
       ═══════════════════════════════════════════════════════════════ */
    const VIEWS = {
        welcome:        { view: 'viewWelcome',        icon: '🤝', title: 'Welcome',          subtitle: 'Your community hub',         tab: null },
        peers:          { view: 'viewPeers',          icon: '👥', title: 'Peer Network',      subtitle: 'Your connections',            tab: 'peers' },
        groups:         { view: 'viewGroups',         icon: '🧑‍🤝‍🧑', title: 'Study Groups',     subtitle: 'Collaborate & connect',       tab: 'groups' },
        events:         { view: 'viewEvents',         icon: '📅', title: 'Upcoming Events',   subtitle: 'Workshops, webinars & more',  tab: 'events' },
        resources:      { view: 'viewResources',      icon: '📚', title: 'Shared Knowledge',  subtitle: 'Community resources',         tab: 'resources' },
        feed:           { view: 'viewFeed',           icon: '🌊', title: 'Activity Feed',     subtitle: 'What\'s happening',           tab: 'feed' },
        dm:             { view: 'viewDM',             icon: '💬', title: 'Chat',              subtitle: '',                            tab: 'peers',    back: true },
        groupchat:      { view: 'viewGroupChat',      icon: '💬', title: 'Group Chat',        subtitle: '',                            tab: 'groups',   back: true },
        eventdetail:    { view: 'viewEventDetail',    icon: '📅', title: 'Event',             subtitle: '',                            tab: 'events',   back: true },
        resourcedetail: { view: 'viewResourceDetail', icon: '📄', title: 'Resource',          subtitle: '',                            tab: 'resources',back: true },
        notifications:  { view: 'viewNotifications',  icon: '🔔', title: 'Notifications',     subtitle: 'Stay in the loop',            tab: null,       back: true },
    };

    /* ═══════════════════════════════════════════════════════════════
       STATE
       ═══════════════════════════════════════════════════════════════ */
    const S = {
        user:      { email: '', name: '', department: '' },
        route:     'welcome',
        prevRoute: null,
        dmPeer:    null,
        groupChat: null,
        peers: [], groups: [], events: [], resources: [], feed: [],
        suggestions: [],
        suggestionFilter: 'all',
        notifications: [], stats: {},
        socket:    null,
        timers:    { stat: null, chat: null, typing: null },
        _ready:    false,
        _loaded:   { peers: false, groups: false, events: false, resources: false, feed: false },
    };

    /* ═══════════════════════════════════════════════════════════════
       DOM HELPERS
       ═══════════════════════════════════════════════════════════════ */
    const $  = (s, c) => (c || document).querySelector(s);
    const $$ = (s, c) => [...(c || document).querySelectorAll(s)];
    const el = id => document.getElementById(id);
    function bind(id, evt, fn) { const e = el(id); if (e) e.addEventListener(evt, fn); }

    function isMobileViewport() {
        return window.innerWidth <= 1280;
    }

    function syncResponsiveLayout() {
        const body = document.body;
        if (!body) return;

        const compact = isMobileViewport();
        body.classList.toggle('compact-layout', compact);
        body.classList.toggle('compact-xs', window.innerWidth <= 640);

        if (!compact) {
            closeSidebar();
        }
    }

    function openSidebar() {
        const sidebar = el('hubSidebar');
        const toggle = el('mobileSidebarToggle');
        if (!sidebar || !isMobileViewport()) return;
        sidebar.classList.add('open');
        document.body.classList.add('sidebar-open');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
    }

    function closeSidebar() {
        const sidebar = el('hubSidebar');
        const toggle = el('mobileSidebarToggle');
        if (!sidebar) return;
        sidebar.classList.remove('open');
        document.body.classList.remove('sidebar-open');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
    }

    const _escEl = document.createElement('div');
    function esc(s) {
        if (!s) return '';
        _escEl.textContent = String(s);
        return _escEl.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function _parseUTC(iso) {
        if (!iso) return null;
        // Append Z if no timezone info so browsers always parse as UTC
        return new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z');
    }

    function timeAgo(iso) {
        const date = _parseUTC(iso);
        if (!date) return '';
        const sec = Math.floor((Date.now() - date.getTime()) / 1000);
        if (sec < 0)      return 'just now';
        if (sec < 60)     return 'just now';
        if (sec < 3600)   return Math.floor(sec / 60) + 'm ago';
        if (sec < 86400)  return Math.floor(sec / 3600) + 'h ago';
        if (sec < 172800) return 'Yesterday';
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }

    // For chat bubbles: shows clock time today, "Yesterday HH:MM", or "11 Mar HH:MM"
    function msgTimeFmt(iso) {
        const date = _parseUTC(iso);
        if (!date) return '';
        const timePart = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
        const today     = new Date();
        const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
        if (date.toDateString() === today.toDateString())     return timePart;
        if (date.toDateString() === yesterday.toDateString()) return 'Yesterday ' + timePart;
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' ' + timePart;
    }

    function dateFmt(iso) {
        const date = _parseUTC(iso);
        if (!date) return '';
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }
    function setTxt(id, v) { const e = el(id); if (e) e.textContent = v; }
    function val(id)  { const e = el(id); return e ? e.value.trim() : ''; }
    function clr(id)  { const e = el(id); if (e) e.value = ''; }

    function skeleton(n = CFG.SKELETON_N) {
        return Array(n).fill('').map(() =>
            `<div class="skeleton-item"><div class="skeleton-avatar"></div><div class="skeleton-lines"><div class="skeleton-line w70"></div><div class="skeleton-line w50"></div></div></div>`
        ).join('');
    }

    let _toastT = 0;
    function toast(msg, type = 'info') {
        const t = el('hubToast'); if (!t) return;
        t.textContent = msg; t.className = 'hub-toast show ' + type;
        clearTimeout(_toastT); _toastT = setTimeout(() => { t.className = 'hub-toast'; }, 3500);
    }

    /* ═══════════════════════════════════════════════════════════════
       NOTIFICATION SOUND (subtle audio feedback)
       ═══════════════════════════════════════════════════════════════ */
    let audioContext = null;
    function playNotificationSound() {
        try {
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            // Silently fail if Web Audio API is not supported
        }
    }

    /* ═══════════════════════════════════════════════════════════════
       API LAYER
       ═══════════════════════════════════════════════════════════════ */
    async function api(path, opts = {}) {
        const url = '/student' + path;
        const init = { method: opts.method || 'GET', credentials: 'same-origin' };
        if (opts.body) { init.headers = { 'Content-Type': 'application/json' }; init.body = JSON.stringify(opts.body); }
        const res = await fetch(url, init);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        return data;
    }

    /* ═══════════════════════════════════════════════════════════════
       SPA ROUTER (pushState)
       ═══════════════════════════════════════════════════════════════ */
    function navigate(route, opts = {}) {
        if (!VIEWS[route]) route = 'welcome';
        const cfg = VIEWS[route];

        // ── Leave previous view cleanup ──
        if (S.route === 'dm' || S.route === 'groupchat') stopChatPolling();
        if (S.route === 'groupchat' && S.groupChat && S.socket) {
            S.socket.emit('leave_group_room', { group_id: S.groupChat.group_id });
        }

        S.prevRoute = S.route;
        S.route = route;

        // ── URL update ──
        if (!opts.silent) {
            const slug = route === 'welcome' ? '' : '/' + route;
            const url = CFG.BASE + slug;
            if (window.location.pathname !== url) {
                history.pushState({ route }, '', url);
            }
        }

        // ── Update document title ──
        document.title = cfg.title + ' — Connect Hub — AURA';

        // ── Update context header ──
        setTxt('contextIcon', cfg.icon);
        setTxt('contextTitle', cfg.title);
        setTxt('contextSubtitle', cfg.subtitle);
        const backBtn = el('contextBack');
        if (backBtn) backBtn.style.display = cfg.back ? '' : 'none';

        // ── Update context actions ──
        const actBox = el('contextActions');
        if (actBox) actBox.innerHTML = getContextActions(route);
        bindContextActions(route);

        // ── Set hub-main data attribute for CSS scoping ──
        const main = el('hubMain');
        if (main) main.dataset.activeView = route;

        // ── Switch active view ──
        $$('.hub-view').forEach(v => {
            const isActive = v.id === cfg.view;
            v.classList.toggle('active', isActive);
        });

        // ── Sync sidebar tab ──
        if (cfg.tab) {
            $$('.nav-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === cfg.tab));
            $$('.sidebar-panel').forEach(p => p.classList.toggle('active', p.dataset.panel === cfg.tab));
        }

        // ── Load data for the view ──
        enterView(route);
    }

    function getContextActions(route) {
        switch (route) {
            case 'groupchat':
                return `<button class="icon-btn context-action" id="ctxGroupMembers" title="Members">👥</button>`;
            default:
                return '';
        }
    }

    function bindContextActions(route) {
        if (route === 'groupchat') {
            bind('ctxGroupMembers', 'click', openGroupMembers);
        }
    }

    function goBack() {
        const cfg = VIEWS[S.route];
        if (cfg && cfg.tab) navigate(cfg.tab);
        else navigate('welcome');
    }

    // Browser back/forward
    window.addEventListener('popstate', (e) => {
        const route = e.state?.route || parseRoute();
        navigate(route, { silent: true });
    });

    function parseRoute() {
        const path = window.location.pathname;
        const after = path.replace(CFG.BASE, '').replace(/^\//, '');
        if (!after || after === '/') return 'welcome';
        const seg = after.split('/')[0];
        return VIEWS[seg] ? seg : 'welcome';
    }

    /* ═══════════════════════════════════════════════════════════════
       VIEW LIFECYCLE — enterView
       Each route triggers specific data load + main content render
       ═══════════════════════════════════════════════════════════════ */
    function enterView(route) {
        switch (route) {
            case 'peers':     loadPeers(); renderPeersMain(); break;
            case 'groups':    loadGroups(); renderGroupsMain(); break;
            case 'events':    loadEvents(); renderEventsMain(); break;
            case 'resources': loadResources(); renderResourcesMain(); break;
            case 'feed':      loadFeed(); renderFeedMain(); break;
            case 'notifications': renderNotifications(); break;
            case 'welcome':   loadFeed(); break;
            // dm, groupchat, eventdetail, resourcedetail are entered by specific functions
        }
    }

    /* ═══════════════════════════════════════════════════════════════
       SOCKET.IO
       ═══════════════════════════════════════════════════════════════ */
    function initSocket() {
        if (typeof io === 'undefined') { startFallbackPolling(); return; }
        try {
            S.socket = io({ transports: ['websocket', 'polling'] });
            S.socket.on('connect', () => console.log('[Hub] Socket connected'));
            S.socket.on('disconnect', () => { console.log('[Hub] Socket disconnected'); startFallbackPolling(); });

            S.socket.on('new_dm', (data) => {
                if (S.route === 'dm' && S.dmPeer && (data.from === S.dmPeer.email || data.to === S.dmPeer.email)) {
                    appendChatBubble('dmMessages', data);
                    if (!data.mine) {
                        S.socket.emit('mark_dm_read', { peer: data.from });
                        playNotificationSound();
                    }
                }
                loadPeers(); loadNotifications();
            });

            S.socket.on('new_group_msg', (data) => {
                if (S.route === 'groupchat' && S.groupChat && data.group_id === S.groupChat.group_id) {
                    appendChatBubble('groupMessages', { ...data, mine: data.sender === S.user.email });
                    if (!data.mine) playNotificationSound();
                }
            });

            S.socket.on('typing_indicator', (data) => {
                if (data.type === 'dm' && S.route === 'dm' && S.dmPeer && data.from === S.dmPeer.email) showTyping('dm', data.name);
                else if (data.type === 'group' && S.route === 'groupchat' && S.groupChat && data.group_id === S.groupChat.group_id) showTyping('group', data.name);
            });

            S.socket.on('online_update', (data) => {
                const peer = S.peers.find(p => p.email === data.email);
                if (peer) { peer.online = data.online; renderPeersSidebar(); }
                if (S.dmPeer && S.dmPeer.email === data.email) {
                    S.dmPeer.online = data.online;
                    setTxt('contextSubtitle', data.online ? '🟢 online' : '⚫ offline');
                }
            });

            S.socket.on('read_receipt', (data) => {
                if (S.route === 'dm' && S.dmPeer && data.from === S.dmPeer.email) {
                    $$('.chat-bubble.mine .bubble-time', el('dmMessages')).forEach(t => {
                        if (!t.textContent.includes('✓✓')) t.textContent = t.textContent.replace(' ✓', '') + ' ✓✓';
                    });
                }
            });

            S.socket.on('dm_error', (d) => toast(d.error, 'error'));
            S.socket.on('group_error', (d) => toast(d.error, 'error'));
            S.socket.on('new_notification', () => { 
                loadNotifications(); 
                playNotificationSound();
            });
        } catch (e) { startFallbackPolling(); }
    }

    function startFallbackPolling() {
        if (S.timers.chat) return;
        S.timers.chat = setInterval(() => {
            if (S.route === 'dm' && S.dmPeer) fetchDMHttp();
            if (S.route === 'groupchat' && S.groupChat) fetchGroupHttp();
        }, CFG.FALLBACK_POLL);
    }
    function stopChatPolling() { clearInterval(S.timers.chat); S.timers.chat = null; }

    let _typingHideTimer = {};
    function showTyping(type, name) {
        const tid = type === 'dm' ? 'dmTyping' : 'groupTyping';
        const nid = type === 'dm' ? 'dmTypingName' : 'groupTypingName';
        const t = el(tid); const n = el(nid);
        if (t) t.style.display = 'flex';
        if (n) n.textContent = name;
        clearTimeout(_typingHideTimer[type]);
        _typingHideTimer[type] = setTimeout(() => { if (t) t.style.display = 'none'; }, 3000);
    }
    function emitTyping(target, type) {
        if (!S.socket || !S.socket.connected) return;
        clearTimeout(S.timers.typing);
        S.socket.emit('typing', { target, type });
        S.timers.typing = setTimeout(() => {
            if (S.socket && S.socket.connected) S.socket.emit('stop_typing', { target, type });
        }, CFG.TYPING_DEBOUNCE);
    }

    /* ═══════════════════════════════════════════════════════════════
       TAB SWITCHING (sidebar click → navigate)
       ═══════════════════════════════════════════════════════════════ */
    function switchTab(tab) {
        navigate(tab);      // tab names match route names
        const loaders = { peers: loadPeers, groups: loadGroups, events: loadEvents, resources: loadResources, feed: loadFeed };
        if (loaders[tab]) loaders[tab]();
    }

    /* ═══════════════════════════════════════════════════════════════
       PEERS — sidebar list + main content
       ═══════════════════════════════════════════════════════════════ */
    async function loadPeers() {
        const box = el('peerList');
        if (box && !S.peers.length) box.innerHTML = skeleton();
        try { const d = await api('/api/connect/peers'); S.peers = d.peers || []; } catch (_) {}
        S._loaded.peers = true;
        renderPeersSidebar();
        if (S.route === 'peers') renderPeersMain();
    }

    function renderPeersSidebar(filter) {
        const box = el('peerList'); if (!box) return;
        let list = S.peers;
        if (filter) {
            const q = (typeof filter === 'string' ? filter : (el('peerSearch')?.value || '')).toLowerCase();
            if (q) list = list.filter(p => (p.name || '').toLowerCase().includes(q) || (p.email || '').toLowerCase().includes(q));
        }
        if (!list.length) {
            box.innerHTML = `<div class="empty-state"><div class="empty-icon">🌱</div>
                <p>${filter ? 'No matches' : 'Your network starts here!'}</p>
                ${!filter ? '<button class="btn btn-sm btn-primary" data-action="find-peers">Find People</button>' : ''}</div>`;
            const b = $('[data-action="find-peers"]', box);
            if (b) b.onclick = openSuggestions;
            return;
        }
        box.innerHTML = list.map(p => `
            <div class="contact-item ${p.online ? 'online' : ''} ${S.dmPeer && S.dmPeer.email === p.email ? 'selected' : ''}" data-peer="${esc(p.email)}">
                <div class="contact-avatar">${esc((p.name || '?')[0].toUpperCase())}</div>
                <div class="contact-info">
                    <div class="contact-name">${esc(p.name)}${p.unread ? `<span class="unread-badge">${p.unread}</span>` : ''}</div>
                    <div class="contact-meta">${esc(p.department || 'Student')} · ${esc(p.stress_level)}</div>
                </div>
                <div class="contact-status ${p.online ? 'online' : 'offline'}"></div>
            </div>`).join('');
        $$('.contact-item[data-peer]', box).forEach(item => {
            item.onclick = () => openDM(item.dataset.peer);
        });
    }

    function renderPeersMain() {
        const box = el('peersMainContent'); if (!box) return;
        if (!S._loaded.peers) { box.innerHTML = `<div class="view-loading">${skeleton(6)}</div>`; return; }
        if (!S.peers.length) {
            box.innerHTML = `<div class="view-empty">
                <div class="empty-icon-lg">👥</div>
                <h3>Build Your Network</h3>
                <p>Connect with peers who share your interests and stress levels. AURA's AI matches you with the most compatible peers.</p>
                <button class="btn btn-glow" data-action="find-peers-main">✨ Find Suggested Peers</button>
            </div>`;
            const b = $('[data-action="find-peers-main"]', box);
            if (b) b.onclick = openSuggestions;
            return;
        }
        // Rich peer cards in main area
        const online = S.peers.filter(p => p.online);
        const offline = S.peers.filter(p => !p.online);
        box.innerHTML = `
            ${online.length ? `<div class="section-block"><h4 class="section-heading"><span class="pulse-dot"></span> Online Now (${online.length})</h4>
                <div class="card-grid">${online.map(p => peerCard(p)).join('')}</div></div>` : ''}
            ${offline.length ? `<div class="section-block"><h4 class="section-heading">All Peers (${offline.length})</h4>
                <div class="card-grid">${offline.map(p => peerCard(p)).join('')}</div></div>` : ''}
            <div class="section-block"><button class="btn btn-glass btn-block" data-action="find-more">✨ Find More Peers</button></div>`;
        $$('[data-peer-card]', box).forEach(c => { c.onclick = () => openPeerProfile(c.dataset.peerCard); });
        $$('.peer-profile-btn', box).forEach(btn => { btn.onclick = (e) => { e.stopPropagation(); openPeerProfile(btn.dataset.profile); }; });
        $$('.peer-dm-btn', box).forEach(btn => { btn.onclick = (e) => { e.stopPropagation(); openDM(btn.dataset.dm); }; });
        const fm = $('[data-action="find-more"]', box);
        if (fm) fm.onclick = openSuggestions;
    }

    function _stressClass(level) {
        if (!level) return 'low';
        const l = level.toLowerCase();
        if (l === 'critical' || l === 'high') return 'high';
        if (l === 'elevated') return 'medium';
        return 'low';
    }

    function peerCard(p) {
        const sc = _stressClass(p.stress_level);
        return `<div class="peer-card ${p.online ? 'is-online' : ''}" data-peer-card="${esc(p.email)}">
            <div class="peer-card-avatar">${p.online ? '<div class="online-ring"></div>' : ''}${esc((p.name || '?')[0].toUpperCase())}</div>
            <div class="peer-card-name">${esc(p.name)}</div>
            <div class="peer-card-dept">${esc(p.department || 'Student')}</div>
            <div class="peer-card-stress-wrap">
                <div class="stress-bar-wrap"><div class="stress-bar-fill ${sc}" style="width:${sc==='high'?85:sc==='medium'?55:30}%"></div></div>
                <span style="font-size:10px;color:var(--h-muted)">${esc(p.stress_level || 'Relaxed')}</span>
            </div>
            ${p.unread ? `<span class="unread-badge card-badge">${p.unread}</span>` : ''}
            <div class="peer-card-actions">
                <button class="btn btn-xs btn-glass peer-profile-btn" data-profile="${esc(p.email)}">👤 Profile</button>
                <button class="btn btn-xs btn-primary peer-dm-btn" data-dm="${esc(p.email)}">💬 Chat</button>
            </div>
        </div>`;
    }

    function openPeerProfile(email) {
        const peer = S.peers.find(p => p.email === email);
        if (!peer) return;
        
        openModal('peerProfileModal');
        el('profileAvatar').textContent = (peer.name || '?')[0].toUpperCase();
        setTxt('profileName', peer.name);
        setTxt('profileDept', peer.department || 'Student');
        setTxt('profileStress', peer.stress_level);
        
        const statusEl = el('profileStatus');
        if (statusEl) {
            if (peer.online) {
                statusEl.textContent = '🟢 Online';
                statusEl.style.color = 'var(--hub-success)';
            } else {
                statusEl.textContent = '⚫ Offline';
                statusEl.style.color = 'var(--hub-text-muted)';
            }
        }
        
        const chatBtn = el('profileChatBtn');
        if (chatBtn) {
            chatBtn.onclick = () => {
                closeModal('peerProfileModal');
                openDM(email);
            };
        }
    }

    /* ═══════════════════════════════════════════════════════════════
       DM CHAT
       ═══════════════════════════════════════════════════════════════ */
    async function openDM(email) {
        const peer = S.peers.find(p => p.email === email);
        S.dmPeer = { email, name: peer ? peer.name : email.split('@')[0], online: peer ? peer.online : false };

        // Update context header dynamically
        navigate('dm');
        setTxt('contextTitle', S.dmPeer.name);
        setTxt('contextSubtitle', S.dmPeer.online ? '🟢 online' : '⚫ offline');
        setTxt('contextIcon', (S.dmPeer.name || '?')[0].toUpperCase());

        // Highlight in sidebar
        renderPeersSidebar();

        el('dmInput')?.focus();
        await fetchDMHttp();
        if (S.socket && S.socket.connected) S.socket.emit('mark_dm_read', { peer: email });
        else { stopChatPolling(); S.timers.chat = setInterval(fetchDMHttp, CFG.FALLBACK_POLL); }
    }

    async function fetchDMHttp() {
        if (!S.dmPeer) return;
        try { const d = await api('/api/chat/dm/' + encodeURIComponent(S.dmPeer.email)); renderChatMessages('dmMessages', d.messages || []); }
        catch (e) { if (/403|Not connected/.test(String(e))) { stopChatPolling(); toast('Connection removed', 'error'); S.dmPeer = null; navigate('peers'); } }
    }

    function sendDM() {
        const input = el('dmInput'); if (!input) return;
        const text = input.value.trim(); if (!text || !S.dmPeer) return;
        input.value = '';
        if (S.socket && S.socket.connected) S.socket.emit('send_dm', { to: S.dmPeer.email, message: text });
        else api('/api/chat/dm/' + encodeURIComponent(S.dmPeer.email) + '/send', { method: 'POST', body: { message: text } }).then(() => fetchDMHttp()).catch(e => { toast(e.message, 'error'); input.value = text; });
    }

    /* ═══════════════════════════════════════════════════════════════
       GROUPS — sidebar + main
       ═══════════════════════════════════════════════════════════════ */
    async function loadGroups() {
        const box = el('groupList');
        if (box && !S.groups.length) box.innerHTML = skeleton();
        const ft = el('groupFilter'); const type = ft ? ft.value : '';
        try { const d = await api('/api/groups' + (type ? '?type=' + type : '')); S.groups = d.groups || []; } catch (_) {}
        S._loaded.groups = true;
        renderGroupsSidebar();
        if (S.route === 'groups') renderGroupsMain();
    }

    function renderGroupsSidebar() {
        const box = el('groupList'); if (!box) return;
        if (!S.groups.length) {
            box.innerHTML = `<div class="empty-state"><div class="empty-icon">🏠</div><p>No groups yet</p>
                <button class="btn btn-sm btn-primary" data-action="create-group">Create Group</button></div>`;
            const b = $('[data-action="create-group"]', box); if (b) b.onclick = () => openModal('createGroupModal');
            return;
        }
        const icons = { study: '📖', relaxation: '🧘', peer_support: '🤝' };
        box.innerHTML = S.groups.map(g => `
            <div class="contact-item group-item ${S.groupChat && S.groupChat.group_id === g.group_id ? 'selected' : ''}" data-gid="${esc(g.group_id)}">
                <div class="contact-avatar group-av">${icons[g.type] || '💬'}</div>
                <div class="contact-info">
                    <div class="contact-name">${esc(g.name)}</div>
                    <div class="contact-meta">${g.member_count}/20 · ${g.last_message ? esc(g.last_message.substring(0, 30)) + '…' : esc(g.type)}</div>
                </div>
                ${g.is_member ? '<button class="btn btn-xs btn-accent grp-chat-btn">💬</button>' : '<button class="btn btn-xs btn-primary grp-join-btn">Join</button>'}
            </div>`).join('');
        $$('.grp-join-btn', box).forEach(btn => { btn.onclick = async (e) => { e.stopPropagation(); const gid = btn.closest('.group-item').dataset.gid;
            try { await api('/api/groups/join', { method: 'POST', body: { group_id: gid } }); toast('Joined!', 'success'); loadGroups(); loadStats(); } catch (err) { toast(err.message, 'error'); } }; });
        $$('.grp-chat-btn', box).forEach(btn => { btn.onclick = (e) => { e.stopPropagation(); const g = S.groups.find(x => x.group_id === btn.closest('.group-item').dataset.gid); if (g) openGroupChat(g); }; });
        $$('.group-item', box).forEach(item => { item.onclick = () => { const g = S.groups.find(x => x.group_id === item.dataset.gid); if (g && g.is_member) openGroupChat(g); }; });
    }

    function renderGroupsMain() {
        const box = el('groupsMainContent'); if (!box) return;
        if (!S._loaded.groups) { box.innerHTML = `<div class="view-loading">${skeleton(6)}</div>`; return; }
        if (!S.groups.length) {
            box.innerHTML = `<div class="view-empty">
                <div class="empty-icon-lg">💬</div><h3>No Groups Yet</h3>
                <p>Create or join study, relaxation, or peer support groups to collaborate with others.</p>
                <button class="btn btn-glow" data-action="create-grp-main">➕ Create a Group</button></div>`;
            const b = $('[data-action="create-grp-main"]', box); if (b) b.onclick = () => openModal('createGroupModal');
            return;
        }
        const icons = { study: '📖', relaxation: '🧘', peer_support: '🤝' };
        const mine = S.groups.filter(g => g.is_member);
        const discover = S.groups.filter(g => !g.is_member);
        box.innerHTML = `
            ${mine.length ? `<div class="section-block"><h4 class="section-heading">Your Groups (${mine.length})</h4>
                <div class="card-grid">${mine.map(g => groupCard(g, icons)).join('')}</div></div>` : ''}
            ${discover.length ? `<div class="section-block"><h4 class="section-heading">Discover</h4>
                <div class="card-grid">${discover.map(g => groupCard(g, icons)).join('')}</div></div>` : ''}`;
        $$('[data-group-card]', box).forEach(c => { const g = S.groups.find(x => x.group_id === c.dataset.groupCard); if (g) c.onclick = () => g.is_member ? openGroupChat(g) : joinGroup(g.group_id); });
    }

    function groupCard(g, icons) {
        return `<div class="group-card" data-group-card="${esc(g.group_id)}">
            <div class="group-card-icon">${icons[g.type] || '💬'}</div>
            <div class="group-card-name">${esc(g.name)}</div>
            <div class="group-card-meta">${g.member_count}/20 members · ${esc(g.type)}</div>
            <div class="group-card-action">${g.is_member ? '<span class="badge badge-success">Member ✓</span>' : '<span class="badge badge-join">Join →</span>'}</div>
        </div>`;
    }

    async function joinGroup(gid) {
        try { await api('/api/groups/join', { method: 'POST', body: { group_id: gid } }); toast('Joined!', 'success'); loadGroups(); loadStats(); } catch (e) { toast(e.message, 'error'); }
    }

    /* ═══════════════════════════════════════════════════════════════
       GROUP CHAT
       ═══════════════════════════════════════════════════════════════ */
    async function openGroupChat(group) {
        S.groupChat = { group_id: group.group_id, name: group.name, member_count: group.member_count, type: group.type };
        navigate('groupchat');
        setTxt('contextTitle', group.name);
        setTxt('contextSubtitle', (group.member_count || 0) + ' members');
        const icons = { study: '📖', relaxation: '🧘', peer_support: '🤝' };
        setTxt('contextIcon', icons[group.type] || '💬');
        renderGroupsSidebar();
        el('groupChatInput')?.focus();
        if (S.socket && S.socket.connected) S.socket.emit('join_group_room', { group_id: group.group_id });
        await fetchGroupHttp();
        if (!S.socket || !S.socket.connected) { stopChatPolling(); S.timers.chat = setInterval(fetchGroupHttp, CFG.FALLBACK_POLL); }
    }

    async function fetchGroupHttp() {
        if (!S.groupChat) return;
        try { const d = await api('/api/chat/group/' + S.groupChat.group_id); renderChatMessages('groupMessages', d.messages || []); }
        catch (e) { if (/403|Not a member/.test(String(e))) { stopChatPolling(); toast('Removed from group', 'error'); S.groupChat = null; navigate('groups'); } }
    }

    function sendGroupMsg() {
        const input = el('groupChatInput'); if (!input) return;
        const text = input.value.trim(); if (!text || !S.groupChat) return;
        input.value = '';
        if (S.socket && S.socket.connected) S.socket.emit('send_group_msg', { group_id: S.groupChat.group_id, message: text });
        else api('/api/chat/group/' + S.groupChat.group_id + '/send', { method: 'POST', body: { message: text } }).then(() => fetchGroupHttp()).catch(e => { toast(e.message, 'error'); input.value = text; });
    }

    async function openGroupMembers() {
        if (!S.groupChat) return;
        openModal('groupMembersModal');
        try {
            const d = await api('/api/groups/' + S.groupChat.group_id + '/members');
            const box = el('memberList'); const mems = d.members || [];
            if (box) box.innerHTML = mems.length ? mems.map(m => `<div class="member-item"><div class="contact-avatar">${esc((m.name || '?')[0].toUpperCase())}</div><span class="member-name">${esc(m.name)}</span><span class="contact-status ${m.online ? 'online' : 'offline'}"></span></div>`).join('') : '<p class="muted">No members</p>';
        } catch (_) {}
    }

    /* ═══════════════════════════════════════════════════════════════
       CHAT RENDERER
       ═══════════════════════════════════════════════════════════════ */
    function renderChatMessages(containerId, msgs) {
        const box = el(containerId); if (!box) return;
        const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
        if (!msgs.length) { box.innerHTML = '<div class="chat-empty"><div class="empty-icon">💬</div><p>Start the conversation!</p></div>'; return; }
        box.innerHTML = msgs.map(m => chatBubbleHtml(m)).join('');
        if (atBottom) box.scrollTop = box.scrollHeight;
    }
    function appendChatBubble(containerId, msg) {
        const box = el(containerId); if (!box) return;
        const empty = $('.chat-empty', box); if (empty) empty.remove();
        const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
        box.insertAdjacentHTML('beforeend', chatBubbleHtml(msg));
        if (atBottom) box.scrollTop = box.scrollHeight;
    }
    function chatBubbleHtml(m) {
        return `<div class="chat-bubble ${m.mine ? 'mine' : 'theirs'}">
            ${!m.mine && m.sender_name ? `<div class="bubble-sender">${esc(m.sender_name)}</div>` : ''}
            <div class="bubble-text">${esc(m.message)}</div>
            <div class="bubble-time">${msgTimeFmt(m.time)}${m.mine ? (m.seen ? ' ✓✓' : ' ✓') : ''}</div>
        </div>`;
    }

    /* ═══════════════════════════════════════════════════════════════
       EVENTS — sidebar + main
       ═══════════════════════════════════════════════════════════════ */
    async function loadEvents() {
        const box = el('eventList');
        if (box && !S.events.length) box.innerHTML = skeleton();
        const ft = el('eventFilter'); const type = ft ? ft.value : '';
        try { const d = await api('/api/events' + (type ? '?type=' + type : '')); S.events = d.events || []; } catch (_) {}
        S._loaded.events = true;
        renderEventsSidebar();
        if (S.route === 'events') renderEventsMain();
    }

    function renderEventsSidebar() {
        const box = el('eventList'); if (!box) return;
        if (!S.events.length) {
            box.innerHTML = `<div class="empty-state"><div class="empty-icon">📅</div><p>No upcoming events</p>
                <button class="btn btn-sm btn-primary" data-action="create-event">Create Event</button></div>`;
            const b = $('[data-action="create-event"]', box); if (b) b.onclick = () => openModal('createEventModal');
            return;
        }
        const icons = { webinar: '🎙', meditation: '🧘', workshop: '🛠' };
        box.innerHTML = S.events.map(ev => `
            <div class="contact-item event-item" data-eid="${esc(ev.event_id)}">
                <div class="contact-avatar">${icons[ev.type] || '📅'}</div>
                <div class="contact-info">
                    <div class="contact-name">${esc(ev.title)}</div>
                    <div class="contact-meta">${dateFmt(ev.date)} · ${ev.participant_count} going</div>
                </div>
                ${ev.is_registered ? '<span class="badge badge-success">Going ✓</span>' : '<button class="btn btn-xs btn-primary ev-rsvp-btn">RSVP</button>'}
            </div>`).join('');
        $$('.ev-rsvp-btn', box).forEach(btn => { btn.onclick = async (e) => { e.stopPropagation(); const eid = btn.closest('.event-item').dataset.eid;
            try { await api('/api/events/rsvp', { method: 'POST', body: { event_id: eid } }); toast('Registered!', 'success'); loadEvents(); } catch (err) { toast(err.message, 'error'); } }; });
        $$('.event-item', box).forEach(item => { item.onclick = () => showEventDetail(item.dataset.eid); });
    }

    function renderEventsMain() {
        const box = el('eventsMainContent'); if (!box) return;
        if (!S._loaded.events) { box.innerHTML = `<div class="view-loading">${skeleton(6)}</div>`; return; }
        if (!S.events.length) {
            box.innerHTML = `<div class="view-empty">
                <div class="empty-icon-lg">📅</div><h3>No Events Scheduled</h3>
                <p>Organize workshops, meditation sessions, or webinars for your community.</p>
                <button class="btn btn-glow" data-action="create-evt-main">📅 Create an Event</button></div>`;
            const b = $('[data-action="create-evt-main"]', box); if (b) b.onclick = () => openModal('createEventModal');
            return;
        }
        const icons = { webinar: '🎙', meditation: '🧘', workshop: '🛠' };
        const registered = S.events.filter(e => e.is_registered);
        const upcoming = S.events.filter(e => !e.is_registered);
        box.innerHTML = `
            ${registered.length ? `<div class="section-block"><h4 class="section-heading">Your Events (${registered.length})</h4>
                <div class="card-grid">${registered.map(e => eventCard(e, icons)).join('')}</div></div>` : ''}
            ${upcoming.length ? `<div class="section-block"><h4 class="section-heading">Upcoming</h4>
                <div class="card-grid">${upcoming.map(e => eventCard(e, icons)).join('')}</div></div>` : ''}`;
        $$('[data-event-card]', box).forEach(c => { c.onclick = () => showEventDetail(c.dataset.eventCard); });
    }

    function eventCard(ev, icons) {
        return `<div class="event-card ${ev.is_registered ? 'registered' : ''}" data-event-card="${esc(ev.event_id)}">
            <div class="event-card-icon">${icons[ev.type] || '📅'}</div>
            <div class="event-card-title">${esc(ev.title)}</div>
            <div class="event-card-date">${dateFmt(ev.date)}</div>
            <div class="event-card-meta">👥 ${ev.participant_count}/${ev.max_participants} · ${esc(ev.type)}</div>
            ${ev.is_registered ? '<span class="badge badge-success">Going ✓</span>' : ''}
        </div>`;
    }

    function showEventDetail(eid) {
        const ev = S.events.find(e => e.event_id === eid); if (!ev) return;
        navigate('eventdetail');
        setTxt('contextTitle', ev.title);
        const icons = { webinar: '🎙', meditation: '🧘', workshop: '🛠' };
        setTxt('contextIcon', icons[ev.type] || '📅');
        setTxt('contextSubtitle', dateFmt(ev.date));
        const c = el('eventDetailContent'); if (!c) return;
        c.innerHTML = `<div class="detail-card">
            <div class="detail-icon">${icons[ev.type] || '📅'}</div><h2>${esc(ev.title)}</h2>
            <p class="detail-desc">${esc(ev.description || 'No description.')}</p>
            <div class="detail-meta"><div>📅 ${dateFmt(ev.date)}</div><div>⏱ ${ev.duration_minutes} min</div><div>👥 ${ev.participant_count}/${ev.max_participants}</div><div>🏷 ${esc(ev.type)}</div></div>
            <div class="detail-actions">
                ${ev.is_registered
                    ? `<button class="btn btn-glass" data-action="cancel-rsvp" data-eid="${esc(eid)}">Cancel RSVP</button><a class="btn btn-primary" href="/student/api/events/${esc(eid)}/ics" download>📥 .ics</a>`
                    : `<button class="btn btn-primary" data-action="do-rsvp" data-eid="${esc(eid)}">RSVP Now</button>`}
            </div></div>`;
        const rsvpBtn = $('[data-action="do-rsvp"]', c);
        if (rsvpBtn) rsvpBtn.onclick = async () => { try { await api('/api/events/rsvp', { method: 'POST', body: { event_id: eid } }); toast('Registered!', 'success'); loadEvents(); showEventDetail(eid); } catch (e) { toast(e.message, 'error'); } };
        const cancelBtn = $('[data-action="cancel-rsvp"]', c);
        if (cancelBtn) cancelBtn.onclick = async () => { try { await api('/api/events/cancel', { method: 'POST', body: { event_id: eid } }); toast('Cancelled', 'info'); loadEvents(); showEventDetail(eid); } catch (e) { toast(e.message, 'error'); } };
    }

    /* ═══════════════════════════════════════════════════════════════
       RESOURCES — sidebar + main
       ═══════════════════════════════════════════════════════════════ */
    async function loadResources() {
        const box = el('resourceList');
        if (box && !S.resources.length) box.innerHTML = skeleton();
        const s = el('resourceSort'); const sort = s ? s.value : 'recent';
        try { const d = await api('/api/resources?sort=' + sort); S.resources = d.resources || []; } catch (_) {}
        S._loaded.resources = true;
        renderResourcesSidebar();
        if (S.route === 'resources') renderResourcesMain();
    }

    function renderResourcesSidebar() {
        const box = el('resourceList'); if (!box) return;
        if (!S.resources.length) {
            box.innerHTML = `<div class="empty-state"><div class="empty-icon">📚</div><p>No resources yet</p>
                <button class="btn btn-sm btn-primary" data-action="share-res">Share Resource</button></div>`;
            const b = $('[data-action="share-res"]', box); if (b) b.onclick = () => openModal('shareResourceModal');
            return;
        }
        box.innerHTML = S.resources.map(r => `
            <div class="contact-item resource-item" data-rid="${esc(r.resource_id)}">
                <div class="contact-avatar">📄</div>
                <div class="contact-info"><div class="contact-name">${esc(r.title)}</div><div class="contact-meta">${(r.tags || []).map(t => esc(t)).join(', ')} · ❤️ ${r.likes}</div></div>
                <button class="btn btn-xs ${r.liked_by_me ? 'btn-liked' : 'btn-like'} res-like-btn">${r.liked_by_me ? '❤️' : '🤍'}</button>
            </div>`).join('');
        $$('.res-like-btn', box).forEach(btn => { btn.onclick = async (e) => { e.stopPropagation(); const rid = btn.closest('.resource-item').dataset.rid;
            try { await api('/api/resources/like', { method: 'POST', body: { resource_id: rid } }); loadResources(); } catch (err) { toast(err.message, 'error'); } }; });
        $$('.resource-item', box).forEach(item => { item.onclick = () => { const r = S.resources.find(x => x.resource_id === item.dataset.rid); if (r) showResourceDetail(r); }; });
    }

    function renderResourcesMain() {
        const box = el('resourcesMainContent'); if (!box) return;
        if (!S._loaded.resources) { box.innerHTML = `<div class="view-loading">${skeleton(6)}</div>`; return; }
        if (!S.resources.length) {
            box.innerHTML = `<div class="view-empty">
                <div class="empty-icon-lg">📚</div><h3>Share Knowledge</h3>
                <p>Share useful links, guides, and resources with your community.</p>
                <button class="btn btn-glow" data-action="share-res-main">📤 Share a Resource</button></div>`;
            const b = $('[data-action="share-res-main"]', box); if (b) b.onclick = () => openModal('shareResourceModal');
            return;
        }
        box.innerHTML = `<div class="card-grid resources-card-grid">${S.resources.map(r => resourceCard(r)).join('')}</div>`;
        $$('[data-res-card]', box).forEach(c => { const r = S.resources.find(x => x.resource_id === c.dataset.resCard); if (r) c.onclick = () => showResourceDetail(r); });
    }

    function resourceCard(r) {
        return `<div class="resource-card" data-res-card="${esc(r.resource_id)}">
            <div class="resource-card-title">${esc(r.title)}</div>
            <div class="resource-card-tags">${(r.tags || []).map(t => `<span class="sug-tag">${esc(t)}</span>`).join('')}</div>
            <div class="resource-card-meta">❤️ ${r.likes} · ${esc((r.uploaded_by || '').split('@')[0])}</div>
        </div>`;
    }

    function showResourceDetail(r) {
        navigate('resourcedetail');
        setTxt('contextTitle', r.title);
        setTxt('contextIcon', '📄');
        setTxt('contextSubtitle', (r.tags || []).join(', '));
        const c = el('resourceDetailContent'); if (!c) return;
        c.innerHTML = `<div class="detail-card"><div class="detail-icon">📄</div><h2>${esc(r.title)}</h2>
            <p class="detail-desc">${esc(r.description || 'No description.')}</p>
            <div class="detail-meta"><div>🏷 ${(r.tags || []).map(t => esc(t)).join(', ') || 'No tags'}</div><div>❤️ ${r.likes} likes</div><div>📤 ${esc((r.uploaded_by || '').split('@')[0])}</div></div>
            <div class="detail-actions"><a class="btn btn-primary" href="${esc(r.link)}" target="_blank" rel="noopener">🔗 Open</a>
                <button class="btn btn-glass" data-action="like-res" data-rid="${esc(r.resource_id)}">${r.liked_by_me ? '💔 Unlike' : '❤️ Like'}</button></div></div>`;
        const likeBtn = $('[data-action="like-res"]', c);
        if (likeBtn) likeBtn.onclick = async () => { try { await api('/api/resources/like', { method: 'POST', body: { resource_id: r.resource_id } }); loadResources(); } catch (e) { toast(e.message, 'error'); } };
    }

    /* ═══════════════════════════════════════════════════════════════
       FEED — sidebar + main
       ═══════════════════════════════════════════════════════════════ */
    async function loadFeed() {
        try { const d = await api('/api/connect-hub/feed'); S.feed = d.feed || []; } catch (_) {}
        S._loaded.feed = true;
        renderFeedSidebar();
        if (S.route === 'feed') renderFeedMain();
        if (S.route === 'welcome') renderFeedWelcome();
    }

    function renderFeedSidebar() {
        const box = el('feedList'); if (!box) return;
        box.innerHTML = !S.feed.length
            ? '<div class="empty-state"><div class="empty-icon">🌊</div><p>Activity will appear here</p></div>'
            : S.feed.slice(0, 15).map(f => `<div class="feed-item"><span class="feed-icon">${esc(f.icon)}</span><span class="feed-text">${esc(f.text)}</span><span class="feed-time">${timeAgo(f.time)}</span></div>`).join('');
    }

    function renderFeedMain() {
        const box = el('feedMainContent'); if (!box) return;
        if (!S.feed.length) {
            box.innerHTML = `<div class="view-empty"><div class="empty-icon-lg">🌊</div><h3>Community Activity</h3><p>Activity from your network will appear here as people connect, join groups, and share resources.</p></div>`;
            return;
        }
        box.innerHTML = `<div class="feed-timeline-list">${S.feed.map(f => `
            <div class="feed-timeline-item">
                <div class="feed-timeline-dot"></div>
                <div class="feed-timeline-content">
                    <span class="feed-icon">${esc(f.icon)}</span>
                    <span class="feed-text">${esc(f.text)}</span>
                    <span class="feed-time">${timeAgo(f.time)}</span>
                </div>
            </div>`).join('')}</div>`;
    }

    function renderFeedWelcome() {
        const box = el('mainFeedList'); if (!box) return;
        box.innerHTML = !S.feed.length
            ? '<p class="muted">No recent activity</p>'
            : S.feed.slice(0, 5).map(f => `<div class="feed-item"><span class="feed-icon">${esc(f.icon)}</span><span class="feed-text">${esc(f.text)}</span><span class="feed-time">${timeAgo(f.time)}</span></div>`).join('');
    }

    /* ═══════════════════════════════════════════════════════════════
       NOTIFICATIONS
       ═══════════════════════════════════════════════════════════════ */
    async function loadNotifications() {
        try {
            const d = await api('/api/connect-hub/notifications');
            S.notifications = d.notifications || [];
            const badge = el('notifBadge');
            if (badge) { if (d.unread_count > 0) { badge.textContent = d.unread_count; badge.style.display = 'inline-flex'; } else badge.style.display = 'none'; }
        } catch (_) {}
    }

    function renderNotifications() {
        const box = el('notifList'); if (!box) return;
        if (!S.notifications.length) { box.innerHTML = '<div class="view-empty"><div class="empty-icon-lg">🔔</div><h3>All Caught Up</h3><p>You have no notifications right now.</p></div>'; return; }
        box.innerHTML = S.notifications.map(n => `
            <div class="notif-item ${n.read ? '' : 'unread'}" data-nid="${esc(n.id)}">
                <div class="notif-title">${esc(n.title)}</div>
                ${n.body ? `<div class="notif-body">${esc(n.body)}</div>` : ''}
                <div class="notif-time">${timeAgo(n.time)}</div>
            </div>`).join('');
        $$('.notif-item.unread', box).forEach(item => {
            item.onclick = async () => { try { await api('/api/connect-hub/notifications/read', { method: 'POST', body: { id: item.dataset.nid } }); item.classList.remove('unread'); loadNotifications(); } catch (_) {} };
        });
    }

    /* ═══════════════════════════════════════════════════════════════
       STATS + RECS
       ═══════════════════════════════════════════════════════════════ */
    async function loadStats() {
        try {
            const d = await api('/api/connect-hub/stats'); S.stats = d;
            setTxt('statOnline', d.active_now || 0); setTxt('statPeers', d.connected_users || 0);
            setTxt('statGroups', d.my_groups || 0); setTxt('statEvents', d.events || 0);
            const reqBadge = el('reqBadge');
            if (reqBadge) { if (d.pending_requests > 0) { reqBadge.textContent = d.pending_requests; reqBadge.style.display = 'inline-flex'; } else reqBadge.style.display = 'none'; }
        } catch (_) {}
    }

    async function loadRecs() {
        try {
            const d = await api('/api/connect-hub/recommendations');
            const recs = d.recommendations || [];
            const container = el('sidebarRecs'); const list = el('recsList');
            if (!container || !list) return;
            if (!recs.length) { container.style.display = 'none'; return; }
            container.style.display = 'block';
            const icons = { users: '👥', calendar: '📅', heart: '💚', wind: '🧘' };
            list.innerHTML = recs.map(r => `<div class="rec-item" data-rec-action="${esc(r.action)}" data-rec-payload='${esc(JSON.stringify(r.action_data))}'><span class="rec-icon">${icons[r.icon] || '✨'}</span><div class="rec-text"><div class="rec-title">${esc(r.title)}</div><div class="rec-desc">${esc(r.description)}</div></div></div>`).join('');
            $$('.rec-item', list).forEach(item => {
                item.onclick = async () => {
                    const action = item.dataset.recAction;
                    let payload; try { payload = JSON.parse(item.dataset.recPayload || '{}'); } catch (_) { payload = {}; }
                    if (action === 'join_group' && payload.group_id) { try { await api('/api/groups/join', { method: 'POST', body: { group_id: payload.group_id } }); toast('Joined!', 'success'); loadGroups(); loadRecs(); } catch (e) { toast(e.message, 'error'); } }
                    else if (action === 'rsvp_event' && payload.event_id) { try { await api('/api/events/rsvp', { method: 'POST', body: { event_id: payload.event_id } }); toast('Registered!', 'success'); loadEvents(); loadRecs(); } catch (e) { toast(e.message, 'error'); } }
                    else if (action === 'view_suggestions') openSuggestions();
                };
            });
        } catch (_) { const c = el('sidebarRecs'); if (c) c.style.display = 'none'; }
    }

    /* ═══════════════════════════════════════════════════════════════
       SEARCH
       ═══════════════════════════════════════════════════════════════ */
    let _searchTimer = null;
    function handleSearch(query) {
        clearTimeout(_searchTimer);
        const box = el('searchResults'); if (!box) return;
        if (!query) { box.style.display = 'none'; return; }
        _searchTimer = setTimeout(() => {
            const q = query.toLowerCase(); const results = [];
            S.peers.filter(p => (p.name || '').toLowerCase().includes(q)).slice(0, 3).forEach(p => results.push({ icon: '👤', label: p.name, sub: p.department || 'Student', action: () => openDM(p.email) }));
            S.groups.filter(g => (g.name || '').toLowerCase().includes(q)).slice(0, 3).forEach(g => results.push({ icon: '💬', label: g.name, sub: g.type, action: () => { if (g.is_member) openGroupChat(g); else navigate('groups'); } }));
            S.events.filter(e => (e.title || '').toLowerCase().includes(q)).slice(0, 3).forEach(e => results.push({ icon: '📅', label: e.title, sub: dateFmt(e.date), action: () => showEventDetail(e.event_id) }));
            S.resources.filter(r => (r.title || '').toLowerCase().includes(q)).slice(0, 3).forEach(r => results.push({ icon: '📄', label: r.title, sub: (r.tags || []).join(', '), action: () => showResourceDetail(r) }));
            if (!results.length) { box.innerHTML = '<div class="search-empty">No results</div>'; box.style.display = 'block'; return; }
            box.innerHTML = results.map((r, i) => `<div class="search-result-item" data-idx="${i}"><span class="sr-icon">${r.icon}</span><div class="sr-text"><div class="sr-label">${esc(r.label)}</div><div class="sr-sub">${esc(r.sub)}</div></div></div>`).join('');
            box.style.display = 'block';
            $$('.search-result-item', box).forEach(item => { item.onclick = () => { results[parseInt(item.dataset.idx)]?.action(); box.style.display = 'none'; el('hubSearchInput').value = ''; }; });
        }, CFG.SEARCH_DEBOUNCE);
    }

    /* ═══════════════════════════════════════════════════════════════
       MODALS + FORMS
       ═══════════════════════════════════════════════════════════════ */
    function openModal(id)  { const m = el(id); if (m) m.classList.add('show'); }
    function closeModal(id) { const m = el(id); if (m) m.classList.remove('show'); }

    async function openSuggestions() {
        openModal('suggestionsModal');
        const list = el('suggestionsList');
        if (!list) return;
        const searchInput = el('suggestionSearch');
        if (searchInput) searchInput.value = '';
        S.suggestionFilter = 'all';
        const filters = el('suggestionsFilters');
        if (filters) $$('.filter-chip', filters).forEach(c => c.classList.toggle('active', c.dataset.filter === 'all'));

        list.innerHTML = skeleton(4);
        try {
            const d = await api('/api/connect/suggestions');
            const sugs = d.suggestions || [];
            if (!sugs.length) {
                list.innerHTML = '<div class="suggestion-empty"><strong>No suggestions yet</strong><span>Try again shortly or invite peers from your department.</span><button class="btn btn-sm btn-glass suggestion-cta" id="suggestionRefreshInline">Refresh</button></div>';
                const refreshInline = el('suggestionRefreshInline');
                if (refreshInline) refreshInline.onclick = openSuggestions;
                return;
            }
            S.suggestions = sugs;
            renderSuggestions();
        } catch (e) {
            list.innerHTML = '<div class="suggestion-error"><strong>Could not load suggestions</strong><span>Please check your connection and try again.</span><button class="btn btn-sm btn-primary suggestion-cta" id="suggestionRetry">Retry</button></div>';
            const retry = el('suggestionRetry');
            if (retry) retry.onclick = openSuggestions;
        }
    }

    function setSuggestionFilter(filter) {
        S.suggestionFilter = filter;
        const filters = el('suggestionsFilters');
        if (filters) $$('.filter-chip', filters).forEach(c => c.classList.toggle('active', c.dataset.filter === filter));
        renderSuggestions();
    }

    function renderSuggestions() {
        const list = el('suggestionsList');
        if (!list) return;
        const query = (el('suggestionSearch')?.value || '').toLowerCase();
        let items = (S.suggestions || []).slice();

        if (S.suggestionFilter === 'online') items = items.filter(s => s.online);
        if (S.suggestionFilter === 'high') items = items.filter(s => (s.match_score || 0) >= 3);
        if (S.suggestionFilter === 'dept') {
            const dept = (S.user.department || '').trim().toLowerCase();
            if (!dept) {
                list.innerHTML = '<div class="suggestion-empty"><strong>No department found</strong><span>Add your department to your profile to use this filter.</span><button class="btn btn-sm btn-glass suggestion-cta" id="suggestionClearFilters">Clear filters</button></div>';
                const clearBtn = el('suggestionClearFilters');
                if (clearBtn) clearBtn.onclick = () => setSuggestionFilter('all');
                return;
            }
            items = items.filter(s => (s.department || '').trim().toLowerCase() === dept);
        }

        if (query) {
            items = items.filter(s => (s.name || '').toLowerCase().includes(query) || (s.department || '').toLowerCase().includes(query));
        }

        if (!items.length) {
            list.innerHTML = '<div class="suggestion-empty"><strong>No matches for this filter</strong><span>Try clearing filters or searching a different name.</span><button class="btn btn-sm btn-glass suggestion-cta" id="suggestionClearFilters">Clear filters</button></div>';
            const clearBtn = el('suggestionClearFilters');
            if (clearBtn) clearBtn.onclick = () => { if (el('suggestionSearch')) el('suggestionSearch').value = ''; setSuggestionFilter('all'); };
            return;
        }

        list.innerHTML = items.map(s => {
            const score = typeof s.match_score === 'number' ? s.match_score.toFixed(1) : '';
            return `<div class="suggestion-card">
                <div class="sug-avatar">${esc((s.name || '?')[0].toUpperCase())}</div>
                <div class="sug-name">${esc(s.name)}</div>
                <div class="sug-dept">${esc(s.department || 'Student')}</div>
                <div class="sug-meta">${s.online ? '🟢 Online' : '⚪ Offline'} · ${esc(s.stress_level)}</div>
                <div class="sug-reasons">${(s.reasons || []).map(r => `<span class="sug-tag">${esc(r)}</span>`).join('')}</div>
                ${score ? `<div class="sug-score">Match ${score}</div>` : ''}
                <button class="btn btn-sm btn-primary sug-connect-btn" data-email="${esc(s.email)}">Connect</button>
            </div>`;
        }).join('');

        $$('.sug-connect-btn', list).forEach(btn => {
            btn.onclick = async () => {
                try {
                    await api('/api/connect/request', { method: 'POST', body: { email: btn.dataset.email } });
                    toast('Request sent!', 'success');
                    btn.textContent = 'Sent ✓';
                    btn.disabled = true;
                    btn.classList.replace('btn-primary', 'btn-glass');
                } catch (e) { toast(e.message, 'error'); }
            };
        });
    }

    async function submitInvite() {
        const email = val('inviteEmail');
        if (!email) { toast('Email required', 'error'); return; }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            toast('Enter a valid email address', 'error');
            return;
        }
        try {
            await api('/api/connect/request', { method: 'POST', body: { email } });
            toast('Invite sent!', 'success');
            clr('inviteEmail');
            loadPeers();
            loadStats();
        } catch (e) {
            if ((e.message || '').toLowerCase().includes('not found')) {
                toast('User not found. Ask them to sign up first.', 'info');
            } else {
                toast(e.message, 'error');
            }
        }
    }

    async function openRequests() {
        openModal('requestsModal');
        try { const d = await api('/api/connect/requests'); const inc = d.incoming || [], out = d.outgoing || [];
            const incBox = el('incomingRequests');
            if (incBox) { incBox.innerHTML = inc.length ? inc.map(r => `<div class="request-item"><div class="req-info"><strong>${esc(r.name)}</strong> · ${esc(r.department || 'Student')} · ${timeAgo(r.created_at)}</div><div class="req-actions"><button class="btn btn-xs btn-primary req-accept-btn" data-rid="${esc(r.id)}">Accept</button><button class="btn btn-xs btn-glass req-reject-btn" data-rid="${esc(r.id)}">Decline</button></div></div>`).join('') : '<p class="muted">No incoming requests</p>';
                $$('.req-accept-btn', incBox).forEach(btn => { btn.onclick = async () => { try { await api('/api/connect/respond', { method: 'POST', body: { request_id: btn.dataset.rid, action: 'accept' } }); toast('Accepted!', 'success'); openRequests(); loadPeers(); loadStats(); } catch (e) { toast(e.message, 'error'); } }; });
                $$('.req-reject-btn', incBox).forEach(btn => { btn.onclick = async () => { try { await api('/api/connect/respond', { method: 'POST', body: { request_id: btn.dataset.rid, action: 'reject' } }); toast('Declined', 'info'); openRequests(); loadStats(); } catch (e) { toast(e.message, 'error'); } }; }); }
            const outBox = el('outgoingRequests');
            if (outBox) outBox.innerHTML = out.length ? out.map(r => `<div class="request-item"><div class="req-info"><strong>${esc(r.name)}</strong> · Pending</div></div>`).join('') : '<p class="muted">No sent requests</p>';
        } catch (_) {}
    }

    async function submitGroup() {
        const name = val('newGroupName'), desc = val('newGroupDesc'), type = val('newGroupType');
        if (!name) { toast('Name required', 'error'); return; }
        try { await api('/api/groups/create', { method: 'POST', body: { name, description: desc, type } }); toast('Group created!', 'success'); closeModal('createGroupModal'); clr('newGroupName'); clr('newGroupDesc'); loadGroups(); loadFeed(); loadStats(); } catch (e) { toast(e.message, 'error'); }
    }
    async function submitEvent() {
        const title = val('newEventTitle'), desc = val('newEventDesc'), type = val('newEventType'), date = val('newEventDate'), dur = val('newEventDuration');
        if (!title) { toast('Title required', 'error'); return; } if (!date) { toast('Date required', 'error'); return; }
        try { await api('/api/events/create', { method: 'POST', body: { title, description: desc, type, date, duration_minutes: parseInt(dur) || 60 } }); toast('Event created!', 'success'); closeModal('createEventModal'); clr('newEventTitle'); clr('newEventDesc'); clr('newEventDate'); loadEvents(); loadFeed(); loadStats(); } catch (e) { toast(e.message, 'error'); }
    }
    async function submitResource() {
        const title = val('newResTitle'), link = val('newResLink'), desc = val('newResDesc'), tagsRaw = val('newResTags');
        const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];
        if (!title) { toast('Title required', 'error'); return; } if (!link) { toast('URL required', 'error'); return; }
        try { await api('/api/resources', { method: 'POST', body: { title, link, description: desc, tags } }); toast('Shared!', 'success'); closeModal('shareResourceModal'); clr('newResTitle'); clr('newResLink'); clr('newResDesc'); clr('newResTags'); loadResources(); loadFeed(); } catch (e) { toast(e.message, 'error'); }
    }



    /* ═══════════════════════════════════════════════════════════════
       INIT
       ═══════════════════════════════════════════════════════════════ */
    function init() {
        if (S._ready) return; S._ready = true;
        console.log('[Connect Hub v4.0] Initializing...');

        syncResponsiveLayout();

        const shell = el('hubShell');
        if (shell) {
            S.user.email = shell.dataset.userEmail || '';
            S.user.name = shell.dataset.userName || '';
            S.user.department = shell.dataset.userDept || '';
        }

        // Tab clicks → navigate
        $$('.nav-tab').forEach(btn => btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
            if (isMobileViewport()) closeSidebar();
        }));

        // Mobile sidebar controls
        bind('mobileSidebarToggle', 'click', () => {
            const sidebar = el('hubSidebar');
            if (!sidebar) return;
            if (sidebar.classList.contains('open')) closeSidebar();
            else openSidebar();
        });
        bind('sidebarCloseBtn', 'click', closeSidebar);
        bind('hubSidebarBackdrop', 'click', closeSidebar);
        window.addEventListener('resize', syncResponsiveLayout);

        // Context back button
        bind('contextBack', 'click', goBack);

        // Chat sends
        bind('dmSendBtn', 'click', sendDM);
        bind('dmInput', 'keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); sendDM(); } else if (S.dmPeer) emitTyping(S.dmPeer.email, 'dm'); });
        bind('groupSendBtn', 'click', sendGroupMsg);
        bind('groupChatInput', 'keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); sendGroupMsg(); } else if (S.groupChat) emitTyping(S.groupChat.group_id, 'group'); });

        // Peer search / filters
        bind('peerSearch', 'input', (e) => renderPeersSidebar(e.target.value));
        bind('groupFilter', 'change', loadGroups);
        bind('eventFilter', 'change', loadEvents);
        bind('resourceSort', 'change', loadResources);

        // Create/Share modal openers
        bind('createGroupBtn', 'click', () => openModal('createGroupModal'));
        bind('createEventBtn', 'click', () => openModal('createEventModal'));
        bind('shareResourceBtn', 'click', () => openModal('shareResourceModal'));

        // Submit buttons
        bind('submitGroupBtn', 'click', submitGroup);
        bind('submitEventBtn', 'click', submitEvent);
        bind('submitResourceBtn', 'click', submitResource);

        // Find people / Requests
        bind('showSuggestionsBtn', 'click', openSuggestions);
        bind('refreshSuggestions', 'click', openSuggestions);
        bind('suggestionSearch', 'input', () => renderSuggestions());
        bind('inviteSendBtn', 'click', submitInvite);
        bind('inviteEmail', 'keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); submitInvite(); } });
        const filterBox = el('suggestionsFilters');
        if (filterBox) {
            $$('.filter-chip', filterBox).forEach(chip => {
                chip.addEventListener('click', () => setSuggestionFilter(chip.dataset.filter || 'all'));
            });
        }
        bind('showRequestsBtn', 'click', openRequests);

        // Welcome panel actions
        bind('welcomeFindPeers', 'click', () => { navigate('peers'); openSuggestions(); });
        bind('welcomeBrowseGroups', 'click', () => navigate('groups'));
        bind('welcomeBrowseEvents', 'click', () => navigate('events'));

        // Notifications
        bind('notifBell', 'click', () => { loadNotifications(); navigate('notifications'); });
        bind('markAllReadBtn', 'click', async () => { try { await api('/api/connect-hub/notifications/read', { method: 'POST', body: { id: 'all' } }); toast('All marked read', 'info'); loadNotifications(); renderNotifications(); } catch (_) {} });

        // Hub-wide search
        bind('hubSearchToggle', 'click', () => { const bar = el('searchBar'); if (bar) { bar.style.display = bar.style.display === 'none' ? 'flex' : 'none'; el('hubSearchInput')?.focus(); } });
        bind('hubSearchInput', 'input', (e) => handleSearch(e.target.value));
        bind('searchClear', 'click', () => { const inp = el('hubSearchInput'); if (inp) inp.value = ''; const box = el('searchResults'); if (box) box.style.display = 'none'; });

        // Modal close
        $$('.hub-modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.remove('show'); });
            $$('[data-close]', overlay).forEach(btn => { btn.addEventListener('click', () => overlay.classList.remove('show')); });
        });

        // Keyboard
        document.addEventListener('keydown', (e) => { 
            if (e.key === 'Escape') { 
                $$('.hub-modal-overlay.show').forEach(m => m.classList.remove('show')); 
                const sr = el('searchResults'); 
                if (sr) sr.style.display = 'none'; 
                closeSidebar();
            }
            // Ctrl+K for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const bar = el('searchBar');
                if (bar) {
                    bar.style.display = 'flex';
                    el('hubSearchInput')?.focus();
                }
            }
            // ? for help
            if (e.key === '?' && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
                e.preventDefault();
                openModal('helpModal');
            }
        });

        // Help button
        bind('helpBtn', 'click', () => openModal('helpModal'));

        // ── Zen Mode toggle ──
        const zenBtn = el('zenToggle');
        if (zenBtn) {
            const zenKey = 'hub_zen_mode';
            // Restore saved state
            if (localStorage.getItem(zenKey) === '1') {
                document.body.classList.add('zen-mode');
                zenBtn.classList.add('active');
                zenBtn.textContent = '🔄 Exit Zen';
            }
            zenBtn.addEventListener('click', () => {
                const isZen = document.body.classList.toggle('zen-mode');
                zenBtn.classList.toggle('active', isZen);
                zenBtn.textContent = isZen ? '🔄 Exit Zen' : '🧘 Zen';
                localStorage.setItem(zenKey, isZen ? '1' : '0');
            });
        }

        // Initial data loads
        loadStats(); loadPeers(); loadFeed(); loadNotifications(); loadRecs();

        // Smart Picks close button
        const recsCloseBtn = el('recsCloseBtn');
        if (recsCloseBtn) {
            recsCloseBtn.addEventListener('click', () => {
                const recs = el('sidebarRecs');
                if (recs) recs.style.display = 'none';
            });
        }

        // Socket.IO
        initSocket();

        // Periodic refresh
        S.timers.stat = setInterval(() => { loadStats(); loadNotifications(); }, CFG.STAT_INTERVAL);

        // Route from URL (handles /student/hub/peers on refresh)
        const initialRoute = parseRoute();
        navigate(initialRoute, { silent: true });
        // Replace current history entry so popstate works
        history.replaceState({ route: initialRoute }, '', window.location.pathname);

        // Reveal
        if (shell) shell.classList.add('ready');
        console.log('[Connect Hub v4.0] Ready ✓');
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
