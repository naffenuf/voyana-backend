"""
Default music track models.
"""
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app import db


class DefaultMusicTrack(db.Model):
    """Default music track model for fallback when tours have no music."""

    __tablename__ = 'default_music_tracks'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Music track details
    url = db.Column(db.String(1024), nullable=False)
    title = db.Column(db.String(200))
    display_order = db.Column(db.Integer, nullable=False)

    # Metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'url': self.url,
            'title': self.title,
            'displayOrder': self.display_order,
            'isActive': self.is_active,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f'<DefaultMusicTrack {self.title or self.url}>'
