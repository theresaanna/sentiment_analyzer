import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { JobStatusProvider, useJobStatus } from './JobStatusContext';
import * as dashboardApi from '../services/dashboardApi';

// Mock the API module
vi.mock('../services/dashboardApi', () => ({
  jobsAPI: {
    getStatus: vi.fn()
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
    it('initializes from localStorage if available', () => {
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

      expect(result.current.jobStatuses).toEqual(mockStatuses);
    });

    it('persists job statuses to localStorage on update', async () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
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

      const saved = JSON.parse(localStorageMock.setItem.mock.calls[0][1]);
      expect(saved).toHaveProperty('video1');
      expect(saved.video1.job_id).toBe('job1');
      expect(saved.video1.status).toBe('queued');
    });
  });

  describe('Job tracking', () => {
    it('tracks new jobs', () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
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

    it('updates job status', () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
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

    it('removes jobs', () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
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
    it('removes completed and failed jobs', () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
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

      dashboardApi.jobsAPI.getStatus.mockResolvedValue({
        success: true,
        jobs: mockJobs
      });

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
      });

      // Fast-forward time to trigger polling
      await act(async () => {
        vi.advanceTimersByTime(3000);
      });

      await waitFor(() => {
        expect(dashboardApi.jobsAPI.getStatus).toHaveBeenCalled();
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

      dashboardApi.jobsAPI.getStatus
        .mockResolvedValueOnce({ success: true, jobs: mockJobsRunning })
        .mockResolvedValueOnce({ success: true, jobs: mockJobsCompleted });

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
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

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      // No active jobs initially
      expect(result.current.activeJobs.size).toBe(0);

      // Fast-forward time
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      // Should not have called getStatus
      expect(dashboardApi.jobsAPI.getStatus).not.toHaveBeenCalled();
    });
  });

  describe('Helper functions', () => {
    it('getVideoJobStatus returns correct status', () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
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

    it('isVideoPreloaded correctly identifies preloaded videos', () => {
      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
      });

      act(() => {
        result.current.trackJob('video1', 'job1');
        result.current.trackJob('video2', 'job2');
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
      });

      expect(result.current.isVideoPreloaded('video1')).toBe(true);
      expect(result.current.isVideoPreloaded('video2')).toBe(false);
      expect(result.current.isVideoPreloaded('video3')).toBe(false);
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
        success: true,
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
      });

      expect(result.current.jobStatuses).toEqual({});
      expect(result.current.activeJobs.size).toBe(0);

      consoleSpy.mockRestore();
    });
  });

  describe('Error handling', () => {
    it('handles polling errors gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      dashboardApi.jobsAPI.getStatus.mockRejectedValue(new Error('API Error'));

      const { result } = renderHook(() => useJobStatus(), {
        wrapper: JobStatusProvider,
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
      });

      // Job should still be tracked despite error
      expect(result.current.jobStatuses.video1).toBeDefined();

      consoleSpy.mockRestore();
    });
  });
});