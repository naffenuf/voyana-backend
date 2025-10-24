"""
Media API endpoints (images, audio, presigned URLs).
"""
from flask import Blueprint, request, jsonify, current_app
from app.services.s3_service import generate_presigned_url

media_bp = Blueprint('media', __name__)


@media_bp.route('/presigned-url', methods=['GET'])
def get_presigned_url():
    """
    Get S3 presigned URL for accessing private objects.

    Query Parameters:
        url: The S3 URL to generate a presigned URL for
        api_key: (Optional) API key for authentication

    Returns:
        JSON response with presigned URL
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
