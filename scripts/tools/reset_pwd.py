"""Quick script to reset demo proctor password for testing."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from aura.utils.auth_helpers import hash_password
from aura.utils.database import get_db

db = get_db()
new_hash = hash_password('Test@123')
result = db.users.update_one(
    {'email': 'proctor@aura.edu'},
    {'$set': {'hashed_password': new_hash}}
)
print(f"Modified: {result.modified_count}")
