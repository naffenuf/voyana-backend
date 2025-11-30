"""
Background tasks for tour operations.

This module contains Celery tasks for processing tour-level operations in the background.
Tasks are triggered by API endpoints and tracked via the BackgroundJob model.
"""
import logging
import time
from datetime import datetime
from app import db
from app.models.tour import Tour
from app.models.site import Site
from app.models.background_job import BackgroundJob
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


def fact_check_tour_sites_task(celery_app, job_id, tour_id, user_id):
    """
    Background task to fact-check all site descriptions in a tour.

    Processes each site sequentially, using AI to fact-check and rewrite descriptions.
    Updates job progress in real-time for status polling. Runs asynchronously
    to avoid HTTP timeout issues (Gunicorn 120s limit, AI calls can be 180s each).

    **Process:**
    1. Fetches all sites in tour
    2. Skips sites that lack descriptions
    3. Fact-checks remaining sites using Grok AI (with 1s delay between requests)
    4. Updates site.description on success
    5. Tracks all results and updates job status

    Args:
        celery_app: Celery application instance
        job_id: UUID of the BackgroundJob tracking this task
        tour_id: UUID of the tour
        user_id: ID of the user who initiated the request

    Returns:
        dict: Results summary with counts and per-site results
    """
    logger.info(f"Starting fact-check task for tour {tour_id}, job {job_id}")

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
        job.progress_message = 'Starting fact-check process...'
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

        logger.info(f"Fact-checking {total_sites} sites for tour {tour_id}")

        for idx, tour_site in enumerate(tour_sites):
            site = tour_site.site

            # Update progress
            progress = int((idx / total_sites) * 100)
            job.progress = progress
            job.progress_message = f'Fact-checking site {idx + 1}/{total_sites}: {site.title}'
            db.session.commit()

            logger.info(f"[{idx + 1}/{total_sites}] Processing site {site.id}: {site.title}")

            # Skip if site has no description
            if not site.description or not site.description.strip():
                logger.info(f"Site {site.id} has no description, skipping")
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'skipped',
                    'reason': 'No description to fact-check'
                })
                sites_skipped += 1
                continue

            # Add delay between requests to avoid rate limiting
            if sites_processed > 0 or sites_skipped > 0:
                time.sleep(1)  # 1 second delay between AI requests

            # Fact-check this site's description
            logger.info(f"Fact-checking site {site.id}: {site.title}")

            try:
                # Prepare location string
                location_str = f"{site.latitude}, {site.longitude}"
                if site.formatted_address:
                    location_str = f"{site.formatted_address} ({site.latitude}, {site.longitude})"

                # Call AI service with fact-check prompt
                ai_result = ai_service.execute_prompt(
                    prompt_name='fact_check_site_description',
                    variables={
                        'site_title': site.title,
                        'location': location_str,
                        'description': site.description
                    },
                    user_id=user_id
                )

                # Extract rewritten description and changes from parsed JSON
                if 'parsed' not in ai_result:
                    raise ValueError('AI response was not valid JSON')

                parsed = ai_result['parsed']
                new_description = parsed.get('rewritten_description')
                changes_list = parsed.get('changes', [])

                if not new_description:
                    raise ValueError('AI did not return a rewritten description')

                # Update site with new description
                original_description = site.description
                site.description = new_description
                db.session.add(site)
                db.session.commit()

                logger.info(f"Successfully fact-checked site {site.id}")

                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'success',
                    'originalDescription': original_description,
                    'newDescription': new_description,
                    'changesList': changes_list,
                    'traceId': ai_result.get('trace_id')
                })
                sites_processed += 1

            except Exception as e:
                logger.error(f"Failed to fact-check site {site.id}: {e}", exc_info=True)
                results.append({
                    'siteId': str(site.id),
                    'siteTitle': site.title,
                    'status': 'error',
                    'error': str(e)
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
            f"Fact-check task completed for tour {tour_id}: "
            f"{sites_processed} processed, {sites_skipped} skipped, {sites_failed} failed"
        )

        return job.result

    except Exception as e:
        logger.error(f"Error in fact-check task for tour {tour_id}: {e}", exc_info=True)

        # Mark job as failed
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.session.commit()

        raise  # Re-raise to let Celery handle retry logic
