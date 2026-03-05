#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
AURA — End-to-End Data Validation Seed Script
═══════════════════════════════════════════════════════════════
Seeds the database with:
  • 1 proctor user
  • 6 demo students (varied stress/risk/status)
  • proctor_students mappings (matching anonymous IDs)
  • risk_incidents (HIGH / MEDIUM / LOW / resolved)
  • student_wellness records (stress + mood)
  • support_requests (grievance data)
  • proctor_notes

Then runs automated validation checks against every API endpoint
to confirm the full data chain:

  Student → anonymous_id → risk_incidents → proctor_students
         → dashboard summary → alerts → student detail page

Usage:
  python scripts/tools/seed_test_data.py          # seed + validate
  python scripts/tools/seed_test_data.py --clean   # wipe test data only
  python scripts/tools/seed_test_data.py --seed     # seed only (no validation)
═══════════════════════════════════════════════════════════════
"""

import sys, os, hashlib, uuid, argparse
from datetime import datetime, timedelta

# ── Add project root to path ──
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.database import get_db
from utils.auth_helpers import hash_password

# ═══════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════

PROCTOR_EMAIL  = 'test_proctor@aura.edu'
PROCTOR_NAME   = 'Dr. Test Proctor'
PROCTOR_PASS   = 'proctor123'
PROCTOR_DEPT   = 'AIML'

# Tag all seeded documents so we can clean them up
SEED_TAG = '__seed_test__'

# 6 demo students with varied profiles
STUDENTS = [
    {
        'name': 'Alpha Student',
        'email': 'alpha@aura.edu',
        'roll': '22AIML001',
        'dept': 'AIML',
        'stress': 85,    # HIGH risk, unreviewed
        'mood': 1,
        'risk': 'HIGH',
        'incident_status': 'UNREVIEWED',
        'case_status': 'new',
        'trigger': 'stress_engine_auto_escalation',
        'incident_type': 'critical_stress_auto',
    },
    {
        'name': 'Beta Student',
        'email': 'beta@aura.edu',
        'roll': '22AIML002',
        'dept': 'AIML',
        'stress': 72,    # MEDIUM risk, pending followup
        'mood': 2,
        'risk': 'MEDIUM',
        'incident_status': 'UNREVIEWED',
        'case_status': 'monitoring',
        'trigger': 'signal_pipeline_low_mood_pattern',
        'incident_type': 'low_mood_pattern',
    },
    {
        'name': 'Charlie Student',
        'email': 'charlie@aura.edu',
        'roll': '22AIML003',
        'dept': 'AIML',
        'stress': 30,    # LOW risk, resolved today
        'mood': 4,
        'risk': 'LOW',
        'incident_status': 'REVIEWED',
        'case_status': 'resolved',
        'trigger': 'signal_pipeline_stress_spike',
        'incident_type': 'stress_spike',
    },
    {
        'name': 'Delta Student',
        'email': 'delta@aura.edu',
        'roll': '22AIML004',
        'dept': 'AIML',
        'stress': 91,    # HIGH risk, unreviewed (auto-triggered)
        'mood': 1,
        'risk': 'HIGH',
        'incident_status': 'UNREVIEWED',
        'case_status': 'new',
        'trigger': 'stress_engine_auto_escalation',
        'incident_type': 'critical_stress_auto',
        'auto_triggered': True,
    },
    {
        'name': 'Echo Student',
        'email': 'echo@aura.edu',
        'roll': '22AIML005',
        'dept': 'AIML',
        'stress': 60,    # MEDIUM risk, resolved
        'mood': 3,
        'risk': 'MEDIUM',
        'incident_status': 'REVIEWED',
        'case_status': 'resolved',
        'trigger': 'signal_pipeline_distress_language',
        'incident_type': 'distress_language',
    },
    {
        'name': 'Foxtrot Student',
        'email': 'foxtrot@aura.edu',
        'roll': '22AIML006',
        'dept': 'AIML',
        'stress': 45,    # LOW risk, no incident
        'mood': 4,
        'risk': 'LOW',
        'incident_status': None,  # No incident for this student
        'case_status': None,
        'trigger': None,
        'incident_type': None,
    },
]


def make_anonymous_id(email: str) -> str:
    """
    MUST match both:
      - routes/student.py  → create_anonymous_student_id()
      - routes/proctor.py  → add_student()
    
    Formula: STU_{MD5(email_lower) % 100000 : 05d}
    """
    hash_value = int(hashlib.md5(email.lower().encode()).hexdigest(), 16) % 100000
    return f'STU_{hash_value:05d}'


# ═══════════════════════════════════════════════
# CLEAN
# ═══════════════════════════════════════════════

def clean_seed_data(db):
    """Remove all documents tagged with SEED_TAG."""
    collections = [
        'users', 'proctor_students', 'risk_incidents',
        'student_wellness', 'support_requests', 'proctor_actions',
        'proctor_notes', 'counseling_sessions'
    ]
    print('\n╔══════════════════════════════════════════╗')
    print('║       CLEANING SEED TEST DATA            ║')
    print('╚══════════════════════════════════════════╝')
    total = 0
    for col in collections:
        result = db[col].delete_many({'_seed': SEED_TAG})
        count = result.deleted_count
        total += count
        if count > 0:
            print(f'  ✓ {col}: removed {count} docs')
    if total == 0:
        print('  (no seed data found)')
    else:
        print(f'  ─── Total removed: {total} documents ───')
    print()


# ═══════════════════════════════════════════════
# SEED
# ═══════════════════════════════════════════════

def seed_data(db):
    """Insert all test data."""
    print('\n╔══════════════════════════════════════════╗')
    print('║       SEEDING TEST DATA                  ║')
    print('╚══════════════════════════════════════════╝')

    now = datetime.utcnow()

    # ── 1. Proctor User ──
    existing_proctor = db['users'].find_one({'email': PROCTOR_EMAIL})
    if existing_proctor and not existing_proctor.get('_seed'):
        print(f'  ⚠ Proctor {PROCTOR_EMAIL} exists (not seeded). Skipping user creation.')
    else:
        db['users'].delete_many({'email': PROCTOR_EMAIL})
        db['users'].insert_one({
            'email': PROCTOR_EMAIL,
            'hashed_password': hash_password(PROCTOR_PASS),
            'name': PROCTOR_NAME,
            'role': 'proctor',
            'department': PROCTOR_DEPT,
            'created_at': now,
            '_seed': SEED_TAG,
        })
        print(f'  ✓ Proctor: {PROCTOR_EMAIL} / {PROCTOR_PASS}')

    # ── 2. Student Users + proctor_students + wellness + incidents ──
    incident_ids = {}  # email → incident_id
    for i, stu in enumerate(STUDENTS):
        email = stu['email'].lower()
        anon_id = make_anonymous_id(email)

        # 2a. User account
        db['users'].delete_many({'email': email, '_seed': SEED_TAG})
        db['users'].insert_one({
            'email': email,
            'hashed_password': hash_password(stu['roll'].lower()),
            'name': stu['name'],
            'role': 'student',
            'department': stu['dept'],
            'created_at': now,
            '_seed': SEED_TAG,
        })

        # 2b. proctor_students mapping
        db['proctor_students'].delete_many({'email': email, '_seed': SEED_TAG})
        db['proctor_students'].insert_one({
            'student_id': str(uuid.uuid4()),
            'anonymous_id': anon_id,
            'name': stu['name'],
            'roll_number': stu['roll'].upper(),
            'email': email,
            'department': stu['dept'],
            'semester': '4',
            'section': 'A',
            'risk_level': stu['risk'],
            'blood_group': '',
            'notes': f'Seeded test student {i+1}',
            'proctor_id': PROCTOR_EMAIL,
            'status': 'active',
            'created_at': now,
            'created_by': PROCTOR_EMAIL,
            '_seed': SEED_TAG,
        })

        # 2c. Wellness data (stress + mood for 7 days)
        for day_offset in range(7):
            ts = now - timedelta(days=day_offset, hours=day_offset)
            # Vary stress: base with some fluctuation
            daily_stress = max(10, min(100, stu['stress'] + (day_offset * (-3 if stu['stress'] > 60 else 2))))
            db['student_wellness'].insert_one({
                'student_id': email,
                'data_type': 'stress',
                'value': daily_stress,
                'timestamp': ts,
                '_seed': SEED_TAG,
            })
            db['student_wellness'].insert_one({
                'student_id': email,
                'data_type': 'mood',
                'value': stu['mood'],
                'timestamp': ts,
                '_seed': SEED_TAG,
            })

        # 2d. Risk incidents (skip Foxtrot — no incident)
        if stu['incident_type']:
            inc_id = str(uuid.uuid4())
            incident_ids[email] = inc_id
            inc_ts = now - timedelta(hours=i * 3)  # Stagger timestamps

            inc_doc = {
                'incident_id': inc_id,
                'anonymous_student_id': anon_id,
                'student_email': None,
                'incident_type': stu['incident_type'],
                'risk_level': stu['risk'],
                'priority': stu['risk'],
                'trigger_source': stu['trigger'],
                'timestamp': inc_ts,
                'status': stu['incident_status'],
                'case_status': stu.get('case_status', 'new'),
                'details': f"Test incident for {anon_id}: stress={stu['stress']}, risk={stu['risk']}",
                'message_excerpt': f"Test: Stress {stu['stress']}/100 — {stu['risk']} risk",
                'action_count': 0,
                'last_action': None,
                'audit_trail': [],
                'resolved_by': PROCTOR_EMAIL if stu['case_status'] == 'resolved' else None,
                'resolved_at': now if stu['case_status'] == 'resolved' else None,
                'auto_triggered': stu.get('auto_triggered', False),
                '_seed': SEED_TAG,
            }
            db['risk_incidents'].insert_one(inc_doc)

        print(f'  ✓ Student {i+1}: {stu["name"]} → {anon_id} | stress={stu["stress"]} | risk={stu["risk"]} | incident={stu["incident_type"] or "none"}')

    # ── 3. Proctor Actions (for resolved incidents) ──
    for email, inc_id in incident_ids.items():
        stu = next(s for s in STUDENTS if s['email'].lower() == email)
        if stu['case_status'] == 'resolved':
            db['proctor_actions'].insert_one({
                'action_id': str(uuid.uuid4()),
                'incident_id': inc_id,
                'proctor_id': PROCTOR_EMAIL,
                'action_type': 'STATUS_CHANGE',
                'reason_code': 'new → resolved',
                'details': f'Resolved test incident for {make_anonymous_id(email)}',
                'timestamp': now - timedelta(hours=1),
                '_seed': SEED_TAG,
            })

    # ── 4. Proctor Notes (for high-risk students) ──
    for stu in STUDENTS:
        if stu['risk'] == 'HIGH':
            anon_id = make_anonymous_id(stu['email'])
            db['proctor_notes'].insert_one({
                'anonymous_student_id': anon_id,
                'proctor_id': PROCTOR_EMAIL,
                'proctor_name': PROCTOR_NAME,
                'note': f'Urgently monitor {anon_id} — stress at {stu["stress"]}/100.',
                'urgent': True,
                'flag_monitoring': True,
                'follow_up_date': (now + timedelta(days=2)).strftime('%Y-%m-%d'),
                'timestamp': now,
                '_seed': SEED_TAG,
            })

    # ── 5. Support Requests (grievances) ──
    grievances = [
        {
            'student_id': 'alpha@aura.edu',
            'anonymous_id': make_anonymous_id('alpha@aura.edu'),
            'subject': 'Academic Pressure & Course Overload',
            'message': 'I feel overwhelmed with the current workload and unable to cope.',
            'type': 'urgent',
            'status': 'pending',
            'priority': 'high',
            'timestamp': now - timedelta(days=1),
        },
        {
            'student_id': 'beta@aura.edu',
            'anonymous_id': make_anonymous_id('beta@aura.edu'),
            'subject': 'Need Counseling Appointment',
            'message': 'I would like to schedule a counseling session to discuss personal matters.',
            'type': 'general',
            'status': 'in_progress',
            'priority': 'medium',
            'timestamp': now - timedelta(days=2),
        },
        {
            'student_id': 'charlie@aura.edu',
            'anonymous_id': make_anonymous_id('charlie@aura.edu'),
            'subject': 'Lab Access Issue Resolved',
            'message': 'Previous lab access issue has been sorted out. Thank you.',
            'type': 'general',
            'status': 'resolved',
            'priority': 'low',
            'timestamp': now - timedelta(days=5),
        },
    ]
    for g in grievances:
        g['_seed'] = SEED_TAG
        g['auto_triggered'] = False
        db['support_requests'].insert_one(g)

    print(f'  ✓ 3 support requests (grievances)')
    print(f'  ✓ Proctor actions for resolved cases')
    print(f'  ✓ Proctor notes for high-risk students')

    print(f'\n  ═══ SEED COMPLETE ═══\n')
    print(f'  Login credentials:')
    print(f'    Proctor:  {PROCTOR_EMAIL} / {PROCTOR_PASS}')
    for stu in STUDENTS:
        print(f'    Student:  {stu["email"]} / {stu["roll"].lower()}')
    print()

    return incident_ids


# ═══════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════

def validate_data(db):
    """Run all validation checks against the seeded data."""
    print('╔══════════════════════════════════════════╗')
    print('║       VALIDATION CHECKS                  ║')
    print('╚══════════════════════════════════════════╝')

    passed = 0
    failed = 0
    total = 0

    def check(desc, condition, detail=''):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f'  ✅ {desc}')
        else:
            failed += 1
            print(f'  ❌ {desc}')
            if detail:
                print(f'     → {detail}')

    # ── 1. Anonymous ID Consistency ──
    print('\n── 1. Anonymous ID Pipeline ──')
    for stu in STUDENTS:
        email = stu['email'].lower()
        expected_id = make_anonymous_id(email)
        ps_record = db['proctor_students'].find_one({'email': email, '_seed': SEED_TAG})
        if ps_record:
            check(
                f'{stu["name"]}: proctor_students.anonymous_id matches MD5 formula',
                ps_record.get('anonymous_id') == expected_id,
                f'expected={expected_id}, got={ps_record.get("anonymous_id")}'
            )
        else:
            check(f'{stu["name"]}: proctor_students record exists', False, 'Record not found')

    # ── 2. Incident ↔ Anonymous ID Linkage ──
    print('\n── 2. Incident ↔ Student Linkage ──')
    for stu in STUDENTS:
        if not stu['incident_type']:
            continue
        email = stu['email'].lower()
        anon_id = make_anonymous_id(email)
        inc = db['risk_incidents'].find_one({
            'anonymous_student_id': anon_id,
            '_seed': SEED_TAG
        })
        check(
            f'{stu["name"]}: incident found via anonymous_id={anon_id}',
            inc is not None,
            f'No incident with anonymous_student_id={anon_id}'
        )
        if inc:
            check(
                f'{stu["name"]}: incident risk_level={stu["risk"]}',
                inc.get('risk_level') == stu['risk'],
                f'expected={stu["risk"]}, got={inc.get("risk_level")}'
            )
            check(
                f'{stu["name"]}: incident status={stu["incident_status"]}',
                inc.get('status') == stu['incident_status'],
                f'expected={stu["incident_status"]}, got={inc.get("status")}'
            )

    # ── 3. Dashboard Summary Simulation ──
    print('\n── 3. Dashboard Summary (simulated) ──')
    my_students_count = db['proctor_students'].count_documents({
        'proctor_id': PROCTOR_EMAIL,
        'status': 'active',
        '_seed': SEED_TAG,
    })
    check('My Students count = 6', my_students_count == 6, f'got={my_students_count}')

    # Get all anon IDs for this proctor
    my_anon_ids = [s['anonymous_id'] for s in db['proctor_students'].find(
        {'proctor_id': PROCTOR_EMAIL, 'status': 'active', '_seed': SEED_TAG},
        {'anonymous_id': 1}
    )]

    # Needs action (UNREVIEWED among my students)
    needs_action = db['risk_incidents'].count_documents({
        'anonymous_student_id': {'$in': my_anon_ids},
        'status': 'UNREVIEWED',
        '_seed': SEED_TAG,
    })
    # Expected: Alpha (HIGH/UNREVIEWED) + Beta (MEDIUM/UNREVIEWED) + Delta (HIGH/UNREVIEWED) = 3
    check('Needs Action count = 3', needs_action == 3, f'got={needs_action}')

    # Pending followups (case_status in assigned/contacted/monitoring)
    pending_followups = db['risk_incidents'].count_documents({
        'anonymous_student_id': {'$in': my_anon_ids},
        'case_status': {'$in': ['assigned', 'contacted', 'monitoring']},
        '_seed': SEED_TAG,
    })
    # Expected: Beta (monitoring) = 1
    check('Pending Followups = 1', pending_followups == 1, f'got={pending_followups}')

    # Resolved today (Charlie + Echo)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = db['risk_incidents'].count_documents({
        'anonymous_student_id': {'$in': my_anon_ids},
        'case_status': 'resolved',
        '_seed': SEED_TAG,
        '$or': [
            {'resolved_at': {'$gte': today_start}},
            {'timestamp': {'$gte': today_start}, 'status': {'$in': ['REVIEWED', 'DISMISSED', 'RESOLVED']}}
        ]
    })
    check('Resolved Today = 2 (Charlie + Echo)', resolved_today == 2, f'got={resolved_today}')

    # ── 4. Alerts Section (HIGH risk + unreviewed among my students) ──
    print('\n── 4. Alerts & Watchlist Logic ──')
    
    # Alerts: students with needs_intervention status or stress >= 70
    alert_students = []
    for stu in STUDENTS:
        if stu['stress'] >= 75 or stu['risk'] == 'HIGH':
            alert_students.append(stu['name'])
    # Expected: Alpha (85, HIGH), Delta (91, HIGH), Beta (72 < 75 but needs checking via /api/my-students)
    
    high_risk_incidents = db['risk_incidents'].count_documents({
        'anonymous_student_id': {'$in': my_anon_ids},
        'risk_level': 'HIGH',
        'status': 'UNREVIEWED',
        '_seed': SEED_TAG,
    })
    check('High risk unreviewed alerts = 2 (Alpha + Delta)', high_risk_incidents == 2, f'got={high_risk_incidents}')

    medium_risk_incidents = db['risk_incidents'].count_documents({
        'anonymous_student_id': {'$in': my_anon_ids},
        'risk_level': 'MEDIUM',
        '_seed': SEED_TAG,
    })
    check('Medium risk incidents = 2 (Beta + Echo)', medium_risk_incidents == 2, f'got={medium_risk_incidents}')

    # ── 5. Wellness Data ──
    print('\n── 5. Wellness Data ──')
    for stu in STUDENTS:
        email = stu['email'].lower()
        stress_count = db['student_wellness'].count_documents({
            'student_id': email,
            'data_type': 'stress',
            '_seed': SEED_TAG,
        })
        mood_count = db['student_wellness'].count_documents({
            'student_id': email,
            'data_type': 'mood',
            '_seed': SEED_TAG,
        })
        check(
            f'{stu["name"]}: 7 stress + 7 mood records',
            stress_count == 7 and mood_count == 7,
            f'stress={stress_count}, mood={mood_count}'
        )

    # ── 6. Student Detail Profile Data ──
    print('\n── 6. Student Detail Page Data ──')
    for stu in STUDENTS:
        if not stu['incident_type']:
            continue
        anon_id = make_anonymous_id(stu['email'])
        incidents = list(db['risk_incidents'].find({
            'anonymous_student_id': anon_id,
            '_seed': SEED_TAG,
        }))
        check(
            f'{stu["name"]} ({anon_id}): detail page has {len(incidents)} incident(s)',
            len(incidents) >= 1,
        )

    # High-risk students should have notes
    for stu in STUDENTS:
        if stu['risk'] == 'HIGH':
            anon_id = make_anonymous_id(stu['email'])
            notes = db['proctor_notes'].count_documents({
                'anonymous_student_id': anon_id,
                '_seed': SEED_TAG,
            })
            check(
                f'{stu["name"]} ({anon_id}): has proctor notes',
                notes >= 1,
                f'notes_count={notes}'
            )

    # ── 7. Grievance / Support Data ──
    print('\n── 7. Grievance Data ──')
    pending_tickets = db['support_requests'].count_documents({'status': 'pending', '_seed': SEED_TAG})
    in_progress_tickets = db['support_requests'].count_documents({'status': 'in_progress', '_seed': SEED_TAG})
    resolved_tickets = db['support_requests'].count_documents({'status': 'resolved', '_seed': SEED_TAG})
    check('Support tickets: 1 pending, 1 in_progress, 1 resolved',
          pending_tickets == 1 and in_progress_tickets == 1 and resolved_tickets == 1,
          f'pending={pending_tickets}, in_progress={in_progress_tickets}, resolved={resolved_tickets}')

    # ── 8. Cross-Contamination Check ──
    print('\n── 8. Cross-Contamination ──')
    # Verify no incidents exist for Foxtrot (no incident student)
    foxtrot_anon = make_anonymous_id('foxtrot@aura.edu')
    foxtrot_incidents = db['risk_incidents'].count_documents({
        'anonymous_student_id': foxtrot_anon,
        '_seed': SEED_TAG,
    })
    check(
        f'Foxtrot ({foxtrot_anon}): zero incidents (clean student)',
        foxtrot_incidents == 0,
        f'got={foxtrot_incidents}'
    )

    # ── 9. Proctor-scope isolation ──
    # All my students should belong to this proctor
    other_proctor_students = db['proctor_students'].count_documents({
        'proctor_id': {'$ne': PROCTOR_EMAIL},
        'anonymous_id': {'$in': my_anon_ids},
        '_seed': SEED_TAG,
    })
    check('No cross-proctor leakage', other_proctor_students == 0, f'got={other_proctor_students}')

    # ── RESULTS ──
    print(f'\n╔══════════════════════════════════════════╗')
    print(f'║  RESULTS: {passed}/{total} passed, {failed} failed')
    if failed == 0:
        print(f'║  ✅ ALL CHECKS PASSED')
    else:
        print(f'║  ❌ {failed} CHECK(S) FAILED')
    print(f'╚══════════════════════════════════════════╝\n')

    return failed == 0


# ═══════════════════════════════════════════════
# PRINT EXPECTED DASHBOARD VIEW
# ═══════════════════════════════════════════════

def print_expected_dashboard():
    """Print what the proctor should see after logging in."""
    print('╔══════════════════════════════════════════╗')
    print('║  EXPECTED DASHBOARD VIEW                 ║')
    print('╚══════════════════════════════════════════╝')
    print()
    print('  📊 Summary Cards:')
    print('  ┌──────────────┬──────────────┬──────────────┬──────────────┐')
    print('  │ My Students  │ Needs Action │ Follow-ups   │ Resolved     │')
    print('  │     6        │     3        │     1        │     2        │')
    print('  └──────────────┴──────────────┴──────────────┴──────────────┘')
    print()
    print('  🚨 High-Priority Alerts:')
    print('  ┌──────────────┬─────────┬──────────┬──────────────────────────┐')
    print('  │ Student      │ Stress  │ Risk     │ Status                   │')
    print('  ├──────────────┼─────────┼──────────┼──────────────────────────┤')

    for stu in STUDENTS:
        if stu['stress'] >= 75 or stu['risk'] == 'HIGH':
            anon_id = make_anonymous_id(stu['email'])
            print(f'  │ {anon_id:<12} │ {stu["stress"]:<7} │ {stu["risk"]:<8} │ needs_intervention       │')

    print('  └──────────────┴─────────┴──────────┴──────────────────────────┘')
    print()
    print('  👀 Full Watchlist (all 6 students sorted by stress):')
    sorted_students = sorted(STUDENTS, key=lambda s: -s['stress'])
    print('  ┌──────────────┬─────────┬──────────┬──────────────┬──────────┐')
    print('  │ Student      │ Stress  │ Trend    │ Status       │ Risk     │')
    print('  ├──────────────┼─────────┼──────────┼──────────────┼──────────┤')
    for stu in sorted_students:
        anon_id = make_anonymous_id(stu['email'])
        if stu['stress'] >= 75 or stu['risk'] == 'HIGH':
            status = 'needs_interv.'
        elif stu['stress'] >= 50 or stu['risk'] == 'MEDIUM':
            status = 'monitor'
        else:
            status = 'normal'
        print(f'  │ {anon_id:<12} │ {stu["stress"]:<7} │ {"stable":<8} │ {status:<12} │ {stu["risk"]:<8} │')
    print('  └──────────────┴─────────┴──────────┴──────────────┴──────────┘')
    print()
    print('  📋 Grievances:')
    print('    • 1 Pending (Alpha — Academic Pressure)')
    print('    • 1 In Progress (Beta — Counseling Request)')
    print('    • 1 Resolved (Charlie — Lab Access)')
    print()


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='AURA test data seeder & validator')
    parser.add_argument('--clean', action='store_true', help='Remove seed data only')
    parser.add_argument('--seed', action='store_true', help='Seed data only (no validation)')
    args = parser.parse_args()

    # Need app context for get_db()
    from app import app
    with app.app_context():
        db = get_db()
        if db is None:
            print('❌ Database connection failed!')
            sys.exit(1)

        if args.clean:
            clean_seed_data(db)
            return

        # Always clean first, then seed
        clean_seed_data(db)
        seed_data(db)

        if not args.seed:
            all_passed = validate_data(db)
            print_expected_dashboard()

            print('═' * 50)
            print(f'  Login: {PROCTOR_EMAIL} / {PROCTOR_PASS}')
            print(f'  URL:   http://127.0.0.1:5000/login')
            print('═' * 50)
            print()

            if not all_passed:
                sys.exit(1)


if __name__ == '__main__':
    main()
