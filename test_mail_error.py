from flask_mail import Message
from app import mail, app
import logging

# Enable Flask-Mail debug logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('flask_mail')
log.setLevel(logging.DEBUG)

with app.app_context():
    try:
        msg = Message(
            subject="TEST MAIL FROM AURA - ERROR HANDLING",
            recipients=["abhishekprathipati07@gmail.com"],
            body="If you see this, mail is working - with error handling"
        )

        print(f"Message created: {msg}")
        print(f"Subject: {msg.subject}")
        print(f"Recipients: {msg.recipients}")
        print(f"Sender: {msg.sender}")
        print()

        mail.send(msg)
        print("[SUCCESS] Mail sent without errors")

    except Exception as e:
        print(f"[ERROR] mail.send() failed: {type(e).__name__}")
        print(f"[ERROR] Details: {e}")
        import traceback
        traceback.print_exc()
