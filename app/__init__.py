"""
Flask application factory.
"""
import os
import logging
from flask import Flask, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, jwt_required
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import text

# Initialize extensions (without app instance)
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(
    key_func=lambda: g.get('current_user', {}).get('id') if hasattr(g, 'current_user') and g.current_user else get_remote_address(),
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://"
)


def register_jwt_callbacks(app):
    """Register JWT callbacks for device validation."""
    from flask_jwt_extended import get_jwt
    from app.models.device import DeviceRegistration

    @jwt.additional_claims_loader
    def add_claims_to_access_token(identity):
        """Add additional claims to JWT token."""
        # Claims are already added when token is created
        # This is just a placeholder for future claims
        return {}

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """
        Check if JWT token should be revoked (device not active).

        This callback is called for every @jwt_required() endpoint.
        Return True to block the token, False to allow it.
        """
        # Get device_id from JWT claims
        device_id = jwt_payload.get('device_id')

        if not device_id:
            # Token doesn't have device_id claim (old token or user token)
            # Allow it for backward compatibility
            return False

        # Check if device is registered and active
        is_active = DeviceRegistration.is_device_active(device_id)

        if not is_active:
            app.logger.warning(f'Token blocked: device {device_id} not active')
            return True  # Block the token

        # Update last_used_at timestamp for active devices
        DeviceRegistration.update_last_used(device_id)

        return False  # Allow the token

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        """Handle expired JWT tokens."""
        return jsonify({
            'error': 'Token has expired',
            'code': 'token_expired'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Handle invalid JWT tokens (including failed device verification)."""
        return jsonify({
            'error': 'Invalid token or device not authorized',
            'code': 'invalid_token'
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Handle missing JWT tokens."""
        return jsonify({
            'error': 'Authorization token is missing',
            'code': 'missing_token'
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """Handle revoked JWT tokens (device not active)."""
        return jsonify({
            'error': 'Device not authorized or has been deactivated',
            'code': 'device_revoked'
        }), 401


def create_app(config_name='development'):
    """
    Application factory pattern.

    Args:
        config_name: 'development', 'production', or 'testing'

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    CORS(app)

    # Register JWT callbacks for device validation
    register_jwt_callbacks(app)

    # Configure logging
    setup_logging(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register CLI commands
    register_cli_commands(app)

    return app


def setup_logging(app):
    """Configure application logging to stdout (cloud-friendly)."""
    # Remove default handlers
    app.logger.handlers.clear()

    # Create stdout handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO if app.config['ENV'] == 'production' else logging.DEBUG)

    # Set format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)

    # Add handler to app logger
    app.logger.addHandler(handler)
    app.logger.setLevel(handler.level)

    # Also configure root logger
    logging.basicConfig(
        level=handler.level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[handler]
    )


def register_blueprints(app):
    """Register Flask blueprints."""
    from app.api.auth import auth_bp
    from app.api.tours import tours_bp
    from app.api.sites import sites_bp
    from app.api.media import media_bp
    from app.api.maps import maps_bp
    from app.api.feedback import feedback_bp
    from app.api.admin import admin_bp
    from app.api.places import places_bp
    from app.api.neighborhoods import neighborhoods_bp

    # API blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tours_bp, url_prefix='/api/tours')
    app.register_blueprint(sites_bp, url_prefix='/api/sites')
    app.register_blueprint(media_bp, url_prefix='/api/media')
    app.register_blueprint(maps_bp, url_prefix='/api/maps')
    app.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    app.register_blueprint(neighborhoods_bp, url_prefix='/api/neighborhoods')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(places_bp)

    # Health check endpoint (no prefix)
    @app.route('/api/health')
    def health_check():
        """Health check for load balancers."""
        try:
            # Check database connection (SQLAlchemy 2.0 requires text() wrapper)
            db.session.execute(text('SELECT 1'))
            return jsonify({
                'status': 'healthy',
                'database': 'connected'
            }), 200
        except Exception as e:
            app.logger.error(f'Health check failed: {e}')
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 503

    # Remote config endpoint (no authentication required)
    @app.route('/api/config', methods=['GET'])
    def get_config():
        """Return remote configuration for mobile apps."""
        import os
        import json

        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'remote-config.json')

        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return jsonify(config_data), 200
        except FileNotFoundError:
            app.logger.error(f"Config file not found at: {config_path}")
            return jsonify({'error': 'Config file not found'}), 404
        except Exception as e:
            app.logger.error(f"Error reading remote-config.json: {e}")
            return jsonify({'error': 'Error reading config', 'details': str(e)}), 500

    # Text-to-speech endpoint (legacy compatibility - iOS expects it at /api/text-to-audio)
    @app.route('/api/text-to-audio', methods=['POST'])
    @jwt_required()
    def text_to_audio():
        """
        Generate audio from text with caching.

        Request body:
            {
                "text": "Text to convert to speech",
                "voiceId": "optional-voice-id"
            }

        Returns:
            {
                "success": true,
                "audioUrl": "https://s3.amazonaws.com/...",
                "fromCache": true
            }

        Authentication:
            Requires valid JWT token in Authorization header
        """
        from flask import request
        from app.services.tts_service import generate_audio

        try:
            # Validate request
            if not request.json or 'text' not in request.json:
                app.logger.warning("Text-to-audio request missing 'text' parameter")
                return jsonify({"error": "Text parameter is required"}), 400

            text = request.json.get('text')
            voice_id = request.json.get('voiceId')  # Optional

            if not text or not text.strip():
                app.logger.warning("Text-to-audio request with empty text")
                return jsonify({"error": "Text cannot be empty"}), 400

            app.logger.info(f"Text-to-audio request - text length: {len(text)}")

            # Generate audio
            result = generate_audio(text, voice_id)

            if result['status'] == 'success':
                return jsonify({
                    "success": True,
                    "audioUrl": result['audio_url'],
                    "fromCache": result.get('from_cache', False)
                }), 200
            else:
                error_msg = result.get('error', 'Unknown error')
                app.logger.error(f"Error in text-to-audio endpoint: {error_msg}")
                return jsonify({
                    "success": False,
                    "error": error_msg
                }), 500

        except Exception as e:
            app.logger.error(f"Error in text-to-audio endpoint: {e}")
            return jsonify({"error": f"Failed to process text-to-audio request: {str(e)}"}), 500


def register_error_handlers(app):
    """Register global error handlers."""

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal server error: {error}')
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'Unhandled exception: {error}', exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


def register_cli_commands(app):
    """Register Flask CLI commands."""

    @app.cli.command()
    def seed_dev_data():
        """Seed database with development data from all_tours.json."""
        import json
        import uuid
        from pathlib import Path
        from app.models.user import User
        from app.models.tour import Tour, TourSite
        from app.models.site import Site

        # Create or get admin user
        admin = User.query.filter_by(email='admin@voyana.com').first()
        if not admin:
            admin = User(
                email='admin@voyana.com',
                name='Voyana System',
                role='admin',
                email_verified=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            app.logger.info(f'Created admin user: admin@voyana.com / admin123')
        else:
            app.logger.info(f'Admin user already exists: admin@voyana.com')

        # Load all_tours.json (copied from iOS app)
        json_path = Path(__file__).parent / 'all_tours.json'
        if not json_path.exists():
            app.logger.error(f'all_tours.json not found at {json_path}')
            return

        with open(json_path, 'r') as f:
            tours_data = json.load(f)

        app.logger.info(f'Loading {len(tours_data)} tours from all_tours.json...')

        # Track sites by ID to avoid duplicates
        site_map = {}

        for tour_data in tours_data:
            # Create tour
            tour = Tour(
                id=uuid.uuid4(),
                owner_id=admin.id,
                name=tour_data.get('name'),
                description=tour_data.get('description'),
                city=tour_data.get('city'),
                neighborhood=tour_data.get('neighborhood'),
                image_url=tour_data.get('imageUrl'),
                audio_url=tour_data.get('audioUrl'),
                map_image_url=tour_data.get('mapImageUrl'),
                duration_minutes=tour_data.get('durationMinutes'),
                distance_meters=tour_data.get('distanceMeters'),
                status='live',
                is_public=True
            )

            # Calculate center point from first site if not provided
            if tour_data.get('sites') and len(tour_data['sites']) > 0:
                first_site = tour_data['sites'][0]
                tour.latitude = first_site.get('latitude')
                tour.longitude = first_site.get('longitude')

            db.session.add(tour)
            db.session.flush()  # Get tour.id

            # Create sites and relationships
            for order, site_data in enumerate(tour_data.get('sites', []), start=1):
                site_id = site_data.get('id')

                # Check if site already exists
                if site_id and site_id in site_map:
                    site = site_map[site_id]
                else:
                    # Create new site
                    site = Site(
                        id=uuid.UUID(site_id) if site_id else uuid.uuid4(),
                        title=site_data.get('title'),
                        description=site_data.get('description'),
                        latitude=site_data.get('latitude'),
                        longitude=site_data.get('longitude'),
                        image_url=site_data.get('imageUrl'),
                        audio_url=site_data.get('audioUrl'),
                        web_url=site_data.get('webUrl'),
                        keywords=site_data.get('keywords', []),
                        rating=site_data.get('rating'),
                        place_id=site_data.get('placeId'),
                        formatted_address=site_data.get('formatted_address'),
                        types=site_data.get('types', []),
                        user_ratings_total=site_data.get('user_ratings_total'),
                        phone_number=site_data.get('phone_number'),
                        city=site_data.get('city'),
                        neighborhood=site_data.get('neighborhood')
                    )
                    db.session.add(site)
                    db.session.flush()  # Get site.id
                    if site_id:
                        site_map[site_id] = site

                # Create tour-site relationship
                tour_site = TourSite(
                    tour_id=tour.id,
                    site_id=site.id,
                    display_order=order
                )
                db.session.add(tour_site)

            app.logger.info(f'Loaded tour: {tour.name} ({len(tour_data.get("sites", []))} sites)')

        db.session.commit()
        app.logger.info(f'Successfully seeded {len(tours_data)} tours with {len(site_map)} unique sites')
        app.logger.info('Admin login: admin@voyana.com / admin123')
