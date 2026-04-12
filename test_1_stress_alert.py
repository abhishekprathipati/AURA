"""
TEST 1: Student Stress Alerts
==============================
Creates a test student with high stress and triggers an alert email.
"""

from app import app
from utils.database import get_db
from services.stress_service import calculate_dynamic_stress
from datetime import datetime, timedelta
from models.mood import MoodModel
import time

TEST_STUDENT_EMAIL = "test.student+stress@gmail.com"

with app.app_context():
    db = get_db()
    print("=" * 60)
    print("TEST 1: STUDENT STRESS ALERT")
    print("=" * 60)
    print()

    # Step 1: Create test user if needed
    print("[1] Creating test student...")
    users = db['users']
    user = users.find_one({'email': TEST_STUDENT_EMAIL})
    if not user:
        users.insert_one({
            'email': TEST_STUDENT_EMAIL,
            'name': 'Stress Test Student',
            'role': 'student',
            'department': 'Engineering',
            'parent_email': 'abhishekprathipati07@gmail.com',  # Will receive alert
            'created_at': datetime.utcnow(),
        })
        print(f"   [OK] Created: {TEST_STUDENT_EMAIL}")
    else:
        print(f"   [OK] Found: {TEST_STUDENT_EMAIL}")
    print()

    # Step 2: Create MULTIPLE mood entries to build stress signal
    print("[2] Creating high-stress mood entries (upward trend over time)...")
    moods = db[MoodModel.collection_name]

    # Clear old test moods
    moods.delete_many({'user_email': TEST_STUDENT_EMAIL})

    # Create stress history: low -> high (establishes upward trend)
    # Days 1-3: low stress (first half average ~30)
    # Days 4-7: high stress (second half average ~85+)
    # This ensures: score>75, trend=up, and high volatility
    stress_history = [
        # First half (7 days ago to 3 days ago) - LOW stress
        ('calm', 2),
        ('normal', 3),
        ('okay', 4),
        # Second half (3 days ago to now) - HIGH stress with volatility
        ('stressed', 7),
        ('anxious', 8),
        ('anxious', 9),
        ('panic', 10),
        ('anxious', 9),  # Extra entry for volatility & data
    ]

    for i, (mood, intensity) in enumerate(stress_history):
        # Spread across 7 days
        days_ago = 7 - (i * 0.875)
        timestamp = datetime.utcnow() - timedelta(days=days_ago)
        moods.insert_one({
            'user_email': TEST_STUDENT_EMAIL,
            'mood': mood,
            'intensity': intensity,
            'created_at': timestamp,
        })
        print(f"   [OK] Added mood: {mood} (intensity {intensity})")
    print()

    # Step 3: Add student to proctor for alert routing
    print("[3] Setting up proctor assignment...")
    proctor_students = db['proctor_students']
    proctor_students.delete_many({'email': TEST_STUDENT_EMAIL})
    proctor_students.insert_one({
        'email': TEST_STUDENT_EMAIL,
        'proctor_id': 'proctor@example.com',  # Placeholder
        'status': 'active',
    })
    print("   [OK] Assigned to proctor queue")
    print()

    # Step 4: Calculate stress (should trigger alert)
    print("[4] Calculating stress and triggering alert...")
    print("   -> score > 90 should auto-alert OR score > 75 + trend + volatility")
    print()

    try:
        result = calculate_dynamic_stress(TEST_STUDENT_EMAIL, force_refresh=True)

        print(f"   Score: {result['score']}/100")
        print(f"   Label: {result['label']}")
        print(f"   Trend: {result['trend']}")
        print(f"   Signals:")
        for sig, val in result['signals'].items():
            print(f"     - {sig}: {val}")
        print()

        # Check if alert criteria met
        score = result['score']
        trend = result['trend']
        volatility = result['signals'].get('volatility', 0)

        alert_triggered = (score > 90) or (score > 75 and trend == 'up' and volatility > 55)

        if alert_triggered:
            print("[SUCCESS] [OK] STRESS ALERT SHOULD BE SENT")
            print(f"           Criteria met: score={score}, trend={trend}, volatility={volatility}")
            print()
            print("Check your email (abhishekprathipati07@gmail.com) for alert within 60 seconds...")
        else:
            print("[INFO] Alert NOT triggered (safe threshold)")
            print(f"       Criteria: score={score}, trend={trend}, volatility={volatility}")
            print(f"       Need: score>90 OR (score>75 AND trend=up AND volatility>55)")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print()
print("=" * 60)
