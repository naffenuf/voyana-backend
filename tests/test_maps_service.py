"""
Tests for Maps service (route optimization).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.maps_service import optimize_route


class TestOptimizeRoute:
    """Tests for optimize_route function."""

    @patch('app.services.maps_service.get_maps_client')
    def test_basic_route_generation(self, mock_get_client, app):
        """Test basic route generation with origin and destination."""
        with app.app_context():
            # Mock Google Maps client
            mock_client = Mock()
            mock_directions_result = [{
                'legs': [{
                    'distance': {'value': 1000},
                    'duration': {'value': 600},
                    'steps': [{
                        'start_location': {'lat': 40.7589, 'lng': -73.9851},
                        'end_location': {'lat': 40.7614, 'lng': -73.9776},
                        'distance': {'value': 500},
                        'duration': {'value': 300},
                        'html_instructions': 'Turn left on Broadway',
                        'polyline': {'points': 'encoded_polyline_1'}
                    }]
                }],
                'overview_polyline': {'points': 'overview_encoded'},
                'waypoint_order': []
            }]
            mock_client.directions.return_value = mock_directions_result
            mock_get_client.return_value = mock_client

            origin = (40.7589, -73.9851)
            destination = (40.7614, -73.9776)

            result = optimize_route(origin, destination, waypoints=[])

            # Verify API was called
            mock_client.directions.assert_called_once()

            # Verify result structure
            assert 'overviewPolyline' in result
            assert 'totalDistanceMeters' in result
            assert 'totalDurationSeconds' in result
            assert result['totalDistanceMeters'] == 1000
            assert result['totalDurationSeconds'] == 600

    @patch('app.services.maps_service.get_maps_client')
    def test_route_with_waypoints(self, mock_get_client, app):
        """Test route generation with waypoints."""
        with app.app_context():
            mock_client = Mock()
            mock_directions_result = [{
                'legs': [
                    {'distance': {'value': 500}, 'duration': {'value': 300}, 'steps': []},
                    {'distance': {'value': 700}, 'duration': {'value': 400}, 'steps': []}
                ],
                'overview_polyline': {'points': 'overview'},
                'waypoint_order': [0, 1]
            }]
            mock_client.directions.return_value = mock_directions_result
            mock_get_client.return_value = mock_client

            origin = (40.7589, -73.9851)
            destination = (40.7614, -73.9776)
            waypoints = [
                {'latitude': 40.7600, 'longitude': -73.9800},
                {'latitude': 40.7605, 'longitude': -73.9790}
            ]

            result = optimize_route(origin, destination, waypoints)

            # Should call with waypoints
            call_args = mock_client.directions.call_args[1]
            assert call_args['waypoints'] is not None
            assert len(call_args['waypoints']) == 2

            # Verify total distance and duration are summed
            assert result['totalDistanceMeters'] == 1200  # 500 + 700
            assert result['totalDurationSeconds'] == 700  # 300 + 400

    @patch('app.services.maps_service.get_maps_client')
    def test_waypoint_optimization(self, mock_get_client, app):
        """Test that waypoint optimization can be enabled."""
        with app.app_context():
            mock_client = Mock()
            mock_directions_result = [{
                'legs': [{'distance': {'value': 1000}, 'duration': {'value': 600}, 'steps': []}],
                'overview_polyline': {'points': 'overview'},
                'waypoint_order': [1, 0]  # Optimized order
            }]
            mock_client.directions.return_value = mock_directions_result
            mock_get_client.return_value = mock_client

            origin = (40.7589, -73.9851)
            destination = (40.7614, -73.9776)
            waypoints = [
                {'latitude': 40.7600, 'longitude': -73.9800},
                {'latitude': 40.7605, 'longitude': -73.9790}
            ]

            result = optimize_route(origin, destination, waypoints, optimize=True)

            # Should call with optimize_waypoints=True
            call_args = mock_client.directions.call_args[1]
            assert call_args['optimize_waypoints'] is True

            # Should return optimized order
            assert result['waypointOrder'] == [1, 0]

    @patch('app.services.maps_service.get_maps_client')
    def test_different_travel_modes(self, mock_get_client, app):
        """Test different travel modes (walking, driving, etc.)."""
        with app.app_context():
            mock_client = Mock()
            mock_directions_result = [{
                'legs': [{'distance': {'value': 1000}, 'duration': {'value': 600}, 'steps': []}],
                'overview_polyline': {'points': 'overview'},
                'waypoint_order': []
            }]
            mock_client.directions.return_value = mock_directions_result
            mock_get_client.return_value = mock_client

            origin = (40.7589, -73.9851)
            destination = (40.7614, -73.9776)

            # Test walking mode
            optimize_route(origin, destination, [], mode='walking')
            call_args = mock_client.directions.call_args[1]
            assert call_args['mode'] == 'walking'

            # Test driving mode
            optimize_route(origin, destination, [], mode='driving')
            call_args = mock_client.directions.call_args[1]
            assert call_args['mode'] == 'driving'

    @patch('app.services.maps_service.get_maps_client')
    def test_leg_polylines_extraction(self, mock_get_client, app):
        """Test extraction of polylines for each leg."""
        with app.app_context():
            mock_client = Mock()
            mock_directions_result = [{
                'legs': [
                    {
                        'distance': {'value': 500},
                        'duration': {'value': 300},
                        'steps': [
                            {'polyline': {'points': 'poly1'}},
                            {'polyline': {'points': 'poly2'}}
                        ]
                    },
                    {
                        'distance': {'value': 700},
                        'duration': {'value': 400},
                        'steps': [
                            {'polyline': {'points': 'poly3'}}
                        ]
                    }
                ],
                'overview_polyline': {'points': 'overview'},
                'waypoint_order': []
            }]
            mock_client.directions.return_value = mock_directions_result
            mock_get_client.return_value = mock_client

            result = optimize_route((40.0, -73.0), (40.1, -73.1), [])

            # Should have polylines for each leg
            assert 'legPolylines' in result
            assert len(result['legPolylines']) == 2
            assert result['legPolylines'][0] == 'poly1poly2'
            assert result['legPolylines'][1] == 'poly3'

    @patch('app.services.maps_service.get_maps_client')
    def test_steps_with_leg_index(self, mock_get_client, app):
        """Test that steps include leg index."""
        with app.app_context():
            mock_client = Mock()
            mock_directions_result = [{
                'legs': [
                    {
                        'distance': {'value': 500},
                        'duration': {'value': 300},
                        'steps': [{
                            'start_location': {'lat': 40.0, 'lng': -73.0},
                            'end_location': {'lat': 40.1, 'lng': -73.1},
                            'distance': {'value': 500},
                            'duration': {'value': 300},
                            'html_instructions': 'Go straight',
                            'polyline': {'points': 'poly'}
                        }]
                    },
                    {
                        'distance': {'value': 700},
                        'duration': {'value': 400},
                        'steps': [{
                            'start_location': {'lat': 40.1, 'lng': -73.1},
                            'end_location': {'lat': 40.2, 'lng': -73.2},
                            'distance': {'value': 700},
                            'duration': {'value': 400},
                            'html_instructions': 'Turn right',
                            'polyline': {'points': 'poly2'}
                        }]
                    }
                ],
                'overview_polyline': {'points': 'overview'},
                'waypoint_order': []
            }]
            mock_client.directions.return_value = mock_directions_result
            mock_get_client.return_value = mock_client

            result = optimize_route((40.0, -73.0), (40.2, -73.2), [])

            # Should have steps from all legs
            assert 'steps' in result
            assert len(result['steps']) == 2

            # First step should be from leg 0
            assert result['steps'][0]['legIndex'] == 0
            assert result['steps'][0]['instructions'] == 'Go straight'

            # Second step should be from leg 1
            assert result['steps'][1]['legIndex'] == 1
            assert result['steps'][1]['instructions'] == 'Turn right'

    @patch('app.services.maps_service.get_maps_client')
    def test_empty_waypoints(self, mock_get_client, app):
        """Test route with empty waypoints list."""
        with app.app_context():
            mock_client = Mock()
            mock_directions_result = [{
                'legs': [{'distance': {'value': 1000}, 'duration': {'value': 600}, 'steps': []}],
                'overview_polyline': {'points': 'overview'},
                'waypoint_order': []
            }]
            mock_client.directions.return_value = mock_directions_result
            mock_get_client.return_value = mock_client

            result = optimize_route((40.0, -73.0), (40.1, -73.1), [])

            # Should call with waypoints=None
            call_args = mock_client.directions.call_args[1]
            assert call_args['waypoints'] is None

    @patch('app.services.maps_service.get_maps_client')
    def test_no_route_found(self, mock_get_client, app):
        """Test handling when no route is found."""
        with app.app_context():
            mock_client = Mock()
            mock_client.directions.return_value = []  # Empty result
            mock_get_client.return_value = mock_client

            result = optimize_route((40.0, -73.0), (40.1, -73.1), [])

            assert result['status'] == 'error'
            assert 'message' in result

    @patch('app.services.maps_service.get_maps_client')
    def test_api_exception_handling(self, mock_get_client, app):
        """Test handling of Google Maps API exceptions."""
        with app.app_context():
            mock_client = Mock()
            mock_client.directions.side_effect = Exception('API Error')
            mock_get_client.return_value = mock_client

            result = optimize_route((40.0, -73.0), (40.1, -73.1), [])

            assert result['status'] == 'error'
            assert 'message' in result
            assert 'error' in result['message'].lower()

    def test_missing_api_key(self, app):
        """Test handling of missing Google Maps API key."""
        with app.app_context():
            # Temporarily remove API key
            original_key = app.config.get('GOOGLE_API_KEY')
            app.config['GOOGLE_API_KEY'] = None

            result = optimize_route((40.0, -73.0), (40.1, -73.1), [])

            assert result['status'] == 'error'
            assert 'message' in result

            # Restore
            app.config['GOOGLE_API_KEY'] = original_key

    @patch('app.services.maps_service.get_maps_client')
    def test_overview_polyline_extraction(self, mock_get_client, app):
        """Test extraction of overview polyline."""
        with app.app_context():
            mock_client = Mock()
            mock_directions_result = [{
                'legs': [{'distance': {'value': 1000}, 'duration': {'value': 600}, 'steps': []}],
                'overview_polyline': {'points': 'OVERVIEW_ENCODED_POLYLINE'},
                'waypoint_order': []
            }]
            mock_client.directions.return_value = mock_directions_result
            mock_get_client.return_value = mock_client

            result = optimize_route((40.0, -73.0), (40.1, -73.1), [])

            assert result['overviewPolyline'] == 'OVERVIEW_ENCODED_POLYLINE'
