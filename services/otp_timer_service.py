"""
OTP Timer Service - manages server-side OTP session state with real-time countdown tracking.
Tracks active OTP sessions and provides countdown information for SocketIO events.

SECURITY: Timer state is ephemeral (in-memory), not persisted. No sensitive data stored.
"""

import threading
from datetime import datetime, timedelta
from typing import Optional, Dict


class OTPTimerService:
    """Thread-safe OTP session tracking with real-time countdown capabilities"""

    # In-memory store: phone -> {expiry_time: datetime, created_at: datetime, delivery_method: str}
    _sessions: Dict[str, dict] = {}
    _lock = threading.Lock()

    @staticmethod
    def register_otp_session(phone: str, expiry_seconds: int, delivery_method: str = 'sms') -> None:
        """
        Register an active OTP session with expiry time.

        Args:
            phone: Normalized phone number (10 digits)
            expiry_seconds: Seconds until OTP expires (typically 300 for 5 minutes)
            delivery_method: 'sms' or 'email'
        """
        with OTPTimerService._lock:
            now = datetime.utcnow()
            expiry_time = now + timedelta(seconds=expiry_seconds)
            OTPTimerService._sessions[phone] = {
                'expiry_time': expiry_time,
                'created_at': now,
                'delivery_method': delivery_method
            }

    @staticmethod
    def get_remaining_seconds(phone: str) -> Optional[int]:
        """
        Get remaining seconds for an active OTP session.

        Returns:
            - Positive int: seconds remaining
            - 0: OTP just expired
            - None: OTP session not found or expired
        """
        with OTPTimerService._lock:
            if phone not in OTPTimerService._sessions:
                return None

            session = OTPTimerService._sessions[phone]
            expiry_time = session['expiry_time']
            now = datetime.utcnow()

            remaining = (expiry_time - now).total_seconds()

            # Clean up if expired
            if remaining <= 0:
                del OTPTimerService._sessions[phone]
                return None

            return int(remaining)

    @staticmethod
    def is_otp_active(phone: str) -> bool:
        """Check if an OTP session is active and not expired"""
        remaining = OTPTimerService.get_remaining_seconds(phone)
        return remaining is not None and remaining > 0

    @staticmethod
    def cancel_otp_session(phone: str) -> None:
        """Cancel and remove an OTP session (called after verification or max attempts)"""
        with OTPTimerService._lock:
            OTPTimerService._sessions.pop(phone, None)

    @staticmethod
    def get_session_info(phone: str) -> Optional[dict]:
        """Get full session info including delivery method"""
        with OTPTimerService._lock:
            if phone not in OTPTimerService._sessions:
                return None

            session = OTPTimerService._sessions[phone]
            remaining = int((session['expiry_time'] - datetime.utcnow()).total_seconds())

            if remaining <= 0:
                del OTPTimerService._sessions[phone]
                return None

            return {
                'phone': phone,
                'remaining_seconds': remaining,
                'delivery_method': session['delivery_method'],
                'created_at': session['created_at'].isoformat(),
                'expired': False
            }

    @staticmethod
    def cleanup_expired_sessions() -> int:
        """
        Remove all expired OTP sessions. Call periodically (e.g., every 30 seconds).

        Returns: Number of sessions cleaned up
        """
        with OTPTimerService._lock:
            now = datetime.utcnow()
            expired_phones = [
                phone for phone, session in OTPTimerService._sessions.items()
                if session['expiry_time'] <= now
            ]
            for phone in expired_phones:
                del OTPTimerService._sessions[phone]
            return len(expired_phones)

    @staticmethod
    def get_all_active_sessions() -> list[str]:
        """Get list of all phone numbers with active OTP sessions (for debugging)"""
        with OTPTimerService._lock:
            now = datetime.utcnow()
            active = [
                phone for phone, session in OTPTimerService._sessions.items()
                if session['expiry_time'] > now
            ]
            return active

    @staticmethod
    def clear_all_sessions() -> None:
        """Clear all sessions (for testing/reset)"""
        with OTPTimerService._lock:
            OTPTimerService._sessions.clear()
