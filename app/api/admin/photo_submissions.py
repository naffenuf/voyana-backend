"""
Admin API endpoints for photo submission feedback management.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import base64
import uuid
from io import BytesIO
from app import db
from app.models.feedback import Feedback
from app.models.feedback_photo import FeedbackPhoto
from app.models.site import Site
from app.services.s3_service import upload_file_to_s3
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
    1. Decode Base64 photo data
    2. Upload the photo to S3
    3. Update the site's image_url (if replaceImage is true)
    4. Store S3 URL in photo_detail.photo_url
    5. Clear photo_data from feedback table
    6. Mark feedback as resolved

    Request body:
        {
            "replaceImage": true,  # If true, replace site's main image
            "updateLocation": false  # If true, update site's location with photo location
        }

    Returns:
        {
            "photo": {...},
            "site": {...}
        }
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
    update_location = data.get('updateLocation', False)

    # Get site
    site = Site.query.get(feedback.site_id)
    if not site:
        return jsonify({'error': 'Associated site not found'}), 404

    try:
        # Decode Base64 photo data
        # Handle data URL format (e.g., "data:image/jpeg;base64,/9j/4AAQ...")
        photo_data_str = feedback.photo_data
        if ',' in photo_data_str and 'base64' in photo_data_str:
            # Extract just the base64 part after the comma
            photo_data_str = photo_data_str.split(',', 1)[1]

        # Decode base64 to bytes
        photo_bytes = base64.b64decode(photo_data_str)

        # Generate unique filename
        file_name = f"user-submitted-{site.id}-{uuid.uuid4()}.jpg"

        # Upload to S3 in 'site-photos' folder
        s3_url = upload_file_to_s3(
            file_data=BytesIO(photo_bytes),
            file_name=file_name,
            folder='site-photos',
            content_type='image/jpeg'
        )

        if not s3_url:
            current_app.logger.error(f'Failed to upload photo to S3 for feedback {feedback_id}')
            return jsonify({'error': 'Failed to upload photo to S3'}), 500

        current_app.logger.info(f'Uploaded photo to S3: {s3_url}')

        # Update site's image_url if requested
        if replace_image:
            old_image_url = site.image_url
            site.image_url = s3_url
            current_app.logger.info(f'Replaced site {site.id} image: {old_image_url} -> {s3_url}')

        # Update site's location if requested and photo has location data
        if update_location and feedback.photo_detail:
            photo_detail = feedback.photo_detail
            if photo_detail.latitude is not None and photo_detail.longitude is not None:
                old_location = (site.latitude, site.longitude)
                site.latitude = photo_detail.latitude
                site.longitude = photo_detail.longitude
                current_app.logger.info(f'Updated site {site.id} location: {old_location} -> ({site.latitude}, {site.longitude})')

        # Get or create photo detail record
        photo_detail = feedback.photo_detail
        if not photo_detail:
            photo_detail = FeedbackPhoto(feedback_id=feedback.id)
            db.session.add(photo_detail)

        # Store S3 URL in photo detail
        photo_detail.photo_url = s3_url

        # Clear Base64 data from feedback (no longer needed, saves DB space)
        feedback.photo_data = None

        # Mark feedback as resolved
        feedback.status = 'resolved'
        feedback.reviewed_at = datetime.utcnow()
        feedback.reviewed_by = int(get_jwt_identity())

        # Add admin note about what was done
        actions = []
        if replace_image:
            actions.append('replaced site image')
        if update_location:
            actions.append('updated site location')
        if not actions:
            actions.append('saved to S3')

        approval_note = f"Photo approved and {', '.join(actions)}."
        if feedback.admin_notes:
            feedback.admin_notes = f"{feedback.admin_notes}\n\n{approval_note}"
        else:
            feedback.admin_notes = approval_note

        # Commit all changes
        db.session.commit()

        current_app.logger.info(f'Approved photo submission {feedback_id}: {approval_note}')

        return jsonify({
            'photo': feedback.to_dict(include_details=True),
            'site': site.to_dict()
        }), 200

    except base64.binascii.Error as e:
        current_app.logger.error(f'Invalid Base64 data for feedback {feedback_id}: {e}')
        db.session.rollback()
        return jsonify({'error': 'Invalid Base64 photo data'}), 400
    except Exception as e:
        current_app.logger.error(f'Error approving photo submission {feedback_id}: {e}')
        db.session.rollback()
        return jsonify({'error': f'Failed to approve photo: {str(e)}'}), 500


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
