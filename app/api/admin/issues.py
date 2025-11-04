"""
Admin API endpoints for issue feedback management.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models.feedback import Feedback
from app.models.feedback_issue import FeedbackIssue
from app.utils.admin_required import admin_required

admin_issues_bp = Blueprint('admin_issues', __name__)


@admin_issues_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_issues():
    """
    List all issue feedback with optional filters (admin only).

    Query params:
        - status: Filter by status (pending, reviewed, resolved, dismissed)
        - severity: Filter by severity (low, medium, high)
        - tour_id: Filter by tour ID
        - site_id: Filter by site ID
        - limit: Number of results (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "issues": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    status = request.args.get('status', '').strip()
    severity = request.args.get('severity', '').strip()
    tour_id = request.args.get('tour_id', '').strip()
    site_id = request.args.get('site_id', '').strip()
    limit = min(request.args.get('limit', 100, type=int), 500)  # Cap at 500
    offset = request.args.get('offset', 0, type=int)

    # Build query - join feedback with issue details
    query = db.session.query(Feedback, FeedbackIssue).join(
        FeedbackIssue,
        Feedback.id == FeedbackIssue.feedback_id
    ).filter(
        Feedback.feedback_type == 'issue'
    )

    # Apply filters
    if status:
        query = query.filter(Feedback.status == status)

    if severity:
        query = query.filter(FeedbackIssue.severity == severity)

    if tour_id:
        query = query.filter(Feedback.tour_id == tour_id)

    if site_id:
        query = query.filter(Feedback.site_id == site_id)

    # Get total count
    total = query.count()

    # Execute query with pagination (most recent first)
    results = query.order_by(Feedback.created_at.desc()).limit(limit).offset(offset).all()

    # Format response
    issues = []
    for feedback, issue_detail in results:
        issue_data = feedback.to_dict(include_details=True)
        issues.append(issue_data)

    return jsonify({
        'issues': issues,
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_issues_bp.route('/<int:feedback_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_issue(feedback_id):
    """
    Get a specific issue feedback by ID (admin only).

    Returns:
        {
            "issue": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'issue':
        return jsonify({'error': 'Issue not found'}), 404

    return jsonify({'issue': feedback.to_dict(include_details=True)}), 200


@admin_issues_bp.route('/<int:feedback_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_issue(feedback_id):
    """
    Update issue status and admin notes (admin only).

    Request body:
        {
            "status": "reviewed" | "resolved" | "dismissed",
            "adminNotes": "Admin comments here..."
        }

    Returns:
        {
            "issue": {...}
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'issue':
        return jsonify({'error': 'Issue not found'}), 404

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

    current_app.logger.info(f'Admin updated issue feedback: {feedback.id} (status: {feedback.status})')

    return jsonify({'issue': feedback.to_dict(include_details=True)}), 200


@admin_issues_bp.route('/<int:feedback_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_issue(feedback_id):
    """
    Delete an issue feedback (admin only).

    Returns:
        {
            "message": "Issue deleted successfully"
        }
    """
    feedback = Feedback.query.get(feedback_id)

    if not feedback or feedback.feedback_type != 'issue':
        return jsonify({'error': 'Issue not found'}), 404

    db.session.delete(feedback)
    db.session.commit()

    current_app.logger.info(f'Admin deleted issue feedback: {feedback_id}')

    return jsonify({
        'message': 'Issue deleted successfully'
    }), 200
