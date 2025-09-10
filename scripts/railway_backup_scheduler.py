#!/usr/bin/env python
"""
Railway backup scheduler for production database.
This script can be run as a Railway cron job or scheduled task.
"""
import os
import sys
import json
import subprocess
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def setup_railway_backup():
    """
    Setup automated backups on Railway.
    Railway doesn't have built-in cron, but you can:
    1. Use GitHub Actions to trigger backups
    2. Use external services like cron-job.org
    3. Create a separate Railway service for backups
    """
    
    print("🚂 Railway Backup Configuration")
    print("=" * 50)
    
    # Check if we're running on Railway
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        print(f"✓ Running on Railway ({os.environ.get('RAILWAY_ENVIRONMENT')} environment)")
    else:
        print("⚠️  Not running on Railway. This script is for Railway deployments.")
    
    # Create backup script for Railway
    backup_script = """#!/bin/bash
# Railway backup script
# Add this to your Railway service

# Install PostgreSQL client if not present
if ! command -v pg_dump &> /dev/null; then
    apt-get update && apt-get install -y postgresql-client
fi

# Run backup
python scripts/db_backup.py backup

# Optional: Upload to cloud storage (S3, Google Cloud, etc.)
# aws s3 cp backups/ s3://your-bucket/backups/ --recursive --exclude "*" --include "*.gz"
"""
    
    print("\n📝 Railway Backup Script:")
    print("-" * 50)
    print(backup_script)
    
    # Create GitHub Action workflow
    github_action = """name: Database Backup

on:
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  backup:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        sudo apt-get update
        sudo apt-get install -y postgresql-client
    
    - name: Run backup
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        FLASK_ENV: production
      run: |
        python scripts/db_backup.py backup
    
    - name: Upload backup to artifacts
      uses: actions/upload-artifact@v3
      with:
        name: database-backup
        path: backups/*.gz
        retention-days: 30
    
    # Optional: Upload to S3
    # - name: Upload to S3
    #   env:
    #     AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    #     AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    #   run: |
    #     aws s3 cp backups/ s3://your-bucket/backups/ --recursive --exclude "*" --include "*.gz"
"""
    
    print("\n📝 GitHub Actions Workflow (.github/workflows/backup.yml):")
    print("-" * 50)
    print(github_action)
    
    # Create Railway.json configuration
    railway_config = {
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "gunicorn run:app",
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 10
        },
        "services": [
            {
                "name": "web",
                "source": {
                    "repo": "github.com/your-repo"
                }
            },
            {
                "name": "backup-worker",
                "source": {
                    "repo": "github.com/your-repo"
                },
                "deploy": {
                    "startCommand": "python scripts/backup_worker.py",
                    "schedule": "0 2 * * *"  # Daily at 2 AM
                }
            }
        ]
    }
    
    print("\n📝 Railway Configuration (railway.json):")
    print("-" * 50)
    print(json.dumps(railway_config, indent=2))
    
    return True


def create_backup_worker():
    """Create a backup worker script for Railway."""
    
    worker_script = """#!/usr/bin/env python
\"\"\"
Backup worker for Railway deployment.
This runs as a separate service or scheduled job.
\"\"\"
import os
import sys
import time
import schedule
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.db_backup import DatabaseBackup


def run_backup():
    \"\"\"Run database backup.\"\"\"
    print(f"[{datetime.now()}] Starting scheduled backup...")
    
    try:
        backup_manager = DatabaseBackup()
        result = backup_manager.backup()
        
        if result:
            print(f"[{datetime.now()}] Backup completed successfully: {result}")
            # Cleanup old backups
            backup_manager.cleanup_old_backups(keep_count=7)
        else:
            print(f"[{datetime.now()}] Backup failed!")
            
    except Exception as e:
        print(f"[{datetime.now()}] Backup error: {e}")


def main():
    \"\"\"Main worker loop.\"\"\"
    print("🤖 Backup Worker Started")
    print(f"   Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
    print(f"   Database URL: {os.environ.get('DATABASE_URL', 'Not set')[:20]}...")
    
    # Schedule daily backup at 2 AM
    schedule.every().day.at("02:00").do(run_backup)
    
    # Also run backup on startup
    run_backup()
    
    # Keep the worker running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == '__main__':
    main()
"""
    
    worker_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'scripts', 
        'backup_worker.py'
    )
    
    with open(worker_path, 'w') as f:
        f.write(worker_script)
    
    print(f"\n✅ Created backup worker: {worker_path}")
    
    return worker_path


def create_procfile():
    """Create or update Procfile for Railway."""
    
    procfile_content = """web: gunicorn run:app
worker: python scripts/backup_worker.py
release: flask db upgrade
"""
    
    procfile_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'Procfile'
    )
    
    with open(procfile_path, 'w') as f:
        f.write(procfile_content)
    
    print(f"\n✅ Created Procfile: {procfile_path}")
    
    return procfile_path


def main():
    """Main setup function."""
    print("🚀 Setting up Railway backup configuration...")
    
    # Setup Railway configuration
    setup_railway_backup()
    
    # Create backup worker
    create_backup_worker()
    
    # Create/update Procfile
    create_procfile()
    
    # Add schedule to requirements if not present
    requirements_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'requirements.txt'
    )
    
    with open(requirements_path, 'r') as f:
        requirements = f.read()
    
    if 'schedule' not in requirements:
        with open(requirements_path, 'a') as f:
            f.write('\n# Backup scheduling\nschedule==1.2.0\n')
        print(f"✅ Added 'schedule' to requirements.txt")
    
    print("\n" + "=" * 50)
    print("✅ Railway backup configuration complete!")
    print("\nNext steps:")
    print("1. Commit and push these changes to your repository")
    print("2. Set DATABASE_URL in Railway environment variables")
    print("3. Optional: Set up GitHub Actions for automated backups")
    print("4. Optional: Configure cloud storage for backup archival")


if __name__ == '__main__':
    main()
