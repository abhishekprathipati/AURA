import os
import re

directories_to_check = ['d:\\AURA\\aura', 'd:\\AURA\\scripts', 'd:\\AURA\\tests']
modules_to_prefix = ['models', 'utils', 'services', 'routes', 'middleware', 'sockets', 'core']

for root_dir in directories_to_check:
    if not os.path.exists(root_dir):
        continue
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                for mod in modules_to_prefix:
                    # from {mod} import ... or from {mod}.something import ...
                    # match indented or not
                    new_content = re.sub(
                        r'^(\s*)from\s+' + mod + r'\b', 
                        r'\1from aura.' + mod, 
                        new_content, 
                        flags=re.MULTILINE
                    )
                    
                    # import {mod}
                    new_content = re.sub(
                        r'^(\s*)import\s+' + mod + r'\b', 
                        r'\1import aura.' + mod, 
                        new_content, 
                        flags=re.MULTILINE
                    )

                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated {filepath}")
