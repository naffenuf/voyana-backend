"""Debug test to see actual responses."""
import sys
sys.path.insert(0, '/app')

from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token, create_refresh_token
import json

# Create app
app = create_app('testing')

with app.app_context():
    # Create tables
    db.create_all()

    # Create a test user
    user = User(
        email='test@example.com',
        name='Test User',
        role='creator'
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    # Create tokens
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role, 'email': user.email}
    )
    refresh_token = create_refresh_token(identity=user.id)

    # Test client
    client = app.test_client()

    # Test 1: Create tour
    print("=" * 60)
    print("TEST 1: Create Tour")
    print("=" * 60)
    response = client.post('/api/tours',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        json={
            'name': 'New Tour',
            'description': 'A new exciting tour',
            'city': 'Manhattan',
            'neighborhood': 'Chelsea',
            'latitude': 40.7465,
            'longitude': -73.9977
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.get_json()}")

    # Test 2: Refresh token
    print("\n" + "=" * 60)
    print("TEST 2: Refresh Token")
    print("=" * 60)
    response = client.post('/auth/refresh',
        headers={
            'Authorization': f'Bearer {refresh_token}'
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.get_json()}")

    # Cleanup
    db.session.remove()
    db.drop_all()
