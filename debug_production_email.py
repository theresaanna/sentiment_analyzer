#!/usr/bin/env python3
"""
Production email debug script.
Run this in production environment to test email functionality.
"""
import os
import sys
from flask import Flask
from app import create_app, db
from app.models import User
from app.email import send_password_reset_email, send_email_sync
from app.config import Config

def test_production_email():
    """Test email functionality in production environment."""
    print("=" * 60)
    print("Production Email Debug Test")
    print("=" * 60)
    
    # Create app with production config
    app = create_app(Config)
    
    with app.app_context():
        # Check configuration
        print("\n1. Checking email configuration...")
        config_items = [
            'MAIL_SERVER', 'MAIL_PORT', 'MAIL_USE_TLS', 'MAIL_USE_SSL',
            'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER'
        ]
        
        for item in config_items:
            value = app.config.get(item)
            if item == 'MAIL_PASSWORD':
                # Mask password for security
                display_value = f"{'*' * len(value)}" if value else "Not set"
            else:
                display_value = value if value else "Not set"
            print(f"  {item}: {display_value}")
        
        # Check if required settings are present
        missing = []
        for item in ['MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER']:
            if not app.config.get(item):
                missing.append(item)
        
        if missing:
            print(f"\n❌ Missing required configuration: {', '.join(missing)}")
            return False
        
        print("\n✅ Email configuration looks complete")
        
        # Test database connection and find a test user
        print("\n2. Finding test user...")
        try:
            # Try to find an existing user for testing
            test_user = User.query.first()
            if not test_user:
                print("❌ No users found in database for testing")
                return False
            
            print(f"✅ Found test user: {test_user.email}")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
        
        # Test email sending
        print(f"\n3. Testing password reset email to {test_user.email}...")
        try:
            success = send_password_reset_email(test_user, use_sync=True)
            if success:
                print("✅ Password reset email sent successfully!")
            else:
                print("❌ Failed to send password reset email")
                return False
                
        except Exception as e:
            print(f"❌ Exception during email sending: {e}")
            return False
        
        # Test basic email sending
        print(f"\n4. Testing basic email functionality...")
        try:
            success = send_email_sync(
                subject="Production Email Test",
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[test_user.email],
                text_body="This is a test email from the production environment.",
                html_body="<p>This is a <strong>test email</strong> from the production environment.</p>"
            )
            
            if success:
                print("✅ Basic email test successful!")
            else:
                print("❌ Basic email test failed")
                return False
                
        except Exception as e:
            print(f"❌ Exception during basic email test: {e}")
            return False
        
        print(f"\n" + "=" * 60)
        print("✅ All email tests passed!")
        print("✅ Email functionality is working correctly in production.")
        print("=" * 60)
        return True

if __name__ == "__main__":
    success = test_production_email()
    if not success:
        print("\n❌ Some tests failed. Check the output above for details.")
        sys.exit(1)
    else:
        print("\n🎉 Production email testing completed successfully!")
