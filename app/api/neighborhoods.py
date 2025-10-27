"""
Public neighborhood description endpoints.
"""
from flask import Blueprint, request, jsonify
from app.models.neighborhood import NeighborhoodDescription

neighborhoods_bp = Blueprint('neighborhoods', __name__)


@neighborhoods_bp.route('', methods=['GET'])
def get_neighborhood_description():
    """
    Get a neighborhood description by city and neighborhood name.

    Query params:
        - city: City name (required)
        - neighborhood: Neighborhood name (required)

    Returns:
        {
            "city": "New York",
            "neighborhood": "Chinatown",
            "description": "Historic neighborhood..."
        }
    """
    city = request.args.get('city', '').strip()
    neighborhood = request.args.get('neighborhood', '').strip()

    if not city or not neighborhood:
        return jsonify({'error': 'Both city and neighborhood parameters are required'}), 400

    # Query for the neighborhood description
    description = NeighborhoodDescription.query.filter_by(
        city=city,
        neighborhood=neighborhood
    ).first()

    if not description:
        return jsonify({'error': 'Neighborhood description not found'}), 404

    return jsonify(description.to_dict()), 200


@neighborhoods_bp.route('/list', methods=['GET'])
def list_all_neighborhood_descriptions():
    """
    List all neighborhood descriptions (public endpoint).

    Query params:
        - city: Filter by city (optional)

    Returns:
        {
            "neighborhoods": [...]
        }
    """
    city = request.args.get('city', '').strip()

    query = NeighborhoodDescription.query

    if city:
        query = query.filter(NeighborhoodDescription.city == city)

    neighborhoods = query.order_by(
        NeighborhoodDescription.city,
        NeighborhoodDescription.neighborhood
    ).all()

    return jsonify({
        'neighborhoods': [n.to_dict() for n in neighborhoods]
    }), 200
