"""
Tour models.
"""
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app import db


class Tour(db.Model):
    """Tour model."""

    __tablename__ = 'tours'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Ownership
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Core fields
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Location context (for discovery)
    city = db.Column(db.String(100))
    neighborhood = db.Column(db.String(100))

    # Tour center point (for proximity queries)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # Media
    image_url = db.Column(db.String(1024))
    audio_url = db.Column(db.String(1024))
    map_image_url = db.Column(db.String(1024))
    music_urls = db.Column(ARRAY(db.String(1024)))  # Background music tracks

    # Metadata
    duration_minutes = db.Column(db.Integer)
    distance_meters = db.Column(db.Float)

    # Ratings (aggregated from user feedback)
    average_rating = db.Column(db.Float)
    rating_count = db.Column(db.Integer, default=0)

    # Status
    status = db.Column(db.String(20), default='draft', nullable=False)  # 'draft', 'ready', 'published', 'archived'

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = db.Column(db.DateTime)

    # Relationships
    owner = db.relationship('User', back_populates='tours')
    tour_sites = db.relationship('TourSite', back_populates='tour', lazy=True, cascade='all, delete-orphan', order_by='TourSite.display_order')

    def get_calculated_rating(self):
        """Calculate average rating from all sites in the tour."""
        if not self.tour_sites:
            return None

        site_ratings = [ts.site.rating for ts in self.tour_sites if ts.site.rating is not None]
        if not site_ratings:
            return None

        return sum(site_ratings) / len(site_ratings)

    def to_dict(self, include_sites=True):
        """Convert to dictionary."""
        result = {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'city': self.city,
            'neighborhood': self.neighborhood,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'imageUrl': self.image_url,
            'audioUrl': self.audio_url,
            'mapImageUrl': self.map_image_url,
            'musicUrls': self.music_urls,
            'durationMinutes': self.duration_minutes,
            'distanceMeters': self.distance_meters,
            'averageRating': self.average_rating,
            'ratingCount': self.rating_count,
            'calculatedRating': self.get_calculated_rating(),
            'status': self.status,
            'ownerId': self.owner_id,
            'ownerName': self.owner.name if self.owner else None,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
            'publishedAt': self.published_at.isoformat() if self.published_at else None,
            'siteCount': len(self.tour_sites),
        }

        # Include neighborhood description if available
        if self.city and self.neighborhood:
            from app.models.neighborhood import NeighborhoodDescription
            neighborhood_desc = NeighborhoodDescription.query.filter_by(
                city=self.city,
                neighborhood=self.neighborhood
            ).first()
            if neighborhood_desc:
                result['neighborhoodDescription'] = neighborhood_desc.description
            else:
                result['neighborhoodDescription'] = None
        else:
            result['neighborhoodDescription'] = None

        if include_sites:
            result['sites'] = [ts.site.to_dict() for ts in self.tour_sites]
            result['siteIds'] = [str(ts.site_id) for ts in self.tour_sites]

        return result

    def __repr__(self):
        return f'<Tour {self.name}>'


class TourSite(db.Model):
    """Association table for tours and sites (many-to-many relationship)."""

    __tablename__ = 'tour_sites'

    tour_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tours.id', ondelete='CASCADE'), primary_key=True)
    site_id = db.Column(UUID(as_uuid=True), db.ForeignKey('sites.id', ondelete='CASCADE'), primary_key=True)
    display_order = db.Column(db.Integer, nullable=False)
    visit_duration_minutes = db.Column(db.Integer)

    # Relationships
    tour = db.relationship('Tour', back_populates='tour_sites')
    site = db.relationship('Site', back_populates='tour_sites')

    def __repr__(self):
        return f'<TourSite tour={self.tour_id} site={self.site_id} order={self.display_order}>'
