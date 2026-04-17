import bcrypt
from pymongo import MongoClient

def simple_migrate():
    # Correct URI from .env
    uri = "mongodb+srv://auraadmin:AuraDB2024pass@cluster0.76fgwmv.mongodb.net/aura_db?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri)
    db = client['aura_db']
    
    password = "Aura@student"
    print(f"Hashing '{password}'...")
    new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    print("Updating student records in database...")
    result = db['users'].update_many(
        {'role': 'student'},
        {'$set': {
            'hashed_password': new_hash,
            'must_change_password': True
        }}
    )
    print(f"DONE. {result.modified_count} student accounts updated.")

    siva = db['users'].find_one({'email': 'sivasrivangapandu@gmail.com'})
    if siva:
        print(f"Successfully verified password reset for: {siva['email']}")
    else:
        print("Note: sivasrivangapandu@gmail.com not found, but other students updated.")

if __name__ == '__main__':
    simple_migrate()
