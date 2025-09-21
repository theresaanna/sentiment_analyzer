import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { JobQueue } from './JobQueue';
import * as dashboardApi from '../../services/dashboardApi';
import { ToastContext } from '../Toast/ToastContext';
import { JobStatusContext } from '../../contexts/JobStatusContext';

// Mock the API module
vi.mock('../../services/dashboardApi', () => ({
  jobsAPI: {
    getStatus: vi.fn(),
    cancelJob: vi.fn()
  },
  preloadAPI: {
    queuePreload: vi.fn()
  }
}));

describe('JobQueue Component', () => {
  const mockJobs = [
    {
      job_id: 'job1',
      status: 'processing',
      progress: 45,
      video_id: 'video1',
      video_title: 'Active Video',
      job_type: 'preload',
      created_at: '2024-01-01T10:00:00Z',
      video_metadata: {
        title: 'Active Video',
        views: 1000,
        channel_title: 'Channel 1'
      }
    },
    {
      job_id: 'job2',
      status: 'completed',
      progress: 100,
      video_id: 'video2',
      video_title: 'Completed Video',
      job_type: 'analysis',
      created_at: '2024-01-01T09:00:00Z',
      video_metadata: {
        title: 'Completed Video',
        views: 2000,
        channel_title: 'Channel 2'
      }
    },
    {
      job_id: 'job3',
      status: 'failed',
      progress: 0,
      video_id: 'video3',
      video_title: 'Failed Video',
      job_type: 'preload',
      created_at: '2024-01-01T08:00:00Z',
      error_message: 'Network error',
      video_metadata: {
        title: 'Failed Video',
        views: 500,
        channel_title: 'Channel 3'
      }
    },
    {
      job_id: 'job4',
      status: 'queued',
      progress: 0,
      video_id: 'video4',
      video_title: 'Queued Video',
      job_type: 'analysis',
      created_at: '2024-01-01T11:00:00Z',
      video_metadata: {
        title: 'Queued Video',
        views: 1500,
        channel_title: 'Channel 4'
      }
    }
  ];

  const mockContextValue = {
    showToast: vi.fn(),
    pollJobStatuses: vi.fn()
  };

  const TestWrapper = ({ children }) => (
    <ToastContext.Provider value={mockContextValue}>
      <JobStatusContext.Provider value={mockContextValue}>
        {children}
      </JobStatusContext.Provider>
    </ToastContext.Provider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
    dashboardApi.jobsAPI.getStatus.mockResolvedValue({
      success: true,
      jobs: mockJobs
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe('Rendering', () => {
    it('should render loading state initially', () => {
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      expect(screen.getByText('Loading job queue...')).toBeInTheDocument();
    });

    it('should render jobs after loading', async () => {
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        expect(screen.getByText('Active Video')).toBeInTheDocument();
        expect(screen.getByText('Completed Video')).toBeInTheDocument();
        expect(screen.getByText('Failed Video')).toBeInTheDocument();
        expect(screen.getByText('Queued Video')).toBeInTheDocument();
      });
    });

    it('should display error state when API fails', async () => {
      dashboardApi.jobsAPI.getStatus.mockRejectedValue(new Error('API Error'));
      
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        expect(screen.getByText(/API Error/)).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    it('should display empty state when no jobs', async () => {
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        success: true,
        jobs: []
      });
      
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        expect(screen.getByText('No jobs found')).toBeInTheDocument();
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should display all tabs with correct counts', async () => {
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        expect(screen.getByText('All')).toBeInTheDocument();
        expect(screen.getByText('4')).toBeInTheDocument(); // Total count
        
        expect(screen.getByText('Active')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument(); // Active count (processing + queued)
        
        expect(screen.getByText('Completed')).toBeInTheDocument();
        expect(screen.getByText('1')).toBeInTheDocument(); // Completed count
        
        expect(screen.getByText('Failed')).toBeInTheDocument();
      });
    });

    it('should filter jobs when active tab is clicked', async () => {
      render(
        <TestWrapper>
          <JobQueue initialView="all" />
        </TestWrapper>
      );
      
      await waitFor(() => {
        expect(screen.getAllByTestId('job-card')).toHaveLength(4);
      });
      
      fireEvent.click(screen.getByText('Active'));
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards).toHaveLength(2);
        expect(screen.getByText('Active Video')).toBeInTheDocument();
        expect(screen.getByText('Queued Video')).toBeInTheDocument();
      });
    });

    it('should filter completed jobs', async () => {
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        fireEvent.click(screen.getByText('Completed'));
      });
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards).toHaveLength(1);
        expect(screen.getByText('Completed Video')).toBeInTheDocument();
      });
    });

    it('should filter failed jobs', async () => {
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        fireEvent.click(screen.getByText('Failed'));
      });
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards).toHaveLength(1);
        expect(screen.getByText('Failed Video')).toBeInTheDocument();
      });
    });

    it('should show history view with completed, failed, and cancelled', async () => {
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        fireEvent.click(screen.getByText('History'));
      });
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards).toHaveLength(2); // completed + failed
      });
    });
  });

  describe('Search Functionality', () => {
    it('should filter jobs by search term', async () => {
      render(
        <TestWrapper>
          <JobQueue showSearch={true} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        expect(screen.getAllByTestId('job-card')).toHaveLength(4);
      });
      
      const searchInput = screen.getByPlaceholderText(/Search by title/);
      fireEvent.change(searchInput, { target: { value: 'Active' } });
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards).toHaveLength(1);
        expect(screen.getByText('Active Video')).toBeInTheDocument();
      });
    });

    it('should search by channel name', async () => {
      render(
        <TestWrapper>
          <JobQueue showSearch={true} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/Search by title/);
        fireEvent.change(searchInput, { target: { value: 'Channel 2' } });
      });
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards).toHaveLength(1);
        expect(screen.getByText('Completed Video')).toBeInTheDocument();
      });
    });

    it('should show empty state when search has no results', async () => {
      render(
        <TestWrapper>
          <JobQueue showSearch={true} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/Search by title/);
        fireEvent.change(searchInput, { target: { value: 'nonexistent' } });
      });
      
      await waitFor(() => {
        expect(screen.getByText('No jobs found')).toBeInTheDocument();
        expect(screen.getByText('Try adjusting your search criteria')).toBeInTheDocument();
      });
    });
  });

  describe('Sorting', () => {
    it('should sort by newest first by default', async () => {
      render(
        <TestWrapper>
          <JobQueue showFilters={true} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards[0]).toHaveTextContent('Queued Video');
        expect(cards[1]).toHaveTextContent('Active Video');
      });
    });

    it('should sort by oldest first', async () => {
      render(
        <TestWrapper>
          <JobQueue showFilters={true} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        const sortSelect = screen.getByDisplayValue('Newest First');
        fireEvent.change(sortSelect, { target: { value: 'oldest' } });
      });
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards[0]).toHaveTextContent('Failed Video');
      });
    });

    it('should sort by title', async () => {
      render(
        <TestWrapper>
          <JobQueue showFilters={true} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        const sortSelect = screen.getByDisplayValue('Newest First');
        fireEvent.change(sortSelect, { target: { value: 'title' } });
      });
      
      await waitFor(() => {
        const cards = screen.getAllByTestId('job-card');
        expect(cards[0]).toHaveTextContent('Active Video');
      });
    });
  });

  describe('Job Actions', () => {
    it('should cancel a job when cancel is clicked', async () => {
      dashboardApi.jobsAPI.cancelJob.mockResolvedValue({ success: true });
      
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        fireEvent.click(screen.getByText('Active'));
      });
      
      // Expand the first active job
      const firstJob = screen.getByText('Active Video').closest('[data-testid="job-card"]');
      fireEvent.click(firstJob.querySelector('.job-card-header'));
      
      await waitFor(() => {
        const cancelButton = screen.getByText('Cancel');
        fireEvent.click(cancelButton);
      });
      
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.cancelJob).toHaveBeenCalledWith('job1');
        expect(mockContextValue.showToast).toHaveBeenCalledWith('Job cancelled successfully', 'success');
      });
    });

    it('should retry a failed job', async () => {
      dashboardApi.preloadAPI.queuePreload.mockResolvedValue({ success: true });
      
      render(
        <TestWrapper>
          <JobQueue />
        </TestWrapper>
      );
      
      await waitFor(() => {
        fireEvent.click(screen.getByText('Failed'));
      });
      
      // Expand the failed job
      const failedJob = screen.getByText('Failed Video').closest('[data-testid="job-card"]');
      fireEvent.click(failedJob.querySelector('.job-card-header'));
      
      await waitFor(() => {
        const retryButton = screen.getByText('Retry');
        fireEvent.click(retryButton);
      });
      
      await waitFor(() => {
        expect(mockContextValue.showToast).toHaveBeenCalledWith('Preload job requeued', 'success');
      });
    });
  });

  describe('Auto Refresh', () => {
    it('should auto-refresh when enabled', async () => {
      vi.useFakeTimers();
      
      render(
        <TestWrapper>
          <JobQueue autoRefresh={true} refreshInterval={1000} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalledTimes(1);
      });
      
      vi.advanceTimersByTime(1000);
      
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalledTimes(2);
      });
      
      vi.useRealTimers();
    });

    it('should display auto-refresh indicator', async () => {
      render(
        <TestWrapper>
          <JobQueue autoRefresh={true} refreshInterval={5000} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        expect(screen.getByText('Auto-refreshing every 5s')).toBeInTheDocument();
      });
    });
  });

  describe('Batch Operations', () => {
    it('should select all visible jobs', async () => {
      render(
        <TestWrapper>
          <JobQueue showFilters={true} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        const selectAllButton = screen.getByText('Select All');
        fireEvent.click(selectAllButton);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Cancel 4')).toBeInTheDocument();
      });
    });

    it('should batch cancel selected jobs', async () => {
      window.confirm = vi.fn(() => true);
      dashboardApi.jobsAPI.cancelJob.mockResolvedValue({ success: true });
      
      render(
        <TestWrapper>
          <JobQueue showFilters={true} />
        </TestWrapper>
      );
      
      await waitFor(() => {
        const selectAllButton = screen.getByText('Select All');
        fireEvent.click(selectAllButton);
      });
      
      await waitFor(() => {
        const batchCancelButton = screen.getByText('Cancel 4');
        fireEvent.click(batchCancelButton);
      });
      
      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalledWith('Cancel 4 job(s)?');
        expect(dashboardApi.jobsAPI.cancelJob).toHaveBeenCalledTimes(4);
      });
    });
  });
});