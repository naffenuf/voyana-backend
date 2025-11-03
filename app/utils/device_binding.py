"""
Device binding authentication decorator.

Ensures JWT tokens can only be used from the device that registered them,
preventing token theft and sharing.
"""
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def get_device_id_for_rate_limit():
    """
    Helper function to extract device ID for rate limiting.

    Returns the device_id from the X-Device-ID header if present,
    otherwise falls back to remote IP address.

    This allows per-device rate limiting instead of per-IP limiting.
    """
    device_id = request.headers.get('X-Device-ID')
    if device_id:
        return f"device:{device_id}"
    return f"ip:{request.remote_addr}"


def device_binding_required():
    """
    Decorator that verifies the JWT's device_id matches the X-Device-ID header.

    This prevents stolen or shared JWT tokens from working on unauthorized devices.
    Only applies to device-type tokens (not user-type tokens).

    Usage:
        @tours_bp.route('', methods=['GET'])
        @device_binding_required()
        def get_tours():
            # ... endpoint logic
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verify JWT is present and valid
            verify_jwt_in_request()
            claims = get_jwt()

            # Only check device-type tokens (skip user tokens)
            if claims.get('type') == 'device':
                token_device_id = claims.get('device_id')
                header_device_id = request.headers.get('X-Device-ID')

                # Require matching device ID
                if not header_device_id:
                    return jsonify({
                        'error': 'Device ID required',
                        'message': 'X-Device-ID header is required for device authentication'
                    }), 400

                if token_device_id != header_device_id:
                    return jsonify({
                        'error': 'Device mismatch',
                        'message': 'This token cannot be used from this device'
                    }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator
