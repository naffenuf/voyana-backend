"""
Flask application factory.
"""
import os
import logging
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# Initialize extensions (without app instance)
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


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
    CORS(app)

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

    # API blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tours_bp, url_prefix='/api/tours')
    app.register_blueprint(sites_bp, url_prefix='/api/sites')
    app.register_blueprint(media_bp, url_prefix='/api/media')
    app.register_blueprint(maps_bp, url_prefix='/api/maps')

    # Health check endpoint (no prefix)
    @app.route('/api/health')
    def health_check():
        """Health check for load balancers."""
        try:
            # Check database connection
            db.session.execute('SELECT 1')
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
        """Seed database with development data."""
        from app.models.user import User
        from app.models.tour import Tour

        # Create admin user
        admin = User(
            email='admin@voyana.com',
            name='Admin User',
            role='admin',
            email_verified=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Create test user
        user = User(
            email='test@voyana.com',
            name='Test User',
            role='creator',
            email_verified=True
        )
        user.set_password('test123')
        db.session.add(user)

        db.session.commit()
        app.logger.info('Development data seeded successfully')
        app.logger.info('Admin: admin@voyana.com / admin123')
        app.logger.info('User: test@voyana.com / test123')
