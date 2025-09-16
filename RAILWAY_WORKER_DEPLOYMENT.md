# Railway Worker Service Deployment Guide

## Overview
Your application needs TWO services on Railway:
1. **Web Service** (main application) - Already deployed
2. **Worker Service** (background job processor) - Needs to be deployed

## Setting Up the Worker Service

### Step 1: Create a New Service in Railway
1. Go to your Railway project dashboard
2. Click "New Service" → "GitHub Repo"
3. Select the same repository (`sentiment_analyzer`)
4. Name it something like "sentiment-analyzer-worker"

### Step 2: Configure the Worker Service

In the Railway dashboard for the worker service, set these configurations:

#### Build Configuration
- **Root Directory**: `/` (same as main app)
- **Build Command**: Leave default (it will use nixpacks.toml)
- **Watch Paths**: Same as main app

#### Deploy Configuration
Set the start command:
```bash
python analysis_worker.py
```

Or if you want to use the railway.worker.json config:
- Set **Railway Config Path** to: `railway.worker.json`

### Step 3: Environment Variables

The worker needs the same environment variables as your main app:

**Required Variables:**
```
DATABASE_URL=<same as main app>
REDIS_URL=<same as main app>
MODAL_ML_BASE_URL=https://theresaanna--sentiment-ml-service-fastapi-app.modal.run
YOUTUBE_API_KEY=<your YouTube API key>
```

**Optional Variables:**
```
WORKER_BATCH_SIZE=100
WORKER_POLL_INTERVAL=5
WORKER_MAX_RETRIES=3
```

### Step 4: Connect to Same Database

IMPORTANT: The worker must connect to the SAME database as your main app.

1. In Railway, go to your PostgreSQL service
2. Copy the `DATABASE_URL` from the Connect tab
3. Add this exact same URL to your worker service's environment variables

### Step 5: Deploy

1. Once configured, Railway will automatically deploy the worker
2. Check the logs to ensure it's running:
   - You should see: "Analysis worker started. Polling for jobs..."
   - It should connect to Redis successfully
   - It should connect to the database successfully

## Verification

### Check Worker is Running:
Look for these log messages:
```
INFO - Analysis worker started. Polling for jobs...
INFO - Redis cache connected successfully
INFO - Connected to database
```

### Test the Worker:
1. Queue a job from your web app (try to analyze a video with "Queue" option)
2. Check worker logs - you should see:
   ```
   INFO - Starting processing for job job_xxxxx
   INFO - Fetching comments for video xxxxx
   INFO - Analyzing sentiment for xxx comments
   INFO - Job job_xxxxx completed successfully
   ```

## Troubleshooting

### Worker Not Processing Jobs
- Check DATABASE_URL is identical in both services
- Check REDIS_URL is identical in both services
- Verify worker is polling (check logs)

### Database Migration Issues
- Migrations run automatically on the web service
- Worker doesn't need to run migrations
- If you see schema errors, redeploy the web service first

### Memory Issues
If worker runs out of memory:
- Reduce WORKER_BATCH_SIZE (default: 100, try 50)
- Process fewer comments at once
- Consider upgrading Railway plan for more memory

## Architecture Notes

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Web App   │────▶│   Database  │◀────│   Worker    │
│  (Gunicorn) │     │ (PostgreSQL)│     │  (Python)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   ▲                    │
       │                   │                    │
       └───────────────────┴────────────────────┘
                     Redis Cache
```

- Web app creates jobs in database with status='queued'
- Worker polls database for queued jobs
- Worker updates job progress in real-time
- Web app shows live progress to users

## Monitoring

### Key Metrics to Watch:
- Worker CPU usage (should be < 80%)
- Worker memory usage (should be < 80%)
- Queue length (queued jobs in database)
- Average processing time per job

### Alerts to Set:
1. Worker hasn't processed jobs in 10 minutes
2. Queue length > 100 jobs
3. Worker memory > 90%
4. Worker repeatedly crashing

## Scaling

If you need to handle more jobs:
1. Increase worker replicas (numReplicas in railway.worker.json)
2. Add job priority system
3. Implement job timeout handling
4. Consider separate queues for different job sizes

## Security Notes

- Worker uses same authentication as main app
- API keys are shared via environment variables
- Database access is restricted to Railway internal network
- No public endpoints exposed by worker

## Deployment Checklist

- [ ] Create new Railway service for worker
- [ ] Configure with railway.worker.json or set start command
- [ ] Copy all environment variables from main app
- [ ] Ensure DATABASE_URL matches exactly
- [ ] Deploy and check logs
- [ ] Test with a queued job
- [ ] Monitor for first 24 hours