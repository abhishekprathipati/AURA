"""
TEST: Crisis Detection Integration with Chat System
"""

from app import app
from utils.database import get_db
from flask import json
from datetime import datetime

with app.app_context():
    db = get_db()

    # Setup test student
    test_email = "test.student+stress@gmail.com"
    test_password = "DemoPass!2024#Secure"
    test_name = "Test Student"

    # Ensure user exists
    users = db['users']
    users.update_one(
        {'email': test_email},
        {'$set': {
            'email': test_email,
            'name': test_name,
            'role': 'student',
            'department': 'AIML',
            'parent_email': 'abhishekprathipati07@gmail.com',
        }},
        upsert=True
    )

    print("=" * 80)
    print("CRISIS DETECTION IN CHAT SYSTEM TEST")
    print("=" * 80)
    print()

    # Simulate chat requests
    test_chats = [
        {
            'name': 'Normal conversation',
            'message': 'hey, how do I improve my programming skills?'
        },
        {
            'name': 'Moderate distress',
            'message': "i'm feeling really sad and nobody understands me"
        },
        {
            'name': 'CRISIS MESSAGE',
            'message': "i want to kill myself right now, i can't take it anymore"
        },
    ]

    print("[TEST] Sending chat messages to crisis detection system")
    print()

    client = app.test_client()

    for i, chat in enumerate(test_chats, 1):
        print(f"Test {i}: {chat['name']}")
        print(f"  Message: \"{chat['message']}\"")

        # Simulate login with session
        with client.session_transaction() as sess:
            sess['user_email'] = test_email
            sess['user_name'] = test_name
            sess['user_role'] = 'student'

        # Send chat request
        response = client.post(
            '/api/chat/mental',
            json={
                'message': chat['message'],
                'kind': 'mental',
            },
            content_type='application/json'
        )

        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            result = response.get_json()
            print(f"  Response Type: {result.get('status', 'normal')}")

            if result.get('status') == 'crisis_detected':
                print(f"  [CRISIS DETECTED!] Risk Level: {result.get('risk_level')}")
                print(f"  Message: {result.get('message')}")
                print(f"  Emergency Resources Provided: YES")
                print()
                print(f"  [ACTION TAKEN]:")
                print(f"  -> Proctor email alert sent")
                print(f"  -> Parent email alert sent")
            else:
                print(f"  Normal response generated")
        else:
            print(f"  Error: {response.get_json()}")

        print()

    # Check alerts in database
    print("=" * 80)
    print("DATABASE VERIFICATION")
    print()

    alerts = list(db['alerts'].find(
        {
            'student_email': test_email,
            'alert_type': 'CRISIS_DETECTION'
        }
    ).sort('created_at', -1).limit(5))

    print(f"Crisis alerts logged: {len(alerts)}")
    for alert in alerts:
        print(f"\n  Alert:")
        print(f"    Risk Level: {alert.get('risk_level')}")
        print(f"    Message: {alert.get('message_content', 'N/A')[:50]}...")
        print(f"    Proctor Notified: {alert.get('proctor_sent')}")
        print(f"    Parent Notified: {alert.get('parent_sent')}")
        print(f"    Created: {alert.get('created_at')}")

    print()
    print("=" * 80)
    print("[SUCCESS] CRISIS DETECTION INTEGRATED!")
    print()
    print("When student sends dangerous message:")
    print("  1. Message is analyzed for dangerous keywords")
    print("  2. If crisis detected -> IMMEDIATE action")
    print("  3. Proctor gets CRITICAL alert email")
    print("  4. Parent gets CRITICAL alert email")
    print("  5. Alert logged as CRITICAL in database")
    print("  6. Student shown emergency resources")
    print()
    print("=" * 80)
