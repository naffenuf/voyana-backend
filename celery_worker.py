"""
Celery worker entry point for background task processing.

This worker handles long-running operations that would timeout in HTTP requests:
- Bulk audio generation for tour sites (admin operations)
- Future: Image processing, report generation, data exports, etc.

**Current Use Cases:**
- Pre-generating TTS audio for all sites in a tour
- Avoiding 120s Gunicorn timeout when processing multiple sites

**Running Locally:**
    celery -A celery_worker.celery_app worker --loglevel=info

**In Docker:**
    Automatically started via docker-compose (see docker-compose.yml)

**Monitoring:**
    - View worker logs: docker-compose logs celery-worker
    - Check job status: GET /api/jobs/<job_id>
    - List all jobs: GET /api/jobs
"""
import os
from app import create_app
from app.celery_config import make_celery

# Create Flask app
flask_app = create_app(os.getenv('FLASK_ENV', 'development'))

# Create Celery app
celery_app = make_celery(flask_app)

# Import tasks to register them with Celery
from app.tasks.audio_tasks import generate_audio_for_tour_task


# Register tasks with Celery decorator
@celery_app.task(bind=True, name='generate_audio_for_tour')
def generate_audio_for_tour(self, job_id, tour_id, user_id):
    """Celery task wrapper for audio generation."""
    return generate_audio_for_tour_task(celery_app, job_id, tour_id, user_id)
