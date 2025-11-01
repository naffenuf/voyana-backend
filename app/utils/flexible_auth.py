"""
Flexible authentication decorator supporting both JWT and API key authentication.
"""
from datetime import datetime
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from app import db
from app.models.user import ApiKey, User


def flexible_auth_required(admin_only=False):
    """
    Decorator that accepts either JWT (Bearer token) or API key (X-API-Key header).

    Sets g.current_user and g.auth_method ('jwt' or 'api_key').
    Optionally enforces admin role when admin_only=True.

    Usage:
        @flexible_auth_required()
        def my_endpoint():
            user_id = g.current_user.id
            # ... endpoint logic

        @flexible_auth_required(admin_only=True)
        def admin_endpoint():
            # Only accessible to admins (via JWT or API key)
            # ... endpoint logic
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for API key first
            api_key = request.headers.get('X-API-Key')

            if api_key:
                # Authenticate with API key
                key_obj = ApiKey.query.filter_by(key=api_key).first()

                if not key_obj:
                    return jsonify({
                        'error': 'Invalid API key',
                        'message': 'The provided API key is not valid'
                    }), 401

                if not key_obj.is_active:
                    return jsonify({
                        'error': 'API key inactive',
                        'message': 'This API key has been deactivated'
                    }), 401

                if not key_obj.user.is_active:
                    return jsonify({
                        'error': 'User account inactive',
                        'message': 'The user associated with this API key is inactive'
                    }), 401

                # Check admin role if required
                if admin_only and key_obj.user.role != 'admin':
                    return jsonify({
                        'error': 'Admin access required',
                        'message': 'This endpoint requires admin privileges'
                    }), 403

                # Update last_used_at timestamp
                key_obj.last_used_at = datetime.utcnow()
                db.session.commit()

                # Store user and auth method in g
                g.current_user = key_obj.user
                g.auth_method = 'api_key'

            else:
                # Authenticate with JWT
                try:
                    verify_jwt_in_request()
                except Exception as e:
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'Please provide either a valid JWT token or API key'
                    }), 401

                # Get user from JWT
                user_id = get_jwt_identity()
                user = User.query.get(user_id)

                if not user:
                    return jsonify({
                        'error': 'User not found',
                        'message': 'The user associated with this token does not exist'
                    }), 401

                if not user.is_active:
                    return jsonify({
                        'error': 'User account inactive',
                        'message': 'Your account has been deactivated'
                    }), 401

                # Check admin role if required
                if admin_only:
                    claims = get_jwt()
                    if claims.get('role') != 'admin':
                        return jsonify({
                            'error': 'Admin access required',
                            'message': 'This endpoint requires admin privileges'
                        }), 403

                # Store user and auth method in g
                g.current_user = user
                g.auth_method = 'jwt'

            return f(*args, **kwargs)

        return decorated_function
    return decorator
