"""Direct test of parent verification email sending."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from aura.utils.database import get_db
from aura.utils.parent_verification import (
    create_parent_verification_record,
    send_parent_verification_email
)

def test_verification_email():
    app = create_app()
    with app.app_context():
        db = get_db()
        
        # Test with Sivasri's account
        student_email = 'sivasrivangapandu@gmail.com'
        parent_email  = 'abhishekprathipati07@gmail.com'
        parent_name   = 'Rama Rao'
        student_name  = 'Sivasri'

        print(f"\n1. Creating verification record for {student_email} → {parent_email}...")
        verification = create_parent_verification_record(db, student_email, parent_email, parent_name)
        print(f"   Token created: {verification['token'][:20]}...")
        print(f"   Expires at   : {verification['expires_at']}")

        # Build the correct URL (production Render URL)
        base_url = 'https://aura-wellness.onrender.com'
        verification_url = f"{base_url}/api/student/parent/verify?token={verification['token']}&email={parent_email}"
        print(f"\n2. Verification URL: {verification_url}")

        print(f"\n3. Sending verification email to {parent_email}...")
        mail_ext = app.extensions.get('mail')
        if not mail_ext:
            print("   ERROR: Flask-Mail extension not found!")
            return

        sent = send_parent_verification_email(
            mail_ext,
            student_name,
            student_email,
            parent_email,
            verification_url
        )

        if sent:
            print(f"   SUCCESS: Verification email sent to {parent_email} ✅")
        else:
            print(f"   FAILED: Email could not be sent ❌")

if __name__ == '__main__':
    test_verification_email()
