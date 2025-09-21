/**
 * Preload Storage Service
 * Manages persistent storage of preloaded video states across sessions
 */

const STORAGE_KEY = 'preloaded_videos';
const METADATA_KEY = 'preloaded_metadata';
const EXPIRY_HOURS = 72; // 3 days

class PreloadStorageService {
  constructor() {
    this.cache = new Map();
    this.initializeFromStorage();
  }

  /**
   * Initialize cache from localStorage
   */
  initializeFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const metadata = localStorage.getItem(METADATA_KEY);
      
      if (stored) {
        const data = JSON.parse(stored);
        // Clean expired entries
        const now = Date.now();
        Object.entries(data).forEach(([videoId, info]) => {
          if (this.isValid(info)) {
            this.cache.set(videoId, info);
          }
        });
        this.persist(); // Clean up storage
      }

      if (metadata) {
        this.metadata = JSON.parse(metadata);
      } else {
        this.metadata = {};
      }
    } catch (error) {
      console.error('Error loading preload storage:', error);
      this.cache.clear();
      this.metadata = {};
    }
  }

  /**
   * Check if a preload entry is still valid
   */
  isValid(info) {
    if (!info || !info.timestamp) return false;
    const age = Date.now() - info.timestamp;
    const maxAge = EXPIRY_HOURS * 60 * 60 * 1000;
    return age < maxAge;
  }

  /**
   * Mark a video as preloaded
   */
  setPreloaded(videoId, jobId = null, metadata = null) {
    const info = {
      preloaded: true,
      jobId,
      metadata,
      timestamp: Date.now(),
      commentCount: 500
    };
    
    this.cache.set(videoId, info);
    
    if (metadata) {
      this.metadata[videoId] = metadata;
    }
    
    this.persist();
    return info;
  }

  /**
   * Remove preloaded status for a video
   */
  removePreloaded(videoId) {
    this.cache.delete(videoId);
    delete this.metadata[videoId];
    this.persist();
  }

  /**
   * Check if a video is preloaded
   */
  isPreloaded(videoId) {
    const info = this.cache.get(videoId);
    return !!(info && this.isValid(info));
  }

  /**
   * Get preload info for a video
   */
  getPreloadInfo(videoId) {
    const info = this.cache.get(videoId);
    if (info && this.isValid(info)) {
      return {
        ...info,
        metadata: this.metadata[videoId] || info.metadata
      };
    }
    return null;
  }

  /**
   * Get all preloaded video IDs
   */
  getAllPreloadedIds() {
    const ids = [];
    this.cache.forEach((info, videoId) => {
      if (this.isValid(info)) {
        ids.push(videoId);
      }
    });
    return ids;
  }

  /**
   * Get all preloaded videos with metadata
   */
  getAllPreloaded() {
    const videos = [];
    this.cache.forEach((info, videoId) => {
      if (this.isValid(info)) {
        videos.push({
          videoId,
          ...info,
          metadata: this.metadata[videoId] || info.metadata
        });
      }
    });
    return videos;
  }

  /**
   * Sync with server data
   */
  async syncWithServer() {
    try {
      const response = await fetch('/api/preload/status');
      const data = await response.json();
      
      if (data.success && data.preloaded_videos) {
        // Update cache with server data
        data.preloaded_videos.forEach(video => {
          const existing = this.cache.get(video.video_id);
          if (!existing || !this.isValid(existing)) {
            this.setPreloaded(
              video.video_id,
              null,
              video.metadata
            );
          }
        });
        
        // Remove videos not on server
        const serverIds = new Set(data.preloaded_videos.map(v => v.video_id));
        this.cache.forEach((_, videoId) => {
          if (!serverIds.has(videoId)) {
            this.removePreloaded(videoId);
          }
        });
      }
    } catch (error) {
      console.error('Error syncing preload status:', error);
    }
  }

  /**
   * Clear all preloaded data
   */
  clear() {
    this.cache.clear();
    this.metadata = {};
    this.persist();
  }

  /**
   * Clear expired entries
   */
  cleanExpired() {
    let cleaned = false;
    this.cache.forEach((info, videoId) => {
      if (!this.isValid(info)) {
        this.cache.delete(videoId);
        delete this.metadata[videoId];
        cleaned = true;
      }
    });
    
    if (cleaned) {
      this.persist();
    }
    
    return cleaned;
  }

  /**
   * Persist current state to localStorage
   */
  persist() {
    try {
      const data = {};
      this.cache.forEach((info, videoId) => {
        if (this.isValid(info)) {
          data[videoId] = info;
        }
      });
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      localStorage.setItem(METADATA_KEY, JSON.stringify(this.metadata));
    } catch (error) {
      console.error('Error persisting preload storage:', error);
    }
  }

  /**
   * Get statistics about preloaded videos
   */
  getStats() {
    let total = 0;
    let valid = 0;
    let expired = 0;
    
    this.cache.forEach(info => {
      total++;
      if (this.isValid(info)) {
        valid++;
      } else {
        expired++;
      }
    });
    
    return { total, valid, expired };
  }

  /**
   * Export data for debugging
   */
  export() {
    return {
      cache: Array.from(this.cache.entries()),
      metadata: this.metadata,
      stats: this.getStats()
    };
  }
}

// Create singleton instance
const preloadStorage = new PreloadStorageService();

// Auto-clean expired entries periodically (disabled during tests)
if (typeof window !== 'undefined' && !(typeof process !== 'undefined' && process.env.NODE_ENV === 'test')) {
  // Clean on page load
  preloadStorage.cleanExpired();
  
  // Clean every hour
  setInterval(() => {
    preloadStorage.cleanExpired();
  }, 60 * 60 * 1000);
  
  // Sync with server on load
  preloadStorage.syncWithServer();
}

export default preloadStorage;
export { PreloadStorageService };