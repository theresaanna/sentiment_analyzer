# Production Deployment Guide

This guide walks you through deploying the Sentiment Analyzer application to production.

## Prerequisites

- Python 3.9+
- PostgreSQL or SQLite database
- Redis (for caching)
- Web server (nginx/Apache)
- SSL certificates

## Database Migration

### 1. Run the Production Database Deployment

The easiest way to get your production database up to date is to use the automated deployment script:

```bash
python scripts/deploy_production_db.py
```

This script will:
- ✅ Check current migration status
- ✅ Run all pending migrations
- ✅ Verify all tables exist and are accessible
- ✅ Offer to create an admin user if needed
- ✅ Provide deployment status and next steps

### 2. Manual Migration (Alternative)

If you prefer to run migrations manually:

```bash
# Check current migration status
python -m flask db current

# Apply all pending migrations
python -m flask db upgrade

# Verify database is ready
python -c "
from app import create_app, db
from app.models import User, Channel, Video, UserChannel, SentimentFeedback
app = create_app()
with app.app_context():
    print('Database verification:')
    print(f'Users: {User.query.count()}')
    print(f'Channels: {Channel.query.count()}')
    print(f'Videos: {Video.query.count()}')
    print(f'User Channels: {UserChannel.query.count()}')
    print(f'Sentiment Feedback: {SentimentFeedback.query.count()}')
"
```

## Database Schema

The production database includes these tables:

### Core Tables
- **`user`**: User accounts with authentication
- **`channel`**: YouTube channels being tracked
- **`video`**: Individual videos from tracked channels
- **`user_channel`**: Many-to-many relationship between users and channels

### Feature Tables
- **`sentiment_feedback`**: User corrections to sentiment predictions for ML training

### Migration History
- **`alembic_version`**: Tracks applied database migrations

## Environment Setup

### 1. Environment Variables

Set these environment variables in your production environment:

```bash
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=your-super-secret-production-key

# Database
DATABASE_URL=postgresql://user:pass@localhost/sentiment_analyzer
# OR for SQLite:
# DATABASE_URL=sqlite:///production.db

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# YouTube API
YOUTUBE_API_KEY=your-youtube-api-key

# Email (for password resets)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Optional: Payment Integration
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Admin User

If you don't have any users yet:

```bash
python scripts/create_admin.py
```

## Web Server Configuration

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/certificate.pem;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/your/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Systemd Service (Ubuntu/Debian)

Create `/etc/systemd/system/sentiment-analyzer.service`:

```ini
[Unit]
Description=Sentiment Analyzer Web App
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/sentiment_analyzer
Environment=PATH=/path/to/sentiment_analyzer/venv/bin
Environment=FLASK_APP=run.py
Environment=FLASK_ENV=production
ExecStart=/path/to/sentiment_analyzer/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable sentiment-analyzer
sudo systemctl start sentiment-analyzer
```

## Database Backup & Monitoring

### Backup Script

```bash
# For PostgreSQL
pg_dump sentiment_analyzer > backup_$(date +%Y%m%d_%H%M%S).sql

# For SQLite
cp production.db backup_$(date +%Y%m%d_%H%M%S).db
```

### Monitoring

Monitor these key metrics:
- Database connection pool usage
- Redis cache hit rates
- YouTube API quota usage
- User registration and engagement

## Security Checklist

- [ ] Database credentials secured
- [ ] Secret key is strong and unique
- [ ] SSL certificates installed and working
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] Regular security updates applied
- [ ] Database backups automated
- [ ] Error logging configured
- [ ] Rate limiting enabled

## Troubleshooting

### Database Issues

```bash
# Check migration status
python -m flask db current

# View migration history
python -m flask db history

# Reset migrations (CAUTION: DATA LOSS)
python -m flask db downgrade base
python -m flask db upgrade
```

### Application Issues

```bash
# Check if tables exist
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    inspector = db.inspect(db.engine)
    print('Tables:', inspector.get_table_names())
"

# Test database connection
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    try:
        db.engine.execute('SELECT 1')
        print('✅ Database connection OK')
    except Exception as e:
        print('❌ Database error:', e)
"
```

## Post-Deployment Verification

1. **Test Authentication**:
   - User registration works
   - Login/logout functions
   - Password reset emails sent

2. **Test Core Features**:
   - YouTube channel analysis
   - Sentiment analysis
   - Comment feedback collection

3. **Check Performance**:
   - Page load times < 2 seconds
   - Database queries optimized
   - Cache hit rates > 80%

4. **Monitor Logs**:
   - No critical errors
   - API rate limits not exceeded
   - User actions tracked properly

## Migration Files

The following migration files are included:

1. **`52ae8f7268db_add_channel_video_userchannel_tables.py`**: Initial migration for basic user and timestamp updates
2. **`a4b9000ca891_ensure_all_tables_exist.py`**: Complete production schema with all tables

These migrations are designed to work whether you're:
- Starting fresh (creates all tables)
- Upgrading existing deployment (only creates missing tables)

## Support

For deployment issues:
1. Check logs: `tail -f /var/log/nginx/error.log`
2. Verify environment variables are set
3. Ensure all dependencies installed
4. Run the deployment verification script

Happy deploying! 🚀