"""
Tests for Authentication API endpoints.
"""
import pytest
import json
from datetime import timedelta
from flask import current_app
from flask_jwt_extended import decode_token
from app.models.user import User, PasswordResetToken
from app import db


class TestDeviceRegistration:
    """Tests for /auth/register-device endpoint."""

    def test_register_device_success(self, client):
        """Test successful device registration."""
        response = client.post('/auth/register-device', json={
            'api_key': 'test-admin-key',
            'device_id': 'test-device-123',
            'device_name': 'iPhone 15'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'expires_in' in data
        assert data['expires_in'] == 31536000  # 1 year in seconds

    def test_register_device_invalid_api_key(self, client):
        """Test device registration with invalid API key."""
        response = client.post('/auth/register-device', json={
            'api_key': 'wrong-key',
            'device_id': 'test-device-123',
            'device_name': 'iPhone 15'
        })

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Invalid API key'

    def test_register_device_missing_device_id(self, client):
        """Test device registration without device_id."""
        response = client.post('/auth/register-device', json={
            'api_key': 'test-admin-key',
            'device_name': 'iPhone 15'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'device_id' in data['error']

    def test_register_device_missing_api_key(self, client):
        """Test device registration without API key."""
        response = client.post('/auth/register-device', json={
            'device_id': 'test-device-123',
            'device_name': 'iPhone 15'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'api_key' in data['error']

    def test_register_device_jwt_claims(self, app, client):
        """Test that device registration creates JWT with correct claims."""
        response = client.post('/auth/register-device', json={
            'api_key': 'test-admin-key',
            'device_id': 'test-device-456',
            'device_name': 'iPad Pro'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        token = data['access_token']

        # Decode and verify token claims
        with app.app_context():
            decoded = decode_token(token)
            assert decoded['sub'] == 'device:test-device-456'
            assert decoded['type'] == 'device'
            assert decoded['device_id'] == 'test-device-456'
            assert decoded['device_name'] == 'iPad Pro'


class TestUserRegistration:
    """Tests for /auth/register endpoint."""

    def test_register_user_success(self, client):
        """Test successful user registration."""
        response = client.post('/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'SecurePassword123',
            'name': 'New User'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'user' in data
        assert data['user']['email'] == 'newuser@example.com'
        assert data['user']['name'] == 'New User'
        assert data['user']['role'] == 'creator'
        assert 'password' not in data['user']

    def test_register_user_duplicate_email(self, client, test_user):
        """Test registration with existing email."""
        response = client.post('/auth/register', json={
            'email': test_user.email,
            'password': 'password123',
            'name': 'Duplicate User'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'already registered' in data['error'].lower()

    def test_register_user_missing_email(self, client):
        """Test registration without email."""
        response = client.post('/auth/register', json={
            'password': 'password123',
            'name': 'No Email'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_register_user_missing_password(self, client):
        """Test registration without password."""
        response = client.post('/auth/register', json={
            'email': 'nopass@example.com',
            'name': 'No Password'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_register_user_creates_database_entry(self, app, client):
        """Test that registration creates user in database."""
        response = client.post('/auth/register', json={
            'email': 'dbtest@example.com',
            'password': 'password123',
            'name': 'DB Test'
        })

        assert response.status_code == 201

        # Verify user was created in database
        with app.app_context():
            user = User.query.filter_by(email='dbtest@example.com').first()
            assert user is not None
            assert user.name == 'DB Test'
            assert user.role == 'creator'
            assert user.check_password('password123')


class TestUserLogin:
    """Tests for /auth/login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post('/auth/login', json={
            'email': test_user.email,
            'password': 'password123'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'user' in data
        assert data['user']['email'] == test_user.email

    def test_login_invalid_email(self, client):
        """Test login with non-existent email."""
        response = client.post('/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'password123'
        })

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'invalid' in data['error'].lower()

    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post('/auth/login', json={
            'email': test_user.email,
            'password': 'wrongpassword'
        })

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'invalid' in data['error'].lower()

    def test_login_inactive_user(self, app, client, test_user):
        """Test that inactive users cannot login."""
        # Deactivate user
        with app.app_context():
            user = User.query.get(test_user.id)
            user.is_active = False
            db.session.commit()

        response = client.post('/auth/login', json={
            'email': test_user.email,
            'password': 'password123'
        })

        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'error' in data
        assert 'inactive' in data['error'].lower()

    def test_login_updates_last_login(self, app, client, test_user):
        """Test that login updates last_login_at timestamp."""
        # Get original last_login_at
        with app.app_context():
            user = User.query.get(test_user.id)
            original_last_login = user.last_login_at

        # Login
        response = client.post('/auth/login', json={
            'email': test_user.email,
            'password': 'password123'
        })

        assert response.status_code == 200

        # Verify last_login_at was updated
        with app.app_context():
            user = User.query.get(test_user.id)
            assert user.last_login_at is not None
            if original_last_login:
                assert user.last_login_at > original_last_login


class TestTokenRefresh:
    """Tests for /auth/refresh endpoint."""

    def test_refresh_token_success(self, app, client, test_user):
        """Test successful token refresh."""
        from flask_jwt_extended import create_refresh_token

        # Create a refresh token
        with app.app_context():
            refresh_token = create_refresh_token(identity=test_user.id)

        # Use refresh token to get new access token
        response = client.post('/auth/refresh', headers={
            'Authorization': f'Bearer {refresh_token}'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data

    def test_refresh_token_invalid_user(self, app, client):
        """Test refresh with non-existent user ID."""
        from flask_jwt_extended import create_refresh_token

        # Create refresh token for non-existent user
        with app.app_context():
            refresh_token = create_refresh_token(identity=99999)

        response = client.post('/auth/refresh', headers={
            'Authorization': f'Bearer {refresh_token}'
        })

        assert response.status_code == 401

    def test_refresh_token_inactive_user(self, app, client, test_user):
        """Test refresh with inactive user."""
        from flask_jwt_extended import create_refresh_token

        # Create refresh token
        with app.app_context():
            refresh_token = create_refresh_token(identity=test_user.id)

        # Deactivate user
        with app.app_context():
            user = User.query.get(test_user.id)
            user.is_active = False
            db.session.commit()

        # Try to refresh
        response = client.post('/auth/refresh', headers={
            'Authorization': f'Bearer {refresh_token}'
        })

        assert response.status_code == 401


class TestGetCurrentUser:
    """Tests for /auth/me endpoint."""

    def test_get_current_user_success(self, client, auth_headers, test_user):
        """Test getting current user profile."""
        response = client.get('/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data
        assert data['user']['email'] == test_user.email
        assert data['user']['id'] == test_user.id

    def test_get_current_user_no_token(self, client):
        """Test that endpoint requires authentication."""
        response = client.get('/auth/me')

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test with invalid token."""
        response = client.get('/auth/me', headers={
            'Authorization': 'Bearer invalid-token'
        })

        assert response.status_code == 422


class TestPasswordReset:
    """Tests for password reset endpoints."""

    def test_forgot_password_existing_email(self, app, client, test_user):
        """Test forgot password with existing email."""
        response = client.post('/auth/forgot-password', json={
            'email': test_user.email
        })

        # Should always return 200 (even for existing email)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify token was created
        with app.app_context():
            token = PasswordResetToken.query.filter_by(user_id=test_user.id).first()
            assert token is not None
            assert token.is_valid()

    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with non-existent email."""
        response = client.post('/auth/forgot-password', json={
            'email': 'nonexistent@example.com'
        })

        # Should return 200 to prevent email enumeration
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

    def test_forgot_password_no_email(self, client):
        """Test forgot password without email."""
        response = client.post('/auth/forgot-password', json={})

        # Should return 200 to prevent email enumeration
        assert response.status_code == 200

    def test_reset_password_success(self, app, client, test_user):
        """Test successful password reset."""
        # Create reset token
        with app.app_context():
            token = PasswordResetToken.create_for_user(test_user)
            db.session.add(token)
            db.session.commit()
            token_string = token.token

        # Reset password
        response = client.post('/auth/reset-password', json={
            'token': token_string,
            'new_password': 'NewSecurePassword123'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify password was changed
        with app.app_context():
            user = User.query.get(test_user.id)
            assert user.check_password('NewSecurePassword123')
            assert not user.check_password('password123')

        # Verify token was marked as used
        with app.app_context():
            token = PasswordResetToken.query.filter_by(token=token_string).first()
            assert token.used is True

    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token."""
        response = client.post('/auth/reset-password', json={
            'token': 'invalid-token',
            'new_password': 'NewPassword123'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_reset_password_missing_fields(self, client):
        """Test password reset with missing fields."""
        response = client.post('/auth/reset-password', json={
            'token': 'some-token'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
