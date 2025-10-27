"""
Tours API endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt
from sqlalchemy import or_
from app import db
from app.models.tour import Tour
import math

tours_bp = Blueprint('tours', __name__)


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


@tours_bp.route('', methods=['GET'])
def list_tours():
    """
    List tours (public tours + authenticated user's own tours).

    Query params:
        - search: Text search in name, city, neighborhood
        - status: Filter by status (draft, live, archived)
        - city: Filter by city
        - neighborhood: Filter by neighborhood
        - include_sites: Include full sites data in response (true/false, default: false)
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
    # Check if user is authenticated (optional)
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        jwt_identity = get_jwt_identity()
        if jwt_identity:
            user_id = int(jwt_identity)
    except:
        pass

    # Get query params
    search_text = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    city = request.args.get('city', '').strip()
    neighborhood = request.args.get('neighborhood', '').strip()
    include_sites_param = request.args.get('include_sites', 'false').lower()
    include_sites = include_sites_param in ['true', '1', 'yes']
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    max_distance = request.args.get('max_distance', 5000, type=int)
    limit = min(request.args.get('limit', 100, type=int), 500)
    offset = request.args.get('offset', 0, type=int)

    # Build query
    query = Tour.query

    # Access control: published tours OR user's own tours
    if user_id:
        query = query.filter(
            or_(
                Tour.status == 'published',
                Tour.owner_id == user_id
            )
        )
    else:
        query = query.filter(Tour.status == 'published')

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
    else:
        # Default: only show live tours
        query = query.filter(Tour.status == 'live')

    # City filter
    if city:
        query = query.filter(Tour.city.ilike(city))

    # Neighborhood filter
    if neighborhood:
        query = query.filter(Tour.neighborhood.ilike(neighborhood))

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
                        tour_dict = tour.to_dict(include_sites=include_sites)
                        tour_dict['distance'] = round(distance, 2)
                        tours_with_distance.append(tour_dict)

            # Sort by distance
            tours_with_distance.sort(key=lambda x: x['distance'])
            tours_data = tours_with_distance
        except (ValueError, TypeError):
            current_app.logger.error(f'Invalid lat/lon values: {lat}, {lon}')
            tours_data = [tour.to_dict(include_sites=include_sites) for tour in tours]
    else:
        tours_data = [tour.to_dict(include_sites=include_sites) for tour in tours]

    return jsonify({
        'tours': tours_data,
        'total': total,
        'limit': limit,
        'offset': offset
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
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        jwt_identity = get_jwt_identity()
        if jwt_identity:
            user_id = int(jwt_identity)
    except:
        pass

    # Allow access if tour is published OR user is the owner OR user is admin
    if tour.status != 'published' and (not user_id or tour.owner_id != user_id):
        # Check if user is admin
        try:
            claims = get_jwt()
            if claims.get('role') != 'admin':
                return jsonify({'error': 'Unauthorized'}), 403
        except:
            return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({'tour': tour.to_dict()}), 200


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
    user_id = int(get_jwt_identity())
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
    Update an existing tour (owner or admin only).

    Returns:
        {
            "tour": {...}
        }
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check ownership (admin or owner)
    if not is_admin and tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Creators cannot edit tours that are in 'ready' status (submitted for review)
    if not is_admin and tour.status == 'ready':
        return jsonify({'error': 'Cannot edit tours that are submitted for review. An admin must revert to draft first.'}), 403

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Update fields
    if 'name' in data:
        tour.name = data['name']
    if 'description' in data:
        tour.description = data['description']
    if 'city' in data:
        tour.city = data['city']
    if 'neighborhood' in data:
        tour.neighborhood = data['neighborhood']
    if 'latitude' in data:
        tour.latitude = data['latitude']
    if 'longitude' in data:
        tour.longitude = data['longitude']
    if 'imageUrl' in data:
        tour.image_url = data['imageUrl']
    if 'audioUrl' in data:
        tour.audio_url = data['audioUrl']
    if 'mapImageUrl' in data:
        tour.map_image_url = data['mapImageUrl']
    if 'musicUrls' in data:
        tour.music_urls = data['musicUrls']
    if 'durationMinutes' in data:
        tour.duration_minutes = data['durationMinutes']
    if 'distanceMeters' in data:
        tour.distance_meters = data['distanceMeters']

    # Status changes
    if 'status' in data:
        new_status = data['status']
        valid_statuses = ['draft', 'ready', 'published', 'archived']

        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400

        # Creators can only change draft → ready
        if not is_admin:
            if tour.status == 'draft' and new_status == 'ready':
                tour.status = new_status
            elif tour.status == new_status:
                # No change, allow
                pass
            else:
                return jsonify({'error': f'Creators can only submit drafts for review (draft → ready)'}), 403
        else:
            # Admins can change to any status
            tour.status = new_status
            # Set published_at when status becomes published
            if new_status == 'published' and not tour.published_at:
                from datetime import datetime
                tour.published_at = datetime.utcnow()

    # Update tour sites (many-to-many relationship)
    if 'siteIds' in data:
        from app.models.site import Site
        from app.models.tour import TourSite

        site_ids = data['siteIds']

        # Validate that all site IDs exist
        for site_id in site_ids:
            site = Site.query.get(site_id)
            if not site:
                return jsonify({'error': f'Site {site_id} not found'}), 404

        # Clear existing tour-site relationships
        TourSite.query.filter_by(tour_id=tour.id).delete()

        # Create new relationships with display order
        for order, site_id in enumerate(site_ids, start=1):
            tour_site = TourSite(
                tour_id=tour.id,
                site_id=site_id,
                display_order=order
            )
            db.session.add(tour_site)

        current_app.logger.info(f'Updated sites for tour {tour.id}: {len(site_ids)} sites')

    db.session.commit()

    current_app.logger.info(f'Updated tour: {tour.id} ({tour.name})')

    return jsonify({'tour': tour.to_dict()}), 200


@tours_bp.route('/<uuid:tour_id>', methods=['DELETE'])
@jwt_required()
def delete_tour(tour_id):
    """
    Delete a tour (owner or admin only).

    Returns:
        {
            "message": "Tour deleted successfully"
        }
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check ownership (admin or owner)
    if not is_admin and tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    tour_name = tour.name
    db.session.delete(tour)
    db.session.commit()

    current_app.logger.info(f'Deleted tour: {tour_id} ({tour_name})')

    return jsonify({'message': 'Tour deleted successfully'}), 200


@tours_bp.route('/nearby', methods=['GET'])
def nearby_tours():
    """
    Find tours by proximity, grouped by neighborhoods.

    Returns tours from the closest N neighborhoods (based on distance to each tour).
    Algorithm:
    1. Calculate distance from user location to all tours
    2. Sort tours by distance (ascending)
    3. Identify neighborhoods in order of first appearance
    4. Return all tours from the first N neighborhoods

    Query params:
        - lat: User latitude (required)
        - lon: User longitude (required)
        - neighborhood_count: Number of neighborhoods to return (default: 3)
        - neighborhood_offset: Pagination offset for neighborhoods (default: 0)
        - city: Filter tours by city (optional)
        - max_distance: Maximum distance in meters (optional, no limit by default)

    Returns:
        {
            "tours": [...],  # All tours from selected neighborhoods, sorted by distance
            "neighborhoods": [...],  # Ordered list of neighborhoods returned
            "totalNeighborhoods": int,  # Total unique neighborhoods in results
            "neighborhoodOffset": int,  # Current pagination offset
            "hasMore": bool  # Whether more neighborhoods are available
        }
    """
    # Get query params
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    neighborhood_count = request.args.get('neighborhood_count', 3, type=int)
    neighborhood_offset = request.args.get('neighborhood_offset', 0, type=int)
    city = request.args.get('city', '').strip()
    max_distance = request.args.get('max_distance', type=int)

    # Validate required params
    if not lat or not lon:
        return jsonify({'error': 'lat and lon parameters are required'}), 400

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid lat/lon values'}), 400

    # Validate lat/lon ranges
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return jsonify({'error': 'Latitude must be -90 to 90, longitude must be -180 to 180'}), 400

    # Check if user is authenticated (optional)
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        jwt_identity = get_jwt_identity()
        if jwt_identity:
            user_id = int(jwt_identity)
    except:
        pass

    # Build base query
    query = Tour.query

    # Access control: published tours OR user's own tours
    if user_id:
        query = query.filter(
            or_(
                Tour.status == 'published',
                Tour.owner_id == user_id
            )
        )
    else:
        query = query.filter(Tour.status == 'published')

    # Default: only show live tours
    query = query.filter(Tour.status == 'live')

    # Optional city filter
    if city:
        query = query.filter(Tour.city.ilike(city))

    # Get all tours (no pagination - we need to calculate distance to all)
    all_tours = query.all()

    # Calculate distance for each tour and filter by max_distance if specified
    tours_with_distance = []
    for tour in all_tours:
        # Skip tours without coordinates
        if not tour.latitude or not tour.longitude:
            continue

        distance = calculate_distance(lat, lon, tour.latitude, tour.longitude)

        # Apply max_distance filter if specified
        if max_distance is not None and distance > max_distance:
            continue

        tours_with_distance.append({
            'tour': tour,
            'distance': round(distance, 2),
            'neighborhood': tour.neighborhood or 'Unspecified'
        })

    # Sort by distance (ascending)
    tours_with_distance.sort(key=lambda x: x['distance'])

    # Identify unique neighborhoods in order of first appearance
    neighborhoods_ordered = []
    seen_neighborhoods = set()

    for item in tours_with_distance:
        neighborhood = item['neighborhood']
        if neighborhood not in seen_neighborhoods:
            neighborhoods_ordered.append(neighborhood)
            seen_neighborhoods.add(neighborhood)

    # Apply pagination to neighborhoods
    total_neighborhoods = len(neighborhoods_ordered)
    start_idx = neighborhood_offset
    end_idx = start_idx + neighborhood_count
    selected_neighborhoods = neighborhoods_ordered[start_idx:end_idx]

    # Filter tours to only include those from selected neighborhoods
    filtered_tours = [
        item for item in tours_with_distance
        if item['neighborhood'] in selected_neighborhoods
    ]

    # Convert to response format
    tours_data = []
    for item in filtered_tours:
        tour_dict = item['tour'].to_dict(include_sites=True)
        tour_dict['distance'] = item['distance']
        tour_dict['neighborhood'] = item['neighborhood']
        tours_data.append(tour_dict)

    return jsonify({
        'tours': tours_data,
        'neighborhoods': selected_neighborhoods,
        'totalNeighborhoods': total_neighborhoods,
        'neighborhoodOffset': neighborhood_offset,
        'hasMore': end_idx < total_neighborhoods
    }), 200
