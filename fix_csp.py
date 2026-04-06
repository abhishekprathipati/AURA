import glob
import re

files = glob.glob(r'd:\AURA\templates\*.html')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace <style> with <style nonce="{{ csp_nonce }}">
    new_content = re.sub(r'<style>', r'<style nonce="{{ csp_nonce }}">', content)
    # Replace <script> with <script nonce="{{ csp_nonce }}">
    new_content = re.sub(r'<script>', r'<script nonce="{{ csp_nonce }}">', new_content)
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {file}')
print('Done!')
