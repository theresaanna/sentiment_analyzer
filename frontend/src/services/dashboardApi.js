/**
 * Dashboard API Service
 * Handles all API calls for the dashboard functionality
 */

export class DashboardAPIError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = 'DashboardAPIError';
    this.status = status;
    this.details = details;
  }
}

/**
 * Fetch wrapper with error handling
 * @param {string} url - The URL to fetch
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<any>} - The response data
 */
async function fetchJSON(url, options = {}) {
  let response;
  
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  } catch (fetchError) {
    // Network error, fetch failed
    throw new DashboardAPIError(
      `Network error: ${fetchError.message}`,
      0,
      fetchError
    );
  }

  // Now we have a response, try to parse it
  let data;
  try {
    data = await response.json();
  } catch (jsonError) {
    // If JSON parsing fails, create error with response status
    throw new DashboardAPIError(
      `Invalid JSON response from server`,
      response.status,
      null
    );
  }

  // Check if request was successful
  if (!response.ok || !data.success) {
    throw new DashboardAPIError(
      data.error || `Request failed with status ${response.status}`,
      response.status,
      data.details || null
    );
  }

  return data;
}

/**
 * Channel API operations
 */
export const channelAPI = {
  /**
   * Load videos from a YouTube channel
   * @param {string} channel - Channel URL or handle
   * @param {number} max - Maximum videos to fetch
   * @returns {Promise<{channel: Object, videos: Array, count: number}>}
   */
  async loadVideos(channel, max = 100) {
    if (!channel) {
      throw new DashboardAPIError('Channel URL or handle is required', 400);
    }
    
    return fetchJSON(
      `/api/youtube/channel-videos?channel=${encodeURIComponent(channel)}&max=${max}`
    );
  },

  /**
   * Delete a channel and all associated data
   * @param {string} channelId - The channel ID to delete
   * @returns {Promise<{deleted_videos: number, deleted_jobs: number}>}
   */
  async deleteChannel(channelId) {
    return fetchJSON(`/api/channel/${channelId}/delete`, {
      method: 'DELETE',
    });
  },
};

/**
 * Jobs API operations
 */
export const jobsAPI = {
  /**
   * Get status of all background jobs
   * @returns {Promise<{jobs: Array}>}
   */
  async getStatus() {
    return fetchJSON('/api/jobs/status');
  },

  /**
   * Cancel a running job
   * @param {string} jobId - The job ID to cancel
   * @returns {Promise<{success: boolean}>}
   */
  async cancelJob(jobId) {
    return fetchJSON(`/api/jobs/cancel/${jobId}`, {
      method: 'POST',
    });
  },

  /**
   * Clear old completed/cancelled jobs
   * @returns {Promise<{cleared: number}>}
   */
  async clearOldJobs() {
    try {
      return await fetchJSON('/api/jobs/clear-old', {
        method: 'POST',
      });
    } catch (error) {
      // Silently ignore if endpoint doesn't exist
      console.log('Could not clear old jobs:', error.message);
      return { cleared: 0 };
    }
  },
};

/**
 * Preload API operations
 */
export const preloadAPI = {
  /**
   * Queue a video for comment preloading with metadata
   * @param {string} videoId - The video ID to preload
   * @param {number|null} targetComments - Target number of comments (default 500)
   * @returns {Promise<Object>}
   */
  async queuePreload(videoId, targetComments = 500) {
    return fetchJSON(`/api/preload/comments/${videoId}`, {
      method: 'POST',
      body: JSON.stringify({ target_comments: targetComments }),
    });
  },

  /**
   * Get list of preloaded videos for current user
   * @returns {Promise<{preloaded_videos: Array, count: number}>}
   */
  async getPreloadedVideos() {
    return fetchJSON('/api/preload/status');
  },

  /**
   * Check if a specific video is preloaded
   * @param {string} videoId - The video ID to check
   * @returns {Promise<boolean>}
   */
  async isVideoPreloaded(videoId) {
    try {
      const result = await this.getPreloadedVideos();
      return result.preloaded_videos.some(v => v.video_id === videoId);
    } catch (error) {
      return false;
    }
  },
};

/**
 * Analysis API operations
 */
export const analysisAPI = {
  /**
   * Queue a video for analysis
   * @param {string} videoId - The video ID to analyze
   * @param {number} commentCount - Number of comments to analyze
   * @param {boolean} includeReplies - Whether to include replies
   * @returns {Promise<{success: boolean, job_id: string}>}
   */
  async queueAnalysis(videoId, commentCount, includeReplies = false) {
    return fetchJSON('/api/analyze/queue', {
      method: 'POST',
      body: JSON.stringify({
        video_id: videoId,
        comment_count: commentCount,
        include_replies: includeReplies,
      }),
    });
  },
};

// Export all APIs as a single object for convenience
export const dashboardAPI = {
  channel: channelAPI,
  jobs: jobsAPI,
  preload: preloadAPI,
  analysis: analysisAPI,
  fetchJSON,
};

// Also export individual APIs for direct imports
export { channelAPI, jobsAPI, preloadAPI, analysisAPI };

export default dashboardAPI;
