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
    issue_detail = db.relationship('FeedbackIssue', backref='feedback', uselist=False)
    photo_detail = db.relationship('FeedbackPhoto', backref='feedback', uselist=False)
    location_detail = db.relationship('FeedbackLocation', backref='feedback', uselist=False)

    def to_dict(self, include_details=False):
        """
        Convert to dictionary.

        Args:
            include_details: If True, include user/tour/site details and type-specific data
        """
        result = {
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

        # Include related entity details if requested (for admin views)
        if include_details:
            # User info
            if self.user:
                result['user'] = {
                    'id': self.user.id,
                    'name': self.user.name or self.user.email,
                    'email': self.user.email,
                }
            else:
                result['user'] = None  # Anonymous

            # Reviewer info
            if self.reviewer:
                result['reviewer'] = {
                    'id': self.reviewer.id,
                    'name': self.reviewer.name or self.reviewer.email,
                    'email': self.reviewer.email,
                }
            else:
                result['reviewer'] = None

            # Tour info
            if self.tour:
                result['tour'] = {
                    'id': str(self.tour.id),
                    'name': self.tour.name,
                    'city': self.tour.city,
                    'neighborhood': self.tour.neighborhood,
                }
            else:
                result['tour'] = None

            # Site info
            if self.site:
                result['site'] = {
                    'id': str(self.site.id),
                    'title': self.site.title,
                    'latitude': self.site.latitude,
                    'longitude': self.site.longitude,
                    'imageUrl': self.site.image_url,
                }
            else:
                result['site'] = None

            # Type-specific details
            if self.feedback_type == 'issue' and hasattr(self, 'issue_detail') and self.issue_detail:
                result['issueDetail'] = self.issue_detail.to_dict()
            elif self.feedback_type == 'photo' and hasattr(self, 'photo_detail') and self.photo_detail:
                result['photoDetail'] = self.photo_detail.to_dict()
            elif self.feedback_type == 'location' and hasattr(self, 'location_detail') and self.location_detail:
                result['locationDetail'] = self.location_detail.to_dict()

        return result

    def __repr__(self):
        target = f'tour={self.tour_id}' if self.tour_id else f'site={self.site_id}'
        return f'<Feedback {self.feedback_type} {target}>'
