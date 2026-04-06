import re
import uuid
import os

files = [
    r'd:\AURA\templates\activities.html',
    r'd:\AURA\templates\games.html', 
    r'd:\AURA\templates\relax.html', 
    r'd:\AURA\templates\student_dashboard.html',
    r'd:\AURA\templates\login.html'
]

total_fixed = 0

for filepath in files:
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    script_additions = []
    
    # We will do a manual pass to avoid regex issues with quotes
    # Find all indices of 'onclick='
    
    pattern = re.compile(r'(<[^>]+?)\s+onclick=([\'"])(.*?)\2', re.IGNORECASE | re.DOTALL)
    
    def repl(m):
        prefix = m.group(1)
        quote = m.group(2)
        code = m.group(3)
        
        # Check if it already has an ID
        id_match = re.search(r'\bid=([\'"])(.*?)\1', prefix, re.IGNORECASE)
        if id_match:
            el_id = id_match.group(2)
            new_prefix = prefix
        else:
            el_id = "auto_evt_" + str(uuid.uuid4()).replace("-", "")[:12]
            new_prefix = f'{prefix} id="{el_id}"'
            
        # Optional: ensure we don't attach to nulls if element isn't in DOM immediately
        script_additions.append(f"    var el = document.getElementById('{el_id}'); if(el) el.addEventListener('click', function(event) {{ {code} }});")
        return new_prefix

    new_content = pattern.sub(repl, content)
    
    if script_additions:
        script_str = "\n".join(script_additions)
        inject_code = f'\n<script nonce="{{{{ csp_nonce }}}}">\ndocument.addEventListener("DOMContentLoaded", function() {{\n{script_str}\n}});\n</script>\n'
        
        if '</body>' in new_content:
            new_content = new_content.replace('</body>', f'{inject_code}</body>')
        else:
            new_content += inject_code
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {os.path.basename(filepath)} with {len(script_additions)} handlers")
        total_fixed += len(script_additions)
    else:
        print(f"No onclick handlers found in {os.path.basename(filepath)}")

print(f"Done! Fixed {total_fixed} onclick handlers.")
