"""
TEST: Crisis Detection & Alert System
"""

from app import app
from utils.crisis_detection import detect_crisis, create_crisis_alert
from utils.alerts import send_crisis_alert

with app.app_context():
    print("=" * 80)
    print("CRISIS DETECTION SYSTEM TEST")
    print("=" * 80)
    print()

    # Test messages
    test_messages = [
        ("Normal message", "hey how are you today"),
        ("Moderate risk", "i'm feeling really sad and alone, nobody cares"),
        ("High risk", "i want to die, i can't take it anymore, i should kill myself"),
        ("CRITICAL", "i want to kill myself right now"),
        ("Threat", "i will hurt you when i see you"),
    ]

    print("[TEST 1] Crisis Detection - Keyword Analysis")
    print()

    for label, message in test_messages:
        is_crisis, risk_level = detect_crisis(message)
        print(f"Message: {label}")
        print(f"  Text: \"{message}\"")
        print(f"  Crisis Detected: {is_crisis}")
        print(f"  Risk Level: {risk_level}")
        print()

    print("=" * 80)
    print("[TEST 2] Send Crisis Alert - Real Test")
    print()

    test_email = "test.student+stress@gmail.com"
    test_name = "Test Student"
    test_message = "i want to kill myself, i can't do this anymore"

    print(f"Student: {test_name} ({test_email})")
    print(f"Message: \"{test_message}\"")
    print()

    # Detect crisis
    is_crisis, risk_level = detect_crisis(test_message)
    print(f"Crisis Detected: {is_crisis}")
    print(f"Risk Level: {risk_level}")
    print()

    if is_crisis:
        print("[ACTION] Sending CRITICAL alerts...")
        print()

        result = send_crisis_alert(test_email, test_name, test_message, risk_level)

        print(f"Result: {result['message']}")
        print(f"Proctor Email Sent: {result['proctor_sent']}")
        print(f"Parent Email Sent: {result['parent_sent']}")
        print(f"Overall Success: {result['success']}")

        if result['errors']:
            print(f"Errors: {result['errors']}")

        print()
        print("=" * 80)
        if result['success']:
            print("[SUCCESS] CRISIS ALERTS SENT!")
            print()
            print("Proctor & Parent notified immediately with:")
            print("  - Full message content")
            print("  - Student contact info")
            print("  - Risk level")
            print("  - Action items")
            print()
            print("Check email: abhishekprathipati07@gmail.com")
        else:
            print("[ERROR] Crisis alerts may not have been sent")

    print("=" * 80)
