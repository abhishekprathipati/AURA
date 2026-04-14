"""
Fetch All Users from Database
"""

from app import app
from aura.utils.database import get_db

with app.app_context():
    db = get_db()
    users = db['users'].find()

    user_list = list(users)

    print("=" * 80)
    print("ALL USERS IN AURA SYSTEM")
    print("=" * 80)
    print()

    if not user_list:
        print("No users found")
    else:
        print(f"Total Users: {len(user_list)}\n")

        for i, user in enumerate(user_list, 1):
            print(f"{i}. Name: {user.get('name', 'N/A')}")
            print(f"   Email: {user.get('email', 'N/A')}")
            print(f"   Role: {user.get('role', 'N/A')}")
            print(f"   Department: {user.get('department', 'N/A')}")
            print(f"   Parent Email: {user.get('parent_email', 'N/A')}")
            print(f"   Created: {user.get('created_at', 'N/A')}")
            print()

print("=" * 80)
