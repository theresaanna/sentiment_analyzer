release: flask db upgrade
web: gunicorn run:app
worker: python scripts/preload_worker.py
