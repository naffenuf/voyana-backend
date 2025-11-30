"""
Background tasks for audio generation.

This module contains Celery tasks for processing audio generation in the background.
Tasks are triggered by API endpoints and tracked via the BackgroundJob model.
"""
import logging
import time
from datetime import datetime
from app import db
from app.models.tour import Tour
from app.models.site import Site
from app.models.background_job import BackgroundJob
from app.services.tts_service import generate_audio

logger = logging.getLogger(__name__)


def generate_audio_for_tour_task(celery_app, job_id, tour_id, user_id):
    """
    Background task to generate audio for all sites in a tour.

    Processes each site sequentially, generating TTS audio via ElevenLabs API.
    Updates job progress in real-time for status polling. Runs asynchronously
    to avoid HTTP timeout issues (Gunicorn 120s limit).

    **Process:**
    1. Fetches all sites in tour
    2. Skips sites that already have audio or lack descriptions
    3. Generates audio for remaining sites (with 1s delay between requests)
    4. Updates site.audio_url on success
    5. Tracks all results and updates job status

    Args:
        celery_app: Celery application instance
        job_id: UUID of the BackgroundJob tracking this task
        tour_id: UUID of the tour
        user_id: ID of the user who initiated the request

    Returns:
        dict: Results summary with counts and per-site results
    """
    logger.info(f"Starting audio generation task for tour {tour_id}, job {job_id}")

    # Get the job record
    job = BackgroundJob.query.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return {'error': 'Job not found'}

    try:
        # Mark job as started
        job.status = 'started'
        job.started_at = datetime.utcnow()
        job.progress = 0
        job.progress_message = 'Starting audio generation...'
        db.session.commit()

        # Get the tour
        tour = Tour.query.get(tour_id)
        if not tour:
            raise ValueError(f'Tour {tour_id} not found')

        # Get all sites for this tour
        tour_sites = tour.tour_sites
        if not tour_sites:
            raise ValueError('Tour has no sites')

        total_sites = len(tour_sites)
        results = []
        sites_processed = 0
        sites_skipped = 0
        sites_failed = 0

        logger.info(f"Processing {total_sites} sites for tour {tour_id}")

        for idx, tour_site in enumerate(tour_sites):
            site = tour_site.site

            # Update progress
            progress = int((idx / total_sites) * 100)
            job.progress = progress
            job.progress_message = f'Processing site {idx + 1}/{total_sites}: {site.title}'
            db.session.commit()

            logger.info(f"[{idx + 1}/{total_sites}] Processing site {site.id}: {site.title}")

            # Skip if site already has audio
            if site.audio_url:
                logger.info(f"Site {site.id} already has audio, skipping")
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'skipped',
                    'reason': 'Already has audio URL'
                })
                sites_skipped += 1
                continue

            # Skip if site has no description
            if not site.description or not site.description.strip():
                logger.info(f"Site {site.id} has no description, skipping")
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'skipped',
                    'reason': 'No description to convert'
                })
                sites_skipped += 1
                continue

            # Generate audio for this site
            logger.info(f"Generating audio for site {site.id}: {site.title}")

            # Add a small delay between requests to avoid rate limiting
            if sites_processed > 0 or sites_skipped > 0:
                time.sleep(1)  # 1 second delay between audio generation requests

            audio_result = generate_audio(site.description, user_id=user_id)

            if audio_result['status'] == 'success':
                # Update site with audio URL
                site.audio_url = audio_result['audio_url']
                db.session.add(site)
                db.session.commit()

                logger.info(
                    f"Audio generated successfully for site {site.id} "
                    f"(from_cache: {audio_result['from_cache']})"
                )

                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'success',
                    'audioUrl': audio_result['audio_url'],
                    'fromCache': audio_result['from_cache'],
                    'traceId': audio_result.get('trace_id')
                })
                sites_processed += 1
            else:
                # Audio generation failed
                logger.error(f"Failed to generate audio for site {site.id}: {audio_result.get('error')}")
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'error',
                    'error': audio_result.get('error', 'Unknown error')
                })
                sites_failed += 1

        # Mark job as complete
        job.status = 'success'
        job.progress = 100
        job.progress_message = f'Completed: {sites_processed} processed, {sites_skipped} skipped, {sites_failed} failed'
        job.result = {
            'sitesProcessed': sites_processed,
            'sitesSkipped': sites_skipped,
            'sitesFailed': sites_failed,
            'totalSites': total_sites,
            'results': results
        }
        job.completed_at = datetime.utcnow()
        db.session.commit()

        logger.info(
            f"Audio generation task completed for tour {tour_id}: "
            f"{sites_processed} processed, {sites_skipped} skipped, {sites_failed} failed"
        )

        return job.result

    except Exception as e:
        logger.error(f"Error in audio generation task for tour {tour_id}: {e}", exc_info=True)

        # Mark job as failed
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.session.commit()

        raise  # Re-raise to let Celery handle retry logic
