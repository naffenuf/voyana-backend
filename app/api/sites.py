"""
Sites API endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_, func
from app import db
from app.models.site import Site
from app.utils.admin_required import admin_required
from app.utils.device_binding import device_binding_required
import math


sites_bp = Blueprint('sites', __name__)


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


@sites_bp.route('', methods=['GET'])
def list_sites():
    """
    List all sites with optional filters.

    Query params:
        - search: Text search in title, city, neighborhood
        - city: Filter by city
        - neighborhood: Filter by neighborhood
        - lat: Latitude for proximity search (requires lon)
        - lon: Longitude for proximity search (requires lat)
        - max_distance: Maximum distance in meters for proximity search (default: 5000)
        - limit: Number of results to return (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "sites": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    search_text = request.args.get('search', '').strip()
    city = request.args.get('city', '').strip()
    neighborhood = request.args.get('neighborhood', '').strip()
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    max_distance = request.args.get('max_distance', 5000, type=int)
    limit = min(request.args.get('limit', 100, type=int), 500)  # Cap at 500
    offset = request.args.get('offset', 0, type=int)

    # Build query
    query = Site.query

    # Text search filter
    if search_text:
        search_pattern = f'%{search_text}%'
        query = query.filter(
            or_(
                Site.title.ilike(search_pattern),
                Site.city.ilike(search_pattern),
                Site.neighborhood.ilike(search_pattern),
                Site.description.ilike(search_pattern)
            )
        )

    # City filter
    if city:
        query = query.filter(Site.city.ilike(city))

    # Neighborhood filter
    if neighborhood:
        query = query.filter(Site.neighborhood.ilike(neighborhood))

    # Get total count
    total = query.count()

    # Execute query with pagination
    sites = query.limit(limit).offset(offset).all()

    # If proximity search is requested, filter and sort by distance
    if lat and lon:
        try:
            lat = float(lat)
            lon = float(lon)

            # Calculate distance for each site
            sites_with_distance = []
            for site in sites:
                distance = calculate_distance(lat, lon, site.latitude, site.longitude)
                if distance <= max_distance:
                    site_dict = site.to_dict()
                    site_dict['distance'] = round(distance, 2)
                    sites_with_distance.append(site_dict)

            # Sort by distance
            sites_with_distance.sort(key=lambda x: x['distance'])
            sites_data = sites_with_distance
        except (ValueError, TypeError):
            current_app.logger.error(f'Invalid lat/lon values: {lat}, {lon}')
            sites_data = [site.to_dict() for site in sites]
    else:
        sites_data = [site.to_dict() for site in sites]

    return jsonify({
        'sites': sites_data,
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@sites_bp.route('/<uuid:site_id>', methods=['GET'])
def get_site(site_id):
    """
    Get a specific site by ID.

    Returns:
        {
            "site": {...}
        }
    """
    site = Site.query.get(site_id)

    if not site:
        return jsonify({'error': 'Site not found'}), 404

    return jsonify({'site': site.to_dict()}), 200


@sites_bp.route('', methods=['POST'])
@device_binding_required()
def create_site():
    """
    Create a new site.

    Request body:
        {
            "title": "Statue of Liberty",
            "description": "...",
            "latitude": 40.6892,
            "longitude": -74.0445,
            "city": "New York",
            "neighborhood": "Liberty Island",
            "imageUrl": "https://...",
            "audioUrl": "https://...",
            "webUrl": "https://...",
            "keywords": ["landmark", "monument"],
            "rating": 4.5,
            "placeId": "ChIJ...",
            "formatted_address": "...",
            "types": ["tourist_attraction"],
            "user_ratings_total": 12345,
            "phone_number": "+1...",
            "googlePhotoReferences": ["https://..."]
        }

    Returns:
        {
            "site": {...}
        }
    """
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400

    if 'latitude' not in data or 'longitude' not in data:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    # Validate coordinate ranges
    try:
        lat = float(data['latitude'])
        lon = float(data['longitude'])

        if not (-90 <= lat <= 90):
            return jsonify({'error': 'Latitude must be between -90 and 90'}), 400
        if not (-180 <= lon <= 180):
            return jsonify({'error': 'Longitude must be between -180 and 180'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid latitude or longitude'}), 400

    # Create site
    site = Site(
        title=data['title'],
        description=data.get('description'),
        latitude=lat,
        longitude=lon,
        city=data.get('city'),
        neighborhood=data.get('neighborhood'),
        image_url=data.get('imageUrl'),
        audio_url=data.get('audioUrl'),
        web_url=data.get('webUrl'),
        keywords=data.get('keywords'),
        rating=data.get('rating'),
        place_id=data.get('placeId'),
        formatted_address=data.get('formatted_address'),
        types=data.get('types'),
        user_ratings_total=data.get('user_ratings_total'),
        phone_number=data.get('phone_number'),
        google_photo_references=data.get('googlePhotoReferences')
    )

    db.session.add(site)
    db.session.commit()

    current_app.logger.info(f'Created site: {site.id} ({site.title})')

    return jsonify({'site': site.to_dict()}), 201


@sites_bp.route('/<uuid:site_id>', methods=['PUT'])
@device_binding_required()
@admin_required()
def update_site(site_id):
    """
    Update a site (admin only).

    Request body: Same as create_site (all fields optional except ID)

    Returns:
        {
            "site": {...}
        }
    """
    site = Site.query.get(site_id)

    if not site:
        return jsonify({'error': 'Site not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Update fields
    if 'title' in data:
        site.title = data['title']
    if 'description' in data:
        site.description = data['description']

    # Update coordinates with validation
    if 'latitude' in data or 'longitude' in data:
        try:
            lat = float(data.get('latitude', site.latitude))
            lon = float(data.get('longitude', site.longitude))

            if not (-90 <= lat <= 90):
                return jsonify({'error': 'Latitude must be between -90 and 90'}), 400
            if not (-180 <= lon <= 180):
                return jsonify({'error': 'Longitude must be between -180 and 180'}), 400

            site.latitude = lat
            site.longitude = lon
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid latitude or longitude'}), 400

    if 'city' in data:
        site.city = data['city']
    if 'neighborhood' in data:
        site.neighborhood = data['neighborhood']
    if 'imageUrl' in data:
        site.image_url = data['imageUrl']
    if 'audioUrl' in data:
        site.audio_url = data['audioUrl']
    if 'webUrl' in data:
        site.web_url = data['webUrl']
    if 'keywords' in data:
        site.keywords = data['keywords']
    if 'rating' in data:
        site.rating = data['rating']
    if 'placeId' in data:
        site.place_id = data['placeId']
    if 'formatted_address' in data:
        site.formatted_address = data['formatted_address']
    if 'types' in data:
        site.types = data['types']
    if 'user_ratings_total' in data:
        site.user_ratings_total = data['user_ratings_total']
    if 'phone_number' in data:
        site.phone_number = data['phone_number']
    if 'googlePhotoReferences' in data:
        site.google_photo_references = data['googlePhotoReferences']

    db.session.commit()

    current_app.logger.info(f'Updated site: {site.id} ({site.title})')

    return jsonify({'site': site.to_dict()}), 200


@sites_bp.route('/<uuid:site_id>', methods=['DELETE'])
@device_binding_required()
@admin_required()
def delete_site(site_id):
    """
    Delete a site (admin only).

    Note: This will also remove the site from any tours that reference it
    and delete associated S3 resources (image, audio, and Google photos).

    Returns:
        {
            "message": "Site deleted successfully"
        }
    """
    site = Site.query.get(site_id)

    if not site:
        return jsonify({'error': 'Site not found'}), 404

    # Check if site is used in any tours and collect them for metric recalculation
    affected_tours = [tour_site.tour for tour_site in site.tour_sites]
    tour_count = len(affected_tours)

    # Collect S3 URLs to delete
    s3_urls_to_delete = []

    if site.image_url:
        s3_urls_to_delete.append(site.image_url)

    if site.audio_url:
        s3_urls_to_delete.append(site.audio_url)

    if site.google_photo_references:
        s3_urls_to_delete.extend(site.google_photo_references)

    site_title = site.title

    # Delete the site from database (CASCADE will delete tour_sites relationships)
    db.session.delete(site)
    db.session.commit()

    # Recalculate metrics for all affected tours
    from app.services.tour_calculator import calculate_tour_metrics
    for tour in affected_tours:
        # Refresh the tour to get updated tour_sites after CASCADE delete
        db.session.expire(tour, ['tour_sites'])
        db.session.refresh(tour)

        # Recalculate distance/duration
        distance_meters, duration_minutes = calculate_tour_metrics(tour)
        tour.distance_meters = distance_meters
        tour.duration_minutes = duration_minutes

        current_app.logger.info(
            f'Recalculated metrics for tour {tour.id} after site deletion: '
            f'{distance_meters:.1f}m, {duration_minutes}min'
        )

    # Commit tour metric updates
    if affected_tours:
        db.session.commit()

    # Delete S3 files
    from app.services.s3_service import delete_file_from_s3
    deleted_count = 0
    for url in s3_urls_to_delete:
        if delete_file_from_s3(url):
            deleted_count += 1

    current_app.logger.info(
        f'Deleted site: {site_id} ({site_title}), removed from {tour_count} tours, '
        f'deleted {deleted_count}/{len(s3_urls_to_delete)} S3 files'
    )

    return jsonify({
        'message': 'Site deleted successfully',
        'removedFromTours': tour_count,
        'deletedS3Files': deleted_count
    }), 200
