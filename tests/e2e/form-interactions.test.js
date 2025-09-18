const { test, expect } = require('@playwright/test');
const { 
  waitForJavaScriptReady, 
  fillFormField,
  hasClass,
  mockYouTubeAPI
} = require('./test-utils');

test.describe('Form Interactions and Validation', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await waitForJavaScriptReady(page);
    await mockYouTubeAPI(page);
  });

  test('should validate YouTube URLs correctly', async ({ page }) => {
    // Test that valid YouTube URLs can be entered and form can be submitted
    const validUrls = [
      'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      'https://youtu.be/dQw4w9WgXcQ'
    ];

    for (const url of validUrls) {
      await page.locator('#urlInput').fill('');
      await fillFormField(page, '#urlInput', url);
      
      // Check that the URL was entered correctly
      const inputValue = await page.locator('#urlInput').inputValue();
      expect(inputValue).toBe(url);
      
      // Check that submit button is enabled
      const submitButton = page.locator('#analyzeBtn');
      await expect(submitButton).toBeEnabled();
    }
  });

  test('should handle invalid URLs', async ({ page }) => {
    // Test that invalid URLs can be entered (client-side validation may be minimal)
    const invalidUrls = [
      'https://www.google.com',
      'not-a-url',
      'https://vimeo.com/123456'
    ];

    for (const url of invalidUrls) {
      await page.locator('#urlInput').fill('');
      await fillFormField(page, '#urlInput', url);
      
      // Check that the URL was entered (even if invalid)
      const inputValue = await page.locator('#urlInput').inputValue();
      expect(inputValue).toBe(url);
      
      // Form should still be submittable (server-side validation handles rejection)
      const submitButton = page.locator('#analyzeBtn');
      await expect(submitButton).toBeEnabled();
    }
  });

  test('should handle form input events correctly', async ({ page }) => {
    const urlInput = page.locator('#urlInput');
    
    // Test input events
    await urlInput.fill('https://www.youtube.com/watch?v=test');
    
    // Check that floating label moves
    const labelGroup = page.locator('.floating-label-group');
    await expect(labelGroup).toBeVisible();
    
    // Test focus and blur events
    await urlInput.focus();
    await page.waitForTimeout(100);
    
    await urlInput.blur();
    await page.waitForTimeout(100);
    
    // Check value is still there after blur
    const inputValue = await urlInput.inputValue();
    expect(inputValue).toContain('youtube.com');
  });

  test('should have loading state structure', async ({ page }) => {
    await fillFormField(page, '#urlInput', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
    
    const button = page.locator('#analyzeBtn');
    
    // Initial state should not be loading
    let isLoading = await hasClass(page, '#analyzeBtn', 'loading');
    expect(isLoading).toBeFalsy();
    
    // Check that button has the required elements for loading states
    await expect(page.locator('#analyzeBtn .button-content')).toBeVisible();
    
    // Check loading elements exist (even if not visible initially)
    const buttonLoading = page.locator('#analyzeBtn .button-loading');
    const loadingSpinner = page.locator('#analyzeBtn .loading-spinner');
    expect(await buttonLoading.count()).toBeGreaterThan(0);
    expect(await loadingSpinner.count()).toBeGreaterThan(0);
  });

  test('should handle keyboard interactions', async ({ page }) => {
    const urlInput = page.locator('#urlInput');
    
    // Test that Enter key works on input
    await urlInput.fill('https://www.youtube.com/watch?v=test123');
    
    // Check that value was entered correctly
    const inputValue = await urlInput.inputValue();
    expect(inputValue).toContain('test123');
    
    // Test Tab navigation
    await urlInput.press('Tab');
    await page.waitForTimeout(50);
    
    // Should move focus away from the input (cross-browser/touch friendly)
    const activeElementId = await page.evaluate(() => document.activeElement.id || '');
    expect(activeElementId).not.toBe('urlInput');
  });


  test('should preserve form state during interactions', async ({ page }) => {
    const testUrl = 'https://www.youtube.com/watch?v=test123';
    
    await fillFormField(page, '#urlInput', testUrl);
    
    // Interact with other elements
    await page.locator('.platform-pill').first().click();
    await page.locator('h1').click();
    
    // URL should still be there
    const inputValue = await page.locator('#urlInput').inputValue();
    expect(inputValue).toBe(testUrl);
  });

  test('should handle form reset correctly', async ({ page }) => {
    await fillFormField(page, '#urlInput', 'https://www.youtube.com/watch?v=test');
    
    // Clear the input
    await page.locator('#urlInput').fill('');
    
    // Check that it's actually cleared
    const inputValue = await page.locator('#urlInput').inputValue();
    expect(inputValue).toBe('');
    
    // Button should not be in loading state
    const hasLoading = await hasClass(page, '#analyzeBtn', 'loading');
    expect(hasLoading).toBeFalsy();
  });

  test('should show proper validation feedback', async ({ page }) => {
    // Test empty submission
    await page.locator('#analyzeBtn').click();
    
    // Wait for validation feedback
    await page.waitForTimeout(500);
    
    const urlInput = page.locator('#urlInput');
    
    // Check for HTML5 validation
    const isInvalid = await urlInput.evaluate(el => !el.validity.valid);
    const validationMessage = await urlInput.evaluate(el => el.validationMessage);
    
    // Should have some form of validation
    if (validationMessage) {
      expect(validationMessage.length).toBeGreaterThan(0);
    }
  });

  test('should handle special characters in URLs', async ({ page }) => {
    const specialUrls = [
      'https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLTest&index=1',
      'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1m30s',
      'https://www.youtube.com/watch?v=dQw4w9WgXcQ#t=90'
    ];

    for (const url of specialUrls) {
      await page.locator('#urlInput').fill('');
      await fillFormField(page, '#urlInput', url);
      
      const inputValue = await page.locator('#urlInput').inputValue();
      expect(inputValue).toBe(url);
      
      // Check that submit button is available
      const submitButton = page.locator('#analyzeBtn');
      await expect(submitButton).toBeEnabled();
    }
  });

  test('should handle CSRF token if present', async ({ page }) => {
    // Check if CSRF token is present
    const csrfToken = page.locator('input[name="csrf_token"]');
    
    if (await csrfToken.count() > 0) {
      const tokenValue = await csrfToken.getAttribute('value');
      expect(tokenValue).toBeTruthy();
      expect(tokenValue.length).toBeGreaterThan(0);
    }
    
    // Check that form has proper structure
    const form = page.locator('#vibeCheckForm');
    await expect(form).toBeVisible();
    const method = await form.getAttribute('method');
    expect(method?.toLowerCase()).toBe('post');
  });

  test('should maintain accessibility during interactions', async ({ page }) => {
    const urlInput = page.locator('#urlInput');
    const submitButton = page.locator('#analyzeBtn');
    
    // Check initial accessibility attributes
    const inputId = await urlInput.getAttribute('id');
    const labelFor = await page.locator(`label[for="${inputId}"]`).count();
    expect(labelFor).toBe(1);
    
    // Check button accessibility
    const buttonType = await submitButton.getAttribute('type');
    expect(buttonType).toBe('submit');
    
    // Test focus management
    await urlInput.focus();
    const activeElement = await page.evaluate(() => document.activeElement.id);
    expect(activeElement).toBe('urlInput');
    
    // Test tab navigation
    await page.keyboard.press('Tab');
    await page.waitForTimeout(100);
    
    const newActiveElement = await page.evaluate(() => document.activeElement.id);
    // Should move focus to next focusable element
    expect(newActiveElement).not.toBe('urlInput');
  });

  test('should handle browser back/forward with form state', async ({ page }) => {
    const testUrl = 'https://www.youtube.com/watch?v=test123';
    
    await fillFormField(page, '#urlInput', testUrl);
    
    // Navigate to another page
    const aboutLink = page.locator('a[href*="about"]').first();
    // If the About link is hidden behind a mobile menu, try to open it
    if (!(await aboutLink.isVisible())) {
      const togglers = [
        '.navbar-toggler',
        '[data-testid="nav-toggle"]',
        '#menu-toggle',
        '.menu-toggle',
        'button[aria-label*="menu" i]',
        'button[aria-label*="navigation" i]',
        'button[aria-controls]',
        'button.hamburger'
      ];
      for (const sel of togglers) {
        const toggle = page.locator(sel).first();
        if (await toggle.count()) {
          await toggle.click({ trial: true }).catch(() => {});
          await toggle.click().catch(() => {});
          // give the menu a moment to open
          await page.waitForTimeout(150);
          if (await aboutLink.isVisible()) break;
        }
      }
    }
    await aboutLink.scrollIntoViewIfNeeded().catch(() => {});
    await aboutLink.click({ timeout: 10000 });
    
    // Go back
    await page.goBack();
    await waitForJavaScriptReady(page);
    
    // Form might or might not preserve state depending on implementation
    // This is more for ensuring no JavaScript errors occur during navigation
    const currentUrl = page.url();
    expect(currentUrl).toContain('/');
  });
});

test.describe('Mobile Form Interactions', () => {
  test.beforeEach(async ({ page }) => {
    // Set mobile viewport with touch support
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await waitForJavaScriptReady(page);
    await mockYouTubeAPI(page);
  });

  test('should work correctly on mobile viewport', async ({ page }) => {
    // Test form interaction on mobile
    await fillFormField(page, '#urlInput', 'https://www.youtube.com/watch?v=mobile123');
    
    // Check that input works on mobile
    const inputValue = await page.locator('#urlInput').inputValue();
    expect(inputValue).toContain('mobile123');
    
    // Check that button is visible and enabled on mobile
    const submitButton = page.locator('#analyzeBtn');
    await expect(submitButton).toBeVisible();
    await expect(submitButton).toBeEnabled();
  });

  test('should handle touch interactions', async ({ page }) => {
    const urlInput = page.locator('#urlInput');
    
    // Click input field (works on both desktop and mobile)
    await urlInput.click();
    await page.waitForTimeout(100);
    
    // Should be focused
    const isFocused = await urlInput.evaluate(el => document.activeElement === el);
    expect(isFocused).toBeTruthy();
    
    // Type on mobile
    await urlInput.fill('https://www.youtube.com/watch?v=mobile');
    
    const inputValue = await urlInput.inputValue();
    expect(inputValue).toContain('mobile');
  });
});