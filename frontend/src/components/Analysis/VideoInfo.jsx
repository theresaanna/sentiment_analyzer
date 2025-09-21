import React from 'react';
import PropTypes from 'prop-types';

export function VideoInfo({ data }) {
  if (!data) return null;

  const formatDuration = (duration) => {
    if (!duration) return 'N/A';
    // Parse ISO 8601 duration or return as-is if already formatted
    if (duration.includes('PT')) {
      const match = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
      if (match) {
        const [, hours, minutes, seconds] = match;
        const parts = [];
        if (hours) parts.push(`${hours}h`);
        if (minutes) parts.push(`${minutes}m`);
        if (seconds) parts.push(`${seconds}s`);
        return parts.join(' ') || 'N/A';
      }
    }
    return duration;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="vibe-card mb-4">
      <div className="card-header-vibe">
        <h3 className="mb-0">
          <span className="emoji-icon">📺</span> {data.title || 'Video Analysis'}
        </h3>
      </div>
      <div className="card-body">
        <div className="row">
          <div className="col-lg-8 col-md-12 mb-4 mb-lg-0">
            {data.id ? (
              <div className="video-wrapper" style={{ position: 'relative', paddingBottom: '56.25%', height: 0, overflow: 'hidden', borderRadius: '12px' }}>
                <iframe
                  src={`https://www.youtube.com/embed/${data.id}`}
                  title={data.title || 'YouTube video'}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: 0
                  }}
                />
              </div>
            ) : (
              <div className="alert alert-warning">
                <i className="fas fa-exclamation-triangle"></i> Unable to load video player
              </div>
            )}
          </div>
          
          <div className="col-lg-4 col-md-12">
            <div className="video-metadata bg-light rounded p-3">
              <h5 className="mb-3">Video Information</h5>
              
              <div className="metadata-item mb-2 pb-2 border-bottom">
                <i className="fas fa-tv text-muted me-2"></i>
                <span className="metadata-label">Channel:</span>
                <span className="metadata-value fw-semibold">{data.channel || 'Unknown'}</span>
              </div>
              
              <div className="metadata-item mb-2 pb-2 border-bottom">
                <i className="fas fa-calendar text-muted me-2"></i>
                <span className="metadata-label">Published:</span>
                <span className="metadata-value">{formatDate(data.published)}</span>
              </div>
              
              <div className="metadata-item mb-2 pb-2 border-bottom">
                <i className="fas fa-clock text-muted me-2"></i>
                <span className="metadata-label">Duration:</span>
                <span className="metadata-value">{formatDuration(data.duration)}</span>
              </div>
              
              <div className="metadata-item mb-2 pb-2 border-bottom">
                <i className="fas fa-eye text-primary me-2"></i>
                <span className="metadata-label">Views:</span>
                <span className="metadata-value fw-bold text-primary">
                  {data.statistics?.views?.toLocaleString() || '0'}
                </span>
              </div>
              
              <div className="metadata-item mb-2 pb-2 border-bottom">
                <i className="fas fa-thumbs-up text-success me-2"></i>
                <span className="metadata-label">Likes:</span>
                <span className="metadata-value fw-bold text-success">
                  {data.statistics?.likes?.toLocaleString() || '0'}
                </span>
              </div>
              
              <div className="metadata-item mb-2">
                <i className="fas fa-comment text-info me-2"></i>
                <span className="metadata-label">Comments:</span>
                <span className="metadata-value fw-bold text-info">
                  {data.statistics?.comments?.toLocaleString() || '0'}
                </span>
              </div>

              {data.url && (
                <div className="mt-3">
                  <a 
                    href={data.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="btn btn-sm btn-outline-primary w-100"
                  >
                    <i className="fas fa-external-link-alt me-2"></i>
                    Watch on YouTube
                  </a>
                </div>
              )}
            </div>
            
            {/* Engagement Rate Card */}
            <div className="mt-3 p-3 bg-info bg-opacity-10 rounded">
              <h6 className="text-info mb-2">
                <i className="fas fa-chart-line me-2"></i>
                Engagement Rate
              </h6>
              <div className="h3 mb-0">
                {data.statistics?.views > 0 
                  ? ((data.statistics.likes / data.statistics.views) * 100).toFixed(2) 
                  : '0.00'}%
              </div>
              <small className="text-muted">Likes / Views</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

VideoInfo.propTypes = {
  data: PropTypes.shape({
    id: PropTypes.string,
    title: PropTypes.string,
    channel: PropTypes.string,
    published: PropTypes.string,
    duration: PropTypes.string,
    url: PropTypes.string,
    statistics: PropTypes.shape({
      views: PropTypes.number,
      likes: PropTypes.number,
      comments: PropTypes.number
    })
  })
};

export default VideoInfo;