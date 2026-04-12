"""
TEST 2: Parent Portal OTP Email
==============================
Tests OTP generation and email delivery for parent authentication.
"""

from app import app
from services.otp_service import OTPService
import time

TEST_PARENT_EMAIL = "abhishekprathipati07@gmail.com"
TEST_PHONE = "+919876543210"  # Format: +country_code + number

with app.app_context():
    print("=" * 60)
    print("TEST 2: PARENT PORTAL OTP EMAIL")
    print("=" * 60)
    print()

    print(f"[1] Sending OTP to email: {TEST_PARENT_EMAIL}")
    print(f"[2] Phone number: {TEST_PHONE}")
    print()

    try:
        # Send OTP via email
        success, message = OTPService.send_otp(
            phone=TEST_PHONE,
            delivery_method='email',
            email_address=TEST_PARENT_EMAIL
        )

        print(f"[Result] Success: {success}")
        print(f"[Message] {message}")
        print()

        if success or (isinstance(success, str) and len(str(success)) == 6):
            # If success=True, email was sent
            # If success=OTP_string, demo mode (OTP returned to client)
            demo_otp = None
            if isinstance(success, str):
                demo_otp = success
                print(f"[DEMO MODE] OTP for testing: {demo_otp}")
                print()

            print("[SUCCESS] [OK] OTP SENT")
            print("           Check email within 30 seconds for verification code...")
            print()

            if demo_otp:
                print(f"           To verify: use OTP = {demo_otp}")
                print()
                # Test verification
                print("[3] Testing OTP verification...")
                verify_success, verify_msg = OTPService.verify_otp(TEST_PHONE, demo_otp)
                print(f"[Verify Result] {verify_msg}")
                if verify_success:
                    print("[SUCCESS] [OK] OTP VERIFIED")
                else:
                    print("[ERROR] OTP verification failed")
        else:
            print("[WARNING] OTP sent but returned False")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print()
print("=" * 60)
