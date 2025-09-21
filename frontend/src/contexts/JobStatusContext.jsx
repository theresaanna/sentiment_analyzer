import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { jobsAPI } from '../services/dashboardApi';

/**
 * Context for managing job statuses across the application
 * This provides a centralized way to track and poll job statuses
 */

const JobStatusContext = createContext();

export const useJobStatus = () => {
  const context = useContext(JobStatusContext);
  if (!context) {
    throw new Error('useJobStatus must be used within a JobStatusProvider');
  }
  return context;
};

export const JobStatusProvider = ({ children }) => {
  // State for all job statuses, keyed by video_id
  const [jobStatuses, setJobStatuses] = useState(() => {
    // Initialize from localStorage if available
    const cached = localStorage.getItem('jobStatuses');
    return cached ? JSON.parse(cached) : {};
  });

  // Track active jobs that need polling
  const [activeJobs, setActiveJobs] = useState(new Set());
  
  // Polling interval reference
  const [pollingInterval, setPollingInterval] = useState(null);
  
  // Track if we're currently polling
  const [isPolling, setIsPolling] = useState(false);

  // Persist job statuses to localStorage
  useEffect(() => {
    localStorage.setItem('jobStatuses', JSON.stringify(jobStatuses));
  }, [jobStatuses]);

  // Add a new job to track
  const trackJob = useCallback((videoId, jobId) => {
    setActiveJobs(prev => new Set([...prev, jobId]));
    setJobStatuses(prev => ({
      ...prev,
      [videoId]: {
        job_id: jobId,
        status: 'queued',
        progress: 0,
        timestamp: Date.now()
      }
    }));
  }, []);

  // Update job status
  const updateJobStatus = useCallback((videoId, status) => {
    setJobStatuses(prev => ({
      ...prev,
      [videoId]: {
        ...prev[videoId],
        ...status,
        timestamp: Date.now()
      }
    }));
  }, []);

  // Remove a job from tracking
  const removeJob = useCallback((videoId) => {
    setJobStatuses(prev => {
      const newStatuses = { ...prev };
      delete newStatuses[videoId];
      return newStatuses;
    });
  }, []);

  // Clear all completed/failed jobs
  const clearCompletedJobs = useCallback(() => {
    setJobStatuses(prev => {
      const newStatuses = {};
      Object.entries(prev).forEach(([videoId, status]) => {
        // Only keep active jobs
        if (['queued', 'processing', 'running'].includes(status.status)) {
          newStatuses[videoId] = status;
        }
      });
      return newStatuses;
    });
  }, []);

  // Poll for job status updates
  const pollJobStatuses = useCallback(async () => {
    if (activeJobs.size === 0 || isPolling) return;
    
    setIsPolling(true);
    try {
      const result = await jobsAPI.getStatus();
      if (result.jobs && Array.isArray(result.jobs)) {
        const updatedStatuses = {};
        const stillActive = new Set();
        
        result.jobs.forEach(job => {
          // Update status for jobs we're tracking
          if (job.video_id) {
            updatedStatuses[job.video_id] = {
              job_id: job.job_id,
              status: job.status,
              progress: job.progress || 0,
              timestamp: Date.now(),
              job_type: job.job_type,
              comment_count: job.comment_count
            };
            
            // Keep tracking if still active
            if (!['completed', 'failed', 'cancelled'].includes(job.status)) {
              stillActive.add(job.job_id);
            }
          }
        });
        
        // Update all statuses at once
        setJobStatuses(prev => ({ ...prev, ...updatedStatuses }));
        setActiveJobs(stillActive);
      }
    } catch (error) {
      console.error('Error polling job statuses:', error);
    } finally {
      setIsPolling(false);
    }
  }, [activeJobs, isPolling]);

  // Set up polling when there are active jobs
  useEffect(() => {
    if (activeJobs.size > 0) {
      // Poll immediately
      pollJobStatuses();
      
      // Set up interval for regular polling
      const interval = setInterval(pollJobStatuses, 3000); // Poll every 3 seconds
      setPollingInterval(interval);
      
      return () => {
        if (interval) clearInterval(interval);
      };
    } else {
      // Clear interval when no active jobs
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
    }
  }, [activeJobs.size]); // Only re-run when the size changes

  // Initial load - check for any active jobs from the server
  useEffect(() => {
    const loadInitialStatuses = async () => {
      try {
        const result = await jobsAPI.getStatus();
        if (result.jobs && Array.isArray(result.jobs)) {
          const statuses = {};
          const active = new Set();
          
          result.jobs.forEach(job => {
            if (job.video_id) {
              statuses[job.video_id] = {
                job_id: job.job_id,
                status: job.status,
                progress: job.progress || 0,
                timestamp: Date.now(),
                job_type: job.job_type,
                comment_count: job.comment_count
              };
              
              if (!['completed', 'failed', 'cancelled'].includes(job.status)) {
                active.add(job.job_id);
              }
            }
          });
          
          setJobStatuses(statuses);
          setActiveJobs(active);
        }
      } catch (error) {
        console.error('Error loading initial job statuses:', error);
      }
    };
    
    loadInitialStatuses();
  }, []); // Only run once on mount

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // Get status for a specific video
  const getVideoJobStatus = useCallback((videoId) => {
    return jobStatuses[videoId] || null;
  }, [jobStatuses]);

  // Check if a video has been preloaded
  const isVideoPreloaded = useCallback((videoId) => {
    const status = jobStatuses[videoId];
    return status && status.status === 'completed' && status.job_type === 'preload';
  }, [jobStatuses]);

  const value = {
    jobStatuses,
    activeJobs,
    isPolling,
    trackJob,
    updateJobStatus,
    removeJob,
    clearCompletedJobs,
    getVideoJobStatus,
    isVideoPreloaded,
    pollJobStatuses
  };

  return (
    <JobStatusContext.Provider value={value}>
      {children}
    </JobStatusContext.Provider>
  );
};