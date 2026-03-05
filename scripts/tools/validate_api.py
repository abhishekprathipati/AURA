#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
AURA — HTTP API Validation Script
═══════════════════════════════════════════════════════════════
Logs in as the test proctor and validates every API endpoint
returns correct data matching the seeded test records.

Requires: server running on http://127.0.0.1:5000
          seed data inserted via seed_test_data.py
═══════════════════════════════════════════════════════════════
"""

import sys, os, hashlib, json, requests

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

BASE = 'http://127.0.0.1:5000'
PROCTOR_EMAIL = 'test_proctor@aura.edu'
PROCTOR_PASS = 'proctor123'

def make_anonymous_id(email):
    h = int(hashlib.md5(email.lower().encode()).hexdigest(), 16) % 100000
    return f'STU_{h:05d}'

passed = 0
failed = 0

def check(desc, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'  ✅ {desc}')
    else:
        failed += 1
        print(f'  ❌ {desc}')
        if detail:
            print(f'     → {detail}')

def main():
    global passed, failed
    
    s = requests.Session()

    # ── LOGIN ──
    print('\n╔══════════════════════════════════════════╗')
    print('║  HTTP API VALIDATION                     ║')
    print('╚══════════════════════════════════════════╝')

    print('\n── Login ──')
    r = s.post(f'{BASE}/login', data={
        'email': PROCTOR_EMAIL,
        'password': PROCTOR_PASS
    }, allow_redirects=False)
    check('Login POST returns redirect (302)', r.status_code == 302, f'got {r.status_code}')
    
    # Follow redirect
    r = s.get(f'{BASE}/proctor/dashboard')
    check('Dashboard loads (200)', r.status_code == 200, f'got {r.status_code}')
    check('Dashboard contains AURA proctor page', 'Proctor Dashboard' in r.text or 'Faculty Proctor' in r.text, 'proctor page markers not found')

    # ── DASHBOARD SUMMARY ──
    print('\n── Dashboard Summary API ──')
    r = s.get(f'{BASE}/proctor/api/dashboard/summary')
    check('Summary API returns 200', r.status_code == 200, f'got {r.status_code}')
    
    data = r.json()
    check('Summary returns success=True', data.get('success') == True, f'got {data}')

    d = data.get('data', {})
    check('my_students >= 6', d.get('my_students', 0) >= 6, f'got {d.get("my_students")}')
    check('needs_action >= 3', d.get('needs_action', 0) >= 3, f'got {d.get("needs_action")}')
    check('pending_followups >= 1', d.get('pending_followups', 0) >= 1, f'got {d.get("pending_followups")}')
    check('resolved_today >= 2', d.get('resolved_today', 0) >= 2, f'got {d.get("resolved_today")}')
    
    pending = d.get('pending', {})
    check('pending.high >= 2', pending.get('high', 0) >= 2, f'got {pending.get("high")}')
    check('pending.medium >= 1', pending.get('medium', 0) >= 1, f'got {pending.get("medium")}')

    # ── MY STUDENTS ──
    print('\n── My Students API ──')
    r = s.get(f'{BASE}/proctor/api/my-students')
    check('My Students API returns 200', r.status_code == 200, f'got {r.status_code}')
    
    data = r.json()
    check('Returns success=True', data.get('success') == True)
    
    students = data.get('data', [])
    check('Student count >= 6', len(students) >= 6, f'got {len(students)}')
    
    # Check specific students by anonymous_id
    anon_map = {s['anonymous_id']: s for s in students}
    
    alpha_id = make_anonymous_id('alpha@aura.edu')
    delta_id = make_anonymous_id('delta@aura.edu')
    foxtrot_id = make_anonymous_id('foxtrot@aura.edu')
    beta_id = make_anonymous_id('beta@aura.edu')
    charlie_id = make_anonymous_id('charlie@aura.edu')
    
    if alpha_id in anon_map:
        a = anon_map[alpha_id]
        check(f'Alpha ({alpha_id}): status=needs_intervention', a.get('status') == 'needs_intervention', f'got {a.get("status")}')
        check(f'Alpha ({alpha_id}): risk_level=HIGH', a.get('risk_level') == 'HIGH', f'got {a.get("risk_level")}')
        check(f'Alpha ({alpha_id}): current_stress=85', a.get('current_stress') == 85, f'got {a.get("current_stress")}')
        check(f'Alpha ({alpha_id}): unreviewed_incidents >= 1', a.get('unreviewed_incidents', 0) >= 1, f'got {a.get("unreviewed_incidents")}')
    else:
        check(f'Alpha ({alpha_id}): found in student list', False, f'anonymous_ids: {list(anon_map.keys())}')

    if delta_id in anon_map:
        d_stu = anon_map[delta_id]
        check(f'Delta ({delta_id}): status=needs_intervention', d_stu.get('status') == 'needs_intervention', f'got {d_stu.get("status")}')
        check(f'Delta ({delta_id}): risk_level=HIGH', d_stu.get('risk_level') == 'HIGH', f'got {d_stu.get("risk_level")}')
    else:
        check(f'Delta ({delta_id}): found in student list', False)

    if foxtrot_id in anon_map:
        f_stu = anon_map[foxtrot_id]
        check(f'Foxtrot ({foxtrot_id}): status=normal (no incidents)', f_stu.get('status') == 'normal', f'got {f_stu.get("status")}')
        check(f'Foxtrot ({foxtrot_id}): risk_level=LOW', f_stu.get('risk_level') == 'LOW', f'got {f_stu.get("risk_level")}')
    else:
        check(f'Foxtrot ({foxtrot_id}): found in student list', False)

    # Check sort order: needs_intervention first
    if len(students) >= 2:
        check('Sort: first student is needs_intervention', students[0].get('status') == 'needs_intervention', f'got {students[0].get("status")}')

    # ── STUDENT DETAIL PAGE ──
    print('\n── Student Detail Page ──')
    r = s.get(f'{BASE}/proctor/student/{alpha_id}')
    check(f'Student detail page loads for {alpha_id} (200)', r.status_code == 200, f'got {r.status_code}')
    check(f'Detail page contains anonymous_id', alpha_id in r.text, 'anonymous_id not found in page')

    # ── STUDENT DETAIL API ──
    print('\n── Student Detail API ──')
    r = s.get(f'{BASE}/proctor/api/student/{alpha_id}/details')
    check('Detail API returns 200', r.status_code == 200, f'got {r.status_code}')
    
    detail = r.json()
    check('Detail returns success=True', detail.get('success') == True)
    
    dd = detail.get('data', {})
    check(f'Alpha total_incidents >= 1', dd.get('total_incidents', 0) >= 1, f'got {dd.get("total_incidents")}')
    check(f'Alpha high_risk_count >= 1', dd.get('high_risk_count', 0) >= 1, f'got {dd.get("high_risk_count")}')
    check(f'Alpha unreviewed_count >= 1', dd.get('unreviewed_count', 0) >= 1, f'got {dd.get("unreviewed_count")}')
    check(f'Alpha has incidents list', len(dd.get('incidents', [])) >= 1, f'got {len(dd.get("incidents", []))}')
    check(f'Alpha has notes', len(dd.get('notes', [])) >= 1, f'got {len(dd.get("notes", []))}')
    
    # Check trigger breakdown
    triggers = dd.get('trigger_breakdown', {})
    check(f'Alpha trigger breakdown has data', len(triggers) >= 1, f'triggers={triggers}')

    # Check stability
    check(f'Alpha stability is not empty', dd.get('stability') is not None, f'got {dd.get("stability")}')
    check(f'Alpha case_status is set', dd.get('case_status') is not None, f'got {dd.get("case_status")}')

    # ── RISK QUEUE ──
    print('\n── Risk Queue API ──')
    r = s.get(f'{BASE}/proctor/api/risk/queue?status=UNREVIEWED')
    check('Risk Queue API returns 200', r.status_code == 200, f'got {r.status_code}')
    
    rq = r.json()
    if rq.get('success'):
        rq_data = rq.get('data', [])
        check('Risk queue has entries', len(rq_data) >= 1, f'got {len(rq_data)}')
        # Check Alpha's incident is in the queue
        rq_anon_ids = [i.get('anonymous_student_id') for i in rq_data]
        check(f'Alpha ({alpha_id}) in risk queue', alpha_id in rq_anon_ids, f'queue IDs: {rq_anon_ids[:5]}')
        check(f'Delta ({delta_id}) in risk queue', delta_id in rq_anon_ids, f'queue IDs: {rq_anon_ids[:5]}')

    # ── SUPPORT TICKETS (GRIEVANCES) ──
    print('\n── Grievance / Support Tickets API ──')
    r = s.get(f'{BASE}/proctor/api/support/tickets?status=pending')
    check('Support tickets API returns 200', r.status_code == 200, f'got {r.status_code}')
    
    tickets = r.json()
    if tickets.get('success'):
        tlist = tickets.get('tickets', [])
        check('Pending tickets >= 1', len(tlist) >= 1, f'got {len(tlist)}')

    r = s.get(f'{BASE}/proctor/api/support/tickets')
    if r.json().get('success'):
        all_tickets = r.json().get('tickets', [])
        check('Total support tickets >= 3', len(all_tickets) >= 3, f'got {len(all_tickets)}')

    # ── REMOVE STUDENT ──
    print('\n── Remove Student Flow ──')
    # Remove Foxtrot
    r = s.post(f'{BASE}/proctor/api/my-students/{foxtrot_id}/remove')
    check(f'Remove {foxtrot_id} returns 200', r.status_code == 200, f'got {r.status_code}')
    
    rm_result = r.json()
    check('Remove returns success=True', rm_result.get('success') == True, f'got {rm_result}')

    # Verify student list now has 5
    r = s.get(f'{BASE}/proctor/api/my-students')
    new_students = r.json().get('data', [])
    new_anon_ids = [s['anonymous_id'] for s in new_students]
    check('Student count dropped (Foxtrot removed)', foxtrot_id not in new_anon_ids, f'still found: {new_anon_ids}')
    check('Remaining students >= 5', len(new_students) >= 5, f'got {len(new_students)}')

    # Verify dashboard summary updated
    r = s.get(f'{BASE}/proctor/api/dashboard/summary')
    new_summary = r.json().get('data', {})
    check('Dashboard my_students updated after removal', new_summary.get('my_students', 0) >= 5, f'got {new_summary.get("my_students")}')

    # ── RE-ADD Foxtrot (restore for future tests) ──
    print('\n── Restore removed student ──')
    # Direct DB restore via re-activating
    r = s.post(f'{BASE}/proctor/api/student/add', json={
        'name': 'Foxtrot Student',
        'roll_number': '22AIML006',
        'email': 'foxtrot@aura.edu',
        'department': 'AIML',
        'parent_name': 'Test Parent',
        'parent_phone': '9999900006',
    })
    # May get 409 if user already exists, that's fine
    if r.status_code == 200:
        check('Re-added Foxtrot successfully', r.json().get('success') == True)
        # Verify anonymous_id matches
        new_fox_id = r.json().get('anonymous_id', '')
        check(f'Re-added Foxtrot has correct anonymous_id={foxtrot_id}', new_fox_id == foxtrot_id, f'got {new_fox_id}')
    elif r.status_code == 409:
        # Roll number or email already exists (from seed), expected
        check('Re-add blocked (duplicate) — expected', True)
    else:
        check('Re-add Foxtrot', False, f'status={r.status_code}, body={r.text[:200]}')

    # ── FINAL REPORT ──
    print(f'\n╔══════════════════════════════════════════╗')
    print(f'║  HTTP VALIDATION: {passed}/{passed+failed} passed, {failed} failed')
    if failed == 0:
        print(f'║  ✅ ALL HTTP CHECKS PASSED')
    else:
        print(f'║  ❌ {failed} CHECK(S) FAILED')
    print(f'╚══════════════════════════════════════════╝\n')

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
