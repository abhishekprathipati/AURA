import re
import os

TEMPLATES = [
    ('d:\\AURA\\templates\\games.html', 'd:\\AURA\\static\\css\\games.css'),
    ('d:\\AURA\\templates\\activities.html', 'd:\\AURA\\static\\css\\activities.css'),
    ('d:\\AURA\\templates\\mental_chatbot.html', 'd:\\AURA\\static\\css\\mental_chatbot.css'),
    ('d:\\AURA\\templates\\study_chatbot.html', 'd:\\AURA\\static\\css\\study_chatbot.css'),
]

for html_path, css_path in TEMPLATES:
    css_filename = os.path.basename(css_path)
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        # Find ALL style blocks and extract them
        style_blocks = list(re.finditer(r'<style[^>]*>(.*?)</style>', text, re.DOTALL))
        
        if not style_blocks:
            print(f'SKIP {html_path}: no inline style blocks')
            continue
        
        # Check if CSS already extracted (external link present)
        if css_filename in text and len(style_blocks) == 0:
            print(f'SKIP {html_path}: already has external CSS')
            continue
        
        all_css = ''
        for sb in style_blocks:
            all_css += sb.group(1) + '\n'
        
        # Write external CSS file
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(f'/* ===== AURA {css_filename} ===== */\n')
            f.write(all_css)
        
        # Replace first style block with link tag, remove the rest
        link_tag = f'<link rel="stylesheet" href="/static/css/{css_filename}?v=20260406">'
        
        # Build new text by removing all style blocks, then inserting link at first style position
        new_text = text
        # Process in reverse to maintain positions
        for sb in reversed(style_blocks):
            new_text = new_text[:sb.start()] + '' + new_text[sb.end():]
        
        # Insert link at position of first style block
        first_pos = style_blocks[0].start()
        new_text = new_text[:first_pos] + link_tag + new_text[first_pos:]
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        
        # Verify
        opens = len(re.findall(r'<style\b', new_text))
        closes = len(re.findall(r'</style>', new_text))
        print(f'OK {os.path.basename(html_path)}: extracted {len(all_css)} chars, style opens={opens} closes={closes}')
        
    except Exception as e:
        print(f'ERROR {html_path}: {e}')

print('Done!')
