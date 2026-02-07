"""
OTP (One-Time Password) Service for Parent Authentication
Handles OTP generation, storage in MongoDB, verification, and SMS delivery via Fast2SMS.
"""

import random
import requests
import logging
from datetime import datetime, timedelta
from utils.database import get_db
from config import Config

logger = logging.getLogger(__name__)


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
    def _send_sms(phone, otp):
        """Send OTP via Fast2SMS API. Returns True if sent, False otherwise."""
        api_key = Config.FAST2SMS_API_KEY
        sms_enabled = Config.SMS_ENABLED

        if not sms_enabled or not api_key:
            logger.info("SMS disabled or no API key configured — using demo mode")
            return False

        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            headers = {
                "authorization": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "route": "otp",
                "variables_values": otp,
                "numbers": phone,
                "flash": 0
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()

            if result.get("return"):
                logger.info(f"SMS sent successfully to +91{phone[:3]}***{phone[-3:]}")
                return True
            else:
                logger.error(f"Fast2SMS error: {result.get('message', 'Unknown error')}")
                return False

        except requests.exceptions.Timeout:
            logger.error("Fast2SMS request timed out")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Fast2SMS connection failed — check internet")
            return False
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return False

    @staticmethod
    def send_otp(phone):
        """Generate OTP, store in DB, and send via SMS"""
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

        # Send OTP via Fast2SMS
        sms_sent = OTPService._send_sms(phone, otp)

        # Console log (always, for debugging)
        print(f"\n{'='*50}")
        print(f"  📱 AURA OTP SERVICE")
        print(f"  Phone : +91 {phone[:3]}***{phone[-3:]}")
        print(f"  OTP   : {otp}")
        print(f"  SMS   : {'✅ Sent' if sms_sent else '⚠ Demo mode (SMS not sent)'}")
        print(f"  Valid  : {OTPService.OTP_EXPIRY_MINUTES} minutes")
        print(f"{'='*50}\n")

        if sms_sent:
            return otp, 'OTP sent to your phone via SMS'
        else:
            return otp, 'OTP generated (demo mode - check banner below)'

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
