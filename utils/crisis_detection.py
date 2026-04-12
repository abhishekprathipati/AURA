"""
CRISIS DETECTION MODULE
=======================
Detects dangerous/suicidal keywords in student messages and alerts immediately.
Sends CRITICAL alerts to proctor and parent with message content.
"""

import logging
from typing import Tuple

log = logging.getLogger(__name__)

# Dangerous keywords that indicate crisis/self-harm risk
CRISIS_KEYWORDS = {
    # Suicidal ideation
    'kill myself', 'want to die', 'should die', 'kill myself',
    'commit suicide', 'end my life', 'hang myself', 'overdose',
    'slit wrist', 'cut myself', 'jump off', 'no point living',
    'better off dead', 'everyone hates me', 'nobody cares',
    'worthless', 'useless', 'end it all', 'finish it',

    # Self-harm
    'cut skin', 'hurt myself', 'burn myself', 'harm myself',
    'self harm', 'self-harm', 'cutting myself',

    # Crisis indicators
    'final goodbye', 'last message', 'last time', 'goodbye forever',
    'see you never', 'leaving forever', 'disappearing', 'never coming back',

    # Homicidal (threaten others)
    'kill you', 'hurt you', 'beat you', 'shoot you', 'stab you',
    'i will hurt', 'i will kill', 'i will attack',

    # Extreme distress
    'panic attack', 'mental breakdown', 'losing my mind',
    'going crazy', "can't take it", "can't do this",
}

# High-risk phrases (exact matches required)
HIGH_RISK_PHRASES = [
    'i want to kill myself',
    'i want to die',
    'i should kill myself',
    'i am going to kill myself',
    'i am going to commit suicide',
    'suicide note',
    'goodbye cruel world',
]


def detect_crisis(message: str) -> Tuple[bool, str]:
    """
    Detect if a message contains crisis/self-harm content.

    Returns:
        (is_crisis, risk_level)
        is_crisis: True if dangerous content detected
        risk_level: 'CRITICAL', 'HIGH', or 'MEDIUM'
    """
    if not message:
        return False, 'NONE'

    message_lower = message.lower().strip()

    # Check high-risk phrases (exact match = CRITICAL)
    for phrase in HIGH_RISK_PHRASES:
        if phrase in message_lower:
            return True, 'CRITICAL'

    # Count dangerous keywords (multiple = higher risk)
    keyword_hits = 0
    for keyword in CRISIS_KEYWORDS:
        if keyword in message_lower:
            keyword_hits += 1

    if keyword_hits >= 3:
        return True, 'CRITICAL'
    elif keyword_hits >= 2:
        return True, 'HIGH'
    elif keyword_hits >= 1:
        return True, 'MEDIUM'

    return False, 'NONE'


def create_crisis_alert(student_email: str, student_name: str,
                       message: str, risk_level: str) -> dict:
    """
    Create a crisis alert record.

    Returns: Alert record to be sent
    """
    return {
        'student_email': student_email,
        'student_name': student_name,
        'message': message,
        'risk_level': risk_level,
        'alert_type': 'CRISIS_DETECTION',
        'requires_immediate_action': True,
        'subject': f'[CRITICAL] CRISIS ALERT: {student_name} - Immediate Action Required',
        'body': f"""
CRISIS ALERT - IMMEDIATE ACTION REQUIRED
=========================================

Risk Level: {risk_level}
Student: {student_name}
Email: {student_email}

Message Content:
"{message}"

ACTION:
1. Contact student IMMEDIATELY
2. Check on their physical safety
3. Connect to mental health resources
4. If life-threatening: Call 911 or emergency services

This is an automated alert from AURA Student Wellness System.
Report generated at: {__import__('datetime').datetime.utcnow().isoformat()}

CONFIDENTIAL - FOR AUTHORIZED PERSONNEL ONLY
        """.strip()
    }
