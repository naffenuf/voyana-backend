"""
Feedback issue model.
"""
from sqlalchemy.dialects.postgresql import ENUM
from app import db


class FeedbackIssue(db.Model):
    """Issue feedback detail model."""

    __tablename__ = 'feedback_issues'

    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id', ondelete='CASCADE'), primary_key=True)

    # Issue details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)  # Optional - user may only select category
    severity = db.Column(db.String(20))  # 'low', 'medium', 'high' - set by user or app

    # Relationship back to parent (defined on Feedback side)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'feedbackId': self.feedback_id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity,
        }

    def __repr__(self):
        return f'<FeedbackIssue {self.feedback_id}: {self.title}>'
