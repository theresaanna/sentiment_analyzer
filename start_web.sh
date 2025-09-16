#!/bin/bash
# Startup script for web service

# Set default port if not provided
PORT=${PORT:-8000}

echo "Starting web server on port $PORT..."

# Run database migrations first
flask db upgrade

# Start gunicorn
exec gunicorn --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --workers 1 \
    --threads 4 \
    --worker-class gthread \
    --log-level info \
    --access-logfile - \
    run:app