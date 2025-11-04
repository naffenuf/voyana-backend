"""
Admin API endpoints for location feedback management.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import func
from app import db
from app.models.feedback import Feedback
from app.models.feedback_location import FeedbackLocation
from app.models.site import Site
from app.utils.admin_required import admin_required

admin_location_data_bp = Blueprint('admin_location_data', __name__)


@admin_location_data_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_location_data():
    """
    List all location feedback with optional filters (admin only).

    Query params:
        - status: Filter by status (pending, reviewed, resolved, dismissed)
        - site_id: Filter by site ID
        - tour_id: Filter by tour ID
        - limit: Number of results (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "locations": [...],
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

    # Build query - join feedback with location details
    query = db.session.query(Feedback, FeedbackLocation).join(
        FeedbackLocation,
        Feedback.id == FeedbackLocation.feedback_id
    ).filter(
        Feedback.feedback_type == 'location'
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
    locations = []
    for feedback, location_detail in results:
        location_data = feedback.to_dict(include_details=True)
        locations.append(location_data)

    return jsonify({
        'locations': locations,
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_location_data_bp.route('/<int:feedback_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_location_data(feedback_id):
    """
    Get a specific location feedback by ID (admin only).

    Returns:
        {
            "location": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'location':
        return jsonify({'error': 'Location data not found'}), 404

    return jsonify({'location': feedback.to_dict(include_details=True)}), 200


@admin_location_data_bp.route('/<int:feedback_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_location_data(feedback_id):
    """
    Update location feedback status and admin notes (admin only).

    Request body:
        {
            "status": "reviewed" | "resolved" | "dismissed",
            "adminNotes": "Admin comments here..."
        }

    Returns:
        {
            "location": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'location':
        return jsonify({'error': 'Location data not found'}), 404

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

    current_app.logger.info(f'Admin updated location feedback: {feedback.id} (status: {feedback.status})')

    return jsonify({'location': feedback.to_dict(include_details=True)}), 200


@admin_location_data_bp.route('/<int:feedback_id>/approve', methods=['POST'])
@jwt_required()
@admin_required()
def approve_location_data(feedback_id):
    """
    Approve location data and add to site's user_submitted_locations (admin only).

    This endpoint will:
    1. Append [latitude, longitude] to site.user_submitted_locations array
    2. Mark feedback as resolved

    Returns:
        {
            "location": {...},
            "site": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'location':
        return jsonify({'error': 'Location data not found'}), 404

    if not feedback.site_id:
        return jsonify({'error': 'Location feedback has no associated site'}), 400

    if not hasattr(feedback, 'location_detail') or not feedback.location_detail:
        return jsonify({'error': 'Location feedback has no location data'}), 400

    # Get site
    site = Site.query.get(feedback.site_id)
    if not site:
        return jsonify({'error': 'Associated site not found'}), 404

    # Get location coordinates
    location_detail = feedback.location_detail
    new_location = [location_detail.latitude, location_detail.longitude]

    # Check if location already exists in array (avoid duplicates)
    if site.user_submitted_locations is None:
        site.user_submitted_locations = []

    # Check for duplicate (within small tolerance for floating point)
    is_duplicate = any(
        abs(loc[0] - new_location[0]) < 0.00001 and abs(loc[1] - new_location[1]) < 0.00001
        for loc in site.user_submitted_locations
    )

    if not is_duplicate:
        # Append new location
        site.user_submitted_locations = site.user_submitted_locations + [new_location]
        current_app.logger.info(f'Added location {new_location} to site {site.id}')

    # Mark feedback as resolved
    feedback.status = 'resolved'
    feedback.reviewed_at = datetime.utcnow()
    feedback.reviewed_by = int(get_jwt_identity())

    db.session.commit()

    current_app.logger.info(f'Admin approved location feedback: {feedback.id}')

    return jsonify({
        'location': feedback.to_dict(include_details=True),
        'site': {
            'id': str(site.id),
            'title': site.title,
            'userSubmittedLocations': site.user_submitted_locations,
            'locationCount': len(site.user_submitted_locations) if site.user_submitted_locations else 0
        }
    }), 200


@admin_location_data_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required()
def get_location_stats():
    """
    Get location data statistics by site (admin only).

    Query params:
        - site_id: Optional - filter stats for specific site

    Returns:
        {
            "stats": {
                "totalSubmissions": count,
                "bySite": [
                    {
                        "siteId": "uuid",
                        "siteTitle": "...",
                        "submissionCount": count,
                        "avgAccuracy": meters
                    }
                ]
            }
        }
    """
    site_id = request.args.get('site_id', '').strip()

    # Build query for site-level aggregations
    query = db.session.query(
        Feedback.site_id,
        func.count(FeedbackLocation.feedback_id).label('count'),
        func.avg(FeedbackLocation.accuracy).label('avg_accuracy')
    ).join(
        FeedbackLocation,
        Feedback.id == FeedbackLocation.feedback_id
    ).filter(
        Feedback.feedback_type == 'location'
    ).group_by(
        Feedback.site_id
    )

    if site_id:
        query = query.filter(Feedback.site_id == site_id)

    results = query.all()

    # Get total count
    total = db.session.query(func.count(FeedbackLocation.feedback_id)).join(
        Feedback,
        Feedback.id == FeedbackLocation.feedback_id
    ).filter(
        Feedback.feedback_type == 'location'
    ).scalar()

    # Format response with site details
    by_site = []
    for site_id, count, avg_accuracy in results:
        site = Site.query.get(site_id)
        by_site.append({
            'siteId': str(site_id),
            'siteTitle': site.title if site else 'Unknown',
            'submissionCount': count,
            'avgAccuracy': round(float(avg_accuracy), 2) if avg_accuracy else None
        })

    return jsonify({
        'stats': {
            'totalSubmissions': total,
            'bySite': by_site
        }
    }), 200


@admin_location_data_bp.route('/<int:feedback_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_location_data(feedback_id):
    """
    Delete location feedback (admin only).

    Returns:
        {
            "message": "Location data deleted successfully"
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'location':
        return jsonify({'error': 'Location data not found'}), 404

    db.session.delete(feedback)
    db.session.commit()

    current_app.logger.info(f'Admin deleted location feedback: {feedback_id}')

    return jsonify({
        'message': 'Location data deleted successfully'
    }), 200
