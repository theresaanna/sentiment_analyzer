#!/usr/bin/env python3
"""
Check if the deployment is ready for the analysis queue feature.
"""
import sys
from app import create_app, db
from app.models import AnalysisJob, User

def check_deployment_ready():
    """Check if all components are ready for deployment."""
    app = create_app()
    
    with app.app_context():
        print("🔍 Checking deployment readiness...\n")
        
        # Check 1: Database migrations
        print("1. Checking database migrations...")
        try:
            # Try to query the AnalysisJob table
            count = AnalysisJob.query.count()
            print(f"   ✅ AnalysisJob table exists ({count} jobs)")
        except Exception as e:
            print(f"   ❌ AnalysisJob table missing: {e}")
            print("   Run: flask db upgrade")
            return False
        
        # Check 2: Required files
        print("\n2. Checking required files...")
        import os
        required_files = [
            'analysis_worker.py',
            'Procfile',
            'railway.json',
            'migrations/versions/cfe8c2fdf688_add_analysisjob_table_for_queued_.py'
        ]
        
        for file in required_files:
            if os.path.exists(file):
                print(f"   ✅ {file}")
            else:
                print(f"   ❌ {file} missing")
                return False
        
        # Check 3: Procfile content
        print("\n3. Checking Procfile configuration...")
        with open('Procfile', 'r') as f:
            content = f.read()
            if 'flask db upgrade' in content:
                print("   ✅ Migrations configured in Procfile")
            else:
                print("   ⚠️  Migrations not in Procfile (but configured in railway.json)")
            
            if 'worker:' in content:
                print("   ✅ Worker process configured")
            else:
                print("   ❌ Worker process not configured")
                return False
        
        # Check 4: Railway configuration
        print("\n4. Checking Railway configuration...")
        import json
        with open('railway.json', 'r') as f:
            config = json.load(f)
            start_cmd = config.get('deploy', {}).get('startCommand', '')
            if 'flask db upgrade' in start_cmd:
                print("   ✅ Migrations configured in Railway")
            else:
                print("   ❌ Migrations not configured in Railway")
                return False
        
        # Check 5: Environment variables
        print("\n5. Checking environment variables...")
        import os
        env_vars = {
            'DATABASE_URL': os.getenv('DATABASE_URL'),
            'REDIS_URL': os.getenv('REDIS_URL'),
            'YOUTUBE_API_KEY': os.getenv('YOUTUBE_API_KEY'),
            'MODAL_ML_BASE_URL': os.getenv('MODAL_ML_BASE_URL')
        }
        
        for var, value in env_vars.items():
            if value:
                print(f"   ✅ {var} is set")
            else:
                print(f"   ⚠️  {var} not set locally (ensure it's set in production)")
        
        print("\n" + "="*50)
        print("✅ Deployment is READY!")
        print("\nNext steps:")
        print("1. Commit all changes: git add . && git commit -m 'Add analysis queue system'")
        print("2. Push to GitHub: git push origin main")
        print("3. Railway will automatically deploy")
        print("4. Create a second Railway service named 'worker' with start command: python analysis_worker.py")
        print("5. Share all environment variables between web and worker services")
        
        return True

if __name__ == '__main__':
    ready = check_deployment_ready()
    sys.exit(0 if ready else 1)