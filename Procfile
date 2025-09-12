release: python scripts/deploy_production_db.py --non-interactive
web: sh -c "gunicorn --bind 0.0.0.0:${PORT:-8000} run:app"
worker: python scripts/preload_worker.py
