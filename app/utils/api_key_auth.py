"""
API key authentication decorator.
"""
from datetime import datetime
from functools import wraps
from flask import request, jsonify, g
from app import db
from app.models.user import ApiKey


def api_key_required():
    """
    Decorator to require API key authentication.

    Checks for X-API-Key header, validates the key, and sets g.current_user.
    Updates last_used_at timestamp on successful authentication.

    Usage:
        @api_key_required()
        def my_endpoint():
            user_id = g.current_user.id
            # ... endpoint logic
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get API key from header
            api_key = request.headers.get('X-API-Key')

            if not api_key:
                return jsonify({
                    'error': 'Missing API key',
                    'message': 'Please provide an API key in the X-API-Key header'
                }), 401

            # Query for the API key
            key_obj = ApiKey.query.filter_by(key=api_key).first()

            if not key_obj:
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is not valid'
                }), 401

            # Check if key is active
            if not key_obj.is_active:
                return jsonify({
                    'error': 'API key inactive',
                    'message': 'This API key has been deactivated'
                }), 401

            # Check if associated user is active
            if not key_obj.user.is_active:
                return jsonify({
                    'error': 'User account inactive',
                    'message': 'The user associated with this API key is inactive'
                }), 401

            # Update last_used_at timestamp
            key_obj.last_used_at = datetime.utcnow()
            db.session.commit()

            # Store user in g for access in the endpoint
            g.current_user = key_obj.user
            g.auth_method = 'api_key'

            return f(*args, **kwargs)

        return decorated_function
    return decorator
