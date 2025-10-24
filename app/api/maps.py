"""
Maps API endpoints (route optimization, directions).
"""
from flask import Blueprint, request, jsonify, current_app
from app.services.maps_service import optimize_route

maps_bp = Blueprint('maps', __name__)


@maps_bp.route('/route', methods=['POST'])
def get_route():
    """
    Get optimized route between origin, waypoints, and destination.

    Request body:
        {
            "origin": {"latitude": float, "longitude": float},
            "destination": {"latitude": float, "longitude": float},
            "waypoints": [{"id": str, "latitude": float, "longitude": float}],
            "mode": "walking" | "driving" | "bicycling" | "transit",
            "optimize": bool
        }

    Returns:
        {
            "overviewPolyline": str,
            "legPolylines": [str],
            "steps": [{...}],
            "totalDistanceMeters": int,
            "totalDurationSeconds": int,
            "waypointOrder": [int]
        }
    """
    try:
        data = request.json

        # Validate required parameters
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        if 'origin' not in data or 'latitude' not in data['origin'] or 'longitude' not in data['origin']:
            return jsonify({"error": "Origin with latitude and longitude is required"}), 400

        # Destination is optional - if not provided, we'll use the last waypoint as destination
        has_destination = ('destination' in data and
                          'latitude' in data.get('destination', {}) and
                          'longitude' in data.get('destination', {}))

        # Validate waypoints (required)
        if 'waypoints' not in data or not isinstance(data['waypoints'], list) or len(data['waypoints']) < 1:
            return jsonify({"error": "At least one waypoint is required"}), 400

        # Validate each waypoint has lat/lng
        for i, wp in enumerate(data['waypoints']):
            if 'latitude' not in wp or 'longitude' not in wp:
                return jsonify({"error": f"Waypoint at index {i} missing latitude or longitude"}), 400

        # Extract parameters
        origin = (data['origin']['latitude'], data['origin']['longitude'])

        # If destination not provided, use last waypoint as destination
        if has_destination:
            destination = (data['destination']['latitude'], data['destination']['longitude'])
            waypoints = data['waypoints']
        else:
            # Use all waypoints except the last one, and use the last one as destination
            waypoints = data['waypoints'][:-1]
            last_waypoint = data['waypoints'][-1]
            destination = (last_waypoint['latitude'], last_waypoint['longitude'])

        mode = data.get('mode', 'walking')
        optimize_flag = data.get('optimize', True)

        current_app.logger.info(f"Route request: {mode} mode, {len(waypoints)} waypoints")

        # Get route from maps service
        route_result = optimize_route(
            origin=origin,
            destination=destination,
            waypoints=waypoints,
            mode=mode,
            optimize=optimize_flag
        )

        if 'status' in route_result and route_result['status'] == 'error':
            error_message = route_result.get('message', 'Failed to generate route')
            current_app.logger.error(f"Error generating route: {error_message}")
            return jsonify({
                "error": error_message
            }), 500

        return jsonify(route_result), 200

    except Exception as e:
        current_app.logger.error(f"Error in route optimization: {e}", exc_info=True)
        return jsonify({
            "error": f"Failed to process route request: {str(e)}"
        }), 500
