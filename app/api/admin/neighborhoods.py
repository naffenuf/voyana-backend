"""
Admin neighborhood description management endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import select, distinct
from app import db
from app.models.neighborhood import NeighborhoodDescription
from app.models.tour import Tour
from app.utils.admin_required import admin_required

admin_neighborhoods_bp = Blueprint('admin_neighborhoods', __name__)


@admin_neighborhoods_bp.route('/all-from-tours', methods=['GET'])
@jwt_required()
@admin_required()
def get_all_neighborhoods_from_tours():
    """
    Get all unique city/neighborhood combinations from tours,
    with their description status (admin only).

    Returns:
        [
            {
                "city": "New York",
                "neighborhood": "Chinatown",
                "hasDescription": true,
                "description": "Historic neighborhood..." (if exists),
                "descriptionId": 123 (if exists),
                "tourCount": 5
            },
            ...
        ]
    """
    try:
        # Get all distinct city/neighborhood from tours with counts
        tour_neighborhoods = db.session.query(
            Tour.city,
            Tour.neighborhood,
            db.func.count(Tour.id).label('tour_count')
        ).filter(
            Tour.city.isnot(None),
            Tour.neighborhood.isnot(None)
        ).group_by(
            Tour.city,
            Tour.neighborhood
        ).all()

        # Get all neighborhood descriptions
        descriptions_dict = {}
        descriptions = NeighborhoodDescription.query.all()
        for desc in descriptions:
            key = (desc.city, desc.neighborhood)
            descriptions_dict[key] = desc

        # Combine the data
        result = []
        for city, neighborhood, tour_count in tour_neighborhoods:
            key = (city, neighborhood)
            desc = descriptions_dict.get(key)

            item = {
                'city': city,
                'neighborhood': neighborhood,
                'tourCount': tour_count,
                'hasDescription': desc is not None
            }

            if desc:
                item['description'] = desc.description
                item['descriptionId'] = desc.id
                item['createdAt'] = desc.created_at.isoformat()
                item['updatedAt'] = desc.updated_at.isoformat()
            else:
                item['description'] = None
                item['descriptionId'] = None

            result.append(item)

        # Sort by city, then neighborhood
        result.sort(key=lambda x: (x['city'], x['neighborhood']))

        return jsonify({'neighborhoods': result, 'total': len(result)}), 200

    except Exception as e:
        current_app.logger.error(f'Error getting neighborhoods from tours: {e}')
        return jsonify({'error': 'Failed to get neighborhoods'}), 500


@admin_neighborhoods_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_neighborhoods():
    """
    List all neighborhood descriptions (admin only).

    Query params:
        - city: Filter by city
        - neighborhood: Filter by neighborhood (partial match)
        - limit: Number of results (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "neighborhoods": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    city = request.args.get('city', '').strip()
    neighborhood = request.args.get('neighborhood', '').strip()
    limit = min(request.args.get('limit', 100, type=int), 500)
    offset = request.args.get('offset', 0, type=int)

    # Build query
    query = NeighborhoodDescription.query

    # Apply filters
    if city:
        query = query.filter(NeighborhoodDescription.city.ilike(f'%{city}%'))
    if neighborhood:
        query = query.filter(NeighborhoodDescription.neighborhood.ilike(f'%{neighborhood}%'))

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    neighborhoods = query.order_by(
        NeighborhoodDescription.city,
        NeighborhoodDescription.neighborhood
    ).limit(limit).offset(offset).all()

    return jsonify({
        'neighborhoods': [n.to_dict() for n in neighborhoods],
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_neighborhoods_bp.route('/<int:neighborhood_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_neighborhood(neighborhood_id):
    """Get a specific neighborhood description by ID (admin only)."""
    neighborhood = NeighborhoodDescription.query.get(neighborhood_id)

    if not neighborhood:
        return jsonify({'error': 'Neighborhood description not found'}), 404

    return jsonify(neighborhood.to_dict()), 200


@admin_neighborhoods_bp.route('', methods=['POST'])
@jwt_required()
@admin_required()
def create_neighborhood():
    """
    Create a new neighborhood description (admin only).

    Request body:
        {
            "city": "New York",
            "neighborhood": "Chinatown",
            "description": "Historic neighborhood known for..."
        }
    """
    data = request.get_json()

    # Validate required fields
    if not data or not all(k in data for k in ['city', 'neighborhood', 'description']):
        return jsonify({'error': 'Missing required fields: city, neighborhood, description'}), 400

    city = data['city'].strip()
    neighborhood = data['neighborhood'].strip()
    description = data['description'].strip()

    if not city or not neighborhood or not description:
        return jsonify({'error': 'City, neighborhood, and description cannot be empty'}), 400

    # Check for duplicates
    existing = NeighborhoodDescription.query.filter_by(
        city=city,
        neighborhood=neighborhood
    ).first()

    if existing:
        return jsonify({'error': f'Neighborhood description for {city}/{neighborhood} already exists'}), 409

    try:
        # Create new neighborhood description
        new_neighborhood = NeighborhoodDescription(
            city=city,
            neighborhood=neighborhood,
            description=description
        )

        db.session.add(new_neighborhood)
        db.session.commit()

        current_app.logger.info(f'Created neighborhood description: {city}/{neighborhood}')
        return jsonify(new_neighborhood.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating neighborhood description: {e}')
        return jsonify({'error': 'Failed to create neighborhood description'}), 500


@admin_neighborhoods_bp.route('/<int:neighborhood_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_neighborhood(neighborhood_id):
    """
    Update a neighborhood description (admin only).

    Request body:
        {
            "city": "New York",
            "neighborhood": "Chinatown",
            "description": "Updated description..."
        }
    """
    neighborhood = NeighborhoodDescription.query.get(neighborhood_id)

    if not neighborhood:
        return jsonify({'error': 'Neighborhood description not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    try:
        # Update fields if provided
        if 'city' in data:
            city = data['city'].strip()
            if not city:
                return jsonify({'error': 'City cannot be empty'}), 400
            neighborhood.city = city

        if 'neighborhood' in data:
            neighborhood_name = data['neighborhood'].strip()
            if not neighborhood_name:
                return jsonify({'error': 'Neighborhood cannot be empty'}), 400
            neighborhood.neighborhood = neighborhood_name

        if 'description' in data:
            description = data['description'].strip()
            if not description:
                return jsonify({'error': 'Description cannot be empty'}), 400
            neighborhood.description = description

        # Check for duplicate city/neighborhood if either was changed
        if 'city' in data or 'neighborhood' in data:
            duplicate = NeighborhoodDescription.query.filter(
                NeighborhoodDescription.id != neighborhood_id,
                NeighborhoodDescription.city == neighborhood.city,
                NeighborhoodDescription.neighborhood == neighborhood.neighborhood
            ).first()

            if duplicate:
                return jsonify({'error': f'Neighborhood description for {neighborhood.city}/{neighborhood.neighborhood} already exists'}), 409

        db.session.commit()

        current_app.logger.info(f'Updated neighborhood description {neighborhood_id}: {neighborhood.city}/{neighborhood.neighborhood}')
        return jsonify(neighborhood.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating neighborhood description {neighborhood_id}: {e}')
        return jsonify({'error': 'Failed to update neighborhood description'}), 500


@admin_neighborhoods_bp.route('/<int:neighborhood_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_neighborhood(neighborhood_id):
    """Delete a neighborhood description (admin only)."""
    neighborhood = NeighborhoodDescription.query.get(neighborhood_id)

    if not neighborhood:
        return jsonify({'error': 'Neighborhood description not found'}), 404

    try:
        city = neighborhood.city
        neighborhood_name = neighborhood.neighborhood

        db.session.delete(neighborhood)
        db.session.commit()

        current_app.logger.info(f'Deleted neighborhood description {neighborhood_id}: {city}/{neighborhood_name}')
        return jsonify({'message': 'Neighborhood description deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting neighborhood description {neighborhood_id}: {e}')
        return jsonify({'error': 'Failed to delete neighborhood description'}), 500
