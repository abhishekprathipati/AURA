from app import app
from flask import render_template

with app.test_request_context('/student/dashboard'):
    html = render_template('student_dashboard.html', show_nav=False)
    print('dashboard-nav in template?', '.dashboard-nav' in html)
    # print a short snippet around any dashboard-nav occurrences
    idx = html.find('.dashboard-nav')
    if idx != -1:
        start = max(0, idx-200)
        end = idx+200
        print(html[start:end])
    else:
        print('No .dashboard-nav found in rendered HTML')
