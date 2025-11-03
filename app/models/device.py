"""
Device registration models for device binding security.
"""
from datetime import datetime
from app import db


class DeviceRegistration(db.Model):
    """
    Model for tracking registered devices.

    Each device that successfully registers gets an entry in this table.
    The device_id (iOS vendor ID or Android ID) is used to bind JWT tokens
    to specific devices, preventing token theft/reuse on unauthorized devices.
    """
    __tablename__ = 'device_registrations'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    device_name = db.Column(db.String(128), nullable=True)
    platform = db.Column(db.String(20), nullable=True)  # 'iOS' or 'Android'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    def __repr__(self):
        return f'<DeviceRegistration {self.device_id} ({self.device_name})>'

    def to_dict(self):
        """Convert device registration to dictionary."""
        return {
            'id': self.id,
            'deviceId': self.device_id,
            'deviceName': self.device_name,
            'platform': self.platform,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastUsedAt': self.last_used_at.isoformat() if self.last_used_at else None,
            'isActive': self.is_active
        }

    @staticmethod
    def register_device(device_id, device_name=None, platform=None):
        """
        Register a new device or reactivate an existing one.

        Args:
            device_id: Unique device identifier (iOS vendor ID or Android ID)
            device_name: Optional device name for display
            platform: Optional platform identifier ('iOS' or 'Android')

        Returns:
            tuple: (DeviceRegistration, was_created) where was_created is True if new
        """
        device = DeviceRegistration.query.filter_by(device_id=device_id).first()

        if device:
            # Device already registered - update last used and reactivate if needed
            device.last_used_at = datetime.utcnow()
            if not device.is_active:
                device.is_active = True
            # Update name/platform if provided
            if device_name:
                device.device_name = device_name
            if platform:
                device.platform = platform
            db.session.commit()
            return device, False
        else:
            # Create new device registration
            device = DeviceRegistration(
                device_id=device_id,
                device_name=device_name,
                platform=platform
            )
            db.session.add(device)
            db.session.commit()
            return device, True

    @staticmethod
    def is_device_active(device_id):
        """
        Check if a device is registered and active.

        Args:
            device_id: Device identifier to check

        Returns:
            bool: True if device is registered and active
        """
        device = DeviceRegistration.query.filter_by(
            device_id=device_id,
            is_active=True
        ).first()
        return device is not None

    @staticmethod
    def update_last_used(device_id):
        """
        Update the last_used_at timestamp for a device.

        Args:
            device_id: Device identifier to update
        """
        device = DeviceRegistration.query.filter_by(device_id=device_id).first()
        if device:
            device.last_used_at = datetime.utcnow()
            db.session.commit()
