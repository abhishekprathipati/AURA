from app import app
import pytest

def test_app_initialization():
    """Verify that the Flask app can be initialized without crashing."""
    assert app is not None
    assert app.name == 'app'

def test_config_loading():
    """Verify that the configuration is loaded."""
    assert 'SECRET_KEY' in app.config
    assert 'MONGODB_URI' in app.config
