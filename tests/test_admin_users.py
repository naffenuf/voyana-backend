"""
Tests for Admin User Management API endpoints.
"""
import pytest
import json
from app.models.user import User
from app import db


class TestAdminListUsers:
    """Tests for GET /api/admin/users endpoint."""

    def test_list_all_users(self, client, admin_headers, test_user, admin_user):
        """Test listing all users as admin."""
        response = client.get('/api/admin/users', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'users' in data
        assert len(data['users']) >= 2  # At least test_user and admin_user

    def test_list_users_requires_admin(self, client, auth_headers):
        """Test that listing users requires admin role."""
        response = client.get('/api/admin/users', headers=auth_headers)

        assert response.status_code in [403, 401]

    def test_list_users_no_auth(self, client):
        """Test that listing users requires authentication."""
        response = client.get('/api/admin/users')

        assert response.status_code == 401


class TestAdminCreateUser:
    """Tests for POST /api/admin/users endpoint."""

    def test_create_user_success(self, client, admin_headers):
        """Test creating a new user as admin."""
        response = client.post('/api/admin/users', headers=admin_headers, json={
            'email': 'newuser@example.com',
            'name': 'New User',
            'password': 'SecurePassword123',
            'role': 'creator'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['email'] == 'newuser@example.com'
        assert data['role'] == 'creator'
        assert 'password' not in data  # Password should not be in response

    def test_create_user_duplicate_email(self, client, admin_headers, test_user):
        """Test creating user with duplicate email."""
        response = client.post('/api/admin/users', headers=admin_headers, json={
            'email': test_user.email,
            'name': 'Duplicate',
            'password': 'password123',
            'role': 'creator'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_user_invalid_role(self, client, admin_headers):
        """Test creating user with invalid role."""
        response = client.post('/api/admin/users', headers=admin_headers, json={
            'email': 'test@example.com',
            'name': 'Test',
            'password': 'password123',
            'role': 'superadmin'  # Invalid role
        })

        assert response.status_code == 400

    def test_create_user_requires_admin(self, client, auth_headers):
        """Test that creating users requires admin role."""
        response = client.post('/api/admin/users', headers=auth_headers, json={
            'email': 'test@example.com',
            'name': 'Test',
            'password': 'password123',
            'role': 'creator'
        })

        assert response.status_code in [403, 401]


class TestAdminGetUser:
    """Tests for GET /api/admin/users/<id> endpoint."""

    def test_get_user_success(self, client, admin_headers, test_user):
        """Test getting a specific user as admin."""
        response = client.get(f'/api/admin/users/{test_user.id}', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == test_user.id
        assert data['email'] == test_user.email
        assert 'password' not in data

    def test_get_user_not_found(self, client, admin_headers):
        """Test getting non-existent user."""
        response = client.get('/api/admin/users/999999', headers=admin_headers)

        assert response.status_code == 404

    def test_get_user_requires_admin(self, client, auth_headers, test_user):
        """Test that getting user details requires admin."""
        response = client.get(f'/api/admin/users/{test_user.id}', headers=auth_headers)

        assert response.status_code in [403, 401]


class TestAdminUpdateUser:
    """Tests for PUT /api/admin/users/<id> endpoint."""

    def test_update_user_success(self, app, client, admin_headers):
        """Test updating a user as admin."""
        with app.app_context():
            user = User(
                email='update@example.com',
                name='Original Name',
                role='creator'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        response = client.put(f'/api/admin/users/{user_id}', headers=admin_headers, json={
            'name': 'Updated Name',
            'email': 'updated@example.com'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Updated Name'
        assert data['email'] == 'updated@example.com'

    def test_update_user_role(self, app, client, admin_headers):
        """Test updating user role via dedicated endpoint."""
        with app.app_context():
            user = User(
                email='role@example.com',
                name='Test User',
                role='creator'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        response = client.put(f'/api/admin/users/{user_id}/role', headers=admin_headers, json={
            'role': 'admin'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['role'] == 'admin'

    def test_update_user_requires_admin(self, client, auth_headers, test_user):
        """Test that updating users requires admin role."""
        response = client.put(f'/api/admin/users/{test_user.id}', headers=auth_headers, json={
            'name': 'Hacked Name'
        })

        assert response.status_code in [403, 401]


class TestAdminDeactivateUser:
    """Tests for DELETE /api/admin/users/<id> endpoint."""

    def test_deactivate_user(self, app, client, admin_headers):
        """Test deactivating a user."""
        with app.app_context():
            user = User(
                email='deactivate@example.com',
                name='To Deactivate',
                role='creator',
                is_active=True
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        response = client.delete(f'/api/admin/users/{user_id}', headers=admin_headers)

        assert response.status_code == 200

        # Verify user is deactivated (not deleted)
        with app.app_context():
            user = User.query.get(user_id)
            assert user is not None
            assert user.is_active == False

    def test_deactivate_user_requires_admin(self, client, auth_headers, test_user):
        """Test that deactivating users requires admin role."""
        response = client.delete(f'/api/admin/users/{test_user.id}', headers=auth_headers)

        assert response.status_code in [403, 401]


class TestAdminResetPassword:
    """Tests for PUT /api/admin/users/<id>/password endpoint."""

    def test_reset_user_password(self, app, client, admin_headers):
        """Test resetting a user's password."""
        with app.app_context():
            user = User(
                email='resetpwd@example.com',
                name='Reset Password',
                role='creator'
            )
            user.set_password('oldpassword')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        response = client.put(f'/api/admin/users/{user_id}/password', headers=admin_headers, json={
            'password': 'NewSecurePassword123'
        })

        assert response.status_code == 200

        # Verify new password works
        with app.app_context():
            user = User.query.get(user_id)
            assert user.check_password('NewSecurePassword123')
            assert not user.check_password('oldpassword')

    def test_reset_password_weak(self, app, client, admin_headers):
        """Test resetting password with weak password."""
        with app.app_context():
            user = User(
                email='weak@example.com',
                name='Test',
                role='creator'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        response = client.put(f'/api/admin/users/{user_id}/password', headers=admin_headers, json={
            'password': '123'  # Too short
        })

        assert response.status_code == 400

    def test_reset_password_requires_admin(self, client, auth_headers, test_user):
        """Test that resetting passwords requires admin role."""
        response = client.put(f'/api/admin/users/{test_user.id}/password', headers=auth_headers, json={
            'password': 'NewPassword123'
        })

        assert response.status_code in [403, 401]
