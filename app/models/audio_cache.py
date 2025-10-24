"""
Audio cache model.
"""
import uuid
import hashlib
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app import db


class AudioCache(db.Model):
    """Model for caching text-to-audio mappings."""

    __tablename__ = 'audio_cache'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)  # MD5 hash of the text
    text_content = db.Column(db.Text, nullable=False)  # Full text content
    audio_url = db.Column(db.String(1024), nullable=False)  # S3 URL of the audio file
    voice_id = db.Column(db.String(64), nullable=False)  # Voice ID used for generation

    # Stats
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_accessed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    access_count = db.Column(db.Integer, default=1)

    @staticmethod
    def get_hash(text):
        """Generate MD5 hash for text content."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @classmethod
    def find_by_text(cls, text):
        """Find cached audio by text content."""
        text_hash = cls.get_hash(text)
        return cls.query.filter_by(text_hash=text_hash).first()

    def update_stats(self):
        """Update access statistics."""
        self.last_accessed_at = datetime.utcnow()
        self.access_count += 1

    def __repr__(self):
        return f'<AudioCache hash={self.text_hash[:8]}... voice={self.voice_id}>'
