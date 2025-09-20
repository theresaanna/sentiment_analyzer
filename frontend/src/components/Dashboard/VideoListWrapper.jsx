import React, { useState, useEffect } from 'react';
import { VideoList } from './VideoList';
import { ToastProvider } from '../Toast/ToastContext';

/**
 * Stateful wrapper for VideoList that manages fetching and state
 * This matches what the tests expect
 */
export const VideoListWrapper = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    fetchVideos();
  }, [filter, currentPage]);

  const fetchVideos = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);
      params.append('page', currentPage);
      params.append('limit', 10);
      
      const response = await fetch(`/api/videos?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch videos');
      }
      
      const data = await response.json();
      setVideos(data.videos || []);
      setTotalPages(data.totalPages || 1);
    } catch (err) {
      setError(err.message);
      setVideos([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  if (loading) {
    return (
      <div className="video-list-container">
        <div className="text-center py-3">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading videos...</span>
          </div>
          <p className="mt-2">Loading videos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-list-container">
        <div className="alert alert-danger">
          <i className="fas fa-exclamation-triangle"></i> Failed to load videos
          <button 
            className="btn btn-sm btn-outline-danger ms-3"
            onClick={fetchVideos}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const filteredVideos = filter === 'all' 
    ? videos 
    : videos.filter(video => video.status === filter);

  return (
    <div className="video-list-container">
      <div className="mb-3">
        <select 
          className="form-select" 
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setCurrentPage(1); // Reset to first page on filter change
          }}
        >
          <option value="all">All Videos</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      
      <button 
        className="btn btn-sm btn-primary mb-3"
        onClick={fetchVideos}
      >
        Refresh
      </button>

      <ToastProvider>
        <VideoList 
          videos={filteredVideos}
          isLoading={false}
        />
      </ToastProvider>
      
      {/* Pagination */}
      {totalPages > 1 && (
        <nav>
          <ul className="pagination">
            <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
              <button 
                className="page-link"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </button>
            </li>
            {[...Array(totalPages)].map((_, i) => (
              <li key={i + 1} className={`page-item ${currentPage === i + 1 ? 'active' : ''}`}>
                <button 
                  className="page-link"
                  onClick={() => handlePageChange(i + 1)}
                >
                  {i + 1}
                </button>
              </li>
            ))}
            <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
              <button 
                className="page-link"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
            </li>
          </ul>
        </nav>
      )}
    </div>
  );
};

// Export both the wrapper and the original for backwards compatibility  
export { VideoList } from './VideoList';