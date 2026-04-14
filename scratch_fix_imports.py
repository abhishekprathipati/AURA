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
                    # from {mod} import ... -> from aura.{mod} import ...
                    # from {mod}.sub import ... -> from aura.{mod}.sub import ...
                    # import {mod}.sub -> import aura.{mod}.sub
                    
                    # Regex for `from {mod}`
                    new_content = re.sub(
                        r'^from\s+' + mod + r'\b', 
                        r'from aura.' + mod, 
                        new_content, 
                        flags=re.MULTILINE
                    )
                    
                    # Regex for `import {mod}`
                    # Only do it if it matches exactly import utils.something or import utils
                    new_content = re.sub(
                        r'^import\s+' + mod + r'\b', 
                        r'import aura.' + mod, 
                        new_content, 
                        flags=re.MULTILINE
                    )

                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated {filepath}")
