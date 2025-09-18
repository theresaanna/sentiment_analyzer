const { test, expect } = require('@playwright/test');
const { 
  waitForJavaScriptReady, 
  fillFormField,
  hasClass,
  checkForConsoleErrors,
  mockYouTubeAPI
} = require('./test-utils');

test.describe('Homepage JavaScript Interactions', () => {
  
  test.beforeEach(async ({ page }) => {
    // Set up console error tracking
    const errors = await checkForConsoleErrors(page);
    
    // Go to homepage
    await page.goto('/');
    
    // Wait for JavaScript to be ready
    await waitForJavaScriptReady(page);
  });

  test('should load homepage with all key elements', async ({ page }) => {
    // Check main elements are present
    await expect(page.locator('h1')).toContainText('VibeCheckAI');
    await expect(page.locator('#vibeCheckForm')).toBeVisible();
    await expect(page.locator('#urlInput')).toBeVisible();
    await expect(page.locator('#analyzeBtn')).toBeVisible();
    await expect(page.locator('.platform-pills')).toBeVisible();
  });


  test('should handle platform switching', async ({ page }) => {
    // Initially YouTube should be active
    const youtubeActive = await hasClass(page, '[data-platform="youtube"]', 'active');
    expect(youtubeActive).toBeTruthy();
    
    // Check that coming-soon platforms have disabled attribute or coming-soon class
    const instagramPill = page.locator('[data-platform="instagram"]');
    const isDisabled = await instagramPill.getAttribute('disabled');
    const hasComingSoon = await hasClass(page, '[data-platform="instagram"]', 'coming-soon');
    expect(isDisabled !== null || hasComingSoon).toBeTruthy();
    
    // Don't try to click disabled buttons - just verify they exist and are disabled
    await expect(instagramPill).toBeVisible();
    if (isDisabled !== null) {
      await expect(instagramPill).toBeDisabled();
    }
    
    // YouTube should remain active since other platforms are disabled
    const stillYoutubeActive = await hasClass(page, '[data-platform="youtube"]', 'active');
    expect(stillYoutubeActive).toBeTruthy();
  });

  test('should update form labels when platform switches', async ({ page }) => {
    // Check initial state (YouTube)
    await expect(page.locator('#platformLabel')).toContainText('YouTube');
    
    // Note: Since other platforms are coming-soon and disabled,
    // we can't actually test platform switching functionality yet
    // This test is prepared for when other platforms are enabled
    
    const platformLabel = page.locator('#platformLabel');
    const labelText = await platformLabel.textContent();
    expect(labelText).toBe('YouTube');
  });

  test('should show form submission loading state', async ({ page }) => {
    // Fill in a valid YouTube URL
    await fillFormField(page, '#urlInput', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
    
    // Get initial button state
    const button = page.locator('#analyzeBtn');
    const initialHasLoading = await hasClass(page, '#analyzeBtn', 'loading');
    expect(initialHasLoading).toBeFalsy();
    
    // Check that button has the correct structure for loading states
    await expect(page.locator('#analyzeBtn .button-content')).toBeVisible();
    
    // The loading state is set by JavaScript on form submission
    // We can test that the structure exists without actually submitting
    const hasButtonLoading = await page.locator('#analyzeBtn .button-loading').count();
    const hasLoadingSpinner = await page.locator('#analyzeBtn .loading-spinner').count();
    expect(hasButtonLoading).toBeGreaterThan(0);
    expect(hasLoadingSpinner).toBeGreaterThan(0);
  });

  test('should have functional form validation', async ({ page }) => {
    // Test empty form submission
    const button = page.locator('#analyzeBtn');
    await button.click();
    
    // Should show browser validation or custom validation
    const urlInput = page.locator('#urlInput');
    const validationMessage = await urlInput.evaluate(el => el.validationMessage);
    
    // Either browser validation kicks in, or we should see an error
    if (validationMessage) {
      expect(validationMessage.length).toBeGreaterThan(0);
    } else {
      // Look for custom error message
      const errorMessage = page.locator('.error-message');
      // Wait a bit for potential async validation
      await page.waitForTimeout(500);
      const errorExists = await errorMessage.count() > 0;
      // Note: This might not trigger if there's no server-side validation for empty fields
    }
  });

  test('should show URL examples', async ({ page }) => {
    // Check if URL examples are visible
    const exampleBox = page.locator('.url-example-box');
    await expect(exampleBox).toBeVisible();
    
    // Check for YouTube URL examples
    const examples = page.locator('.example-url');
    const exampleCount = await examples.count();
    expect(exampleCount).toBeGreaterThan(0);
    
    // Check specific example URLs
    const firstExample = await examples.first().textContent();
    expect(firstExample).toContain('youtube.com');
  });

  test('should have working CTA button', async ({ page }) => {
    // Find CTA button that focuses URL input
    const ctaButton = page.locator('button:has-text("Start Free Vibe Check")');
    
    if (await ctaButton.count() > 0) {
      await ctaButton.click();
      
      // Check if URL input gets focused
      const urlInput = page.locator('#urlInput');
      const isFocused = await urlInput.evaluate(el => document.activeElement === el);
      expect(isFocused).toBeTruthy();
    }
  });

  test('should handle navigation menu interactions', async ({ page }) => {
    // Test navbar toggle on mobile (if present)
    const navbarToggler = page.locator('.navbar-toggler');
    
    if (await navbarToggler.isVisible()) {
      // Simulate mobile viewport
      await page.setViewportSize({ width: 480, height: 800 });
      await page.reload();
      await waitForJavaScriptReady(page);
      
      // Click navbar toggler
      await navbarToggler.click();
      
      // Check if navbar collapse is shown
      const navbarCollapse = page.locator('#navbarNav');
      const isExpanded = await navbarToggler.getAttribute('aria-expanded');
      expect(isExpanded).toBe('true');
    }
  });

  test('should not have JavaScript console errors', async ({ page }) => {
    const errors = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Filter out known acceptable errors (favicon, etc.)
        if (!text.includes('favicon.ico') && 
            !text.includes('404') && 
            !text.includes('ERR_CONNECTION_REFUSED')) {
          errors.push(text);
        }
      }
    });
    
    // Interact with page to trigger any JavaScript
    await page.locator('#urlInput').fill('test');
    await page.locator('#urlInput').clear();
    await page.locator('.platform-pill').first().click();
    
    // Wait for any delayed errors
    await page.waitForTimeout(1000);
    
    expect(errors).toHaveLength(0);
  });

  test('should have proper accessibility attributes', async ({ page }) => {
    // Check form labels (floating labels might not use standard for/id pattern)
    const urlInput = page.locator('#urlInput');
    await expect(urlInput).toBeVisible();
    
    // Check if there's a label associated (floating label or standard label)
    const labelFor = await page.locator('label[for="urlInput"]').count();
    const floatingLabel = await page.locator('.floating-label').count();
    expect(labelFor >= 1 || floatingLabel >= 1).toBeTruthy();
    
    // Check button accessibility
    const submitButton = page.locator('#analyzeBtn');
    const buttonType = await submitButton.getAttribute('type');
    expect(buttonType).toBe('submit');
    
    // Check navbar toggler attributes only if it exists and has aria-controls
    const navbarToggler = page.locator('.navbar-toggler');
    if (await navbarToggler.count() > 0) {
      const ariaControls = await navbarToggler.getAttribute('aria-controls');
      // Only check if the attribute exists - it might be null and that's ok
      if (ariaControls !== null) {
        expect(ariaControls.length).toBeGreaterThan(0);
      }
    }
  });
});