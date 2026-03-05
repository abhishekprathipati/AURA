"""
═══════════════════════════════════════════════════════════════
AURA — Role-Based Access Control (RBAC) Helper
═══════════════════════════════════════════════════════════════
Single source of truth for data visibility.

Usage:
    from utils.access_control import get_visible_student_ids, get_department_filter

    # In any API route:
    student_ids = get_visible_student_ids()     # list of anonymous_ids
    dept_filter = get_department_filter()        # MongoDB filter dict

Roles:
    student  → own data only
    proctor  → only assigned students (proctor_students.proctor_id)
    hod      → all students in their department
    admin    → everything
═══════════════════════════════════════════════════════════════
"""
import hashlib
from flask import session
from utils.database import get_db


def create_anonymous_id(email: str) -> str:
    """
    Canonical anonymous ID generation.
    Formula: STU_{MD5(email.lower().strip()) % 100000 : 05d}
    This is the SINGLE source of truth — all other code must call this.
    """
    clean = email.lower().strip()
    h = int(hashlib.md5(clean.encode()).hexdigest(), 16) % 100000
    return f"STU_{h:05d}"


def get_current_user() -> dict:
    """
    Return the current user's identity from the session.
    Returns: {email, name, role, department}
    """
    return {
        'email': session.get('user_email', ''),
        'name': session.get('user_name', ''),
        'role': session.get('user_role', ''),
        'department': session.get('user_department', ''),
    }


def get_visible_student_ids(user: dict | None = None) -> list[str]:
    """
    Return a list of anonymous_ids that the current user is allowed to see.

    Rules:
        student → [own anonymous_id]
        proctor → anonymous_ids from proctor_students where proctor_id == email
        hod     → anonymous_ids from proctor_students where department == user.department
        admin   → all anonymous_ids from proctor_students

    Returns an empty list if role is unknown.
    """
    if user is None:
        user = get_current_user()

    db = get_db()
    role = user.get('role', '')
    email = user.get('email', '')
    department = user.get('department', '')

    if role == 'student':
        return [create_anonymous_id(email)]

    if role == 'proctor':
        docs = db['proctor_students'].find(
            {'proctor_id': email, 'status': 'active'},
            {'anonymous_id': 1}
        )
        return [d['anonymous_id'] for d in docs if d.get('anonymous_id')]

    if role == 'hod':
        if not department:
            return []
        docs = db['proctor_students'].find(
            {'department': department, 'status': 'active'},
            {'anonymous_id': 1}
        )
        return [d['anonymous_id'] for d in docs if d.get('anonymous_id')]

    if role == 'admin':
        docs = db['proctor_students'].find(
            {'status': 'active'},
            {'anonymous_id': 1}
        )
        return [d['anonymous_id'] for d in docs if d.get('anonymous_id')]

    return []


def get_visible_students(user: dict | None = None) -> list[dict]:
    """
    Return full student documents the current user can see.
    Same scoping rules as get_visible_student_ids().
    """
    if user is None:
        user = get_current_user()

    db = get_db()
    role = user.get('role', '')
    email = user.get('email', '')
    department = user.get('department', '')

    if role == 'student':
        return []  # Students don't see a student list

    query = {'status': 'active'}

    if role == 'proctor':
        query['proctor_id'] = email
    elif role == 'hod':
        if department:
            query['department'] = department
        else:
            return []
    elif role == 'admin':
        pass  # no filter
    else:
        return []

    return list(db['proctor_students'].find(query))


def get_department_filter(user: dict | None = None) -> dict:
    """
    Return a MongoDB filter dict that scopes queries to the user's department.

    For proctor: returns {} (proctors see only assigned students, not dept-wide)
    For hod:     returns {'department': dept}
    For admin:   returns {} (no restriction)
    For student: returns {'department': dept}
    """
    if user is None:
        user = get_current_user()

    role = user.get('role', '')
    department = user.get('department', '')

    if role in ('hod', 'student') and department:
        return {'department': department}

    return {}


def get_incident_filter(user: dict | None = None) -> dict:
    """
    Return a MongoDB filter dict for risk_incidents that respects role scoping.

    student → own anonymous_id only
    proctor → incidents for assigned students
    hod     → incidents for department students
    admin   → no filter
    """
    if user is None:
        user = get_current_user()

    ids = get_visible_student_ids(user)
    role = user.get('role', '')

    if role == 'admin':
        return {}

    if not ids:
        return {'anonymous_student_id': {'$in': []}}  # empty result

    return {'anonymous_student_id': {'$in': ids}}


def can_access_student(anonymous_id: str, user: dict | None = None) -> bool:
    """
    Check if the current user has permission to view a specific student.
    """
    if user is None:
        user = get_current_user()

    role = user.get('role', '')
    if role == 'admin':
        return True

    visible = get_visible_student_ids(user)
    return anonymous_id in visible
