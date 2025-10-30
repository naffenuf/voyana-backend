"""
Feedback model.
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app import db


class Feedback(db.Model):
    """Feedback model for tours and sites."""

    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)

    # What is this feedback for?
    tour_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tours.id', ondelete='CASCADE'))
    site_id = db.Column(UUID(as_uuid=True), db.ForeignKey('sites.id', ondelete='CASCADE'))

    # Who submitted it (optional - allow anonymous)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))

    # Feedback content
    feedback_type = db.Column(db.String(50), nullable=False)  # 'issue', 'rating', 'comment', 'suggestion', 'photo'
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.Text)
    photo_data = db.Column(db.Text)  # Base64-encoded image for 'photo' feedback type

    # Status tracking
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'reviewed', 'resolved', 'dismissed'
    admin_notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))

    # Relationships
    tour = db.relationship('Tour')
    site = db.relationship('Site')
    user = db.relationship('User', foreign_keys=[user_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'tourId': str(self.tour_id) if self.tour_id else None,
            'siteId': str(self.site_id) if self.site_id else None,
            'userId': self.user_id,
            'feedbackType': self.feedback_type,
            'rating': self.rating,
            'comment': self.comment,
            'photoData': self.photo_data,
            'status': self.status,
            'adminNotes': self.admin_notes,
            'createdAt': self.created_at.isoformat(),
            'reviewedAt': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewedBy': self.reviewed_by,
        }

    def __repr__(self):
        target = f'tour={self.tour_id}' if self.tour_id else f'site={self.site_id}'
        return f'<Feedback {self.feedback_type} {target}>'
