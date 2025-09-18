const { expect } = require('@playwright/test');

/**
 * Wait for an element to be visible and stable
 * @param {import('@playwright/test').Page} page 
 * @param {string} selector 
 * @param {number} timeout 
 */
async function waitForElement(page, selector, timeout = 10000) {
  await page.waitForSelector(selector, { state: 'visible', timeout });
  // Wait a bit more for any animations to complete
  await page.waitForTimeout(100);
}

/**
 * Wait for JavaScript to be loaded and executed
 * @param {import('@playwright/test').Page} page 
 */
async function waitForJavaScriptReady(page) {
  // Wait for document ready state
  await page.waitForFunction(() => document.readyState === 'complete');
  
  // Wait for any initial JavaScript execution
  await page.waitForTimeout(500);
}

/**
 * Check if sparkles are being created on the page
 * @param {import('@playwright/test').Page} page 
 */
async function checkSparklesAnimation(page) {
  // Wait for sparkle container to exist
  await waitForElement(page, '.sparkle-container');
  
  // Wait for sparkles to be created
  await page.waitForTimeout(1000);
  
  // Check if sparkles exist
  const sparkleCount = await page.locator('.sparkle').count();
  expect(sparkleCount).toBeGreaterThan(0);
  
  return sparkleCount;
}

/**
 * Fill a form field and trigger change events
 * @param {import('@playwright/test').Page} page 
 * @param {string} selector 
 * @param {string} value 
 */
async function fillFormField(page, selector, value) {
  await page.locator(selector).fill(value);
  // Trigger blur to ensure validation runs
  await page.locator(selector).blur();
  await page.waitForTimeout(100);
}

/**
 * Check if an element has a specific class
 * @param {import('@playwright/test').Page} page 
 * @param {string} selector 
 * @param {string} className 
 */
async function hasClass(page, selector, className) {
  const element = page.locator(selector);
  const classes = await element.getAttribute('class');
  return classes && classes.split(' ').includes(className);
}

/**
 * Wait for form submission state changes
 * @param {import('@playwright/test').Page} page 
 * @param {string} buttonSelector 
 */
async function waitForFormSubmission(page, buttonSelector = '#analyzeBtn') {
  // Click the submit button
  await page.locator(buttonSelector).click();
  
  // Wait for loading state
  await page.waitForFunction(
    (selector) => {
      const btn = document.querySelector(selector);
      return btn && btn.classList.contains('loading');
    },
    buttonSelector,
    { timeout: 5000 }
  );
}

/**
 * Mock YouTube API responses for testing
 * @param {import('@playwright/test').Page} page 
 */
async function mockYouTubeAPI(page) {
  // Mock successful video analysis
  await page.route('**/api/analyze', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          job_id: 'test-job-123',
          message: 'Analysis started'
        })
      });
    }
  });
  
  // Mock job status endpoint
  await page.route('**/api/analyze/job/test-job-123', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-job-123',
        status: 'processing',
        progress: 50,
        video_title: 'Test Video',
        comment_count_processed: 50,
        comment_count_requested: 100
      })
    });
  });
}

/**
 * Check for console errors (excluding known acceptable ones)
 * @param {import('@playwright/test').Page} page 
 */
async function checkForConsoleErrors(page) {
  const errors = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Filter out known acceptable errors
      if (!text.includes('favicon') && 
          !text.includes('404') && 
          !text.includes('net::ERR_CONNECTION_REFUSED')) {
        errors.push(text);
      }
    }
  });
  
  return errors;
}

/**
 * Simulate platform switching interaction
 * @param {import('@playwright/test').Page} page 
 * @param {string} platform - youtube, instagram, tiktok, etc.
 */
async function switchPlatform(page, platform) {
  const platformSelector = `[data-platform="${platform}"]`;
  await page.locator(platformSelector).click();
  
  // Wait for any UI updates
  await page.waitForTimeout(200);
  
  // Check if platform switched
  const isActive = await hasClass(page, platformSelector, 'active');
  return isActive;
}

/**
 * Check URL validation behavior
 * @param {import('@playwright/test').Page} page 
 * @param {string} url 
 * @param {boolean} shouldBeValid 
 */
async function testURLValidation(page, url, shouldBeValid = true) {
  await fillFormField(page, '#urlInput', url);
  
  // Try to submit
  await page.locator('#analyzeBtn').click();
  
  if (shouldBeValid) {
    // Should start processing or redirect
    await page.waitForTimeout(1000);
    const hasError = await page.locator('.error-message').isVisible().catch(() => false);
    expect(hasError).toBeFalsy();
  } else {
    // Should show validation error
    await waitForElement(page, '.error-message');
    const errorVisible = await page.locator('.error-message').isVisible();
    expect(errorVisible).toBeTruthy();
  }
}

module.exports = {
  waitForElement,
  waitForJavaScriptReady,
  checkSparklesAnimation,
  fillFormField,
  hasClass,
  waitForFormSubmission,
  mockYouTubeAPI,
  checkForConsoleErrors,
  switchPlatform,
  testURLValidation
};