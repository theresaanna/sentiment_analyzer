# End-to-End JavaScript Testing with Playwright

This directory contains Playwright end-to-end tests specifically focused on testing the JavaScript functionality in the VibeCheckAI sentiment analyzer templates.

## Overview

The test suite covers:
- **Homepage JavaScript interactions** - Sparkle animations, form submission loading states, platform switching
- **Analysis status page polling** - Real-time status checking, progress updates, job cancellation
- **Form validation and interactions** - URL validation, input handling, accessibility
- **Mobile responsiveness** - Touch interactions and mobile-specific behaviors

## Setup

### Prerequisites
- Node.js (14+ recommended)
- Python Flask application (for the backend)

### Installation

1. Install Node.js dependencies:
```bash
npm install
```

2. Install Playwright browsers:
```bash
npm run install:browsers
```

3. Install system dependencies (if needed):
```bash
npm run install:deps
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
npm test

# Run tests with UI mode (interactive)
npm run test:ui

# Run tests in headed mode (see browser)
npm run test:headed

# Debug tests step by step
npm run test:debug
```

### Advanced Options

```bash
# Run specific test file
npx playwright test tests/e2e/homepage.test.js

# Run tests in specific browser
npx playwright test --project=chromium

# Run tests in mobile viewport
npx playwright test --project="Mobile Chrome"

# Run tests with verbose output
npx playwright test --reporter=list
```

### View Test Results

```bash
# Show HTML report
npm run test:report

# This opens the interactive HTML report in your browser
```

## Test Structure

### Test Files

- `tests/e2e/homepage.test.js` - Tests homepage JavaScript functionality
  - Sparkle animations
  - Platform switching (YouTube/Instagram/TikTok/etc.)
  - Form submission loading states
  - URL input validation
  - Navigation menu interactions

- `tests/e2e/analysis-status.test.js` - Tests analysis status page functionality
  - Real-time polling for job updates
  - Progress bar updates
  - Status badge changes
  - Job cancellation
  - Time formatting functions

- `tests/e2e/form-interactions.test.js` - Tests form validation and interactions
  - YouTube URL validation
  - Input field behaviors
  - Loading states
  - Keyboard interactions
  - Mobile touch interactions

### Utility Files

- `tests/e2e/test-utils.js` - Shared utility functions
- `tests/e2e/global-setup.js` - Starts Flask server before tests
- `tests/e2e/global-teardown.js` - Stops Flask server after tests

## Key Features Tested

### JavaScript Animations
- ✅ Sparkle animations on homepage
- ✅ Loading spinners and state changes
- ✅ CSS transitions and transforms

### Interactive Elements  
- ✅ Form submission and validation
- ✅ Real-time polling and updates
- ✅ Button state management
- ✅ Platform switching logic

### User Experience
- ✅ Mobile responsiveness
- ✅ Touch interactions
- ✅ Keyboard navigation
- ✅ Accessibility attributes

### Error Handling
- ✅ JavaScript console errors
- ✅ API error responses
- ✅ Network failures
- ✅ Form validation errors

## Configuration

### Playwright Config (`playwright.config.js`)
- Runs tests against `http://127.0.0.1:8000`
- Tests in Chrome, Firefox, Safari, and mobile viewports
- Screenshots on failure
- Video recording for failed tests
- HTML and JSON reports

### Environment Variables
Tests use these Flask environment variables:
- `FLASK_ENV=development`
- `DEBUG=false`
- `DATABASE_URL=sqlite:///:memory:` (test database)
- `TESTING=true`

## Mocking and Test Data

The tests use Playwright's route mocking to:
- Mock YouTube API responses
- Simulate job status updates
- Test error conditions
- Avoid hitting real APIs during testing

### Mock Examples

```javascript
// Mock YouTube analysis API
await page.route('**/api/analyze', async (route) => {
  await route.fulfill({
    status: 200,
    body: JSON.stringify({ success: true, job_id: 'test-123' })
  });
});
```

## Browser Support

Tests run on:
- **Desktop**: Chrome, Firefox, Safari
- **Mobile**: iPhone 12, Pixel 5
- **Tablets**: iPad (if configured)

## Debugging Tests

### Debug Mode
```bash
npm run test:debug
```
This opens the Playwright inspector where you can:
- Step through tests line by line
- Inspect the page at any point
- See network requests
- View console logs

### Visual Debugging
```bash
npm run test:headed
```
Runs tests with the browser visible so you can see what's happening.

### Screenshots and Videos
Failed tests automatically capture:
- Screenshots at the point of failure
- Video recordings of the entire test
- Network logs and console output

All artifacts are saved to `test-results/`

## Continuous Integration

To run tests in CI:

```bash
# Install dependencies
npm ci
npx playwright install --with-deps

# Run tests
npm test
```

### GitHub Actions Example
```yaml
- name: Run Playwright tests
  run: |
    npm ci
    npx playwright install --with-deps
    npm test
```

## Troubleshooting

### Common Issues

**Flask server won't start:**
- Check that `run.py` exists and is executable
- Ensure all Python dependencies are installed
- Check port 8000 isn't already in use

**Tests timing out:**
- Increase timeouts in `playwright.config.js`
- Check network connectivity
- Ensure Flask server starts successfully

**Flaky tests:**
- Add more `waitForTimeout()` calls
- Use `waitForSelector()` instead of fixed timeouts
- Check for race conditions in JavaScript

### Logs and Debugging

```bash
# Run with debug output
DEBUG=pw:api npm test

# See all network requests
npm test -- --trace on
```

## Writing New Tests

### Test Structure
```javascript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForJavaScriptReady(page);
  });

  test('should do something', async ({ page }) => {
    // Test implementation
  });
});
```

### Best Practices
1. Use utility functions from `test-utils.js`
2. Mock external APIs
3. Wait for JavaScript to be ready
4. Test both positive and negative cases
5. Check for console errors
6. Verify accessibility attributes

### Useful Selectors
- `#urlInput` - Main URL input field
- `#analyzeBtn` - Submit button
- `.sparkle` - Animated sparkle elements
- `.progress-bar` - Analysis progress bar
- `.platform-pill` - Platform selection buttons

## Performance Testing

The tests also verify:
- Page load times
- JavaScript execution time
- Animation performance
- Memory leaks (basic detection)

## Accessibility Testing

Each test file includes accessibility checks:
- ARIA attributes
- Keyboard navigation
- Focus management
- Screen reader compatibility

## Contributing

When adding new JavaScript functionality to templates:

1. Add corresponding tests
2. Update existing tests if behavior changes
3. Run tests locally before committing
4. Check both desktop and mobile viewports

---

For more information about Playwright: https://playwright.dev/docs/intro