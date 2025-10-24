"""
S3 service for presigned URL generation and file uploads.
"""
import re
import logging
import boto3
from botocore.exceptions import ClientError
from flask import current_app

logger = logging.getLogger(__name__)


def get_s3_client():
    """Create and return a boto3 S3 client using app configuration."""
    return boto3.client(
        's3',
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
        region_name=current_app.config['AWS_S3_REGION']
    )


def generate_presigned_url(object_url, expires_in=3600):
    """
    Generate a presigned URL for accessing a private object in S3.

    Args:
        object_url: The URL of the object in S3
        expires_in: Time in seconds for the URL to remain valid (default: 1 hour)

    Returns:
        A presigned URL for the object, or the original URL if not an S3 URL
    """
    try:
        if not object_url:
            logger.warning("Empty object URL provided")
            return None

        logger.info(f"Processing URL for presigned access: {object_url[:100]}...")

        # Early return for non-S3 URLs
        if not (('s3.' in object_url and 'amazonaws.com' in object_url) or
                '.s3.amazonaws.com' in object_url):
            logger.info(f"Not an S3 URL, returning original: {object_url[:100]}...")
            return object_url

        s3_client = get_s3_client()
        bucket_name = current_app.config['AWS_S3_BUCKET_NAME']
        object_key = None

        # Extract bucket name from URL for multi-bucket support
        bucket_name_from_url = None
        if '.s3.' in object_url and '.amazonaws.com' in object_url:
            # Format: https://bucket-name.s3.region.amazonaws.com/...
            match = re.search(r'https?://([^.]+)\.s3\.', object_url)
            if match:
                bucket_name_from_url = match.group(1)
                logger.debug(f"Extracted bucket name from URL: {bucket_name_from_url}")
        elif '.s3.amazonaws.com' in object_url:
            # Format: https://bucket-name.s3.amazonaws.com/...
            match = re.search(r'https?://([^.]+)\.s3\.amazonaws', object_url)
            if match:
                bucket_name_from_url = match.group(1)
                logger.debug(f"Extracted bucket name from URL: {bucket_name_from_url}")

        # Extract the object key based on URL format
        if '.s3.' in object_url and '.amazonaws.com/' in object_url:
            # Regional URL format: https://bucket-name.s3.region.amazonaws.com/path/to/file.jpg
            parts = object_url.split('.amazonaws.com/')
            if len(parts) == 2:
                object_key = parts[1]
                logger.debug(f"Parsed S3 URL (regional format): {object_key[:50]}...")
        elif 's3.amazonaws.com/' in object_url:
            # Global URL format: https://bucket-name.s3.amazonaws.com/path/to/file.jpg
            parts = object_url.split('amazonaws.com/')
            if len(parts) == 2:
                object_key = parts[1]
                logger.debug(f"Parsed S3 URL (global format): {object_key[:50]}...")
        elif '.s3.amazonaws.com/' in object_url:
            # Alternate bucket format: https://bucket-name.s3.amazonaws.com/path/to/file.jpg
            parts = object_url.split('.s3.amazonaws.com/')
            if len(parts) == 2:
                object_key = parts[1]
                logger.debug(f"Parsed S3 URL (alternate bucket format): {object_key[:50]}...")

        if not object_key:
            logger.warning(f"Could not extract object key from URL: {object_url[:100]}...")
            return object_url

        # If we extracted a bucket name from the URL and it's different from config, use that instead
        if bucket_name_from_url and bucket_name_from_url != bucket_name:
            logger.info(f"Using bucket name from URL: {bucket_name_from_url} instead of config: {bucket_name}")
            bucket_name = bucket_name_from_url

        # Generate a presigned URL
        try:
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': object_key,
                    'ResponseCacheControl': 'max-age=31536000, public'  # Cache for 1 year
                },
                ExpiresIn=expires_in
            )

            logger.info(f"Generated presigned URL for {object_key[:50]}... (expires in {expires_in}s)")
            return presigned_url

        except ClientError as e:
            logger.error(f"Error generating presigned URL for {object_key}: {e}")
            return object_url  # Fall back to original URL

    except Exception as e:
        logger.error(f"Error in generate_presigned_url: {e}")
        return object_url  # Fall back to original URL on error


def upload_file_to_s3(file_data, file_name, folder='audio', content_type='audio/mpeg'):
    """
    Upload a file to S3 bucket and return the URL.

    Args:
        file_data: File-like object or bytes containing the file data
        file_name: Name for the file in S3
        folder: Folder/prefix in S3 bucket (default: 'audio')
        content_type: MIME type of the file (default: 'audio/mpeg')

    Returns:
        URL to the uploaded file or None if upload fails
    """
    try:
        s3_client = get_s3_client()
        bucket_name = current_app.config['AWS_S3_BUCKET_NAME']
        region = current_app.config['AWS_S3_REGION']

        # Construct the S3 key (path)
        object_key = f"{folder}/{file_name}"

        logger.info(f"Uploading file to S3: {object_key}")

        # Upload the file
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_data,
            ContentType=content_type,
            CacheControl='max-age=31536000, public'  # Cache for 1 year
        )

        # Construct the S3 URL
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_key}"

        logger.info(f"Successfully uploaded file to: {s3_url}")
        return s3_url

    except ClientError as e:
        logger.error(f"Error uploading file to S3: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading file to S3: {e}")
        return None
