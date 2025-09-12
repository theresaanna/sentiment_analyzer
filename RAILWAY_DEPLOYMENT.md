# Railway Deployment Checklist

## 🚀 Automatic Steps (handled by Railway)
- ✅ Code deployment from GitHub main branch
- ✅ Installing Python dependencies from requirements.txt
- ✅ Running release command (database migrations)

## 🔧 Manual Setup Required

### 1. Environment Variables
Ensure these are set in Railway Dashboard → Variables:

#### Required:
- [ ] `DATABASE_URL` - PostgreSQL connection string (Railway provides this)
- [ ] `REDIS_URL` - Redis connection string (add Redis plugin or external)
- [ ] `SECRET_KEY` - Flask secret key for sessions
- [ ] `YOUTUBE_API_KEY` - Your YouTube Data API v3 key

#### Email Configuration (if using):
- [ ] `MAIL_SERVER` - SMTP server
- [ ] `MAIL_PORT` - Usually 587 for TLS
- [ ] `MAIL_USERNAME` - Email username
- [ ] `MAIL_PASSWORD` - Email password
- [ ] `MAIL_USE_TLS` - Set to `True`
- [ ] `MAIL_DEFAULT_SENDER` - Default from email

#### Google OAuth (if using):
- [ ] `GOOGLE_CLIENT_ID` - OAuth client ID
- [ ] `GOOGLE_CLIENT_SECRET` - OAuth client secret

#### Stripe (if using):
- [ ] `STRIPE_PUBLISHABLE_KEY`
- [ ] `STRIPE_SECRET_KEY`
- [ ] `STRIPE_WEBHOOK_SECRET`
- [ ] `STRIPE_PRICE_ID`

#### Optional Performance Settings:
- [ ] `MAX_COMMENTS_PER_VIDEO` - Default: 10000
- [ ] `CACHE_TIMEOUT` - Default: 3600
- [ ] `OPENAI_API_KEY` - If using GPT features

### 2. Redis Setup
Railway doesn't include Redis by default. You need to:

#### Option A: Add Redis Plugin
1. Go to your Railway project
2. Click "New" → "Database" → "Add Redis"
3. It will automatically set `REDIS_URL`

#### Option B: Use External Redis
1. Use Redis Cloud, Upstash, or another provider
2. Add `REDIS_URL` manually to Railway variables

### 3. Database Migration
With the updated Procfile, migrations will run automatically on each deploy via the `release` command.

To run manually if needed:
```bash
railway run flask db upgrade
```

### 4. New Tables Added
The following tables will be created by migrations:
- `sentiment_feedback` - User corrections for ML training
- `channel` - YouTube channel information  
- `video` - Video metadata
- `user_channel` - User-channel relationships

### 5. Post-Deployment Verification

1. **Check logs** for migration success:
   ```bash
   railway logs
   ```

2. **Verify Redis connection**:
   - Try running a sentiment analysis
   - Check for cache errors in logs

3. **Test new features**:
   - Manual sentiment corrections
   - Feedback persistence
   - Dashboard (if enabled)

### 6. Troubleshooting

#### Redis Memory Issues
If you see "bigredis-max-ram" errors:
1. Clear Redis cache: `railway run flask shell` then:
   ```python
   from app.cache import cache
   cache.redis_client.flushdb()
   ```
2. Consider upgrading Redis tier

#### Migration Failures
If migrations fail:
1. Check DATABASE_URL is set correctly
2. Run manually: `railway run flask db upgrade`
3. Check for conflicting migrations

#### Missing Dependencies
If imports fail:
1. Ensure all packages are in requirements.txt
2. Clear build cache: Railway Dashboard → Settings → Clear Build Cache

## 🎯 Quick Deploy Commands

```bash
# Push changes
git add -A
git commit -m "Update for Railway deployment"
git push origin main

# Run migrations manually if needed
railway run flask db upgrade

# Check deployment logs
railway logs

# Open deployed app
railway open
```

## 📝 Notes
- Railway auto-deploys from main branch
- SSL/HTTPS is handled automatically
- Custom domains can be added in Settings
- Scaling can be configured in Railway dashboard
