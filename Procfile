web: gunicorn run:app --workers 2 --threads 4 --worker-class sync --bind 0.0.0.0:$PORT --timeout 120 --keep-alive 5 --log-level info

