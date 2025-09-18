# Testing Quick Start Guide

## 🚀 Automated Pre-Push Testing

Your repository is now configured to automatically run both Python unit tests and Playwright JavaScript e2e tests when pushing to production branches (`main`, `master`, or `production`).

## How It Works

When you push to a production branch:
1. **Python unit tests** run first (fast, essential functionality)
2. **Playwright e2e tests** run second (JavaScript functionality in templates)
3. Push is **blocked** if any tests fail
4. Push **proceeds** only if all tests pass

## Manual Test Commands

### Run All Tests (Like Pre-Push)
```bash
./run_pre_push_tests.sh
# or
npm run pre-push
```

### Run Only JavaScript E2E Tests
```bash
npm test                    # All e2e tests
npm run test:fast          # Quick version (for pre-push)
npm run test:ui            # Interactive mode
npm run test:debug         # Debug mode
```

### Run Specific Test Files
```bash
npm run test:example       # Basic setup verification
npm run test:homepage      # Homepage JavaScript features
npm run test:status        # Analysis status page polling
npm run test:forms         # Form validation and interactions
```

### Run Only Python Tests
```bash
pytest tests/ -k "not integration and not slow"
```

## What Gets Tested

### ✨ JavaScript Functionality
- **Sparkle animations** on homepage
- **Form submission** loading states
- **Real-time polling** on analysis status page
- **Platform switching** (YouTube/Instagram/TikTok buttons)
- **URL validation** and input handling
- **Mobile responsiveness** and touch interactions
- **Accessibility** attributes and keyboard navigation

### 🐍 Python Functionality  
- Unit tests for Flask routes
- Model functionality
- API endpoints
- Business logic

## Quick Setup Verification

Test that everything is working:
```bash
npm run test:example
```

This should:
- ✅ Start Flask server on port 8001
- ✅ Load homepage successfully
- ✅ Verify no JavaScript console errors
- ✅ Stop Flask server cleanly

## Troubleshooting

**Port conflicts:**
- Tests use port 8001 (not 8000) to avoid conflicts
- Old processes are automatically killed

**Missing dependencies:**
```bash
npm install                 # Install Node.js dependencies
npx playwright install      # Install browser binaries
```

**Tests failing:**
```bash
npm run test:ui            # Debug interactively
npm run test:headed        # Watch tests run
npm run test:report        # View detailed results
```

**Skip e2e tests temporarily:**
Push to a feature branch instead of `main`/`master`/`production`

## Performance

- **Python tests**: ~10-30 seconds
- **JavaScript e2e tests**: ~1-3 minutes
- **Total pre-push time**: ~2-4 minutes

The pre-push hook uses optimized settings:
- Shorter timeouts (30s vs 10s)
- Single worker process
- Only 1 retry attempt

## Benefits

✅ **Catch JavaScript bugs** before they reach production  
✅ **Ensure cross-browser compatibility** (Chrome, Firefox, Safari)  
✅ **Test mobile responsiveness** automatically  
✅ **Verify real user interactions** work correctly  
✅ **No broken deployments** due to frontend issues  

Your JavaScript functionality is now protected by comprehensive automated testing! 🎉