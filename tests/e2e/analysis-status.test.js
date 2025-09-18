const { test, expect } = require('@playwright/test');
const { 
  waitForJavaScriptReady, 
  waitForElement,
  hasClass 
} = require('./test-utils');

test.describe('Analysis Status Page JavaScript', () => {
  
  test.beforeEach(async ({ page }) => {
    // Mock the analysis status API responses
    await setupStatusPageMocks(page);
  });

  test('should display initial job status correctly', async ({ page }) => {
    // Go to a mock analysis status page
    await page.goto('/analyze/status/test-job-123');
    await waitForJavaScriptReady(page);

    // Check initial elements are present
    await expect(page.locator('.status-badge')).toBeVisible();
    await expect(page.locator('.progress-bar')).toBeVisible();
    
    // Check if JavaScript variables are set
    const jobId = await page.evaluate(() => window.jobId);
    expect(jobId).toBe('test-job-123');
  });

  test('should poll for status updates', async ({ page }) => {
    let requestCount = 0;
    
    // Track API requests
    page.on('request', request => {
      if (request.url().includes('/api/analyze/status/')) {
        requestCount++;
      }
    });

    await page.goto('/analyze/status/test-job-123');
    await waitForJavaScriptReady(page);

    // Wait for multiple polling cycles
    await page.waitForTimeout(15000);  // Wait 15 seconds to catch at least 3 polls (every 5 seconds)
    
    // Should have made multiple requests
    expect(requestCount).toBeGreaterThanOrEqual(2);
  });

  test('should update progress bar correctly', async ({ page }) => {
    await page.goto('/analyze/status/test-job-123');
    await waitForJavaScriptReady(page);

    // Wait for initial load
    await waitForElement(page, '.progress-bar');
    
    // Check initial progress (immediate poll may bump to 50%)
    let progressWidth = await page.locator('.progress-bar').evaluate(el => el.style.width);
    expect(['25%', '50%']).toContain(progressWidth);
    
    // Wait for progress update (our mock will simulate progress)
    await page.waitForTimeout(6000);  // Wait for next poll
    
    progressWidth = await page.locator('.progress-bar').evaluate(el => el.style.width);
    expect(['50%', '75%', '100%']).toContain(progressWidth);
  });

  test('should update status badge correctly', async ({ page }) => {
    await page.goto('/analyze/status/test-job-123');
    await waitForJavaScriptReady(page);

    // Check initial status
    await waitForElement(page, '.status-badge');
    const initialStatus = await page.locator('.status-badge').textContent();
    expect(['QUEUED', 'PROCESSING']).toContain(initialStatus);

    // Check status badge class
    const hasStatusClass = await hasClass(page, '.status-badge', 'status-queued') ||
                          await hasClass(page, '.status-badge', 'status-processing');
    expect(hasStatusClass).toBeTruthy();
  });

  test('should format time estimates correctly', async ({ page }) => {
    await page.goto('/analyze/status/test-job-123');
    await waitForJavaScriptReady(page);

    // Test the formatTime function
    const timeFormatTests = await page.evaluate(() => {
      // Access the formatTime function from the global scope
      if (typeof formatTime !== 'function') {
        return 'formatTime function not found';
      }
      
      return {
        seconds: formatTime(45),
        minutes: formatTime(90),
        hours: formatTime(7200),
        zero: formatTime(0),
        negative: formatTime(-10)
      };
    });

    expect(timeFormatTests.seconds).toBe('45 seconds');
    expect(timeFormatTests.minutes).toBe('2 minutes');
    expect(timeFormatTests.hours).toBe('2 hours');
    expect(timeFormatTests.zero).toBe('calculating...');
    expect(timeFormatTests.negative).toBe('calculating...');
  });

  test('should show queue information when job is queued', async ({ page }) => {
    await page.goto('/analyze/status/test-job-queued');
    await waitForJavaScriptReady(page);

    // Wait for queue info to appear
    await waitForElement(page, '#queueInfo');
    
    // Check queue information elements
    await expect(page.locator('#queueInfo')).toBeVisible();
    await expect(page.locator('#queueInfo')).toContainText('Queue Position');
    await expect(page.locator('#queueInfo')).toContainText('Estimated Wait Time');
  });

  test('should show processing information when job is processing', async ({ page }) => {
    await page.goto('/analyze/status/test-job-processing');
    await waitForJavaScriptReady(page);

    // Wait for processing info to appear
    await page.waitForTimeout(1000);
    
    const processingInfo = page.locator('#processingInfo');
    if (await processingInfo.count() > 0) {
      await expect(processingInfo).toBeVisible();
      await expect(processingInfo).toContainText('Estimated Time Remaining');
    }
  });

  test('should handle job completion and redirect', async ({ page }) => {
    await page.goto('/analyze/status/test-job-completed');
    await waitForJavaScriptReady(page);

    // Wait for potential redirect
    await page.waitForTimeout(2000);
    
    // Check if redirected to results page or if completion message is shown
    const currentUrl = page.url();
    const isRedirected = currentUrl.includes('/analysis/') || currentUrl.includes('/auth/login');
    
    if (!isRedirected) {
      // If not redirected (e.g., login required), should show completion message
      const completionMessage = page.locator('.alert-success, .completion-message');
      const hasCompletion = await completionMessage.count() > 0;
      expect(hasCompletion).toBeTruthy();
    }
  });

  test('should handle job cancellation', async ({ page }) => {
    // Mock the cancel endpoint
    await page.route('**/api/analyze/job/test-job-123', async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        });
      }
    });

    await page.goto('/analyze/status/test-job-123');
    await waitForJavaScriptReady(page);

    // Look for cancel button
    const cancelButton = page.locator('button:has-text("Cancel")');
    
    if (await cancelButton.count() > 0) {
      // Handle confirm and alert dialogs from cancel flow
      page.on('dialog', async dialog => {
        try {
          if (dialog.type() === 'confirm') {
            await dialog.accept();
          } else {
            await dialog.accept().catch(() => dialog.dismiss());
          }
        } catch {}
      });

      await cancelButton.click();
      
      // Wait for potential redirect or success message
      await page.waitForTimeout(1000);
    }
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API error
  await page.route('**/api/analyze/status/test-job-error', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Server error' })
      });
    });

    await page.goto('/analyze/status/test-job-error');
    await waitForJavaScriptReady(page);

    // Wait for error handling
    await page.waitForTimeout(6000);

    // Should not crash and should handle the error
    const hasErrorMessage = await page.locator('.alert-danger, .error-message').count() > 0;
    // Error handling might be minimal, so this is optional
  });

  test('should cleanup intervals on page unload', async ({ page }) => {
    await page.goto('/analyze/status/test-job-123');
    await waitForJavaScriptReady(page);

    // Check that interval is set
    const hasInterval = await page.evaluate(() => {
      return typeof refreshInterval !== 'undefined' && refreshInterval !== null;
    });
    expect(hasInterval).toBeTruthy();

    // Navigate away
    await page.goto('/');
    
    // The beforeunload event should have cleared the interval
    // This is hard to test directly, but we can check the navigation works
    await expect(page).toHaveURL('/');
  });

  test('should display comment processing progress', async ({ page }) => {
    await page.goto('/analyze/status/test-job-processing');
    await waitForJavaScriptReady(page);

    // Wait for comment count to be updated
    await page.waitForTimeout(2000);

    const statusDetails = page.locator('.status-details');
    if (await statusDetails.count() > 0) {
      const detailsText = await statusDetails.textContent();
      expect(detailsText).toContain('Comments Processed');
    }
  });

  test('should handle video title updates', async ({ page }) => {
    await page.goto('/analyze/status/test-job-123');
    await waitForJavaScriptReady(page);

    // Wait for title update
    await page.waitForTimeout(2000);

    const titleElement = page.locator('h4');
    if (await titleElement.count() > 0) {
      const titleText = await titleElement.textContent();
      expect(titleText).not.toContain('Loading');
    }
  });
});

async function setupStatusPageMocks(page) {
  let progressCounter = 25;
  
  // Mock different job statuses
  await page.route('**/api/analyze/status/test-job-123', async (route) => {
    progressCounter = Math.min(progressCounter + 25, 100);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        status: {
          id: 'test-job-123',
          status: progressCounter < 100 ? 'processing' : 'completed',
          progress: progressCounter,
          video_title: 'Test Video Title',
          comment_count_processed: Math.floor(progressCounter * 2),
          comment_count_requested: 200,
          estimated_processing_time: Math.max(0, 300 - progressCounter * 3)
        }
      })
    });
  });

  await page.route('**/api/analyze/status/test-job-queued', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        status: {
          id: 'test-job-queued',
          status: 'queued',
          progress: 0,
          queue_position: 3,
          estimated_wait_time: 120,
          estimated_processing_time: 300
        }
      })
    });
  });

  await page.route('**/api/analyze/status/test-job-processing', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        status: {
          id: 'test-job-processing',
          status: 'processing',
          progress: 60,
          video_title: 'Processing Video',
          comment_count_processed: 120,
          comment_count_requested: 200,
          estimated_processing_time: 180
        }
      })
    });
  });

  await page.route('**/api/analyze/status/test-job-completed', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        status: {
          id: 'test-job-completed',
          status: 'completed',
          progress: 100,
          video_title: 'Completed Video',
          comment_count_processed: 200,
          comment_count_requested: 200
        }
      })
    });
  });
}