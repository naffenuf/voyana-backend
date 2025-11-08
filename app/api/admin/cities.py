"""
Admin city management endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.models.city import City
from app.models.tour import Tour
from app.utils.admin_required import admin_required
from sqlalchemy import func

admin_cities_bp = Blueprint('admin_cities', __name__)


@admin_cities_bp.route('/all-from-tours', methods=['GET'])
@jwt_required()
@admin_required()
def get_all_cities_from_tours():
    """
    Get all unique cities from tours with their city record status.

    Similar to neighborhoods endpoint - shows which cities need hero images.

    Returns:
        [
            {
                "name": "New York",
                "tourCount": 150,
                "hasRecord": true,
                "id": 1,
                "heroImageUrl": "...",
                "heroTitle": "...",
                "latitude": 40.7589,
                "longitude": -73.9851
            },
            ...
        ]
    """
    try:
        # Get all unique cities from published tours with tour counts
        city_tour_counts = db.session.query(
            Tour.city,
            func.count(Tour.id).label('tour_count')
        ).filter(
            Tour.status == 'published',
            Tour.city.isnot(None),
            Tour.city != ''
        ).group_by(Tour.city).all()

        # Get existing city records
        existing_cities = City.query.filter_by(is_active=True).all()
        city_records = {city.name: city for city in existing_cities}

        # Build response
        result = []
        for city_name, tour_count in city_tour_counts:
            city_record = city_records.get(city_name)

            result.append({
                'name': city_name,
                'tourCount': tour_count,
                'hasRecord': city_record is not None,
                'id': city_record.id if city_record else None,
                'heroImageUrl': city_record.hero_image_url if city_record else None,
                'heroTitle': city_record.hero_title if city_record else None,
                'heroSubtitle': city_record.hero_subtitle if city_record else None,
                'latitude': city_record.latitude if city_record else None,
                'longitude': city_record.longitude if city_record else None,
                'country': city_record.country if city_record else None,
                'stateProvince': city_record.state_province if city_record else None,
            })

        # Sort by tour count (descending)
        result.sort(key=lambda x: x['tourCount'], reverse=True)

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f'Error getting cities from tours: {e}', exc_info=True)
        return jsonify({'error': 'Failed to fetch cities'}), 500


@admin_cities_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_cities():
    """
    List all cities with optional filters.

    Query params:
        - name: Filter by city name (case-insensitive contains)
        - include_inactive: Include inactive cities (default: false)

    Returns:
        [
            {
                "id": 1,
                "name": "New York",
                "latitude": 40.7589,
                "longitude": -73.9851,
                "heroImageUrl": "...",
                "heroTitle": "...",
                "tourCount": 150,
                "isActive": true
            },
            ...
        ]
    """
    try:
        # Build query
        query = City.query

        # Filter by active status
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        if not include_inactive:
            query = query.filter_by(is_active=True)

        # Filter by name
        name_filter = request.args.get('name', '').strip()
        if name_filter:
            query = query.filter(City.name.ilike(f'%{name_filter}%'))

        cities = query.all()

        # Add tour counts
        result = []
        for city in cities:
            tour_count = Tour.query.filter_by(
                city=city.name,
                status='published'
            ).count()

            city_dict = city.to_dict()
            city_dict['tourCount'] = tour_count
            result.append(city_dict)

        # Sort by name
        result.sort(key=lambda x: x['name'])

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f'Error listing cities: {e}', exc_info=True)
        return jsonify({'error': 'Failed to list cities'}), 500


@admin_cities_bp.route('/<int:city_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_city(city_id):
    """
    Get a specific city by ID.

    Returns:
        {
            "id": 1,
            "name": "New York",
            "latitude": 40.7589,
            "longitude": -73.9851,
            "heroImageUrl": "...",
            "heroTitle": "...",
            "tourCount": 150
        }
    """
    try:
        city = City.query.get(city_id)

        if not city:
            return jsonify({'error': 'City not found'}), 404

        city_dict = city.to_dict()

        # Add tour count
        tour_count = Tour.query.filter_by(
            city=city.name,
            status='published'
        ).count()
        city_dict['tourCount'] = tour_count

        return jsonify(city_dict), 200

    except Exception as e:
        current_app.logger.error(f'Error getting city {city_id}: {e}', exc_info=True)
        return jsonify({'error': 'Failed to get city'}), 500


@admin_cities_bp.route('', methods=['POST'])
@jwt_required()
@admin_required()
def create_city():
    """
    Create a new city.

    Request body:
        {
            "name": "San Francisco",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "heroImageUrl": "https://...",
            "heroTitle": "Explore San Francisco",
            "heroSubtitle": "",
            "country": "United States",
            "stateProvince": "California",
            "timezone": "America/Los_Angeles"
        }

    Returns:
        {
            "message": "City created successfully",
            "city": {...}
        }
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('name') or data.get('latitude') is None or data.get('longitude') is None:
            return jsonify({'error': 'Missing required fields: name, latitude, longitude'}), 400

        # Check if city with same name and coordinates already exists
        existing = City.query.filter_by(
            name=data['name'],
            latitude=data['latitude'],
            longitude=data['longitude']
        ).first()

        if existing:
            return jsonify({'error': 'City with same name and location already exists'}), 409

        # Create new city
        city = City(
            name=data['name'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            hero_image_url=data.get('heroImageUrl'),
            hero_title=data.get('heroTitle'),
            hero_subtitle=data.get('heroSubtitle', 'Self-Guided Audio Walking Tours'),
            country=data.get('country'),
            state_province=data.get('stateProvince'),
            timezone=data.get('timezone'),
            is_active=data.get('isActive', True)
        )

        db.session.add(city)
        db.session.commit()

        current_app.logger.info(f'City created: {city.name} (ID: {city.id})')

        return jsonify({
            'message': 'City created successfully',
            'city': city.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating city: {e}', exc_info=True)
        return jsonify({'error': 'Failed to create city'}), 500


@admin_cities_bp.route('/<int:city_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_city(city_id):
    """
    Update a city.

    Request body: Same as POST (all fields optional)

    Returns:
        {
            "message": "City updated successfully",
            "city": {...}
        }
    """
    try:
        city = City.query.get(city_id)

        if not city:
            return jsonify({'error': 'City not found'}), 404

        data = request.get_json()

        # Update fields if provided
        if 'name' in data:
            city.name = data['name']
        if 'latitude' in data:
            city.latitude = data['latitude']
        if 'longitude' in data:
            city.longitude = data['longitude']
        if 'heroImageUrl' in data:
            city.hero_image_url = data['heroImageUrl']
        if 'heroTitle' in data:
            city.hero_title = data['heroTitle']
        if 'heroSubtitle' in data:
            city.hero_subtitle = data['heroSubtitle']
        if 'country' in data:
            city.country = data['country']
        if 'stateProvince' in data:
            city.state_province = data['stateProvince']
        if 'timezone' in data:
            city.timezone = data['timezone']
        if 'isActive' in data:
            city.is_active = data['isActive']

        db.session.commit()

        current_app.logger.info(f'City updated: {city.name} (ID: {city.id})')

        return jsonify({
            'message': 'City updated successfully',
            'city': city.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating city {city_id}: {e}', exc_info=True)
        return jsonify({'error': 'Failed to update city'}), 500


@admin_cities_bp.route('/<int:city_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_city(city_id):
    """
    Soft delete a city (set is_active=False).

    Returns:
        {
            "message": "City deleted successfully"
        }
    """
    try:
        city = City.query.get(city_id)

        if not city:
            return jsonify({'error': 'City not found'}), 404

        city.is_active = False
        db.session.commit()

        current_app.logger.info(f'City deleted: {city.name} (ID: {city.id})')

        return jsonify({'message': 'City deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting city {city_id}: {e}', exc_info=True)
        return jsonify({'error': 'Failed to delete city'}), 500
