from datetime import datetime


class ParentModel:
    """Parent model for database operations"""

    collection_name = 'parents'

    @staticmethod
    def create_parent(db, student_roll, parent_name, parent_phone,
                      relationship='parent', parent_email=''):
        """Create a new parent account (OTP-based, no password required).
        Uses upsert on parent_phone to prevent duplicate accounts from
        concurrent registration requests (race-condition safe)."""
        parent_data = {
            'student_roll': student_roll,
            'parent_name': parent_name,
            'parent_phone': parent_phone,
            'parent_email': parent_email,
            'relationship': relationship,
            'auth_type': 'otp',
            'created_at': datetime.utcnow(),
            'is_active': True,
            'notifications_enabled': True
        }
        result = db[ParentModel.collection_name].update_one(
            {'parent_phone': parent_phone},
            {'$setOnInsert': parent_data},
            upsert=True,
        )
        if result.upserted_id:
            return result.upserted_id
        existing = db[ParentModel.collection_name].find_one({'parent_phone': parent_phone})
        return existing['_id'] if existing else None

    @staticmethod
    def find_by_student_roll(db, student_roll):
        """Find parent by student roll number"""
        return db[ParentModel.collection_name].find_one({'student_roll': student_roll})

    @staticmethod
    def find_by_phone(db, phone):
        """Find parent by phone number"""
        return db[ParentModel.collection_name].find_one({
            'parent_phone': phone,
            'is_active': True
        })

    @staticmethod
    def find_by_email(db, parent_email):
        """Find parent by email"""
        return db[ParentModel.collection_name].find_one({'parent_email': parent_email})

    @staticmethod
    def update_last_login(db, student_roll):
        """Update parent's last login time"""
        db[ParentModel.collection_name].update_one(
            {'student_roll': student_roll},
            {'$set': {'last_login': datetime.utcnow()}}
        )
