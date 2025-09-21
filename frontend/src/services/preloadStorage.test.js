import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { PreloadStorageService } from './preloadStorage';

describe('PreloadStorageService', () => {
  let service;
  let mockLocalStorage;

  beforeEach(() => {
    // Mock localStorage
    mockLocalStorage = {
      store: {},
      getItem: vi.fn((key) => mockLocalStorage.store[key] || null),
      setItem: vi.fn((key, value) => {
        mockLocalStorage.store[key] = value;
      }),
      removeItem: vi.fn((key) => {
        delete mockLocalStorage.store[key];
      }),
      clear: vi.fn(() => {
        mockLocalStorage.store = {};
      }),
    };

    // Replace global localStorage
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
    });

    // Mock fetch for server sync
    global.fetch = vi.fn();

    // Create new service instance
    service = new PreloadStorageService();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('initialization', () => {
    it('should initialize with empty cache when localStorage is empty', () => {
      expect(service.cache.size).toBe(0);
      expect(service.metadata).toEqual({});
    });

    it('should initialize from localStorage when data exists', () => {
      const testData = {
        'video123': {
          preloaded: true,
          jobId: 'job456',
          timestamp: Date.now(),
          commentCount: 500,
        },
      };

      mockLocalStorage.store['preloaded_videos'] = JSON.stringify(testData);
      mockLocalStorage.store['preloaded_metadata'] = JSON.stringify({ video123: { title: 'Test Video' } });

      service = new PreloadStorageService();

      expect(service.cache.size).toBe(1);
      expect(service.cache.has('video123')).toBe(true);
      expect(service.metadata).toHaveProperty('video123');
    });

    it('should filter out expired entries on initialization', () => {
      const oldTimestamp = Date.now() - (73 * 60 * 60 * 1000); // 73 hours ago
      const testData = {
        'expired': {
          preloaded: true,
          timestamp: oldTimestamp,
        },
        'valid': {
          preloaded: true,
          timestamp: Date.now(),
        },
      };

      mockLocalStorage.store['preloaded_videos'] = JSON.stringify(testData);
      service = new PreloadStorageService();

      expect(service.cache.size).toBe(1);
      expect(service.cache.has('valid')).toBe(true);
      expect(service.cache.has('expired')).toBe(false);
    });
  });

  describe('setPreloaded', () => {
    it('should mark a video as preloaded', () => {
      const videoId = 'test123';
      const jobId = 'job456';
      const metadata = { title: 'Test Video', duration: '10:30' };

      const result = service.setPreloaded(videoId, jobId, metadata);

      expect(result).toHaveProperty('preloaded', true);
      expect(result).toHaveProperty('jobId', jobId);
      expect(result).toHaveProperty('timestamp');
      expect(result).toHaveProperty('commentCount', 500);

      expect(service.cache.has(videoId)).toBe(true);
      expect(service.metadata[videoId]).toEqual(metadata);
    });

    it('should persist to localStorage', () => {
      service.setPreloaded('video123', 'job456');

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'preloaded_videos',
        expect.any(String)
      );

      const stored = JSON.parse(mockLocalStorage.setItem.mock.calls[0][1]);
      expect(stored).toHaveProperty('video123');
    });
  });

  describe('isPreloaded', () => {
    it('should return true for preloaded videos', () => {
      service.setPreloaded('video123');
      expect(service.isPreloaded('video123')).toBe(true);
    });

    it('should return false for non-preloaded videos', () => {
      expect(service.isPreloaded('nonexistent')).toBe(false);
    });

    it('should return false for expired videos', () => {
      const videoId = 'expired';
      service.cache.set(videoId, {
        preloaded: true,
        timestamp: Date.now() - (73 * 60 * 60 * 1000), // Expired
      });

      expect(service.isPreloaded(videoId)).toBe(false);
    });
  });

  describe('removePreloaded', () => {
    it('should remove a preloaded video', () => {
      service.setPreloaded('video123', 'job456', { title: 'Test' });
      expect(service.cache.has('video123')).toBe(true);

      service.removePreloaded('video123');

      expect(service.cache.has('video123')).toBe(false);
      expect(service.metadata).not.toHaveProperty('video123');
    });
  });

  describe('getAllPreloadedIds', () => {
    it('should return all valid preloaded video IDs', () => {
      service.setPreloaded('video1');
      service.setPreloaded('video2');
      service.setPreloaded('video3');

      // Add an expired entry
      service.cache.set('expired', {
        preloaded: true,
        timestamp: Date.now() - (73 * 60 * 60 * 1000),
      });

      const ids = service.getAllPreloadedIds();

      expect(ids).toHaveLength(3);
      expect(ids).toContain('video1');
      expect(ids).toContain('video2');
      expect(ids).toContain('video3');
      expect(ids).not.toContain('expired');
    });
  });

  describe('getPreloadInfo', () => {
    it('should return full info for valid preloaded videos', () => {
      const metadata = { title: 'Test Video' };
      service.setPreloaded('video123', 'job456', metadata);

      const info = service.getPreloadInfo('video123');

      expect(info).toHaveProperty('preloaded', true);
      expect(info).toHaveProperty('jobId', 'job456');
      expect(info).toHaveProperty('metadata', metadata);
      expect(info).toHaveProperty('commentCount', 500);
    });

    it('should return null for non-preloaded videos', () => {
      expect(service.getPreloadInfo('nonexistent')).toBeNull();
    });

    it('should return null for expired videos', () => {
      service.cache.set('expired', {
        preloaded: true,
        timestamp: Date.now() - (73 * 60 * 60 * 1000),
      });

      expect(service.getPreloadInfo('expired')).toBeNull();
    });
  });

  describe('syncWithServer', () => {
    it('should sync preloaded videos from server', async () => {
      const serverData = {
        success: true,
        preloaded_videos: [
          {
            video_id: 'server1',
            metadata: { title: 'Server Video 1' },
          },
          {
            video_id: 'server2',
            metadata: { title: 'Server Video 2' },
          },
        ],
      };

      global.fetch.mockResolvedValueOnce({
        json: () => Promise.resolve(serverData),
      });

      await service.syncWithServer();

      expect(service.isPreloaded('server1')).toBe(true);
      expect(service.isPreloaded('server2')).toBe(true);
      expect(service.metadata['server1']).toEqual({ title: 'Server Video 1' });
    });

    it('should remove videos not on server', async () => {
      service.setPreloaded('local1');
      service.setPreloaded('server1');

      const serverData = {
        success: true,
        preloaded_videos: [
          {
            video_id: 'server1',
            metadata: {},
          },
        ],
      };

      global.fetch.mockResolvedValueOnce({
        json: () => Promise.resolve(serverData),
      });

      await service.syncWithServer();

      expect(service.isPreloaded('server1')).toBe(true);
      expect(service.isPreloaded('local1')).toBe(false);
    });

    it('should handle sync errors gracefully', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      await service.syncWithServer();

      expect(consoleSpy).toHaveBeenCalledWith(
        'Error syncing preload status:',
        expect.any(Error)
      );
    });
  });

  describe('cleanExpired', () => {
    it('should remove expired entries', () => {
      const now = Date.now();
      
      service.cache.set('valid', {
        preloaded: true,
        timestamp: now,
      });
      
      service.cache.set('expired', {
        preloaded: true,
        timestamp: now - (73 * 60 * 60 * 1000),
      });

      expect(service.cache.size).toBe(2);

      const cleaned = service.cleanExpired();

      expect(cleaned).toBe(true);
      expect(service.cache.size).toBe(1);
      expect(service.cache.has('valid')).toBe(true);
      expect(service.cache.has('expired')).toBe(false);
    });

    it('should return false if no entries were cleaned', () => {
      service.setPreloaded('video1');
      service.setPreloaded('video2');

      const cleaned = service.cleanExpired();

      expect(cleaned).toBe(false);
      expect(service.cache.size).toBe(2);
    });
  });

  describe('clear', () => {
    it('should clear all data', () => {
      service.setPreloaded('video1', 'job1', { title: 'Video 1' });
      service.setPreloaded('video2', 'job2', { title: 'Video 2' });

      expect(service.cache.size).toBe(2);
      expect(Object.keys(service.metadata)).toHaveLength(2);

      service.clear();

      expect(service.cache.size).toBe(0);
      expect(service.metadata).toEqual({});
    });
  });

  describe('getStats', () => {
    it('should return statistics about cached entries', () => {
      const now = Date.now();
      
      service.cache.set('valid1', { preloaded: true, timestamp: now });
      service.cache.set('valid2', { preloaded: true, timestamp: now });
      service.cache.set('expired', {
        preloaded: true,
        timestamp: now - (73 * 60 * 60 * 1000),
      });

      const stats = service.getStats();

      expect(stats).toEqual({
        total: 3,
        valid: 2,
        expired: 1,
      });
    });
  });

  describe('persistence', () => {
    it('should handle localStorage errors gracefully', () => {
      mockLocalStorage.setItem.mockImplementationOnce(() => {
        throw new Error('Storage full');
      });

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      service.setPreloaded('video123');

      expect(consoleSpy).toHaveBeenCalledWith(
        'Error persisting preload storage:',
        expect.any(Error)
      );
    });

    it('should handle corrupted localStorage data', () => {
      mockLocalStorage.store['preloaded_videos'] = 'invalid json';
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      service = new PreloadStorageService();

      expect(service.cache.size).toBe(0);
      expect(consoleSpy).toHaveBeenCalled();
    });
  });
});