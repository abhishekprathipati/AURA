from flask_mail import Message
from app import mail, app

with app.app_context():
    msg = Message(
        subject="TEST MAIL FROM AURA",
        recipients=["abhishekprathipati07@gmail.com"],
        body="If you see this, mail is working ✅"
    )
    mail.send(msg)

print("Mail sent")
