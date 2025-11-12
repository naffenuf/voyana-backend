"""
Tour metrics calculation service.

Calculates tour distance and duration based on site locations and descriptions.
Matches iOS calculation logic for consistency.
"""

import math
from typing import Tuple


# Constants matching iOS implementation (Tour.swift:41-42)
WALKING_SPEED_METERS_PER_MINUTE = 73.15  # 22 min/mile strolling pace with dwell time
NARRATION_WORDS_PER_MINUTE = 130.0  # Natural tour pacing with pauses
CITY_GRID_ADJUSTMENT = 1.2  # Multiplier for straight-line distance to account for city grid


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Uses the Haversine formula to compute the distance between two latitude/longitude
    coordinates. Returns the distance in meters.

    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees

    Returns:
        Distance between the two points in meters
    """
    # Earth's radius in meters
    R = 6371000

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def count_words(text: str) -> int:
    """
    Count the number of words in a text string.

    Matches iOS implementation which uses split(separator: " ").

    Args:
        text: The text to count words in

    Returns:
        Number of words in the text
    """
    if not text:
        return 0
    return len(text.split())


def calculate_tour_metrics(tour) -> Tuple[float, int]:
    """
    Calculate tour distance and duration based on sites.

    Matches iOS calculation logic (Tour.swift:37-59):
    - Distance: Haversine distance between consecutive sites × 1.2 (city grid adjustment)
    - Duration: (distance / walking_speed) + (total_words / narration_speed), rounded up

    Args:
        tour: Tour model instance with tour_sites relationship loaded

    Returns:
        Tuple of (distance_meters, duration_minutes)
        - distance_meters: Total walking distance in meters (int, rounded)
        - duration_minutes: Total estimated duration in minutes (int, rounded up)
    """
    # Get sites ordered by display_order from tour_sites relationship
    tour_sites_ordered = sorted(tour.tour_sites, key=lambda ts: ts.display_order)
    sites = [ts.site for ts in tour_sites_ordered]

    if len(sites) == 0:
        return (0.0, 0)

    # Calculate total straight-line distance between consecutive sites
    total_distance = 0.0
    for i in range(len(sites) - 1):
        site1 = sites[i]
        site2 = sites[i + 1]

        # Both sites must have coordinates
        if (site1.latitude and site1.longitude and
            site2.latitude and site2.longitude):
            distance = haversine_distance(
                site1.latitude, site1.longitude,
                site2.latitude, site2.longitude
            )
            total_distance += distance

    # Apply city grid adjustment (multiply by 1.2)
    adjusted_distance = total_distance * CITY_GRID_ADJUSTMENT

    # Calculate walking time in minutes
    walking_minutes = adjusted_distance / WALKING_SPEED_METERS_PER_MINUTE

    # Calculate total words across all site descriptions
    total_words = sum(count_words(site.description or '') for site in sites)

    # Calculate narration time in minutes
    narration_minutes = total_words / NARRATION_WORDS_PER_MINUTE

    # Total duration (rounded up to nearest minute)
    total_minutes = math.ceil(walking_minutes + narration_minutes)

    # Round distance to nearest integer (sub-meter precision not needed for tours)
    distance_meters = round(adjusted_distance)

    return (distance_meters, total_minutes)
