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

# Note: Migrations will run via Procfile release command
# Not during Docker build

# Railway will use PORT environment variable
EXPOSE 8000

# Use shell form to allow environment variable substitution
CMD sh -c "gunicorn --bind 0.0.0.0:${PORT:-8000} run:app"
