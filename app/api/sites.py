"""
Sites API endpoints.
"""
from flask import Blueprint

sites_bp = Blueprint('sites', __name__)


@sites_bp.route('', methods=['GET'])
def list_sites():
    """List all sites."""
    return {'sites': []}, 200


# TODO: Implement remaining CRUD endpoints
