"""
Background Jobs API endpoints.
"""
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.background_job import BackgroundJob

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/<uuid:job_id>', methods=['GET'])
@jwt_required()
def get_job_status(job_id):
    """
    Get the status of a background job.

    Args:
        job_id: UUID of the background job

    Returns:
        {
            "id": "uuid",
            "jobType": "tour_audio_generation",
            "status": "pending" | "started" | "success" | "failed",
            "progress": 0-100,
            "progressMessage": "Processing site 3/10: Site Name",
            "result": {...},  // Only present when status is 'success'
            "errorMessage": "...",  // Only present when status is 'failed'
            "createdAt": "ISO8601",
            "startedAt": "ISO8601",
            "completedAt": "ISO8601"
        }
    """
    user_id = get_jwt_identity()

    try:
        # Get the job
        job = BackgroundJob.query.get(job_id)

        if not job:
            return jsonify({'error': 'Job not found'}), 404

        # Check if user has permission to view this job
        if job.user_id != user_id:
            # Allow admins to view any job
            from app.models.user import User
            user = User.query.get(user_id)
            if not user or user.role != 'admin':
                return jsonify({'error': 'You do not have permission to view this job'}), 403

        return jsonify(job.to_dict()), 200

    except Exception as e:
        current_app.logger.error(f'Error getting job status: {e}', exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@jobs_bp.route('', methods=['GET'])
@jwt_required()
def list_user_jobs():
    """
    List all background jobs for the current user.

    Query parameters:
        - status: Filter by status (pending, started, success, failed)
        - job_type: Filter by job type
        - limit: Max number of results (default: 50, max: 100)
        - offset: Pagination offset (default: 0)

    Returns:
        {
            "jobs": [...],
            "total": 123,
            "limit": 50,
            "offset": 0
        }
    """
    from flask import request
    user_id = get_jwt_identity()

    try:
        # Parse query parameters
        status = request.args.get('status')
        job_type = request.args.get('job_type')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))

        # Build query
        query = BackgroundJob.query.filter_by(user_id=user_id)

        if status:
            query = query.filter_by(status=status)
        if job_type:
            query = query.filter_by(job_type=job_type)

        # Get total count
        total = query.count()

        # Get paginated results, ordered by creation date (newest first)
        jobs = query.order_by(BackgroundJob.created_at.desc()).limit(limit).offset(offset).all()

        return jsonify({
            'jobs': [job.to_dict() for job in jobs],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200

    except ValueError as e:
        return jsonify({'error': f'Invalid query parameter: {str(e)}'}), 400
    except Exception as e:
        current_app.logger.error(f'Error listing jobs: {e}', exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500
