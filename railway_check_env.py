#!/usr/bin/env python3
"""
Railway Environment Check Script
Verifies the environment is ready for deployment
"""
import os
import sys

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking Railway Environment...")
    
    required_vars = [
        'DATABASE_URL',
        'SECRET_KEY', 
        'YOUTUBE_API_KEY'
    ]
    
    optional_vars = [
        'REDIS_URL',
        'MAIL_SERVER',
        'STRIPE_PUBLIC_KEY'
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
        else:
            print(f"✅ {var}: Set")
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
        else:
            print(f"✅ {var}: Set")
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        print("🔧 Set these in Railway Dashboard -> Variables")
        return False
    
    if missing_optional:
        print(f"⚠️  Missing optional environment variables: {', '.join(missing_optional)}")
        print("💡 These are optional but recommended for full functionality")
    
    print("✅ Environment check complete!")
    return True

if __name__ == "__main__":
    success = check_environment()
    sys.exit(0 if success else 1)