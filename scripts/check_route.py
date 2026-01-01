import requests
try:
    r = requests.get('http://127.0.0.1:5000/student/chat/mental', timeout=10)
    print('STATUS', r.status_code)
    print('LENGTH', len(r.text))
    print(r.text[:5000])
except Exception as e:
    print('ERROR', e)
