"""
Feedback API endpoints.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from sqlalchemy import func
from datetime import datetime
from app import db, limiter
from app.models.feedback import Feedback
from app.models.feedback_issue import FeedbackIssue
from app.models.feedback_photo import FeedbackPhoto
from app.models.feedback_location import FeedbackLocation
from app.models.tour import Tour
from app.models.site import Site

feedback_bp = Blueprint('feedback', __name__)


@feedback_bp.route('', methods=['POST'])
@limiter.limit("50 per hour", key_func=lambda: get_jwt_identity() if verify_jwt_in_request(optional=True) else request.remote_addr)
def submit_feedback():
    """
    Submit feedback for a tour or site.

    Request body depends on feedback type:

    Rating:
        {
            "feedbackType": "rating",
            "tourId": "uuid-string",
            "rating": 1-5,
            "comment": "optional comment"
        }

    Issue:
        {
            "feedbackType": "issue",
            "tourId": "uuid-string",
            "siteId": "uuid-string" (optional),
            "title": "Issue category",
            "description": "Details" (optional),
            "severity": "low|medium|high" (optional)
        }

    Photo:
        {
            "feedbackType": "photo",
            "tourId": "uuid-string",
            "siteId": "uuid-string" (required),
            "photoData": "base64-encoded-image",
            "caption": "Optional description"
        }

    Location:
        {
            "feedbackType": "location",
            "tourId": "uuid-string",
            "siteId": "uuid-string" (required),
            "latitude": 40.7589,
            "longitude": -73.9851,
            "accuracy": 10.5 (optional),
            "recordedAt": "ISO timestamp" (optional)
        }

    Suggestion:
        {
            "feedbackType": "suggestion",
            "tourId": "uuid-string",
            "siteId": "uuid-string" (required),
            "comment": "User-provided details or improvements for site description"
        }

    Returns:
        {
            "message": "Feedback submitted successfully",
            "feedbackId": 123,
            ... type-specific response data ...
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Get feedback type
    feedback_type = data.get('feedbackType', 'rating')  # Default to rating for backward compat
    if feedback_type not in ['rating', 'issue', 'photo', 'location', 'suggestion']:
        return jsonify({'error': f'Invalid feedbackType: {feedback_type}'}), 400

    # tourId is required for all types
    if 'tourId' not in data:
        return jsonify({'error': 'tourId is required'}), 400

    tour_id = data['tourId']
    site_id = data.get('siteId')

    # Validate tour exists
    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Validate site if provided
    site = None
    if site_id:
        site = Site.query.get(site_id)
        if not site:
            return jsonify({'error': 'Site not found'}), 404

    # Get user ID if authenticated (optional - allow anonymous)
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            user_id = int(identity)
    except Exception:
        pass  # Anonymous feedback allowed

    try:
        # Handle each feedback type
        if feedback_type == 'rating':
            return _handle_rating_feedback(data, tour_id, user_id, tour)
        elif feedback_type == 'issue':
            return _handle_issue_feedback(data, tour_id, site_id, user_id)
        elif feedback_type == 'photo':
            return _handle_photo_feedback(data, tour_id, site_id, user_id, site)
        elif feedback_type == 'location':
            return _handle_location_feedback(data, tour_id, site_id, user_id, site)
        elif feedback_type == 'suggestion':
            return _handle_suggestion_feedback(data, tour_id, site_id, user_id, site)

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to submit feedback: {str(e)}'}), 500


def _handle_rating_feedback(data, tour_id, user_id, tour):
    """Handle rating feedback submission."""
    if 'rating' not in data:
        raise ValueError('rating is required for rating feedback')

    rating = data['rating']
    comment = data.get('comment')

    # Validate rating range
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError('rating must be an integer between 1 and 5')

    # Check for duplicate rating from same user
    if user_id:
        existing_feedback = Feedback.query.filter_by(
            tour_id=tour_id,
            user_id=user_id,
            feedback_type='rating'
        ).first()

        if existing_feedback:
            raise ValueError('You have already rated this tour')

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
        'feedbackId': feedback.id,
        'tourRating': {
            'averageRating': tour.average_rating,
            'ratingCount': tour.rating_count
        }
    }), 201


def _handle_issue_feedback(data, tour_id, site_id, user_id):
    """Handle issue feedback submission."""
    if 'title' not in data:
        raise ValueError('title is required for issue feedback')

    title = data['title']
    description = data.get('description')
    severity = data.get('severity')

    # Strip empty strings to None
    if description and description.strip() == '':
        description = None

    # Validate severity if provided
    if severity and severity not in ['low', 'medium', 'high']:
        raise ValueError('severity must be low, medium, or high')

    # Create feedback record
    feedback = Feedback(
        tour_id=tour_id,
        site_id=site_id,  # Optional
        user_id=user_id,
        feedback_type='issue',
        status='pending'
    )

    db.session.add(feedback)
    db.session.flush()  # Get feedback.id

    # Create issue detail
    issue_detail = FeedbackIssue(
        feedback_id=feedback.id,
        title=title,
        description=description,
        severity=severity
    )

    db.session.add(issue_detail)
    db.session.commit()

    return jsonify({
        'message': 'Issue reported successfully',
        'feedbackId': feedback.id
    }), 201


def _handle_photo_feedback(data, tour_id, site_id, user_id, site):
    """Handle photo feedback submission."""
    if not site_id:
        raise ValueError('siteId is required for photo feedback')

    if 'photoData' not in data:
        raise ValueError('photoData is required for photo feedback')

    photo_data = data['photoData']
    caption = data.get('caption')

    # Strip empty strings to None
    if caption and caption.strip() == '':
        caption = None

    # Create feedback record
    feedback = Feedback(
        tour_id=tour_id,
        site_id=site_id,
        user_id=user_id,
        feedback_type='photo',
        photo_data=photo_data,  # Store temporarily in feedback table
        status='pending'
    )

    db.session.add(feedback)
    db.session.flush()  # Get feedback.id

    # Create photo detail
    photo_detail = FeedbackPhoto(
        feedback_id=feedback.id,
        caption=caption
        # photo_url will be set when admin approves
    )

    db.session.add(photo_detail)
    db.session.commit()

    return jsonify({
        'message': 'Photo submitted successfully',
        'feedbackId': feedback.id
    }), 201


def _handle_location_feedback(data, tour_id, site_id, user_id, site):
    """Handle location feedback submission."""
    if not site_id:
        raise ValueError('siteId is required for location feedback')

    if 'latitude' not in data or 'longitude' not in data:
        raise ValueError('latitude and longitude are required for location feedback')

    latitude = data['latitude']
    longitude = data['longitude']
    accuracy = data.get('accuracy')
    recorded_at_str = data.get('recordedAt')

    # Parse timestamp
    recorded_at = datetime.utcnow()
    if recorded_at_str:
        try:
            recorded_at = datetime.fromisoformat(recorded_at_str.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('Invalid recordedAt timestamp format')

    # Validate coordinates
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError('latitude and longitude must be numbers')

    if latitude < -90 or latitude > 90:
        raise ValueError('latitude must be between -90 and 90')

    if longitude < -180 or longitude > 180:
        raise ValueError('longitude must be between -180 and 180')

    if accuracy is not None and (not isinstance(accuracy, (int, float)) or accuracy <= 0):
        raise ValueError('accuracy must be a positive number')

    # Create feedback record
    feedback = Feedback(
        tour_id=tour_id,
        site_id=site_id,
        user_id=user_id,
        feedback_type='location',
        status='pending'
    )

    db.session.add(feedback)
    db.session.flush()  # Get feedback.id

    # Create location detail
    location_detail = FeedbackLocation(
        feedback_id=feedback.id,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        recorded_at=recorded_at
    )

    db.session.add(location_detail)
    db.session.commit()

    return jsonify({
        'message': 'Location data submitted successfully',
        'feedbackId': feedback.id
    }), 201


def _handle_suggestion_feedback(data, tour_id, site_id, user_id, site):
    """Handle suggestion feedback submission (site details/description improvements)."""
    if not site_id:
        raise ValueError('siteId is required for suggestion feedback')

    if 'comment' not in data:
        raise ValueError('comment is required for suggestion feedback')

    comment = data['comment']

    # Validate comment is not empty
    if not comment or comment.strip() == '':
        raise ValueError('comment cannot be empty')

    # Create feedback record
    feedback = Feedback(
        tour_id=tour_id,
        site_id=site_id,
        user_id=user_id,
        feedback_type='suggestion',
        comment=comment,  # Store suggestion text in comment field
        status='pending'
    )

    db.session.add(feedback)
    db.session.commit()

    return jsonify({
        'message': 'Suggestion submitted successfully',
        'feedbackId': feedback.id
    }), 201
