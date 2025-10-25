"""
Site model.
"""
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app import db


class Site(db.Model):
    """Site (location/point of interest) model."""

    __tablename__ = 'sites'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core fields
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Location (required)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    # User-submitted optimal viewing locations
    # Array of arrays: [[lat1, lng1], [lat2, lng2], ...]
    user_submitted_locations = db.Column(ARRAY(db.Float, dimensions=2))

    # Media
    image_url = db.Column(db.String(1024))
    audio_url = db.Column(db.String(1024))
    web_url = db.Column(db.String(1024))

    # Discovery
    keywords = db.Column(ARRAY(db.String(50)))
    rating = db.Column(db.Float)

    # Location context
    city = db.Column(db.String(100))
    neighborhood = db.Column(db.String(100))

    # Google Places integration
    place_id = db.Column(db.String(255), index=True)
    formatted_address = db.Column(db.Text)
    types = db.Column(ARRAY(db.String(50)))
    user_ratings_total = db.Column(db.Integer)
    phone_number = db.Column(db.Text)

    # Google Places photos
    google_photo_references = db.Column(ARRAY(db.String(1024)))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tour_sites = db.relationship('TourSite', back_populates='site', lazy=True, cascade='all, delete-orphan')

    def add_user_location(self, lat, lng):
        """Add a user-submitted location to the array."""
        if self.user_submitted_locations is None:
            self.user_submitted_locations = []
        self.user_submitted_locations = self.user_submitted_locations + [[lat, lng]]

    def get_average_location(self):
        """Calculate average of all user-submitted locations."""
        if not self.user_submitted_locations or len(self.user_submitted_locations) == 0:
            return (self.latitude, self.longitude)

        avg_lat = sum(loc[0] for loc in self.user_submitted_locations) / len(self.user_submitted_locations)
        avg_lng = sum(loc[1] for loc in self.user_submitted_locations) / len(self.user_submitted_locations)
        return (avg_lat, avg_lng)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'imageUrl': self.image_url,
            'audioUrl': self.audio_url,
            'webUrl': self.web_url,
            'keywords': self.keywords or [],
            'rating': self.rating,
            'city': self.city,
            'neighborhood': self.neighborhood,
            'placeId': self.place_id,
            'formatted_address': self.formatted_address,  # snake_case for iOS decoder
            'types': self.types or [],
            'user_ratings_total': self.user_ratings_total,  # snake_case for iOS decoder
            'phone_number': self.phone_number,  # snake_case for iOS decoder
            'googlePhotoReferences': self.google_photo_references or [],
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f'<Site {self.title}>'
