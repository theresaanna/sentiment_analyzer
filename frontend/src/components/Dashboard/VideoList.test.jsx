import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { VideoList } from './VideoList';
import { ToastProvider } from '../Toast/ToastContext';
import { JobStatusProvider } from '../../contexts/JobStatusContext';
import * as dashboardApi from '../../services/dashboardApi';

// Mock the API
vi.mock('../../services/dashboardApi', () => ({
  preloadAPI: {
    queuePreload: vi.fn()
  },
  jobsAPI: {
    getStatus: vi.fn()
  }
}));

// Mock the toast hook
vi.mock('../Toast/ToastContext', async () => {
  const actual = await vi.importActual('../Toast/ToastContext');
  return {
    ...actual,
    useToast: () => ({
      showToast: vi.fn()
    })
  };
});

describe('VideoList Component - Enhanced Tests', () => {
  const mockVideos = [
    {
      id: 'video1',
      title: 'Test Video 1',
      statistics: {
        views: 10000,
        comments: 500
      }
    },
    {
      id: 'video2', 
      title: 'Test Video 2',
      statistics: {
        views: 5000,
        comments: 250
      }
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock for getStatus - no jobs initially
    dashboardApi.jobsAPI.getStatus.mockResolvedValue({
      success: true,
      jobs: []
    });
  });

  describe('Job Status Integration', () => {
    it('shows queued status when preload is initiated', async () => {
      dashboardApi.preloadAPI.queuePreload.mockResolvedValue({
        success: true,
        job_id: 'job1'
      });

      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      // Click first preload button
      const preloadButtons = screen.getAllByText('Preload');
      fireEvent.click(preloadButtons[0]);

      // Should show queuing state
      await waitFor(() => {
        expect(screen.getByText(/Queuing.../)).toBeInTheDocument();
      });

      // API should be called
      expect(dashboardApi.preloadAPI.queuePreload).toHaveBeenCalledWith('video1');
    });

    it('updates button state based on job status', async () => {
      // Mock initial job status as processing
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        success: true,
        jobs: [{
          job_id: 'job1',
          video_id: 'video1',
          status: 'processing',
          progress: 50,
          job_type: 'preload'
        }]
      });

      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      // Should show processing state with progress
      await waitFor(() => {
        expect(screen.getByText(/Processing/)).toBeInTheDocument();
        expect(screen.getByText(/50%/)).toBeInTheDocument();
      });
    });

    it('shows completed state for finished preloads', async () => {
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        success: true,
        jobs: [{
          job_id: 'job1',
          video_id: 'video1',
          status: 'completed',
          progress: 100,
          job_type: 'preload'
        }]
      });

      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      await waitFor(() => {
        // Find the preloaded button for video1
        const buttons = screen.getAllByRole('button');
        const preloadedButton = buttons.find(btn => 
          btn.textContent.includes('Preloaded') && 
          btn.closest('[class*="video-item"]')?.textContent.includes('Test Video 1')
        );
        expect(preloadedButton).toBeInTheDocument();
        expect(preloadedButton).toBeDisabled();
      });
    });

    it('shows failed state with retry option', async () => {
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        success: true,
        jobs: [{
          job_id: 'job1',
          video_id: 'video1',
          status: 'failed',
          progress: 0,
          job_type: 'preload'
        }]
      });

      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      await waitFor(() => {
        expect(screen.getByText(/Failed/)).toBeInTheDocument();
      });

      // Failed button should be clickable for retry
      const failedButton = screen.getByText(/Failed/);
      expect(failedButton.closest('button')).not.toBeDisabled();
    });

    it('shows cancelled state', async () => {
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        success: true,
        jobs: [{
          job_id: 'job1',
          video_id: 'video1', 
          status: 'cancelled',
          progress: 0,
          job_type: 'preload'
        }]
      });

      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      await waitFor(() => {
        expect(screen.getByText(/Cancelled/)).toBeInTheDocument();
      });
    });
  });

  describe('Preloaded Videos Set', () => {
    it('respects preloadedVideos prop', () => {
      const preloadedSet = new Set(['video1']);

      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList 
              videos={mockVideos} 
              preloadedVideos={preloadedSet}
              isLoading={false} 
            />
          </ToastProvider>
        </JobStatusProvider>
      );

      // First video should show as preloaded
      const buttons = screen.getAllByRole('button');
      const video1Button = buttons.find(btn => 
        btn.closest('[class*="video-item"]')?.textContent.includes('Test Video 1')
      );
      expect(video1Button?.textContent).toContain('Preloaded');
      expect(video1Button).toBeDisabled();

      // Second video should show normal preload button
      const video2Button = buttons.find(btn => 
        btn.closest('[class*="video-item"]')?.textContent.includes('Test Video 2')
      );
      expect(video2Button?.textContent).toContain('Preload');
      expect(video2Button).not.toBeDisabled();
    });
  });

  describe('Button State Transitions', () => {
    it('disables button during preload process', async () => {
      dashboardApi.preloadAPI.queuePreload.mockResolvedValue({
        success: true,
        job_id: 'job1'
      });

      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={[mockVideos[0]]} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      const preloadButton = screen.getByText('Preload');
      expect(preloadButton.closest('button')).not.toBeDisabled();

      // Click to start preload
      fireEvent.click(preloadButton);

      // Button should be disabled during process
      await waitFor(() => {
        const button = screen.getByRole('button');
        expect(button).toBeDisabled();
      });
    });

    it('applies correct CSS classes for different states', async () => {
      // Start with processing state
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        success: true,
        jobs: [{
          job_id: 'job1',
          video_id: 'video1',
          status: 'processing',
          progress: 50,
          job_type: 'preload'
        }]
      });

      const { rerender } = render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      await waitFor(() => {
        const button = screen.getAllByRole('button')[0];
        expect(button.className).toContain('vibe-button');
      });

      // Update to completed state
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        success: true,
        jobs: [{
          job_id: 'job1',
          video_id: 'video1',
          status: 'completed',
          progress: 100,
          job_type: 'preload'
        }]
      });

      // Trigger re-render to update state
      rerender(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      await waitFor(() => {
        const button = screen.getAllByRole('button')[0];
        expect(button.className).toContain('preloaded');
      });
    });
  });

  describe('Error Handling', () => {
    it('handles preload API errors gracefully', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      dashboardApi.preloadAPI.queuePreload.mockRejectedValue(
        new Error('API Error')
      );

      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={[mockVideos[0]]} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      const preloadButton = screen.getByText('Preload');
      fireEvent.click(preloadButton);

      await waitFor(() => {
        expect(dashboardApi.preloadAPI.queuePreload).toHaveBeenCalled();
      });

      // Button should return to normal state after error
      await waitFor(() => {
        expect(screen.getByText('Preload')).toBeInTheDocument();
      });

      consoleError.mockRestore();
    });
  });

  describe('Video Display', () => {
    it('displays video information correctly', () => {
      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      // Check video titles
      expect(screen.getByText('Test Video 1')).toBeInTheDocument();
      expect(screen.getByText('Test Video 2')).toBeInTheDocument();

      // Check statistics
      expect(screen.getByText('10,000 views')).toBeInTheDocument();
      expect(screen.getByText('500 comments')).toBeInTheDocument();
      expect(screen.getByText('5,000 views')).toBeInTheDocument();
      expect(screen.getByText('250 comments')).toBeInTheDocument();
    });

    it('creates analyze links for each video', () => {
      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      const links = screen.getAllByRole('link');
      expect(links[0]).toHaveAttribute('href', '/analyze/video1');
      expect(links[1]).toHaveAttribute('href', '/analyze/video2');
    });
  });

  describe('Loading and Empty States', () => {
    it('shows loading state when isLoading is true', () => {
      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={[]} isLoading={true} />
          </ToastProvider>
        </JobStatusProvider>
      );

      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('shows empty state when no videos', () => {
      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={[]} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      expect(screen.getByText('No videos found')).toBeInTheDocument();
    });
  });

  describe('Animation and Stagger', () => {
    it('applies staggered animation to video items', () => {
      render(
        <JobStatusProvider>
          <ToastProvider>
            <VideoList videos={mockVideos} isLoading={false} />
          </ToastProvider>
        </JobStatusProvider>
      );

      const videoItems = document.querySelectorAll('.video-item');
      expect(videoItems).toHaveLength(2);

      // Check animation delays are different
      const style1 = window.getComputedStyle(videoItems[0]);
      const style2 = window.getComputedStyle(videoItems[1]);
      
      // Animation should be applied
      expect(style1.animation).toContain('fadeIn');
      expect(style2.animation).toContain('fadeIn');
    });
  });
})
