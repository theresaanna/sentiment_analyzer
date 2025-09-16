#!/bin/bash
# Startup script for web service

# Handle PORT environment variable
# Check if PORT is set and is a valid number
if [[ -z "$PORT" ]] || [[ "$PORT" == "\$PORT" ]] || ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "Warning: PORT environment variable is not set or invalid ('$PORT'). Using default port 8000."
    export PORT=8000
fi

echo "Starting web server on port $PORT..."

# Run database migrations first
echo "Running database migrations..."
flask db upgrade || echo "Warning: Database migration failed, continuing anyway"

# Start gunicorn with explicit port
echo "Starting Gunicorn on 0.0.0.0:$PORT"
exec gunicorn --bind "0.0.0.0:${PORT}" \
    --timeout 120 \
    --workers 1 \
    --threads 4 \
    --worker-class gthread \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    run:app
