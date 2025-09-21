import React, { useState, useEffect } from 'react';
import { formatNumber, staggerDelay } from '../../utils/dashboardUtils';
import { preloadAPI } from '../../services/dashboardApi';
import { useToast } from '../Toast/ToastContext';
import { useJobStatus } from '../../contexts/JobStatusContext';
import './VideoList.css';

/**
 * Individual Video Item Component
 */
const VideoItem = ({ video, isPreloaded, jobStatus, onPreload, index }) => {
  const [isPreloading, setIsPreloading] = useState(false);
  const [localPreloaded, setLocalPreloaded] = useState(isPreloaded);

  useEffect(() => {
    setLocalPreloaded(isPreloaded);
  }, [isPreloaded]);

  // Update preloading state based on job status
  useEffect(() => {
    if (jobStatus) {
      if (jobStatus.status === 'queued' || jobStatus.status === 'processing') {
        setIsPreloading(true);
        setLocalPreloaded(false);
      } else if (jobStatus.status === 'completed') {
        setIsPreloading(false);
        setLocalPreloaded(true);
      } else if (jobStatus.status === 'failed' || jobStatus.status === 'cancelled') {
        setIsPreloading(false);
        setLocalPreloaded(false);
      }
    }
  }, [jobStatus]);

  const handlePreload = async () => {
    if (localPreloaded || isPreloading) return;
    
    setIsPreloading(true);
    const success = await onPreload(video.id);  // Parent will handle job tracking
    // If onPreload returns false or undefined (error), reset loading state
    if (!success) {
      setIsPreloading(false);
    }
  };

  // Determine button state and text based on job status
  const getButtonContent = () => {
    if (jobStatus) {
      switch(jobStatus.status) {
        case 'queued':
          return (
            <>
              <i className="fas fa-hourglass-half"></i> Queued
              {jobStatus.progress > 0 && <span className="ms-1">({jobStatus.progress}%)</span>}
            </>
          );
        case 'processing':
          return (
            <>
              <i className="fas fa-spinner fa-spin"></i> Processing
              {jobStatus.progress > 0 && <span className="ms-1">({jobStatus.progress}%)</span>}
            </>
          );
        case 'completed':
          return (
            <>
              <span className="button-icon">✅</span>
              <span className="button-text">Preloaded</span>
            </>
          );
        case 'failed':
          return (
            <>
              <span className="button-icon">❌</span>
              <span className="button-text">Failed</span>
            </>
          );
        case 'cancelled':
          return (
            <>
              <span className="button-icon">🚫</span>
              <span className="button-text">Cancelled</span>
            </>
          );
        default:
          break;
      }
    }

    if (isPreloading) {
      return (
        <>
          <i className="fas fa-spinner fa-spin"></i> Queuing...
        </>
      );
    } else if (localPreloaded) {
      return (
        <>
          <span className="button-icon">✅</span>
          <span className="button-text">Preloaded</span>
        </>
      );
    } else {
      return (
        <>
          <span className="button-icon">🚀</span>
          <span className="button-text">Preload</span>
        </>
      );
    }
  };

  return (
    <div 
      className="video-item"
      style={{
        opacity: 0,
        animation: `fadeIn 0.5s ease-in-out forwards`,
        animationDelay: `${staggerDelay(index)}ms`
      }}
    >
      <div className="flex-grow-1">
        <p className="video-title">
          <a 
            href={`/analyze/${video.id}`}
            className="text-decoration-none"
            title={`Click to analyze: ${video.title || 'Untitled'}`}
            data-bs-toggle="tooltip"
            data-bs-placement="top"
          >
            <i className="fas fa-play-circle" style={{ color: '#ff0000', transition: 'all 0.2s ease' }}></i>
            <span>{video.title || 'Untitled'}</span>
          </a>
        </p>
        <div className="video-meta">
          <span className="me-3">
            <i className="fas fa-fingerprint me-1"></i>
            <code>{video.id}</code>
          </span>
          <span className="me-3">
            <i className="fas fa-eye me-1"></i>
            {formatNumber(video.statistics?.views)} views
          </span>
          <span>
            <i className="fas fa-comment me-1"></i>
            {formatNumber(video.statistics?.comments)} comments
          </span>
        </div>
      </div>
      <div>
        <button 
          className={`vibe-button small ${
            localPreloaded ? 'preloaded' : ''
          } ${
            jobStatus?.status === 'failed' ? 'failed' : ''
          } ${
            jobStatus?.status === 'cancelled' ? 'cancelled' : ''
          }`}
          onClick={handlePreload}
          disabled={localPreloaded || isPreloading || 
            (jobStatus && ['queued', 'processing'].includes(jobStatus.status))}
        >
          {getButtonContent()}
        </button>
      </div>
    </div>
  );
};

/**
 * Video List Component
 */
const VideoList = ({ videos, preloadedVideos: propPreloadedVideos = new Set(), isLoading }) => {
  const { showToast } = useToast();
  const { getVideoJobStatus, trackJob, isVideoPreloaded, preloadedVideos: contextPreloadedVideos } = useJobStatus();
  
  // Combine preloaded videos from props and context
  const allPreloadedVideos = new Set([
    ...propPreloadedVideos,
    ...contextPreloadedVideos
  ]);
  
  // Handle preload action
  const handlePreload = async (videoId) => {
    try {
      const result = await preloadAPI.queuePreload(videoId);
      if (result.job_id) {
        // Track this job in the context
        trackJob(videoId, result.job_id);
        showToast(`Preload queued for video`, 'success');
        return true; // Success
      }
      return false; // No job_id
    } catch (error) {
      showToast(error.message || 'Failed to queue preload', 'danger');
      return false; // Error occurred
    }
  };

  if (isLoading) {
    return (
      <div className="video-list-container">
        <div className="loading-overlay">
          <div className="text-center">
            <div className="spinner-border text-primary mb-3" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="text-muted">Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!videos || videos.length === 0) {
    return (
      <div className="video-list">
        <div className="no-items-message">
          <i className="fas fa-film"></i>
          <p>No videos found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="video-list">
      {videos.map((video, index) => {
        const jobStatus = getVideoJobStatus(video.id);
        const isPreloaded = allPreloadedVideos.has(video.id) || 
                           isVideoPreloaded(video.id) ||
                           jobStatus?.status === 'completed';
        
        return (
          <VideoItem
            key={video.id}
            video={video}
            isPreloaded={isPreloaded}
            jobStatus={jobStatus}
            onPreload={handlePreload}
            index={index}
          />
        );
      })}
    </div>
  );
};

export { VideoList };
