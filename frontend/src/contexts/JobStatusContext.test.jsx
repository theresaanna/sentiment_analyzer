import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { JobStatusProvider, useJobStatus } from './JobStatusContext';
import * as dashboardApi from '../services/dashboardApi';

// Mock the API module
vi.mock('../services/dashboardApi', () => ({
  jobsAPI: {
    getStatus: vi.fn(() => Promise.resolve({ jobs: [] }))
  }
}));

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: vi.fn((key) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('JobStatusContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Context Provider', () => {
    it('provides context values', () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      expect(result.current).toHaveProperty('jobStatuses');
      expect(result.current).toHaveProperty('activeJobs');
      expect(result.current).toHaveProperty('isPolling');
      expect(result.current).toHaveProperty('trackJob');
      expect(result.current).toHaveProperty('updateJobStatus');
      expect(result.current).toHaveProperty('removeJob');
      expect(result.current).toHaveProperty('clearCompletedJobs');
      expect(result.current).toHaveProperty('getVideoJobStatus');
      expect(result.current).toHaveProperty('isVideoPreloaded');
    });

    it('throws error when used outside provider', () => {
      // Suppress error output for this test
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      expect(() => {
        renderHook(() => useJobStatus());
      }).toThrow('useJobStatus must be used within a JobStatusProvider');
      
      spy.mockRestore();
    });
  });

  describe('localStorage persistence', () => {
    it('initializes from localStorage if available', async () => {
      const mockStatuses = {
        'video1': {
          job_id: 'job1',
          status: 'completed',
          progress: 100,
          timestamp: Date.now()
        }
      };
      localStorageMock.setItem('jobStatuses', JSON.stringify(mockStatuses));

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load to complete
      await waitFor(() => {
        // After initial load, localStorage values should be preserved
        expect(result.current.jobStatuses).toEqual(mockStatuses);
      });
    });

    it('persists job statuses to localStorage on update', async () => {
      // Mock successful empty response for initial load
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({ jobs: [] });
      
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
      });

      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith(
          'jobStatuses',
          expect.stringContaining('video1')
        );
      });

      const savedCall = localStorageMock.setItem.mock.calls.find(
        call => call[0] === 'jobStatuses' && call[1].includes('video1')
      );
      const saved = JSON.parse(savedCall[1]);
      expect(saved).toHaveProperty('video1');
      expect(saved.video1.job_id).toBe('job1');
      expect(saved.video1.status).toBe('queued');
    });
  });

  describe('Job tracking', () => {
    beforeEach(async () => {
      // Setup default mock for initial load
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({ jobs: [] });
    });

    it('tracks new jobs', async () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
      });

      expect(result.current.jobStatuses.video1).toEqual({
        job_id: 'job1',
        status: 'queued',
        progress: 0,
        timestamp: expect.any(Number)
      });
      expect(result.current.activeJobs.has('job1')).toBe(true);
    });

    it('updates job status', async () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
      });

      act(() => {
        result.current.updateJobStatus('video1', {
          status: 'processing',
          progress: 50
        });
      });

      expect(result.current.jobStatuses.video1.status).toBe('processing');
      expect(result.current.jobStatuses.video1.progress).toBe(50);
    });

    it('removes jobs', async () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
        result.current.trackJob('video2', 'job2');
      });

      act(() => {
        result.current.removeJob('video1');
      });

      expect(result.current.jobStatuses.video1).toBeUndefined();
      expect(result.current.jobStatuses.video2).toBeDefined();
    });
  });

  describe('Clear completed jobs', () => {
    beforeEach(() => {
      // Setup default mock for initial load
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({ jobs: [] });
    });

    it('removes completed and failed jobs', async () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
        result.current.trackJob('video2', 'job2');
        result.current.trackJob('video3', 'job3');
      });

      act(() => {
        result.current.updateJobStatus('video1', { status: 'completed' });
        result.current.updateJobStatus('video2', { status: 'failed' });
        result.current.updateJobStatus('video3', { status: 'processing' });
      });

      act(() => {
        result.current.clearCompletedJobs();
      });

      expect(result.current.jobStatuses.video1).toBeUndefined();
      expect(result.current.jobStatuses.video2).toBeUndefined();
      expect(result.current.jobStatuses.video3).toBeDefined();
    });
  });

  describe('Polling mechanism', () => {
    beforeEach(() => {
      dashboardApi.jobsAPI.getStatus.mockClear();
    });

    it('polls for job updates when there are active jobs', async () => {
      const mockJobs = [
        {
          job_id: 'job1',
          video_id: 'video1',
          status: 'processing',
          progress: 75,
          job_type: 'preload',
          comment_count: 5000
        }
      ];

      // First call for initial load, then polling
      dashboardApi.jobsAPI.getStatus
        .mockResolvedValueOnce({ jobs: [] })
        .mockResolvedValue({ jobs: mockJobs });

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalledTimes(1);
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
      });

      // Fast-forward time to trigger polling
      await act(async () => {
        vi.advanceTimersByTime(3000);
      });

      await waitFor(() => {
        // Should have been called twice now (initial + poll)
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalledTimes(2);
      });

      expect(result.current.jobStatuses.video1.status).toBe('processing');
      expect(result.current.jobStatuses.video1.progress).toBe(75);
    });

    it('stops polling when job completes', async () => {
      const mockJobsRunning = [
        {
          job_id: 'job1',
          video_id: 'video1',
          status: 'processing',
          progress: 50
        }
      ];

      const mockJobsCompleted = [
        {
          job_id: 'job1',
          video_id: 'video1',
          status: 'completed',
          progress: 100
        }
      ];

      // Initial load, first poll (running), second poll (completed)
      dashboardApi.jobsAPI.getStatus
        .mockResolvedValueOnce({ jobs: [] })
        .mockResolvedValueOnce({ jobs: mockJobsRunning })
        .mockResolvedValueOnce({ jobs: mockJobsCompleted });

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalledTimes(1);
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
      });

      // First poll - job is running
      await act(async () => {
        vi.advanceTimersByTime(3000);
      });

      await waitFor(() => {
        expect(result.current.activeJobs.has('job1')).toBe(true);
      });

      // Second poll - job completes
      await act(async () => {
        vi.advanceTimersByTime(3000);
      });

      await waitFor(() => {
        expect(result.current.activeJobs.has('job1')).toBe(false);
      });

      expect(result.current.jobStatuses.video1.status).toBe('completed');
    });

    it('does not poll when there are no active jobs', async () => {
      dashboardApi.jobsAPI.getStatus.mockClear();
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({ jobs: [] });

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load to complete
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalledTimes(1);
      });

      // No active jobs after initial load
      expect(result.current.activeJobs.size).toBe(0);

      // Fast-forward time
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      // Should not have polled again (only initial load call)
      expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalledTimes(1);
    });
  });

  describe('Helper functions', () => {
    beforeEach(() => {
      dashboardApi.jobsAPI.getStatus.mockResolvedValue({ jobs: [] });
    });

    it('getVideoJobStatus returns correct status', async () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
      });

      const status = result.current.getVideoJobStatus('video1');
      expect(status).toEqual({
        job_id: 'job1',
        status: 'queued',
        progress: 0,
        timestamp: expect.any(Number)
      });

      const nonExistent = result.current.getVideoJobStatus('video999');
      expect(nonExistent).toBeNull();
    });

    it('isVideoPreloaded correctly identifies preloaded videos', async () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
        result.current.trackJob('video2', 'job2');
        result.current.trackJob('video3', 'job3');
      });

      act(() => {
        result.current.updateJobStatus('video1', {
          status: 'completed',
          job_type: 'preload'
        });
        result.current.updateJobStatus('video2', {
          status: 'completed',
          job_type: 'analysis'
        });
        result.current.updateJobStatus('video3', {
          status: 'processing',
          job_type: 'preload'
        });
      });

      expect(result.current.isVideoPreloaded('video1')).toBe(true);
      expect(result.current.isVideoPreloaded('video2')).toBe(false);
      expect(result.current.isVideoPreloaded('video3')).toBe(false); // Not completed yet
    });
  });

  describe('Initial load', () => {
    it('loads initial statuses from server on mount', async () => {
      const mockJobs = [
        {
          job_id: 'job1',
          video_id: 'video1',
          status: 'processing',
          progress: 30,
          job_type: 'preload',
          comment_count: 5000
        },
        {
          job_id: 'job2',
          video_id: 'video2',
          status: 'completed',
          progress: 100,
          job_type: 'analysis',
          comment_count: 1000
        }
      ];

      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        jobs: mockJobs
      });

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      expect(result.current.jobStatuses.video1).toBeDefined();
      expect(result.current.jobStatuses.video2).toBeDefined();
      expect(result.current.activeJobs.has('job1')).toBe(true);
      expect(result.current.activeJobs.has('job2')).toBe(false);
    });

    it('handles error when loading initial statuses', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      dashboardApi.jobsAPI.getStatus.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Error loading initial job statuses:',
          expect.any(Error)
        );
      }, { timeout: 2000 });

      expect(result.current.jobStatuses).toEqual({});
      expect(result.current.activeJobs.size).toBe(0);

      consoleSpy.mockRestore();
    });
  });

  describe('Error handling', () => {
    it('handles polling errors gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      // Initial load succeeds, then polling fails
      dashboardApi.jobsAPI.getStatus
        .mockResolvedValueOnce({ jobs: [] })
        .mockRejectedValue(new Error('API Error'));

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
      });

      await act(async () => {
        vi.advanceTimersByTime(3000);
      });

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Error polling job statuses:',
          expect.any(Error)
        );
      }, { timeout: 2000 });

      // Job should still be tracked despite error
      expect(result.current.jobStatuses.video1).toBeDefined();

      consoleSpy.mockRestore();
    });
  });
});