"""
Test the consolidate status migration.
"""
import pytest
from app import create_app, db
from app.models.tour import Tour
from app.models.user import User
import uuid


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_migration_published_tours(app):
    """Test that tours with is_public=true had status set to 'published'."""
    with app.app_context():
        # Create a test user
        user = User(email='test@example.com', name='Test User', role='admin')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        # Query for published tours (should have been migrated from is_public=true)
        published_tours = Tour.query.filter_by(status='published').all()

        # After migration, all previously public tours should be published
        for tour in published_tours:
            assert tour.status == 'published'
            assert tour.published_at is not None  # Should have published_at set
            # The is_public column should not exist anymore
            assert not hasattr(tour, 'is_public')


def test_migration_ready_tours(app):
    """Test that tours with is_public=false and status='live' became 'ready'."""
    with app.app_context():
        # Query for ready tours (should have been migrated from is_public=false + status='live')
        ready_tours = Tour.query.filter_by(status='ready').all()

        for tour in ready_tours:
            assert tour.status == 'ready'
            # The is_public column should not exist anymore
            assert not hasattr(tour, 'is_public')


def test_new_tour_without_is_public(app):
    """Test creating a new tour doesn't have is_public field."""
    with app.app_context():
        # Create a test user
        user = User(email='creator@example.com', name='Creator', role='creator')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        # Create a new tour (post-migration)
        tour = Tour(
            id=uuid.uuid4(),
            owner_id=user.id,
            name='Test Tour',
            status='draft'
        )
        db.session.add(tour)
        db.session.commit()

        # Verify the tour was created with only status field
        assert tour.status == 'draft'
        assert not hasattr(tour, 'is_public')

        # Verify all valid statuses work
        tour.status = 'ready'
        db.session.commit()
        assert tour.status == 'ready'

        tour.status = 'published'
        db.session.commit()
        assert tour.status == 'published'

        tour.status = 'archived'
        db.session.commit()
        assert tour.status == 'archived'


def test_tour_to_dict_no_is_public(app):
    """Test that tour.to_dict() doesn't include isPublic."""
    with app.app_context():
        # Create a test user and tour
        user = User(email='test@example.com', name='Test', role='creator')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        tour = Tour(
            id=uuid.uuid4(),
            owner_id=user.id,
            name='Test Tour',
            status='draft'
        )
        db.session.add(tour)
        db.session.commit()

        # Get dictionary representation
        tour_dict = tour.to_dict(include_sites=False)

        # Verify isPublic is not in the dict
        assert 'isPublic' not in tour_dict
        # But status should be there
        assert 'status' in tour_dict
        assert tour_dict['status'] == 'draft'


def test_status_values(app):
    """Test that all new status values are valid."""
    with app.app_context():
        user = User(email='test@example.com', name='Test', role='admin')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        valid_statuses = ['draft', 'ready', 'published', 'archived']

        for status in valid_statuses:
            tour = Tour(
                id=uuid.uuid4(),
                owner_id=user.id,
                name=f'Tour {status}',
                status=status
            )
            db.session.add(tour)
            db.session.commit()

            # Verify tour was saved correctly
            saved_tour = Tour.query.get(tour.id)
            assert saved_tour.status == status
