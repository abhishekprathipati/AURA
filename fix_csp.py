import re
import os

files_to_fix = [
    'd:\\AURA\\templates\\student_dashboard.html',
    'd:\\AURA\\templates\\proctor_dashboard.html',
    'd:\\AURA\\templates\\parent_dashboard.html',
    'd:\\AURA\\templates\\hod_dashboard.html',
    'd:\\AURA\\templates\\study_chatbot.html',
    'd:\\AURA\\templates\\mental_chatbot.html',
    'd:\\AURA\\templates\\connect_hub.html'
]

for path in files_to_fix:
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace <script> with <script nonce="{{ csp_nonce }}">
    content = re.sub(r'<script>', r'<script nonce="{{ csp_nonce }}">', content)
    # Replace <style> with <style nonce="{{ csp_nonce }}">
    content = re.sub(r'<style>', r'<style nonce="{{ csp_nonce }}">', content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print('Done replacing.')
