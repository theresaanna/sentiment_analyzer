"""
YouTube Sentiment Analyzer Flask Application
Modified to preload ML models at startup for better performance on Railway
"""
import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from app.config import Config

# Initialize extensions (without app)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

logger = logging.getLogger(__name__)


def preload_models():
    """Preload ML models at application startup."""
    try:
        # Import model manager
        from app.utils.model_manager import get_model_manager

        model_manager = get_model_manager()

        # Check if we should skip model preloading (for migrations, etc.)
        if os.environ.get('SKIP_MODEL_PRELOAD'):
            logger.info("Skipping model preloading (SKIP_MODEL_PRELOAD is set)")
            return

        # For Railway deployment, check available memory
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            # Use minimal models on Railway if specified
            if os.environ.get('RAILWAY_MINIMAL_MODELS'):
                logger.info("Loading minimal model set for Railway deployment")
                os.environ['MINIMAL_MODELS'] = '1'

        # Preload all models
        logger.info("Starting model preloading...")
        model_manager.preload_all_models()

        # Log statistics
        stats = model_manager.get_model_stats()
        logger.info(f"Models loaded: {stats.get('loaded_models', [])}")
        logger.info(f"Total load time: {sum(stats.get('load_times', {}).values()):.2f}s")

    except Exception as e:
        logger.error(f"Failed to preload models: {e}")
        # Don't crash the app if model preloading fails
        # Models will be loaded on-demand instead


def create_app(config_class=Config):
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Setup logging
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Enable CORS for all routes
    if app.config.get('DEBUG', False):
        CORS(app, origins=['http://localhost:3000', 'http://localhost:3002'])
    else:
        CORS(app, origins=['https://web-production-6a064.up.railway.app'])

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Initialize Flask-Mail
    from app.email import mail
    mail.init_app(app)

    # Register custom Jinja2 filters
    from app.filters import register_filters
    register_filters(app)

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Import models for migrations
    with app.app_context():
        try:
            from app.models import User  # noqa: F401
            # Create tables if they don't exist (for initial deployment)
            # This is safe to run even with migrations
            db.create_all()
        except Exception as e:
            logger.warning(f"Could not initialize database: {e}")

    # Preload ML models after app context is established
    # This runs once at startup, not per request
    with app.app_context():
        preload_models()

    # Add health check endpoint for Railway
    @app.route('/health')
    def health_check():
        """Health check endpoint for Railway."""
        # Basic health check - just verify the app is running
        health_status = {
            'status': 'healthy',
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Try to check database (but don't fail if it's not ready)
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = f'initializing'
            logger.info(f"Database not ready yet: {e}")
        
        # Try to check model status (but don't fail if models aren't loaded)
        try:
            from app.utils.model_manager import get_model_manager
            model_manager = get_model_manager()
            stats = model_manager.get_model_stats()
            health_status['models_loaded'] = len(stats.get('loaded_models', []))
        except Exception as e:
            health_status['models_loaded'] = 0
            health_status['models_status'] = f'error: {str(e)}'
            logger.warning(f"Model health check failed: {e}")
        
        # Always return 200 OK for basic health
        return jsonify(health_status), 200

    # Add model stats endpoint (for debugging)
    @app.route('/api/model-stats')
    def model_stats():
        """Get model loading statistics."""
        try:
            from app.utils.model_manager import get_model_manager
            model_manager = get_model_manager()
            return model_manager.get_model_stats(), 200
        except Exception as e:
            return {'error': str(e)}, 500

    return app