"""
Tests for tour metrics calculation service.
"""
import pytest
import math
from app import db
from app.models.tour import Tour, TourSite
from app.models.site import Site
from app.services.tour_calculator import (
    haversine_distance,
    count_words,
    calculate_tour_metrics,
    WALKING_SPEED_METERS_PER_MINUTE,
    NARRATION_WORDS_PER_MINUTE,
    CITY_GRID_ADJUSTMENT
)


class TestHaversineDistance:
    """Test the Haversine distance calculation."""

    def test_same_point(self):
        """Distance between same point should be zero."""
        distance = haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert distance == 0.0

    def test_known_distance(self):
        """Test with known distance between two points."""
        # Distance from New York City Hall to Statue of Liberty
        # Approximately 4.2 km
        lat1, lon1 = 40.7128, -74.0060  # NYC City Hall
        lat2, lon2 = 40.6892, -74.0445  # Statue of Liberty

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be approximately 4200 meters (allowing 10% tolerance)
        assert 3800 < distance < 4600

    def test_short_walking_distance(self):
        """Test a short walking distance (~1.8km)."""
        # Two points roughly 1.8km apart in Manhattan
        lat1, lon1 = 40.7580, -73.9855  # Times Square
        lat2, lon2 = 40.7489, -73.9680  # Grand Central

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be approximately 1800 meters
        assert 1700 < distance < 1900

    def test_cross_hemisphere(self):
        """Test distance calculation across hemispheres."""
        # New York to London (very long distance)
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 51.5074, -0.1278

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # Should be approximately 5,570 km
        assert 5_500_000 < distance < 5_650_000


class TestCountWords:
    """Test word counting function."""

    def test_empty_string(self):
        """Empty string should have 0 words."""
        assert count_words("") == 0

    def test_none_value(self):
        """None should return 0 words."""
        assert count_words(None) == 0

    def test_single_word(self):
        """Single word should count as 1."""
        assert count_words("Hello") == 1

    def test_multiple_words(self):
        """Multiple words separated by spaces."""
        text = "This is a test description with seven words"
        assert count_words(text) == 8

    def test_extra_spaces(self):
        """Text with multiple spaces should count correctly."""
        text = "Hello   world   with   spaces"
        assert count_words(text) == 4

    def test_long_description(self):
        """Test with realistic site description."""
        text = """
        The Empire State Building is a 102-story Art Deco skyscraper in Midtown Manhattan.
        It was designed by Shreve, Lamb & Harmon and completed in 1931.
        The building has a roof height of 1,250 feet and stands a total of 1,454 feet tall.
        """
        # Should have approximately 45 words
        word_count = count_words(text)
        assert 40 < word_count < 50


class TestCalculateTourMetrics:
    """Test tour metrics calculation."""

    def test_empty_tour(self, app, test_user):
        """Tour with no sites should have 0 distance and duration."""
        tour = Tour(
            owner_id=test_user.id,
            name='Empty Tour',
            description='Tour with no sites',
            city='New York',
            status='draft'
        )
        db.session.add(tour)
        db.session.commit()

        distance, duration = calculate_tour_metrics(tour)

        assert distance == 0.0
        assert duration == 0

    def test_single_site(self, app, test_user):
        """Tour with single site should have 0 distance but narration time."""
        tour = Tour(
            owner_id=test_user.id,
            name='Single Site Tour',
            city='New York',
            status='draft'
        )
        db.session.add(tour)
        db.session.flush()

        # Create site with ~100 words (should be ~0.77 min narration = 1 min rounded up)
        description = " ".join(["word"] * 100)
        site = Site(
            title='Test Site',
            description=description,
            latitude=40.7580,
            longitude=-73.9855
        )
        db.session.add(site)
        db.session.flush()

        # Link site to tour
        tour_site = TourSite(tour_id=tour.id, site_id=site.id, display_order=1)
        db.session.add(tour_site)
        db.session.commit()

        distance, duration = calculate_tour_metrics(tour)

        # No distance for single site
        assert distance == 0.0

        # Duration = 100 words / 130 WPM = 0.77 min → rounds up to 1
        assert duration == 1

    def test_two_sites_with_distance(self, app, test_user):
        """Tour with two sites should calculate distance and duration."""
        tour = Tour(
            owner_id=test_user.id,
            name='Two Site Tour',
            city='New York',
            status='draft'
        )
        db.session.add(tour)
        db.session.flush()

        # Site 1: Times Square
        site1 = Site(
            title='Times Square',
            description='A busy tourist area.',  # 5 words
            latitude=40.7580,
            longitude=-73.9855
        )
        db.session.add(site1)
        db.session.flush()

        # Site 2: Grand Central (approximately 1500m from Times Square)
        site2 = Site(
            title='Grand Central',
            description='A historic train station.',  # 4 words
            latitude=40.7489,
            longitude=-73.9680
        )
        db.session.add(site2)
        db.session.flush()

        # Link sites to tour
        tour_site1 = TourSite(tour_id=tour.id, site_id=site1.id, display_order=1)
        tour_site2 = TourSite(tour_id=tour.id, site_id=site2.id, display_order=2)
        db.session.add(tour_site1)
        db.session.add(tour_site2)
        db.session.commit()

        distance, duration = calculate_tour_metrics(tour)

        # Distance should be ~1788m × 1.2 (city grid adjustment) = ~2145m
        assert 2000 < distance < 2300

        # Duration calculation:
        # Walking: 2145m / 73.15 m/min = ~29.3 min
        # Narration: 9 words / 130 WPM = ~0.07 min
        # Total: ~29.37 min → rounds up to 30
        assert duration == 30

    def test_complex_tour(self, app, test_user):
        """Test realistic tour with multiple sites."""
        tour = Tour(
            owner_id=test_user.id,
            name='Chinatown Tour',
            city='New York',
            status='draft'
        )
        db.session.add(tour)
        db.session.flush()

        # Create 4 sites in a rough square pattern
        sites_data = [
            {
                'title': 'Columbus Park',
                'description': ' '.join(['word'] * 80),  # 80 words
                'lat': 40.7150,
                'lon': -73.9978
            },
            {
                'title': 'Museum of Chinese in America',
                'description': ' '.join(['word'] * 120),  # 120 words
                'lat': 40.7189,
                'lon': -73.9980
            },
            {
                'title': 'Mahayana Buddhist Temple',
                'description': ' '.join(['word'] * 100),  # 100 words
                'lat': 40.7136,
                'lon': -73.9968
            },
            {
                'title': 'Kim Lau Square',
                'description': ' '.join(['word'] * 90),  # 90 words
                'lat': 40.7142,
                'lon': -73.9982
            }
        ]

        for order, site_data in enumerate(sites_data, start=1):
            site = Site(
                title=site_data['title'],
                description=site_data['description'],
                latitude=site_data['lat'],
                longitude=site_data['lon']
            )
            db.session.add(site)
            db.session.flush()

            tour_site = TourSite(tour_id=tour.id, site_id=site.id, display_order=order)
            db.session.add(tour_site)

        db.session.commit()

        distance, duration = calculate_tour_metrics(tour)

        # Total words: 80 + 120 + 100 + 90 = 390 words
        # Narration time: 390 / 130 = 3 minutes

        # Distance should be reasonable for 4 sites in Chinatown (roughly 800-1200m adjusted)
        assert 600 < distance < 1500

        # Duration should account for both walking and narration
        # Walking time depends on distance, but should be 10-20 min
        # Plus narration: 3 min
        # Total: roughly 13-23 minutes
        assert 10 < duration < 25

    def test_empty_descriptions(self, app, test_user):
        """Sites with empty descriptions should have 0 narration time."""
        tour = Tour(
            owner_id=test_user.id,
            name='Silent Tour',
            city='New York',
            status='draft'
        )
        db.session.add(tour)
        db.session.flush()

        # Two sites with coordinates but no descriptions
        site1 = Site(
            title='Site 1',
            description=None,
            latitude=40.7580,
            longitude=-73.9855
        )
        site2 = Site(
            title='Site 2',
            description='',
            latitude=40.7489,
            longitude=-73.9680
        )
        db.session.add(site1)
        db.session.add(site2)
        db.session.flush()

        tour_site1 = TourSite(tour_id=tour.id, site_id=site1.id, display_order=1)
        tour_site2 = TourSite(tour_id=tour.id, site_id=site2.id, display_order=2)
        db.session.add(tour_site1)
        db.session.add(tour_site2)
        db.session.commit()

        distance, duration = calculate_tour_metrics(tour)

        # Should have walking distance (~2145m with city grid adjustment)
        assert distance > 2000

        # Duration should be purely walking time (no narration)
        # ~2145m / 73.15 m/min = ~29.3 min → rounds up to 30
        assert duration == 30

    def test_constants_match_ios(self):
        """Verify that constants match iOS implementation."""
        # These values must match Tour.swift:41-42
        assert WALKING_SPEED_METERS_PER_MINUTE == 73.15
        assert NARRATION_WORDS_PER_MINUTE == 130.0
        assert CITY_GRID_ADJUSTMENT == 1.2

    def test_recalculate_after_site_removal(self, app, test_user):
        """Test that metrics are recalculated when a site is removed from a tour."""
        tour = Tour(
            owner_id=test_user.id,
            name='Test Tour',
            city='New York',
            status='draft'
        )
        db.session.add(tour)
        db.session.flush()

        # Create 3 sites
        site1 = Site(
            title='Site 1',
            description=' '.join(['word'] * 100),  # 100 words
            latitude=40.7580,
            longitude=-73.9855
        )
        site2 = Site(
            title='Site 2',
            description=' '.join(['word'] * 100),  # 100 words
            latitude=40.7489,
            longitude=-73.9680
        )
        site3 = Site(
            title='Site 3',
            description=' '.join(['word'] * 100),  # 100 words
            latitude=40.7410,
            longitude=-73.9900
        )
        db.session.add_all([site1, site2, site3])
        db.session.flush()

        # Link all 3 sites to tour
        tour_site1 = TourSite(tour_id=tour.id, site_id=site1.id, display_order=1)
        tour_site2 = TourSite(tour_id=tour.id, site_id=site2.id, display_order=2)
        tour_site3 = TourSite(tour_id=tour.id, site_id=site3.id, display_order=3)
        db.session.add_all([tour_site1, tour_site2, tour_site3])
        db.session.commit()

        # Calculate initial metrics
        initial_distance, initial_duration = calculate_tour_metrics(tour)

        # Initial metrics should account for 3 sites, 300 words
        assert initial_distance > 0
        assert initial_duration > 0

        # Now simulate removing site2 (the middle site)
        # This is what the API does: delete all tour_sites and recreate with new list
        TourSite.query.filter_by(tour_id=tour.id).delete()

        # Recreate with only site1 and site3
        new_tour_site1 = TourSite(tour_id=tour.id, site_id=site1.id, display_order=1)
        new_tour_site3 = TourSite(tour_id=tour.id, site_id=site3.id, display_order=2)
        db.session.add_all([new_tour_site1, new_tour_site3])
        db.session.flush()

        # THIS IS THE KEY: We need to properly refresh the relationship
        db.session.expire(tour, ['tour_sites'])
        db.session.refresh(tour)

        # Calculate new metrics
        new_distance, new_duration = calculate_tour_metrics(tour)

        # New metrics should be different (only 2 sites, 200 words)
        # Distance should be less (only 1 segment instead of 2)
        # Duration should be less (200 words instead of 300, plus different distance)
        assert new_distance < initial_distance
        assert new_duration < initial_duration

        # Verify we're calculating for exactly 2 sites
        tour_sites = sorted(tour.tour_sites, key=lambda ts: ts.display_order)
        assert len(tour_sites) == 2
        assert tour_sites[0].site_id == site1.id
        assert tour_sites[1].site_id == site3.id
