"""
Admin-only API endpoints.
"""
from flask import Blueprint
from .users import admin_users_bp
from .feedback import admin_feedback_bp
from .upload import admin_upload_bp
from .tours import admin_tours_bp

# Create main admin blueprint
admin_bp = Blueprint('admin', __name__)

# Register sub-blueprints
admin_bp.register_blueprint(admin_users_bp, url_prefix='/users')
admin_bp.register_blueprint(admin_feedback_bp, url_prefix='/feedback')
admin_bp.register_blueprint(admin_upload_bp, url_prefix='/upload')
admin_bp.register_blueprint(admin_tours_bp, url_prefix='/tours')
