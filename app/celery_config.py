"""
Celery configuration for background tasks.
"""
from celery import Celery
from flask import Flask


def make_celery(app: Flask) -> Celery:
    """
    Create and configure Celery instance integrated with Flask app.

    Args:
        app: Flask application instance

    Returns:
        Configured Celery instance
    """
    celery = Celery(
        app.import_name
    )

    # Configure broker and backend using new-style setting names
    celery.conf.broker_url = app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    celery.conf.result_backend = app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    # Configure task settings
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,  # 10 minutes max per task
        task_soft_time_limit=540,  # 9 minute soft limit
        worker_prefetch_multiplier=1,  # Process one task at a time
        worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory leaks
    )

    # Make celery work with Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    return celery
