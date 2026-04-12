"""
TEST: Verify Alerts Sent to Proctor & Parent (Simplified)
"""

from app import app
from utils.database import get_db
from utils.alerts import send_institutional_alert
from datetime import datetime

with app.app_context():
    db = get_db()

    # Use existing student
    test_email = "test.student+stress@gmail.com"
    test_parent = "abhishekprathipati07@gmail.com"
    test_proctor = "proctor@aura.edu"

    print("=" * 70)
    print("ALERT SYSTEM TEST: Proctor & Parent Notifications")
    print("=" * 70)
    print()

    # Test 1: High stress alert
    print("[TEST 1] CRITICAL Stress Alert (score > 85)")
    print(f"  Student: {test_email}")
    print(f"  Proctor: {test_proctor}")
    print(f"  Parent: {test_parent}")
    print(f"  Stress Score: 95/100")
    print()

    result = send_institutional_alert(test_email, score=95)

    print(f"  Result: {result['message']}")
    print(f"  [Proctor Email Sent]: {result['proctor_sent']}")
    print(f"  [Parent Email Sent]: {result['parent_sent']}")
    print(f"  [Overall Success]: {result['success']}")
    if result['errors']:
        print(f"  Errors: {result['errors']}")
    print()

    # Test 2: Rising stress alert
    print("[TEST 2] HIGH Stress Alert (score > 70)")
    print(f"  Stress Score: 78/100")
    print()

    result2 = send_institutional_alert(test_email, score=78)

    print(f"  Result: {result2['message']}")
    print(f"  [Proctor Email Sent]: {result2['proctor_sent']}")
    print(f"  [Parent Email Sent]: {result2['parent_sent']}")
    print(f"  [Overall Success]: {result2['success']}")
    print()

    # Test 3: Check alerts in database
    print("[TEST 3] Alerts Logged in Database")
    alerts_coll = list(db['alerts'].find({'student_email': test_email}).sort('created_at', -1).limit(5))

    print(f"  Total alerts for this student: {len(alerts_coll)}")
    for i, alert in enumerate(alerts_coll[:2], 1):
        print(f"\n  Alert #{i}:")
        print(f"    Score: {alert.get('score')}/100")
        print(f"    Proctor Notified: {alert.get('proctor_sent')}")
        print(f"    Parent Notified: {alert.get('parent_sent')}")
        print(f"    Status: {alert.get('status')}")
        print(f"    Created: {alert.get('created_at')}")

    print()
    print("=" * 70)
    if result['success'] and result2['success']:
        print("[SUCCESS] ALERTS SYSTEM WORKING!")
        print()
        print("When student stress is HIGH:")
        print("  -> Proctor gets EMAIL alert")
        print("  -> Parent gets EMAIL alert")
        print("  -> Alert logged in DATABASE")
        print()
        print("Check your email: abhishekprathipati07@gmail.com")
    else:
        print("[WARNING] Check email delivery settings")
    print("=" * 70)
