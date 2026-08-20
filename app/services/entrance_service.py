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

# Only the fields needed to pick an entrance. Note that entrances and
# navigationPoints are siblings of primary, not nested inside it - asking for
# them under primary is rejected as an invalid argument.
FIELD_MASK = (
    'destinations.primary.location,'
    'destinations.primary.structureType,'
    'destinations.entrances,'
    'destinations.navigationPoints'
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


def extract_structure_type(result: dict):
    """
    How big the place is: 'POINT', 'BUILDING', or 'GROUNDS'.

    This is what makes a large shift interpretable. A GROUNDS place - a park,
    campus, or memorial plaza - legitimately has entrances hundreds of metres
    from its centroid, while the same shift on a POINT storefront means
    something went wrong. Returns None when the response does not say.
    """
    destinations = result.get('destinations') or []
    if not destinations:
        return None
    return (destinations[0].get('primary') or {}).get('structureType')


def _coords(obj):
    """Pull (lat, lng) out of a location field, or None if incomplete."""
    location = (obj or {}).get('location') or {}
    if 'latitude' in location and 'longitude' in location:
        return (location['latitude'], location['longitude'])
    return None


def _belongs_to(entrance, place_id: str) -> bool:
    """
    Whether an entrance is this place's own.

    A response can include every entrance on a shared building, including
    other tenants' doors. Each entrance carries the place it serves, so
    anything naming a different place is discarded - a neighbour's door is
    worse than the centroid. Entrances with no place named are kept.
    """
    place = entrance.get('place')
    return not place or place.split('/')[-1] == place_id


def extract_entrance(result: dict, place_id: str, centroid):
    """
    Pick the best routing coordinate from a SearchDestinations response.

    Preference order:
      1. An entrance tagged PREFERRED (the main entrance).
      2. Any other entrance belonging to this place.
      3. A navigation point that supports WALK.

    `centroid` is the site's stored (lat, lng), used to break ties: a place
    can return several entrances all tagged PREFERRED, so the nearest one is
    chosen for a stable, minimal shift rather than depending on list order.

    Returns (latitude, longitude, source), or None when the response offers
    nothing better than the centroid.
    """
    destinations = result.get('destinations') or []
    if not destinations:
        return None
    destination = destinations[0]

    entrances = [e for e in (destination.get('entrances') or [])
                 if _coords(e) and _belongs_to(e, place_id)]

    preferred = [e for e in entrances if 'PREFERRED' in (e.get('tags') or [])]
    candidates = preferred or entrances
    if candidates:
        best = min(candidates,
                   key=lambda e: _distance(centroid, _coords(e)))
        source = 'preferred_entrance' if preferred else 'entrance'
        return (*_coords(best), source)

    # A large site returns many perimeter access points - The Battery has
    # eight walkable ones spread from 118m to 284m out. List order is
    # arbitrary, so take the nearest rather than whichever came first.
    walkable = [p for p in (destination.get('navigationPoints') or [])
                if 'WALK' in (p.get('travelModes') or []) and _coords(p)]
    if walkable:
        best = min(walkable, key=lambda p: _distance(centroid, _coords(p)))
        return (*_coords(best), 'walk_navigation_point')

    return None


def _distance(a, b) -> float:
    """Straight-line metres between two (lat, lng) pairs."""
    from app.services.route_planner import haversine
    return haversine(a, b)
