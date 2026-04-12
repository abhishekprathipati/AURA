import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

print(f"Testing SMTP Connection...")
print(f"Server: {MAIL_SERVER}")
print(f"Port: {MAIL_PORT}")
print(f"Username: {MAIL_USERNAME}")
print(f"Password length: {len(MAIL_PASSWORD) if MAIL_PASSWORD else 'NONE'}")
print(f"TLS: True")
print()

try:
    server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
    server.starttls()
    print("[OK] TLS connection successful")

    server.login(MAIL_USERNAME, MAIL_PASSWORD)
    print("[OK] Authentication successful!")

    server.quit()
    print("\n[SUCCESS] SMTP is working correctly!")

except smtplib.SMTPAuthenticationError as e:
    print(f"[ERROR] AUTHENTICATION FAILED: {e}")
    print("\nLikely causes:")
    print("1. Gmail password is wrong")
    print("2. Gmail App Password not generated (need 2-Step Verification)")
    print("3. Password format issue (check for spaces)")

except smtplib.SMTPException as e:
    print(f"[ERROR] SMTP ERROR: {e}")

except Exception as e:
    print(f"[ERROR] CONNECTION ERROR: {e}")
