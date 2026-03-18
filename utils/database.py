# TODO: ARCHITECTURE #10 - No ORM / schema validation
#   Consider using Pydantic models for request/response validation, or mongoengine
#   for ODM (Object-Document Mapping) to enforce schema consistency and type safety.

# TODO: ARCHITECTURE #12 - No database migration system
#   Add a migration system (like mongomock-mate, migrate-mongo, or a custom solution)
#   to handle schema changes, index updates, and data transformations safely across
#   deployments without manual intervention.

import threading
from typing import Any, Dict
from pymongo import MongoClient, ASCENDING, errors
from datetime import datetime
from config import Config
from models import UserModel, ChatModel, MoodModel, StressModel

# Thread-safe lazy initialization for database connection (#11)
_db_lock = threading.Lock()
client: MongoClient | None = None
db = None

def _build_client() -> MongoClient:
    if not Config.MONGODB_URI:
        raise RuntimeError('MONGODB_URI is not set. Please configure your .env')
    tls = getattr(Config, 'MONGODB_TLS', False)
    allow_invalid = getattr(Config, 'MONGODB_TLS_ALLOW_INVALID_CERTIFICATES', False)

    # Connection pooling configuration (#29 Scalability)
    # These settings optimize connection reuse and prevent connection exhaustion
    client_kwargs = {
        'serverSelectionTimeoutMS': 5000,
        # Pool size settings - adjust based on expected concurrent connections
        'maxPoolSize': 50,           # Max connections per server (default: 100, reduced for free tiers)
        'minPoolSize': 5,            # Minimum idle connections to maintain
        'maxIdleTimeMS': 30000,      # Close idle connections after 30s
        # Connection lifecycle
        'connectTimeoutMS': 10000,   # Timeout for initial connection
        'socketTimeoutMS': 30000,    # Timeout for socket operations
        # Write concern for data safety
        'retryWrites': True,         # Automatically retry failed writes
        'retryReads': True,          # Automatically retry failed reads
        # For serverless/free tier MongoDB Atlas, use smaller pool
        'waitQueueTimeoutMS': 10000, # Max time to wait for available connection
    }
    if tls:
        client_kwargs['tls'] = True
        if allow_invalid:
            client_kwargs['tlsAllowInvalidCertificates'] = True
    try:
        client = MongoClient(Config.MONGODB_URI, **client_kwargs)
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

    # ── RBAC indexes (role-based access control) ──
    # Use try/except to handle existing indexes with different names
    def _safe_index(coll, keys, **kwargs):
        try:
            coll.create_index(keys, **kwargs)
        except errors.OperationFailure as e:
            if e.code == 85:  # IndexOptionsConflict — index exists with different name
                pass
            else:
                raise

    ps = database['proctor_students']
    _safe_index(ps, [('proctor_id', ASCENDING)])
    _safe_index(ps, [('department', ASCENDING)])
    _safe_index(ps, [('anonymous_id', ASCENDING)])
    _safe_index(ps, [('status', ASCENDING)])
    _safe_index(ps, [('proctor_id', ASCENDING), ('status', ASCENDING)])
    _safe_index(ps, [('department', ASCENDING), ('status', ASCENDING)])

    ri = database['risk_incidents']
    _safe_index(ri, [('anonymous_student_id', ASCENDING)])
    _safe_index(ri, [('department', ASCENDING)])
    _safe_index(ri, [('anonymous_student_id', ASCENDING), ('status', ASCENDING)])

    # users role + department
    _safe_index(database['users'], [('role', ASCENDING)])
    _safe_index(database['users'], [('department', ASCENDING)])

# Demo user configuration - single source of truth
# Used by both create_demo_users() and seed_demo_data()
DEMO_USERS_CONFIG = [
    {
        'email': 'student@aura.edu',
        'name': 'Demo Student',
        'role': 'student',
        'roll_number': 'STU001',
        'parent_phone': '9876543210',
        'department': 'AIML',
    },
    {
        'email': 'proctor@aura.edu',
        'name': 'Demo Proctor',
        'role': 'proctor',
        'department': 'AIML',
    },
    {
        'email': 'hod@aura.edu',
        'name': 'Demo HOD',
        'role': 'hod',
        'department': 'AIML',
    },
]

# Demo password - stored separately for security visibility
DEMO_PASSWORD = 'DemoPass!2024#Secure'


def create_demo_users(database) -> int:
    """
    Create demo users in the database. This is the single source of truth
    for demo user configuration.

    Returns:
        Number of newly inserted users.
    """
    from utils.auth_helpers import hash_password
    users = database[UserModel.collection_name]

    inserted = 0
    for config in DEMO_USERS_CONFIG:
        user_doc = {
            **config,
            'hashed_password': hash_password(DEMO_PASSWORD),
            'created_at': datetime.utcnow(),
        }
        res = users.update_one(
            {'email': config['email']},
            {'$setOnInsert': user_doc},
            upsert=True
        )
        if res.upserted_id is not None:
            inserted += 1

    # Backfill critical fields for existing demo users
    users.update_one(
        {'email': 'student@aura.edu'},
        {'$set': {
            'roll_number': 'STU001',
            'parent_phone': '9876543210',
            'department': 'AIML'
        }}
    )
    users.update_one(
        {'email': 'proctor@aura.edu'},
        {'$set': {'department': 'AIML'}}
    )
    users.update_one(
        {'email': 'hod@aura.edu'},
        {'$set': {'department': 'AIML'}}
    )

    return inserted


def seed_demo_data(database) -> Dict[str, Any]:
    """
    Seed the database with demo data for testing and demonstration.
    Delegates user creation to create_demo_users() to avoid duplication.
    """
    users = database[UserModel.collection_name]
    chats = database[ChatModel.collection_name]
    moods = database[MoodModel.collection_name]
    stress = database[StressModel.collection_name]

    # Create demo users (single source of truth)
    create_demo_users(database)

    # Demo data - only seed if no demo data exists (prevents duplicates on restart)
    if chats.count_documents({'user_email': 'student@aura.edu'}) == 0:
        chats.insert_one({
            'user_email': 'student@aura.edu',
            'message': 'I feel stressed about exams',
            'response': "Let's break tasks into smaller chunks.",
            'type': 'mental',
            'created_at': datetime.utcnow(),
        })

    if moods.count_documents({'user_email': 'student@aura.edu'}) == 0:
        moods.insert_one({
            'user_email': 'student@aura.edu',
            'mood': 'anxious',
            'intensity': 7,
            'created_at': datetime.utcnow(),
        })

    if stress.count_documents({'user_email': 'student@aura.edu'}) == 0:
        stress.insert_one({
            'user_email': 'student@aura.edu',
            'score': 62,
            'source': 'exams',
            'created_at': datetime.utcnow(),
        })

    # Connection Hub seed data
    connection_rooms = database['room_messages']
    if connection_rooms.count_documents({'user_id': 'demo@aura.edu'}) == 0:
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

def init_db(app=None):
    """Initialize database connection with thread-safe lazy initialization."""
    global client, db
    with _db_lock:
        if db is not None:
            return db  # Already initialized
        client = _build_client()
        db = client[Config.MONGODB_DB_NAME]
        _ensure_indexes(db)
        seed_demo_data(db)
        return db


def get_db():
    """Return an active database connection, initializing if needed (thread-safe)."""
    global db, client
    # Fast path: already initialized
    if db is not None:
        return db
    # Slow path: acquire lock and initialize
    with _db_lock:
        # Double-check after acquiring lock
        if db is not None:
            return db
        # Attempt to initialize if not already done
        try:
            init_db()
            return db
        except Exception as exc:
            raise RuntimeError(f'Database connection failed: {exc}')


# ── Pagination Utility (#27 Scalability) ─────────────────────────────────────
def paginate_query(cursor, page: int = 1, per_page: int = 20, max_per_page: int = 100):
    """
    Apply pagination to a MongoDB cursor.

    Args:
        cursor: A PyMongo cursor from collection.find()
        page: Page number (1-indexed, defaults to 1)
        per_page: Number of items per page (defaults to 20)
        max_per_page: Maximum allowed items per page (defaults to 100)

    Returns:
        The cursor with skip/limit applied

    Usage:
        # In a route:
        from utils.database import get_db, paginate_query

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        cursor = db['collection'].find(query).sort('created_at', -1)
        results = list(paginate_query(cursor, page, per_page))

    Note: For total count (if needed for pagination UI), call:
        total = db['collection'].count_documents(query)
        total_pages = (total + per_page - 1) // per_page
    """
    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))
    skip = (page - 1) * per_page
    return cursor.skip(skip).limit(per_page)
