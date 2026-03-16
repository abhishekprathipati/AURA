"""
Proctor Service layer for extracting Database queries from standard routes.
"""
from datetime import datetime
import uuid

from utils.database import get_db
from utils.auth_helpers import hash_password, generate_temp_password
from utils.access_control import generate_anonymous_id

def register_new_student(proctor_email: str, student_data: dict) -> dict:
    """
    Registers a new student under a proctor's supervision.
    Handles duplicate checks, random password generation, and DB insertion.
    Returns:
        dict: {'success': bool, 'error': str (optional), 'temp_password': str (optional), 'anonymous_id': str}
    """
    db = get_db()
    
    name = student_data.get('name', '')
    roll_number = student_data.get('roll_number', '').upper()
    email = student_data.get('email', '').lower()
    department = student_data.get('department', '')
    parent_name = student_data.get('parent_name', '')
    parent_phone = student_data.get('parent_phone', '')
    
    # Check duplicates 
    if db['proctor_students'].find_one({'roll_number': roll_number}):
        return {'success': False, 'status_code': 409, 'error': f'Student with roll number {roll_number} already exists.'}
    if db['proctor_students'].find_one({'email': email}):
        return {'success': False, 'status_code': 409, 'error': f'Student with email {email} already exists.'}

    # Build student record 
    temp_password = generate_temp_password()
    anonymous_id = generate_anonymous_id()

    student_record = {
        'student_id': str(uuid.uuid4()),
        'anonymous_id': anonymous_id,
        'name': name,
        'roll_number': roll_number,
        'email': email,
        'department': department,
        'semester': student_data.get('semester', '4'),
        'section': student_data.get('section', 'A'),
        'risk_level': (student_data.get('risk_level') or 'low').upper(),
        'blood_group': student_data.get('blood_group', ''),
        'notes': student_data.get('notes', ''),
        'proctor_id': proctor_email,
        'status': 'active',
        'created_at': datetime.utcnow(),
        'created_by': proctor_email,
    }

    # Insert student 
    db['proctor_students'].insert_one(student_record)

    # Insert or update login credentials map 
    existing_user = db['users'].find_one({'email': email})
    if not existing_user:
        db['users'].insert_one({
            'email': email,
            'hashed_password': hash_password(temp_password),
            'name': name,
            'role': 'student',
            'department': department,
            'roll_number': roll_number,
            'parent_phone': parent_phone,
            'created_at': datetime.utcnow(),
            'must_change_password': True,
        })
    else:
        # Patch missing fields if user already exists
        update_fields = {}
        if not existing_user.get('roll_number'):
            update_fields['roll_number'] = roll_number
        if not existing_user.get('parent_phone'):
            update_fields['parent_phone'] = parent_phone
        if update_fields:
            db['users'].update_one({'email': email}, {'$set': update_fields})

    # Add parent record
    parent_record = {
        'student_roll': roll_number,
        'parent_name': parent_name,
        'parent_phone': parent_phone,
        'parent_email': (student_data.get('parent_email') or '').strip(),
        'relationship': student_data.get('parent_relationship', 'parent'),
        'auth_type': 'otp',
        'created_at': datetime.utcnow(),
        'is_active': True,
        'notifications_enabled': True,
    }
    db['parents'].update_one(
        {'student_roll': roll_number},
        {'$set': parent_record},
        upsert=True,
    )
        
    return {
        'success': True,
        'status_code': 201,
        'student_id': student_record['student_id'],
        'anonymous_id': anonymous_id,
        'temp_password': temp_password,
        'message': f'Student {name} successfully added.'
    }
