"""
Feedback location model.
"""
from datetime import datetime
from app import db


class FeedbackLocation(db.Model):
    """Location feedback detail model."""

    __tablename__ = 'feedback_locations'

    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id', ondelete='CASCADE'), primary_key=True)

    # Location details
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float)  # Accuracy in meters (optional)
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship back to parent (defined on Feedback side)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'feedbackId': self.feedback_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'recordedAt': self.recorded_at.isoformat() if self.recorded_at else None,
        }

    def __repr__(self):
        return f'<FeedbackLocation {self.feedback_id}: {self.latitude}, {self.longitude}>'
