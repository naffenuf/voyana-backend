"""
Role-based rate limiting utilities.

Flask-Limiter supports dynamic limits via callable functions.
These utilities provide role-based rate limiting for audio generation endpoints.
"""
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request


def get_audio_rate_limit_key():
    """
    Generate a unique rate limit key for audio generation based on user identity.

    Returns:
        str: Rate limit key in format "audio_generation_{user_id}"
    """
    user_id = get_jwt_identity()
    return f"audio_generation_{user_id}"


def get_user_audio_limit():
    """
    Get the appropriate audio generation rate limit for the current user based on role.

    Limits:
    - Admins: 200 requests per day
    - Creators: 20 requests per day

    This function is designed to be used as a dynamic limit with Flask-Limiter:
        @limiter.limit(get_user_audio_limit, key_func=get_audio_rate_limit_key)

    Returns:
        str: Rate limit string (e.g., "200 per day" or "20 per day")
    """
    try:
        # Ensure JWT is verified (should already be done by @jwt_required or @device_binding_required)
        verify_jwt_in_request(optional=True)

        # Get JWT claims to check role
        claims = get_jwt()
        user_role = claims.get('role', 'creator')  # Default to creator if no role

        # Return limit based on role
        if user_role == 'admin':
            return "200 per day"
        else:
            # Creators and any other role
            return "20 per day"

    except Exception:
        # If JWT verification fails or claims not available, default to creator limit
        return "20 per day"
