"""Fix sidebar overflow so all content is visible when scrolling."""
import pathlib

css_path = pathlib.Path(r"d:\AURA\static\css\student_dashboard.css")
css = css_path.read_text(encoding='utf-8')

# Fix 1: dashboard-right - remove overflow:hidden that blocks scrolling
old = """.dashboard-right {
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

new = """.dashboard-right {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
    max-width: 100%;
    overflow-x: hidden;
    overflow-y: auto;
    position: sticky;
    top: 90px;
    max-height: calc(100vh - 108px);
    overscroll-behavior: contain;
    scrollbar-width: thin;
    padding-bottom: 16px;
}"""

if old in css:
    css = css.replace(old, new)
    print("Fixed dashboard-right overflow")
else:
    print("WARNING: dashboard-right block not found exactly")

# Fix 2: Remove the glass-effect !important on sidebar-summary-card
# The glass-effect background was hiding the stats
old_glass = """.glass-effect {
    background: rgba(255, 255, 255, 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    box-shadow: 
        0 8px 32px rgba(0,0,0,0.08),
        inset 0 1px 1px rgba(255,255,255,0.9),
        inset 0 -1px 1px rgba(0,0,0,0.03);
}"""

new_glass = """.glass-effect {
    background: rgba(255, 255, 255, 0.75) !important;
    backdrop-filter: blur(16px) saturate(180%);
    -webkit-backdrop-filter: blur(16px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    box-shadow: 
        0 8px 32px rgba(0,0,0,0.06),
        inset 0 1px 0 rgba(255,255,255,0.8);
}"""

if old_glass in css:
    css = css.replace(old_glass, new_glass)
    print("Fixed glass-effect")

css_path.write_text(css, encoding='utf-8')
print("All fixes applied!")
