"""
Direction segment model for fixed directions between tour sites.
"""
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app import db


class DirectionSegment(db.Model):
    """
    Direction segment for author-created fixed directions between tour sites.

    When a tour has fixed directions enabled, authors can place multiple
    waypoints between consecutive sites. Each waypoint has a GPS trigger
    point that activates when the user enters its radius, playing either
    uploaded audio or TTS of the direction text.
    """

    __tablename__ = 'direction_segments'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent tour
    tour_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tours.id', ondelete='CASCADE'), nullable=False)

    # Transition: from one site to the next
    from_site_id = db.Column(UUID(as_uuid=True), db.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False)
    to_site_id = db.Column(UUID(as_uuid=True), db.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False)

    # Order within the transition (0 = first waypoint after from_site, 1 = second, etc.)
    segment_order = db.Column(db.Integer, nullable=False, default=0)

    # Direction content
    direction_text = db.Column(db.Text, nullable=False)  # Required: used for TTS fallback and accessibility
    audio_url = db.Column(db.String(1024))  # Optional: if set, play this instead of TTS

    # GPS trigger point
    trigger_latitude = db.Column(db.Float, nullable=False)
    trigger_longitude = db.Column(db.Float, nullable=False)
    trigger_radius = db.Column(db.Float, default=21.0, nullable=False)  # Meters, min 15 (VoiceMap default: 21m)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tour = db.relationship('Tour', back_populates='direction_segments')
    from_site = db.relationship('Site', foreign_keys=[from_site_id])
    to_site = db.relationship('Site', foreign_keys=[to_site_id])

    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            'id': str(self.id),
            'tourId': str(self.tour_id),
            'fromSiteId': str(self.from_site_id),
            'toSiteId': str(self.to_site_id),
            'segmentOrder': self.segment_order,
            'directionText': self.direction_text,
            'audioUrl': self.audio_url,
            'triggerLatitude': self.trigger_latitude,
            'triggerLongitude': self.trigger_longitude,
            'triggerRadius': self.trigger_radius,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f'<DirectionSegment {self.from_site_id} -> {self.to_site_id} #{self.segment_order}>'
