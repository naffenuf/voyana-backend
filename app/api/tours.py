"""
Tours API endpoints.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.tour import Tour

tours_bp = Blueprint('tours', __name__)


@tours_bp.route('', methods=['GET'])
def list_tours():
    """
    List all tours (public + user's own).

    Query params:
        status: Filter by status ('draft', 'live', 'archived')
        city: Filter by city
        neighborhood: Filter by neighborhood

    Returns:
        {
            "tours": [...]
        }
    """
    query = Tour.query

    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    else:
        # Default: show only live tours for public
        query = query.filter_by(status='live', is_public=True)

    # Filter by location
    city = request.args.get('city')
    if city:
        query = query.filter_by(city=city)

    neighborhood = request.args.get('neighborhood')
    if neighborhood:
        query = query.filter_by(neighborhood=neighborhood)

    tours = query.all()

    return jsonify({
        'tours': [tour.to_dict() for tour in tours]
    }), 200


@tours_bp.route('/<uuid:tour_id>', methods=['GET'])
def get_tour(tour_id):
    """
    Get a specific tour by ID.

    Returns:
        {
            "tour": {...}
        }
    """
    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check if user has access (public or owner)
    # TODO: Check JWT if present

    return jsonify(tour.to_dict()), 200


@tours_bp.route('', methods=['POST'])
@jwt_required()
def create_tour():
    """
    Create a new tour.

    Request body:
        {
            "name": "Tour Name",
            "description": "Tour description",
            "city": "New York",
            "neighborhood": "SoHo",
            ...
        }

    Returns:
        {
            "tour": {...}
        }
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': 'Tour name is required'}), 400

    tour = Tour(
        owner_id=user_id,
        name=data['name'],
        description=data.get('description'),
        city=data.get('city'),
        neighborhood=data.get('neighborhood'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        status='draft'  # Default to draft
    )

    db.session.add(tour)
    db.session.commit()

    return jsonify(tour.to_dict()), 201


@tours_bp.route('/<uuid:tour_id>', methods=['PUT'])
@jwt_required()
def update_tour(tour_id):
    """
    Update an existing tour.

    Returns:
        {
            "tour": {...}
        }
    """
    user_id = get_jwt_identity()
    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check ownership
    if tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    # Update fields
    if 'name' in data:
        tour.name = data['name']
    if 'description' in data:
        tour.description = data['description']
    if 'city' in data:
        tour.city = data['city']
    if 'neighborhood' in data:
        tour.neighborhood = data['neighborhood']
    if 'status' in data:
        tour.status = data['status']

    db.session.commit()

    return jsonify(tour.to_dict()), 200


@tours_bp.route('/<uuid:tour_id>', methods=['DELETE'])
@jwt_required()
def delete_tour(tour_id):
    """
    Delete a tour.

    Returns:
        {
            "message": "Tour deleted successfully"
        }
    """
    user_id = get_jwt_identity()
    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check ownership
    if tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(tour)
    db.session.commit()

    return jsonify({'message': 'Tour deleted successfully'}), 200
