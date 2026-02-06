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
    
    # Connection Hub indexes
    room_msgs = database['room_messages']
    room_msgs.create_index([('room_id', ASCENDING)])
    room_msgs.create_index([('created_at', ASCENDING)])
    room_msgs.create_index([('user_id', ASCENDING)])
    
    ts_coll = database['message_timestamps']
    ts_coll.create_index([('user_id', ASCENDING)], unique=True)

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
            'roll_number': 'STU001',
            'parent_phone': '9876543210',
            'department': 'Computer Science',
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

    # Ensure existing demo student has academic fields (parent phone for OTP auth)
    users.update_one(
        {'email': 'student@aura.edu'},
        {'$set': {
            'roll_number': 'STU001',
            'parent_phone': '9876543210',
            'department': 'Computer Science'
        }}
    )

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
    
    # Connection Hub seed data
    connection_rooms = database['room_messages']
    demo_messages = [
        {
            'room_id': 'exam_stress',
            'user_id': 'demo@aura.edu',
            'display_name': 'Anonymous Student',
            'message': 'Anyone else feeling the exam pressure? Lets talk about it.',
            'created_at': datetime.utcnow(),
        },
        {
            'room_id': 'exam_stress',
            'user_id': 'demo2@aura.edu',
            'display_name': 'Anonymous Student',
            'message': 'Ive been studying for 6 hours straight. Feeling burned out!',
            'created_at': datetime.utcnow(),
        },
    ]
    for msg in demo_messages:
        connection_rooms.insert_one(msg)

    return {
        'users': users.count_documents({}),
        'chats': chats.count_documents({}),
        'moods': moods.count_documents({}),
        'stress': stress.count_documents({}),
        'connection_messages': connection_rooms.count_documents({}),
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
            'roll_number': 'STU001',
            'parent_phone': '9876543210',
            'department': 'Computer Science',
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
        if res.upserted_id is not None:
            inserted += 1

    # Ensure existing demo student has academic fields (parent phone for OTP auth)
    users.update_one(
        {'email': 'student@aura.edu'},
        {'$set': {
            'roll_number': 'STU001',
            'parent_phone': '9876543210',
            'department': 'Computer Science'
        }}
    )
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
