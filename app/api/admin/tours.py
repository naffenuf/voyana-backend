"""
Admin tour management endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from datetime import datetime
from app import db
from app.models.tour import Tour
from app.utils.admin_required import admin_required
import math

admin_tours_bp = Blueprint('admin_tours', __name__)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on the earth (specified in decimal degrees).
    Returns distance in meters.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in meters
    r = 6371000

    return c * r


@admin_tours_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_all_tours():
    """
    List ALL tours regardless of status or owner (admin only).

    Query params:
        - search: Text search in name, city, neighborhood
        - status: Filter by status (draft, live, archived)
        - city: Filter by city
        - neighborhood: Filter by neighborhood
        - owner_id: Filter by owner ID
        - is_public: Filter by public status (true/false)
        - lat: Latitude for proximity search (requires lon)
        - lon: Longitude for proximity search (requires lat)
        - max_distance: Maximum distance in meters for proximity search (default: 5000)
        - limit: Number of results (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "tours": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    search_text = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    city = request.args.get('city', '').strip()
    neighborhood = request.args.get('neighborhood', '').strip()
    owner_id = request.args.get('owner_id')
    is_public = request.args.get('is_public')
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    max_distance = request.args.get('max_distance', 5000, type=int)
    limit = min(request.args.get('limit', 100, type=int), 500)  # Cap at 500
    offset = request.args.get('offset', 0, type=int)

    # Build query
    query = Tour.query

    # Text search filter
    if search_text:
        search_pattern = f'%{search_text}%'
        query = query.filter(
            or_(
                Tour.name.ilike(search_pattern),
                Tour.city.ilike(search_pattern),
                Tour.neighborhood.ilike(search_pattern),
                Tour.description.ilike(search_pattern)
            )
        )

    # Status filter
    if status:
        query = query.filter(Tour.status == status)

    # City filter
    if city:
        query = query.filter(Tour.city.ilike(city))

    # Neighborhood filter
    if neighborhood:
        query = query.filter(Tour.neighborhood.ilike(neighborhood))

    # Owner filter
    if owner_id:
        try:
            query = query.filter(Tour.owner_id == int(owner_id))
        except ValueError:
            pass

    # Public status filter
    if is_public is not None:
        is_public_bool = is_public.lower() in ['true', '1', 'yes']
        query = query.filter(Tour.is_public == is_public_bool)

    # Get total count
    total = query.count()

    # Execute query with pagination
    tours = query.order_by(Tour.created_at.desc()).limit(limit).offset(offset).all()

    # If proximity search is requested, filter and sort by distance
    if lat and lon:
        try:
            lat = float(lat)
            lon = float(lon)

            # Calculate distance for each tour that has coordinates
            tours_with_distance = []
            for tour in tours:
                if tour.latitude and tour.longitude:
                    distance = calculate_distance(lat, lon, tour.latitude, tour.longitude)
                    if distance <= max_distance:
                        tour_dict = tour.to_dict(include_sites=False)
                        tour_dict['distance'] = round(distance, 2)
                        tours_with_distance.append(tour_dict)

            # Sort by distance
            tours_with_distance.sort(key=lambda x: x['distance'])
            tours_data = tours_with_distance
        except (ValueError, TypeError):
            current_app.logger.error(f'Invalid lat/lon values: {lat}, {lon}')
            tours_data = [tour.to_dict(include_sites=False) for tour in tours]
    else:
        tours_data = [tour.to_dict(include_sites=False) for tour in tours]

    return jsonify({
        'tours': tours_data,
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_tours_bp.route('/<uuid:tour_id>/publish', methods=['PUT'])
@jwt_required()
@admin_required()
def toggle_publish(tour_id):
    """
    Publish or unpublish a tour (admin only).

    Request body:
        {
            "published": true | false
        }

    Publishing sets is_public=True and published_at to current time.
    Unpublishing sets is_public=False.

    Returns:
        {
            "tour": {...}
        }
    """
    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    data = request.get_json()

    if not data or 'published' not in data:
        return jsonify({'error': 'published field is required (true/false)'}), 400

    should_publish = bool(data['published'])

    if should_publish:
        # Validate: only live tours can be published
        if tour.status != 'live':
            return jsonify({'error': 'Only live tours can be published. Current status: ' + tour.status}), 400

        # Publish the tour
        tour.is_public = True
        if not tour.published_at:
            tour.published_at = datetime.utcnow()
    else:
        # Unpublish the tour
        tour.is_public = False

    db.session.commit()

    action = 'published' if should_publish else 'unpublished'
    current_app.logger.info(f'Admin {action} tour: {tour.id} ({tour.name})')

    return jsonify({'tour': tour.to_dict(include_sites=False)}), 200
