"""
Admin feedback management endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from datetime import datetime
from app import db
from app.models.feedback import Feedback
from app.utils.admin_required import admin_required

admin_feedback_bp = Blueprint('admin_feedback', __name__)


@admin_feedback_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_feedback():
    """
    List all feedback with optional filters (admin only).

    Query params:
        - status: Filter by status (pending, reviewed, resolved, dismissed)
        - feedback_type: Filter by type (issue, rating, comment, suggestion)
        - tour_id: Filter by tour ID
        - site_id: Filter by site ID
        - limit: Number of results (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "feedback": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    status = request.args.get('status', '').strip()
    feedback_type = request.args.get('feedback_type', '').strip()
    tour_id = request.args.get('tour_id', '').strip()
    site_id = request.args.get('site_id', '').strip()
    limit = min(request.args.get('limit', 100, type=int), 500)  # Cap at 500
    offset = request.args.get('offset', 0, type=int)

    # Build query
    query = Feedback.query

    # Status filter
    if status:
        query = query.filter(Feedback.status == status)

    # Feedback type filter
    if feedback_type:
        query = query.filter(Feedback.feedback_type == feedback_type)

    # Tour filter
    if tour_id:
        query = query.filter(Feedback.tour_id == tour_id)

    # Site filter
    if site_id:
        query = query.filter(Feedback.site_id == site_id)

    # Get total count
    total = query.count()

    # Execute query with pagination (most recent first)
    feedback_items = query.order_by(Feedback.created_at.desc()).limit(limit).offset(offset).all()

    return jsonify({
        'feedback': [item.to_dict() for item in feedback_items],
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_feedback_bp.route('/<int:feedback_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_feedback(feedback_id):
    """
    Get a specific feedback item by ID (admin only).

    Returns:
        {
            "feedback": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({'error': 'Feedback not found'}), 404

    return jsonify({'feedback': feedback.to_dict()}), 200


@admin_feedback_bp.route('/<int:feedback_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_feedback(feedback_id):
    """
    Update feedback status and admin notes (admin only).

    Request body:
        {
            "status": "reviewed" | "resolved" | "dismissed",
            "adminNotes": "Admin comments here..."
        }

    Returns:
        {
            "feedback": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({'error': 'Feedback not found'}), 404

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

        # Set reviewed timestamp if changing from pending to reviewed/resolved/dismissed
        if old_status == 'pending' and new_status != 'pending':
            feedback.reviewed_at = datetime.utcnow()
            feedback.reviewed_by = int(get_jwt_identity())

    # Update admin notes
    if 'adminNotes' in data:
        feedback.admin_notes = data['adminNotes']

    db.session.commit()

    current_app.logger.info(f'Admin updated feedback: {feedback.id} (status: {feedback.status})')

    return jsonify({'feedback': feedback.to_dict()}), 200


@admin_feedback_bp.route('/<int:feedback_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_feedback(feedback_id):
    """
    Delete a feedback item (admin only).

    Returns:
        {
            "message": "Feedback deleted successfully"
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback:
        return jsonify({'error': 'Feedback not found'}), 404

    db.session.delete(feedback)
    db.session.commit()

    current_app.logger.info(f'Admin deleted feedback: {feedback_id}')

    return jsonify({
        'message': 'Feedback deleted successfully'
    }), 200


@admin_feedback_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required()
def get_feedback_stats():
    """
    Get feedback statistics (admin only).

    Returns:
        {
            "stats": {
                "total": count,
                "byStatus": {...},
                "byType": {...},
                "averageRating": float
            }
        }
    """
    # Total count
    total = Feedback.query.count()

    # Count by status
    by_status = {}
    for status in ['pending', 'reviewed', 'resolved', 'dismissed']:
        by_status[status] = Feedback.query.filter_by(status=status).count()

    # Count by type
    by_type = {}
    for feedback_type in ['issue', 'rating', 'comment', 'suggestion']:
        by_type[feedback_type] = Feedback.query.filter_by(feedback_type=feedback_type).count()

    # Average rating
    ratings = db.session.query(db.func.avg(Feedback.rating)).filter(
        Feedback.rating.isnot(None)
    ).scalar()
    average_rating = round(float(ratings), 2) if ratings else None

    return jsonify({
        'stats': {
            'total': total,
            'byStatus': by_status,
            'byType': by_type,
            'averageRating': average_rating
        }
    }), 200
