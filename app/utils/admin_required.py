"""
Admin authorization decorators for Flask routes.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def admin_required():
    """
    Decorator that requires the user to have admin role.

    Usage:
        @app.route('/admin/users')
        @admin_required()
        def list_users():
            ...

    Returns 403 if the user is not an admin.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()

            # Check if user has admin role
            if claims.get('role') != 'admin':
                return jsonify({'error': 'Admin access required'}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_or_owner_required(get_resource_owner_id):
    """
    Decorator that requires the user to be either an admin or the owner of the resource.

    Args:
        get_resource_owner_id: A function that takes the same arguments as the route
                               and returns the owner_id of the resource being accessed.

    Usage:
        def get_tour_owner(tour_id):
            tour = Tour.query.get(tour_id)
            return tour.owner_id if tour else None

        @app.route('/tours/<uuid:tour_id>', methods=['PUT'])
        @admin_or_owner_required(lambda tour_id: get_tour_owner(tour_id))
        def update_tour(tour_id):
            ...

    Returns 403 if the user is neither admin nor the resource owner.
    Returns 404 if the resource doesn't exist.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask_jwt_extended import get_jwt_identity

            verify_jwt_in_request()
            claims = get_jwt()
            user_id = int(get_jwt_identity())

            # Admin can access anything
            if claims.get('role') == 'admin':
                return fn(*args, **kwargs)

            # Check if user owns the resource
            owner_id = get_resource_owner_id(*args, **kwargs)

            if owner_id is None:
                return jsonify({'error': 'Resource not found'}), 404

            if owner_id != user_id:
                return jsonify({'error': 'Unauthorized'}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator
