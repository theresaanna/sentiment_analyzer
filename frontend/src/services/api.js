// Production-grade API Service Layer
class ApiService {
  constructor() {
    this.baseUrl = process.env.REACT_APP_API_URL || '/api';
    this.timeout = 30000; // 30 seconds
    this.retryAttempts = 3;
    this.retryDelay = 1000; // 1 second
  }

  // Generic fetch wrapper with error handling and retry logic
  async fetchWithRetry(url, options = {}, retries = this.retryAttempts) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        // Handle specific HTTP errors
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in.');
        } else if (response.status === 403) {
          throw new Error('Access denied. Please upgrade your account.');
        } else if (response.status === 429) {
          throw new Error('Too many requests. Please wait and try again.');
        } else if (response.status === 507) {
          throw new Error('Service temporarily unavailable. Please try again later.');
        } else if (response.status >= 500) {
          throw new Error(`Server error: ${response.status}. Please try again.`);
        }
        
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Request failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      // Retry logic for network errors
      if (retries > 0 && this.shouldRetry(error)) {
        await this.delay(this.retryDelay);
        return this.fetchWithRetry(url, options, retries - 1);
      }

      // Handle abort errors
      if (error.name === 'AbortError') {
        throw new Error('Request timeout. Please check your connection and try again.');
      }

      throw error;
    }
  }

  // Determine if error is retryable
  shouldRetry(error) {
    return (
      error.name === 'TypeError' || // Network error
      error.message.includes('fetch') ||
      error.message.includes('network') ||
      error.message.includes('Server error')
    );
  }

  // Utility delay function
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Start sentiment analysis
  async startAnalysis(videoId, config = {}) {
    const { maxComments = 100, includeReplies = false, percentageSelected = 100 } = config;
    
    return this.fetchWithRetry(`${this.baseUrl}/analyze/sentiment/${videoId}`, {
      method: 'POST',
      body: JSON.stringify({
        max_comments: maxComments,
        include_replies: includeReplies,
        percentage_selected: percentageSelected,
      }),
    });
  }

  // Get analysis status
  async getAnalysisStatus(analysisId) {
    return this.fetchWithRetry(`${this.baseUrl}/analyze/status/${analysisId}`);
  }

  // Get analysis results
  async getAnalysisResults(analysisId) {
    return this.fetchWithRetry(`${this.baseUrl}/analyze/results/${analysisId}`);
  }

  // Submit sentiment feedback
  async submitFeedback(videoId, commentId, originalSentiment, correctedSentiment) {
    return this.fetchWithRetry(`${this.baseUrl}/feedback/sentiment`, {
      method: 'POST',
      body: JSON.stringify({
        video_id: videoId,
        comment_id: commentId,
        original_sentiment: originalSentiment,
        corrected_sentiment: correctedSentiment,
      }),
    });
  }

  // Retry summary generation
  async retrySummary(analysisId) {
    return this.fetchWithRetry(`${this.baseUrl}/analyze/retry-summary/${analysisId}`, {
      method: 'POST',
    });
  }

  // Get video info
  async getVideoInfo(videoId) {
    return this.fetchWithRetry(`${this.baseUrl}/video/${videoId}`);
  }

  // Queue analysis job (for authenticated users)
  async queueAnalysis(videoId, config = {}) {
    return this.fetchWithRetry(`${this.baseUrl}/analyze/queue`, {
      method: 'POST',
      body: JSON.stringify({
        video_id: videoId,
        ...config,
      }),
    });
  }

  // Get user's analysis history
  async getAnalysisHistory() {
    return this.fetchWithRetry(`${this.baseUrl}/user/analysis-history`);
  }

  // Export analysis results
  async exportResults(analysisId, format = 'json') {
    return this.fetchWithRetry(`${this.baseUrl}/analyze/export/${analysisId}?format=${format}`);
  }

  // Health check endpoint
  async healthCheck() {
    return this.fetchWithRetry(`${this.baseUrl}/health`, {
      method: 'GET',
    }, 1); // Only 1 retry for health checks
  }
}

// Create singleton instance
export const api = new ApiService();

// Export for testing purposes
export default ApiService;