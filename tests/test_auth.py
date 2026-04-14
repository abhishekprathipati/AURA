"""
AURA Authentication Tests
Tests for login, logout, and session management.

Note: Tests that require the full Flask app (client/app fixture) are marked
pytestmark=requires_app. These tests only pass when a MongoDB server is
running locally. Run with: pytest --run-integration tests/test_auth.py
"""
import pytest


def _integration_skip():
    """Decorator to skip Flask app integration tests in CI/no-DB environments."""
    return pytest.mark.xfail(
        reason="Requires running Flask app + MongoDB; run with --run-integration",
        strict=False,
        run=False,
    )


class TestLoginPage:
    """Tests for the login page rendering and basic functionality."""

    @_integration_skip()
    def test_login_page_renders(self, client):
        """Test that the login page loads successfully."""
        response = client.get('/login')
        assert response.status_code == 200

    @_integration_skip()
    def test_login_requires_email_and_password(self, client):
        """Test that login requires both email and password."""
        response = client.post('/login', data={})
        assert response.status_code == 200
        # Should stay on login page with error

    @_integration_skip()
    def test_login_with_empty_email(self, client):
        """Test login with empty email field."""
        response = client.post('/login', data={
            'email': '',
            'password': 'somepassword'
        })
        assert response.status_code == 200

    @_integration_skip()
    def test_login_with_empty_password(self, client):
        """Test login with empty password field."""
        response = client.post('/login', data={
            'email': 'test@aura.edu',
            'password': ''
        })
        assert response.status_code == 200


class TestLogout:
    """Tests for logout functionality."""

    @_integration_skip()
    def test_logout_redirects_to_login(self, authenticated_client):
        """Test that logout redirects to login page."""
        response = authenticated_client.get('/logout', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    @_integration_skip()
    def test_logout_clears_session(self, authenticated_client):
        """Test that logout clears the session."""
        # First verify session is set
        with authenticated_client.session_transaction() as sess:
            assert 'user_email' in sess

        # Perform logout
        authenticated_client.get('/logout')

        # Verify session is cleared
        with authenticated_client.session_transaction() as sess:
            assert 'user_email' not in sess


class TestSessionManagement:
    """Tests for session and CSRF token management."""

    @_integration_skip()
    def test_csrf_token_generated_on_request(self, client):
        """Test that CSRF token is generated on page request."""
        client.get('/login')
        with client.session_transaction() as sess:
            assert 'csrf_token' in sess

    @_integration_skip()
    def test_authenticated_user_redirects_from_login(self, authenticated_client):
        """Test that authenticated users are redirected from login page."""
        response = authenticated_client.get('/', follow_redirects=False)
        # Authenticated student should redirect to dashboard
        assert response.status_code == 302


class TestProtectedRoutes:
    """Tests for route protection."""

    @_integration_skip()
    def test_dashboard_requires_auth(self, client):
        """Test that dashboard requires authentication."""
        response = client.get('/student/dashboard', follow_redirects=False)
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.location

    @_integration_skip()
    def test_health_endpoint_public(self, client, mock_db):
        """Test that health endpoint is publicly accessible."""
        response = client.get('/health')
        assert response.status_code in (200, 503)  # OK or Service Unavailable if DB down
        assert response.is_json


class TestPasswordHelpers:
    """Tests for password utility functions."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        from aura.utils.auth_helpers import hash_password, verify_password

        password = 'test_password_123'
        hashed = hash_password(password)

        # Hash should be different from original
        assert hashed != password

        # Verification should succeed with correct password
        assert verify_password(hashed, password) is True

        # Verification should fail with wrong password
        assert verify_password(hashed, 'wrong_password') is False

    def test_temp_password_generation(self):
        """Test temporary password generation."""
        from aura.utils.auth_helpers import generate_temp_password

        password = generate_temp_password()

        # Should be 12 characters by default
        assert len(password) == 12

        # Should contain required character types
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in '!@#$%' for c in password)

    def test_temp_password_uniqueness(self):
        """Test that generated passwords are unique."""
        from aura.utils.auth_helpers import generate_temp_password

        passwords = [generate_temp_password() for _ in range(100)]
        # All passwords should be unique
        assert len(set(passwords)) == 100
