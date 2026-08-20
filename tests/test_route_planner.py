"""
Tests for route planning and entrance extraction (pure functions, no DB).
"""
import random

from app.services.route_planner import (
    haversine,
    haversine_matrix,
    path_length,
    plan_tour,
    score_start_candidates,
    solve_open_path,
    transit_score,
    _solve_brute_force,
    _solve_held_karp,
)
from app.services.entrance_service import extract_entrance, extract_structure_type


def random_matrix(n, seed):
    rng = random.Random(seed)
    return [[0.0 if i == j else rng.uniform(50, 1000) for j in range(n)]
            for i in range(n)]


class TestSolver:
    def test_held_karp_matches_brute_force(self):
        """Held-Karp must find the same optimal length as exhaustive search."""
        for seed in range(20):
            n = random.Random(seed).randint(3, 8)
            matrix = random_matrix(n, seed)
            for start in range(n):
                _, brute_len, _ = _solve_brute_force(matrix, start)
                _, hk_len, _ = _solve_held_karp(matrix, start)
                assert abs(brute_len - hk_len) < 1e-6

    def test_order_is_valid_permutation_starting_at_start(self):
        matrix = random_matrix(7, seed=42)
        order, total, _ = solve_open_path(matrix, start=3)
        assert order[0] == 3
        assert sorted(order) == list(range(7))
        assert abs(path_length(matrix, order) - total) < 1e-9

    def test_runner_up_is_never_better_than_best(self):
        matrix = random_matrix(6, seed=7)
        _, best, runner_up = solve_open_path(matrix, start=0)
        assert runner_up is not None
        assert runner_up >= best

    def test_open_path_beats_or_matches_any_fixed_endpoint(self):
        """A free endpoint can never be worse than forcing one."""
        matrix = random_matrix(6, seed=11)
        _, best, _ = solve_open_path(matrix, start=0)
        # Compare against best path forced to end at each specific site.
        from itertools import permutations
        for end in range(1, 6):
            middle = [i for i in range(1, 6) if i != end]
            forced = min(path_length(matrix, (0,) + p + (end,))
                         for p in permutations(middle))
            assert best <= forced + 1e-9

    def test_two_sites(self):
        matrix = [[0, 10], [10, 0]]
        order, total, _ = solve_open_path(matrix, start=1)
        assert order == [1, 0]
        assert total == 10


class TestGeometry:
    def test_haversine_known_distance(self):
        # Union Square to Washington Square Park is roughly 800m.
        d = haversine((40.7359, -73.9911), (40.7308, -73.9973))
        assert 700 < d < 900

    def test_haversine_matrix_symmetric_zero_diagonal(self):
        points = [(40.73, -73.99), (40.74, -73.98), (40.72, -74.00)]
        m = haversine_matrix(points)
        for i in range(3):
            assert m[i][i] == 0.0
            for j in range(3):
                assert abs(m[i][j] - m[j][i]) < 1e-9


class TestStartScoring:
    def test_transit_score_prefers_multiple_close_stations(self):
        stations = [{'name': 'A', 'location': (40.7300, -73.9900)},
                    {'name': 'B', 'location': (40.7302, -73.9902)}]
        near_both = transit_score((40.7301, -73.9901), stations)
        near_none = transit_score((40.7500, -73.9500), stations)
        assert near_both > 1.0
        assert near_none == 0.0

    def test_landmark_with_transit_beats_popular_restaurant(self):
        """The Tompkins Square case: park with subway access must outrank a
        well-reviewed bakery with none."""
        stations = [{'name': 'Stop', 'location': (40.7265, -73.9815)}]
        sites = [
            {'latitude': 40.7290, 'longitude': -73.9760,  # far from stop
             'types': ['bakery', 'food'], 'user_ratings_total': 5000},
            {'latitude': 40.7266, 'longitude': -73.9816,  # at the stop
             'types': ['park'], 'user_ratings_total': 500},
        ]
        scores = score_start_candidates(sites, stations)
        assert scores[1]['total'] > scores[0]['total']

    def test_plan_tour_reports_change_and_margin(self):
        # Four sites on a line, stored in a zigzag order; start forced to an
        # endpoint by transit. Optimal open path walks the line in order.
        sites = [
            {'latitude': 40.7000, 'longitude': -74.0000, 'types': ['park'],
             'user_ratings_total': 100},
            {'latitude': 40.7020, 'longitude': -74.0000, 'types': [],
             'user_ratings_total': 10},
            {'latitude': 40.7010, 'longitude': -74.0000, 'types': [],
             'user_ratings_total': 10},
            {'latitude': 40.7030, 'longitude': -74.0000, 'types': [],
             'user_ratings_total': 10},
        ]
        stations = [{'name': 'S', 'location': (40.7000, -74.0001)}]
        points = [(s['latitude'], s['longitude']) for s in sites]
        matrix = haversine_matrix(points)

        plan = plan_tour(sites, stations, matrix)
        assert plan['start_index'] == 0
        assert plan['order'] == [0, 2, 1, 3]
        assert plan['proposed_meters'] < plan['current_meters']
        assert plan['runner_up_margin_pct'] is not None
        assert plan['runner_up_margin_pct'] >= 0


class TestExtractEntrance:
    """
    Response shapes follow the live Geocoding v4 contract: entrances and
    navigationPoints are siblings of primary, and each entrance names the
    place it serves.
    """

    PLACE = 'ChIJtest'
    CENTROID = (40.7000, -74.0000)

    def _response(self, **destination):
        destination.setdefault('primary', {'location': {
            'latitude': self.CENTROID[0], 'longitude': self.CENTROID[1]}})
        return {'destinations': [destination]}

    def _loc(self, lat, lng, **extra):
        return {'location': {'latitude': lat, 'longitude': lng},
                'place': f'places/{self.PLACE}', **extra}

    def test_preferred_entrance_wins_over_plain_and_nav_point(self):
        result = self._response(
            entrances=[self._loc(40.7001, -74.0001),
                       self._loc(40.7002, -74.0002, tags=['PREFERRED'])],
            navigationPoints=[{'location': {'latitude': 40.9, 'longitude': -74.9},
                               'travelModes': ['WALK']}],
        )
        lat, lng, source = extract_entrance(result, self.PLACE, self.CENTROID)
        assert (round(lat, 4), round(lng, 4)) == (40.7002, -74.0002)
        assert source == 'preferred_entrance'

    def test_multiple_preferred_picks_nearest_to_centroid(self):
        """A place can tag several entrances PREFERRED; choice must be stable
        and minimal rather than dependent on list order."""
        far = self._loc(40.7050, -74.0050, tags=['PREFERRED'])
        near = self._loc(40.7001, -74.0001, tags=['PREFERRED'])
        for entrances in ([far, near], [near, far]):
            lat, lng, source = extract_entrance(
                self._response(entrances=entrances), self.PLACE, self.CENTROID)
            assert (round(lat, 4), round(lng, 4)) == (40.7001, -74.0001)
            assert source == 'preferred_entrance'

    def test_other_tenants_entrance_is_ignored(self):
        """Shared buildings return neighbours' doors too; those are worse than
        the centroid and must not be used."""
        result = self._response(entrances=[
            {'location': {'latitude': 40.7001, 'longitude': -74.0001},
             'tags': ['PREFERRED'], 'place': 'places/ChIJsomeoneelse'},
        ])
        assert extract_entrance(result, self.PLACE, self.CENTROID) is None

    def test_untagged_entrance_used_when_none_preferred(self):
        result = self._response(entrances=[self._loc(40.7001, -74.0001)])
        lat, lng, source = extract_entrance(result, self.PLACE, self.CENTROID)
        assert source == 'entrance'
        assert (round(lat, 4), round(lng, 4)) == (40.7001, -74.0001)

    def test_falls_back_to_walk_navigation_point(self):
        result = self._response(navigationPoints=[
            {'location': {'latitude': 40.71, 'longitude': -74.01},
             'travelModes': ['DRIVE']},
            {'location': {'latitude': 40.72, 'longitude': -74.02},
             'travelModes': ['DRIVE', 'WALK']},
        ])
        assert extract_entrance(result, self.PLACE, self.CENTROID) == (
            40.72, -74.02, 'walk_navigation_point')

    def test_structure_type_read_from_primary(self):
        result = self._response()
        result['destinations'][0]['primary']['structureType'] = 'GROUNDS'
        assert extract_structure_type(result) == 'GROUNDS'
        assert extract_structure_type({}) is None
        assert extract_structure_type(self._response()) is None

    def test_point_type_place_with_no_entrance_data(self):
        """Most small venues are structureType POINT and carry nothing."""
        assert extract_entrance({}, self.PLACE, self.CENTROID) is None
        assert extract_entrance({'destinations': []}, self.PLACE, self.CENTROID) is None
        assert extract_entrance(self._response(), self.PLACE, self.CENTROID) is None
        assert extract_entrance(
            self._response(navigationPoints=[
                {'location': {'latitude': 40.71, 'longitude': -74.01},
                 'travelModes': ['DRIVE']}]),
            self.PLACE, self.CENTROID) is None


class TestShiftLimits:
    """
    A large shift is only suspicious relative to how big the place is: a
    memorial plaza's entrance is legitimately far from its centroid.
    """

    def _limit(self, structure, override=None):
        from app.cli_route_planning import _shift_limit
        return _shift_limit(structure, override)

    def test_limit_scales_with_structure_type(self):
        assert self._limit('POINT') < self._limit('BUILDING') < self._limit('GROUNDS')

    def test_grounds_tolerates_a_shift_that_would_flag_a_point(self):
        """The WTC memorial case: ~209m is expected on GROUNDS, wrong on POINT."""
        shift = 209.4
        assert shift <= self._limit('GROUNDS')
        assert shift > self._limit('POINT')

    def test_unknown_structure_falls_back_to_default(self):
        from app.cli_route_planning import DEFAULT_MAX_SHIFT_M
        assert self._limit(None) == DEFAULT_MAX_SHIFT_M
        assert self._limit('SOMETHING_NEW') == DEFAULT_MAX_SHIFT_M

    def test_explicit_override_wins_for_every_type(self):
        for structure in ('POINT', 'BUILDING', 'GROUNDS', None):
            assert self._limit(structure, override=42.0) == 42.0
