from flask import current_app
from app import app, mail
from flask_mail import Message
import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')

with app.app_context():
    print("=== Testing Alert Email Code Path ===\n")

    # Exactly as in alerts.py
    mail_ext = current_app.extensions.get('mail')
    print(f"1. Mail extension retrieved: {mail_ext is not None}")

    if mail_ext:
        print(f"2. Mail object: {mail_ext}")

        msg = Message(
            subject="AURA Alert: High Stress (95) for Test Student",
            recipients=["abhishekprathipati07@gmail.com"],
            body="This is an automated alert from AURA.\n\nStudent: Test Student (test@example.com)\nStress score: 95\n\nPlease reach out and provide guidance."
        )

        print(f"3. Message created: OK")
        print(f"4. Subject: {msg.subject}")
        print(f"5. Recipients: {msg.recipients}")
        print(f"6. Body length: {len(msg.body)} chars")
        print()

        try:
            mail_ext.send(msg)
            print("[SUCCESS] Alert email sent (using extensions.get)")
        except Exception as e:
            print(f"[ERROR] Alert email failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ERROR] mail_ext is None!")
