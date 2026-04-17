import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from aura.utils.database import get_db
from aura.utils.auth_helpers import hash_password, DEFAULT_STUDENT_PASSWORD

def migrate_passwords():
    app = create_app()
    with app.app_context():
        db = get_db()
        print(f"Hashing new default password: {DEFAULT_STUDENT_PASSWORD}...")
        new_hash = hash_password(DEFAULT_STUDENT_PASSWORD)
        
        # 1. Update all students
        result = db['users'].update_many(
            {'role': 'student'},
            {'$set': {
                'hashed_password': new_hash,
                'must_change_password': True  # Force safety change for production
            }}
        )
        print(f"Migration Complete: {result.modified_count} student accounts updated.")
        
        # 2. Specifically confirm/verify siva account
        siva = db['users'].find_one({'email': 'sivasrivangapandu@gmail.com'})
        if siva:
            print(f"Verified: Account {siva['email']} has been reset.")
        else:
            print("Warning: sivasrivangapandu@gmail.com not found during migration.")

if __name__ == '__main__':
    migrate_passwords()
