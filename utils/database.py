import ssl
from typing import Any, Dict
from pymongo import MongoClient, ASCENDING, errors
from datetime import datetime
from config import Config
from models import UserModel, ChatModel, MoodModel, StressModel

client: MongoClient | None = None
db = None

def _build_client() -> MongoClient:
    if not Config.MONGODB_URI:
        raise RuntimeError('MONGODB_URI is not set. Please configure your .env')
    tls = getattr(Config, 'MONGODB_TLS', False)
    allow_invalid = getattr(Config, 'MONGODB_TLS_ALLOW_INVALID_CERTIFICATES', False)
    try:
        client = MongoClient(
            Config.MONGODB_URI,
            **({'tls': tls} if tls else {}),
            serverSelectionTimeoutMS=5000,
        )
        # Trigger server selection to validate connection
        client.admin.command('ping')
        return client
    except errors.ServerSelectionTimeoutError as e:
        raise RuntimeError(f'MongoDB connection timeout: {e}')
    except Exception as e:
        raise RuntimeError(f'Failed to connect to MongoDB: {e}')

def _ensure_indexes(database) -> None:
    models = [UserModel, ChatModel, MoodModel, StressModel]
    for model in models:
        coll = database[model.collection_name]
        # Common indexes
        if hasattr(model, 'index_specs'):
            for field, options in model.index_specs():
                coll.create_index([(field, ASCENDING)], **options)
        else:
            # Default indexes per model
            if model is UserModel:
                coll.create_index([('email', ASCENDING)], unique=True)
                coll.create_index([('created_at', ASCENDING)])
            elif model is ChatModel:
                coll.create_index([('user_email', ASCENDING)])
                coll.create_index([('type', ASCENDING)])
                coll.create_index([('created_at', ASCENDING)])
            elif model is MoodModel:
                coll.create_index([('user_email', ASCENDING)])
                coll.create_index([('created_at', ASCENDING)])
            elif model is StressModel:
                coll.create_index([('user_email', ASCENDING)])
                coll.create_index([('created_at', ASCENDING)])

def seed_demo_data(database) -> Dict[str, Any]:
    from utils.auth_helpers import hash_password
    users = database[UserModel.collection_name]
    chats = database[ChatModel.collection_name]
    moods = database[MoodModel.collection_name]
    stress = database[StressModel.collection_name]

    # Demo users with proper email domains for login page
    demo_users = [
        {
            'email': 'student@aura.edu',
            'hashed_password': hash_password('password123'),
            'name': 'Demo Student',
            'role': 'student',
            'created_at': datetime.utcnow(),
        },
        {
            'email': 'proctor@aura.edu',
            'hashed_password': hash_password('password123'),
            'name': 'Demo Proctor',
            'role': 'proctor',
            'created_at': datetime.utcnow(),
        },
        {
            'email': 'hod@aura.edu',
            'hashed_password': hash_password('password123'),
            'name': 'Demo HOD',
            'role': 'hod',
            'created_at': datetime.utcnow(),
        },
    ]
    for u in demo_users:
        users.update_one({'email': u['email']}, {'$setOnInsert': u}, upsert=True)

    # Demo chat
    chats.insert_one({
        'user_email': 'student@aura.edu',
        'message': 'I feel stressed about exams',
        'response': 'Let’s break tasks into smaller chunks.',
        'type': 'mental',
        'created_at': datetime.utcnow(),
    })

    # Demo mood
    moods.insert_one({
        'user_email': 'student@aura.edu',
        'mood': 'anxious',
        'intensity': 7,
        'created_at': datetime.utcnow(),
    })

    # Demo stress
    stress.insert_one({
        'user_email': 'student@aura.edu',
        'score': 62,
        'source': 'exams',
        'created_at': datetime.utcnow(),
    })

    return {
        'users': users.count_documents({}),
        'chats': chats.count_documents({}),
        'moods': moods.count_documents({}),
        'stress': stress.count_documents({}),
    }

def create_demo_users(database) -> int:
    from utils.auth_helpers import hash_password
    users = database[UserModel.collection_name]
    demo_users = [
        {
            'email': 'student@aura.edu',
            'hashed_password': hash_password('password123'),
            'name': 'Demo Student',
            'role': 'student',
            'created_at': datetime.utcnow(),
        },
        {
            'email': 'proctor@aura.edu',
            'hashed_password': hash_password('password123'),
            'name': 'Demo Proctor',
            'role': 'proctor',
            'created_at': datetime.utcnow(),
        },
        {
            'email': 'hod@aura.edu',
            'hashed_password': hash_password('password123'),
            'name': 'Demo HOD',
            'role': 'hod',
            'created_at': datetime.utcnow(),
        },
    ]
    inserted = 0
    for u in demo_users:
        res = users.update_one({'email': u['email']}, {'$setOnInsert': u}, upsert=True)
        # Count as inserted if upsert triggered
        if res.upserted_id is not None:
            inserted += 1
    return inserted

def init_db(app=None):
    global client, db
    client = _build_client()
    db = client[Config.MONGODB_DB_NAME]
    _ensure_indexes(db)
    return db


def get_db():
    """Return an active database connection, initializing if needed."""
    global db, client
    if db is not None:
        return db
    # Attempt to initialize if not already done
    try:
        init_db()
        return db
    except Exception as exc:
        raise RuntimeError(f'Database connection failed: {exc}')
