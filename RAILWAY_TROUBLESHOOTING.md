# Railway Deployment Troubleshooting

This guide helps resolve common Railway deployment issues, especially the pip/Python environment problems.

## 🔧 Quick Fixes for Common Issues

### Issue 1: "pip: command not found" during build

**Error Message:**
```
/bin/bash: line 1: pip: command not found
```

**Solutions:**

#### Solution A: Update nixpacks.toml (Recommended)
The `nixpacks.toml` file has been updated with proper Python setup:
```toml
[phases.setup]
nixPkgs = ["python311", "python311Packages.pip", "postgresql_16", "gcc"]

[phases.install]
cmds = ["python -m pip install --upgrade pip", "python -m pip install -r requirements.txt"]

[phases.build]
cmds = ["./railway_build.sh"]

[start]
cmd = "gunicorn run:app"
```

#### Solution B: Use Dockerfile (Alternative)
If Nixpacks continues to have issues, switch to Docker:
1. Rename `Dockerfile.railway` to `Dockerfile`
2. Railway will automatically detect and use Docker
3. Remove or rename `nixpacks.toml` to disable Nixpacks

#### Solution C: Simplify Procfile
Ensure your `Procfile` is minimal:
```
release: python scripts/deploy_production_db.py --non-interactive
web: gunicorn run:app
worker: python scripts/preload_worker.py
```

### Issue 2: Database Migration Fails

**Error Messages:**
- "No module named 'app'"
- "Database connection failed"

**Solutions:**

#### Check Environment Variables
```bash
# Use the environment check script
python railway_check_env.py
```

Required variables:
- `DATABASE_URL` - Should be automatically set by Railway PostgreSQL
- `SECRET_KEY` - Set this manually
- `YOUTUBE_API_KEY` - Set this manually

#### Manual Migration
If automatic migration fails:
```bash
railway run python scripts/deploy_production_db.py --non-interactive
```

### Issue 3: Build Timeout or Memory Issues

**Solutions:**
1. **Simplify requirements**: Use minimal dependencies for build
2. **Use build requirements**: Install only essential packages during build
3. **Remove heavy dependencies**: Move ML models to runtime loading

### Issue 4: Import Errors

**Error Message:**
```
ModuleNotFoundError: No module named 'transformers'
```

**Solutions:**
1. **Check requirements.txt**: Ensure all dependencies are listed
2. **Clear build cache**: Railway Dashboard → Settings → Clear Build Cache
3. **Try Docker build**: Switch from Nixpacks to Docker

## 🚀 Deployment Strategies

### Strategy 1: Nixpacks (Default)
- Uses `nixpacks.toml` configuration
- Good for simple Python apps
- Can have pip path issues

### Strategy 2: Docker (Recommended for Complex Apps)
```bash
# Switch to Docker
mv Dockerfile.railway Dockerfile
mv nixpacks.toml nixpacks.toml.disabled
```

### Strategy 3: Minimal Build + Runtime Install
- Install minimal dependencies during build
- Load heavy dependencies at runtime

## 🔍 Debugging Commands

### Check Railway Environment
```bash
# SSH into Railway container (if available)
railway shell

# Check environment variables
railway run env | grep -E "(DATABASE|SECRET|YOUTUBE)"

# Test database connection
railway run python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    print('Database connection:', db.engine.url)
    db.engine.execute('SELECT 1')
    print('✅ Database connected')
"
```

### Check Migration Status
```bash
# View migration history
railway run python -m flask db current
railway run python -m flask db history

# Run migration manually
railway run python scripts/deploy_production_db.py --non-interactive
```

### Check Logs
```bash
# View recent logs
railway logs

# Follow logs in real-time
railway logs --follow

# Filter for specific errors
railway logs | grep -i error
```

## 📋 Pre-Deployment Checklist

- [ ] All required environment variables set
- [ ] `requirements.txt` includes all dependencies
- [ ] Database (PostgreSQL) added to Railway project
- [ ] Redis added if using caching features
- [ ] `Procfile` has correct release command
- [ ] Build scripts have execute permissions

## 🛠️ Configuration Files Status

Current setup includes:

### Working Files
- ✅ `Procfile` - Release command configured
- ✅ `scripts/deploy_production_db.py` - Enhanced with `--non-interactive`
- ✅ `railway_build.sh` - Simplified build script
- ✅ `railway_check_env.py` - Environment verification

### Alternative Configs
- 🔄 `nixpacks.toml` - Updated for better pip support
- 🔄 `Dockerfile.railway` - Backup Docker solution
- 🔄 `requirements-build.txt` - Minimal build dependencies

### Migration Files
- ✅ `migrations/versions/a4b9000ca891_ensure_all_tables_exist.py` - Complete schema

## 🎯 Expected Deployment Flow

1. **Code Push** → Railway detects changes
2. **Setup Phase** → Install Python, pip, PostgreSQL tools
3. **Install Phase** → `python -m pip install -r requirements.txt`
4. **Build Phase** → `./railway_build.sh` (verification only)
5. **Release Phase** → `python scripts/deploy_production_db.py --non-interactive`
6. **Start Phase** → `gunicorn run:app`

## 🆘 Emergency Fixes

### If deployment completely fails:
1. **Switch to Docker**:
   ```bash
   mv Dockerfile.railway Dockerfile
   git add Dockerfile
   git commit -m "Switch to Docker build"
   git push origin main
   ```

2. **Minimal Procfile**:
   ```
   web: gunicorn run:app
   ```

3. **Manual migration after deployment**:
   ```bash
   railway run python scripts/deploy_production_db.py --non-interactive
   ```

### If pip issues persist:
1. **Use python -m pip everywhere**
2. **Add pip to PATH explicitly**
3. **Use virtual environment setup**

## 📞 Getting Help

1. **Check Railway logs**: `railway logs`
2. **Railway Discord**: Get community help
3. **Railway documentation**: https://docs.railway.app
4. **Test locally**: Ensure everything works locally first

## ✅ Success Indicators

Look for these in the Railway deployment logs:
```
🚀 Starting Production Database Deployment
🤖 Running in non-interactive mode
✅ Current migration: a4b9000ca891 (head)
✅ Migrations completed successfully
✅ All required tables are present
✅ All tables are accessible
🎉 PRODUCTION DATABASE DEPLOYMENT COMPLETE!
```

Your deployment is successful when you see all these checkmarks! 🎊