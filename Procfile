release: echo "Skipping database migrations for now"
web: gunicorn --bind 0.0.0.0:${PORT:-8000} --timeout 120 --workers 1 --threads 2 --worker-class sync --preload --log-level info --access-logfile - run:app
