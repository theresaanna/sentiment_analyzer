import React, { useState, useEffect } from 'react';
import { formatNumber, staggerDelay } from '../../utils/dashboardUtils';
import { preloadAPI } from '../../services/dashboardApi';
import { useToast } from '../Toast/ToastContext';
import './VideoList.css';

/**
 * Individual Video Item Component
 */
const VideoItem = ({ video, isPreloaded, onPreload, index }) => {
  const [isPreloading, setIsPreloading] = useState(false);
  const [localPreloaded, setLocalPreloaded] = useState(isPreloaded);

  useEffect(() => {
    setLocalPreloaded(isPreloaded);
  }, [isPreloaded]);

  const handlePreload = async () => {
    if (localPreloaded || isPreloading) return;
    
    setIsPreloading(true);
    await onPreload(video.id);
    
    // Optimistically mark as preloaded
    setTimeout(() => {
      setLocalPreloaded(true);
      setIsPreloading(false);
    }, 2000);
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
          className={`vibe-button small ${localPreloaded ? 'preloaded' : ''}`}
          onClick={handlePreload}
          disabled={localPreloaded || isPreloading}
        >
          {isPreloading ? (
            <>
              <i className="fas fa-spinner fa-spin"></i> Queuing...
            </>
          ) : localPreloaded ? (
            <>
              <span className="button-icon">✅</span>
              <span className="button-text">Preloaded</span>
            </>
          ) : (
            <>
              <span className="button-icon">🚀</span>
              <span className="button-text">Preload</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

/**
 * Video List Component
 */
const VideoList = ({ videos, preloadedVideos, isLoading }) => {
  const { showToast } = useToast();
  
  const handlePreload = async (videoId) => {
    try {
      await preloadAPI.queuePreload(videoId);
      showToast(`Preload queued for ${videoId}`, 'success');
    } catch (error) {
      showToast(error.message || 'Failed to queue preload', 'danger');
    }
  };

  if (isLoading) {
    return (
      <div className="video-list-container">
        <div className="loading-overlay">
          <div className="text-center">
            <div className="spinner-border text-primary mb-3" role="status">
              <span className="visually-hidden">Loading videos...</span>
            </div>
            <p className="text-muted">Loading videos...</p>
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
      {videos.map((video, index) => (
        <VideoItem
          key={video.id}
          video={video}
          isPreloaded={preloadedVideos.has(video.id)}
          onPreload={handlePreload}
          index={index}
        />
      ))}
    </div>
  );
};

export default VideoList;