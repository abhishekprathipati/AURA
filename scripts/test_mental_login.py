import requests
s = requests.Session()
base = 'http://127.0.0.1:5000'
# Attempt login
try:
    r = s.post(base + '/login', data={'email':'student@aura.edu','password':'password123'}, allow_redirects=True, timeout=10)
    print('LOGIN STATUS', r.status_code, 'LENGTH', len(r.text))
    # Fetch mental chat
    r2 = s.get(base + '/student/chat/mental', timeout=10)
    print('MENTAL STATUS', r2.status_code)
    print(r2.text[:2000])
except Exception as e:
    print('ERROR', repr(e))

