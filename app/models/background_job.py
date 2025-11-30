"""
BackgroundJob model for tracking async job status.
"""
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSON
from app import db


class BackgroundJob(db.Model):
    """BackgroundJob model for tracking background task status."""

    __tablename__ = 'background_jobs'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job identification
    job_type = db.Column(db.String(50), nullable=False, index=True)  # 'tour_audio_generation', etc.
    celery_task_id = db.Column(db.String(255), nullable=False, unique=True, index=True)

    # Job parameters
    parameters = db.Column(JSON)  # Original request parameters (e.g., tour_id, user_id)

    # Status tracking
    status = db.Column(
        db.String(20),
        nullable=False,
        default='pending',
        index=True
    )  # 'pending', 'started', 'success', 'failed', 'cancelled'

    # Progress tracking
    progress = db.Column(db.Integer, default=0)  # 0-100 percentage
    progress_message = db.Column(db.String(255))  # Human-readable progress update

    # Results
    result = db.Column(JSON)  # Final result data
    error_message = db.Column(db.Text)  # Error details if failed

    # User tracking
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'jobType': self.job_type,
            'celeryTaskId': self.celery_task_id,
            'parameters': self.parameters or {},
            'status': self.status,
            'progress': self.progress,
            'progressMessage': self.progress_message,
            'result': self.result or {},
            'errorMessage': self.error_message,
            'userId': self.user_id,
            'createdAt': self.created_at.isoformat(),
            'startedAt': self.started_at.isoformat() if self.started_at else None,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self):
        return f'<BackgroundJob {self.job_type} - {self.status}>'
