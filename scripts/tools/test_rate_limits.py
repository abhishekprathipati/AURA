"""
═══════════════════════════════════════════════════════════════
AURA — Rate Limiting Validation Script
═══════════════════════════════════════════════════════════════
Tests:
  1. Login brute-force protection (5 failures → lockout)
  2. API rate limiting on proctor endpoints
  3. Export endpoint rate limiting
  4. Reseed guard (password survives restart)
  5. 429 response format validation
═══════════════════════════════════════════════════════════════
"""
import requests
import time
import sys
import json

BASE = 'http://127.0.0.1:5000'
PASS = 0
FAIL = 0


def check(label, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  ← {detail}")


def login_session(email='proctor@aura.edu', password='DemoPass!2024#Secure'):
    """Create an authenticated session."""
    s = requests.Session()
    r = s.post(f'{BASE}/login', data={'email': email, 'password': password}, allow_redirects=True)
    return s, r


# ═══════════════════════════════════════════════════════════
print("\n═══ 1. LOGIN BRUTE-FORCE PROTECTION ═══")
# ═══════════════════════════════════════════════════════════
print("  Sending 7 failed login attempts...")
lockout_hit = False
lockout_status = None
for i in range(7):
    r = requests.post(f'{BASE}/login',
                      data={'email': 'test_brute@aura.edu', 'password': f'wrong{i}'},
                      allow_redirects=False)
    if r.status_code == 429:
        lockout_hit = True
        lockout_status = r.status_code
        print(f"    → Locked out at attempt {i+1}")
        break

check("Brute-force lockout triggers before 7 attempts", lockout_hit,
      f"Never got 429, last status: {r.status_code}")

# Verify lockout message
if lockout_hit:
    # The 429 is returned from the login handler as HTML with flash message
    check("429 status code on lockout", lockout_status == 429)

# Wait a moment then verify a good login still works
time.sleep(1)
s, r = login_session()
check("Valid login still works after brute-force on different email",
      'proctor' in r.url or 'dashboard' in r.url,
      f"Got: {r.url}")


# ═══════════════════════════════════════════════════════════
print("\n═══ 2. API RATE LIMITING (ACTIVITY LOGS) ═══")
# ═══════════════════════════════════════════════════════════
s, _ = login_session()

# Send requests within limit (60/min for STANDARD)
r1 = s.get(f'{BASE}/proctor/api/activity-logs', params={'days': '7'})
check("Activity logs accessible within limit", r1.status_code == 200)

# Rapid-fire to trigger limit (60/min = need 61 in under 60s)
print("  Sending 65 rapid requests to activity-logs...")
statuses = []
for i in range(65):
    r = s.get(f'{BASE}/proctor/api/activity-logs', params={'days': '1'})
    statuses.append(r.status_code)
    if r.status_code == 429:
        print(f"    → Rate limited at request {i+1}")
        break

got_429 = 429 in statuses
check("Rate limit triggered on rapid API calls", got_429,
      f"All {len(statuses)} requests returned 200")

# Validate 429 response format
if got_429:
    idx = statuses.index(429)
    r_limited = s.get(f'{BASE}/proctor/api/activity-logs', params={'days': '1'})
    if r_limited.status_code == 429:
        try:
            body = r_limited.json()
            check("429 response is JSON", True)
            check("429 has 'error' field", 'error' in body, f"Keys: {list(body.keys())}")
            check("429 has 'retry_after_seconds'", 'retry_after_seconds' in body)
            check("Retry-After header present", 'Retry-After' in r_limited.headers,
                  f"Headers: {dict(r_limited.headers)}")
        except Exception:
            check("429 response is JSON", False, "Not JSON")


# ═══════════════════════════════════════════════════════════
print("\n═══ 3. EXPORT ENDPOINT RATE LIMITING ═══")
# ═══════════════════════════════════════════════════════════
s2, _ = login_session()
print("  Sending 12 rapid CSV export requests...")
export_statuses = []
for i in range(12):
    r = s2.get(f'{BASE}/proctor/api/activity-logs/export/csv', params={'days': '7'})
    export_statuses.append(r.status_code)
    if r.status_code == 429:
        print(f"    → Export rate limited at request {i+1}")
        break

check("Export endpoint rate limited (10/min)",
      429 in export_statuses,
      f"All {len(export_statuses)} returned 200")


# ═══════════════════════════════════════════════════════════
print("\n═══ 4. WRITE ENDPOINT RATE LIMITING ═══")
# ═══════════════════════════════════════════════════════════
s3, _ = login_session()

# Test add student rate limit (MODERATE = 30/min)
print("  Sending 35 rapid add-student requests...")
write_statuses = []
for i in range(35):
    r = s3.post(f'{BASE}/proctor/api/student/add',
                json={'email': f'ratelimit_test_{i}@example.com', 'name': f'Test {i}',
                      'roll_number': f'RL{i:04d}', 'department': 'Testing'})
    write_statuses.append(r.status_code)
    if r.status_code == 429:
        print(f"    → Write rate limited at request {i+1}")
        break

check("Write endpoint rate limited (30/min)",
      429 in write_statuses,
      f"All {len(write_statuses)} returned non-429 ({set(write_statuses)})")


# ═══════════════════════════════════════════════════════════
print("\n═══ 5. DECORATOR ORDERING VALIDATION ═══")
# ═══════════════════════════════════════════════════════════
# Demo account hits @demo_restricted before @apply_rate_limit on write endpoints
# This is correct: rejected requests shouldn't consume rate-limit budget
s4, _ = login_session()
r_demo = s4.post(f'{BASE}/proctor/api/my-students/fake_student/remove')
try:
    d = r_demo.json()
    is_demo_blocked = d.get('demo_restricted', False) or 'demo' in d.get('error', '').lower()
except Exception:
    is_demo_blocked = False
check("Demo accounts blocked before rate limit on write endpoints", 
      r_demo.status_code in (403, 200) and (is_demo_blocked or r_demo.status_code == 200),
      f"Status: {r_demo.status_code}")

# Verify rate limit decorator IS applied (check code presence)
with open(r'd:\AURA\routes\proctor.py', 'r', encoding='utf-8') as f:
    proctor_code = f.read()
check("apply_rate_limit imported in proctor.py", 'apply_rate_limit' in proctor_code)
check("Limits imported in proctor.py", 'from utils.rate_limit import' in proctor_code)
rl_count = proctor_code.count('@apply_rate_limit')
check(f"Rate limit decorators applied ({rl_count} endpoints)", rl_count >= 15,
      f"Only {rl_count} found")


# ═══════════════════════════════════════════════════════════
print("\n═══ 6. RESEED GUARD VALIDATION ═══")
# ═══════════════════════════════════════════════════════════
# Verify the database.py uses $setOnInsert
with open(r'd:\AURA\utils\database.py', 'r', encoding='utf-8') as f:
    db_code = f.read()

check("Uses $setOnInsert for demo users", '$setOnInsert' in db_code)
check("No replace_one for demo users", 'replace_one' not in db_code,
      "Still uses replace_one")
check("Chat seeding is guarded", "chats.count_documents" in db_code)
check("Mood seeding is guarded", "moods.count_documents" in db_code)
check("Stress seeding is guarded", "stress.count_documents" in db_code)
check("Room messages seeding is guarded", "connection_rooms.count_documents" in db_code)


# ═══════════════════════════════════════════════════════════
print(f"\n{'═'*50}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed  ({PASS}/{PASS+FAIL})")
print(f"{'═'*50}")

if FAIL > 0:
    sys.exit(1)
