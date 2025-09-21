import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { JobCard } from './JobCard';
import { jobsAPI } from '../../services/dashboardApi';
import { useToast } from '../Toast/ToastContext';
import { useJobStatus } from '../../contexts/JobStatusContext';
import './JobQueue.css';

/**
 * Filter jobs by status
 */
const filterJobsByView = (jobs, view) => {
  switch (view) {
    case 'active':
      return jobs.filter(job => 
        ['queued', 'processing', 'running'].includes(job.status)
      );
    case 'completed':
      return jobs.filter(job => job.status === 'completed');
    case 'failed':
      return jobs.filter(job => job.status === 'failed');
    case 'history':
      return jobs.filter(job => 
        ['completed', 'failed', 'cancelled'].includes(job.status)
      );
    default:
      return jobs;
  }
};

/**
 * Sort jobs by various criteria
 */
const sortJobs = (jobs, sortBy) => {
  const sorted = [...jobs];
  
  switch (sortBy) {
    case 'newest':
      return sorted.sort((a, b) => 
        new Date(b.created_at || 0) - new Date(a.created_at || 0)
      );
    case 'oldest':
      return sorted.sort((a, b) => 
        new Date(a.created_at || 0) - new Date(b.created_at || 0)
      );
    case 'title':
      return sorted.sort((a, b) => {
        const titleA = (a.video_metadata?.title || a.video_title || '').toLowerCase();
        const titleB = (b.video_metadata?.title || b.video_title || '').toLowerCase();
        return titleA.localeCompare(titleB);
      });
    case 'status':
      return sorted.sort((a, b) => a.status.localeCompare(b.status));
    case 'progress':
      return sorted.sort((a, b) => (b.progress || 0) - (a.progress || 0));
    default:
      return sorted;
  }
};

/**
 * JobQueue Component - Enhanced queue display with multiple views
 */
export const JobQueue = ({ 
  initialView = 'all',
  showFilters = true,
  showSearch = true,
  autoRefresh = true,
  refreshInterval = 5000,
  maxJobs = 50,
  className = ''
}) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentView, setCurrentView] = useState(initialView);
  const [sortBy, setSortBy] = useState('newest');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedJobs, setExpandedJobs] = useState(new Set());
  const [selectedJobs, setSelectedJobs] = useState(new Set());
  
  const { showToast } = useToast();
  const { pollJobStatuses } = useJobStatus();
  
  // Fetch jobs from API
  const fetchJobs = useCallback(async () => {
    try {
      setError(null);
      const result = await jobsAPI.getStatus();
      
      if (result.success && result.jobs) {
        // Limit number of jobs
        const limitedJobs = result.jobs.slice(0, maxJobs);
        setJobs(limitedJobs);
        
        // Trigger status context update
        if (pollJobStatuses) {
          pollJobStatuses();
        }
      }
    } catch (err) {
      console.error('Error fetching jobs:', err);
      setError(err.message);
      showToast('Failed to fetch jobs', 'danger');
    } finally {
      setLoading(false);
    }
  }, [maxJobs, showToast, pollJobStatuses]);
  
  // Initial fetch
  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);
  
  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(fetchJobs, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchJobs]);
  
  // Handle job cancellation
  const handleCancelJob = useCallback(async (jobId) => {
    try {
      const result = await jobsAPI.cancelJob(jobId);
      if (result.success) {
        showToast('Job cancelled successfully', 'success');
        fetchJobs();
      }
    } catch (err) {
      showToast('Failed to cancel job', 'danger');
    }
  }, [showToast, fetchJobs]);
  
  // Handle job retry
  const handleRetryJob = useCallback(async (jobId) => {
    try {
      // Find the job to retry
      const job = jobs.find(j => j.job_id === jobId);
      if (!job || !job.video_id) {
        showToast('Cannot retry this job', 'warning');
        return;
      }
      
      // Queue a new job based on the failed one
      if (job.job_type === 'preload' || job.job_type === 'pro_preload') {
        const { preloadAPI } = await import('../../services/dashboardApi');
        await preloadAPI.queuePreload(job.video_id, job.comment_count_requested);
        showToast('Preload job requeued', 'success');
      } else {
        showToast('Job retry not available for this type', 'info');
      }
      
      fetchJobs();
    } catch (err) {
      showToast('Failed to retry job', 'danger');
    }
  }, [jobs, showToast, fetchJobs]);
  
  // Handle view analysis
  const handleViewAnalysis = useCallback((videoId) => {
    window.location.href = `/analyze/${videoId}`;
  }, []);
  
  // Handle expand toggle
  const handleToggleExpand = useCallback((jobId) => {
    setExpandedJobs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(jobId)) {
        newSet.delete(jobId);
      } else {
        newSet.add(jobId);
      }
      return newSet;
    });
  }, []);
  
  // Handle batch actions
  const handleSelectJob = useCallback((jobId, selected) => {
    setSelectedJobs(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(jobId);
      } else {
        newSet.delete(jobId);
      }
      return newSet;
    });
  }, []);
  
  const handleSelectAll = useCallback(() => {
    const visibleJobs = filteredAndSortedJobs.map(j => j.job_id);
    if (selectedJobs.size === visibleJobs.length) {
      setSelectedJobs(new Set());
    } else {
      setSelectedJobs(new Set(visibleJobs));
    }
  }, [selectedJobs]);
  
  const handleBatchCancel = useCallback(async () => {
    if (selectedJobs.size === 0) return;
    
    const confirmMsg = `Cancel ${selectedJobs.size} job(s)?`;
    if (!window.confirm(confirmMsg)) return;
    
    try {
      const promises = Array.from(selectedJobs).map(jobId => 
        jobsAPI.cancelJob(jobId).catch(err => ({ error: err }))
      );
      
      const results = await Promise.all(promises);
      const successCount = results.filter(r => !r.error).length;
      
      if (successCount > 0) {
        showToast(`${successCount} job(s) cancelled`, 'success');
        setSelectedJobs(new Set());
        fetchJobs();
      }
    } catch (err) {
      showToast('Failed to cancel jobs', 'danger');
    }
  }, [selectedJobs, showToast, fetchJobs]);
  
  // Filter and sort jobs
  const filteredAndSortedJobs = useMemo(() => {
    let filtered = filterJobsByView(jobs, currentView);
    
    // Apply search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(job => {
        const title = (job.video_metadata?.title || job.video_title || '').toLowerCase();
        const channel = (job.video_metadata?.channel_title || '').toLowerCase();
        const id = (job.video_id || job.job_id || '').toLowerCase();
        
        return title.includes(search) || 
               channel.includes(search) || 
               id.includes(search);
      });
    }
    
    // Apply sorting
    return sortJobs(filtered, sortBy);
  }, [jobs, currentView, sortBy, searchTerm]);
  
  // View counts
  const viewCounts = useMemo(() => ({
    all: jobs.length,
    active: filterJobsByView(jobs, 'active').length,
    completed: filterJobsByView(jobs, 'completed').length,
    failed: filterJobsByView(jobs, 'failed').length,
    history: filterJobsByView(jobs, 'history').length
  }), [jobs]);
  
  // Loading state
  if (loading) {
    return (
      <div className={`job-queue ${className}`}>
        <div className="queue-loading">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading jobs...</span>
          </div>
          <p className="mt-3">Loading job queue...</p>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className={`job-queue ${className}`}>
        <div className="queue-error">
          <div className="alert alert-danger">
            <i className="fas fa-exclamation-triangle"></i> {error}
            <button 
              className="btn btn-sm btn-outline-danger ms-3"
              onClick={fetchJobs}
            >
              <i className="fas fa-redo"></i> Retry
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className={`job-queue ${className}`}>
      {/* Header */}
      <div className="queue-header">
        <h2 className="queue-title">
          <i className="fas fa-tasks"></i> Processing Queue
        </h2>
        
        <div className="queue-actions">
          <button 
            className="btn btn-sm btn-outline-primary"
            onClick={fetchJobs}
            title="Refresh"
          >
            <i className="fas fa-sync"></i>
          </button>
          
          {selectedJobs.size > 0 && (
            <button 
              className="btn btn-sm btn-danger"
              onClick={handleBatchCancel}
            >
              <i className="fas fa-times"></i> Cancel {selectedJobs.size}
            </button>
          )}
        </div>
      </div>
      
      {/* Tabs */}
      <div className="queue-tabs">
        <ul className="nav nav-tabs">
          <li className="nav-item">
            <button 
              className={`nav-link ${currentView === 'all' ? 'active' : ''}`}
              onClick={() => setCurrentView('all')}
            >
              All <span className="badge bg-secondary ms-1">{viewCounts.all}</span>
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${currentView === 'active' ? 'active' : ''}`}
              onClick={() => setCurrentView('active')}
            >
              Active <span className="badge bg-primary ms-1">{viewCounts.active}</span>
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${currentView === 'completed' ? 'active' : ''}`}
              onClick={() => setCurrentView('completed')}
            >
              Completed <span className="badge bg-success ms-1">{viewCounts.completed}</span>
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${currentView === 'failed' ? 'active' : ''}`}
              onClick={() => setCurrentView('failed')}
            >
              Failed <span className="badge bg-danger ms-1">{viewCounts.failed}</span>
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link ${currentView === 'history' ? 'active' : ''}`}
              onClick={() => setCurrentView('history')}
            >
              History <span className="badge bg-info ms-1"><span aria-hidden="true">{viewCounts.history}</span><span className="visually-hidden">{viewCounts.history} items</span></span>
            </button>
          </li>
        </ul>
      </div>
      
      {/* Filters */}
      {(showFilters || showSearch) && (
        <div className="queue-filters">
          {showSearch && (
            <div className="search-box">
              <i className="fas fa-search"></i>
              <input 
                type="text"
                className="form-control"
                placeholder="Search by title, channel, or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          )}
          
          {showFilters && (
            <div className="filter-controls">
              <select 
                className="form-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="title">By Title</option>
                <option value="status">By Status</option>
                <option value="progress">By Progress</option>
              </select>
              
              {filteredAndSortedJobs.length > 0 && (
                <button 
                  className="btn btn-sm btn-outline-secondary"
                  onClick={handleSelectAll}
                >
                  {selectedJobs.size === filteredAndSortedJobs.length ? 
                    'Deselect All' : 'Select All'}
                </button>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Job List */}
      <div className="queue-content">
        {filteredAndSortedJobs.length === 0 ? (
          <div className="queue-empty">
            <i className="fas fa-inbox fa-3x text-muted mb-3"></i>
            <h4>No jobs found</h4>
            <p className="text-muted">
              {searchTerm ? 
                'Try adjusting your search criteria' : 
                `No ${currentView === 'all' ? '' : currentView} jobs in the queue`}
            </p>
          </div>
        ) : (
          <div className="job-list">
            {filteredAndSortedJobs.map(job => (
              <JobCard 
                key={job.job_id}
                job={job}
                expanded={expandedJobs.has(job.job_id)}
                onToggleExpand={handleToggleExpand}
                onCancel={handleCancelJob}
                onRetry={handleRetryJob}
                onViewAnalysis={handleViewAnalysis}
                showActions={true}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* Footer */}
      {filteredAndSortedJobs.length > 0 && (
        <div className="queue-footer">
          <div className="queue-stats">
            Showing {filteredAndSortedJobs.length} of {jobs.length} jobs
          </div>
          
          {autoRefresh && (
            <div className="auto-refresh-indicator">
              <i className="fas fa-sync fa-spin"></i> Auto-refreshing every {refreshInterval / 1000}s
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default JobQueue;