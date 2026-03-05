"""Append sidebar button and slide panel CSS."""
css_block = """
/* ===== SIDEBAR BUTTONS (compact action triggers) ===== */
.sidebar-btn {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    cursor: pointer;
    color: var(--text);
    font-family: inherit;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s ease;
    text-align: left;
}

.sidebar-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    border-color: rgba(var(--primary-rgb), 0.25);
}

.sidebar-btn-icon {
    width: 36px;
    height: 36px;
    min-width: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.sidebar-btn-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.sidebar-btn-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 999px;
    white-space: nowrap;
}

.sidebar-btn-badge.green {
    background: rgba(16, 185, 129, 0.12);
    color: #059669;
}

.sidebar-btn-badge.red {
    background: rgba(239, 68, 68, 0.12);
    color: #dc2626;
}

.sidebar-btn-arrow {
    width: 16px;
    height: 16px;
    min-width: 16px;
    opacity: 0.4;
    transition: opacity 0.2s, transform 0.2s;
}

.sidebar-btn:hover .sidebar-btn-arrow {
    opacity: 0.8;
    transform: translateX(2px);
}

[data-theme="dark"] .sidebar-btn {
    background: var(--surface);
    border-color: var(--border);
}

[data-theme="dark"] .sidebar-btn:hover {
    border-color: rgba(var(--primary-rgb), 0.3);
}

[data-theme="dark"] .sidebar-btn-badge.green {
    background: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
}

[data-theme="dark"] .sidebar-btn-badge.red {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
}

/* ===== SLIDE-IN PANEL ===== */
.slide-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.4);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    z-index: 9998;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.3s ease, visibility 0.3s ease;
}

.slide-overlay.active {
    opacity: 1;
    visibility: visible;
}

.slide-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: min(420px, 90vw);
    height: 100vh;
    background: var(--bg);
    border-left: 1px solid var(--border);
    box-shadow: -8px 0 30px rgba(0,0,0,0.12);
    z-index: 9999;
    transform: translateX(100%);
    transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.slide-panel.active {
    transform: translateX(0);
}

.slide-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
    flex-shrink: 0;
}

.slide-panel-title {
    display: flex;
    align-items: center;
    gap: 12px;
}

.slide-panel-title h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: var(--text);
}

.slide-panel-close {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface-muted);
    color: var(--text);
    font-size: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.slide-panel-close:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #dc2626;
    border-color: rgba(239, 68, 68, 0.3);
}

.slide-panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    overscroll-behavior: contain;
}

[data-theme="dark"] .slide-panel {
    background: var(--bg);
    border-color: var(--border);
    box-shadow: -8px 0 30px rgba(0,0,0,0.4);
}

[data-theme="dark"] .slide-panel-header {
    background: var(--surface);
}

[data-theme="dark"] .slide-panel-close {
    background: var(--surface);
    border-color: var(--border);
}

body.panel-open {
    overflow: hidden;
}
"""

with open(r'd:\AURA\static\css\student_dashboard.css', 'r', encoding='utf-8') as f:
    css = f.read()

css += css_block

with open(r'd:\AURA\static\css\student_dashboard.css', 'w', encoding='utf-8') as f:
    f.write(css)

print('CSS appended! Total length:', len(css))
