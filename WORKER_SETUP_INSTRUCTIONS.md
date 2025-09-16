# Railway Worker Setup Instructions

## One-Time Setup (Do this now)

1. **Go to Railway Dashboard**
   - Visit: https://railway.app/dashboard
   - Open your project "lavish-renewal"
   - You should see two services: "web" and "triumphant-peace" (the new worker)

2. **Rename the Worker Service**
   - Click on "triumphant-peace" service
   - Go to Settings
   - Rename it to "worker" for clarity

3. **Configure Start Command**
   - In the worker service settings
   - Find "Deploy" section
   - Set Custom Start Command to: `python analysis_worker.py`

4. **Copy Environment Variables**
   - Go to the "Variables" tab in the worker service
   - Click "Add Variable" → "Add Reference" 
   - Reference all variables from the web service, especially:
     - DATABASE_URL
     - REDIS_URL
     - YOUTUBE_API_KEY
     - MODAL_ML_BASE_URL
     - SENTIMENT_API_URL
     - Any other environment variables your web service has

5. **Verify Deployment**
   - Check the worker logs in Railway
   - You should see: "Analysis worker started"
   - Jobs should start processing

## Future Deployments

After this initial setup, you have two options:

### Option 1: Deploy Both Services (Recommended)
```bash
# This deploys to whichever service you're currently linked to
railway up

# To switch between services:
railway service  # Select which service to deploy to
```

### Option 2: Use GitHub Integration (Easiest)
- Connect your GitHub repo to Railway
- Both services will auto-deploy on push to main branch

## How to Deploy Updates

### To deploy BOTH web and worker:
```bash
# Deploy web service
railway service  # Choose "web"
railway up

# Deploy worker service  
railway service  # Choose "worker"
railway up
```

### Quick deployment script (create this):
```bash
#!/bin/bash
# save as deploy_all.sh

echo "Deploying web service..."
railway service web
railway up

echo "Deploying worker service..."
railway service worker  
railway up

echo "Both services deployed!"
```

## Monitoring

- Check worker status: Look at logs in Railway dashboard
- Check queue status: Visit your app's dashboard page
- If jobs are stuck in "queued", check worker logs for errors

## Troubleshooting

If worker isn't processing jobs:
1. Check Railway worker logs for errors
2. Verify environment variables are set
3. Ensure Redis connection is working
4. Check that start command is `python analysis_worker.py`