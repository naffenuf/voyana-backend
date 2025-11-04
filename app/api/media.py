"""
Media API endpoints (images, audio, presigned URLs).
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.services.s3_service import generate_presigned_url
from app.utils.device_binding import device_binding_required

media_bp = Blueprint('media', __name__)


@media_bp.route('/presigned-url', methods=['GET'])
@device_binding_required()
def get_presigned_url():
    """
    Get S3 presigned URL for accessing private objects.

    Query Parameters:
        url: The S3 URL to generate a presigned URL for

    Returns:
        JSON response with presigned URL

    Authentication:
        Requires valid JWT token in Authorization header
    """
    try:
        # Get URL from query parameters
        url = request.args.get('url')

        if not url:
            current_app.logger.warning("Presigned URL request missing 'url' parameter")
            return jsonify({"error": "URL parameter is required"}), 400

        current_app.logger.info(f"Presigned URL requested for: {url[:100]}...")

        # Generate presigned URL with 1 hour expiration
        presigned_url = generate_presigned_url(url, expires_in=3600)

        if presigned_url:
            return jsonify({
                "success": True,
                "presignedUrl": presigned_url,
                "originalUrl": url,
                "expiresIn": 3600
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to generate presigned URL"
            }), 500

    except Exception as e:
        current_app.logger.error(f"Error generating presigned URL: {e}")
        return jsonify({"error": "Failed to generate presigned URL"}), 500


# TODO: Implement media upload/download endpoints
