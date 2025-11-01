"""
Admin AI endpoints for prompt execution and trace management.
"""
from flask import Blueprint, request, jsonify, current_app, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from datetime import datetime
from app import db, limiter
from app.models.ai_trace import AITrace
from app.services.ai_service import ai_service
from app.utils.admin_required import admin_required

admin_ai_bp = Blueprint('admin_ai', __name__)


@admin_ai_bp.route('/generate-description', methods=['POST'])
@jwt_required()
@admin_required()
@limiter.limit("20 per hour", key_func=lambda: f"ai_generate_{get_jwt_identity()}")
def generate_description():
    """
    Generate a site description using AI (Grok with web search).

    Request body:
        {
            "siteName": "The Hoxton Hotel Williamsburg",
            "latitude": 40.7171,
            "longitude": -73.9619
        }

    Returns:
        {
            "description": "Generated description text...",
            "traceId": "uuid-here"
        }
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    site_name = data.get('siteName')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not site_name:
        return jsonify({'error': 'siteName is required'}), 400

    if latitude is None or longitude is None:
        return jsonify({'error': 'latitude and longitude are required'}), 400

    # Validate coordinates
    try:
        lat = float(latitude)
        lon = float(longitude)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid coordinate format'}), 400

    # Format location string
    location = f"{lat}, {lon}"

    try:
        # Execute the prompt
        result = ai_service.execute_prompt(
            prompt_name='generate_site_description_grok',
            variables={
                'site_name': site_name,
                'location': location
            },
            user_id=user_id
        )

        # Extract description from JSON response
        description = result.get('parsed', {}).get('description', result.get('response'))

        return jsonify({
            'description': description,
            'traceId': result['trace_id']
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f'Error generating description: {e}')
        return jsonify({'error': 'Failed to generate description'}), 500


@admin_ai_bp.route('/traces', methods=['GET'])
@jwt_required()
@admin_required()
def list_traces():
    """
    List all AI traces with filtering and pagination.

    Query params:
        - prompt_name: Filter by prompt name
        - provider: Filter by provider (openai, grok)
        - status: Filter by status (pending, success, error)
        - from_date: Filter traces created after this date (ISO format)
        - to_date: Filter traces created before this date (ISO format)
        - limit: Number of results (default: 50, max: 500)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "traces": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    prompt_name = request.args.get('prompt_name')
    provider = request.args.get('provider')
    status = request.args.get('status')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    limit = min(request.args.get('limit', 50, type=int), 500)
    offset = request.args.get('offset', 0, type=int)

    # Build query
    query = AITrace.query

    # Apply filters
    if prompt_name:
        query = query.filter(AITrace.prompt_name == prompt_name)

    if provider:
        query = query.filter(AITrace.provider == provider)

    if status:
        query = query.filter(AITrace.status == status)

    if from_date:
        try:
            from_datetime = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            query = query.filter(AITrace.created_at >= from_datetime)
        except ValueError:
            return jsonify({'error': 'Invalid from_date format. Use ISO format.'}), 400

    if to_date:
        try:
            to_datetime = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            query = query.filter(AITrace.created_at <= to_datetime)
        except ValueError:
            return jsonify({'error': 'Invalid to_date format. Use ISO format.'}), 400

    # Get total count
    total = query.count()

    # Execute query with pagination
    traces = query.order_by(AITrace.created_at.desc()).limit(limit).offset(offset).all()

    return jsonify({
        'traces': [trace.to_dict(include_raw=False) for trace in traces],
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_ai_bp.route('/traces/<uuid:trace_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_trace(trace_id):
    """
    Get detailed information about a specific AI trace.

    Returns:
        {
            "trace": {
                "id": "uuid",
                "promptName": "...",
                "provider": "...",
                "model": "...",
                "systemPrompt": "...",
                "userPrompt": "...",
                "response": "...",
                "rawRequest": {...},
                "rawResponse": {...},
                "metadata": {...},
                "status": "...",
                "errorMessage": "...",
                "userId": 123,
                "createdAt": "...",
                "completedAt": "..."
            }
        }
    """
    trace = AITrace.query.get(trace_id)

    if not trace:
        return jsonify({'error': 'Trace not found'}), 404

    return jsonify({
        'trace': trace.to_dict(include_raw=True)
    }), 200


@admin_ai_bp.route('/traces/stats', methods=['GET'])
@jwt_required()
@admin_required()
def get_trace_stats():
    """
    Get statistics about AI traces.

    Returns:
        {
            "totalTraces": count,
            "byProvider": {"openai": count, "grok": count},
            "byStatus": {"success": count, "error": count, "pending": count},
            "byPromptName": {"prompt1": count, "prompt2": count}
        }
    """
    # Total traces
    total = AITrace.query.count()

    # By provider
    from sqlalchemy import func
    provider_stats = db.session.query(
        AITrace.provider,
        func.count(AITrace.id)
    ).group_by(AITrace.provider).all()
    by_provider = {provider: count for provider, count in provider_stats}

    # By status
    status_stats = db.session.query(
        AITrace.status,
        func.count(AITrace.id)
    ).group_by(AITrace.status).all()
    by_status = {status: count for status, count in status_stats}

    # By prompt name
    prompt_stats = db.session.query(
        AITrace.prompt_name,
        func.count(AITrace.id)
    ).group_by(AITrace.prompt_name).all()
    by_prompt_name = {prompt: count for prompt, count in prompt_stats}

    return jsonify({
        'totalTraces': total,
        'byProvider': by_provider,
        'byStatus': by_status,
        'byPromptName': by_prompt_name
    }), 200
