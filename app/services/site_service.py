"""
Site service - business logic for site operations.
"""
import logging
from app import db

logger = logging.getLogger(__name__)


def delete_site_with_assets(site, skip_db_delete=False):
    """
    Delete a site's S3 assets and optionally the site itself.

    This handles cleanup of:
    - Site image (image_url)
    - Site audio (audio_url)
    - Google photo references (google_photo_references array)

    Args:
        site: Site model instance
        skip_db_delete: If True, only delete S3 assets (useful when CASCADE will handle DB deletion)

    Returns:
        dict with:
        - s3_files_deleted: Number of S3 files successfully deleted
        - s3_files_failed: Number of S3 files that failed to delete
    """
    from app.services.s3_service import delete_file_from_s3

    # Collect S3 URLs to delete
    s3_urls_to_delete = []

    if site.image_url:
        s3_urls_to_delete.append(site.image_url)

    if site.audio_url:
        s3_urls_to_delete.append(site.audio_url)

    if site.google_photo_references:
        s3_urls_to_delete.extend(site.google_photo_references)

    # Delete S3 files
    deleted_count = 0
    failed_count = 0

    for url in s3_urls_to_delete:
        try:
            if delete_file_from_s3(url):
                deleted_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete S3 file {url}: {e}")
            failed_count += 1

    if s3_urls_to_delete:
        logger.info(
            f"Site {site.id} ({site.title}): deleted {deleted_count}/{len(s3_urls_to_delete)} S3 files"
        )

    # Delete from database unless skipped
    if not skip_db_delete:
        db.session.delete(site)

    return {
        's3_files_deleted': deleted_count,
        's3_files_failed': failed_count
    }


def bulk_delete_sites_with_assets(sites):
    """
    Delete multiple sites and their S3 assets.

    Args:
        sites: List of Site model instances

    Returns:
        dict with:
        - sites_deleted: Number of sites deleted
        - s3_files_deleted: Total S3 files deleted
        - s3_files_failed: Total S3 files that failed to delete
    """
    total_s3_deleted = 0
    total_s3_failed = 0
    sites_deleted = 0

    for site in sites:
        result = delete_site_with_assets(site, skip_db_delete=False)
        total_s3_deleted += result['s3_files_deleted']
        total_s3_failed += result['s3_files_failed']
        sites_deleted += 1

    return {
        'sites_deleted': sites_deleted,
        's3_files_deleted': total_s3_deleted,
        's3_files_failed': total_s3_failed
    }
