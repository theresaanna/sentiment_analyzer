#!/usr/bin/env python
"""
WSGI entry point for production deployment.
"""
import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from app import create_app
    
    # Get configuration from environment
    config_name = os.environ.get('FLASK_ENV', 'production')
    logger.info(f"Starting application in {config_name} mode")
    
    # Create the application
    app = create_app()
    
    # Log configuration details (without sensitive data)
    logger.info(f"Database configured: {'DATABASE_URL' in os.environ}")
    logger.info(f"Redis configured: {'REDIS_URL' in os.environ}")
    logger.info(f"YouTube API configured: {'YOUTUBE_API_KEY' in os.environ}")
    
    # Add error handlers
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {error}")
        return "Internal Server Error", 500
    
    @app.errorhandler(Exception)
    def unhandled_exception(error):
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return "An error occurred", 500
    
    logger.info("Application started successfully")
    
except Exception as e:
    logger.error(f"Failed to start application: {e}", exc_info=True)
    sys.exit(1)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000))
    )
