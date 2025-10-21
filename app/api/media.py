"""
Media API endpoints (images, audio, presigned URLs).
"""
from flask import Blueprint

media_bp = Blueprint('media', __name__)


@media_bp.route('/presigned-url', methods=['GET'])
def get_presigned_url():
    """Get S3 presigned URL."""
    return {'presigned_url': 'TODO'}, 200


# TODO: Implement media upload/download endpoints
