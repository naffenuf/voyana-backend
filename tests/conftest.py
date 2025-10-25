"""
Test configuration and fixtures for the Voyana Tours Server.
"""
import pytest
import os
from app import create_app, db
from app.models.user import User
from app.models.tour import Tour
from app.models.site import Site
from flask_jwt_extended import create_access_token


@pytest.fixture(scope='function')
def app():
    """Create and configure a test application instance."""
    # Set testing environment variables BEFORE creating app
    test_env = {
        'TESTING': 'true',
        'JWT_SECRET_KEY': 'test-secret-key',
        'SECRET_KEY': 'test-secret',
        'ADMIN_API_KEY': 'test-admin-key',
    }

    for key, value in test_env.items():
        os.environ[key] = value

    # Create app with testing config
    _app = create_app('testing')

    # Create application context
    with _app.app_context():
        # Create all database tables
        db.create_all()

        yield _app

        # Cleanup
        db.session.remove()
        db.drop_all()

    # Clean up environment
    for key in test_env.keys():
        os.environ.pop(key, None)


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    """Create a test user."""
    user = User(
        email='test@example.com',
        name='Test User',
        role='creator'
    )
    user.set_password('password123')

    db.session.add(user)
    db.session.commit()

    return user


@pytest.fixture
def admin_user(app):
    """Create an admin user."""
    user = User(
        email='admin@example.com',
        name='Admin User',
        role='admin'
    )
    user.set_password('admin123')

    db.session.add(user)
    db.session.commit()

    return user


@pytest.fixture
def auth_token(app, test_user):
    """Generate a valid JWT token for the test user."""
    with app.app_context():
        token = create_access_token(
            identity=str(test_user.id),
            additional_claims={'role': test_user.role, 'email': test_user.email}
        )
    return token


@pytest.fixture
def admin_token(app, admin_user):
    """Generate a valid JWT token for the admin user."""
    with app.app_context():
        token = create_access_token(
            identity=str(admin_user.id),
            additional_claims={'role': admin_user.role, 'email': admin_user.email}
        )
    return token


@pytest.fixture
def device_token(app):
    """Generate a valid device JWT token."""
    with app.app_context():
        token = create_access_token(
            identity="device:test-device-123",
            additional_claims={
                'type': 'device',
                'device_id': 'test-device-123',
                'device_name': 'Test iPhone'
            }
        )
    return token


@pytest.fixture
def test_tour(app, test_user):
    """Create a test tour."""
    tour = Tour(
        owner_id=test_user.id,
        name='Test Tour',
        description='A test tour description',
        city='New York',
        neighborhood='SoHo',
        latitude=40.7241,
        longitude=-73.9973,
        status='live',
        is_public=True
    )

    db.session.add(tour)
    db.session.commit()

    return tour


@pytest.fixture
def draft_tour(app, test_user):
    """Create a draft tour."""
    tour = Tour(
        owner_id=test_user.id,
        name='Draft Tour',
        description='A draft tour',
        city='Brooklyn',
        neighborhood='Williamsburg',
        status='draft',
        is_public=False
    )

    db.session.add(tour)
    db.session.commit()

    return tour


@pytest.fixture
def test_site(app):
    """Create a test site."""
    site = Site(
        title='Test Site',
        description='A test site description',
        latitude=40.7241,
        longitude=-73.9973,
        formatted_address='123 Test St, New York, NY 10013',
        place_id='test_place_id_123'
    )

    db.session.add(site)
    db.session.commit()

    return site


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers with JWT token."""
    return {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def admin_headers(admin_token):
    """Create authorization headers with admin JWT token."""
    return {
        'Authorization': f'Bearer {admin_token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def device_headers(device_token):
    """Create authorization headers with device JWT token."""
    return {
        'Authorization': f'Bearer {device_token}',
        'Content-Type': 'application/json'
    }
