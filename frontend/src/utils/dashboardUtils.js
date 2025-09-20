/**
 * Dashboard Utility Functions
 * Shared helper functions for the dashboard
 */

/**
 * HTML escape function for security
 * @param {string} str - String to escape
 * @returns {string} - Escaped string
 */
export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Format number with commas
 * @param {number} num - Number to format
 * @returns {string} - Formatted number
 */
export function formatNumber(num) {
  return (num || 0).toLocaleString();
}

/**
 * Storage utilities with error handling
 */
export const storage = {
  /**
   * Get item from localStorage with JSON parsing
   * @param {string} key - Storage key
   * @param {any} defaultValue - Default value if not found or error
   * @returns {any} - Parsed value or default
   */
  get(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error(`Error reading from localStorage[${key}]:`, error);
      return defaultValue;
    }
  },

  /**
   * Set item in localStorage with JSON stringification
   * @param {string} key - Storage key
   * @param {any} value - Value to store
   * @returns {boolean} - Success status
   */
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error(`Error writing to localStorage[${key}]:`, error);
      return false;
    }
  },

  /**
   * Remove item from localStorage
   * @param {string} key - Storage key
   */
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`Error removing from localStorage[${key}]:`, error);
    }
  },
};

/**
 * Storage keys used by the dashboard
 */
export const STORAGE_KEYS = {
  USER_CHANNELS: 'vibe:userChannels',
  LAST_CHANNEL: 'vibe:lastChannel',
  SENTIMENT_CORRECTIONS: (videoId) => `sentiment_corrections_${videoId}`,
};

/**
 * Job status helpers
 */
export const JobStatus = {
  COMPLETED: 'completed',
  FAILED: 'failed',
  RUNNING: 'running',
  PENDING: 'pending',
  QUEUED: 'queued',
  CANCELLED: 'cancelled',
  FETCHING: 'fetching',
  SYNCING: 'syncing',
};

/**
 * Get status icon for job status
 * @param {string} status - Job status
 * @returns {string} - Status icon emoji
 */
export function getStatusIcon(status) {
  const icons = {
    [JobStatus.COMPLETED]: '✅',
    [JobStatus.FAILED]: '❌',
    [JobStatus.RUNNING]: '🔄',
    [JobStatus.PENDING]: '⏳',
    [JobStatus.QUEUED]: '⏳',
    [JobStatus.CANCELLED]: '🚫',
    [JobStatus.FETCHING]: '⬇️',
    [JobStatus.SYNCING]: '🔄',
  };
  return icons[status] || '⏳';
}

/**
 * Get status color for job status (Bootstrap color names)
 * @param {string} status - Job status
 * @returns {string} - Bootstrap color name
 */
export function getStatusColor(status) {
  const colors = {
    [JobStatus.COMPLETED]: 'success',
    [JobStatus.FAILED]: 'danger',
    [JobStatus.RUNNING]: 'primary',
    [JobStatus.PENDING]: 'secondary',
    [JobStatus.QUEUED]: 'secondary',
    [JobStatus.CANCELLED]: 'warning',
    [JobStatus.FETCHING]: 'info',
    [JobStatus.SYNCING]: 'info',
  };
  return colors[status] || 'secondary';
}

/**
 * Check if a job is cancellable
 * @param {string} status - Job status
 * @returns {boolean} - Whether the job can be cancelled
 */
export function isJobCancellable(status) {
  return [JobStatus.RUNNING, JobStatus.PENDING, JobStatus.QUEUED].includes(status);
}

/**
 * Check if a job is active (not completed/failed/cancelled)
 * @param {string} status - Job status
 * @returns {boolean} - Whether the job is active
 */
export function isJobActive(status) {
  return [
    JobStatus.QUEUED,
    JobStatus.PENDING,
    JobStatus.RUNNING,
    JobStatus.FETCHING,
    JobStatus.SYNCING,
  ].includes(status);
}

/**
 * Debounce function for performance optimization
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function for performance optimization
 * @param {Function} func - Function to throttle
 * @param {number} limit - Limit in milliseconds
 * @returns {Function} - Throttled function
 */
export function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Constants for dashboard configuration
 */
export const DASHBOARD_CONFIG = {
  MAX_CHANNELS: 5,
  VIDEO_FETCH_INTERVAL: 60000, // 60 seconds
  JOB_POLL_INTERVAL: 2000, // 2 seconds
  MAX_VIDEOS_DISPLAY: 100,
  PRELOAD_BATCH_SIZE: 10,
  TOAST_DURATION: 3000,
};

/**
 * Toast message variants
 */
export const TOAST_VARIANTS = {
  SUCCESS: 'success',
  ERROR: 'danger',
  WARNING: 'warning',
  INFO: 'info',
};

/**
 * Animation delay helper
 * @param {number} index - Item index
 * @param {number} baseDelay - Base delay in milliseconds
 * @returns {number} - Calculated delay
 */
export function staggerDelay(index, baseDelay = 50) {
  return index * baseDelay;
}

export default {
  escapeHtml,
  formatNumber,
  storage,
  STORAGE_KEYS,
  JobStatus,
  getStatusIcon,
  getStatusColor,
  isJobCancellable,
  isJobActive,
  debounce,
  throttle,
  DASHBOARD_CONFIG,
  TOAST_VARIANTS,
  staggerDelay,
};