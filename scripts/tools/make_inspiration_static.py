"""Update CSS to make inspiration card static (not scrollable)."""
import pathlib

css_path = pathlib.Path(r"d:\AURA\static\css\student_dashboard.css")
css = css_path.read_text(encoding='utf-8')

# Find and replace the dashboard-right CSS
old_dash_right = """.dashboard-right {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
    position: sticky;
    top: 90px;
    max-height: calc(100vh - 104px);
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: thin;
}"""

new_dash_right = """.dashboard-right {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
    position: sticky;
    top: 90px;
    max-height: calc(100vh - 108px);
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: thin;
    padding-bottom: 4px;
}"""

css = css.replace(old_dash_right, new_dash_right)

# Add CSS for static inspiration card
static_css = """
/* Static Inspiration Card (not scrollable) */
.sidebar-inspiration-static {
    flex-shrink: 0;
    margin-top: auto;
    position: sticky;
    bottom: 0;
    background: linear-gradient(135deg, rgba(107,115,255,0.08), rgba(159,122,234,0.08));
    border: 1px solid rgba(var(--primary-rgb), 0.12);
    border-radius: 14px;
    padding: 16px;
}

[data-theme="dark"] .sidebar-inspiration-static {
    background: linear-gradient(135deg, rgba(107,115,255,0.1), rgba(159,122,234,0.08));
    border-color: rgba(107,115,255,0.15);
}
"""

if "/* Static Inspiration Card" not in css:
    css += static_css

css_path.write_text(css, encoding='utf-8')
print("CSS updated: Inspiration card now static!")
