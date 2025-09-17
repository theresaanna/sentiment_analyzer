# Railway Worker Service Setup

## Required Environment Variables for Worker Service

Copy these environment variables from your web service to the worker service:

### Database
- `DATABASE_URL` - PostgreSQL connection string (shared with web service)

### Redis (if using)
- `REDIS_URL` - Redis connection string (shared with web service)

### API Keys & External Services
- `MODAL_ML_BASE_URL` - Your Modal ML service endpoint
- `SENTIMENT_API_URL` - Same as MODAL_ML_BASE_URL
- `YOUTUBE_API_KEY` - Your YouTube Data API key
- `SECRET_KEY` - Flask secret key (can be same as web service)

### App Configuration
- `FLASK_ENV=production`
- `FLASK_APP=run.py`

### Optional Analytics/Monitoring
- `GOOGLE_ANALYTICS_ID` (if you're using it)
- Any other monitoring/logging service keys you have

## Service Configuration

### Start Command
```
python analysis_worker.py
```

### Healthcheck
**DISABLE** - Workers don't serve HTTP so healthchecks will always fail

### Port
**REMOVE/DISABLE** - Workers don't need to listen on a port

### Resources
- CPU: Standard (same as web service)
- Memory: 1GB+ (processing can be memory intensive)

## Deployment Steps

1. Create new service from same GitHub repo
2. Set start command to `python analysis_worker.py`
3. Copy environment variables from web service
4. Disable healthcheck
5. Remove port configuration
6. Deploy

## Verification

After deployment, check the logs:
- Worker should start with "Analysis worker started"
- Should connect to database successfully  
- Should be ready to process jobs from the queue

## Testing

1. Submit an analysis job through your web interface
2. Check worker logs to see it pick up and process the job
3. Verify job status updates in your web interface

## Important Notes

- Both services (web + worker) share the same database
- Both services should have access to the same Redis instance (if using)
- The worker runs continuously, polling for new jobs
- If a worker crashes, Railway will restart it automatically
- You can scale workers by creating additional worker services if needed