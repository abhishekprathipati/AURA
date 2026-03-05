"""Append sidebar widget CSS (Today's Summary + Daily Inspiration)."""
import pathlib

css_path = pathlib.Path(r"d:\AURA\static\css\student_dashboard.css")
css = css_path.read_text(encoding="utf-8")

new_css = """
/* ===== TODAY'S SUMMARY CARD ===== */
.sidebar-summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    transition: all 0.25s ease;
}

.sidebar-summary-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}

.summary-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
}

.summary-header h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
}

.summary-icon {
    font-size: 18px;
}

.summary-stats {
    display: flex;
    justify-content: space-between;
    gap: 8px;
}

.summary-stat {
    flex: 1;
    text-align: center;
    padding: 10px 6px;
    background: rgba(var(--primary-rgb), 0.04);
    border-radius: 10px;
    transition: background 0.2s;
}

.summary-stat:hover {
    background: rgba(var(--primary-rgb), 0.08);
}

.stat-value {
    display: block;
    font-size: 20px;
    font-weight: 800;
    background: linear-gradient(135deg, #6b73ff, #9f7aea);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
}

.stat-label {
    display: block;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    margin-top: 4px;
    white-space: nowrap;
}

/* ===== DAILY INSPIRATION CARD ===== */
.sidebar-inspiration-card {
    background: linear-gradient(135deg, rgba(107,115,255,0.08), rgba(159,122,234,0.08));
    border: 1px solid rgba(var(--primary-rgb), 0.12);
    border-radius: 14px;
    padding: 18px 16px;
    position: relative;
    overflow: hidden;
    transition: all 0.25s ease;
}

.sidebar-inspiration-card::before {
    content: "";
    position: absolute;
    top: -20px;
    right: -20px;
    width: 80px;
    height: 80px;
    background: linear-gradient(135deg, rgba(107,115,255,0.15), rgba(159,122,234,0.1));
    border-radius: 50%;
    pointer-events: none;
}

.sidebar-inspiration-card:hover {
    box-shadow: 0 4px 16px rgba(107,115,255,0.1);
    border-color: rgba(var(--primary-rgb), 0.2);
}

.inspiration-quote {
    position: relative;
}

.quote-mark {
    margin-bottom: 6px;
    color: var(--primary);
    opacity: 0.4;
}

.quote-text {
    font-size: 13.5px;
    font-weight: 500;
    line-height: 1.6;
    color: var(--text);
    margin: 0 0 10px 0;
    font-style: italic;
}

.quote-attr {
    font-size: 11.5px;
    font-weight: 600;
    color: var(--primary);
    opacity: 0.7;
}

/* Dark theme adjustments */
[data-theme="dark"] .sidebar-summary-card {
    background: var(--surface);
    border-color: var(--border);
}

[data-theme="dark"] .summary-stat {
    background: rgba(255,255,255,0.04);
}

[data-theme="dark"] .summary-stat:hover {
    background: rgba(255,255,255,0.07);
}

[data-theme="dark"] .sidebar-inspiration-card {
    background: linear-gradient(135deg, rgba(107,115,255,0.1), rgba(159,122,234,0.08));
    border-color: rgba(107,115,255,0.15);
}

[data-theme="dark"] .sidebar-inspiration-card::before {
    background: linear-gradient(135deg, rgba(107,115,255,0.12), rgba(159,122,234,0.08));
}
"""

css += new_css
css_path.write_text(css, encoding="utf-8")
print("CSS appended successfully!")
