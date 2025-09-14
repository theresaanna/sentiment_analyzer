# Railway Testing Configuration Guide

## Overview
Tests can be configured to run automatically during Railway deployments. This ensures code quality before your app goes live.

## Quick Start

### Enable Tests in Railway
Add this environment variable in your Railway dashboard:
```
RAILWAY_RUN_TESTS=true
```

### Disable Tests (for faster deployments)
```
RAILWAY_RUN_TESTS=false
```
Or:
```
RAILWAY_SKIP_TESTS=true
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAILWAY_RUN_TESTS` | `false` | Set to `true` to enable tests during build |
| `RAILWAY_SKIP_TESTS` | `false` | Set to `true` to skip all tests (overrides RUN_TESTS) |
| `SKIP_INTEGRATION_TESTS` | `true` | Skip tests that need external services |
| `RAILWAY_COVERAGE` | `false` | Generate coverage reports during tests |

## How It Works

1. **Build Phase**: Railway runs `nixpacks.toml` configuration
2. **Test Phase**: Executes `scripts/run_tests_railway.py`
3. **Decision**: 
   - If tests pass → Deployment continues
   - If tests fail → Deployment is aborted

## Test Categories

### Unit Tests (Always Run)
- Fast, isolated tests
- No external dependencies
- ~30 seconds to complete

### Integration Tests (Skipped by Default)
- Require external services (Redis, DB)
- Slower execution
- Enable with: `SKIP_INTEGRATION_TESTS=false`

## Recommended Settings

### For Production
```env
RAILWAY_RUN_TESTS=true
SKIP_INTEGRATION_TESTS=true
```
✅ Runs unit tests only (fast, reliable)

### For Staging
```env
RAILWAY_RUN_TESTS=true
SKIP_INTEGRATION_TESTS=false
RAILWAY_COVERAGE=true
```
✅ Full test suite with coverage

### For Quick Fixes
```env
RAILWAY_SKIP_TESTS=true
```
⚠️ Skips all tests (use sparingly!)

## Test Output

When tests run, you'll see:
```
🚂 Railway Test Runner
============================================================
Environment: RAILWAY_ENVIRONMENT=production
Config: RAILWAY_RUN_TESTS=true
Config: RAILWAY_SKIP_TESTS=false
============================================================
✅ Tests ENABLED
✅ Test environment configured
🧪 Running unit tests...
============================================================
tests/test_api.py::test_analyze_endpoint PASSED
tests/test_auth.py::test_login PASSED
...
============================================================
✅ All tests passed!
```

## Troubleshooting

### Tests Not Running?
Check Railway logs:
```bash
railway logs | grep "Railway Test Runner"
```

Verify environment variables:
```bash
railway variables
```

### Tests Failing?
1. Check the specific test output in Railway logs
2. Run locally first: `make test`
3. Ensure Modal service is accessible
4. Verify all environment variables are set

### Need to Deploy Urgently?
Temporarily disable tests:
```bash
railway variables set RAILWAY_SKIP_TESTS=true
railway up
```
**Remember to re-enable after fixing!**

## Local Testing

Before pushing to Railway:
```bash
# Quick unit tests
make test-quick

# Full test suite
make test

# Test Modal integration
make test-modal
```

## Best Practices

1. **Always test locally first**: `make test` before pushing
2. **Keep tests fast**: Skip slow integration tests in production
3. **Monitor test times**: If tests take >2 minutes, optimize
4. **Use skip sparingly**: Only disable tests for emergency fixes
5. **Fix failing tests immediately**: Don't let them accumulate

## Related Files

- `nixpacks.toml` - Railway build configuration
- `scripts/run_tests_railway.py` - Test runner script
- `Makefile` - Local test commands
- `.env` - Local environment variables