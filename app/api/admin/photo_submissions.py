"""
Admin API endpoints for photo submission feedback management.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models.feedback import Feedback
from app.models.feedback_photo import FeedbackPhoto
from app.models.site import Site
from app.utils.admin_required import admin_required

admin_photo_submissions_bp = Blueprint('admin_photo_submissions', __name__)


@admin_photo_submissions_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_photo_submissions():
    """
    List all photo submission feedback with optional filters (admin only).

    Query params:
        - status: Filter by status (pending, reviewed, resolved, dismissed)
        - site_id: Filter by site ID
        - tour_id: Filter by tour ID
        - limit: Number of results (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "photos": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    status = request.args.get('status', '').strip()
    site_id = request.args.get('site_id', '').strip()
    tour_id = request.args.get('tour_id', '').strip()
    limit = min(request.args.get('limit', 100, type=int), 500)  # Cap at 500
    offset = request.args.get('offset', 0, type=int)

    # Build query - join feedback with photo details
    query = db.session.query(Feedback, FeedbackPhoto).join(
        FeedbackPhoto,
        Feedback.id == FeedbackPhoto.feedback_id
    ).filter(
        Feedback.feedback_type == 'photo'
    )

    # Apply filters
    if status:
        query = query.filter(Feedback.status == status)

    if site_id:
        query = query.filter(Feedback.site_id == site_id)

    if tour_id:
        query = query.filter(Feedback.tour_id == tour_id)

    # Get total count
    total = query.count()

    # Execute query with pagination (most recent first)
    results = query.order_by(Feedback.created_at.desc()).limit(limit).offset(offset).all()

    # Format response
    photos = []
    for feedback, photo_detail in results:
        photo_data = feedback.to_dict(include_details=True)
        photos.append(photo_data)

    return jsonify({
        'photos': photos,
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_photo_submissions_bp.route('/<int:feedback_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_photo_submission(feedback_id):
    """
    Get a specific photo submission feedback by ID (admin only).

    Returns:
        {
            "photo": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'photo':
        return jsonify({'error': 'Photo submission not found'}), 404

    return jsonify({'photo': feedback.to_dict(include_details=True)}), 200


@admin_photo_submissions_bp.route('/<int:feedback_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_photo_submission(feedback_id):
    """
    Update photo submission status and admin notes (admin only).

    Request body:
        {
            "status": "reviewed" | "resolved" | "dismissed",
            "adminNotes": "Admin comments here..."
        }

    Returns:
        {
            "photo": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'photo':
        return jsonify({'error': 'Photo submission not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Update status
    if 'status' in data:
        valid_statuses = ['pending', 'reviewed', 'resolved', 'dismissed']
        new_status = data['status']

        if new_status not in valid_statuses:
            return jsonify({'error': f'Status must be one of: {", ".join(valid_statuses)}'}), 400

        old_status = feedback.status
        feedback.status = new_status

        # Set reviewed timestamp if changing from pending
        if old_status == 'pending' and new_status != 'pending':
            feedback.reviewed_at = datetime.utcnow()
            feedback.reviewed_by = int(get_jwt_identity())

    # Update admin notes
    if 'adminNotes' in data:
        feedback.admin_notes = data['adminNotes']

    db.session.commit()

    current_app.logger.info(f'Admin updated photo submission: {feedback.id} (status: {feedback.status})')

    return jsonify({'photo': feedback.to_dict(include_details=True)}), 200


@admin_photo_submissions_bp.route('/<int:feedback_id>/approve', methods=['POST'])
@jwt_required()
@admin_required()
def approve_photo_submission(feedback_id):
    """
    Approve a photo submission and replace site's image (admin only).

    This endpoint will:
    1. Upload the photo_data to S3
    2. Update the site's image_url
    3. Store S3 URL in photo_detail.photo_url
    4. Clear photo_data from feedback table
    5. Mark feedback as resolved

    Request body:
        {
            "replaceImage": true  # If true, replace site's main image
        }

    Returns:
        {
            "photo": {...},
            "site": {...}
        }

    Note: S3 upload service will be implemented in Phase 5
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'photo':
        return jsonify({'error': 'Photo submission not found'}), 404

    if not feedback.site_id:
        return jsonify({'error': 'Photo submission has no associated site'}), 400

    if not feedback.photo_data:
        return jsonify({'error': 'Photo submission has no photo data'}), 400

    data = request.get_json() or {}
    replace_image = data.get('replaceImage', True)

    # Get site
    site = Site.query.get(feedback.site_id)
    if not site:
        return jsonify({'error': 'Associated site not found'}), 404

    # TODO: Phase 5 - Implement S3 upload service
    # For now, return error indicating this is not yet implemented
    return jsonify({
        'error': 'Photo approval with S3 upload not yet implemented. This will be added in Phase 5.'
    }), 501  # Not Implemented


@admin_photo_submissions_bp.route('/<int:feedback_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_photo_submission(feedback_id):
    """
    Delete a photo submission feedback (admin only).

    Returns:
        {
            "message": "Photo submission deleted successfully"
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'photo':
        return jsonify({'error': 'Photo submission not found'}), 404

    db.session.delete(feedback)
    db.session.commit()

    current_app.logger.info(f'Admin deleted photo submission: {feedback_id}')

    return jsonify({
        'message': 'Photo submission deleted successfully'
    }), 200
