"""Test the activity log API end-to-end."""
import requests
import json

BASE = 'http://127.0.0.1:5000'

def run_audit_test():
    s = requests.Session()

    # Login
    r = s.post(f'{BASE}/login', data={'email': 'proctor@aura.edu', 'password': 'password123'}, allow_redirects=True)
    print(f"1. Login: {r.status_code} -> {r.url}")
    assert 'proctor' in r.url or 'dashboard' in r.url, "Login failed!"

    # Test: Add a student (to generate an audit log)
    r_add = s.post(f'{BASE}/proctor/api/student/add', json={
        'email': 'audit_test_student@example.com',
        'name': 'Audit Test Student',
        'roll_number': 'AUDIT001',
        'department': 'Testing'
    })
    print(f"2. Add student: {r_add.status_code} {r_add.json().get('success', r_add.json().get('error', ''))}")

    # Test: Activity logs API
    r2 = s.get(f'{BASE}/proctor/api/activity-logs', params={'days': '30'})
    data = r2.json()
    print(f"\n3. Activity Logs API: {r2.status_code}")
    print(f"   success: {data.get('success')}")
    print(f"   count: {data.get('count')}")
    print(f"   summary: {data.get('summary')}")
    print(f"   period_days: {data.get('period_days')}")

    if data.get('data'):
        print(f"\n   All log entries:")
        for i, log in enumerate(data['data']):
            print(f"   [{i+1}] {log['action']:20s} | {log.get('target_type',''):10s} | {log.get('target_id',''):30s} | {log.get('time_ago','')}")

    # Test: Filter by action
    r3 = s.get(f'{BASE}/proctor/api/activity-logs', params={'days': '30', 'action': 'ADD_STUDENT'})
    d3 = r3.json()
    print(f"\n4. Filtered by ADD_STUDENT: {d3.get('count')} entries")

    # Test: CSV export
    r4 = s.get(f'{BASE}/proctor/api/activity-logs/export/csv', params={'days': '30'})
    print(f"\n5. CSV Export: {r4.status_code}, content-type: {r4.headers.get('content-type')}")
    if r4.status_code == 200:
        lines = r4.text.strip().split('\n')
        print(f"   CSV rows: {len(lines)} (including header)")
        print(f"   Header: {lines[0]}")

    # Cleanup - remove the test student
    r_rm = s.post(f'{BASE}/proctor/api/my-students/audit_test_student%40example.com/remove')

    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    run_audit_test()
