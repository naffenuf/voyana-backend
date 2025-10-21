"""
Application configuration.
"""
import os
from datetime import timedelta


class BaseConfig:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,  # Verify connections before use
    }

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # AWS S3
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME', 'voyana-tours')
    AWS_S3_REGION = os.getenv('AWS_S3_REGION', 'us-east-1')

    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # ElevenLabs
    ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')
    ELEVEN_LABS_VOICE_ID = os.getenv('ELEVEN_LABS_VOICE_ID', 'XrExE9yKIg1WjnnlVkGX')

    # Google
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

    # Email
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_FROM = os.getenv('SMTP_FROM', 'noreply@voyana.com')


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    ENV = 'development'
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://voyana:voyana_dev_pass@localhost:5432/voyana_db'
    )


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    ENV = 'production'
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

    # Require all secrets in production
    @classmethod
    def init_app(cls, app):
        """Validate production config."""
        required = [
            'SECRET_KEY',
            'JWT_SECRET_KEY',
            'SQLALCHEMY_DATABASE_URI',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
        ]
        for key in required:
            if not getattr(cls, key, None):
                raise ValueError(f'Production config missing: {key}')


class TestingConfig(BaseConfig):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret'
    SECRET_KEY = 'test-secret'
