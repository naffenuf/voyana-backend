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
    Only a site's own PREFERRED entrance is used. Anything else - the
    containing building's entrance, a neighbouring tenant's door, a street
    navigation point - is not attributable to the site, so the site keeps its
    stored centroid instead.
    """

    PLACE = 'ChIJbrewery'
    CENTROID = (40.7213069, -73.9574503)

    def _response(self, entrances=None, navigation_points=None, primary=None):
        destination = {'primary': primary or {'location': {
            'latitude': self.CENTROID[0], 'longitude': self.CENTROID[1]}}}
        if entrances is not None:
            destination['entrances'] = entrances
        if navigation_points is not None:
            destination['navigationPoints'] = navigation_points
        return {'destinations': [destination]}

    def _entrance(self, lat, lng, place=None, tags=('PREFERRED',)):
        e = {'location': {'latitude': lat, 'longitude': lng}}
        if tags:
            e['tags'] = list(tags)
        if place:
            e['place'] = f'places/{place}'
        return e

    def test_own_preferred_entrance_is_used(self):
        result = self._response(entrances=[
            self._entrance(40.7215904, -73.9576480, place=self.PLACE)])
        assert extract_entrance(result, self.PLACE, self.CENTROID) == (
            40.7215904, -73.9576480, 'preferred_entrance')

    def test_containing_building_entrance_is_not_used(self):
        """The Brooklyn Brewery case: 73 Wythe Ave contains both the brewery
        and Brooklyn Bowl, so the building's recorded door is not the
        brewery's."""
        result = self._response(entrances=[
            self._entrance(40.7215904, -73.9576480, place='ChIJ73WytheAve')])
        assert extract_entrance(result, self.PLACE, self.CENTROID) is None

    def test_navigation_points_are_never_used(self):
        """Navigation points are street-network points with no owner, and were
        what previously put the brewery at Brooklyn Bowl's door."""
        result = self._response(navigation_points=[
            {'location': {'latitude': 40.7219006, 'longitude': -73.9577703},
             'travelModes': ['WALK']},
            {'location': {'latitude': 40.7219, 'longitude': -73.9577},
             'travelModes': ['DRIVE', 'WALK']},
        ])
        assert extract_entrance(result, self.PLACE, self.CENTROID) is None

    def test_untagged_own_entrance_is_not_used(self):
        result = self._response(entrances=[
            self._entrance(40.7215, -73.9576, place=self.PLACE, tags=None)])
        assert extract_entrance(result, self.PLACE, self.CENTROID) is None

    def test_entrance_without_a_place_is_not_used(self):
        """No place named means no attribution, so it cannot be trusted."""
        result = self._response(entrances=[
            self._entrance(40.7215, -73.9576, place=None)])
        assert extract_entrance(result, self.PLACE, self.CENTROID) is None

    def test_distance_never_disqualifies_an_own_entrance(self):
        """A memorial plaza's own gate can be far from its middle."""
        far = self._entrance(40.7280, -73.9640, place=self.PLACE)
        result = self._response(entrances=[far])
        got = extract_entrance(result, self.PLACE, self.CENTROID)
        assert got is not None and got[2] == 'preferred_entrance'

    def test_multiple_own_preferred_picks_nearest_for_stability(self):
        near = self._entrance(40.7214, -73.9575, place=self.PLACE)
        far = self._entrance(40.7250, -73.9600, place=self.PLACE)
        for entrances in ([far, near], [near, far]):
            got = extract_entrance(self._response(entrances=entrances),
                                   self.PLACE, self.CENTROID)
            assert (round(got[0], 4), round(got[1], 4)) == (40.7214, -73.9575)

    def test_empty_and_missing_responses(self):
        assert extract_entrance({}, self.PLACE, self.CENTROID) is None
        assert extract_entrance({'destinations': []}, self.PLACE, self.CENTROID) is None
        assert extract_entrance(self._response(), self.PLACE, self.CENTROID) is None


class TestStructureType:
    def test_structure_type_read_from_primary(self):
        result = {'destinations': [{'primary': {'structureType': 'GROUNDS'}}]}
        assert extract_structure_type(result) == 'GROUNDS'
        assert extract_structure_type({}) is None
        assert extract_structure_type({'destinations': [{'primary': {}}]}) is None
