"""
Entrance lookup service using Geocoding API v4 SearchDestinations.

Site coordinates come from Google Places and are building centroids, which can
route users to the wrong side of a building. SearchDestinations returns the
building's known entrances and walking navigation points for a place ID; the
best of those becomes the site's routing coordinate.

The site's stored latitude/longitude are never modified - entrances live in
separate columns and routing falls back to the centroid when no entrance is
known.
"""
import logging
import requests

logger = logging.getLogger(__name__)

SEARCH_DESTINATIONS_URL = 'https://geocode.googleapis.com/v4/geocode/destinations'

# Only the fields needed to pick an entrance.
FIELD_MASK = (
    'destinations.primary.location,'
    'destinations.primary.entrances,'
    'destinations.primary.navigationPoints'
)

REQUEST_TIMEOUT_SECONDS = 15


class EntranceLookupBlocked(Exception):
    """The API key does not allow Geocoding v4 SearchDestinations."""


def fetch_destination(api_key: str, place_id: str) -> dict:
    """
    Call SearchDestinations for one place ID and return the raw response.

    Raises EntranceLookupBlocked when the key blocks the v4 API (a Cloud
    Console configuration problem that retrying cannot fix), and
    requests.HTTPError for other failures.
    """
    response = requests.post(
        SEARCH_DESTINATIONS_URL,
        json={'place': f'places/{place_id}'},
        headers={
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': FIELD_MASK,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code == 403:
        detail = response.json().get('error', {}).get('message', '')
        if 'blocked' in detail.lower():
            raise EntranceLookupBlocked(
                'The Google API key blocks Geocoding v4 SearchDestinations. '
                'In Cloud Console: enable the Geocoding API for this project '
                "and add it to the key's API restrictions, then re-run. "
                f'({detail})'
            )

    response.raise_for_status()
    return response.json()


def extract_entrance(result: dict):
    """
    Pick the best routing coordinate from a SearchDestinations response.

    Preference order:
      1. An entrance tagged PREFERRED (the main entrance).
      2. The only entrance, when exactly one is returned.
      3. A navigation point that supports WALK.

    Returns (latitude, longitude, source) or None when the response offers
    nothing better than the centroid. Multiple untagged entrances are treated
    as ambiguous rather than guessed between.
    """
    destinations = result.get('destinations') or []
    if not destinations:
        return None
    primary = destinations[0].get('primary') or {}

    entrances = primary.get('entrances') or []
    preferred = [e for e in entrances if 'PREFERRED' in (e.get('tags') or [])]
    candidates = preferred or (entrances if len(entrances) == 1 else [])
    for entrance in candidates:
        location = entrance.get('location') or {}
        if 'latitude' in location and 'longitude' in location:
            source = 'preferred_entrance' if preferred else 'sole_entrance'
            return (location['latitude'], location['longitude'], source)

    for point in primary.get('navigationPoints') or []:
        if 'WALK' not in (point.get('travelModes') or []):
            continue
        location = point.get('location') or {}
        if 'latitude' in location and 'longitude' in location:
            return (location['latitude'], location['longitude'], 'walk_navigation_point')

    return None
