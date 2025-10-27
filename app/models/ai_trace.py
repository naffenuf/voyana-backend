"""
AITrace model for logging AI API calls.
"""
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSON
from app import db


class AITrace(db.Model):
    """AITrace model for tracking all AI API calls."""

    __tablename__ = 'ai_traces'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Prompt identification
    prompt_name = db.Column(db.String(100), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False, index=True)  # 'openai', 'grok', etc.
    model = db.Column(db.String(100), nullable=False)

    # Prompts and response
    system_prompt = db.Column(db.Text)
    user_prompt = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)

    # Raw request and response (for debugging)
    raw_request = db.Column(JSON)
    raw_response = db.Column(JSON)

    # Metadata (renamed from metadata to avoid SQLAlchemy reserved word)
    trace_metadata = db.Column(JSON)  # tokens, cost, latency, etc.

    # Status tracking
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # 'pending', 'success', 'error'
    error_message = db.Column(db.Text)

    # User tracking (optional)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = db.Column(db.DateTime)

    def to_dict(self, include_raw=False):
        """Convert to dictionary."""
        result = {
            'id': str(self.id),
            'promptName': self.prompt_name,
            'provider': self.provider,
            'model': self.model,
            'systemPrompt': self.system_prompt,
            'userPrompt': self.user_prompt,
            'response': self.response,
            'metadata': self.trace_metadata or {},
            'status': self.status,
            'errorMessage': self.error_message,
            'userId': self.user_id,
            'createdAt': self.created_at.isoformat(),
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
        }

        if include_raw:
            result['rawRequest'] = self.raw_request or {}
            result['rawResponse'] = self.raw_response or {}

        return result

    def __repr__(self):
        return f'<AITrace {self.prompt_name} - {self.provider}>'
