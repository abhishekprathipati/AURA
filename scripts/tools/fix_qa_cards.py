"""Wrap QA card text elements in a container div for proper text truncation."""
with open(r'd:\AURA\templates\student_dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re

# Pattern: find each qa-card's h4 and p tags and wrap them
# Replace: <h4>X</h4>\n...<p>Y</p>  with  <div class="qa-card-text"><h4>X</h4><p>Y</p></div>
# inside .qa-card elements

# Find the qa-grid-2x2 block
start = html.find('qa-grid-2x2')
end = html.find('</div>\n', html.find('</a>', html.find('Activities', start)) + 4)

section = html[start:end+10]
print("Found section, length:", len(section))

# For each qa-card, wrap h4+p in a div.qa-card-text
def wrap_card(match):
    icon = match.group(1)
    h4 = match.group(2)
    p = match.group(3)
    return f'{icon}\n                            <div class="qa-card-text">{h4}{p}</div>'

pattern = r'(<div class="qa-card-icon[^"]*">[^<]*</div>)\s*\n\s*(<h4>[^<]*</h4>)\s*\n\s*(<p>[^<]*</p>)'
new_section = re.sub(pattern, wrap_card, section)

if new_section != section:
    html = html[:start] + new_section + html[start+len(section):]
    with open(r'd:\AURA\templates\student_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('Done! QA cards wrapped with .qa-card-text')
else:
    print('Pattern did not match')
    # Debug: show the actual content
    idx = html.find('qa-card-icon purple')
    print(repr(html[idx:idx+200]))
