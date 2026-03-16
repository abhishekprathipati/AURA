"""
Pydantic v2 request schemas for AURA API endpoints.

Usage
-----
    from utils.schemas import ChatMessageRequest, ValidationError

    try:
        payload = ChatMessageRequest.model_validate(request.get_json() or {})
    except ValidationError as exc:
        return jsonify({'success': False, 'error': exc.errors()[0]['msg']}), 400

All schemas use strict type coercion and length limits to prevent injection
and oversized-payload attacks at the system boundary.
"""

from __future__ import annotations
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

# Re-export so callers can do `from utils.schemas import ..., ValidationError`
from pydantic import ValidationError  # noqa: F401

VALID_DEPARTMENTS = {"AIML", "CSE", "ECE", "CIVIL", "MECH"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-().]{10,15}$")


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    """Payload sent by the student to the AI chat endpoints."""

    message: str = Field(..., min_length=1, max_length=2000, strip_whitespace=True)
    context: Optional[str] = Field(None, max_length=500, strip_whitespace=True)
    session_id: Optional[str] = Field(None, max_length=64)
    persona: Optional[str] = Field("mental", max_length=20)

    @field_validator("persona")
    @classmethod
    def valid_persona(cls, v: str) -> str:
        allowed = {"mental", "study", "general"}
        if v not in allowed:
            raise ValueError(f"persona must be one of {allowed}")
        return v


# ── Wellness / mood ───────────────────────────────────────────────────────────

class WellnessCheckinRequest(BaseModel):
    """Mood / stress log submitted from the student dashboard."""

    mood: int = Field(..., ge=1, le=5)
    stress: int = Field(..., ge=0, le=100)
    notes: str = Field("", max_length=500, strip_whitespace=True)

class ScheduleSessionRequest(BaseModel):
    """Booking a 1-on-1 counseling session."""
    date: str = Field(..., min_length=1, max_length=20, strip_whitespace=True)
    time: str = Field(..., min_length=1, max_length=20, strip_whitespace=True)
    type: str = Field("general", max_length=50, strip_whitespace=True)
    notes: str = Field("", max_length=500, strip_whitespace=True)

class SupportRequestSchema(BaseModel):
    """Requesting immediate support."""
    notes: str = Field("", max_length=1000, strip_whitespace=True)

class MoodUpdateRequest(BaseModel):
    mood: str = Field("calm", max_length=50, strip_whitespace=True)

class JournalEntryRequest(BaseModel):
    entry: str = Field(..., min_length=1, max_length=2000, strip_whitespace=True)

class QuickActionRequest(BaseModel):
    action: str = Field(..., max_length=50, strip_whitespace=True)

class GrievanceRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200, strip_whitespace=True)
    description: str = Field(..., min_length=1, max_length=2000, strip_whitespace=True)



# ── Student registration ──────────────────────────────────────────────────────

class StudentAddRequest(BaseModel):
    """Proctor → add student form payload."""

    name: str = Field(..., min_length=2, max_length=100, strip_whitespace=True)
    roll_number: str = Field(..., min_length=2, max_length=20, strip_whitespace=True)
    email: str = Field(..., min_length=5, max_length=100, strip_whitespace=True)
    department: str = Field(..., strip_whitespace=True)
    parent_name: str = Field(..., min_length=2, max_length=100, strip_whitespace=True)
    parent_phone: str = Field(..., min_length=10, max_length=15, strip_whitespace=True)
    semester: Optional[str] = Field("4", max_length=5)
    section: Optional[str] = Field("A", max_length=5)
    risk_level: Optional[str] = Field("LOW", max_length=10)
    blood_group: Optional[str] = Field("", max_length=5)
    notes: Optional[str] = Field("", max_length=500)
    parent_email: Optional[str] = Field("", max_length=100)
    parent_relationship: Optional[str] = Field("parent", max_length=30)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address format")
        return v.lower()

    @field_validator("department")
    @classmethod
    def valid_department(cls, v: str) -> str:
        if v not in VALID_DEPARTMENTS:
            raise ValueError(f"Department must be one of {VALID_DEPARTMENTS}")
        return v

    @field_validator("parent_phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        if not _PHONE_RE.match(v):
            raise ValueError("Phone must be 10–15 digits, optionally with spaces or dashes")
        return v


# ── Proctor registration ──────────────────────────────────────────────────────

class ProctorAddRequest(BaseModel):
    """HOD → add proctor form payload."""

    name: str = Field(..., min_length=2, max_length=100, strip_whitespace=True)
    email: str = Field(..., min_length=5, max_length=100, strip_whitespace=True)
    phone: str = Field(..., min_length=10, max_length=15, strip_whitespace=True)
    department: str = Field(..., strip_whitespace=True)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address format")
        return v.lower()

    @field_validator("department")
    @classmethod
    def valid_department(cls, v: str) -> str:
        if v not in VALID_DEPARTMENTS:
            raise ValueError(f"Department must be one of {VALID_DEPARTMENTS}")
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        if not _PHONE_RE.match(v):
            raise ValueError("Phone must be 10–15 digits, optionally with spaces or dashes")
        return v


# ── Password change ───────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    """Student → change password payload."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)

    @model_validator(mode="after")
    def passwords_differ(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password")
        return self
