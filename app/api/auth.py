"""
Authentication API endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from datetime import timedelta
from app import db, limiter
from app.models.user import User, PasswordResetToken

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register-device', methods=['POST'])
@limiter.limit("10 per hour", key_func=lambda: request.remote_addr)
def register_device():
    """
    Register a device and get JWT token (no user account required).

    Request body:
        {
            "api_key": "xxx",
            "device_id": "xxx",
            "device_name": "iPhone 15"  (optional)
        }

    Returns:
        {
            "access_token": "...",
            "expires_in": 31536000  (1 year in seconds)
        }
    """
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('api_key') or not data.get('device_id'):
        return jsonify({'error': 'api_key and device_id are required'}), 400

    # Validate API key against configured admin key
    valid_api_key = current_app.config.get('ADMIN_API_KEY')
    if not valid_api_key or data['api_key'] != valid_api_key:
        return jsonify({'error': 'Invalid API key'}), 401

    device_id = data['device_id']
    device_name = data.get('device_name', 'Unknown Device')

    # Create JWT token with device identity (1 year expiry)
    access_token = create_access_token(
        identity=f"device:{device_id}",
        additional_claims={
            'type': 'device',
            'device_id': device_id,
            'device_name': device_name
        },
        expires_delta=timedelta(days=365)
    )

    return jsonify({
        'access_token': access_token,
        'expires_in': 31536000  # 1 year in seconds
    }), 200


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per hour", key_func=lambda: request.remote_addr)
def register():
    """
    Register a new user.

    Request body:
        {
            "email": "user@example.com",
            "password": "SecurePassword123",
            "name": "John Doe"
        }

    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "user": {...}
        }
    """
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    # Create user
    user = User(
        email=data['email'],
        name=data.get('name'),
        role='creator'  # Default role
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    # Create tokens
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role, 'email': user.email}
    )
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("20 per hour", key_func=lambda: request.remote_addr)
def login():
    """
    Log in an existing user.

    Request body:
        {
            "email": "user@example.com",
            "password": "SecurePassword123"
        }

    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "user": {...}
        }
    """
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    # Find user
    user = User.query.filter_by(email=data['email']).first()

    # Check credentials
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Check if user is active
    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 403

    # Update last login
    user.last_login_at = db.func.now()
    db.session.commit()

    # Create tokens
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role, 'email': user.email}
    )
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.

    Headers:
        Authorization: Bearer <refresh_token>

    Returns:
        {
            "access_token": "..."
        }
    """
    identity = get_jwt_identity()
    user = User.query.get(int(identity))

    if not user or not user.is_active:
        return jsonify({'error': 'Invalid user'}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role, 'email': user.email}
    )

    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current user profile.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        {
            "user": {...}
        }
    """
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("5 per hour", key_func=lambda: request.remote_addr)
def forgot_password():
    """
    Request password reset token.

    Request body:
        {
            "email": "user@example.com"
        }

    Returns:
        {
            "message": "If the email exists, a reset link has been sent"
        }

    Note: Always returns success to prevent email enumeration
    """
    data = request.get_json()
    email = data.get('email')

    # Always return success (prevent email enumeration)
    if not email:
        return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200

    user = User.query.filter_by(email=email).first()

    if user:
        # Create reset token
        token = PasswordResetToken.create_for_user(user)
        db.session.add(token)
        db.session.commit()

        # TODO: Send email with reset link
        # email_service.send_password_reset(user.email, token.token)
        pass

    return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Reset password using token from email.

    Request body:
        {
            "token": "reset_token_from_email",
            "new_password": "NewSecurePassword456"
        }

    Returns:
        {
            "message": "Password updated successfully"
        }
    """
    data = request.get_json()
    token_string = data.get('token')
    new_password = data.get('new_password')

    if not token_string or not new_password:
        return jsonify({'error': 'Token and new password are required'}), 400

    # Find token
    token = PasswordResetToken.query.filter_by(token=token_string).first()

    if not token or not token.is_valid():
        return jsonify({'error': 'Invalid or expired token'}), 400

    # Update password
    user = token.user
    user.set_password(new_password)
    token.used = True

    db.session.commit()

    return jsonify({'message': 'Password updated successfully'}), 200
