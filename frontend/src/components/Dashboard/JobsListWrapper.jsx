import React, { useState, useEffect } from 'react';
import { JobsList } from './JobsList';

/**
 * Stateful wrapper for JobsList that manages fetching and state
 * This matches what the tests expect
 */
export const JobsListWrapper = ({ onJobCancelled }) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchJobs();
  }, [filter]);

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);
      
      const response = await fetch(`/api/jobs?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch jobs');
      }
      
      const data = await response.json();
      setJobs(data.jobs || []);
    } catch (err) {
      setError(err.message);
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelJob = async (jobId) => {
    try {
      const response = await fetch(`/api/jobs/${jobId}/cancel`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error('Failed to cancel job');
      }
      
      const data = await response.json();
      if (data.success) {
        // Remove cancelled job from list
        setJobs(prev => prev.filter(j => j.id !== jobId));
        if (onJobCancelled) {
          onJobCancelled(jobId);
        }
      }
    } catch (err) {
      console.error('Error cancelling job:', err);
    }
  };

  if (loading) {
    return (
      <div className="jobs-list-container">
        <div className="text-center py-3">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading jobs...</span>
          </div>
          <p className="mt-2">Loading jobs...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="jobs-list-container">
        <div className="alert alert-danger">
          <i className="fas fa-exclamation-triangle"></i> Failed to load jobs
          <button 
            className="btn btn-sm btn-outline-danger ms-3"
            onClick={fetchJobs}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const filteredJobs = filter === 'all' 
    ? jobs 
    : jobs.filter(job => job.status === filter);

  return (
    <div className="jobs-list-container">
      <div className="mb-3">
        <select 
          className="form-select" 
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">All Jobs</option>
          <option value="queued">Queued</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      
      <button 
        className="btn btn-sm btn-primary mb-3"
        onClick={fetchJobs}
      >
        Refresh
      </button>

      <JobsList 
        jobs={filteredJobs}
        isLoading={false}
        onCancelJob={handleCancelJob}
      />
    </div>
  );
};

// Export both the wrapper and the original for backwards compatibility
export { JobsList } from './JobsList';