#!/usr/bin/env python3
"""
Run tests on Railway during build phase.
This script sets up the test environment and runs pytest.
If tests fail, the build will be aborted.
"""

import os
import sys
import subprocess

def setup_test_environment():
    """Set up environment variables for testing."""
    test_env = {
        'FLASK_ENV': 'testing',
        'SECRET_KEY': 'railway-test-secret-key',
        'DATABASE_URL': 'sqlite:///test.db',
        'REDIS_URL': 'redis://localhost:6379/0',
        'MODAL_ML_BASE_URL': 'https://theresaanna--sentiment-ml-service-fastapi-app.modal.run',
        'OAUTHLIB_INSECURE_TRANSPORT': '1',
        'CI': 'true',
        'SKIP_MODEL_PRELOAD': 'true',
        'PYTHONPATH': os.getcwd()
    }
    
    # Update environment
    os.environ.update(test_env)
    
    print("✅ Test environment configured")
    for key, value in test_env.items():
        if 'SECRET' not in key and 'PASSWORD' not in key:
            print(f"  {key}={value}")

def run_tests():
    """Run pytest with appropriate options for Railway."""
    print("\n🧪 Running unit tests...")
    print("=" * 60)
    
    # Determine which tests to run based on environment
    skip_integration = os.environ.get('SKIP_INTEGRATION_TESTS', 'true').lower() == 'true'
    
    # Build pytest command
    pytest_args = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',                    # Verbose output
        '--tb=short',           # Short traceback format
        '--maxfail=10',         # Stop after 10 failures
        '--disable-warnings',    # Reduce noise in CI
        '-p', 'no:cacheprovider' # Disable cache in CI
    ]
    
    # Skip integration tests if requested (they might need external services)
    if skip_integration:
        pytest_args.extend([
            '-k', 'not integration and not redis_cloud and not slow',
            '--ignore=tests/test_enhanced_integration.py',
            '--ignore=tests/test_redis_cloud.py'
        ])
        print("ℹ️  Skipping integration tests (SKIP_INTEGRATION_TESTS=true)")
    
    # Add coverage if requested
    if os.environ.get('RAILWAY_COVERAGE', 'false').lower() == 'true':
        pytest_args.extend(['--cov=app', '--cov-report=term-missing'])
    
    # Run tests
    result = subprocess.run(pytest_args)
    
    print("=" * 60)
    
    # Pytest exit code meanings:
    # 0 = success, 1-4 = failures/errors, 5 = no tests collected
    if result.returncode == 0:
        print("✅ All tests passed!")
        return 0
    elif result.returncode == 5:
        print("⚠️  No tests collected (exit code 5). Treating as success in CI.")
        return 0
    else:
        print("❌ Tests failed! Build will be aborted.")
        print(f"   Exit code: {result.returncode}")
        return 1

def main():
    """Main entry point."""
    print("🚂 Railway Test Runner")
    print("=" * 60)
    
    # Check environment variables
    railway_env = os.environ.get('RAILWAY_ENVIRONMENT')
    run_tests = os.environ.get('RAILWAY_RUN_TESTS', 'false').lower()
    skip_tests = os.environ.get('RAILWAY_SKIP_TESTS', 'false').lower()
    
    print(f"Environment: RAILWAY_ENVIRONMENT={railway_env}")
    print(f"Config: RAILWAY_RUN_TESTS={run_tests}")
    print(f"Config: RAILWAY_SKIP_TESTS={skip_tests}")
    print("=" * 60)
    
    # Determine if we should run tests
    if skip_tests == 'true':
        print("⚠️  Tests SKIPPED (RAILWAY_SKIP_TESTS=true)")
        print("   To enable: Set RAILWAY_SKIP_TESTS=false in Railway variables")
        return 0
    
    if run_tests != 'true' and not railway_env:
        print("ℹ️  Tests SKIPPED (not in Railway or RAILWAY_RUN_TESTS!=true)")
        print("   To enable: Set RAILWAY_RUN_TESTS=true in Railway variables")
        return 0
    
    # Tests will run
    print("✅ Tests ENABLED")
    
    # Setup and run
    setup_test_environment()
    exit_code = run_tests()
    
    # Exit with test result code
    sys.exit(exit_code)

if __name__ == '__main__':
    main()