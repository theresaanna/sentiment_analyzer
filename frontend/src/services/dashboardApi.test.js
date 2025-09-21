import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { preloadAPI, DashboardAPIError } from './dashboardApi';

// Mock fetch globally
global.fetch = vi.fn();

describe('preloadAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('queuePreload', () => {
    it('should queue a preload job with default 500 comments', async () => {
      const mockResponse = {
        success: true,
        job_id: 'job123',
        metadata: {
          title: 'Test Video',
          duration: 'PT10M30S',
        },
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await preloadAPI.queuePreload('video123');

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/preload/comments/video123',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ target_comments: 500 }),
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should queue a preload job with custom comment count', async () => {
      const mockResponse = {
        success: true,
        job_id: 'job456',
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await preloadAPI.queuePreload('video456', 300);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/preload/comments/video456',
        expect.objectContaining({
          body: JSON.stringify({ target_comments: 300 }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle API errors', async () => {
      const errorResponse = {
        success: false,
        error: 'Video not found',
      };

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve(errorResponse),
      });

      await expect(
        preloadAPI.queuePreload('invalid')
      ).rejects.toThrow(DashboardAPIError);

      // Set up mock again for the second test
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve(errorResponse),
      });

      try {
        await preloadAPI.queuePreload('invalid');
      } catch (error) {
        expect(error).toBeInstanceOf(DashboardAPIError);
        expect(error.status).toBe(404);
        expect(error.message).toContain('Video not found');
      }
    });

    it('should handle network errors', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network failed'));

      await expect(
        preloadAPI.queuePreload('video123')
      ).rejects.toThrow(DashboardAPIError);

      // Set up mock again for the second test
      global.fetch.mockRejectedValueOnce(new Error('Network failed'));

      try {
        await preloadAPI.queuePreload('video123');
      } catch (error) {
        expect(error).toBeInstanceOf(DashboardAPIError);
        expect(error.status).toBe(0);
        expect(error.message).toContain('Network error');
      }
    });
  });

  describe('getPreloadedVideos', () => {
    it('should fetch list of preloaded videos', async () => {
      const mockResponse = {
        success: true,
        preloaded_videos: [
          {
            video_id: 'video1',
            video_title: 'Video 1',
            preloaded_at: '2024-01-01T00:00:00Z',
            comment_count: 500,
            metadata: { duration: 'PT5M' },
          },
          {
            video_id: 'video2',
            video_title: 'Video 2',
            preloaded_at: '2024-01-02T00:00:00Z',
            comment_count: 500,
            metadata: { duration: 'PT10M' },
          },
        ],
        count: 2,
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await preloadAPI.getPreloadedVideos();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/preload/status',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
      expect(result.preloaded_videos).toHaveLength(2);
      expect(result.count).toBe(2);
    });

    it('should handle empty preloaded videos list', async () => {
      const mockResponse = {
        success: true,
        preloaded_videos: [],
        count: 0,
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await preloadAPI.getPreloadedVideos();

      expect(result.preloaded_videos).toHaveLength(0);
      expect(result.count).toBe(0);
    });

    it('should handle API errors', async () => {
      const errorResponse = {
        success: false,
        error: 'Authentication required',
      };

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve(errorResponse),
      });

      await expect(
        preloadAPI.getPreloadedVideos()
      ).rejects.toThrow(DashboardAPIError);

      // Set up mock again for the second test
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve(errorResponse),
      });

      try {
        await preloadAPI.getPreloadedVideos();
      } catch (error) {
        expect(error).toBeInstanceOf(DashboardAPIError);
        expect(error.status).toBe(401);
        expect(error.message).toContain('Authentication required');
      }
    });
  });

  describe('isVideoPreloaded', () => {
    it('should return true for preloaded videos', async () => {
      const mockResponse = {
        success: true,
        preloaded_videos: [
          { video_id: 'video1' },
          { video_id: 'video2' },
        ],
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await preloadAPI.isVideoPreloaded('video1');

      expect(result).toBe(true);
    });

    it('should return false for non-preloaded videos', async () => {
      const mockResponse = {
        success: true,
        preloaded_videos: [
          { video_id: 'video1' },
          { video_id: 'video2' },
        ],
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await preloadAPI.isVideoPreloaded('video3');

      expect(result).toBe(false);
    });

    it('should return false when API call fails', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await preloadAPI.isVideoPreloaded('video1');

      expect(result).toBe(false);
    });

    it('should return false when API returns error', async () => {
      const errorResponse = {
        success: false,
        error: 'Server error',
      };

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve(errorResponse),
      });

      const result = await preloadAPI.isVideoPreloaded('video1');

      expect(result).toBe(false);
    });

    it('should handle empty preloaded list', async () => {
      const mockResponse = {
        success: true,
        preloaded_videos: [],
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await preloadAPI.isVideoPreloaded('video1');

      expect(result).toBe(false);
    });
  });

  describe('integration scenarios', () => {
    it('should handle complete preload workflow', async () => {
      // 1. Queue preload
      const queueResponse = {
        success: true,
        job_id: 'job789',
        metadata: { title: 'Test Video' },
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(queueResponse),
      });

      const queueResult = await preloadAPI.queuePreload('video789');
      expect(queueResult.job_id).toBe('job789');

      // 2. Check preloaded videos (initially empty)
      const initialStatusResponse = {
        success: true,
        preloaded_videos: [],
        count: 0,
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(initialStatusResponse),
      });

      let isPreloaded = await preloadAPI.isVideoPreloaded('video789');
      expect(isPreloaded).toBe(false);

      // 3. Check again after completion
      const completedStatusResponse = {
        success: true,
        preloaded_videos: [
          {
            video_id: 'video789',
            video_title: 'Test Video',
            preloaded_at: '2024-01-01T12:00:00Z',
            comment_count: 500,
            metadata: { title: 'Test Video' },
          },
        ],
        count: 1,
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(completedStatusResponse),
      });

      isPreloaded = await preloadAPI.isVideoPreloaded('video789');
      expect(isPreloaded).toBe(true);
    });

    it('should handle concurrent preload requests', async () => {
      const videos = ['video1', 'video2', 'video3'];
      const responses = videos.map((id) => ({
        success: true,
        job_id: `job_${id}`,
        metadata: { title: `Video ${id}` },
      }));

      // Mock all responses
      responses.forEach((response) => {
        global.fetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(response),
        });
      });

      // Queue all preloads concurrently
      const promises = videos.map((id) => preloadAPI.queuePreload(id));
      const results = await Promise.all(promises);

      expect(results).toHaveLength(3);
      results.forEach((result, index) => {
        expect(result.job_id).toBe(`job_${videos[index]}`);
      });
    });

    it('should handle partial failures in batch operations', async () => {
      const videos = ['valid1', 'invalid', 'valid2'];
      
      // First video succeeds
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          job_id: 'job1',
        }),
      });

      // Second video fails
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({
          success: false,
          error: 'Video not found',
        }),
      });

      // Third video succeeds
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          job_id: 'job2',
        }),
      });

      const results = await Promise.allSettled(
        videos.map((id) => preloadAPI.queuePreload(id))
      );

      expect(results[0].status).toBe('fulfilled');
      expect(results[0].value.job_id).toBe('job1');

      expect(results[1].status).toBe('rejected');
      expect(results[1].reason).toBeInstanceOf(DashboardAPIError);

      expect(results[2].status).toBe('fulfilled');
      expect(results[2].value.job_id).toBe('job2');
    });
  });
});