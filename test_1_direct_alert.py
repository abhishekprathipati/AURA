"""
TEST 1-DIRECT: Test Alert Sending (Bypassing Threshold)
======================================================
Tests the alert email sending directly with a forced score.
"""

from app import app
from utils.database import get_db
from utils.alerts import send_institutional_alert
from datetime import datetime

TEST_STUDENT_EMAIL = "test.student+stress@gmail.com"

with app.app_context():
    db = get_db()
    print("=" * 60)
    print("TEST 1-DIRECT: ALERT EMAIL SENDING")
    print("=" * 60)
    print()

    # Ensure student exists
    print("[1] Ensuring test student exists...")
    users = db['users']
    users.update_one(
        {'email': TEST_STUDENT_EMAIL},
        {'$set': {
            'email': TEST_STUDENT_EMAIL,
            'name': 'Stress Test Student',
            'role': 'student',
            'department': 'Engineering',
            'parent_email': 'abhishekprathipati07@gmail.com',
            'created_at': datetime.utcnow(),
        }},
        upsert=True
    )
    print(f"   [OK] Student ready: {TEST_STUDENT_EMAIL}")
    print()

    # Set a proctor for alert routing
    print("[2] Setting proctor for routing...")
    proctors = db['users'].find_one({'role': 'proctor'})
    proctor_email = proctors['email'] if proctors else 'no-proctor@example.com'

    proctor_students = db['proctor_students']
    proctor_students.update_one(
        {'email': TEST_STUDENT_EMAIL},
        {'$set': {
            'email': TEST_STUDENT_EMAIL,
            'proctor_id': proctor_email,
            'status': 'active',
        }},
        upsert=True
    )
    print(f"   [OK] Routed to: {proctor_email}")
    print()

    # Send alert directly
    print("[3] Sending alert with score=95...")
    try:
        send_institutional_alert(TEST_STUDENT_EMAIL, score=95)
        print("   [OK] send_institutional_alert() completed")
        print()
        print("[SUCCESS] ALERT EMAIL SENT")
        print("          Check email (abhishekprathipati07@gmail.com) for alert...")
        print()

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("=" * 60)
