import React, { memo } from 'react';
import PropTypes from 'prop-types';
import './VideoGrid.css';

/**
 * Individual video card component
 */
const VideoCard = memo(({ video, onVideoClick }) => {
  const formatDuration = (duration) => {
    if (!duration) return '';
    
    // Parse ISO 8601 duration (e.g., PT4M13S)
    const match = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
    if (!match) return duration;
    
    const hours = parseInt(match[1]) || 0;
    const minutes = parseInt(match[2]) || 0;
    const seconds = parseInt(match[3]) || 0;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatViews = (views) => {
    if (!views) return '0 views';
    
    if (views >= 1000000) {
      return `${(views / 1000000).toFixed(1)}M views`;
    } else if (views >= 1000) {
      return `${(views / 1000).toFixed(1)}K views`;
    }
    return `${views.toLocaleString()} views`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  return (
    <div 
      className="video-card" 
      onClick={() => onVideoClick(video)}
      role="button"
      tabIndex={0}
      onKeyPress={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onVideoClick(video);
        }
      }}
      aria-label={`Video: ${video.title}`}
    >
      <div className="video-thumbnail-container">
        <img 
          src={video.thumbnail || `https://i.ytimg.com/vi/${video.video_id}/mqdefault.jpg`}
          alt={video.title}
          className="video-thumbnail"
          loading="lazy"
        />
        {video.duration && (
          <span className="video-duration">{formatDuration(video.duration)}</span>
        )}
      </div>
      
      <div className="video-info">
        <h3 className="video-title" title={video.title}>
          {video.title}
        </h3>
        
        <div className="video-metadata">
          <span className="video-channel">{video.channel_title || 'Unknown Channel'}</span>
          <div className="video-stats">
            <span className="video-views">{formatViews(video.views)}</span>
            <span className="video-separator">•</span>
            <span className="video-date">{formatDate(video.published_at)}</span>
          </div>
        </div>
        
        {video.sentiment_data && (
          <div className="video-sentiment">
            <div className="sentiment-badge" data-sentiment={video.sentiment_data.overall_sentiment}>
              {video.sentiment_data.overall_sentiment}
            </div>
            <span className="comment-count">
              {video.sentiment_data.comment_count} comments analyzed
            </span>
          </div>
        )}
      </div>
    </div>
  );
});

VideoCard.propTypes = {
  video: PropTypes.shape({
    video_id: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    thumbnail: PropTypes.string,
    duration: PropTypes.string,
    views: PropTypes.number,
    channel_title: PropTypes.string,
    published_at: PropTypes.string,
    sentiment_data: PropTypes.shape({
      overall_sentiment: PropTypes.string,
      comment_count: PropTypes.number
    })
  }).isRequired,
  onVideoClick: PropTypes.func.isRequired
};

VideoCard.displayName = 'VideoCard';

/**
 * VideoGrid component - displays videos in a responsive grid layout
 */
const VideoGrid = ({ videos, onVideoClick, loading, error }) => {
  if (error) {
    return (
      <div className="video-grid-error">
        <div className="error-icon">⚠️</div>
        <p>Error loading videos: {error}</p>
      </div>
    );
  }

  if (!loading && videos.length === 0) {
    return (
      <div className="video-grid-empty">
        <div className="empty-icon">📹</div>
        <p>No videos found</p>
        <span>Videos from your channel will appear here</span>
      </div>
    );
  }

  return (
    <div className="video-grid">
      {videos.map((video) => (
        <VideoCard 
          key={video.video_id} 
          video={video} 
          onVideoClick={onVideoClick}
        />
      ))}
      
      {loading && (
        <div className="video-grid-loading">
          {[...Array(6)].map((_, index) => (
            <div key={`skeleton-${index}`} className="video-card-skeleton">
              <div className="skeleton-thumbnail"></div>
              <div className="skeleton-info">
                <div className="skeleton-title"></div>
                <div className="skeleton-metadata"></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

VideoGrid.propTypes = {
  videos: PropTypes.arrayOf(PropTypes.object).isRequired,
  onVideoClick: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  error: PropTypes.string
};

VideoGrid.defaultProps = {
  loading: false,
  error: null
};

export default VideoGrid;