"""
Admin-only API endpoints.
"""
from flask import Blueprint
from .users import admin_users_bp
from .feedback import admin_feedback_bp
from .upload import admin_upload_bp
from .tours import admin_tours_bp
from .ai import admin_ai_bp
from .neighborhoods import admin_neighborhoods_bp
from .cities import admin_cities_bp
from .api_keys import api_keys_bp

# Create main admin blueprint
admin_bp = Blueprint('admin', __name__)

# Register sub-blueprints
admin_bp.register_blueprint(admin_users_bp, url_prefix='/users')
admin_bp.register_blueprint(admin_feedback_bp, url_prefix='/feedback')
admin_bp.register_blueprint(admin_upload_bp, url_prefix='/upload')
admin_bp.register_blueprint(admin_tours_bp, url_prefix='/tours')
admin_bp.register_blueprint(admin_ai_bp, url_prefix='/ai')
admin_bp.register_blueprint(admin_neighborhoods_bp, url_prefix='/neighborhoods')
admin_bp.register_blueprint(admin_cities_bp, url_prefix='/cities')
admin_bp.register_blueprint(api_keys_bp, url_prefix='/api-keys')
