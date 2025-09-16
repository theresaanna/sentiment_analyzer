# Worker Deployment Guide

## Overview
The analysis worker must run as a separate process in production to handle queued sentiment analysis jobs. Here's how to deploy it on different platforms.

## Platform-Specific Instructions

### 1. **Railway (Recommended)**

Railway requires creating **two separate services** in your project:

#### Step 1: Deploy the Web Service
1. Connect your GitHub repo to Railway
2. Create a new service named "web"
3. Use the default `railway.json` configuration
4. Set all environment variables

#### Step 2: Deploy the Worker Service
1. In the same Railway project, click "New Service"
2. Choose "GitHub Repo" and select the same repository
3. Name it "worker"
4. In Settings, set the start command:
   ```
   python analysis_worker.py
   ```
5. Share the same environment variables as the web service
6. Both services will share the same database and Redis

#### Important Railway Settings:
- Both services must have the same:
  - `DATABASE_URL`
  - `REDIS_URL` 
  - `YOUTUBE_API_KEY`
  - `MODAL_ML_BASE_URL`

### 2. **Heroku**

Heroku uses the `Procfile` to define multiple process types:

#### Setup:
1. Ensure your `Procfile` contains:
   ```
   web: gunicorn run:app --bind 0.0.0.0:$PORT
   worker: python analysis_worker.py
   ```

2. Deploy to Heroku:
   ```bash
   git push heroku main
   ```

3. Scale the worker dyno:
   ```bash
   heroku ps:scale worker=1
   ```

4. Verify both are running:
   ```bash
   heroku ps
   ```

### 3. **Docker / Docker Compose**

Use for local development or VPS deployment:

#### Local Development:
```bash
docker-compose up
```

#### Production with Docker:
```bash
# Build the image
docker build -t sentiment-analyzer .

# Run web service
docker run -d --name web -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e REDIS_URL=$REDIS_URL \
  sentiment-analyzer \
  gunicorn --bind 0.0.0.0:8000 run:app

# Run worker service
docker run -d --name worker \
  -e DATABASE_URL=$DATABASE_URL \
  -e REDIS_URL=$REDIS_URL \
  sentiment-analyzer \
  python analysis_worker.py
```

### 4. **VPS with Supervisor**

For traditional VPS deployments:

#### Install Supervisor:
```bash
sudo apt-get install supervisor
```

#### Configure:
```bash
sudo cp supervisor.conf /etc/supervisor/conf.d/sentiment-analyzer.conf
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

#### Monitor:
```bash
sudo supervisorctl status
```

### 5. **Systemd (Linux)**

Create service files:

#### `/etc/systemd/system/sentiment-web.service`:
```ini
[Unit]
Description=Sentiment Analyzer Web
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/sentiment_analyzer
Environment="PATH=/var/www/sentiment_analyzer/venv/bin"
ExecStart=/var/www/sentiment_analyzer/venv/bin/gunicorn --bind 0.0.0.0:8000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/sentiment-worker.service`:
```ini
[Unit]
Description=Sentiment Analyzer Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/sentiment_analyzer
Environment="PATH=/var/www/sentiment_analyzer/venv/bin"
ExecStart=/var/www/sentiment_analyzer/venv/bin/python analysis_worker.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sentiment-web sentiment-worker
sudo systemctl start sentiment-web sentiment-worker
```

## Environment Variables

Both web and worker services need:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db

# Redis (for queue coordination)
REDIS_URL=redis://localhost:6379

# YouTube API
YOUTUBE_API_KEY=your_key_here

# Sentiment Analysis API
MODAL_ML_BASE_URL=https://your-modal-endpoint.modal.run

# Flask
SECRET_KEY=your_secret_key
```

## Monitoring

### Check Worker Status:
```python
# Via Flask shell
from app.models import AnalysisJob
jobs = AnalysisJob.query.filter_by(status='processing').all()
print(f"Processing: {len(jobs)} jobs")
```

### Worker Health Check Endpoint:
Add to your web app:
```python
@app.route('/api/worker/health')
def worker_health():
    # Check for recent completed jobs
    from datetime import datetime, timedelta
    recent = AnalysisJob.query.filter(
        AnalysisJob.completed_at > datetime.utcnow() - timedelta(minutes=5)
    ).count()
    return jsonify({
        'healthy': recent > 0 or AnalysisJob.query.filter_by(status='processing').count() > 0,
        'recent_completions': recent
    })
```

## Scaling

### Multiple Workers:
- **Heroku**: `heroku ps:scale worker=2`
- **Railway**: Increase replicas in service settings
- **Docker**: Run multiple worker containers
- **Supervisor**: Add multiple worker programs with different names

### Queue Priority (Future Enhancement):
```python
# In worker.py
def get_next_job(self):
    # Prioritize by subscription status
    return AnalysisJob.query.filter_by(status='queued')\
        .join(User)\
        .order_by(User.is_subscribed.desc(), AnalysisJob.created_at.asc())\
        .first()
```

## Troubleshooting

### Worker Not Processing Jobs:
1. Check worker logs
2. Verify database connectivity
3. Check Redis connection
4. Ensure YouTube API key is valid
5. Verify sentiment API is accessible

### Jobs Stuck in Queue:
```bash
# Reset stuck jobs
python -c "
from app import create_app, db
from app.models import AnalysisJob
app = create_app()
with app.app_context():
    stuck = AnalysisJob.query.filter_by(status='processing').all()
    for job in stuck:
        job.status = 'queued'
    db.session.commit()
"
```

### Memory Issues:
- Limit comment batch size in worker
- Add memory monitoring
- Use worker recycling (restart after N jobs)

## Best Practices

1. **Always run at least one worker** in production
2. **Monitor queue length** and scale workers accordingly
3. **Set up alerts** for failed jobs
4. **Implement retry logic** for transient failures
5. **Log processing times** to optimize estimates
6. **Use separate Redis databases** for cache vs queue if needed

## Quick Start Commands

### Railway:
```bash
# No command needed - use Railway UI to create services
```

### Heroku:
```bash
heroku ps:scale web=1 worker=1
```

### Docker:
```bash
docker-compose up -d
```

### Systemd:
```bash
sudo systemctl start sentiment-web sentiment-worker
```

### Supervisor:
```bash
sudo supervisorctl start all
```