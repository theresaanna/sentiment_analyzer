#!/usr/bin/env python3
"""
Production Database Deployment Script

This script handles the complete database setup for production deployment.
It ensures all tables are created and migrations are properly applied.
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from flask_migrate import upgrade, current
import subprocess


def check_migration_status():
    """Check current migration status"""
    print("📋 Checking current migration status...")
    try:
        result = subprocess.run(
            ['python', '-m', 'flask', 'db', 'current'], 
            capture_output=True, 
            text=True,
            check=True
        )
        current_rev = result.stdout.strip().split('\n')[-1]
        print(f"✅ Current migration: {current_rev}")
        return current_rev
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking migration status: {e}")
        return None


def run_migrations():
    """Apply all pending migrations"""
    print("🔄 Running database migrations...")
    try:
        result = subprocess.run(
            ['python', '-m', 'flask', 'db', 'upgrade'], 
            capture_output=True, 
            text=True,
            check=True
        )
        print("✅ Migrations completed successfully")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def verify_tables():
    """Verify all required tables exist"""
    print("🔍 Verifying database tables...")
    app = create_app()
    
    expected_tables = [
        'user', 'channel', 'video', 'user_channel', 'sentiment_feedback'
    ]
    
    with app.app_context():
        try:
            # Get all table names
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            print(f"📋 Found {len(existing_tables)} tables:")
            for table in sorted(existing_tables):
                print(f"  • {table}")
            
            # Check if all expected tables exist
            missing_tables = set(expected_tables) - set(existing_tables)
            if missing_tables:
                print(f"❌ Missing tables: {', '.join(missing_tables)}")
                return False
            else:
                print("✅ All required tables are present")
                return True
                
        except Exception as e:
            print(f"❌ Error verifying tables: {e}")
            return False


def verify_table_data():
    """Verify tables can be accessed and show counts"""
    print("📊 Checking table accessibility and data...")
    app = create_app()
    
    with app.app_context():
        try:
            from app.models import User, Channel, Video, UserChannel, SentimentFeedback
            
            # Count records in each table
            tables = [
                ('users', User),
                ('channels', Channel), 
                ('videos', Video),
                ('user_channels', UserChannel),
                ('sentiment_feedback', SentimentFeedback)
            ]
            
            for table_name, model in tables:
                try:
                    count = model.query.count()
                    print(f"  • {table_name}: {count} records")
                except Exception as e:
                    print(f"  ❌ {table_name}: Error accessing table - {e}")
                    return False
            
            print("✅ All tables are accessible")
            return True
            
        except Exception as e:
            print(f"❌ Error accessing tables: {e}")
            return False


def create_admin_user(non_interactive=False):
    """Prompt to create admin user if none exists"""
    print("👤 Checking for admin users...")
    app = create_app()
    
    with app.app_context():
        try:
            from app.models import User
            
            user_count = User.query.count()
            if user_count == 0:
                print("⚠️  No users found in database.")
                
                if non_interactive:
                    print("ℹ️  Non-interactive mode: Skipping admin user creation")
                    print("💡 Create an admin user later with: python scripts/create_admin.py")
                    return True
                
                response = input("Would you like to create an admin user? (y/N): ").lower().strip()
                
                if response == 'y':
                    print("\n🔧 Creating admin user...")
                    result = subprocess.run(
                        ['python', 'scripts/create_admin.py'],
                        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                    return result.returncode == 0
                else:
                    print("ℹ️  Skipping admin user creation")
                    return True
            else:
                print(f"✅ Found {user_count} existing users")
                return True
                
        except Exception as e:
            print(f"❌ Error checking users: {e}")
            return False


def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description='Deploy production database')
    parser.add_argument('--non-interactive', action='store_true', 
                       help='Run in non-interactive mode (for CI/CD)')
    args = parser.parse_args()
    
    print("🚀 Starting Production Database Deployment")
    if args.non_interactive:
        print("🤖 Running in non-interactive mode")
    print("=" * 50)
    
    # Step 1: Check current migration status
    current_migration = check_migration_status()
    if current_migration is None:
        print("❌ Cannot proceed without knowing migration status")
        return False
    
    # Step 2: Run migrations
    print(f"\n{'='*50}")
    if not run_migrations():
        print("❌ Migration failed - deployment aborted")
        return False
    
    # Step 3: Verify tables exist
    print(f"\n{'='*50}")
    if not verify_tables():
        print("❌ Table verification failed - deployment incomplete")
        return False
    
    # Step 4: Verify table accessibility
    print(f"\n{'='*50}")
    if not verify_table_data():
        print("❌ Table accessibility check failed")
        return False
    
    # Step 5: Optional admin user creation
    print(f"\n{'='*50}")
    if not create_admin_user(non_interactive=args.non_interactive):
        print("⚠️  Admin user creation had issues, but continuing...")
    
    # Final status
    print(f"\n{'='*50}")
    print("🎉 PRODUCTION DATABASE DEPLOYMENT COMPLETE!")
    print("\nDatabase is ready for production use with:")
    print("  ✅ User authentication and management")
    print("  ✅ YouTube channel and video tracking") 
    print("  ✅ Sentiment analysis feedback collection")
    print("  ✅ All required indexes and constraints")
    print("\n💡 Next steps:")
    print("  • Configure your web server")
    print("  • Set up SSL certificates")
    print("  • Configure monitoring and backups")
    print("  • Test the application endpoints")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)