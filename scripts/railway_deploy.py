#!/usr/bin/env python
"""
Railway deployment initialization script.
Handles database setup and migrations for Railway deployments.
"""
import os
import sys
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_command(cmd):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}", file=sys.stderr)
    return result.returncode


def setup_database():
    """Setup database for Railway deployment."""
    print("🚂 Railway Deployment Setup")
    print("=" * 50)
    
    # Check environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("⚠️  No DATABASE_URL found. Using SQLite.")
    else:
        print(f"✓ DATABASE_URL found: {db_url[:30]}...")
        
        # Railway uses postgres:// but SQLAlchemy needs postgresql://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
            os.environ['DATABASE_URL'] = db_url
            print("✓ Updated DATABASE_URL for SQLAlchemy compatibility")
    
    # Check if this is the first deployment
    if not os.path.exists('migrations'):
        print("\n📦 First deployment detected. Initializing migrations...")
        
        # Initialize migrations
        if run_command(['flask', 'db', 'init']) != 0:
            print("❌ Failed to initialize migrations")
            return 1
        
        print("✓ Migrations initialized")
        
        # Create initial migration
        if run_command(['flask', 'db', 'migrate', '-m', 'Initial migration']) != 0:
            print("⚠️  No changes detected or migration creation failed")
        else:
            print("✓ Initial migration created")
    else:
        print("\n✓ Migrations already initialized")
        
        # Check for pending migrations
        result = subprocess.run(['flask', 'db', 'current'], 
                              capture_output=True, text=True)
        current = result.stdout.strip()
        
        result = subprocess.run(['flask', 'db', 'heads'], 
                              capture_output=True, text=True)
        head = result.stdout.strip()
        
        if current != head:
            print("📦 Pending migrations detected")
        else:
            print("✓ Database is up to date")
    
    # Apply migrations
    print("\n🔄 Applying database migrations...")
    if run_command(['flask', 'db', 'upgrade']) != 0:
        print("❌ Failed to apply migrations")
        
        # Try to create tables directly as fallback
        print("\n🔧 Attempting fallback: creating tables directly...")
        try:
            from app import create_app, db
            from app.models import User
            
            app = create_app()
            with app.app_context():
                db.create_all()
                print("✓ Tables created successfully")
        except Exception as e:
            print(f"❌ Fallback failed: {e}")
            return 1
    else:
        print("✓ Migrations applied successfully")
    
    print("\n✅ Railway deployment setup complete!")
    return 0


if __name__ == '__main__':
    sys.exit(setup_database())
