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
from app.services.entrance_service import extract_entrance


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
    def _response(self, primary):
        return {'destinations': [{'primary': primary}]}

    def test_preferred_entrance_wins(self):
        result = self._response({
            'entrances': [
                {'location': {'latitude': 1.0, 'longitude': 2.0}},
                {'location': {'latitude': 3.0, 'longitude': 4.0},
                 'tags': ['PREFERRED']},
            ],
            'navigationPoints': [
                {'location': {'latitude': 9.0, 'longitude': 9.0},
                 'travelModes': ['WALK']},
            ],
        })
        assert extract_entrance(result) == (3.0, 4.0, 'preferred_entrance')

    def test_sole_untagged_entrance_used(self):
        result = self._response({
            'entrances': [{'location': {'latitude': 1.0, 'longitude': 2.0}}],
        })
        assert extract_entrance(result) == (1.0, 2.0, 'sole_entrance')

    def test_multiple_untagged_entrances_fall_through_to_walk_point(self):
        result = self._response({
            'entrances': [
                {'location': {'latitude': 1.0, 'longitude': 2.0}},
                {'location': {'latitude': 3.0, 'longitude': 4.0}},
            ],
            'navigationPoints': [
                {'location': {'latitude': 5.0, 'longitude': 6.0},
                 'travelModes': ['DRIVE']},
                {'location': {'latitude': 7.0, 'longitude': 8.0},
                 'travelModes': ['DRIVE', 'WALK']},
            ],
        })
        assert extract_entrance(result) == (7.0, 8.0, 'walk_navigation_point')

    def test_nothing_useful_returns_none(self):
        assert extract_entrance({}) is None
        assert extract_entrance({'destinations': []}) is None
        assert extract_entrance(self._response({})) is None
        assert extract_entrance(self._response({
            'navigationPoints': [
                {'location': {'latitude': 5.0, 'longitude': 6.0},
                 'travelModes': ['DRIVE']},
            ],
        })) is None
