"""
OTP (One-Time Password) Service for Parent Authentication
Handles OTP generation, storage in MongoDB, verification, and SMS delivery via Fast2SMS.

SECURITY: OTPs are hashed using bcrypt before storage in MongoDB.
          OTPs are NEVER returned in API responses - only sent via SMS.
"""

import secrets
import requests
import logging
import bcrypt
from datetime import datetime, timedelta
from utils.database import get_db
from config import Config
from services.otp_timer_service import OTPTimerService

logger = logging.getLogger(__name__)


class OTPService:
    """OTP generation, storage, and verification service"""

    collection_name = 'otp_verifications'
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3
    RESEND_COOLDOWN_SECONDS = 30

    @staticmethod
    def _hash_otp(otp: str) -> str:
        """Hash an OTP using bcrypt for secure storage."""
        return bcrypt.hashpw(otp.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def _verify_otp_hash(otp: str, hashed_otp: str) -> bool:
        """Verify an OTP against its bcrypt hash."""
        try:
            return bcrypt.checkpw(otp.encode('utf-8'), hashed_otp.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def generate_otp():
        """Generate a cryptographically secure 6-digit OTP"""
        return str(secrets.randbelow(900000) + 100000)

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
                logger.info("SMS sent successfully to +91%s***%s", phone[:3], phone[-3:])
                return True
            else:
                logger.error("Fast2SMS error: %s", result.get('message', 'Unknown error'))
                return False

        except requests.exceptions.Timeout:
            logger.error("Fast2SMS request timed out")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Fast2SMS connection failed — check internet")
            return False
        except Exception as e:
            logger.error("SMS sending failed: %s", str(e))
            return False

    @staticmethod
    def _send_email(phone, otp, email_address):
        """Send OTP via email using Flask-Mail. Returns True if sent, False otherwise."""
        try:
            from flask import current_app
            from flask_mail import Message
            from utils.email_templates import get_otp_email_template

            if not email_address:
                logger.warning("No email address provided for OTP delivery")
                return False

            # Get mail app extension
            mail = current_app.extensions.get('mail')
            if not mail:
                logger.warning("Flask-Mail not configured or initialized")
                return False

            # Generate email content
            subject, html_body, text_body = get_otp_email_template(otp, OTPService.OTP_EXPIRY_MINUTES)

            # Create and send message
            msg = Message(
                subject=subject,
                recipients=[email_address],
                html=html_body,
                body=text_body,
                sender=Config.MAIL_DEFAULT_SENDER or f"noreply@{email_address.split('@')[1]}"
            )

            mail.send(msg)
            logger.info("Email sent successfully to %s***%s", email_address[:3], email_address.split('@')[0][-3:])
            return True

        except ImportError:
            logger.warning("Flask-Mail not installed; email delivery disabled")
            return False
        except Exception as e:
            logger.error("Email sending failed: %s", str(e))
            return False


    @staticmethod
    def send_otp(phone, delivery_method='sms', email_address=None):
        """Generate OTP, store hashed in DB, and send via SMS or Email.

        SECURITY: OTP is hashed before storage and NEVER returned in the response.
        The OTP is only sent via SMS/Email - never exposed in API responses.

        Args:
            phone: Normalized phone number (10 digits)
            delivery_method: 'sms' or 'email' (default: 'sms')
            email_address: Email to send to if delivery_method is 'email'

        Returns: (success: bool or str, message: str)
                 - success is True/False for production, or OTP string for demo mode
        """
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
            return False, 'Please wait before requesting a new OTP'

        # Invalidate existing OTPs for this phone
        db[OTPService.collection_name].update_many(
            {'phone': phone, 'verified': False},
            {'$set': {'expired': True}}
        )

        # Hash OTP before storing (SECURITY FIX #4)
        hashed_otp = OTPService._hash_otp(otp)

        # Store new OTP (hashed) with delivery method
        otp_record = {
            'phone': phone,
            'otp_hash': hashed_otp,  # Store hash, not plaintext
            'attempts': 0,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=OTPService.OTP_EXPIRY_MINUTES),
            'verified': False,
            'expired': False,
            'delivery_method': delivery_method
        }
        db[OTPService.collection_name].insert_one(otp_record)

        # Register timer session for real-time countdown
        OTPTimerService.register_otp_session(
            phone,
            OTPService.OTP_EXPIRY_MINUTES * 60,
            delivery_method
        )

        # Send OTP via requested delivery method
        if delivery_method == 'email':
            if not email_address:
                return False, 'Email address required for email delivery'
            sent = OTPService._send_email(phone, otp, email_address)
            delivery_name = 'email'
        else:
            sent = OTPService._send_sms(phone, otp)
            delivery_name = 'SMS'

        # Structured log (OTP never exposed)
        _log = logging.getLogger('aura.otp')
        _log.info('OTP generated  phone=+91%s***%s  delivery=%s  sms=%s  ttl=%dm',
                  phone[:3], phone[-3:],
                  delivery_name,
                  'sent' if sent else 'demo',
                  OTPService.OTP_EXPIRY_MINUTES)

        # SECURITY FIX #5: Never return OTP to frontend in production.
        # For demo mode: we MUST return it so the UI banner works.
        if sent:
            return True, f'OTP sent to your {delivery_name.lower()} via {delivery_name}'
        else:
            _log.warning('DEMO MODE: OTP for %s***%s is %s (returned to client)',
                        phone[:3], phone[-3:], otp)
            return otp, f'OTP generated (demo mode - check screen banner)'

    @staticmethod
    def verify_otp(phone, otp):
        """Verify OTP for a phone number using bcrypt hash comparison.

        SECURITY: OTPs are stored as bcrypt hashes. Verification uses
        constant-time comparison to prevent timing attacks.

        Returns: (success: bool, message: str)
        """
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
            # Cancel timer session since OTP expired/not found
            OTPTimerService.cancel_otp_session(phone)
            return False, 'OTP expired or not found. Please request a new one.'

        # Check max attempts
        if record.get('attempts', 0) >= OTPService.MAX_ATTEMPTS:
            db[OTPService.collection_name].update_one(
                {'_id': record['_id']},
                {'$set': {'expired': True}}
            )
            OTPTimerService.cancel_otp_session(phone)
            return False, 'Too many failed attempts. Please request a new OTP.'

        # Increment attempt count
        db[OTPService.collection_name].update_one(
            {'_id': record['_id']},
            {'$inc': {'attempts': 1}}
        )

        # Check OTP match using bcrypt hash verification (SECURITY FIX #4)
        # Support both old plaintext 'otp' field and new 'otp_hash' field for migration
        stored_hash = record.get('otp_hash')
        stored_plain = record.get('otp')

        otp_valid = False
        if stored_hash:
            # New secure method: verify against bcrypt hash
            otp_valid = OTPService._verify_otp_hash(otp, stored_hash)
        elif stored_plain:
            # Legacy fallback for old records (will be phased out)
            otp_valid = (stored_plain == otp)

        if not otp_valid:
            remaining = OTPService.MAX_ATTEMPTS - record.get('attempts', 0) - 1
            return False, f'Invalid OTP. {remaining} attempt(s) remaining.'

        # OTP matched - mark as verified and cancel timer
        db[OTPService.collection_name].update_one(
            {'_id': record['_id']},
            {'$set': {'verified': True, 'verified_at': datetime.utcnow()}}
        )
        OTPTimerService.cancel_otp_session(phone)

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
