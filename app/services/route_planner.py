"""
Route planning service.

Chooses a deliberate starting site for each tour and orders the remaining
sites as an open walking path. Tours are walked start-to-finish without
returning to the origin, so ordering minimises path length, not loop length.

Site counts are small (typically 3-9), so ordering is solved exactly rather
than heuristically: brute force up to BRUTE_FORCE_MAX_SITES (which also yields
the runner-up ordering, used to report how decisive the winner is), Held-Karp
beyond that. Only pairwise distances are fetched from Google; candidate
orderings are evaluated from that matrix in memory.
"""
import logging
import math
from itertools import permutations
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

logger = logging.getLogger(__name__)

EARTH_RADIUS_M = 6371000.0

# Places API (New) v1, matching the endpoints used in app/api/places.py, and
# Routes API v2. The legacy Distance Matrix and Places Nearby APIs are not
# enabled for this project, so the googlemaps client is not used here.
PLACES_API_BASE_URL = 'https://places.googleapis.com/v1'
SEARCH_NEARBY_ENDPOINT = f'{PLACES_API_BASE_URL}/places:searchNearby'
ROUTE_MATRIX_ENDPOINT = ('https://routes.googleapis.com'
                         '/distanceMatrix/v2:computeRouteMatrix')

REQUEST_TIMEOUT_SECONDS = 30

# Types that make a site a good place to begin: outdoors, findable, and
# recognisable as a meeting point.
ANCHOR_TYPES = {
    'tourist_attraction', 'historical_landmark', 'historical_place',
    'park', 'museum', 'plaza', 'monument', 'church', 'city_hall',
}

# Stations beyond this walking radius do not count toward a site's score.
TRANSIT_RADIUS_M = 500.0

# Margin added around the tour's own extent when searching for stations.
TRANSIT_SEARCH_MARGIN_M = 1200

# Relative weight of each signal when choosing the starting site. Transit
# access dominates, then landmark quality; review volume only breaks ties,
# because volume alone favours busy restaurants over actual landmarks.
WEIGHT_TRANSIT = 0.5
WEIGHT_ANCHOR = 0.3
WEIGHT_PROMINENCE = 0.2

# computeRouteMatrix allows 625 elements (origins x destinations) per request
# for non-traffic-aware modes, so any realistic tour fits in a single call.
MATRIX_MAX_ELEMENTS = 625

# Largest site count solved by brute force (with runner-up margin).
BRUTE_FORCE_MAX_SITES = 9

# searchNearby caps results per request.
MAX_NEARBY_RESULTS = 20


class GoogleServiceBlocked(Exception):
    """The API key is not permitted to call a required Google service."""


def _raise_if_blocked(response, service_label: str):
    """Turn a key-restriction 403 into an actionable error."""
    if response.status_code != 403:
        return
    try:
        message = response.json()['error']['message']
    except Exception:
        message = response.text[:200]
    raise GoogleServiceBlocked(
        f'The Google API key cannot call {service_label}. In Cloud Console, '
        f'enable it for the project and add it to the API restrictions of the '
        f'key the server uses. ({message})'
    )


def haversine(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Great-circle distance in metres between two (lat, lng) pairs."""
    lat1, lon1 = a
    lat2, lon2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    h = (math.sin(dphi / 2) ** 2 +
         math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def centroid(points: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Mean latitude and longitude of a set of points."""
    return (sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points))


# ---------------------------------------------------------------------------
# Transit
# ---------------------------------------------------------------------------

def find_transit_stations(api_key: str, points: Sequence[Tuple[float, float]]
                          ) -> List[Dict[str, Any]]:
    """
    Find transit stations near a tour via Places API (New) searchNearby.

    One search is issued per tour from its centroid rather than one per site,
    so every site is scored against the same complete station list. All
    station types go in a single request.
    """
    center = centroid(points)
    spread = max((haversine(center, p) for p in points), default=0.0)
    radius = float(min(spread + TRANSIT_SEARCH_MARGIN_M, 5000))

    response = requests.post(
        SEARCH_NEARBY_ENDPOINT,
        json={
            'includedTypes': ['subway_station', 'train_station',
                              'light_rail_station'],
            'maxResultCount': MAX_NEARBY_RESULTS,
            'locationRestriction': {
                'circle': {
                    'center': {'latitude': center[0], 'longitude': center[1]},
                    'radius': radius,
                }
            },
        },
        headers={
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': 'places.id,places.displayName,places.location',
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    _raise_if_blocked(response, 'Places API (New) searchNearby')
    response.raise_for_status()

    stations = []
    for place in response.json().get('places', []):
        location = place.get('location') or {}
        if 'latitude' not in location or 'longitude' not in location:
            continue
        stations.append({
            'name': (place.get('displayName') or {}).get('text', 'Unknown'),
            'location': (location['latitude'], location['longitude']),
        })
    return stations


def transit_score(point: Tuple[float, float],
                  stations: Sequence[Dict[str, Any]]) -> float:
    """
    Score a site's transit access.

    Sums an inverse-distance falloff over every station within walking range,
    so a site near several lines outscores one near a single stop.
    """
    total = 0.0
    for station in stations:
        d = haversine(point, station['location'])
        if d < TRANSIT_RADIUS_M:
            total += 1.0 - (d / TRANSIT_RADIUS_M)
    return total


# ---------------------------------------------------------------------------
# Start selection
# ---------------------------------------------------------------------------

def _normalise(values: Sequence[float]) -> List[float]:
    """Scale values to 0-1. Returns all zeros when they are all equal."""
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def score_start_candidates(sites: Sequence[Dict[str, Any]],
                           stations: Sequence[Dict[str, Any]]
                           ) -> List[Dict[str, Any]]:
    """
    Score each site's suitability as the tour's starting point.

    `sites` are dicts with latitude, longitude, types and user_ratings_total.
    Returns one score dict per site, aligned by index.
    """
    points = [(s['latitude'], s['longitude']) for s in sites]

    transit = [transit_score(p, stations) for p in points]
    anchor = [1.0 if ANCHOR_TYPES & set(s.get('types') or []) else 0.0
              for s in sites]
    prominence = [math.log1p(s.get('user_ratings_total') or 0) for s in sites]

    n_transit = _normalise(transit)
    n_prominence = _normalise(prominence)

    return [
        {
            'total': (WEIGHT_TRANSIT * n_transit[i] +
                      WEIGHT_ANCHOR * anchor[i] +
                      WEIGHT_PROMINENCE * n_prominence[i]),
            'transit': round(transit[i], 3),
            'anchor': bool(anchor[i]),
            'reviews': sites[i].get('user_ratings_total') or 0,
        }
        for i in range(len(sites))
    ]


# ---------------------------------------------------------------------------
# Walking distances
# ---------------------------------------------------------------------------

def walking_distance_matrix(api_key: str, points: Sequence[Tuple[float, float]]
                            ) -> Optional[List[List[float]]]:
    """
    Fetch pairwise walking distances in metres via Routes API v2
    computeRouteMatrix.

    The endpoint allows 625 elements per request, so any realistic tour fits
    in one call; larger inputs are refused rather than chunked. The response
    is a JSON array with one element per origin/destination pair. Pairs with
    no walking route fall back to straight-line distance. Returns None when
    the API fails outright, so the caller can skip the tour.
    """
    n = len(points)
    if n * n > MATRIX_MAX_ELEMENTS:
        logger.error(f'{n} sites is {n * n} elements, over the '
                     f'{MATRIX_MAX_ELEMENTS}-element request limit')
        return None

    waypoints = [{'waypoint': {'location': {'latLng': {
        'latitude': lat, 'longitude': lng}}}} for lat, lng in points]

    try:
        response = requests.post(
            ROUTE_MATRIX_ENDPOINT,
            json={
                'origins': waypoints,
                'destinations': waypoints,
                'travelMode': 'WALK',
            },
            headers={
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask':
                    'originIndex,destinationIndex,distanceMeters,condition',
            },
            timeout=REQUEST_TIMEOUT_SECONDS * 2,
        )
        _raise_if_blocked(response, 'Routes API v2 computeRouteMatrix')
        response.raise_for_status()
        elements = response.json()
    except GoogleServiceBlocked:
        raise
    except Exception as e:
        logger.error(f'computeRouteMatrix request failed: {e}')
        return None

    matrix = [[None] * n for _ in range(n)]
    for element in elements:
        i = element.get('originIndex')
        j = element.get('destinationIndex')
        if i is None or j is None:
            continue
        if (element.get('condition') == 'ROUTE_EXISTS'
                and 'distanceMeters' in element):
            matrix[i][j] = float(element['distanceMeters'])

    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 0.0
            elif matrix[i][j] is None:
                logger.warning(f'No walking route between points {i} and {j}; '
                               f'using straight-line distance')
                matrix[i][j] = haversine(points[i], points[j])

    return matrix


def haversine_matrix(points: Sequence[Tuple[float, float]]
                     ) -> List[List[float]]:
    """Straight-line matrix, used only for free previews of the planner."""
    n = len(points)
    return [[haversine(points[i], points[j]) for j in range(n)]
            for i in range(n)]


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

def path_length(matrix: Sequence[Sequence[float]],
                order: Sequence[int]) -> float:
    """Total distance for an ordering, with no return leg."""
    return sum(matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))


def _solve_brute_force(matrix, start):
    """Exact best and runner-up open paths from `start`."""
    n = len(matrix)
    rest = [i for i in range(n) if i != start]
    best = runner_up = None
    best_order = None
    for perm in permutations(rest):
        order = (start,) + perm
        length = path_length(matrix, order)
        if best is None or length < best:
            best, runner_up, best_order = length, best, order
        elif runner_up is None or length < runner_up:
            runner_up = length
    return list(best_order), best, runner_up


def _solve_held_karp(matrix, start):
    """Exact optimal open path from `start` for larger site counts."""
    n = len(matrix)
    full = (1 << n) - 1
    INF = float('inf')

    # cost[visited][last]: shortest path from `start` covering the sites in
    # `visited`, currently standing at `last`.
    cost = [[INF] * n for _ in range(1 << n)]
    parent = [[-1] * n for _ in range(1 << n)]
    cost[1 << start][start] = 0.0

    for visited in range(1 << n):
        if not (visited >> start) & 1:
            continue
        row = cost[visited]
        for last in range(n):
            here = row[last]
            if here == INF:
                continue
            for nxt in range(n):
                if (visited >> nxt) & 1:
                    continue
                merged = visited | (1 << nxt)
                candidate = here + matrix[last][nxt]
                if candidate < cost[merged][nxt]:
                    cost[merged][nxt] = candidate
                    parent[merged][nxt] = last

    end = min(range(n), key=lambda i: cost[full][i])
    total = cost[full][end]

    order = []
    visited, last = full, end
    while last != -1:
        order.append(last)
        previous = parent[visited][last]
        visited ^= (1 << last)
        last = previous
    order.reverse()

    return order, total, None


def solve_open_path(matrix: Sequence[Sequence[float]], start: int
                    ) -> Tuple[List[int], float, Optional[float]]:
    """
    Shortest path visiting every site once, beginning at `start`.

    The endpoint is chosen by the solver rather than fixed: tours stop at
    their last site instead of returning to the origin. Returns
    (order, total_metres, runner_up_metres); the runner-up is None when the
    site count forces the Held-Karp path.
    """
    n = len(matrix)
    if n == 1:
        return [start], 0.0, None
    if n <= BRUTE_FORCE_MAX_SITES:
        return _solve_brute_force(matrix, start)
    return _solve_held_karp(matrix, start)


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------

def plan_tour(sites: Sequence[Dict[str, Any]],
              stations: Sequence[Dict[str, Any]],
              matrix: Sequence[Sequence[float]]) -> Dict[str, Any]:
    """
    Choose a starting site and order the rest as an open walking path.

    `sites` are dicts (latitude, longitude, types, user_ratings_total) in
    their current stored order; `matrix` is pairwise walking distances in the
    same index space. Pure computation - all fetching happens in the caller.
    """
    n = len(sites)
    scores = score_start_candidates(sites, stations)
    start = max(range(n), key=lambda i: scores[i]['total'])

    order, proposed, runner_up = solve_open_path(matrix, start)
    current = path_length(matrix, list(range(n)))

    margin_pct = None
    if runner_up is not None and proposed > 0:
        margin_pct = round((runner_up / proposed - 1.0) * 100, 1)

    return {
        'order': order,
        'start_index': start,
        'proposed_meters': round(proposed, 1),
        'current_meters': round(current, 1),
        'runner_up_margin_pct': margin_pct,
        'scores': scores,
    }
