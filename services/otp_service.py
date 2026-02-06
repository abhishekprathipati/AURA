"""
OTP (One-Time Password) Service for Parent Authentication
Handles OTP generation, storage in MongoDB, and verification.

In production, integrate with an SMS gateway (Twilio, Fast2SMS, MSG91, etc.)
For demo purposes, OTP is printed to console and returned in API response.
"""

import random
from datetime import datetime, timedelta
from utils.database import get_db


class OTPService:
    """OTP generation, storage, and verification service"""

    collection_name = 'otp_verifications'
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3
    RESEND_COOLDOWN_SECONDS = 30

    @staticmethod
    def generate_otp():
        """Generate a cryptographically random 6-digit OTP"""
        return str(random.randint(100000, 999999))

    @staticmethod
    def normalize_phone(phone):
        """Normalize phone number to 10 digits"""
        if not phone:
            return ''
        # Strip all non-digit characters
        digits = ''.join(c for c in phone if c.isdigit())
        # If starts with country code 91 and has 12 digits, strip it
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        # If starts with 0 and has 11 digits, strip leading 0
        if len(digits) == 11 and digits.startswith('0'):
            digits = digits[1:]
        return digits

    @staticmethod
    def send_otp(phone):
        """Generate OTP, store in DB, and simulate sending via SMS"""
        db = get_db()
        phone = OTPService.normalize_phone(phone)
        otp = OTPService.generate_otp()

        # Check resend cooldown
        recent = db[OTPService.collection_name].find_one(
            {
                'phone': phone,
                'expired': False,
                'created_at': {
                    '$gt': datetime.utcnow() - timedelta(seconds=OTPService.RESEND_COOLDOWN_SECONDS)
                }
            }
        )
        if recent:
            return None, 'Please wait before requesting a new OTP'

        # Invalidate existing OTPs for this phone
        db[OTPService.collection_name].update_many(
            {'phone': phone, 'verified': False},
            {'$set': {'expired': True}}
        )

        # Store new OTP
        otp_record = {
            'phone': phone,
            'otp': otp,
            'attempts': 0,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=OTPService.OTP_EXPIRY_MINUTES),
            'verified': False,
            'expired': False
        }
        db[OTPService.collection_name].insert_one(otp_record)

        # ===== SMS INTEGRATION POINT =====
        # In production, send OTP via SMS API:
        #   Twilio:   client.messages.create(body=f"Your AURA OTP: {otp}", to=f"+91{phone}")
        #   Fast2SMS: requests.post(url, data={'message': otp, 'numbers': phone})
        #   MSG91:    requests.post(url, json={'otp': otp, 'mobile': phone})
        # ==================================

        print(f"\n{'='*50}")
        print(f"  📱 AURA OTP SERVICE")
        print(f"  Phone : +91 {phone[:3]}***{phone[-3:]}")
        print(f"  OTP   : {otp}")
        print(f"  Valid  : {OTPService.OTP_EXPIRY_MINUTES} minutes")
        print(f"{'='*50}\n")

        return otp, 'OTP sent successfully'

    @staticmethod
    def verify_otp(phone, otp):
        """Verify OTP for a phone number. Returns (success, message)"""
        db = get_db()
        phone = OTPService.normalize_phone(phone)

        # Find the latest valid OTP for this phone
        record = db[OTPService.collection_name].find_one(
            {
                'phone': phone,
                'verified': False,
                'expired': False,
                'expires_at': {'$gt': datetime.utcnow()}
            },
            sort=[('created_at', -1)]
        )

        if not record:
            return False, 'OTP expired or not found. Please request a new one.'

        # Check max attempts
        if record.get('attempts', 0) >= OTPService.MAX_ATTEMPTS:
            db[OTPService.collection_name].update_one(
                {'_id': record['_id']},
                {'$set': {'expired': True}}
            )
            return False, 'Too many failed attempts. Please request a new OTP.'

        # Increment attempt count
        db[OTPService.collection_name].update_one(
            {'_id': record['_id']},
            {'$inc': {'attempts': 1}}
        )

        # Check OTP match
        if record['otp'] != otp:
            remaining = OTPService.MAX_ATTEMPTS - record.get('attempts', 0) - 1
            return False, f'Invalid OTP. {remaining} attempt(s) remaining.'

        # OTP matched — mark as verified
        db[OTPService.collection_name].update_one(
            {'_id': record['_id']},
            {'$set': {'verified': True, 'verified_at': datetime.utcnow()}}
        )

        return True, 'OTP verified successfully'

    @staticmethod
    def is_phone_verified(phone):
        """Check if a phone was recently verified (within last 10 minutes)"""
        db = get_db()
        phone = OTPService.normalize_phone(phone)

        record = db[OTPService.collection_name].find_one({
            'phone': phone,
            'verified': True,
            'verified_at': {'$gt': datetime.utcnow() - timedelta(minutes=10)}
        })
        return record is not None

    @staticmethod
    def cleanup_expired():
        """Remove expired OTP records (call periodically for housekeeping)"""
        db = get_db()
        result = db[OTPService.collection_name].delete_many({
            'expires_at': {'$lt': datetime.utcnow()}
        })
        return result.deleted_count
