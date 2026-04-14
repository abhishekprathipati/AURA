import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import app
from aura.utils.database import get_db
from aura.utils.auth_helpers import hash_password

with app.app_context():
    db = get_db()
    email = 'abhishekprathipati07@gmail.com'
    new_password = 'Aura@hod'
    
    pwd_hash = hash_password(new_password)
    db['users'].update_one({'email': email}, {'$set': {'hashed_password': pwd_hash}})
    print(f'Successfully updated password for: {email}')
