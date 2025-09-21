"""
End-to-end tests for job management functionality.
Tests job cancellation, clearing old jobs, and managing multiple concurrent jobs.
"""

import pytest
import asyncio

# Skip these tests if playwright is not installed
try:
    from playwright.async_api import async_playwright, expect
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

pytestmark = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright not installed")


class TestJobManagementE2E:
    """E2E tests for job management features."""

    @pytest.mark.asyncio
    async def test_cancel_running_job(self, authenticated_page):
        """Test cancelling a running job."""
        page = authenticated_page
        
        # Mock job status to show a running job
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': [{
                    'job_id': 'job1',
                    'video_id': 'video1',
                    'status': 'running',
                    'progress': 30,
                    'job_type': 'preload',
                    'video_title': 'Test Video 1',
                    'comment_count': 5000
                }]
            }))
        
        await page.goto('/dashboard')
        
        # Wait for jobs to load
        await page.wait_for_selector('.job-item', timeout=5000)
        
        # Find cancel button
        cancel_button = page.locator('.job-cancel-btn').first
        await expect(cancel_button).to_be_visible()
        await expect(cancel_button).to_contain_text('Cancel')
        
        # Mock cancel API response
        await page.route('**/api/jobs/cancel/**', lambda route:
            route.fulfill(json={'success': True, 'message': 'Job cancellation requested'}))
        
        # Click cancel button
        await cancel_button.click()
        
        # Button should be disabled during cancellation
        await expect(cancel_button).to_be_disabled()
        
        # Should show success toast
        toast = page.locator('.toast-body')
        await expect(toast).to_contain_text('Job cancelled')
        
        # Job should be updated to cancelled state
        await page.wait_for_timeout(1000)
        
        # Mock updated status showing cancelled
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': [{
                    'job_id': 'job1',
                    'video_id': 'video1',
                    'status': 'cancelled',
                    'progress': 30
                }]
            }))
        
        # Verify job shows cancelled status
        job_status = page.locator('.job-status-badge').first
        await expect(job_status).to_contain_text('cancelled')

    @pytest.mark.asyncio
    async def test_cannot_cancel_completed_job(self, authenticated_page):
        """Test that completed jobs cannot be cancelled."""
        page = authenticated_page
        
        # Mock job status to show a completed job
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': [{
                    'job_id': 'job1',
                    'video_id': 'video1',
                    'status': 'completed',
                    'progress': 100,
                    'job_type': 'preload'
                }]
            }))
        
        await page.goto('/dashboard')
        await page.wait_for_selector('.job-item')
        
        # Cancel button should not be present for completed jobs
        cancel_buttons = page.locator('.job-cancel-btn')
        count = await cancel_buttons.count()
        assert count == 0
        
        # Should have a view button instead
        view_button = page.locator('a:has-text("View")')
        await expect(view_button).to_be_visible()

    @pytest.mark.asyncio
    async def test_clear_old_jobs(self, authenticated_page):
        """Test clearing completed and cancelled jobs."""
        page = authenticated_page
        
        # Mock multiple jobs with different statuses
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': [
                    {
                        'job_id': 'job1',
                        'video_id': 'video1',
                        'status': 'completed',
                        'progress': 100
                    },
                    {
                        'job_id': 'job2',
                        'video_id': 'video2',
                        'status': 'running',
                        'progress': 50
                    },
                    {
                        'job_id': 'job3',
                        'video_id': 'video3',
                        'status': 'failed',
                        'progress': 0
                    },
                    {
                        'job_id': 'job4',
                        'video_id': 'video4',
                        'status': 'cancelled',
                        'progress': 25
                    }
                ]
            }))
        
        await page.goto('/dashboard')
        await page.wait_for_selector('.job-item')
        
        # Should have 4 jobs initially
        job_items = page.locator('.job-item')
        initial_count = await job_items.count()
        assert initial_count == 4
        
        # Mock clear-old API response
        await page.route('**/api/jobs/clear-old', lambda route:
            route.fulfill(json={
                'success': True,
                'cleared': 3,
                'remaining': 1
            }))
        
        # Trigger clear old jobs (this would be in a button or automatic)
        # For testing, we'll simulate the API call
        await page.evaluate("""
            fetch('/api/jobs/clear-old', { method: 'POST' })
                .then(r => r.json())
                .then(data => console.log('Cleared:', data));
        """)
        
        await page.wait_for_timeout(1000)
        
        # Mock updated status showing only running job
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': [{
                    'job_id': 'job2',
                    'video_id': 'video2',
                    'status': 'running',
                    'progress': 50
                }]
            }))
        
        # Trigger a refresh of the jobs list
        await page.reload()
        await page.wait_for_selector('.job-item')
        
        # Should only have 1 job remaining (the running one)
        remaining_jobs = page.locator('.job-item')
        remaining_count = await remaining_jobs.count()
        assert remaining_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_job_limit(self, authenticated_page):
        """Test that concurrent job limit is enforced."""
        page = authenticated_page
        
        # Set up initial state with max concurrent jobs
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': [
                    {'job_id': 'job1', 'video_id': 'v1', 'status': 'running'},
                    {'job_id': 'job2', 'video_id': 'v2', 'status': 'running'},
                    {'job_id': 'job3', 'video_id': 'v3', 'status': 'running'}
                ]
            }))
        
        await page.goto('/dashboard')
        await page.fill('#channelInput', '@testchannel')
        await page.click('#loadChannelBtn')
        await page.wait_for_selector('.video-item')
        
        # Try to start another preload when at limit
        await page.route('**/api/preload/comments/**', lambda route:
            route.fulfill(
                status=429,
                json={'success': False, 'error': 'Too many active jobs'}
            ))
        
        # Find a preload button that's not already running
        preload_button = page.locator('.vibe-button:has-text("Preload")').first
        await preload_button.click()
        
        # Should show error message
        toast = page.locator('.toast-body')
        await expect(toast).to_contain_text('Too many active jobs')
        
        # Button should return to normal state
        await expect(preload_button).to_contain_text('Preload')
        await expect(preload_button).to_be_enabled()

    @pytest.mark.asyncio
    async def test_job_progress_updates(self, authenticated_page):
        """Test that job progress updates are displayed correctly."""
        page = authenticated_page
        
        # Initial job state
        progress_values = [0, 25, 50, 75, 100]
        current_progress = 0
        
        async def mock_progressive_status(route):
            nonlocal current_progress
            status = 'running' if current_progress < 100 else 'completed'
            await route.fulfill(json={
                'success': True,
                'jobs': [{
                    'job_id': 'job1',
                    'video_id': 'video1',
                    'status': status,
                    'progress': progress_values[current_progress],
                    'job_type': 'preload'
                }]
            })
            if current_progress < len(progress_values) - 1:
                current_progress += 1
        
        await page.route('**/api/jobs/status', mock_progressive_status)
        
        await page.goto('/dashboard')
        
        # Wait for initial job display
        await page.wait_for_selector('.job-item')
        
        # Check initial progress
        progress_bar = page.locator('.progress-bar').first
        await expect(progress_bar).to_have_attribute('aria-valuenow', '0')
        
        # Simulate progress updates through polling
        for expected_progress in [25, 50, 75, 100]:
            await page.wait_for_timeout(3500)  # Wait for next poll
            
            if expected_progress < 100:
                # Check progress bar updates
                await expect(progress_bar).to_have_attribute('aria-valuenow', str(expected_progress))
                await expect(progress_bar).to_contain_text(f'{expected_progress}%')
            else:
                # Job should be completed
                job_status = page.locator('.job-status-badge').first
                await expect(job_status).to_contain_text('completed')

    @pytest.mark.asyncio
    async def test_job_metadata_display(self, authenticated_page):
        """Test that job metadata (video info) is displayed correctly."""
        page = authenticated_page
        
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': [{
                    'job_id': 'job1',
                    'video_id': 'video1',
                    'status': 'processing',
                    'progress': 50,
                    'job_type': 'preload',
                    'video_title': 'Amazing Tutorial Video',
                    'comment_count': 5000,
                    'video_metadata': {
                        'title': 'Amazing Tutorial Video',
                        'views': 100000,
                        'comments': 5000,
                        'published': '2024-01-15T10:00:00Z'
                    }
                }]
            }))
        
        await page.goto('/dashboard')
        await page.wait_for_selector('.job-item')
        
        # Check job type is displayed
        job_item = page.locator('.job-item').first
        await expect(job_item).to_contain_text('COMMENT PRELOAD')
        
        # Check video title is displayed
        await expect(job_item).to_contain_text('Amazing Tutorial Video')
        
        # Check metadata is displayed
        await expect(job_item).to_contain_text('100,000 views')
        await expect(job_item).to_contain_text('5,000 comments')
        await expect(job_item).to_contain_text('2024-01-15')

    @pytest.mark.asyncio
    async def test_job_list_auto_refresh(self, authenticated_page):
        """Test that job list refreshes automatically via polling."""
        page = authenticated_page
        
        # Start with one job
        call_count = 0
        async def mock_changing_jobs(route):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call - one job
                await route.fulfill(json={
                    'success': True,
                    'jobs': [{
                        'job_id': 'job1',
                        'video_id': 'video1',
                        'status': 'running',
                        'progress': 30
                    }]
                })
            else:
                # Second call - two jobs
                await route.fulfill(json={
                    'success': True,
                    'jobs': [
                        {
                            'job_id': 'job1',
                            'video_id': 'video1',
                            'status': 'running',
                            'progress': 60
                        },
                        {
                            'job_id': 'job2',
                            'video_id': 'video2',
                            'status': 'queued',
                            'progress': 0
                        }
                    ]
                })
        
        await page.route('**/api/jobs/status', mock_changing_jobs)
        
        await page.goto('/dashboard')
        
        # Initially should have 1 job
        await page.wait_for_selector('.job-item')
        job_items = page.locator('.job-item')
        initial_count = await job_items.count()
        assert initial_count == 1
        
        # Wait for auto-refresh (polling interval)
        await page.wait_for_timeout(3000)
        
        # Should now have 2 jobs
        updated_count = await job_items.count()
        assert updated_count == 2
        
        # First job should show updated progress
        first_job_progress = page.locator('.progress-bar').first
        await expect(first_job_progress).to_have_attribute('aria-valuenow', '60')

    @pytest.mark.asyncio
    async def test_job_view_button_for_completed(self, authenticated_page):
        """Test that completed jobs have a View button to navigate to analysis."""
        page = authenticated_page
        
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': [{
                    'job_id': 'job1',
                    'video_id': 'completed_video',
                    'status': 'completed',
                    'progress': 100,
                    'job_type': 'preload',
                    'video_title': 'Completed Video'
                }]
            }))
        
        await page.goto('/dashboard')
        await page.wait_for_selector('.job-item')
        
        # Find the View button
        view_button = page.locator('a.btn-success:has-text("View")')
        await expect(view_button).to_be_visible()
        
        # Check it has correct href
        href = await view_button.get_attribute('href')
        assert href == '/analyze/completed_video'
        
        # Click should navigate to analyze page
        await view_button.click()
        await page.wait_for_url('**/analyze/completed_video')
        
        # Verify we're on the analyze page
        current_url = page.url
        assert '/analyze/completed_video' in current_url

    @pytest.mark.asyncio
    async def test_empty_jobs_state(self, authenticated_page):
        """Test display when no jobs are active."""
        page = authenticated_page
        
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={
                'success': True,
                'jobs': []
            }))
        
        await page.goto('/dashboard')
        
        # Wait for jobs container to load
        jobs_container = page.locator('#jobsContainer')
        await expect(jobs_container).to_be_visible()
        
        # Should show no active jobs message
        await expect(jobs_container).to_contain_text('No active jobs')
        
        # Should have the empty state icon
        empty_icon = jobs_container.locator('.fa-check-circle')
        await expect(empty_icon).to_be_visible()


# Re-use the authenticated_page fixture from test_preload_workflow.py
@pytest.fixture
async def authenticated_page():
    """Create an authenticated browser page for testing."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Mock authentication
        await page.goto('http://localhost:5000/login')
        await page.evaluate("""() => {
            localStorage.setItem('auth_token', 'test_pro_token');
            localStorage.setItem('user_type', 'pro');
            document.cookie = 'session=test_session; path=/';
        }""")
        
        # Default API mocks
        await page.route('**/api/youtube/channel-videos**', lambda route:
            route.fulfill(json={
                'success': True,
                'channel': {'id': 'ch1', 'title': 'Test Channel'},
                'videos': [
                    {'id': 'v1', 'title': 'Video 1', 'statistics': {'views': 1000, 'comments': 50}},
                    {'id': 'v2', 'title': 'Video 2', 'statistics': {'views': 2000, 'comments': 100}},
                    {'id': 'v3', 'title': 'Video 3', 'statistics': {'views': 3000, 'comments': 150}},
                    {'id': 'v4', 'title': 'Video 4', 'statistics': {'views': 4000, 'comments': 200}}
                ],
                'count': 4
            }))
        
        # Default preload success
        await page.route('**/api/preload/comments/**', lambda route:
            route.fulfill(json={'success': True, 'job_id': 'new_job'}))
        
        # Default empty jobs status
        await page.route('**/api/jobs/status', lambda route:
            route.fulfill(json={'success': True, 'jobs': []}))
        
        yield page
        
        await context.close()
        await browser.close()