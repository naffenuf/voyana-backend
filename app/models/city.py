"""
City model for storing city-specific metadata and hero images.
"""
from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid


class City(db.Model):
    """
    Represents a city with tours. Stores hero image and metadata.

    Coordinates are used to disambiguate cities with the same name
    (e.g., Paris, France vs Paris, Texas).
    """
    __tablename__ = 'cities'

    id = db.Column(db.Integer, primary_key=True)

    # City identification
    name = db.Column(db.String(100), nullable=False, index=True)

    # Location (center point for proximity matching)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    # Hero image for explore screen
    hero_image_url = db.Column(db.String(1024))
    hero_title = db.Column(db.String(200))
    hero_subtitle = db.Column(db.String(200))

    # Display metadata
    country = db.Column(db.String(100))
    state_province = db.Column(db.String(100))
    timezone = db.Column(db.String(50))

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # Unique constraint: same city name can exist in different locations
    __table_args__ = (
        db.Index('idx_city_location', 'name', 'latitude', 'longitude'),
        db.UniqueConstraint('name', 'latitude', 'longitude', name='uq_city_location'),
    )

    def to_dict(self):
        """Convert city to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'heroImageUrl': self.hero_image_url,
            'heroTitle': self.hero_title,
            'heroSubtitle': self.hero_subtitle,
            'country': self.country,
            'stateProvince': self.state_province,
            'timezone': self.timezone,
            'isActive': self.is_active,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<City {self.name} ({self.latitude}, {self.longitude})>'
