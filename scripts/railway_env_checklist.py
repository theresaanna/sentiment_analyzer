#!/usr/bin/env python3
"""
Railway Environment Variables Checklist
This script shows which environment variables need to be set in Railway
"""
import os
from dotenv import load_dotenv

# Load local .env to compare
load_dotenv()

print("=" * 60)
print("REQUIRED RAILWAY ENVIRONMENT VARIABLES")
print("=" * 60)
print("\nAdd these in Railway Dashboard → Variables tab:")
print("(https://railway.app/project/[your-project-id]/service/[service-id]/settings)\n")

# Critical Modal ML Service vars
print("🔴 CRITICAL - Modal ML Service Integration:")
print("─" * 40)
print("MODAL_ML_BASE_URL=https://theresaanna--sentiment-ml-service-fastapi-app.modal.run")
print("  ↳ This is your Modal service endpoint\n")

# Important API Keys
print("🟡 IMPORTANT - External Services:")
print("─" * 40)
print(f"YOUTUBE_API_KEY={os.getenv('YOUTUBE_API_KEY', 'your-youtube-api-key-here')}")
print("  ↳ Required for YouTube data fetching\n")

print(f"SECRET_KEY=generate-a-secure-random-key-for-production")
print("  ↳ Flask secret key (DO NOT use the dev one!)\n")

# Optional but recommended
print("🟢 RECOMMENDED - Performance Settings:")
print("─" * 40)
print("PRECOMPUTE_ANALYSIS_ON_PRELOAD=true")
print("PRELOAD_ANALYSIS_LIMIT=500")
print("PRELOAD_ANALYSIS_METHOD=auto")
print("  ↳ These optimize Modal service usage\n")

# Payment/Auth services (if using)
print("🔵 OPTIONAL - Additional Services:")
print("─" * 40)

if os.getenv('STRIPE_SECRET_KEY'):
    print(f"STRIPE_SECRET_KEY={os.getenv('STRIPE_SECRET_KEY')}")
    print(f"STRIPE_PRICE_ID={os.getenv('STRIPE_PRICE_ID')}")
    print(f"STRIPE_WEBHOOK_SECRET={os.getenv('STRIPE_WEBHOOK_SECRET')}")
    print("  ↳ For payment processing\n")

if os.getenv('GOOGLE_CLIENT_ID'):
    print(f"GOOGLE_CLIENT_ID={os.getenv('GOOGLE_CLIENT_ID')}")
    print(f"GOOGLE_CLIENT_SECRET={os.getenv('GOOGLE_CLIENT_SECRET')}")
    print("  ↳ For Google OAuth login\n")

# Railway auto-provides these
print("✅ AUTO-PROVIDED by Railway (don't set manually):")
print("─" * 40)
print("DATABASE_URL - PostgreSQL connection string")
print("REDIS_URL - Redis connection (if Redis service attached)")
print("PORT - Server port")
print("RAILWAY_ENVIRONMENT - Environment name")
print()

print("=" * 60)
print("HOW TO ADD THESE TO RAILWAY:")
print("=" * 60)
print("""
1. Go to your Railway project dashboard
2. Click on your service (web)
3. Go to the "Variables" tab
4. Click "Raw Editor" for bulk add, or add one by one
5. Paste the variables above (update values as needed)
6. Railway will automatically redeploy

For the SECRET_KEY, generate a secure one with:
  python -c "import secrets; print(secrets.token_hex(32))"
""")

print("=" * 60)
print("VERIFY DEPLOYMENT:")
print("=" * 60)
print("""
After setting variables and redeployment:
1. Check deployment logs: railway logs
2. Visit your app URL
3. Test sentiment analysis functionality
""")