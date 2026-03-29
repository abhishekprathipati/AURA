"""
AURA OTP Service Tests
Tests for OTP generation, verification, and phone number handling.
"""
import pytest
from datetime import datetime, timedelta


class TestOTPGeneration:
    """Tests for OTP generation functionality."""

    def test_generate_otp_returns_6_digits(self):
        """Test that generated OTP is 6 digits."""
        from services.otp_service import OTPService

        otp = OTPService.generate_otp()

        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_range(self):
        """Test that OTP is within valid range (100000-999999)."""
        from services.otp_service import OTPService

        for _ in range(100):
            otp = OTPService.generate_otp()
            otp_int = int(otp)
            assert 100000 <= otp_int <= 999999

    def test_generate_otp_uniqueness(self):
        """Test that generated OTPs are sufficiently random."""
        from services.otp_service import OTPService

        otps = [OTPService.generate_otp() for _ in range(50)]
        # Most should be unique (allowing some collisions due to randomness)
        unique_count = len(set(otps))
        assert unique_count >= 45  # At least 90% unique


class TestPhoneNormalization:
    """Tests for phone number normalization."""

    def test_normalize_10_digit_phone(self):
        """Test normalizing a standard 10-digit phone number."""
        from services.otp_service import OTPService

        result = OTPService.normalize_phone('9876543210')
        assert result == '9876543210'

    def test_normalize_phone_with_country_code(self):
        """Test normalizing phone with +91 country code."""
        from services.otp_service import OTPService

        result = OTPService.normalize_phone('919876543210')
        assert result == '9876543210'

    def test_normalize_phone_with_leading_zero(self):
        """Test normalizing phone with leading zero."""
        from services.otp_service import OTPService

        result = OTPService.normalize_phone('09876543210')
        assert result == '9876543210'

    def test_normalize_phone_with_spaces(self):
        """Test normalizing phone with spaces and dashes."""
        from services.otp_service import OTPService

        result = OTPService.normalize_phone('98765-43210')
        assert result == '9876543210'

        result = OTPService.normalize_phone('98765 43210')
        assert result == '9876543210'

    def test_normalize_phone_with_plus_sign(self):
        """Test normalizing phone with +91 prefix."""
        from services.otp_service import OTPService

        result = OTPService.normalize_phone('+919876543210')
        assert result == '9876543210'

    def test_normalize_empty_phone(self):
        """Test normalizing empty phone returns empty string."""
        from services.otp_service import OTPService

        result = OTPService.normalize_phone('')
        assert result == ''

        result = OTPService.normalize_phone(None)
        assert result == ''


class TestOTPSendWithMockDB:
    """Tests for OTP sending with mocked database."""

    def test_send_otp_returns_otp_and_message(self, mock_db):
        """Test that send_otp returns (success, message) — OTP is never returned for security."""
        from services.otp_service import OTPService

        success, message = OTPService.send_otp('9876543210')

        assert success is True, f"Expected success=True, got {success!r}"
        assert isinstance(message, str), f"Expected message to be str, got {type(message)}"
        assert len(message) > 0
        # OTP intentionally NOT in response (security fix #5)
        assert 'OTP' in message or 'demo' in message.lower() or 'sent' in message.lower()

    def test_send_otp_stores_in_database(self, mock_db):
        """Test that send_otp stores the OTP record."""
        from services.otp_service import OTPService

        success, _ = OTPService.send_otp('9876543210')

        # Check that data was inserted into the collection
        collection = mock_db[OTPService.collection_name]
        assert len(collection._data) > 0


class TestOTPVerificationWithMockDB:
    """Tests for OTP verification logic."""

    def test_verify_otp_with_no_record(self, mock_db):
        """Test verification fails when no OTP exists."""
        from services.otp_service import OTPService

        success, message = OTPService.verify_otp('9876543210', '123456')

        assert success is False
        assert 'expired' in message.lower() or 'not found' in message.lower()


class TestOTPServiceConstants:
    """Tests for OTP service configuration constants."""

    def test_otp_expiry_configured(self):
        """Test that OTP expiry is configured."""
        from services.otp_service import OTPService

        assert hasattr(OTPService, 'OTP_EXPIRY_MINUTES')
        assert OTPService.OTP_EXPIRY_MINUTES > 0

    def test_max_attempts_configured(self):
        """Test that max attempts is configured."""
        from services.otp_service import OTPService

        assert hasattr(OTPService, 'MAX_ATTEMPTS')
        assert OTPService.MAX_ATTEMPTS > 0

    def test_resend_cooldown_configured(self):
        """Test that resend cooldown is configured."""
        from services.otp_service import OTPService

        assert hasattr(OTPService, 'RESEND_COOLDOWN_SECONDS')
        assert OTPService.RESEND_COOLDOWN_SECONDS > 0
