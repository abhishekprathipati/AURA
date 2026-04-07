import sys

with open(r'd:\AURA\templates\activities.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

try:
    style_start = lines.index('<style>\n')
    style_end = lines.index('</style>\n', style_start)
    
    with open(r'd:\AURA\static\css\activities.css', 'w', encoding='utf-8') as f:
        f.writelines(lines[style_start+1:style_end])
    
    script_start = lines.index('<script>\n')
    
    new_lines = (
        lines[:style_start] + 
        ['<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/activities.css\') }}">\n'] + 
        lines[style_end+1:script_start] + 
        ['<script nonce="{{ csp_nonce }}">\n'] + 
        lines[script_start+1:]
    )
    
    with open(r'd:\AURA\templates\activities.html', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('Successfully extracted CSS and replaced tags.')
except Exception as e:
    print('Error:', e)
