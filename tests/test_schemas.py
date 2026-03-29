"""
AURA Pydantic Schema Tests
=============================
FIX #10: Tests for schema validation models.
"""
import pytest
import uuid
from datetime import datetime


class TestUserSchema:
    """Tests for UserSchema validation."""

    def test_valid_user(self):
        from models.schemas import UserSchema
        user = UserSchema(
            user_id=str(uuid.uuid4()),
            email="test@aura.edu",
            hashed_password="$2b$12$somehashedpasswordhere",
            name="Test User",
            role="student",
            department="Computer Science",
        )
        assert user.email == "test@aura.edu"
        assert user.timezone_offset == 330  # Default IST

    def test_email_lowercased(self):
        from models.schemas import UserSchema
        user = UserSchema(
            user_id=str(uuid.uuid4()),
            email="  TEST@AURA.edu  ",
            hashed_password="$2b$12$somehashedpasswordhere",
            name="Test",
            role="student",
        )
        assert user.email == "test@aura.edu"

    def test_invalid_role_rejected(self):
        from models.schemas import UserSchema
        with pytest.raises(Exception):
            UserSchema(
                user_id=str(uuid.uuid4()),
                email="t@a.edu",
                hashed_password="$2b$12$hash",
                name="T",
                role="superadmin",
            )

    def test_empty_name_rejected(self):
        from models.schemas import UserSchema
        with pytest.raises(Exception):
            UserSchema(
                user_id=str(uuid.uuid4()),
                email="t@a.edu",
                hashed_password="$2b$12$hash",
                name="",
                role="student",
            )


class TestMoodSchema:
    """Tests for MoodSchema validation."""

    def test_valid_mood(self):
        from models.schemas import MoodSchema
        mood = MoodSchema(
            user_email="test@aura.edu",
            mood="Happy",
            score=25,
        )
        assert mood.score == 25

    def test_score_out_of_range(self):
        from models.schemas import MoodSchema
        with pytest.raises(Exception):
            MoodSchema(user_email="t@a.edu", mood="Bad", score=150)

    def test_negative_score_rejected(self):
        from models.schemas import MoodSchema
        with pytest.raises(Exception):
            MoodSchema(user_email="t@a.edu", mood="Bad", score=-10)


class TestChatSchema:
    """Tests for ChatSchema validation."""

    def test_valid_chat_message(self):
        from models.schemas import ChatSchema
        chat = ChatSchema(
            user_email="test@aura.edu",
            role="user",
            message="Hello, how are you?",
        )
        assert chat.role == "user"

    def test_invalid_role(self):
        from models.schemas import ChatSchema
        with pytest.raises(Exception):
            ChatSchema(
                user_email="t@a.edu",
                role="moderator",
                message="test",
            )

    def test_empty_message_rejected(self):
        from models.schemas import ChatSchema
        with pytest.raises(Exception):
            ChatSchema(user_email="t@a.edu", role="user", message="")


class TestStressSchema:
    """Tests for StressSchema validation."""

    def test_valid_stress(self):
        from models.schemas import StressSchema
        stress = StressSchema(user_email="t@a.edu", score=75)
        assert stress.score == 75

    def test_score_clamped(self):
        from models.schemas import StressSchema
        with pytest.raises(Exception):
            StressSchema(user_email="t@a.edu", score=101)
