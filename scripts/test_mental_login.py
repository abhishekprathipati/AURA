import requests
import os
from dotenv import load_dotenv

load_dotenv()

s = requests.Session()
base = 'http://127.0.0.1:5000'

# Use credentials from environment or prompt user
email = os.getenv('TEST_EMAIL', input('Enter test email: '))
password = os.getenv('TEST_PASSWORD', input('Enter test password: '))

try:
    r = s.post(base + '/login', data={'email': email, 'password': password}, allow_redirects=True, timeout=10)
    print('LOGIN STATUS', r.status_code, 'LENGTH', len(r.text))
    # Fetch mental chat
    r2 = s.get(base + '/student/chat/mental', timeout=10)
    print('MENTAL STATUS', r2.status_code)
    print(r2.text[:2000])
except Exception as e:
    print('ERROR', repr(e))

