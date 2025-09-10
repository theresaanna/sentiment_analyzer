"""
YouTube Sentiment Analyzer Flask Application
"""
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from app.config import Config

# Initialize extensions (without app)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for all routes
    if app.config.get('DEBUG', False):
        CORS(app, origins=['http://localhost:3000', 'http://localhost:3002'])
    else:
        CORS(app, origins=['https://web-production-6a064.up.railway.app'])

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Import models for migrations
    with app.app_context():
        try:
            from app.models import User  # noqa: F401
            # Note: db.create_all() is now handled by migrations
            # Only create tables if migrations folder doesn't exist
            import os
            if not os.path.exists('migrations'):
                db.create_all()
        except Exception as e:
            print(f"Warning: could not initialize database: {e}")
    
    return app
