"""
Feedback API endpoints.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from sqlalchemy import func
from app import db
from app.models.feedback import Feedback
from app.models.tour import Tour

feedback_bp = Blueprint('feedback', __name__)


@feedback_bp.route('', methods=['POST'])
def submit_feedback():
    """
    Submit feedback/rating for a tour.

    Request body:
        {
            "tourId": "uuid-string",
            "rating": 1-5,
            "comment": "optional comment"
        }

    Returns:
        {
            "message": "Feedback submitted successfully",
            "tourRating": {
                "averageRating": 4.5,
                "ratingCount": 42
            }
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate required fields
    if 'tourId' not in data:
        return jsonify({'error': 'tourId is required'}), 400

    if 'rating' not in data:
        return jsonify({'error': 'rating is required'}), 400

    tour_id = data['tourId']
    rating = data['rating']
    comment = data.get('comment')

    # Validate rating range
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'rating must be an integer between 1 and 5'}), 400

    # Check if tour exists
    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Get user ID if authenticated (optional - allow anonymous)
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            user_id = int(identity)
    except Exception:
        pass  # Anonymous feedback allowed

    # Check for duplicate rating from same user
    if user_id:
        existing_feedback = Feedback.query.filter_by(
            tour_id=tour_id,
            user_id=user_id,
            feedback_type='rating'
        ).first()

        if existing_feedback:
            return jsonify({'error': 'You have already rated this tour'}), 409

    # Create feedback record
    feedback = Feedback(
        tour_id=tour_id,
        user_id=user_id,
        feedback_type='rating',
        rating=rating,
        comment=comment,
        status='pending'
    )

    db.session.add(feedback)

    # Update tour aggregate rating
    # Calculate new average and count
    rating_feedbacks = Feedback.query.filter_by(
        tour_id=tour_id,
        feedback_type='rating'
    ).with_entities(
        func.avg(Feedback.rating).label('avg_rating'),
        func.count(Feedback.id).label('count')
    ).first()

    if rating_feedbacks.count > 0:
        tour.average_rating = round(float(rating_feedbacks.avg_rating), 2)
        tour.rating_count = rating_feedbacks.count

    db.session.commit()

    return jsonify({
        'message': 'Feedback submitted successfully',
        'tourRating': {
            'averageRating': tour.average_rating,
            'ratingCount': tour.rating_count
        }
    }), 201
