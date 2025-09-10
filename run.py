#!/usr/bin/env python
"""
Entry point for the YouTube Sentiment Analyzer Flask application.
"""
import os
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix Railway's postgres:// URL if needed
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)
    logger.info("Fixed DATABASE_URL for PostgreSQL compatibility")

from app import create_app, db
from app.models import User

# Get configuration from environment or use default
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app()

# Ensure database tables exist
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables ready")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

if __name__ == '__main__':
    # Run the application
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        debug=app.config.get('DEBUG', False)
    )
