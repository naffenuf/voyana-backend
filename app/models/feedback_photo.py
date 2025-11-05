"""
Feedback photo model.
"""
from app import db


class FeedbackPhoto(db.Model):
    """Photo feedback detail model."""

    __tablename__ = 'feedback_photos'

    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id', ondelete='CASCADE'), primary_key=True)

    # Photo details
    photo_url = db.Column(db.String(1024))  # S3 URL after admin approves and uploads
    caption = db.Column(db.Text)  # Optional user caption

    # Relationship back to parent (defined on Feedback side)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'feedbackId': self.feedback_id,
            'photoUrl': self.photo_url,
            'caption': self.caption,
        }

    def __repr__(self):
        return f'<FeedbackPhoto {self.feedback_id}>'
