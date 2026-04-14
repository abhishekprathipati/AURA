"""
AURA Pydantic Schemas — Data Validation Layer
================================================
FIX #10: Pydantic models for validating data before DB operations.
Use these schemas at service boundaries to catch invalid data early.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator


class UserSchema(BaseModel):
    """Validates user document before insert/update."""
    user_id: str = Field(description="UUID — canonical internal identifier")
    email: str = Field(description="Unique email for login")
    hashed_password: str = Field(min_length=10)
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern=r'^(student|proctor|hod|admin)$')
    department: str = Field(default='', max_length=100)
    timezone_offset: int = Field(default=330, ge=-720, le=840)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.strip().lower()


class MoodSchema(BaseModel):
    """Validates mood log entries."""
    user_email: str
    mood: str = Field(min_length=1, max_length=50)
    score: int = Field(ge=0, le=100)
    context: str = Field(default='', max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StressSchema(BaseModel):
    """Validates stress score records."""
    user_email: str
    score: int = Field(ge=0, le=100)
    signals: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSchema(BaseModel):
    """Validates chat message records."""
    user_email: str
    role: str = Field(pattern=r'^(user|assistant|system)$')
    message: str = Field(min_length=1, max_length=5000)
    mood: Optional[str] = None
    stress_score: Optional[int] = Field(default=None, ge=0, le=100)
    model_version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OTPSchema(BaseModel):
    """Validates OTP records."""
    phone: str = Field(min_length=10, max_length=15)
    hashed_otp: str
    attempts: int = Field(default=0, ge=0)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlertSchema(BaseModel):
    """Validates institutional stress alerts."""
    student_email: str
    score: int = Field(ge=0, le=100)
    proctor_email: Optional[str] = None
    parent_email: Optional[str] = None
    status: str = Field(default='logged', pattern=r'^(sent|logged|failed)$')
    created_at: datetime = Field(default_factory=datetime.utcnow)
