# Railway Auto-Deploy Configuration for Web + Worker

## Current Setup Status
✅ Your repository auto-deploys to Railway when you push to `origin main`
⚠️  Worker service needs configuration in Railway dashboard

## Required Railway Dashboard Configuration

### 1. Go to Railway Dashboard
Visit: https://railway.app/project/7cfed323-856d-48bc-9135-4040df5d83ef

### 2. Configure the Worker Service (triumphant-peace)

#### In Settings Tab:
- **Service Name**: Rename to "worker" (optional but recommended)
- **Source**: Should be connected to same GitHub repo as web service
- **Branch**: main (same as web service)
- **Root Directory**: / (same as web service)
- **Watch Paths**: Leave empty (will watch entire repo)

#### In Deploy Tab:
- **Start Command**: `python analysis_worker.py`
- **Build Command**: Leave empty (uses railway.toml)
- **Healthcheck**: Disable (workers don't need healthchecks)
- **Restart Policy**: ON_FAILURE with max 10 retries

#### In Variables Tab:
You MUST add these variables (reference from web service):
```
DATABASE_URL → ${{web.DATABASE_URL}}
REDIS_URL → ${{web.REDIS_URL}}
YOUTUBE_API_KEY → ${{web.YOUTUBE_API_KEY}}
MODAL_ML_BASE_URL → ${{web.MODAL_ML_BASE_URL}}
SENTIMENT_API_URL → ${{web.SENTIMENT_API_URL}}
```

### 3. Ensure GitHub Integration
Both services should show:
- **Source**: GitHub Repo (your-username/sentiment_analyzer)
- **Branch**: main
- **Auto Deploy**: Enabled

## How It Works After Setup

When you `git push origin main`:
1. Railway detects the push
2. Both services (web and worker) trigger builds
3. Railway uses `railway.toml` for build configuration
4. Each service uses its own start command:
   - Web: Runs the gunicorn server
   - Worker: Runs `python analysis_worker.py`
5. Services deploy in parallel

## Verification

After pushing to main, check:
1. Railway dashboard shows both services building
2. Build logs show success for both
3. Worker logs show: "Analysis worker started"
4. Web app processes queued jobs successfully

## File Structure for Auto-Deploy

```
sentiment_analyzer/
├── railway.toml          # Shared build config (we just created this)
├── railway.json          # Web service config (existing)
├── Procfile             # Defines both web and worker processes
├── analysis_worker.py   # Worker script
├── requirements.txt     # Python dependencies
└── run.py              # Web app entry point
```

## Important Notes

1. **Don't delete railway.json** - It contains web-specific configuration
2. **railway.toml** provides shared build configuration for all services
3. **Each service needs its own start command** configured in Railway dashboard
4. **Environment variables must be shared** between services

## Troubleshooting Auto-Deploy

If worker doesn't auto-deploy:
1. Check worker service is connected to GitHub repo
2. Verify "Auto Deploy" is enabled in worker service settings
3. Ensure worker has all required environment variables
4. Check build logs for errors

## Manual Deploy Override

If needed, you can still manually deploy:
```bash
# Force deploy both services
railway up -s web
railway up -s worker
```

## Testing Locally Before Push

```bash
# Test worker locally
python analysis_worker.py

# Test web locally
python run.py
```