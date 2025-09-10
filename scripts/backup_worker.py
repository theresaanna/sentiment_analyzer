#!/usr/bin/env python
"""
Backup worker for Railway deployment.
This runs as a separate service or scheduled job.
"""
import os
import sys
import time
import schedule
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.db_backup import DatabaseBackup


def run_backup():
    """Run database backup."""
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
    """Main worker loop."""
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
