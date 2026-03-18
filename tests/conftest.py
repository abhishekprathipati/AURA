"""
AURA Test Configuration
Provides pytest fixtures for testing Flask application components.
"""
import os
import sys
import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set testing environment variables before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['TESTING'] = 'true'
os.environ['MONGODB_URI'] = 'mongodb://localhost:27017/aura_test'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['SMS_ENABLED'] = 'false'


@pytest.fixture(scope='session')
def app():
    """Create and configure a test application instance."""
    from app import app as flask_app

    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
    })

    yield flask_app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def mock_db(monkeypatch):
    """Mock database connection for unit tests that don't need real DB."""
    class MockCollection:
        def __init__(self):
            self._data = []

        def find_one(self, query=None, *args, **kwargs):
            return None

        def find(self, query=None, *args, **kwargs):
            return MockCursor([])

        def insert_one(self, doc):
            self._data.append(doc)
            return type('Result', (), {'inserted_id': 'mock_id'})()

        def update_one(self, query, update, **kwargs):
            return type('Result', (), {'modified_count': 1, 'upserted_id': None})()

        def update_many(self, query, update, **kwargs):
            return type('Result', (), {'modified_count': 1})()

        def count_documents(self, query=None):
            return 0

        def delete_many(self, query):
            return type('Result', (), {'deleted_count': 0})()

    class MockCursor:
        def __init__(self, data):
            self._data = data

        def sort(self, *args, **kwargs):
            return self

        def limit(self, n):
            return self

        def __iter__(self):
            return iter(self._data)

        def __list__(self):
            return self._data

    class MockDB:
        def __init__(self):
            self._collections = {}

        def __getitem__(self, name):
            if name not in self._collections:
                self._collections[name] = MockCollection()
            return self._collections[name]

        def command(self, cmd):
            return {'ok': 1}

    mock_database = MockDB()

    def mock_get_db():
        return mock_database

    monkeypatch.setattr('utils.database.get_db', mock_get_db)
    return mock_database


@pytest.fixture
def authenticated_client(client, mock_db):
    """Create a test client with an authenticated session."""
    with client.session_transaction() as sess:
        sess['user_email'] = 'test@aura.edu'
        sess['user_name'] = 'Test User'
        sess['user_role'] = 'student'
        sess['csrf_token'] = 'test-csrf-token'
    return client
