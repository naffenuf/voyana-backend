"""
Tests for Feedback API endpoints.
"""
import pytest
import json
from app.models.feedback import Feedback
from app import db


class TestSubmitFeedback:
    """Tests for POST /api/feedback endpoint."""

    def test_submit_feedback_for_tour(self, client, test_tour):
        """Test submitting feedback for a tour."""
        response = client.post('/api/feedback', json={
            'tourId': str(test_tour.id),
            'feedbackType': 'rating',
            'rating': 5,
            'comment': 'Amazing tour!'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'id' in data
        assert data['rating'] == 5

    def test_submit_feedback_for_site(self, client, test_site):
        """Test submitting feedback for a site."""
        response = client.post('/api/feedback', json={
            'siteId': str(test_site.id),
            'feedbackType': 'comment',
            'comment': 'Great location!'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'id' in data

    def test_submit_feedback_anonymous(self, client, test_tour):
        """Test submitting anonymous feedback."""
        response = client.post('/api/feedback', json={
            'tourId': str(test_tour.id),
            'feedbackType': 'rating',
            'rating': 4,
            'comment': 'Good tour'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'id' in data

    def test_submit_feedback_authenticated(self, client, auth_headers, test_tour):
        """Test submitting feedback while authenticated."""
        response = client.post('/api/feedback', headers=auth_headers, json={
            'tourId': str(test_tour.id),
            'feedbackType': 'suggestion',
            'comment': 'Could add more historical context'
        })

        assert response.status_code == 201

    def test_submit_feedback_missing_target(self, client):
        """Test submitting feedback without tour or site ID."""
        response = client.post('/api/feedback', json={
            'feedbackType': 'comment',
            'comment': 'Some feedback'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_submit_feedback_invalid_rating(self, client, test_tour):
        """Test submitting feedback with invalid rating."""
        response = client.post('/api/feedback', json={
            'tourId': str(test_tour.id),
            'feedbackType': 'rating',
            'rating': 10  # Invalid, should be 1-5
        })

        assert response.status_code == 400


class TestAdminFeedbackManagement:
    """Tests for admin feedback management endpoints."""

    def test_list_all_feedback(self, app, client, admin_headers, test_tour):
        """Test listing all feedback as admin."""
        with app.app_context():
            # Create some feedback
            feedback1 = Feedback(
                tour_id=test_tour.id,
                feedback_type='rating',
                rating=5,
                comment='Great'
            )
            feedback2 = Feedback(
                tour_id=test_tour.id,
                feedback_type='issue',
                comment='Problem here'
            )
            db.session.add(feedback1)
            db.session.add(feedback2)
            db.session.commit()

        response = client.get('/api/admin/feedback', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'feedback' in data
        assert len(data['feedback']) >= 2

    def test_list_feedback_requires_admin(self, client, auth_headers):
        """Test that listing feedback requires admin role."""
        response = client.get('/api/admin/feedback', headers=auth_headers)

        assert response.status_code in [403, 401]

    def test_get_specific_feedback(self, app, client, admin_headers, test_tour):
        """Test getting a specific feedback item."""
        with app.app_context():
            feedback = Feedback(
                tour_id=test_tour.id,
                feedback_type='rating',
                rating=4
            )
            db.session.add(feedback)
            db.session.commit()
            feedback_id = feedback.id

        response = client.get(f'/api/admin/feedback/{feedback_id}', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == feedback_id

    def test_update_feedback_status(self, app, client, admin_headers, test_tour):
        """Test updating feedback status."""
        with app.app_context():
            feedback = Feedback(
                tour_id=test_tour.id,
                feedback_type='issue',
                comment='Problem',
                status='pending'
            )
            db.session.add(feedback)
            db.session.commit()
            feedback_id = feedback.id

        response = client.put(
            f'/api/admin/feedback/{feedback_id}',
            headers=admin_headers,
            json={'status': 'resolved', 'adminNotes': 'Fixed the issue'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'resolved'

    def test_delete_feedback(self, app, client, admin_headers, test_tour):
        """Test deleting feedback."""
        with app.app_context():
            feedback = Feedback(
                tour_id=test_tour.id,
                feedback_type='comment',
                comment='Test'
            )
            db.session.add(feedback)
            db.session.commit()
            feedback_id = feedback.id

        response = client.delete(f'/api/admin/feedback/{feedback_id}', headers=admin_headers)

        assert response.status_code == 200

        # Verify deleted
        with app.app_context():
            deleted = Feedback.query.get(feedback_id)
            assert deleted is None

    def test_get_feedback_stats(self, app, client, admin_headers, test_tour):
        """Test getting feedback statistics."""
        with app.app_context():
            # Create feedback with different ratings
            for rating in [5, 4, 5, 3, 5]:
                feedback = Feedback(
                    tour_id=test_tour.id,
                    feedback_type='rating',
                    rating=rating
                )
                db.session.add(feedback)
            db.session.commit()

        response = client.get('/api/admin/feedback/stats', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'totalFeedback' in data or 'averageRating' in data
