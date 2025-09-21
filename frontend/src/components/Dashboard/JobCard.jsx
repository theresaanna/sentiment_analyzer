import React, { useState, useMemo } from 'react';
import { formatNumber, getStatusIcon, getStatusColor } from '../../utils/dashboardUtils';
import './JobCard.css';

/**
 * Format duration from ISO 8601 (PT10M30S) to human readable
 */
const formatDuration = (duration) => {
  if (!duration) return null;
  
  const match = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!match) return duration;
  
  const hours = parseInt(match[1] || 0);
  const minutes = parseInt(match[2] || 0);
  const seconds = parseInt(match[3] || 0);
  
  const parts = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (seconds > 0 && hours === 0) parts.push(`${seconds}s`);
  
  return parts.join(' ') || '0s';
};

/**
 * Format date to relative time
 */
const formatRelativeTime = (dateString) => {
  if (!dateString) return null;
  
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (days > 7) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  } else if (days > 0) {
    return `${days}d ago`;
  } else if (hours > 0) {
    return `${hours}h ago`;
  } else if (minutes > 0) {
    return `${minutes}m ago`;
  } else {
    return 'just now';
  }
};

/**
 * JobCard Component - Enhanced display for job items with metadata
 */
export const JobCard = ({ 
  job, 
  onCancel, 
  onRetry, 
  onViewAnalysis,
  expanded,
  onToggleExpand,
  showActions = true,
  className = ''
}) => {
  const [localExpanded, setLocalExpanded] = useState(expanded);
  
  // Compute derived values
  // Use controlled expansion only if expanded prop is explicitly provided
  const isExpanded = typeof expanded !== 'undefined' ? expanded : localExpanded;
  const statusIcon = getStatusIcon(job.status);
  const statusColor = getStatusColor(job.status);
  const isActive = ['queued', 'processing', 'running'].includes(job.status);
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';
  const isCancellable = isActive && showActions;
  
  // Extract metadata
  const metadata = job.video_metadata || {};
  const videoTitle = metadata.title || job.video_title || (job.video_id ? `Video ${job.video_id}` : 'Untitled');
  const channelTitle = metadata.channel_title || job.channel_title || '';
  const duration = formatDuration(metadata.duration);
  // Choose a sensible timestamp: if job was created very recently, show that; otherwise use video published date
  let timestampToFormat = null;
  const createdAtDate = job.created_at ? new Date(job.created_at) : null;
  const publishedAtDate = metadata.published_at ? new Date(metadata.published_at) : null;
  if (createdAtDate) {
    const RECENT_MS = 48 * 60 * 60 * 1000; // 48 hours threshold
    if (!publishedAtDate || (Date.now() - createdAtDate.getTime()) < RECENT_MS) {
      timestampToFormat = job.created_at;
    } else {
      timestampToFormat = metadata.published_at;
    }
  } else if (publishedAtDate) {
    timestampToFormat = metadata.published_at;
  }
  const publishedAt = formatRelativeTime(timestampToFormat);
  const thumbnail = metadata.thumbnail || null;
  
  // Job type display
  const jobTypeDisplay = useMemo(() => {
    switch (job.job_type) {
      case 'preload':
      case 'pro_preload':
        return { icon: 'fa-download', label: 'PRELOAD', color: 'primary' };
      case 'analysis':
        return { icon: 'fa-chart-line', label: 'ANALYSIS', color: 'success' };
      case 'channel_sync':
        return { icon: 'fa-sync', label: 'CHANNEL SYNC', color: 'info' };
      default:
        return { icon: 'fa-tasks', label: job.job_type?.toUpperCase() || 'JOB', color: 'secondary' };
    }
  }, [job.job_type]);
  
  // Progress display
  const progressPercentage = job.progress || 0;
  const progressText = job.status === 'processing' && job.processed_count && job.total_count
    ? `${job.processed_count} / ${job.total_count}`
    : `${progressPercentage}%`;
  
  const handleToggle = () => {
    // Always toggle local expanded state for usability in uncontrolled scenarios
    setLocalExpanded(prev => !prev);
    // Also notify parent if callback provided (for controlled scenarios)
    if (onToggleExpand) {
      onToggleExpand(job.job_id);
    }
  };
  
  return (
    <div 
      className={`job-card ${className} status-${job.status} ${isExpanded ? 'expanded' : ''}`}
      data-job-id={job.job_id}
      data-testid="job-card"
    >
      {/* Card Header */}
      <div className="job-card-header" onClick={handleToggle}>
        <div className="job-card-header-left">
          {thumbnail && (
            <div className="job-thumbnail">
              <img src={thumbnail} alt={videoTitle} loading="lazy" />
            </div>
          )}
          
          <div className="job-info">
            <div className="job-title-row">
              <span className={`job-type-badge badge bg-${jobTypeDisplay.color}`}>
                <i className={`fas ${jobTypeDisplay.icon}`}></i> {jobTypeDisplay.label}
              </span>
              <h3 className="job-title" title={videoTitle}>
                {videoTitle.length > 60 ? `${videoTitle.substring(0, 60)}...` : videoTitle}
              </h3>
            </div>
            
            {channelTitle && (
              <div className="job-channel">
                <i className="fas fa-user-circle"></i> {channelTitle}
              </div>
            )}
            
            <div className="job-meta">
              {job.video_id && (
                <span className="meta-item">
                  <i className="fas fa-fingerprint"></i> 
                  <code>{job.video_id}</code>
                </span>
              )}
              {duration && (
                <span className="meta-item">
                  <i className="fas fa-clock"></i> {duration}
                </span>
              )}
              {publishedAt && (
                <span className="meta-item">
                  <i className="fas fa-calendar"></i> {publishedAt}
                </span>
              )}
            </div>
          </div>
        </div>
        
        <div className="job-card-header-right">
          <div className={`job-status badge bg-${statusColor}`}>
            <span aria-hidden="true">{statusIcon}</span>
            <span className="status-text">{job.status.toUpperCase()}</span>
          </div>
          
          {isActive && (
            <div className="job-progress">
              <div className="progress">
                <div 
                  className="progress-bar progress-bar-striped progress-bar-animated"
                  role="progressbar"
                  style={{ width: `${progressPercentage}%` }}
                  aria-valuenow={progressPercentage}
                  aria-valuemin="0"
                  aria-valuemax="100"
                >
                  {progressText}
                </div>
              </div>
            </div>
          )}
          
          <button className="expand-toggle" aria-label="Toggle details">
            <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'}`}></i>
          </button>
        </div>
      </div>
      
      {/* Expanded Content */}
      {isExpanded && (
        <div className="job-card-body">
          <div className="job-details">
            {/* Video Statistics */}
            {(metadata.views || metadata.likes || metadata.comments) && (
              <div className="job-stats">
                <h4>Video Statistics</h4>
                <div className="stats-grid">
                  {metadata.views !== undefined && (
                    <div className="stat-item">
                      <i className="fas fa-eye"></i>
                      <span className="stat-value">{formatNumber(metadata.views)}</span>
                      <span className="stat-label">Views</span>
                    </div>
                  )}
                  {metadata.likes !== undefined && (
                    <div className="stat-item">
                      <i className="fas fa-thumbs-up"></i>
                      <span className="stat-value">{formatNumber(metadata.likes)}</span>
                      <span className="stat-label">Likes</span>
                    </div>
                  )}
                  {metadata.comments !== undefined && (
                    <div className="stat-item">
                      <i className="fas fa-comment"></i>
                      <span className="stat-value">{formatNumber(metadata.comments)}</span>
                      <span className="stat-label">Comments</span>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Job Details */}
            <div className="job-metadata">
              <h4>Job Information</h4>
              <dl className="metadata-list">
                <dt>Job ID:</dt>
                <dd><code>{job.job_id}</code></dd>
                
                {job.comment_count_requested && (
                  <>
                    <dt>Comments Requested:</dt>
                    <dd>{formatNumber(job.comment_count_requested)}</dd>
                  </>
                )}
                
                {job.created_at && (
                  <>
                    <dt>Created:</dt>
                    <dd>{new Date(job.created_at).toLocaleString()}</dd>
                  </>
                )}
                
                {job.completed_at && (
                  <>
                    <dt>Completed:</dt>
                    <dd>{new Date(job.completed_at).toLocaleString()}</dd>
                  </>
                )}
                
                {job.error_message && (
                  <>
                    <dt>Error:</dt>
                    <dd className="error-message">{job.error_message}</dd>
                  </>
                )}
              </dl>
            </div>
            
            {/* Description if available */}
            {metadata.description && (
              <div className="job-description">
                <h4>Description</h4>
                <p className="description-text">
                  {metadata.description.length > 200 
                    ? `${metadata.description.substring(0, 200)}...` 
                    : metadata.description}
                </p>
              </div>
            )}
          </div>
          
          {/* Action Buttons */}
          {showActions && (
            <div className="job-actions">
              {isCancellable && onCancel && (
                <button 
                  className="btn btn-sm btn-danger"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCancel(job.job_id);
                  }}
                >
                  <i className="fas fa-times"></i> Cancel
                </button>
              )}
              
              {isCompleted && job.video_id && onViewAnalysis && (
                <button 
                  className="btn btn-sm btn-success"
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewAnalysis(job.video_id);
                  }}
                >
                  <i className="fas fa-chart-line"></i> View Analysis
                </button>
              )}
              
              {isFailed && onRetry && (
                <button 
                  className="btn btn-sm btn-warning"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRetry(job.job_id);
                  }}
                >
                  <i className="fas fa-redo"></i> Retry
                </button>
              )}
              
              {job.video_id && (
                <a 
                  href={`https://youtube.com/watch?v=${job.video_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-sm btn-outline-secondary"
                  onClick={(e) => e.stopPropagation()}
                >
                  <i className="fab fa-youtube"></i> View on YouTube
                </a>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default JobCard;