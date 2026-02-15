"""
Tours API endpoints.
"""
from flask import Blueprint, request, jsonify, current_app, g
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt
from sqlalchemy import or_
from app import db, limiter
from app.models.tour import Tour, TourSite
from app.models.direction_segment import DirectionSegment
from app.models.site import Site
from app.models.user import User
from app.services.tts_service import generate_audio
from app.services.tour_calculator import calculate_tour_metrics
from app.utils.device_binding import device_binding_required, get_device_id_for_rate_limit
from app.utils.rate_limiting import get_user_audio_limit, get_audio_rate_limit_key
import math
import time

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
@device_binding_required()
@limiter.limit("100 per hour", key_func=get_device_id_for_rate_limit)
def list_tours():
    """
    List tours (requires authentication).

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
    # Get authenticated user ID (JWT required)
    jwt_identity = get_jwt_identity()
    user_id = int(jwt_identity) if jwt_identity and jwt_identity.isdigit() else None

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
    owner_id = request.args.get('owner_id', type=int)
    exclude_owner = request.args.get('exclude_owner', type=int)

    # Build query
    query = Tour.query

    # Access control
    if exclude_owner:
        # For "Other Tours" section - published tours NOT owned by user
        query = query.filter(
            Tour.status == 'published',
            Tour.owner_id != exclude_owner
        )
    elif owner_id:
        # For "Your Tours" section - only tours owned by specific user
        query = query.filter(Tour.owner_id == owner_id)
    else:
        # Regular access control: published tours OR user's own tours
        query = query.filter(
            or_(
                Tour.status == 'published',
                Tour.owner_id == user_id
            )
        )

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
@device_binding_required()
def get_tour(tour_id):
    """
    Get a specific tour by ID (requires authentication).

    Returns:
        {
            "tour": {...}
        }
    """
    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Get authenticated user ID
    jwt_identity = get_jwt_identity()
    user_id = int(jwt_identity) if jwt_identity and jwt_identity.isdigit() else None

    # Allow access if tour is published OR user is the owner OR user is admin
    if tour.status != 'published' and tour.owner_id != user_id:
        # Check if user is admin
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

    # Get tour data
    tour_data = tour.to_dict()

    return jsonify({'tour': tour_data}), 200


@tours_bp.route('', methods=['POST'])
@device_binding_required()
@limiter.limit("50 per hour", key_func=get_device_id_for_rate_limit)
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
@device_binding_required()
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
        # Filter out empty/whitespace-only strings
        music_urls = [url.strip() for url in data['musicUrls'] if url and url.strip()]
        tour.music_urls = music_urls if music_urls else None
    if 'durationMinutes' in data:
        tour.duration_minutes = data['durationMinutes']
    if 'distanceMeters' in data:
        tour.distance_meters = data['distanceMeters']

    # Track if is_ordered changed (for map regeneration)
    is_ordered_changed = False
    if 'isOrdered' in data:
        old_value = tour.is_ordered
        tour.is_ordered = data['isOrdered']
        is_ordered_changed = old_value != data['isOrdered']
        # If disabling isOrdered, also disable hasFixedDirections
        if not data['isOrdered'] and tour.has_fixed_directions:
            tour.has_fixed_directions = False

    # Handle hasFixedDirections (requires isOrdered to be True)
    if 'hasFixedDirections' in data:
        if data['hasFixedDirections']:
            # Validate that isOrdered is True when enabling fixed directions
            is_ordered = data.get('isOrdered', tour.is_ordered)
            if not is_ordered:
                return jsonify({'error': 'Fixed directions requires fixed route order (isOrdered must be true)'}), 400
            tour.has_fixed_directions = True
        else:
            tour.has_fixed_directions = False

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

        # Clear direction segments when sites are reordered (transitions are invalidated)
        if tour.has_fixed_directions:
            deleted_segments = DirectionSegment.query.filter_by(tour_id=tour.id).delete()
            if deleted_segments > 0:
                current_app.logger.info(
                    f'Cleared {deleted_segments} direction segments for tour {tour.id} due to site reordering'
                )

        # Auto-calculate tour metrics based on updated sites
        # Flush to ensure tour_sites relationships are available
        db.session.flush()

        # Expire the tour_sites relationship to force fresh reload from database
        # This ensures we get the updated tour_sites after delete/recreate operations
        db.session.expire(tour, ['tour_sites'])

        # Refresh the tour.sites relationship to get updated data
        db.session.refresh(tour)

        # Calculate and update distance/duration
        distance_meters, duration_minutes = calculate_tour_metrics(tour)
        tour.distance_meters = distance_meters
        tour.duration_minutes = duration_minutes

        current_app.logger.info(
            f'Auto-calculated metrics for tour {tour.id}: '
            f'{distance_meters:.1f}m, {duration_minutes}min'
        )

        # Auto-regenerate map when sites change
        try:
            from app.services.map_generation_service import map_generation_service
            current_app.logger.info(f'Auto-regenerating map for tour {tour.id}')
            map_url = map_generation_service.generate_tour_map(str(tour.id))
            if map_url:
                tour.map_image_url = map_url
                current_app.logger.info(f'Successfully regenerated map for tour {tour.id}: {map_url}')
            else:
                current_app.logger.warning(f'Failed to auto-regenerate map for tour {tour.id}')
        except Exception as e:
            current_app.logger.error(f'Error auto-regenerating map for tour {tour.id}: {e}')
            # Don't fail the whole request if map generation fails

    # Regenerate map if is_ordered changed (route display will be different)
    elif is_ordered_changed and len(tour.tour_sites) >= 2:
        try:
            from app.services.map_generation_service import map_generation_service
            current_app.logger.info(f'Regenerating map for tour {tour.id} due to is_ordered change')
            map_url = map_generation_service.generate_tour_map(str(tour.id))
            if map_url:
                tour.map_image_url = map_url
                current_app.logger.info(f'Successfully regenerated map for tour {tour.id}: {map_url}')
            else:
                current_app.logger.warning(f'Failed to regenerate map for tour {tour.id}')
        except Exception as e:
            current_app.logger.error(f'Error regenerating map for tour {tour.id}: {e}')
            # Don't fail the whole request if map generation fails

    db.session.commit()

    current_app.logger.info(f'Updated tour: {tour.id} ({tour.name})')

    return jsonify({'tour': tour.to_dict()}), 200


@tours_bp.route('/<uuid:tour_id>', methods=['DELETE'])
@device_binding_required()
def delete_tour(tour_id):
    """
    Delete a tour (owner or admin only).

    Query params:
        - delete_sites: If 'true', also delete sites that are ONLY in this tour
                       (sites shared with other tours are preserved)

    Returns:
        {
            "message": "Tour deleted successfully",
            "sitesDeleted": 0,  // Only present if delete_sites=true
            "s3FilesDeleted": 0  // Only present if delete_sites=true
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
    sites_deleted = 0
    s3_files_deleted = 0

    # Check if we should also delete sites
    delete_sites = request.args.get('delete_sites', 'false').lower() == 'true'

    try:
        if delete_sites:
            # Get all site IDs for this tour
            tour_site_ids = [ts.site_id for ts in tour.tour_sites]

            if tour_site_ids:
                # Efficient query: find sites that are ONLY in this tour
                # Subquery gets all site_ids that appear in OTHER tours
                from sqlalchemy import and_
                shared_site_ids_subquery = db.session.query(TourSite.site_id).filter(
                    TourSite.tour_id != tour_id
                ).subquery()

                # Get sites that are in this tour but NOT in the shared subquery
                sites_to_delete = Site.query.filter(
                    Site.id.in_(tour_site_ids),
                    ~Site.id.in_(shared_site_ids_subquery)
                ).all()

                # Delete sites with S3 cleanup
                if sites_to_delete:
                    from app.services.site_service import bulk_delete_sites_with_assets

                    # Log what we're deleting
                    for site in sites_to_delete:
                        current_app.logger.info(f'Deleting site {site.id} ({site.title}) - only in tour {tour_id}')

                    result = bulk_delete_sites_with_assets(sites_to_delete)
                    sites_deleted = result['sites_deleted']
                    s3_files_deleted = result['s3_files_deleted']

                    current_app.logger.info(
                        f'Deleted {sites_deleted} sites and {s3_files_deleted} S3 files for tour {tour_id}'
                    )

                # Log sites that were preserved
                preserved_count = len(tour_site_ids) - sites_deleted
                if preserved_count > 0:
                    current_app.logger.info(f'Preserved {preserved_count} sites that are shared with other tours')

        db.session.delete(tour)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting tour {tour_id}: {e}', exc_info=True)
        return jsonify({'error': 'Failed to delete tour'}), 500

    current_app.logger.info(f'Deleted tour: {tour_id} ({tour_name})')

    response = {'message': 'Tour deleted successfully'}
    if delete_sites:
        response['sitesDeleted'] = sites_deleted
        response['s3FilesDeleted'] = s3_files_deleted

    return jsonify(response), 200


@tours_bp.route('/nearby', methods=['GET'])
@device_binding_required()
def nearby_tours():
    """
    Find tours by proximity, grouped by neighborhoods (requires authentication).

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

    # Get authenticated user ID (JWT required)
    jwt_identity = get_jwt_identity()
    user_id = int(jwt_identity) if jwt_identity and jwt_identity.isdigit() else None

    # Build base query
    query = Tour.query

    # Access control: published tours OR user's own tours
    query = query.filter(
        or_(
            Tour.status == 'published',
            Tour.owner_id == user_id
        )
    )

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

    # Filter by closest tour's city (unless city filter was explicitly provided)
    if not city and tours_with_distance:
        closest_city = tours_with_distance[0]['tour'].city
        if closest_city:
            tours_with_distance = [
                item for item in tours_with_distance
                if item['tour'].city and item['tour'].city.lower() == closest_city.lower()
            ]
            current_app.logger.info(f'Filtered tours to city: {closest_city} ({len(tours_with_distance)} tours)')

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

    # Get city context from closest tour
    city_context = None
    if tours_with_distance:
        from app.models.city import City
        import math

        def haversine_distance_km(lat1, lon1, lat2, lon2):
            """Calculate distance in kilometers."""
            R = 6371  # Earth radius in km
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            a = (math.sin(delta_lat / 2) ** 2 +
                 math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        # Get city name and coordinates from closest tour
        closest_tour = tours_with_distance[0]['tour']
        if closest_tour.city:
            # Find the city in database that matches name and is closest to tour coordinates
            cities_with_name = City.query.filter_by(
                name=closest_tour.city,
                is_active=True
            ).all()

            if cities_with_name:
                # Find closest city with this name
                closest_city = None
                min_distance = float('inf')

                for city_candidate in cities_with_name:
                    distance = haversine_distance_km(
                        closest_tour.latitude,
                        closest_tour.longitude,
                        city_candidate.latitude,
                        city_candidate.longitude
                    )
                    if distance < min_distance:
                        min_distance = distance
                        closest_city = city_candidate

                if closest_city:
                    city_context = {
                        'id': closest_city.id,
                        'name': closest_city.name,
                        'latitude': closest_city.latitude,
                        'longitude': closest_city.longitude,
                        'heroImageUrl': closest_city.hero_image_url,
                        'heroTitle': closest_city.hero_title,
                        'heroSubtitle': closest_city.hero_subtitle
                    }

    return jsonify({
        'tours': tours_data,
        'neighborhoods': selected_neighborhoods,
        'totalNeighborhoods': total_neighborhoods,
        'neighborhoodOffset': neighborhood_offset,
        'hasMore': end_idx < total_neighborhoods,
        'cityContext': city_context
    }), 200


@tours_bp.route('/<uuid:tour_id>/generate-audio-for-sites', methods=['POST'])
@device_binding_required()
@limiter.limit(get_user_audio_limit, key_func=get_audio_rate_limit_key)
def generate_audio_for_tour_sites(tour_id):
    """
    Generate audio for all sites in a tour that don't already have audio URLs.

    Args:
        tour_id: UUID of the tour

    Returns:
        {
            "sitesProcessed": 5,
            "sitesSkipped": 2,
            "results": [
                {
                    "siteId": "uuid",
                    "siteTitle": "Site Name",
                    "status": "success" | "skipped" | "error",
                    "audioUrl": "https://...",
                    "fromCache": true,
                    "error": "error message if failed"
                }
            ]
        }
    """
    user_id = get_jwt_identity()

    try:
        # Get the tour
        tour = Tour.query.get(tour_id)

        if not tour:
            return jsonify({'error': 'Tour not found'}), 404

        # Get current user to check admin status
        user = User.query.get(user_id)
        is_admin = user and user.role == 'admin'

        # Check if user has permission to modify this tour (owner or admin)
        if tour.owner_id != user_id and not is_admin:
            return jsonify({'error': 'You do not have permission to modify this tour'}), 403

        # Creators cannot modify tours that are in 'ready' status (submitted for review)
        if not is_admin and tour.status == 'ready':
            return jsonify({'error': 'Cannot modify tours that are submitted for review. An admin must revert to draft first.'}), 403

        # Get all sites for this tour through tour_sites junction table
        tour_sites = tour.tour_sites

        if not tour_sites:
            return jsonify({'error': 'Tour has no sites'}), 400

        results = []
        sites_processed = 0
        sites_skipped = 0

        current_app.logger.info(f'Generating audio for {len(tour_sites)} sites in tour {tour_id}')

        for tour_site in tour_sites:
            site = tour_site.site

            # Skip if site has no description
            if not site.description or not site.description.strip():
                current_app.logger.info(f'Site {site.id} has no description, skipping')
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'skipped',
                    'reason': 'No description to convert'
                })
                sites_skipped += 1
                continue

            # Generate audio for this site
            has_existing_audio = bool(site.audio_url)
            action = 'Regenerating' if has_existing_audio else 'Generating'
            current_app.logger.info(f'{action} audio for site {site.id}: {site.title}')

            # Add a small delay between requests to avoid rate limiting
            # Skip delay for first site (sites_processed == 0 and sites_skipped == 0)
            if sites_processed > 0 or sites_skipped > 0:
                time.sleep(1)  # 1 second delay between audio generation requests

            # Capture old URL for deletion (will be deleted by generate_audio after success)
            old_audio_url = site.audio_url if has_existing_audio else None
            audio_result = generate_audio(site.description, user_id=user_id, old_audio_url=old_audio_url)

            if audio_result['status'] == 'success':
                # Update site with audio URL
                site.audio_url = audio_result['audio_url']
                db.session.add(site)

                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'success',
                    'audioUrl': audio_result['audio_url'],
                    'fromCache': audio_result.get('from_cache', False)
                })
                sites_processed += 1
                current_app.logger.info(f'Successfully generated audio for site {site.id}')
            else:
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'error',
                    'error': audio_result.get('error', 'Unknown error')
                })
                current_app.logger.error(f'Failed to generate audio for site {site.id}: {audio_result.get("error")}')

        # Commit all changes
        try:
            db.session.commit()
            current_app.logger.info(f'Successfully generated audio for {sites_processed} sites, skipped {sites_skipped}')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error committing audio URLs: {e}')
            return jsonify({'error': 'Failed to save audio URLs to sites'}), 500

        return jsonify({
            'sitesProcessed': sites_processed,
            'sitesSkipped': sites_skipped,
            'results': results
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error generating audio for tour sites: {e}', exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@tours_bp.route('/<uuid:tour_id>/apply-location-to-sites', methods=['POST'])
@jwt_required()
def apply_location_to_sites(tour_id):
    """
    Apply the tour's city and neighborhood to all sites in the tour.

    Args:
        tour_id: UUID of the tour

    Returns:
        {
            "sitesUpdated": 5,
            "city": "San Francisco",
            "neighborhood": "Mission District"
        }
    """
    user_id = get_jwt_identity()
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    try:
        # Get the tour
        tour = Tour.query.get(tour_id)

        if not tour:
            return jsonify({'error': 'Tour not found'}), 404

        # Check if user has permission to modify this tour (owner or admin)
        if tour.owner_id != int(user_id) and not is_admin:
            return jsonify({'error': 'You do not have permission to modify this tour'}), 403

        # Creators cannot edit tours that are in 'ready' status
        if not is_admin and tour.status == 'ready':
            return jsonify({'error': 'Cannot edit tours that are submitted for review'}), 403

        # Get all sites for this tour
        tour_sites = tour.tour_sites

        if not tour_sites:
            return jsonify({'error': 'Tour has no sites'}), 400

        if not tour.city and not tour.neighborhood:
            return jsonify({'error': 'Tour has no city or neighborhood set'}), 400

        # Update all sites with tour's city and neighborhood
        sites_updated = 0
        for tour_site in tour_sites:
            site = tour_site.site
            if tour.city:
                site.city = tour.city
            if tour.neighborhood:
                site.neighborhood = tour.neighborhood
            db.session.add(site)
            sites_updated += 1

        db.session.commit()

        current_app.logger.info(
            f'Applied location to {sites_updated} sites in tour {tour_id}: '
            f'city={tour.city}, neighborhood={tour.neighborhood}'
        )

        return jsonify({
            'sitesUpdated': sites_updated,
            'city': tour.city,
            'neighborhood': tour.neighborhood
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error applying location to sites: {e}', exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@tours_bp.route('/<uuid:tour_id>/fact-check-sites', methods=['POST'])
@jwt_required()
def fact_check_tour_sites(tour_id):
    """
    Fact-check and rewrite descriptions for all sites in a tour using AI.
    This replaces the site descriptions in the database with fact-checked versions.

    Args:
        tour_id: UUID of the tour

    Returns:
        {
            "sitesProcessed": 5,
            "sitesSkipped": 2,
            "results": [
                {
                    "siteId": "uuid",
                    "siteTitle": "Site Name",
                    "status": "success" | "skipped" | "error",
                    "originalDescription": "...",
                    "newDescription": "...",
                    "changesLis": "...",
                    "error": "error message if failed"
                }
            ]
        }
    """
    from app.services.ai_service import ai_service

    user_id = get_jwt_identity()

    try:
        # Get the tour
        tour = Tour.query.get(tour_id)

        if not tour:
            return jsonify({'error': 'Tour not found'}), 404

        # Get current user to check admin status
        user = User.query.get(user_id)
        is_admin = user and user.role == 'admin'

        # Check if user has permission to modify this tour (owner or admin)
        if tour.owner_id != user_id and not is_admin:
            return jsonify({'error': 'You do not have permission to modify this tour'}), 403

        # Creators cannot modify tours that are in 'ready' status (submitted for review)
        if not is_admin and tour.status == 'ready':
            return jsonify({'error': 'Cannot modify tours that are submitted for review. An admin must revert to draft first.'}), 403

        # Get all sites for this tour through tour_sites junction table
        tour_sites = tour.tour_sites

        if not tour_sites:
            return jsonify({'error': 'Tour has no sites'}), 400

        results = []
        sites_processed = 0
        sites_skipped = 0

        current_app.logger.info(f'Fact-checking descriptions for {len(tour_sites)} sites in tour {tour_id}')

        for tour_site in tour_sites:
            site = tour_site.site

            # Skip if site has no description
            if not site.description or not site.description.strip():
                current_app.logger.info(f'Site {site.id} has no description, skipping')
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'skipped',
                    'reason': 'No description to fact-check'
                })
                sites_skipped += 1
                continue

            # Fact-check this site's description
            current_app.logger.info(f'Fact-checking site {site.id}: {site.title}')

            # Add a small delay between requests to avoid rate limiting
            if sites_processed > 0 or sites_skipped > 0:
                time.sleep(1)  # 1 second delay between API requests

            try:
                # Prepare location string
                location_str = f"{site.latitude}, {site.longitude}"
                if site.formatted_address:
                    location_str = f"{site.formatted_address} ({site.latitude}, {site.longitude})"

                # Call AI service with fact-check prompt
                ai_result = ai_service.execute_prompt(
                    prompt_name='fact_check_site_description',
                    variables={
                        'site_title': site.title,
                        'location': location_str,
                        'description': site.description
                    },
                    user_id=user_id
                )

                # Extract rewritten description and changes from parsed JSON
                if 'parsed' not in ai_result:
                    raise ValueError('AI response was not valid JSON')

                parsed = ai_result['parsed']
                new_description = parsed.get('rewritten_description')
                changes_list = parsed.get('changes_list')

                if not new_description:
                    raise ValueError('AI response missing rewritten_description')

                # Update site with new description
                original_description = site.description
                site.description = new_description
                db.session.add(site)

                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'success',
                    'originalDescription': original_description,
                    'newDescription': new_description,
                    'changesList': changes_list,
                    'traceId': ai_result.get('trace_id')
                })
                sites_processed += 1
                current_app.logger.info(f'Successfully fact-checked site {site.id}')

            except Exception as e:
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'error',
                    'error': str(e)
                })
                current_app.logger.error(f'Failed to fact-check site {site.id}: {e}')

        # Commit all changes
        try:
            db.session.commit()
            current_app.logger.info(f'Successfully fact-checked {sites_processed} sites, skipped {sites_skipped}')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error committing fact-checked descriptions: {e}')
            return jsonify({'error': 'Failed to save fact-checked descriptions to sites'}), 500

        return jsonify({
            'sitesProcessed': sites_processed,
            'sitesSkipped': sites_skipped,
            'results': results
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error fact-checking tour sites: {e}', exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@tours_bp.route('/<uuid:tour_id>/generate-map', methods=['POST'])
@jwt_required()
def generate_tour_map(tour_id):
    """
    Generate or regenerate map image for a tour (admin or owner only).

    Returns:
        {
            "mapUrl": "https://s3.../tour-xxx.png"
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

    try:
        from app.services.map_generation_service import map_generation_service

        current_app.logger.info(f'Manual map generation requested for tour {tour.id}')

        map_url = map_generation_service.generate_tour_map(str(tour_id))

        if not map_url:
            return jsonify({'error': 'Failed to generate map. Tour may have fewer than 2 sites with coordinates.'}), 400

        current_app.logger.info(f'Successfully generated map for tour {tour.id}: {map_url}')

        return jsonify({'mapUrl': map_url}), 200

    except Exception as e:
        current_app.logger.error(f'Error generating map for tour {tour.id}: {e}')
        return jsonify({'error': f'Failed to generate map: {str(e)}'}), 500


# ============================================================================
# Direction Segments API Endpoints
# ============================================================================

@tours_bp.route('/<uuid:tour_id>/directions', methods=['GET'])
@device_binding_required()
def get_tour_directions(tour_id):
    """
    Get all direction segments for a tour, grouped by transition.

    Returns:
        {
            "directions": [
                {
                    "fromSiteId": "uuid",
                    "toSiteId": "uuid",
                    "segments": [...]
                }
            ],
            "totalTransitions": 3,
            "completedTransitions": 2
        }
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check access (owner, admin, or published tour)
    if tour.status != 'published' and not is_admin and tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get all direction segments for this tour
    segments = DirectionSegment.query.filter_by(tour_id=tour_id).order_by(
        DirectionSegment.from_site_id,
        DirectionSegment.to_site_id,
        DirectionSegment.segment_order
    ).all()

    # Group segments by transition
    transitions = {}
    for segment in segments:
        key = (str(segment.from_site_id), str(segment.to_site_id))
        if key not in transitions:
            transitions[key] = {
                'fromSiteId': str(segment.from_site_id),
                'toSiteId': str(segment.to_site_id),
                'segments': []
            }
        transitions[key]['segments'].append(segment.to_dict())

    # Calculate total expected transitions based on tour sites
    tour_sites = TourSite.query.filter_by(tour_id=tour_id).order_by(TourSite.display_order).all()
    total_transitions = max(0, len(tour_sites) - 1)
    completed_transitions = len(transitions)

    return jsonify({
        'directions': list(transitions.values()),
        'totalTransitions': total_transitions,
        'completedTransitions': completed_transitions
    }), 200


@tours_bp.route('/<uuid:tour_id>/directions/<uuid:from_site_id>/<uuid:to_site_id>', methods=['GET'])
@device_binding_required()
def get_transition_directions(tour_id, from_site_id, to_site_id):
    """
    Get direction segments for a specific transition.

    Returns:
        {
            "fromSiteId": "uuid",
            "toSiteId": "uuid",
            "segments": [...]
        }
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check access
    if tour.status != 'published' and not is_admin and tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get segments for this transition
    segments = DirectionSegment.query.filter_by(
        tour_id=tour_id,
        from_site_id=from_site_id,
        to_site_id=to_site_id
    ).order_by(DirectionSegment.segment_order).all()

    return jsonify({
        'fromSiteId': str(from_site_id),
        'toSiteId': str(to_site_id),
        'segments': [s.to_dict() for s in segments]
    }), 200


@tours_bp.route('/<uuid:tour_id>/directions/<uuid:from_site_id>/<uuid:to_site_id>', methods=['PUT'])
@device_binding_required()
def upsert_transition_directions(tour_id, from_site_id, to_site_id):
    """
    Create or replace direction segments for a transition.

    Request body:
        {
            "segments": [
                {
                    "directionText": "Turn left at the fountain...",
                    "audioUrl": "https://...",  // optional
                    "triggerLatitude": 40.123,
                    "triggerLongitude": -74.456,
                    "triggerRadius": 21.0  // optional, default 21
                }
            ]
        }

    Returns:
        {
            "fromSiteId": "uuid",
            "toSiteId": "uuid",
            "segments": [...]
        }
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check ownership
    if not is_admin and tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Creators cannot edit tours in 'ready' status
    if not is_admin and tour.status == 'ready':
        return jsonify({'error': 'Cannot edit tours submitted for review'}), 403

    # Validate that fixed directions is enabled
    if not tour.has_fixed_directions:
        return jsonify({'error': 'Fixed directions not enabled for this tour'}), 400

    # Validate that from_site and to_site are in this tour
    from_site_in_tour = TourSite.query.filter_by(tour_id=tour_id, site_id=from_site_id).first()
    to_site_in_tour = TourSite.query.filter_by(tour_id=tour_id, site_id=to_site_id).first()

    if not from_site_in_tour or not to_site_in_tour:
        return jsonify({'error': 'Sites must be part of this tour'}), 400

    data = request.get_json()

    if not data or 'segments' not in data:
        return jsonify({'error': 'segments array is required'}), 400

    segments_data = data['segments']

    # Validate each segment
    for i, seg in enumerate(segments_data):
        if not seg.get('directionText'):
            return jsonify({'error': f'Segment {i}: directionText is required'}), 400
        if seg.get('triggerLatitude') is None or seg.get('triggerLongitude') is None:
            return jsonify({'error': f'Segment {i}: triggerLatitude and triggerLongitude are required'}), 400

        # Validate trigger radius (min 15, default 21)
        radius = seg.get('triggerRadius', 21.0)
        if radius < 15:
            return jsonify({'error': f'Segment {i}: triggerRadius must be at least 15 meters'}), 400

    # Delete existing segments for this transition
    DirectionSegment.query.filter_by(
        tour_id=tour_id,
        from_site_id=from_site_id,
        to_site_id=to_site_id
    ).delete()

    # Create new segments
    new_segments = []
    for order, seg in enumerate(segments_data):
        segment = DirectionSegment(
            tour_id=tour_id,
            from_site_id=from_site_id,
            to_site_id=to_site_id,
            segment_order=order,
            direction_text=seg['directionText'],
            audio_url=seg.get('audioUrl'),
            trigger_latitude=seg['triggerLatitude'],
            trigger_longitude=seg['triggerLongitude'],
            trigger_radius=seg.get('triggerRadius', 21.0)
        )
        db.session.add(segment)
        new_segments.append(segment)

    db.session.commit()

    current_app.logger.info(
        f'Updated direction segments for tour {tour_id}: {from_site_id} -> {to_site_id} ({len(new_segments)} segments)'
    )

    return jsonify({
        'fromSiteId': str(from_site_id),
        'toSiteId': str(to_site_id),
        'segments': [s.to_dict() for s in new_segments]
    }), 200


@tours_bp.route('/<uuid:tour_id>/directions/<uuid:from_site_id>/<uuid:to_site_id>', methods=['DELETE'])
@device_binding_required()
def delete_transition_directions(tour_id, from_site_id, to_site_id):
    """
    Delete all direction segments for a transition.

    Returns:
        {
            "message": "Deleted 3 segments"
        }
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check ownership
    if not is_admin and tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Creators cannot edit tours in 'ready' status
    if not is_admin and tour.status == 'ready':
        return jsonify({'error': 'Cannot edit tours submitted for review'}), 403

    # Delete segments
    deleted_count = DirectionSegment.query.filter_by(
        tour_id=tour_id,
        from_site_id=from_site_id,
        to_site_id=to_site_id
    ).delete()

    db.session.commit()

    current_app.logger.info(
        f'Deleted {deleted_count} direction segments for tour {tour_id}: {from_site_id} -> {to_site_id}'
    )

    return jsonify({'message': f'Deleted {deleted_count} segments'}), 200


@tours_bp.route('/<uuid:tour_id>/directions/<uuid:segment_id>/audio', methods=['POST'])
@device_binding_required()
def upload_direction_audio(tour_id, segment_id):
    """
    Upload audio file for a direction segment.

    Expects multipart form with 'audio' file field.

    Returns:
        {
            "audioUrl": "https://s3.../audio.mp3",
            "segment": {...}
        }
    """
    from app.services.s3_service import upload_file_to_s3

    user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check ownership
    if not is_admin and tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Creators cannot edit tours in 'ready' status
    if not is_admin and tour.status == 'ready':
        return jsonify({'error': 'Cannot edit tours submitted for review'}), 403

    # Find segment
    segment = DirectionSegment.query.filter_by(id=segment_id, tour_id=tour_id).first()

    if not segment:
        return jsonify({'error': 'Direction segment not found'}), 404

    # Check for audio file
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']

    if not audio_file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Validate file extension
    allowed_extensions = {'mp3', 'm4a', 'wav', 'aac'}
    ext = audio_file.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed_extensions:
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}), 400

    try:
        # Upload to S3
        import uuid as uuid_module
        filename = f"directions/{tour_id}/{segment_id}/{uuid_module.uuid4()}.{ext}"
        audio_url = upload_file_to_s3(audio_file, filename)

        # Update segment
        segment.audio_url = audio_url
        db.session.commit()

        current_app.logger.info(f'Uploaded audio for direction segment {segment_id}: {audio_url}')

        return jsonify({
            'audioUrl': audio_url,
            'segment': segment.to_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f'Error uploading direction audio: {e}')
        return jsonify({'error': f'Failed to upload audio: {str(e)}'}), 500


@tours_bp.route('/<uuid:tour_id>/directions/<uuid:segment_id>/audio', methods=['DELETE'])
@device_binding_required()
def delete_direction_audio(tour_id, segment_id):
    """
    Remove audio file from a direction segment.

    Returns:
        {
            "message": "Audio removed",
            "segment": {...}
        }
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get('role') == 'admin'

    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check ownership
    if not is_admin and tour.owner_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Creators cannot edit tours in 'ready' status
    if not is_admin and tour.status == 'ready':
        return jsonify({'error': 'Cannot edit tours submitted for review'}), 403

    # Find segment
    segment = DirectionSegment.query.filter_by(id=segment_id, tour_id=tour_id).first()

    if not segment:
        return jsonify({'error': 'Direction segment not found'}), 404

    # Clear audio URL
    old_url = segment.audio_url
    segment.audio_url = None
    db.session.commit()

    current_app.logger.info(f'Removed audio from direction segment {segment_id} (was: {old_url})')

    return jsonify({
        'message': 'Audio removed',
        'segment': segment.to_dict()
    }), 200
