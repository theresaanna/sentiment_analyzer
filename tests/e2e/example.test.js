const { test, expect } = require('@playwright/test');

test.describe('Example Tests - Setup Verification', () => {
  
  test('should be able to access the homepage', async ({ page }) => {
    // This is a simple test to verify that the setup is working
    await page.goto('/');
    
    // Check that the page loaded
    await expect(page).toHaveTitle(/VibeCheckAI/);
    
    // Check for key elements
    await expect(page.locator('h1')).toBeVisible();
    
    console.log('✅ Homepage loads successfully');
    console.log('✅ Playwright setup is working');
    console.log('✅ Flask server is running');
  });

  test('should have no JavaScript errors on page load', async ({ page }) => {
    const jsErrors = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        jsErrors.push(msg.text());
      }
    });
    
    await page.goto('/');
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    
    // Filter out common acceptable errors
    const realErrors = jsErrors.filter(error => 
      !error.includes('favicon') && 
      !error.includes('404') &&
      !error.includes('ERR_CONNECTION_REFUSED')
    );
    
    expect(realErrors).toHaveLength(0);
    console.log('✅ No JavaScript console errors detected');
  });
});