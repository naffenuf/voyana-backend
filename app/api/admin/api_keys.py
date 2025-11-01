"""
API key management endpoints (admin only).
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models.user import ApiKey, User
from app.utils.admin_required import admin_required

api_keys_bp = Blueprint('api_keys', __name__)


@api_keys_bp.route('', methods=['POST'])
@jwt_required()
@admin_required()
def create_api_key():
    """
    Create a new API key (admin only).

    Request body:
        {
            "name": "Tour Generation Agent",
            "userId": 1  # Optional, defaults to current user
        }

    Returns:
        {
            "id": 1,
            "name": "Tour Generation Agent",
            "key": "abc123...",
            "createdAt": "2025-11-01T12:00:00",
            "isActive": true
        }
    """
    try:
        data = request.get_json()

        if not data or not data.get('name'):
            return jsonify({
                'error': 'Invalid request',
                'message': 'API key name is required'
            }), 400

        # Get user ID (can create keys for other users if admin)
        user_id = data.get('userId', get_jwt_identity())

        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': f'User with ID {user_id} does not exist'
            }), 404

        # Check if user is admin (only admins can create keys)
        if user.role != 'admin':
            return jsonify({
                'error': 'Invalid user',
                'message': 'API keys can only be created for admin users'
            }), 400

        # Generate API key
        api_key = ApiKey(
            key=ApiKey.generate_key(),
            name=data['name'],
            user_id=user_id,
            is_active=True
        )

        db.session.add(api_key)
        db.session.commit()

        current_app.logger.info(f"Created API key '{api_key.name}' for user {user_id}")

        return jsonify({
            'id': api_key.id,
            'name': api_key.name,
            'key': api_key.key,  # Only returned once!
            'userId': api_key.user_id,
            'createdAt': api_key.created_at.isoformat(),
            'isActive': api_key.is_active
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating API key: {e}")
        return jsonify({
            'error': 'Failed to create API key',
            'message': str(e)
        }), 500


@api_keys_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_api_keys():
    """
    List all API keys (admin only).

    Query params:
        - userId: Filter by user ID
        - isActive: Filter by active status (true/false)

    Returns:
        {
            "apiKeys": [
                {
                    "id": 1,
                    "name": "Tour Generation Agent",
                    "userId": 1,
                    "createdAt": "2025-11-01T12:00:00",
                    "lastUsedAt": "2025-11-01T14:30:00",
                    "isActive": true
                }
            ]
        }
    """
    try:
        # Build query
        query = ApiKey.query

        # Filter by user ID
        user_id = request.args.get('userId')
        if user_id:
            try:
                query = query.filter_by(user_id=int(user_id))
            except ValueError:
                return jsonify({
                    'error': 'Invalid user ID',
                    'message': 'User ID must be an integer'
                }), 400

        # Filter by active status
        is_active = request.args.get('isActive')
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            query = query.filter_by(is_active=is_active_bool)

        # Execute query
        api_keys = query.order_by(ApiKey.created_at.desc()).all()

        return jsonify({
            'apiKeys': [{
                'id': key.id,
                'name': key.name,
                'userId': key.user_id,
                'userName': key.user.name if key.user else None,
                'createdAt': key.created_at.isoformat(),
                'lastUsedAt': key.last_used_at.isoformat() if key.last_used_at else None,
                'isActive': key.is_active
            } for key in api_keys]
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error listing API keys: {e}")
        return jsonify({
            'error': 'Failed to list API keys',
            'message': str(e)
        }), 500


@api_keys_bp.route('/<int:key_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_api_key(key_id):
    """
    Delete (revoke) an API key permanently (admin only).

    Returns:
        {
            "message": "API key deleted successfully"
        }
    """
    try:
        api_key = ApiKey.query.get(key_id)

        if not api_key:
            return jsonify({
                'error': 'API key not found',
                'message': f'API key with ID {key_id} does not exist'
            }), 404

        db.session.delete(api_key)
        db.session.commit()

        current_app.logger.info(f"Deleted API key '{api_key.name}' (ID: {key_id})")

        return jsonify({
            'message': 'API key deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting API key: {e}")
        return jsonify({
            'error': 'Failed to delete API key',
            'message': str(e)
        }), 500


@api_keys_bp.route('/<int:key_id>', methods=['PATCH'])
@jwt_required()
@admin_required()
def update_api_key(key_id):
    """
    Update an API key (admin only).

    Currently supports toggling active status and updating name.

    Request body:
        {
            "isActive": false,
            "name": "New Name"  # Optional
        }

    Returns:
        {
            "id": 1,
            "name": "Tour Generation Agent",
            "isActive": false,
            "updatedAt": "2025-11-01T15:00:00"
        }
    """
    try:
        api_key = ApiKey.query.get(key_id)

        if not api_key:
            return jsonify({
                'error': 'API key not found',
                'message': f'API key with ID {key_id} does not exist'
            }), 404

        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required'
            }), 400

        # Update active status
        if 'isActive' in data:
            api_key.is_active = bool(data['isActive'])

        # Update name
        if 'name' in data and data['name']:
            api_key.name = data['name']

        db.session.commit()

        current_app.logger.info(f"Updated API key '{api_key.name}' (ID: {key_id})")

        return jsonify({
            'id': api_key.id,
            'name': api_key.name,
            'isActive': api_key.is_active,
            'updatedAt': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating API key: {e}")
        return jsonify({
            'error': 'Failed to update API key',
            'message': str(e)
        }), 500
