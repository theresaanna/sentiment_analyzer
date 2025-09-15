#!/usr/bin/env python
"""
Script to run database migrations on Railway production.
Run this script in Railway's shell or as a one-off command after deployment.
"""

import os
import sys
from flask_migrate import upgrade
from app import create_app

def run_migration():
    """Run the latest database migration."""
    print("🚀 Starting database migration...")
    
    # Create the Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Run the migration
            upgrade()
            print("✅ Migration completed successfully!")
            print("📝 theresasumma@gmail.com should now have Pro status")
            
            # Verify the update
            from app.models import User
            from app import db
            
            user = User.query.filter_by(email='theresasumma@gmail.com').first()
            if user:
                print(f"✨ User status verified:")
                print(f"   Email: {user.email}")
                print(f"   Pro Status: {user.is_subscribed}")
                print(f"   Provider: {user.provider}")
            else:
                print("⚠️ User theresasumma@gmail.com not found in database")
                
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    run_migration()