# Database Operations Guide

This guide covers database migrations and backup procedures for the Sentiment Analyzer application, both for local development and Railway production deployment.

## Table of Contents
- [Database Migrations](#database-migrations)
- [Database Backups](#database-backups)
- [Railway Deployment](#railway-deployment)
- [Troubleshooting](#troubleshooting)

## Database Migrations

We use Flask-Migrate (based on Alembic) to manage database schema changes.

### Initial Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize migrations (first time only):**
   ```bash
   python scripts/init_migrations.py
   # OR
   python scripts/manage_migrations.py init
   ```

### Common Migration Commands

#### Using Flask-Migrate directly:
```bash
# Create a new migration
flask db migrate -m "Add new column to User table"

# Apply migrations
flask db upgrade

# Rollback one migration
flask db downgrade

# View migration history
flask db history

# Check current migration
flask db current
```

#### Using the management script:
```bash
# Check migration status
python scripts/manage_migrations.py status

# Create a new migration
python scripts/manage_migrations.py create -m "Add subscription fields"

# Apply all pending migrations
python scripts/manage_migrations.py upgrade

# Rollback last migration
python scripts/manage_migrations.py downgrade

# Check for pending migrations
python scripts/manage_migrations.py check

# Auto-detect and create migration
python scripts/manage_migrations.py auto
```

### Best Practices for Migrations

1. **Always backup before migrations:**
   - The manage_migrations.py script automatically creates backups before upgrades
   - Manual backup: `python scripts/db_backup.py backup`

2. **Review migrations before applying:**
   - Check the generated migration file in `migrations/versions/`
   - Ensure the upgrade and downgrade functions are correct

3. **Test migrations locally first:**
   - Apply migrations to a test database
   - Verify data integrity after migration

4. **Version control:**
   - Always commit migration files to git
   - Never edit migration files after they've been applied to production

## Database Backups

### Manual Backups

#### Create a backup:
```bash
python scripts/db_backup.py backup
```

#### List available backups:
```bash
python scripts/db_backup.py list
```

#### Cleanup old backups (keep last 10):
```bash
python scripts/db_backup.py cleanup --keep 10
```

### Restore from Backup

#### Interactive restore (select from list):
```bash
python scripts/db_restore.py
```

#### Restore specific backup:
```bash
python scripts/db_restore.py --backup backup_development_20240110_143022.db.gz
```

#### Force restore (skip confirmation):
```bash
python scripts/db_restore.py --backup backup_file.gz --force
```

### Automated Backups

#### Local Development (using cron):
```bash
# Add to crontab (crontab -e)
# Daily backup at 2 AM
0 2 * * * cd /path/to/project && python scripts/db_backup.py backup

# Hourly backup (for active development)
0 * * * * cd /path/to/project && python scripts/db_backup.py backup --keep 24
```

#### Using the backup worker:
```bash
# Run backup worker (keeps running, performs scheduled backups)
python scripts/backup_worker.py
```

## Railway Deployment

### Environment Variables

Set these in Railway dashboard:
```
DATABASE_URL=postgresql://user:pass@host:port/dbname
FLASK_ENV=production
SECRET_KEY=your-secret-key
YOUTUBE_API_KEY=your-api-key
```

### Automatic Migrations on Deploy

The Procfile includes a release command that runs migrations automatically:
```
release: flask db upgrade
```

### Setting up Automated Backups on Railway

#### Option 1: GitHub Actions
1. Copy the workflow from the railway_backup_scheduler.py output to `.github/workflows/backup.yml`
2. Add DATABASE_URL to GitHub Secrets
3. Backups will run daily at 2 AM UTC

#### Option 2: Separate Backup Service
1. Create a new Railway service
2. Set it to run `python scripts/backup_worker.py`
3. The worker will perform scheduled backups

#### Option 3: External Cron Service
Use services like cron-job.org to trigger backup endpoint or GitHub Action

### PostgreSQL Client Installation

For production backups/restores with PostgreSQL:

```bash
# macOS
brew install postgresql

# Ubuntu/Debian
apt-get update && apt-get install -y postgresql-client

# RHEL/CentOS
yum install postgresql
```

## Troubleshooting

### Common Issues

#### 1. "No migrations initialized"
**Solution:** Run `python scripts/init_migrations.py`

#### 2. "pg_dump not found" (on Railway)
**Solution:** The backup script automatically installs PostgreSQL client tools when needed

#### 3. Database locked (SQLite)
**Solution:** Ensure no other processes are accessing the database

#### 4. Migration conflicts
**Solution:** 
```bash
# Reset to a known good state
python scripts/manage_migrations.py stamp head
# Then create new migration
python scripts/manage_migrations.py create -m "Fix conflicts"
```

#### 5. Restore fails on Railway
**Solution:** Ensure DATABASE_URL is correctly set and you have proper permissions

### Emergency Recovery

If something goes wrong:

1. **Local SQLite:**
   ```bash
   # Find latest backup
   python scripts/db_backup.py list
   # Restore
   python scripts/db_restore.py
   ```

2. **Railway PostgreSQL:**
   ```bash
   # Download backup from GitHub Actions artifacts
   # Then restore locally or via Railway CLI
   ```

3. **Complete reset:**
   ```bash
   # Backup current state
   python scripts/db_backup.py backup
   # Remove migrations
   rm -rf migrations/
   # Reinitialize
   python scripts/init_migrations.py
   ```

## Backup Storage Recommendations

### Local Development
- Keep backups in `backups/` directory (gitignored)
- Retain last 10-20 backups
- Consider daily backups to cloud storage

### Production (Railway)
- Use GitHub Actions artifacts (30-day retention)
- Configure S3 or Google Cloud Storage for long-term storage
- Implement backup rotation policy (daily for 7 days, weekly for 4 weeks, monthly for 12 months)

## Security Considerations

1. **Never commit database files or backups to git**
   - Ensure `*.db`, `*.sqlite`, and `backups/` are in `.gitignore`

2. **Encrypt sensitive backups**
   - For production backups containing user data
   - Use GPG or similar encryption before uploading to cloud storage

3. **Secure database URLs**
   - Never hardcode DATABASE_URL in code
   - Use environment variables or secrets management

4. **Access control**
   - Limit who can run migration and restore commands in production
   - Use Railway's team permissions for production access

## Quick Reference

### Daily Operations
```bash
# Check status
python scripts/manage_migrations.py status

# Create and apply migration
python scripts/manage_migrations.py auto

# Backup database
python scripts/db_backup.py backup
```

### Weekly Maintenance
```bash
# Clean old backups
python scripts/db_backup.py cleanup --keep 7

# Check for pending migrations
python scripts/manage_migrations.py check
```

### Before Major Changes
```bash
# Full backup
python scripts/db_backup.py backup

# Test migration locally
python scripts/manage_migrations.py create -m "Major change"
# Review the migration file
python scripts/manage_migrations.py upgrade

# If issues, rollback
python scripts/manage_migrations.py downgrade
python scripts/db_restore.py
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Flask-Migrate documentation: https://flask-migrate.readthedocs.io/
3. Check Railway documentation: https://docs.railway.app/
