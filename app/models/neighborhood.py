"""
Neighborhood description model.
"""
from datetime import datetime
from app import db


class NeighborhoodDescription(db.Model):
    """Neighborhood description model."""

    __tablename__ = 'neighborhood_descriptions'

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    neighborhood = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('city', 'neighborhood', name='unique_city_neighborhood'),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'city': self.city,
            'neighborhood': self.neighborhood,
            'description': self.description,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f'<NeighborhoodDescription {self.city}/{self.neighborhood}>'
