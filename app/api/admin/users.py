"""
Admin user management endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from app import db
from app.models.user import User
from app.utils.admin_required import admin_required

admin_users_bp = Blueprint('admin_users', __name__)


@admin_users_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_users():
    """
    List all users with optional filters (admin only).

    Query params:
        - search: Text search in name or email
        - role: Filter by role (admin, creator, viewer)
        - is_active: Filter by active status (true/false)
        - limit: Number of results (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "users": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    search_text = request.args.get('search', '').strip()
    role = request.args.get('role', '').strip()
    is_active = request.args.get('is_active')
    limit = min(request.args.get('limit', 100, type=int), 500)  # Cap at 500
    offset = request.args.get('offset', 0, type=int)

    # Build query
    query = User.query

    # Text search filter
    if search_text:
        search_pattern = f'%{search_text}%'
        query = query.filter(
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )

    # Role filter
    if role and role in ['admin', 'creator', 'viewer']:
        query = query.filter(User.role == role)

    # Active status filter
    if is_active is not None:
        is_active_bool = is_active.lower() in ['true', '1', 'yes']
        query = query.filter(User.is_active == is_active_bool)

    # Get total count
    total = query.count()

    # Execute query with pagination
    users = query.order_by(User.created_at.desc()).limit(limit).offset(offset).all()

    return jsonify({
        'users': [user.to_dict() for user in users],
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_user(user_id):
    """
    Get a specific user by ID (admin only).

    Returns:
        {
            "user": {...}
        }
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user.to_dict()}), 200


@admin_users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_user(user_id):
    """
    Update a user (admin only).

    Request body:
        {
            "name": "New Name",
            "email": "newemail@example.com",
            "is_active": true
        }

    Note: Use the /role endpoint to change user role.

    Returns:
        {
            "user": {...}
        }
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Update fields
    if 'name' in data:
        user.name = data['name']

    if 'email' in data:
        # Check if new email is already taken by another user
        new_email = data['email']
        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Email already in use'}), 400
        user.email = new_email

    if 'is_active' in data:
        user.is_active = bool(data['is_active'])

    db.session.commit()

    current_app.logger.info(f'Admin updated user: {user.id} ({user.email})')

    return jsonify({'user': user.to_dict()}), 200


@admin_users_bp.route('/<int:user_id>/role', methods=['PUT'])
@jwt_required()
@admin_required()
def update_user_role(user_id):
    """
    Change a user's role (admin only).

    Request body:
        {
            "role": "admin" | "creator" | "viewer"
        }

    Returns:
        {
            "user": {...}
        }
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if not data or 'role' not in data:
        return jsonify({'error': 'Role is required'}), 400

    new_role = data['role']

    # Validate role
    valid_roles = ['admin', 'creator', 'viewer']
    if new_role not in valid_roles:
        return jsonify({'error': f'Role must be one of: {", ".join(valid_roles)}'}), 400

    old_role = user.role
    user.role = new_role

    db.session.commit()

    current_app.logger.info(f'Admin changed user role: {user.id} ({user.email}) from {old_role} to {new_role}')

    return jsonify({'user': user.to_dict()}), 200


@admin_users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def deactivate_user(user_id):
    """
    Deactivate a user (soft delete, admin only).

    Note: This does NOT delete the user from the database, just sets is_active to False.
    The user's tours and other data remain intact but the account cannot be used.

    Returns:
        {
            "message": "User deactivated successfully"
        }
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not user.is_active:
        return jsonify({'error': 'User is already inactive'}), 400

    user.is_active = False

    db.session.commit()

    current_app.logger.info(f'Admin deactivated user: {user.id} ({user.email})')

    return jsonify({
        'message': 'User deactivated successfully'
    }), 200


@admin_users_bp.route('/<int:user_id>/password', methods=['PUT'])
@jwt_required()
@admin_required()
def reset_user_password(user_id):
    """
    Reset a user's password (admin only).

    Request body:
        {
            "new_password": "NewSecurePassword123"
        }

    Returns:
        {
            "message": "Password updated successfully"
        }
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if not data or 'new_password' not in data:
        return jsonify({'error': 'new_password is required'}), 400

    new_password = data['new_password']

    # Basic password validation
    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    user.set_password(new_password)

    db.session.commit()

    current_app.logger.info(f'Admin reset password for user: {user.id} ({user.email})')

    return jsonify({
        'message': 'Password updated successfully'
    }), 200
