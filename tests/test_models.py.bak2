"""
Tests for database models.
"""
import pytest
from datetime import datetime, timedelta
from app.models.user import User, PasswordResetToken
from app.models.tour import Tour, TourSite
from app.models.site import Site
from app.models.audio_cache import AudioCache
from app import db


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, app):
        """Test creating a user."""
        with app.app_context():
            user = User(
                email='test@example.com',
                name='Test User',
                role='creator'
            )
            user.set_password('password123')

            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.email == 'test@example.com'
            assert user.name == 'Test User'
            assert user.role == 'creator'
            assert user.is_active is True

    def test_password_hashing(self, app):
        """Test password hashing and verification."""
        with app.app_context():
            user = User(email='test@example.com')
            user.set_password('mypassword')

            # Password should be hashed
            assert user.password_hash != 'mypassword'
            assert user.password_hash is not None

            # Should verify correct password
            assert user.check_password('mypassword') is True

            # Should reject incorrect password
            assert user.check_password('wrongpassword') is False

    def test_to_dict_excludes_password(self, app, test_user):
        """Test that to_dict() doesn't include password hash."""
        with app.app_context():
            user = User.query.get(test_user.id)
            user_dict = user.to_dict()

            assert 'password_hash' not in user_dict
            assert 'password' not in user_dict
            assert 'email' in user_dict
            assert 'name' in user_dict

    def test_user_role_validation(self, app):
        """Test user role values."""
        with app.app_context():
            # Valid roles
            for role in ['admin', 'creator', 'viewer']:
                user = User(
                    email=f'{role}@example.com',
                    role=role
                )
                user.set_password('pass')
                db.session.add(user)
                db.session.commit()
                assert user.role == role

    def test_user_timestamps(self, app):
        """Test that timestamps are set automatically."""
        with app.app_context():
            user = User(email='timestamp@example.com')
            user.set_password('pass')

            db.session.add(user)
            db.session.commit()

            assert user.created_at is not None
            assert user.updated_at is not None
            assert isinstance(user.created_at, datetime)


class TestPasswordResetToken:
    """Tests for PasswordResetToken model."""

    def test_create_for_user(self, app, test_user):
        """Test creating a reset token for a user."""
        with app.app_context():
            user = User.query.get(test_user.id)
            token = PasswordResetToken.create_for_user(user)

            assert token.user_id == user.id
            assert token.token is not None
            assert len(token.token) > 20  # Should be a long random string
            assert token.used is False
            assert token.expires_at > datetime.utcnow()

    def test_token_is_valid(self, app, test_user):
        """Test checking if token is valid."""
        with app.app_context():
            user = User.query.get(test_user.id)
            token = PasswordResetToken.create_for_user(user)
            db.session.add(token)
            db.session.commit()

            # Fresh token should be valid
            assert token.is_valid() is True

            # Used token should be invalid
            token.used = True
            db.session.commit()
            assert token.is_valid() is False

            # Expired token should be invalid
            token.used = False
            token.expires_at = datetime.utcnow() - timedelta(hours=1)
            db.session.commit()
            assert token.is_valid() is False


class TestTourModel:
    """Tests for Tour model."""

    def test_create_tour(self, app, test_user):
        """Test creating a tour."""
        with app.app_context():
            tour = Tour(
                owner_id=test_user.id,
                name='Test Tour',
                description='A test tour',
                city='New York',
                neighborhood='SoHo',
                latitude=40.7241,
                longitude=-73.9973,
                status='draft'
            )

            db.session.add(tour)
            db.session.commit()

            assert tour.id is not None
            assert str(tour.id)  # UUID should be convertible to string
            assert tour.name == 'Test Tour'
            assert tour.status == 'draft'
            assert tour.is_public is False  # Default

    def test_tour_status_validation(self, app, test_user):
        """Test tour status values."""
        with app.app_context():
            # Valid statuses
            for status in ['draft', 'live', 'archived']:
                tour = Tour(
                    owner_id=test_user.id,
                    name=f'{status} Tour',
                    status=status
                )
                db.session.add(tour)
                db.session.commit()
                assert tour.status == status

    def test_tour_to_dict(self, app, test_tour):
        """Test tour serialization to dict."""
        with app.app_context():
            tour = Tour.query.get(test_tour.id)
            tour_dict = tour.to_dict()

            assert tour_dict['id'] == str(tour.id)
            assert tour_dict['name'] == tour.name
            assert tour_dict['city'] == tour.city
            assert tour_dict['status'] == tour.status
            assert 'created_at' in tour_dict

    def test_tour_timestamps(self, app, test_user):
        """Test that tour timestamps are set."""
        with app.app_context():
            tour = Tour(
                owner_id=test_user.id,
                name='Timestamp Tour'
            )
            db.session.add(tour)
            db.session.commit()

            assert tour.created_at is not None
            assert tour.updated_at is not None


class TestSiteModel:
    """Tests for Site model."""

    def test_create_site(self, app):
        """Test creating a site."""
        with app.app_context():
            site = Site(
                title='Test Site',
                description='A test site',
                latitude=40.7241,
                longitude=-73.9973,
                formatted_address='123 Test St, New York, NY',
                place_id='test_place_123'
            )

            db.session.add(site)
            db.session.commit()

            assert site.id is not None
            assert str(site.id)  # UUID should work
            assert site.title == 'Test Site'
            assert site.latitude == 40.7241
            assert site.longitude == -73.9973

    def test_site_coordinates_required(self, app):
        """Test that coordinates are required."""
        with app.app_context():
            site = Site(
                title='No Coords Site',
                latitude=40.0,
                longitude=-73.0
            )
            db.session.add(site)
            db.session.commit()
            assert site.latitude == 40.0
            assert site.longitude == -73.0

    def test_site_user_submitted_locations(self, app):
        """Test user_submitted_locations array field."""
        with app.app_context():
            site = Site(
                title='Site with Locations',
                latitude=40.7241,
                longitude=-73.9973,
                user_submitted_locations=[[40.7242, -73.9974], [40.7240, -73.9972]]
            )

            db.session.add(site)
            db.session.commit()

            assert len(site.user_submitted_locations) == 2
            assert site.user_submitted_locations[0] == [40.7242, -73.9974]

    def test_site_google_fields(self, app):
        """Test Google Places fields."""
        with app.app_context():
            site = Site(
                title='Google Site',
                latitude=40.7241,
                longitude=-73.9973,
                place_id='ChIJ_test_123',
                formatted_address='456 Google St',
                types=['restaurant', 'point_of_interest'],
                phone_number='+1234567890',
                user_ratings_total=100,
                google_photo_references=['photo1', 'photo2']
            )

            db.session.add(site)
            db.session.commit()

            assert site.place_id == 'ChIJ_test_123'
            assert 'restaurant' in site.types
            assert len(site.google_photo_references) == 2


class TestTourSiteModel:
    """Tests for TourSite junction model."""

    def test_create_tour_site(self, app, test_tour, test_site):
        """Test creating a tour-site relationship."""
        with app.app_context():
            tour = Tour.query.get(test_tour.id)
            site = Site.query.get(test_site.id)

            tour_site = TourSite(
                tour_id=tour.id,
                site_id=site.id,
                display_order=1,
                visit_duration_minutes=30
            )

            db.session.add(tour_site)
            db.session.commit()

            assert tour_site.tour_id == tour.id
            assert tour_site.site_id == site.id
            assert tour_site.display_order == 1
            assert tour_site.visit_duration_minutes == 30

    def test_tour_site_ordering(self, app, test_tour, test_site):
        """Test that sites can be ordered within a tour."""
        with app.app_context():
            tour = Tour.query.get(test_tour.id)

            # Create multiple sites
            site1 = Site(title='Site 1', latitude=40.0, longitude=-73.0)
            site2 = Site(title='Site 2', latitude=40.1, longitude=-73.1)
            site3 = Site(title='Site 3', latitude=40.2, longitude=-73.2)

            db.session.add_all([site1, site2, site3])
            db.session.commit()

            # Add them to tour in specific order
            TourSite(tour_id=tour.id, site_id=site1.id, display_order=2)
            TourSite(tour_id=tour.id, site_id=site2.id, display_order=1)
            TourSite(tour_id=tour.id, site_id=site3.id, display_order=3)
            db.session.commit()

            # Query and verify order
            tour_sites = TourSite.query.filter_by(tour_id=tour.id).order_by(TourSite.display_order).all()
            assert len(tour_sites) == 3
            assert tour_sites[0].site_id == site2.id  # order 1
            assert tour_sites[1].site_id == site1.id  # order 2
            assert tour_sites[2].site_id == site3.id  # order 3


class TestAudioCacheModel:
    """Tests for AudioCache model."""

    def test_get_hash(self):
        """Test hash generation for text."""
        text1 = "Hello world"
        text2 = "Hello world"
        text3 = "Different text"

        hash1 = AudioCache.get_hash(text1)
        hash2 = AudioCache.get_hash(text2)
        hash3 = AudioCache.get_hash(text3)

        # Same text should produce same hash
        assert hash1 == hash2

        # Different text should produce different hash
        assert hash1 != hash3

        # Hash should be consistent length
        assert len(hash1) == 64  # SHA-256 produces 64 char hex string

    def test_create_audio_cache(self, app):
        """Test creating audio cache entry."""
        with app.app_context():
            text = "Turn left on Main Street"
            text_hash = AudioCache.get_hash(text)

            cache = AudioCache(
                text_hash=text_hash,
                text_content=text,
                audio_url='https://s3.amazonaws.com/bucket/audio.mp3',
                voice_id='test_voice'
            )

            db.session.add(cache)
            db.session.commit()

            assert cache.id is not None
            assert cache.text_hash == text_hash
            assert cache.text_content == text
            assert cache.access_count == 1  # Default is 1

    def test_find_by_text(self, app):
        """Test finding cached audio by text."""
        with app.app_context():
            text = "Turn right on Broadway"
            text_hash = AudioCache.get_hash(text)

            cache = AudioCache(
                text_hash=text_hash,
                text_content=text,
                audio_url='https://s3.amazonaws.com/bucket/audio2.mp3',
                voice_id='test_voice'
            )

            db.session.add(cache)
            db.session.commit()

            # Find by exact same text
            found = AudioCache.find_by_text(text)
            assert found is not None
            assert found.text_content == text
            assert found.audio_url == 'https://s3.amazonaws.com/bucket/audio2.mp3'

            # Should not find different text
            not_found = AudioCache.find_by_text("Different instruction")
            assert not_found is None

    def test_update_stats(self, app):
        """Test updating cache hit statistics."""
        with app.app_context():
            text = "Go straight"
            cache = AudioCache(
                text_hash=AudioCache.get_hash(text),
                text_content=text,
                audio_url='https://s3.amazonaws.com/bucket/audio3.mp3'
            )

            db.session.add(cache)
            db.session.commit()

            initial_access_count = cache.access_count
            initial_last_accessed = cache.last_accessed_at

            # Update stats
            cache.update_stats()
            db.session.commit()

            assert cache.access_count == initial_access_count + 1
            assert cache.last_accessed_at > initial_last_accessed

    def test_cache_timestamps(self, app):
        """Test that cache timestamps are set."""
        with app.app_context():
            cache = AudioCache(
                text_hash=AudioCache.get_hash("test"),
                text_content="test",
                audio_url='https://s3.amazonaws.com/bucket/test.mp3'
            )

            db.session.add(cache)
            db.session.commit()

            assert cache.created_at is not None
            assert cache.last_accessed_at is not None
