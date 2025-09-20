import React from 'react';
import { getStatusIcon, getStatusColor, isJobCancellable, formatNumber } from '../../utils/dashboardUtils';
import './JobsList.css';

/**
 * Individual Job Item Component
 */
const JobItem = ({ job, onCancel }) => {
  const statusIcon = getStatusIcon(job.status);
  const statusColor = getStatusColor(job.status);
  const isCancellable = isJobCancellable(job.status);
  const isCompleted = job.status === 'completed';
  const isSync = job.job_type === 'channel_sync';
  
  // Extract video metadata
  const hasMetadata = job.video_metadata && job.video_metadata.title;
  const videoTitle = hasMetadata ? job.video_metadata.title : (job.video_id ? `Video ${job.video_id}` : '');
  const truncatedTitle = videoTitle.length > 60 ? videoTitle.substring(0, 60) + '...' : videoTitle;
  
  return (
    <div className="job-item" data-job-id={job.job_id}>
      <div>
        <div className="d-flex justify-content-between align-items-center">
          <div className="flex-grow-1">
            <div>
              <span className="job-type">
                {isSync ? (
                  <><i className="fas fa-sync"></i> CHANNEL SYNC</>
                ) : (
                  <><i className="fas fa-download"></i> COMMENT PRELOAD</>
                )}
              </span>
              {job.video_id && <code className="ms-2">{job.video_id}</code>}
            </div>
            {job.video_id && (
              <div className="mt-2">
                {isCompleted ? (
                  <a href={`/analyze/${job.video_id}`} className="text-decoration-none fw-bold">
                    <i className="fas fa-chart-line me-1"></i>View Analysis
                  </a>
                ) : (
                  <span className="text-muted">
                    <i className="fas fa-video me-1"></i>
                    {truncatedTitle || `Video: ${job.video_id}`}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="d-flex align-items-center job-status-container">
            <span className={`badge bg-${statusColor} me-2 job-status-badge`}>
              {statusIcon} {job.status}
            </span>
            <div className="job-progress-container">
              {job.status === 'running' ? (
                <div className="progress" style={{ width: '100px', height: '20px' }}>
                  <div 
                    className="progress-bar progress-bar-striped progress-bar-animated bg-primary"
                    role="progressbar"
                    style={{ width: `${job.progress || 0}%` }}
                    aria-valuenow={job.progress || 0}
                    aria-valuemin="0"
                    aria-valuemax="100"
                  >
                    {job.progress || 0}%
                  </div>
                </div>
              ) : job.status !== 'completed' ? (
                <span className="job-progress">{job.progress || 0}%</span>
              ) : null}
            </div>
            {isCancellable && (
              <button 
                className="job-cancel-btn"
                onClick={() => onCancel(job.job_id, job.video_id || job.channel_id || '')}
              >
                <i className="fas fa-times"></i> Cancel
              </button>
            )}
            {isCompleted && job.video_id && (
              <a 
                href={`/analyze/${job.video_id}`} 
                className="btn btn-sm btn-success ms-2"
                style={{ padding: '4px 12px', fontSize: '0.85rem' }}
              >
                <i className="fas fa-external-link-alt"></i> View
              </a>
            )}
          </div>
        </div>
        {hasMetadata && job.video_metadata && (
          <div className="job-video-meta">
            {job.video_metadata.views && (
              <span>
                <i className="fas fa-eye"></i> {formatNumber(job.video_metadata.views)} views
              </span>
            )}
            {job.video_metadata.comments && (
              <span>
                <i className="fas fa-comment"></i> {formatNumber(job.video_metadata.comments)} comments
              </span>
            )}
            {job.video_metadata.published && (
              <span>
                <i className="fas fa-calendar"></i> {job.video_metadata.published.split('T')[0]}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Jobs List Component
 */
const JobsList = ({ jobs, isLoading, onCancelJob }) => {
  if (isLoading) {
    return (
      <div className="jobs-container-wrapper">
        <div className="loading-overlay">
          <div className="text-center">
            <div className="spinner-border spinner-border-sm text-primary" role="status">
              <span className="visually-hidden">Loading jobs...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!jobs || jobs.length === 0) {
    return (
      <div className="no-items-message">
        <i className="fas fa-check-circle"></i>
        <p>No active jobs</p>
      </div>
    );
  }

  return (
    <div id="jobsContainer">
      {jobs.map(job => (
        <JobItem 
          key={job.job_id} 
          job={job} 
          onCancel={onCancelJob}
        />
      ))}
    </div>
  );
};

export default JobsList;