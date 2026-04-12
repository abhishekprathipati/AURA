import smtplib
import os
from dotenv import load_dotenv
from flask_mail import Message
from app import app, mail

load_dotenv()

# Enable SMTP debugging
smtplib.SMTP.debuglevel = 2

with app.app_context():
    print("=== ATTEMPTING EMAIL WITH SMTP DEBUG ===\n")

    msg = Message(
        subject="AURA Alert: High Stress (99) - TESTING",
        recipients=["abhishekprathipati07@gmail.com"],
        body="This is a test of AURA alerts with full SMTP debugging enabled."
    )

    try:
        mail.send(msg)
        print("\n[SUCCESS] Message sent")
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
