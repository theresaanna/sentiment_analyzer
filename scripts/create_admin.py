#!/usr/bin/env python
"""
Create an admin user for production deployment.
Can be run locally with DATABASE_URL or on Railway.
"""
import os
import sys
import getpass
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Railway's postgres:// URL if needed
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)

from app import create_app, db
from app.models import User


def create_admin_user():
    """Create an admin user interactively or from environment variables."""
    app = create_app()
    
    with app.app_context():
        print("🔐 Create Admin User")
        print("=" * 50)
        
        # Check if running in production
        is_production = os.environ.get('FLASK_ENV') == 'production'
        
        # Get user details from environment or prompt
        if os.environ.get('ADMIN_EMAIL') and os.environ.get('ADMIN_PASSWORD'):
            # Use environment variables (for automated setup)
            email = os.environ.get('ADMIN_EMAIL')
            password = os.environ.get('ADMIN_PASSWORD')
            name = os.environ.get('ADMIN_NAME', 'Admin')
            print(f"Creating admin user from environment variables: {email}")
        else:
            # Interactive mode
            print("\nEnter admin user details:")
            name = input("Name (default: Admin): ").strip() or "Admin"
            email = input("Email: ").strip()
            
            if not email:
                print("❌ Email is required!")
                return False
            
            # Password input with confirmation
            while True:
                password = getpass.getpass("Password: ")
                password_confirm = getpass.getpass("Confirm password: ")
                
                if password != password_confirm:
                    print("❌ Passwords don't match. Try again.")
                    continue
                
                if len(password) < 8:
                    print("❌ Password must be at least 8 characters.")
                    continue
                
                break
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"⚠️  User with email {email} already exists.")
            
            if not is_production:
                response = input("Update password for existing user? (y/n): ")
                if response.lower() == 'y':
                    existing_user.set_password(password)
                    existing_user.name = name
                    existing_user.is_subscribed = True  # Make admin a subscribed user
                    db.session.commit()
                    print(f"✅ Updated password for {email}")
                else:
                    print("❌ Cancelled.")
            else:
                print("Use the web interface to manage existing users.")
            
            return existing_user
        
        # Create new user
        try:
            user = User(
                name=name,
                email=email,
                is_subscribed=True,  # Admins get premium access
                created_at=datetime.utcnow()
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            print(f"\n✅ Admin user created successfully!")
            print(f"   Email: {email}")
            print(f"   Name: {name}")
            print(f"   Subscribed: Yes")
            print(f"\nYou can now log in at /login")
            
            return user
            
        except Exception as e:
            print(f"❌ Failed to create user: {e}")
            db.session.rollback()
            return None


def create_default_admin():
    """Create a default admin user for quick setup."""
    app = create_app()
    
    with app.app_context():
        # Default admin credentials (CHANGE THESE!)
        email = "admin@example.com"
        password = "changeme123"
        name = "Admin"
        
        print("⚠️  Creating DEFAULT admin user (CHANGE PASSWORD IMMEDIATELY!)")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print("Default admin already exists.")
            return existing_user
        
        user = User(
            name=name,
            email=email,
            is_subscribed=True,
            created_at=datetime.utcnow()
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print("✅ Default admin created. CHANGE THE PASSWORD!")
        return user


def list_users():
    """List all existing users."""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("No users found in database.")
            return
        
        print(f"\n📋 Existing Users ({len(users)} total):")
        print("-" * 70)
        for user in users:
            sub_status = "✓ Subscribed" if user.is_subscribed else "✗ Free"
            print(f"  {user.email:<30} {user.name:<20} {sub_status}")
        print()


def main():
    """Main function with CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Admin user management')
    parser.add_argument('--list', action='store_true', 
                       help='List all existing users')
    parser.add_argument('--default', action='store_true',
                       help='Create default admin (for testing only!)')
    parser.add_argument('--email', type=str,
                       help='Admin email (for non-interactive mode)')
    parser.add_argument('--password', type=str,
                       help='Admin password (for non-interactive mode)')
    parser.add_argument('--name', type=str, default='Admin',
                       help='Admin name')
    
    args = parser.parse_args()
    
    if args.list:
        list_users()
    elif args.default:
        create_default_admin()
    elif args.email and args.password:
        # Non-interactive mode
        os.environ['ADMIN_EMAIL'] = args.email
        os.environ['ADMIN_PASSWORD'] = args.password
        os.environ['ADMIN_NAME'] = args.name
        create_admin_user()
    else:
        # Interactive mode
        create_admin_user()


if __name__ == '__main__':
    main()
