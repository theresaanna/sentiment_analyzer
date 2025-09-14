# Railway Dockerfile for Sentiment Analyzer
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x railway_build.sh || true
RUN chmod +x scripts/deploy_production_db.py || true
RUN chmod +x railway_check_env.py || true

# Run unit tests during build; fail the build if tests fail
# This uses the project-provided test runner which skips integration tests by default
RUN RAILWAY_RUN_TESTS=true python scripts/run_tests_railway.py

# Note: Migrations will run via Procfile release command
# Not during Docker build

# Railway will use PORT environment variable
EXPOSE 8000

# Use shell form to allow environment variable substitution
# Skip startup script for now and start gunicorn directly
# Set SKIP_MODEL_PRELOAD to avoid memory issues during startup
ENV SKIP_MODEL_PRELOAD=true
ENV RAILWAY_MINIMAL_MODELS=true
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} --timeout 120 --workers 1 --threads 2 --worker-class sync --preload --log-level info run:app
