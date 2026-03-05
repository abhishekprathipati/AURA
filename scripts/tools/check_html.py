import re
html = open(r'd:\AURA\templates\student_dashboard.html', 'r', encoding='utf-8').read()
opens = len(re.findall(r'<div[\s>]', html))
closes = len(re.findall(r'</div>', html))
print(f'div open={opens} close={closes} balanced={opens==closes}')
# Check slide panels exist
panels = re.findall(r'class="slide-panel"', html)
print(f'Slide panels: {len(panels)}')
btns = re.findall(r'class="sidebar-btn"', html)
print(f'Sidebar buttons: {len(btns)}')
overlay = 'slideOverlay' in html
print(f'Overlay exists: {overlay}')
