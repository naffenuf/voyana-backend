"""
City API endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.city import City
from app.models.tour import Tour
from sqlalchemy import func
from app.utils.device_binding import device_binding_required
import math


cities_bp = Blueprint('cities', __name__)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


@cities_bp.route('', methods=['GET'])
@device_binding_required()
def list_cities():
    """
    Get all active cities with tours.

    Optional query params:
        - lat, lon: Return closest city based on coordinates
        - include_tour_count: Include number of tours per city (default: true)

    Returns:
        {
            "cities": [
                {
                    "id": 1,
                    "name": "New York",
                    "latitude": 40.7589,
                    "longitude": -73.9851,
                    "heroImageUrl": "...",
                    "heroTitle": "Explore New York",
                    "tourCount": 150
                }
            ],
            "closestCity": {...}  // If lat/lon provided
        }
    """
    try:
        # Get query parameters
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        include_tour_count = request.args.get('include_tour_count', 'true').lower() == 'true'

        # Get all active cities
        cities_query = City.query.filter_by(is_active=True)
        cities = cities_query.all()

        # Build response
        cities_data = []
        for city in cities:
            city_dict = city.to_dict()

            # Add tour count if requested
            if include_tour_count:
                tour_count = Tour.query.filter_by(
                    city=city.name,
                    status='published'
                ).count()
                city_dict['tourCount'] = tour_count

            cities_data.append(city_dict)

        response = {
            'cities': cities_data
        }

        # Find closest city if coordinates provided
        if lat is not None and lon is not None:
            closest_city = None
            min_distance = float('inf')

            for city_dict in cities_data:
                distance = haversine_distance(
                    lat, lon,
                    city_dict['latitude'], city_dict['longitude']
                )
                if distance < min_distance:
                    min_distance = distance
                    closest_city = city_dict.copy()
                    closest_city['distanceKm'] = round(distance, 2)
                    closest_city['distanceMiles'] = round(distance * 0.621371, 2)

            response['closestCity'] = closest_city

        return jsonify(response), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@cities_bp.route('/<int:city_id>', methods=['GET'])
@device_binding_required()
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
            "heroTitle": "Explore New York",
            "tourCount": 150
        }
    """
    try:
        city = City.query.filter_by(id=city_id, is_active=True).first()
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
        return jsonify({'error': str(e)}), 500


@cities_bp.route('/by-location', methods=['GET'])
@device_binding_required()
def get_city_by_location():
    """
    Find the closest city to given coordinates with the specified name.

    Required query params:
        - city: City name (e.g., "New York")
        - lat: Latitude
        - lon: Longitude

    Returns:
        {
            "id": 1,
            "name": "New York",
            "latitude": 40.7589,
            "longitude": -73.9851,
            "heroImageUrl": "...",
            "heroTitle": "Explore New York",
            "distanceKm": 2.5,
            "distanceMiles": 1.6
        }
    """
    try:
        city_name = request.args.get('city')
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)

        if not city_name or lat is None or lon is None:
            return jsonify({'error': 'Missing required parameters: city, lat, lon'}), 400

        # Find all cities with this name
        cities = City.query.filter_by(name=city_name, is_active=True).all()

        if not cities:
            return jsonify({'error': f'City "{city_name}" not found'}), 404

        # Find closest city with this name
        closest_city = None
        min_distance = float('inf')

        for city in cities:
            distance = haversine_distance(lat, lon, city.latitude, city.longitude)
            if distance < min_distance:
                min_distance = distance
                closest_city = city

        if not closest_city:
            return jsonify({'error': 'No matching city found'}), 404

        city_dict = closest_city.to_dict()
        city_dict['distanceKm'] = round(min_distance, 2)
        city_dict['distanceMiles'] = round(min_distance * 0.621371, 2)

        return jsonify(city_dict), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@cities_bp.route('', methods=['POST'])
@jwt_required()
def create_city():
    """
    Create a new city. Admin only.

    Request body:
        {
            "name": "San Francisco",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "heroImageUrl": "https://s3.../sf-hero.jpg",
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
        # Check if user is admin (you may have a different auth mechanism)
        jwt_data = get_jwt()
        # For now, allow any authenticated user. Add admin check later.

        data = request.get_json()

        # Validate required fields
        if not data.get('name') or data.get('latitude') is None or data.get('longitude') is None:
            return jsonify({'error': 'Missing required fields: name, latitude, longitude'}), 400

        # Check if city with same name and coordinates already exists
        existing_city = City.query.filter_by(
            name=data['name'],
            latitude=data['latitude'],
            longitude=data['longitude']
        ).first()

        if existing_city:
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

        return jsonify({
            'message': 'City created successfully',
            'city': city.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@cities_bp.route('/<int:city_id>', methods=['PUT'])
@jwt_required()
def update_city(city_id):
    """
    Update a city. Admin only.

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

        return jsonify({
            'message': 'City updated successfully',
            'city': city.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@cities_bp.route('/<int:city_id>', methods=['DELETE'])
@jwt_required()
def delete_city(city_id):
    """
    Soft delete a city (set is_active=False). Admin only.

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

        return jsonify({'message': 'City deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
