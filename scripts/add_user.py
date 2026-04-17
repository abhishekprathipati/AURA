import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import datetime
from app import app
from aura.utils.database import get_db
from aura.utils.auth_helpers import hash_password

with app.app_context():
    db = get_db()
    email = '22mh1a4257@acoe.edu.in'
    
    pwd_hash = hash_password('Aura@student')
    user = db['users'].find_one({'email': email})
    
    if not user:
        db['users'].insert_one({
            'email': email,
            'name': 'AURA Student',
            'hashed_password': pwd_hash,
            'role': 'student',
            'department': 'Computer Science',
            'year': 3,
            'created_at': datetime.datetime.utcnow()
        })
        print("Created user successfully")
    else:
        db['users'].update_one({'email': email}, {'$set': {'hashed_password': pwd_hash}})
        print("Updated user password successfully")
