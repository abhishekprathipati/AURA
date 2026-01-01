from app import app
from flask import render_template
import re

with app.test_request_context('/student/dashboard'):
    html = render_template('student_dashboard.html', show_nav=False)
    print('--- Rendered HTML snippet (first 1000 chars) ---')
    print(html[:1000])
    print('\n--- Searching for <nav ...> tags ---')
    navs = re.findall(r'<nav[^>]*>.*?</nav>', html, flags=re.S)
    if navs:
        print(f'Found {len(navs)} <nav> tags:')
        for i, n in enumerate(navs, 1):
            print(f'--- NAV {i} outerHTML ---')
            print(n[:1000])
    else:
        print('No <nav> tags found in rendered HTML')

    print('\n--- Searching for .dashboard-nav in HTML ---')
    idx = html.find('.dashboard-nav')
    if idx != -1:
        start = max(0, idx-200)
        end = min(len(html), idx+200)
        print('Context around .dashboard-nav:')
        print(html[start:end])
    else:
        print('No .dashboard-nav string in rendered HTML')
