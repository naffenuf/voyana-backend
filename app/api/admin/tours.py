"""
Admin tour management endpoints.
"""
from flask import Blueprint, request, jsonify, current_app, g
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from datetime import datetime
import uuid
import math
from app import db, limiter
from app.models.tour import Tour, TourSite
from app.models.site import Site
from app.utils.admin_required import admin_required
from app.utils.flexible_auth import flexible_auth_required

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
    # Get query params
    search_text = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    city = request.args.get('city', '').strip()
    neighborhood = request.args.get('neighborhood', '').strip()
    owner_id = request.args.get('owner_id')
    include_sites_param = request.args.get('include_sites', 'false').lower()
    include_sites = include_sites_param in ['true', '1', 'yes']
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


@admin_tours_bp.route('/upload', methods=['POST'])
@flexible_auth_required(admin_only=True)
@limiter.limit("100 per hour", key_func=lambda: f"upload_{g.current_user.id}_{g.auth_method}")
def bulk_upload_tours():
    """
    Bulk upload tours with sites (admin only).

    Accepts either JWT (Bearer token) or API key (X-API-Key header).
    Rate limited to 100 uploads per hour for API keys, 50 per hour for JWT.

    Request body:
        {
            "tours": [
                {
                    "name": "Tour Name",
                    "description": "Tour description",
                    "city": "City Name",
                    "neighborhood": "Neighborhood",
                    "imageUrl": "https://...",
                    "audioUrl": "https://...",
                    "mapImageUrl": "https://...",
                    "published": false,
                    "durationMinutes": 90,
                    "distanceMeters": 1500,
                    "difficulty": "moderate",
                    "sites": [
                        {
                            "title": "Site Title",
                            "description": "Site description",
                            "latitude": 47.6062,
                            "longitude": -122.3321,
                            "imageUrl": "https://...",
                            "audioUrl": "https://...",
                            "webUrl": "https://...",
                            "keywords": ["museum", "art"],
                            "rating": 4.5,
                            "placeId": "ChIJ...",
                            "formatted_address": "123 Main St...",
                            "types": ["museum", "point_of_interest"],
                            "user_ratings_total": 1234,
                            "phone_number": "+1 206-123-4567",
                            "opening_hours": "{...}",
                            "accessibility_info": "{...}",
                            "editorialDescription": "...",
                            "city": "City Name",
                            "neighborhood": "Neighborhood"
                        }
                    ]
                }
            ]
        }

    Returns:
        {
            "success": [
                {"tourName": "Tour 1", "tourId": "uuid", "sitesCreated": 5}
            ],
            "errors": [
                {"tourName": "Tour 2", "error": "Missing required field: name"}
            ],
            "summary": {
                "total": 10,
                "succeeded": 8,
                "failed": 2
            }
        }
    """
    try:
        data = request.get_json()

        if not data or 'tours' not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must contain a "tours" array'
            }), 400

        tours_data = data['tours']

        if not isinstance(tours_data, list):
            return jsonify({
                'error': 'Invalid request',
                'message': '"tours" must be an array'
            }), 400

        if len(tours_data) == 0:
            return jsonify({
                'error': 'Invalid request',
                'message': 'At least one tour is required'
            }), 400

        if len(tours_data) > 100:
            return jsonify({
                'error': 'Too many tours',
                'message': 'Maximum 100 tours per upload'
            }), 400

        success = []
        errors = []

        for tour_data in tours_data:
            try:
                # Validate required fields
                if not tour_data.get('name'):
                    errors.append({
                        'tourName': tour_data.get('name', 'Unknown'),
                        'error': 'Missing required field: name'
                    })
                    continue

                if not tour_data.get('sites') or not isinstance(tour_data['sites'], list):
                    errors.append({
                        'tourName': tour_data['name'],
                        'error': 'Missing or invalid sites array'
                    })
                    continue

                # Determine status from "published" field
                published = tour_data.get('published', False)
                status = 'published' if published else 'draft'

                # Create tour
                tour = Tour(
                    id=uuid.uuid4(),
                    owner_id=g.current_user.id,
                    name=tour_data['name'],
                    description=tour_data.get('description'),
                    city=tour_data.get('city'),
                    neighborhood=tour_data.get('neighborhood'),
                    image_url=tour_data.get('imageUrl'),
                    audio_url=tour_data.get('audioUrl'),
                    map_image_url=tour_data.get('mapImageUrl'),
                    duration_minutes=tour_data.get('durationMinutes'),
                    distance_meters=tour_data.get('distanceMeters'),
                    status=status
                )

                # Calculate center point from first site if not provided
                if tour_data['sites'] and len(tour_data['sites']) > 0:
                    first_site = tour_data['sites'][0]
                    if first_site.get('latitude') and first_site.get('longitude'):
                        tour.latitude = first_site['latitude']
                        tour.longitude = first_site['longitude']

                db.session.add(tour)
                db.session.flush()  # Get tour.id

                sites_created = 0

                # Process sites
                for order, site_data in enumerate(tour_data['sites'], start=1):
                    # Validate site required fields
                    if not site_data.get('title'):
                        current_app.logger.warning(f"Site missing title in tour {tour_data['name']}, skipping")
                        continue

                    if not site_data.get('latitude') or not site_data.get('longitude'):
                        current_app.logger.warning(f"Site {site_data.get('title')} missing coordinates, skipping")
                        continue

                    # Check if site exists by placeId
                    site = None
                    place_id = site_data.get('placeId')

                    if place_id:
                        site = Site.query.filter_by(place_id=place_id).first()

                    # Create new site if it doesn't exist
                    if not site:
                        site = Site(
                            id=uuid.uuid4(),
                            title=site_data['title'],
                            description=site_data.get('description'),
                            latitude=site_data['latitude'],
                            longitude=site_data['longitude'],
                            image_url=site_data.get('imageUrl'),
                            audio_url=site_data.get('audioUrl'),
                            web_url=site_data.get('webUrl'),
                            keywords=site_data.get('keywords', []),
                            rating=site_data.get('rating'),
                            city=site_data.get('city'),
                            neighborhood=site_data.get('neighborhood'),
                            place_id=place_id,
                            formatted_address=site_data.get('formatted_address'),
                            types=site_data.get('types', []),
                            user_ratings_total=site_data.get('user_ratings_total'),
                            phone_number=site_data.get('phone_number')
                        )
                        db.session.add(site)
                        db.session.flush()
                        sites_created += 1

                    # Create tour-site relationship
                    tour_site = TourSite(
                        tour_id=tour.id,
                        site_id=site.id,
                        display_order=order
                    )
                    db.session.add(tour_site)

                # Commit this tour
                db.session.commit()

                success.append({
                    'tourName': tour.name,
                    'tourId': str(tour.id),
                    'sitesCreated': sites_created,
                    'status': status
                })

                current_app.logger.info(f"Uploaded tour: {tour.name} ({len(tour_data['sites'])} sites)")

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error uploading tour {tour_data.get('name', 'Unknown')}: {e}")
                errors.append({
                    'tourName': tour_data.get('name', 'Unknown'),
                    'error': str(e)
                })

        return jsonify({
            'success': success,
            'errors': errors,
            'summary': {
                'total': len(tours_data),
                'succeeded': len(success),
                'failed': len(errors)
            }
        }), 201 if len(success) > 0 else 400

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk upload: {e}")
        return jsonify({
            'error': 'Upload failed',
            'message': str(e)
        }), 500


