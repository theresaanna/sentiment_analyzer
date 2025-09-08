"""
YouTube Sentiment Analyzer Flask Application
"""
from flask import Flask
from flask_cors import CORS
from app.config import Config


def create_app(config_class=Config):
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for all routes
    CORS(app, origins=['http://localhost:3000', 'http://localhost:3002'])
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    return app
