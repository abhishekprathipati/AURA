"""
═══════════════════════════════════════════════════════════════
AURA — Audit Log Stress Test
═══════════════════════════════════════════════════════════════
Validates scalability of the proctor_activity_logs system.

Tests:
  Phase 1: Seed 5,000 audit log entries (varied actions, 50 students)
  Phase 2: Measure MongoDB query performance
  Phase 3: Measure API response latency
  Phase 4: Concurrent request simulation
  Phase 5: CSV export under load
  Phase 6: Cleanup

Run:
  python scripts/tools/stress_test_audit.py
  python scripts/tools/stress_test_audit.py --cleanup   # remove test data
═══════════════════════════════════════════════════════════════
"""
import sys
import os
import time
import random
import hashlib
import statistics
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# ── Configuration ─────────────────────────────────────────
NUM_LOG_ENTRIES   = 5_000
NUM_STUDENTS      = 50
NUM_PROCTORS      = 5
CONCURRENCY       = 10
API_LATENCY_RUNS  = 10
BASE_URL          = 'http://127.0.0.1:5000'
TAG               = '__stress_test__'   # metadata tag for cleanup

ACTIONS = [
    'ADD_STUDENT', 'REMOVE_STUDENT',
    'REVIEW_INCIDENT', 'DISMISS_INCIDENT', 'ESCALATE_INCIDENT',
    'CLOSE_INCIDENT', 'CONTACT_STUDENT', 'MONITOR_STUDENT',
    'CASE_STATUS_CHANGE', 'ASSIGN_COUNSELOR',
    'ADD_NOTE', 'UPDATE_TICKET',
    'LOGIN', 'LOGOUT', 'BULK_ACTION',
]

TARGETS = ['student', 'incident', 'ticket', 'note', 'session']
DEPARTMENTS = ['Computer Science', 'Mechanical', 'Electronics', 'Civil', 'Chemical']
COUNSELORS = ['Dr. Smith', 'Dr. Patel', 'Prof. Gupta', 'Dr. Rao']
STATUSES = ['new', 'reviewing', 'monitoring', 'resolved', 'escalated']

# ── Helpers ───────────────────────────────────────────────
def anon_id(email):
    h = int(hashlib.md5(email.lower().encode()).hexdigest(), 16) % 100000
    return f'STU_{h:05d}'


def random_log(i, proctors, students):
    """Generate a single realistic audit log document."""
    action = random.choice(ACTIONS)
    proctor = random.choice(proctors)
    student = random.choice(students)
    ts = datetime.utcnow() - timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )

    meta = {'__tag': TAG}
    target_type = 'student'
    target_id = anon_id(student)

    if action in ('REVIEW_INCIDENT', 'DISMISS_INCIDENT', 'ESCALATE_INCIDENT', 'CLOSE_INCIDENT'):
        target_type = 'incident'
        target_id = f'INC-{random.randint(1000, 9999)}'
        meta['risk_level'] = random.choice(['HIGH', 'MEDIUM', 'LOW'])
    elif action == 'UPDATE_TICKET':
        target_type = 'ticket'
        target_id = f'TKT-{random.randint(100, 999)}'
        meta['new_status'] = random.choice(STATUSES)
    elif action == 'ADD_NOTE':
        target_type = 'note'
        meta['urgent'] = random.choice([True, False])
    elif action == 'ASSIGN_COUNSELOR':
        meta['counselor_name'] = random.choice(COUNSELORS)
    elif action in ('LOGIN', 'LOGOUT'):
        target_type = 'session'
        target_id = proctor['email']
        meta['role'] = 'proctor'
    elif action in ('ADD_STUDENT', 'REMOVE_STUDENT'):
        meta['department'] = random.choice(DEPARTMENTS)
    elif action == 'CASE_STATUS_CHANGE':
        meta['old_status'] = random.choice(STATUSES)
        meta['new_status'] = random.choice(STATUSES)
    elif action == 'BULK_ACTION':
        meta['count'] = random.randint(2, 10)

    return {
        'proctor_email': proctor['email'],
        'proctor_name': proctor['name'],
        'action': action,
        'target_type': target_type,
        'target_id': target_id,
        'metadata': meta,
        'ip_address': f'192.168.1.{random.randint(1, 254)}',
        'user_agent': f'StressTest/{i}',
        'timestamp': ts,
    }


def fmt_ms(seconds):
    return f'{seconds * 1000:.1f}ms'


def fmt_stat(times):
    """Return min/avg/p95/max stats."""
    s = sorted(times)
    p95 = s[int(len(s) * 0.95)] if len(s) > 1 else s[0]
    return (f'min={fmt_ms(min(s))} avg={fmt_ms(statistics.mean(s))} '
            f'p95={fmt_ms(p95)} max={fmt_ms(max(s))}')


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════
def main():
    from aura.utils.database import get_db
    import requests

    # Handle --cleanup flag
    if '--cleanup' in sys.argv:
        db = get_db()
        result = db['proctor_activity_logs'].delete_many({'metadata.__tag': TAG})
        print(f'Cleaned up {result.deleted_count} stress-test entries.')
        return

    print('═' * 60)
    print('  AURA — Audit Log Stress Test')
    print('═' * 60)

    db = get_db()
    col = db['proctor_activity_logs']

    # Count existing entries
    existing = col.count_documents({})
    print(f'\n  Existing entries: {existing:,}')

    # Generate test data
    proctors = [
        {'email': f'proctor_stress_{i}@aura.edu', 'name': f'Dr. StressTest {i}'}
        for i in range(NUM_PROCTORS)
    ]
    students = [f'stress_student_{i}@example.com' for i in range(NUM_STUDENTS)]

    # ────────────────────────────────────────────────────
    # PHASE 1: Seed 5,000 log entries (batch insert)
    # ────────────────────────────────────────────────────
    print(f'\n── Phase 1: Seeding {NUM_LOG_ENTRIES:,} audit log entries ──')
    docs = [random_log(i, proctors, students) for i in range(NUM_LOG_ENTRIES)]

    t0 = time.perf_counter()
    # Insert in batches of 500 for efficiency
    batch_size = 500
    for start in range(0, len(docs), batch_size):
        batch = docs[start:start + batch_size]
        col.insert_many(batch, ordered=False)
    seed_time = time.perf_counter() - t0

    total = col.count_documents({})
    print(f'  Inserted: {NUM_LOG_ENTRIES:,} entries in {fmt_ms(seed_time)}')
    print(f'  Total entries now: {total:,}')
    print(f'  Throughput: {NUM_LOG_ENTRIES / seed_time:,.0f} inserts/sec')

    # ────────────────────────────────────────────────────
    # PHASE 2: MongoDB query performance
    # ────────────────────────────────────────────────────
    print(f'\n── Phase 2: MongoDB Query Performance ──')

    queries = [
        ('Full scan (30 days)',
         {'timestamp': {'$gte': datetime.utcnow() - timedelta(days=30)}}),
        ('Filter by action (ESCALATE_INCIDENT)',
         {'action': 'ESCALATE_INCIDENT', 'timestamp': {'$gte': datetime.utcnow() - timedelta(days=30)}}),
        ('Filter by proctor',
         {'proctor_email': proctors[0]['email'], 'timestamp': {'$gte': datetime.utcnow() - timedelta(days=30)}}),
        ('Filter by target_type (incident)',
         {'target_type': 'incident', 'timestamp': {'$gte': datetime.utcnow() - timedelta(days=30)}}),
    ]

    for label, q in queries:
        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            results = list(col.find(q, sort=[('timestamp', -1)]).limit(200))
            t1 = time.perf_counter()
            times.append(t1 - t0)
        count = col.count_documents(q)
        print(f'  {label}:')
        print(f'    matches={count:,}  →  {fmt_stat(times)}')

    # Aggregation performance
    print(f'\n  Aggregation (summary counts):')
    agg_times = []
    for _ in range(5):
        t0 = time.perf_counter()
        pipeline = [
            {'$match': {'timestamp': {'$gte': datetime.utcnow() - timedelta(days=30)}}},
            {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
        ]
        list(col.aggregate(pipeline))
        t1 = time.perf_counter()
        agg_times.append(t1 - t0)
    print(f'    {fmt_stat(agg_times)}')

    # ────────────────────────────────────────────────────
    # PHASE 3: API response latency
    # ────────────────────────────────────────────────────
    print(f'\n── Phase 3: API Response Latency ({API_LATENCY_RUNS} sequential) ──')

    s = requests.Session()
    r = s.post(f'{BASE_URL}/login',
               data={'email': 'proctor@aura.edu', 'password': 'password123'},
               allow_redirects=True)
    if 'proctor' not in r.url and 'dashboard' not in r.url:
        print('  ✗ Login failed — skipping API tests')
        print(f'    URL: {r.url}')
    else:
        # Warm up
        s.get(f'{BASE_URL}/proctor/api/activity-logs', params={'days': '1', 'limit': '10'})

        api_tests = [
            ('GET /activity-logs (7d, limit 200)',
             {'days': '7', 'limit': '200'}),
            ('GET /activity-logs (30d, limit 200)',
             {'days': '30', 'limit': '200'}),
            ('GET /activity-logs (30d, limit 1000)',
             {'days': '30', 'limit': '1000'}),
            ('GET /activity-logs (filtered by action)',
             {'days': '30', 'action': 'ESCALATE_INCIDENT', 'limit': '200'}),
        ]

        for label, params in api_tests:
            times = []
            for _ in range(API_LATENCY_RUNS):
                t0 = time.perf_counter()
                r = s.get(f'{BASE_URL}/proctor/api/activity-logs', params=params)
                t1 = time.perf_counter()
                times.append(t1 - t0)
                if r.status_code == 429:
                    print(f'  ⚠ Rate limited on {label} — reducing runs')
                    break
            if times:
                data = r.json() if r.status_code == 200 else {}
                count = data.get('count', '?')
                print(f'  {label}:')
                print(f'    returned={count}  →  {fmt_stat(times)}')

        # ────────────────────────────────────────────────
        # PHASE 4: Concurrent requests
        # ────────────────────────────────────────────────
        print(f'\n── Phase 4: Concurrent Requests ({CONCURRENCY} threads) ──')

        def make_request(i):
            """Each thread creates its own session."""
            sess = requests.Session()
            sess.post(f'{BASE_URL}/login',
                      data={'email': 'proctor@aura.edu', 'password': 'password123'},
                      allow_redirects=True)
            t0 = time.perf_counter()
            r = sess.get(f'{BASE_URL}/proctor/api/activity-logs',
                         params={'days': '7', 'limit': '50'})
            elapsed = time.perf_counter() - t0
            count = 0
            if r.status_code == 200:
                try:
                    count = r.json().get('count', 0)
                except Exception:
                    pass
            return {
                'thread': i,
                'status': r.status_code,
                'elapsed': elapsed,
                'count': count,
            }

        t0_conc = time.perf_counter()
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = [executor.submit(make_request, i) for i in range(CONCURRENCY)]
            results_conc = [f.result() for f in as_completed(futures)]
        total_conc = time.perf_counter() - t0_conc

        statuses = [r['status'] for r in results_conc]
        elapsed_list = [r['elapsed'] for r in results_conc]
        ok_count = statuses.count(200)
        rate_limited = statuses.count(429)

        print(f'  Total wall time: {fmt_ms(total_conc)}')
        print(f'  Responses: {ok_count} OK, {rate_limited} rate-limited, '
              f'{len(statuses) - ok_count - rate_limited} errors')
        if elapsed_list:
            print(f'  Latency: {fmt_stat(elapsed_list)}')

        # ────────────────────────────────────────────────
        # PHASE 5: CSV export under load
        # ────────────────────────────────────────────────
        print(f'\n── Phase 5: CSV Export Performance ──')

        # New session to avoid rate limits from phase 3/4
        s2 = requests.Session()
        s2.post(f'{BASE_URL}/login',
                data={'email': 'proctor@aura.edu', 'password': 'password123'},
                allow_redirects=True)

        csv_times = []
        for _ in range(5):
            t0 = time.perf_counter()
            r = s2.get(f'{BASE_URL}/proctor/api/activity-logs/export/csv',
                       params={'days': '30'})
            t1 = time.perf_counter()
            csv_times.append(t1 - t0)
            if r.status_code == 429:
                print('  ⚠ Rate limited on CSV export')
                break

        if csv_times:
            lines = r.text.strip().split('\n') if r.status_code == 200 else []
            print(f'  CSV rows: {len(lines):,} (incl. header)')
            print(f'  CSV size: {len(r.content):,} bytes')
            print(f'  Latency: {fmt_stat(csv_times)}')

    # ────────────────────────────────────────────────────
    # Summary
    # ────────────────────────────────────────────────────
    print(f'\n{"═" * 60}')
    print(f'  STRESS TEST COMPLETE')
    print(f'  Total entries in collection: {col.count_documents({}):,}')
    print(f'  Stress-test entries: {col.count_documents({"metadata.__tag": TAG}):,}')
    print(f'{"═" * 60}')
    print(f'\n  To clean up: python scripts/tools/stress_test_audit.py --cleanup')


if __name__ == '__main__':
    main()
