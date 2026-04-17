from app import create_app
from aura.utils.database import get_db

def check_user():
    app = create_app()
    with app.app_context():
        db = get_db()
        email = 'sivasrivangapandu@gmail.com'
        user = db['users'].find_one({'email': email})
        if user:
            print(f"FOUND: {user['name']} ({user['role']})")
        else:
            print("NOT FOUND")

if __name__ == '__main__':
    check_user()
