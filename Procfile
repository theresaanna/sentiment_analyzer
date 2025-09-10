web: gunicorn run:app
worker: python scripts/backup_worker.py
release: flask db upgrade
