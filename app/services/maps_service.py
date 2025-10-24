"""
Maps service for route optimization using Google Directions API.
"""
import logging
import googlemaps
from datetime import datetime
from flask import current_app
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def get_maps_client():
    """Get Google Maps API client."""
    api_key = current_app.config.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("Google Maps API key not configured")
    return googlemaps.Client(key=api_key)


def optimize_route(origin: Tuple[float, float],
                   destination: Tuple[float, float],
                   waypoints: List[Dict[str, Any]],
                   mode: str = "walking",
                   optimize: bool = True) -> Dict[str, Any]:
    """
    Generate an optimized route between origin, waypoints, and destination.

    Args:
        origin: (latitude, longitude) tuple for starting point
        destination: (latitude, longitude) tuple for ending point
        waypoints: List of waypoint dicts with 'latitude' and 'longitude' keys
        mode: Travel mode ('walking', 'driving', 'bicycling', 'transit')
        optimize: Whether to optimize the waypoint order

    Returns:
        Dictionary with route information matching iOS expectations
    """
    try:
        client = get_maps_client()

        # Format intermediate waypoints for the API
        intermediate_points = []
        for wp in waypoints:
            if 'latitude' in wp and 'longitude' in wp:
                intermediate_points.append({
                    "lat": wp['latitude'],
                    "lng": wp['longitude']
                })

        logger.info(f"Requesting route: {mode} mode, {len(intermediate_points)} waypoints, optimize={optimize}")

        # Call Google Maps Directions API
        directions_result = client.directions(
            origin=origin,
            destination=destination,
            waypoints=intermediate_points if intermediate_points else None,
            optimize_waypoints=optimize,
            mode=mode,
            departure_time=datetime.now()
        )

        if not directions_result:
            return {
                "status": "error",
                "message": "No route found"
            }

        # Process the result
        route = directions_result[0]
        legs = route.get('legs', [])

        # Calculate total distance and duration
        total_distance = sum(leg.get('distance', {}).get('value', 0) for leg in legs)
        total_duration = sum(leg.get('duration', {}).get('value', 0) for leg in legs)

        # Get the optimized waypoint order if available
        waypoint_order = route.get('waypoint_order', [])

        # Extract leg polylines
        leg_polylines = []
        for leg in legs:
            if 'steps' in leg and leg['steps']:
                # Concatenate all step polylines for this leg
                step_polylines = [
                    step.get('polyline', {}).get('points', '')
                    for step in leg['steps']
                ]
                leg_polylines.append("".join(step_polylines))
            else:
                leg_polylines.append("")

        # Extract steps from all legs with leg index
        all_steps = []
        for leg_idx, leg in enumerate(legs):
            for step in leg.get('steps', []):
                start_loc = step.get('start_location', {})
                end_loc = step.get('end_location', {})

                step_info = {
                    'legIndex': leg_idx,
                    'startLocation': [start_loc.get('lat'), start_loc.get('lng')],
                    'endLocation': [end_loc.get('lat'), end_loc.get('lng')],
                    'distance': step.get('distance', {}).get('value'),
                    'duration': step.get('duration', {}).get('value'),
                    'instructions': step.get('html_instructions', ''),
                    'polyline': step.get('polyline', {}).get('points', '')
                }
                all_steps.append(step_info)

        # Get the overview polyline
        overview_polyline = route.get('overview_polyline', {}).get('points', '')

        # Build response matching iOS expectations
        response = {
            "overviewPolyline": overview_polyline,
            "legPolylines": leg_polylines,
            "steps": all_steps,
            "totalDistanceMeters": total_distance,
            "totalDurationSeconds": total_duration,
            "waypointOrder": waypoint_order
        }

        logger.info(f"Route generated successfully: {total_distance}m, {total_duration}s")
        return response

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Error generating route: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error generating route: {str(e)}"
        }
