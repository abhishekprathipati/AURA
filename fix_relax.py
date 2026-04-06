import re

with open(r'd:\AURA\templates\relax.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Extract the CSS content between <style ...> and </style>
m = re.search(r'<style[^>]*>(.*?)</style>', text, re.DOTALL)
if m:
    css_content = m.group(1)
    with open(r'd:\AURA\static\css\relax.css', 'w', encoding='utf-8') as f:
        f.write('/* ===== AURA Relax Page Styles ===== */\n')
        f.write(css_content)
    print('Extracted', len(css_content), 'chars to relax.css')

    link_tag = '<link rel="stylesheet" href="/static/css/relax.css?v=20260406">'
    new_text = text[:m.start()] + link_tag + text[m.end():]

    with open(r'd:\AURA\templates\relax.html', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('Replaced inline style with link tag')

    with open(r'd:\AURA\templates\relax.html', 'r', encoding='utf-8') as f:
        verify = f.read()
    opens = len(re.findall(r'<style\b', verify))
    closes = len(re.findall(r'</style>', verify))
    print(f'Verification: <style> opens={opens}, </style> closes={closes}')
    print('relax.css link present:', 'relax.css' in verify)
else:
    print('ERROR: no style block found')
