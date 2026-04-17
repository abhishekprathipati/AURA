"""Minimal direct SMTP test — no Flask app context needed."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets

# From .env
SMTP_SERVER   = 'smtp.gmail.com'
SMTP_PORT     = 587
SENDER_EMAIL  = 'abhishekprathipati07@gmail.com'
SENDER_PASS   = 'huihqbspdfirmiem'

PARENT_EMAIL  = 'abhishekprathipati07@gmail.com'
STUDENT_NAME  = 'Sivasri'
STUDENT_EMAIL = 'sivasrivangapandu@gmail.com'

token = secrets.token_urlsafe(32)
base_url = 'https://aura-wellness.onrender.com'
verification_url = f"{base_url}/api/student/parent/verify?token={token}&email={PARENT_EMAIL}"

subject = "Verify Your Email - AURA Student Wellness Alerts"
body = f"""Hello,

{STUDENT_NAME} ({STUDENT_EMAIL}) has added you as a parent contact in AURA.

Click the link below within 7 days to confirm:

{verification_url}

Once verified you will receive:
  - STRESS ALERTS when stress score exceeds 70/100
  - CRISIS ALERTS with Indian helplines (iCall 9152987821, Vandrevala 9999 666 555)

If you did not expect this, simply ignore this email.

---
AURA Student Wellness System
"""

msg = MIMEMultipart()
msg['From']    = SENDER_EMAIL
msg['To']      = PARENT_EMAIL
msg['Subject'] = subject
msg.attach(MIMEText(body, 'plain'))

print("Connecting to smtp.gmail.com:587...")
try:
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.sendmail(SENDER_EMAIL, PARENT_EMAIL, msg.as_string())
    print("SUCCESS! Verification email sent to " + PARENT_EMAIL)
    print("Token: " + token[:20] + "...")
except Exception as e:
    print("FAILED: " + str(e))
