"""
User and authentication models.
"""
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import UUID
from app import db


class User(db.Model):
    """User account model."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))  # NULL for OAuth-only users
    name = db.Column(db.String(255))
    role = db.Column(db.String(20), default='creator', nullable=False)

    # OAuth identifiers
    google_id = db.Column(db.String(255), unique=True)
    apple_id = db.Column(db.String(255), unique=True)

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime)

    # Relationships
    tours = db.relationship('Tour', back_populates='owner', lazy='dynamic', cascade='all, delete-orphan')
    api_keys = db.relationship('ApiKey', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat(),
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
        }

    def __repr__(self):
        return f'<User {self.email}>'


class ApiKey(db.Model):
    """API key for programmatic access."""

    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='api_keys')

    @staticmethod
    def generate_key():
        """Generate a random, URL-safe API key."""
        return secrets.token_urlsafe(32)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'key': self.key if self.is_active else None,
            'created_at': self.created_at.isoformat(),
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<ApiKey {self.name}>'


class PasswordResetToken(db.Model):
    """Password reset token for email-based password reset."""

    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User')

    @staticmethod
    def generate_token():
        """Generate a random token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_for_user(user, expiry_hours=24):
        """Create a new reset token for a user."""
        token = PasswordResetToken(
            user_id=user.id,
            token=PasswordResetToken.generate_token(),
            expires_at=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        return token

    def is_valid(self):
        """Check if token is still valid."""
        return not self.used and datetime.utcnow() < self.expires_at

    def __repr__(self):
        return f'<PasswordResetToken user_id={self.user_id}>'
