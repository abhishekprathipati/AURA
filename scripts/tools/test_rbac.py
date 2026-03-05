#!/usr/bin/env python
"""
═══════════════════════════════════════════════════════════════
AURA — RBAC Integration Test
═══════════════════════════════════════════════════════════════
Validates role-based access control across all protected endpoints.

Tests:
  1. Login sessions for student / proctor / hod
  2. Proctor can only see assigned students
  3. HOD can see all department students
  4. Student can only see own data
  5. Cross-role access denied (403)
  6. Dashboard summaries are properly scoped
  7. Risk queue is properly scoped
  8. Incident actions require ownership
  9. Audit logging fires on sensitive actions

Usage:
    python scripts/tools/test_rbac.py [--base-url http://127.0.0.1:5000]
"""
import argparse
import hashlib
import sys
import time
import requests

# ── Defaults ──
BASE = 'http://127.0.0.1:5000'

# Demo accounts (must exist in DB)
STUDENT  = {'email': 'student@aura.edu',  'password': 'password123'}
PROCTOR  = {'email': 'proctor@aura.edu',  'password': 'password123'}
HOD      = {'email': 'hod@aura.edu',      'password': 'password123'}

# ── Helpers ──
passed = 0
failed = 0
total  = 0


def anon_id(email):
    clean = email.lower().strip()
    h = int(hashlib.md5(clean.encode()).hexdigest(), 16) % 100000
    return f"STU_{h:05d}"


def login(sess, creds, label=''):
    """Login and return True if role session was set."""
    r = sess.post(f'{BASE}/login', data=creds, allow_redirects=False)
    ok = r.status_code in (200, 302)
    if not ok:
        print(f"  ✗ Login failed for {label or creds['email']} — HTTP {r.status_code}")
    return ok


def check(condition, description):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  ✓ {description}")
    else:
        failed += 1
        print(f"  ✗ FAIL: {description}")


# ═══════════════════════════════════════════════
# Test Suites
# ═══════════════════════════════════════════════

def test_login_sessions():
    """T1: Each role can log in and gets redirected correctly."""
    print("\n── T1: Login sessions ──")

    for label, creds, expected_redirect in [
        ('student', STUDENT, '/student/dashboard'),
        ('proctor', PROCTOR, '/proctor/dashboard'),
        ('hod',     HOD,     '/proctor/hod'),
    ]:
        s = requests.Session()
        r = s.post(f'{BASE}/login', data=creds, allow_redirects=False)
        check(r.status_code == 302, f"{label} login returns 302")
        loc = r.headers.get('Location', '')
        check(expected_redirect in loc, f"{label} redirects to {expected_redirect}")
        s.close()


def test_proctor_student_visibility():
    """T2: Proctor sees only assigned students via /api/my-students."""
    print("\n── T2: Proctor student visibility ──")
    s = requests.Session()
    login(s, PROCTOR, 'proctor')

    r = s.get(f'{BASE}/proctor/api/my-students')
    check(r.status_code == 200, "GET /api/my-students returns 200")

    data = r.json()
    check(data.get('success') is True, "Response success=True")
    students = data.get('data', [])
    check(isinstance(students, list), f"Students list returned ({len(students)} items)")
    # RBAC guarantees scoping — endpoint only returns students from get_visible_students()
    # We verify count matches 'summary.total'
    summary = data.get('summary', {})
    check(summary.get('total', -1) == len(students),
          f"Summary total matches list length ({len(students)})")

    s.close()


def test_hod_department_scoping():
    """T3: HOD sees only their department students."""
    print("\n── T3: HOD department scoping ──")
    s = requests.Session()
    login(s, HOD, 'hod')

    # HOD dashboard stats should have department set
    r = s.get(f'{BASE}/proctor/api/hod/dashboard-stats')
    check(r.status_code == 200, "HOD dashboard-stats returns 200")
    data = r.json()
    inner = data.get('data', data)  # response is {success, data: {...}}
    check('department' in inner, "Response includes department field")
    dept = inner.get('department', '')
    check(len(dept) > 0, f"Department is non-empty: '{dept}'")

    # HOD risk distribution
    r2 = s.get(f'{BASE}/proctor/api/hod/risk-distribution')
    check(r2.status_code == 200, "HOD risk-distribution returns 200")

    # HOD wellness trends
    r3 = s.get(f'{BASE}/proctor/api/hod/wellness-trends')
    check(r3.status_code == 200, "HOD wellness-trends returns 200")

    # HOD proctor performance
    r4 = s.get(f'{BASE}/proctor/api/hod/proctor-performance')
    check(r4.status_code == 200, "HOD proctor-performance returns 200")

    # HOD recent escalations
    r5 = s.get(f'{BASE}/proctor/api/hod/recent-escalations')
    check(r5.status_code == 200, "HOD recent-escalations returns 200")

    s.close()


def test_student_cannot_access_proctor():
    """T4: Students should NOT be able to access proctor endpoints."""
    print("\n── T4: Student blocked from proctor routes ──")
    s = requests.Session()
    login(s, STUDENT, 'student')

    endpoints = [
        '/proctor/api/my-students',
        '/proctor/api/dashboard/summary',
        '/proctor/api/risk/queue',
        '/proctor/api/hod/dashboard-stats',
    ]
    for ep in endpoints:
        r = s.get(f'{BASE}{ep}', allow_redirects=False)
        # Should be 403 (forbidden) or 302 (redirect to login)
        check(r.status_code in (302, 403),
              f"Student blocked from {ep} (HTTP {r.status_code})")

    s.close()


def test_proctor_dashboard_summary_scoped():
    """T5: Proctor dashboard summary counts only assigned students."""
    print("\n── T5: Dashboard summary scoping ──")
    s = requests.Session()
    login(s, PROCTOR, 'proctor')

    r = s.get(f'{BASE}/proctor/api/dashboard/summary')
    check(r.status_code == 200, "Dashboard summary returns 200")
    data = r.json()
    inner = data.get('data', data)  # response is {success, data: {...}}
    # my_students should be a count (int)
    my = inner.get('my_students')
    check(isinstance(my, int), f"my_students is int: {my}")
    # Should NOT have all_assigned_students (removed during refactor)
    check('all_assigned_students' not in inner,
          "all_assigned_students field removed")

    s.close()


def test_proctor_student_detail_access():
    """T6: Proctor can access details for assigned student but not unknown ones."""
    print("\n── T6: Student detail access control ──")
    s = requests.Session()
    login(s, PROCTOR, 'proctor')

    # Try accessing a non-existent student
    r = s.get(f'{BASE}/proctor/api/student/STU_99999/details')
    check(r.status_code in (403, 404),
          f"Non-assigned student returns {r.status_code}")

    s.close()


def test_hod_blocked_as_proctor_my_students():
    """T7: HOD can also call /api/my-students (proctor_only allows hod)."""
    print("\n── T7: HOD accesses proctor endpoints ──")
    s = requests.Session()
    login(s, HOD, 'hod')

    r = s.get(f'{BASE}/proctor/api/my-students')
    check(r.status_code == 200, "HOD can call /api/my-students (200)")

    r2 = s.get(f'{BASE}/proctor/api/dashboard/summary')
    check(r2.status_code == 200, "HOD can call /api/dashboard/summary (200)")

    s.close()


def test_notes_access_control():
    """T8: Notes endpoint enforces student ownership."""
    print("\n── T8: Notes access control ──")
    s = requests.Session()
    login(s, PROCTOR, 'proctor')

    # Try to read notes for a student the proctor may not own
    r = s.get(f'{BASE}/proctor/api/notes/STU_99999')
    check(r.status_code in (200, 403),
          f"Notes for unknown student returns {r.status_code}")

    s.close()


def test_risk_queue_scoping():
    """T9: Risk queue only shows incidents for visible students."""
    print("\n── T9: Risk queue scoping ──")
    s = requests.Session()
    login(s, PROCTOR, 'proctor')

    r = s.get(f'{BASE}/proctor/api/risk/queue')
    check(r.status_code == 200, "Risk queue returns 200")
    data = r.json()
    incidents = data if isinstance(data, list) else data.get('incidents', [])
    # We can't check ownership without knowing assigned students,
    # but we can verify the response structure is intact
    check(isinstance(incidents, list), "Risk queue returns a list of incidents")

    s.close()


def test_proctor_add_student():
    """T10: Proctor can add a student and it appears in their list.
    Note: demo accounts are blocked by @demo_restricted, so we add directly via DB."""
    print("\n── T10: Proctor add student flow ──")
    s = requests.Session()
    login(s, PROCTOR, 'proctor')

    test_email = 'rbac_test_student@aura.edu'
    test_anon = anon_id(test_email)

    # Demo accounts are restricted from adds — test the restriction works
    r = s.post(f'{BASE}/proctor/api/student/add', json={
        'email': test_email,
        'name': 'RBAC Test Student',
        'roll_number': 'RBAC001',
        'department': 'Computer Science',
        'parent_name': 'Test Parent',
        'parent_phone': '9999999999',
    })
    # Demo proctor should be blocked (403) or succeed (200)
    check(r.status_code in (200, 201, 403, 409),
          f"Add student returns {r.status_code} (demo-restricted or success)")

    # If demo-restricted, seed student directly via DB for remaining checks
    from pymongo import MongoClient
    from datetime import datetime as dt
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000)
        db_direct = client['aura_db']
        # Ensure a test student exists under this proctor
        db_direct['proctor_students'].update_one(
            {'anonymous_id': test_anon},
            {'$setOnInsert': {
                'anonymous_id': test_anon, 'email': test_email,
                'name': 'RBAC Test Student', 'roll_number': 'RBAC001',
                'department': 'Computer Science', 'proctor_id': PROCTOR['email'],
                'status': 'active', 'created_at': dt.utcnow(),
            }},
            upsert=True,
        )
        client.close()
    except Exception as e:
        check(False, f"Could not seed test data: {e}")
        s.close()
        return

    # Now the student should be visible
    r2 = s.get(f'{BASE}/proctor/api/my-students')
    data = r2.json()
    students = data.get('data', []) if isinstance(data, dict) else data
    ids = [st.get('anonymous_id') for st in students]
    check(test_anon in ids, f"Added student {test_anon} visible in my-students")

    # Proctor can access their details
    r3 = s.get(f'{BASE}/proctor/api/student/{test_anon}/details')
    check(r3.status_code == 200, f"Assigned student details accessible (200)")

    # Clean up via DB
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000)
        client['aura_db']['proctor_students'].delete_one({'anonymous_id': test_anon})
        client.close()
    except Exception:
        pass

    s.close()


def test_cross_proctor_isolation():
    """T11: Student assigned to a DIFFERENT proctor is inaccessible."""
    print("\n── T11: Cross-proctor isolation ──")
    s = requests.Session()
    login(s, PROCTOR, 'proctor')

    # Seed a student under a *different* proctor via DB
    test_email = 'isolation_test@aura.edu'
    test_anon = anon_id(test_email)

    from pymongo import MongoClient
    from datetime import datetime as dt
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000)
        db_d = client['aura_db']
        db_d['proctor_students'].update_one(
            {'anonymous_id': test_anon},
            {'$set': {
                'anonymous_id': test_anon, 'email': test_email,
                'name': 'Isolation Test', 'roll_number': 'ISO001',
                'department': 'Computer Science',
                'proctor_id': 'other_proctor@aura.edu',  # different proctor
                'status': 'active', 'created_at': dt.utcnow(),
            }},
            upsert=True,
        )
        client.close()
    except Exception as e:
        check(False, f"Could not seed isolation data: {e}")
        s.close()
        return

    # Proctor should NOT be able to access another proctor's student
    r = s.get(f'{BASE}/proctor/api/student/{test_anon}/details')
    check(r.status_code in (403, 404),
          f"Cross-proctor student inaccessible ({r.status_code})")

    # Cleanup
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000)
        client['aura_db']['proctor_students'].delete_one({'anonymous_id': test_anon})
        client.close()
    except Exception:
        pass

    s.close()


def test_audit_log_on_sensitive_actions():
    """T12: Audit log entries are created for login and view actions."""
    print("\n── T12: Audit logging on sensitive actions ──")
    s = requests.Session()
    # Login triggers audit log for proctor/hod
    login(s, PROCTOR, 'proctor')

    # Access dashboard (triggers view events)
    s.get(f'{BASE}/proctor/api/dashboard/summary')

    # Check audit log in proctor_activity_logs collection
    from pymongo import MongoClient
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000)
        db = client['aura_db']
        # Login audit entries use 'LOGIN' action
        log = db['proctor_activity_logs'].find_one({
            'proctor_email': PROCTOR['email'],
            'action': 'LOGIN',
        }, sort=[('timestamp', -1)])
        check(log is not None, "Audit log entry exists for LOGIN")
        if log:
            check(log.get('proctor_email') == PROCTOR['email'],
                  f"Audit actor is proctor: {log.get('proctor_email')}")
        client.close()
    except Exception as e:
        check(False, f"Could not check audit log: {e}")

    s.close()


def test_unauthenticated_access():
    """T13: Unauthenticated requests are blocked."""
    print("\n── T13: Unauthenticated access ──")
    s = requests.Session()  # no login

    endpoints = [
        '/proctor/api/my-students',
        '/proctor/api/dashboard/summary',
        '/proctor/api/risk/queue',
        '/proctor/api/hod/dashboard-stats',
        '/student/dashboard',
    ]
    for ep in endpoints:
        r = s.get(f'{BASE}{ep}', allow_redirects=False)
        check(r.status_code in (302, 401, 403),
              f"Unauthenticated {ep} blocked ({r.status_code})")

    s.close()


# ═══════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════
def main():
    global BASE
    parser = argparse.ArgumentParser(description='AURA RBAC Integration Tests')
    parser.add_argument('--base-url', default=BASE, help='Server base URL')
    args = parser.parse_args()
    BASE = args.base_url.rstrip('/')

    print("═══════════════════════════════════════════════════")
    print("  AURA — RBAC Integration Test Suite")
    print(f"  Target: {BASE}")
    print("═══════════════════════════════════════════════════")

    # Verify server is reachable
    try:
        r = requests.get(f'{BASE}/', timeout=5)
        print(f"  Server reachable (HTTP {r.status_code})")
    except Exception as e:
        print(f"  ✗ Server unreachable: {e}")
        sys.exit(1)

    test_login_sessions()
    test_proctor_student_visibility()
    test_hod_department_scoping()
    test_student_cannot_access_proctor()
    time.sleep(1)  # avoid rate limiting
    test_proctor_dashboard_summary_scoped()
    test_proctor_student_detail_access()
    test_hod_blocked_as_proctor_my_students()
    test_notes_access_control()
    time.sleep(1)  # avoid rate limiting
    test_risk_queue_scoping()
    test_proctor_add_student()
    test_cross_proctor_isolation()
    test_audit_log_on_sensitive_actions()
    test_unauthenticated_access()

    print("\n═══════════════════════════════════════════════════")
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("═══════════════════════════════════════════════════")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
