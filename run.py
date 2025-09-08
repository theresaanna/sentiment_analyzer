#!/usr/bin/env python
"""
Entry point for the YouTube Sentiment Analyzer Flask application.
"""
import os
from app import create_app

# Get configuration from environment or use default
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app()

if __name__ == '__main__':
    # Run the application
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        debug=app.config.get('DEBUG', False)
    )
