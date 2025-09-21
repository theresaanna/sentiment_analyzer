import React, { useState, useEffect, useCallback, useRef } from 'react';
import PropTypes from 'prop-types';
import VideoGrid from './VideoGrid';
import useIntersectionObserver from '../hooks/useIntersectionObserver';
import './InfiniteScrollVideos.css';

/**
 * InfiniteScrollVideos Component
 * Displays user's YouTube channel videos with infinite scroll
 * Automatically loads more videos as user scrolls down
 */
const InfiniteScrollVideos = ({ 
  channelId, 
  onVideoSelect,
  initialPageSize = 20,
  scrollThreshold = 0.8 
}) => {
  // State management
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [totalVideos, setTotalVideos] = useState(null);
  
  // Refs for preventing duplicate calls
  const isLoadingRef = useRef(false);
  const lastLoadedPageRef = useRef(0);
  const abortControllerRef = useRef(null);

  /**
   * Load videos from API
   */
  const loadVideos = useCallback(async (pageNumber, isInitial = false) => {
    // Prevent duplicate calls
    if (isLoadingRef.current || (!hasMore && !isInitial)) {
      return;
    }

    // Check if this page was already loaded
    if (pageNumber <= lastLoadedPageRef.current && !isInitial) {
      return;
    }

    isLoadingRef.current = true;
    
    // Cancel any pending requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Create new abort controller
    abortControllerRef.current = new AbortController();
    
    try {
      if (isInitial) {
        setLoading(true);
        setError(null);
      } else {
        setLoadingMore(true);
      }

      // API call to fetch videos
      const response = await fetch(
        `/api/channel/${channelId}/videos?page=${pageNumber}&limit=${initialPageSize}`,
        {
          signal: abortControllerRef.current.signal,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to load videos: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success) {
        const newVideos = data.videos || [];
        
        // Update state
        if (isInitial) {
          setVideos(newVideos);
        } else {
          setVideos(prev => {
            // Filter out duplicates
            const existingIds = new Set(prev.map(v => v.video_id));
            const uniqueNewVideos = newVideos.filter(v => !existingIds.has(v.video_id));
            return [...prev, ...uniqueNewVideos];
          });
        }
        
        // Update pagination info
        setTotalVideos(data.total || null);
        setHasMore(data.has_more !== false && newVideos.length === initialPageSize);
        lastLoadedPageRef.current = pageNumber;
        
        // Update page number for next load
        if (!isInitial) {
          setPage(pageNumber + 1);
        }
      } else {
        throw new Error(data.error || 'Failed to load videos');
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        // Request was aborted, ignore
        return;
      }
      
      console.error('Error loading videos:', err);
      setError(err.message);
      setHasMore(false);
    } finally {
      isLoadingRef.current = false;
      setLoading(false);
      setLoadingMore(false);
    }
  }, [channelId, initialPageSize, hasMore]);

  /**
   * Load more videos when scrolling
   */
  const loadMore = useCallback(() => {
    if (!loading && !loadingMore && hasMore && !isLoadingRef.current) {
      loadVideos(page, false);
    }
  }, [loading, loadingMore, hasMore, page, loadVideos]);

  /**
   * Setup intersection observer for infinite scroll
   */
  const sentinelRef = useIntersectionObserver(loadMore, {
    root: null,
    rootMargin: '200px',
    threshold: 0.1
  });

  /**
   * Initial load
   */
  useEffect(() => {
    setVideos([]);
    setPage(1);
    setHasMore(true);
    lastLoadedPageRef.current = 0;
    loadVideos(1, true);

    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [channelId]); // Only reload when channel changes

  /**
   * Handle video selection
   */
  const handleVideoClick = useCallback((video) => {
    if (onVideoSelect) {
      onVideoSelect(video);
    }
  }, [onVideoSelect]);

  /**
   * Retry loading after error
   */
  const handleRetry = useCallback(() => {
    setError(null);
    loadVideos(1, true);
  }, [loadVideos]);

  /**
   * Load all remaining videos
   */
  const loadAllVideos = useCallback(async () => {
    if (!hasMore || isLoadingRef.current) return;
    
    setLoadingMore(true);
    let currentPage = page;
    let allLoaded = false;
    
    while (!allLoaded && currentPage <= 100) { // Safety limit
      try {
        const response = await fetch(
          `/api/channel/${channelId}/videos?page=${currentPage}&limit=50`, // Larger batch for load all
          {
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
            }
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to load videos: ${response.statusText}`);
        }

        const data = await response.json();
        
        if (data.success) {
          const newVideos = data.videos || [];
          
          setVideos(prev => {
            const existingIds = new Set(prev.map(v => v.video_id));
            const uniqueNewVideos = newVideos.filter(v => !existingIds.has(v.video_id));
            return [...prev, ...uniqueNewVideos];
          });
          
          if (data.has_more === false || newVideos.length < 50) {
            allLoaded = true;
            setHasMore(false);
          }
          
          currentPage++;
        } else {
          throw new Error(data.error || 'Failed to load videos');
        }
      } catch (err) {
        console.error('Error loading all videos:', err);
        setError(err.message);
        break;
      }
    }
    
    setLoadingMore(false);
    setPage(currentPage);
  }, [channelId, hasMore, page]);

  return (
    <div className="infinite-scroll-videos">
      <div className="videos-header">
        <h2 className="videos-title">Your Videos</h2>
        {totalVideos !== null && (
          <span className="videos-count">
            {videos.length} of {totalVideos} videos loaded
          </span>
        )}
        {hasMore && videos.length > 0 && (
          <button 
            className="load-all-button"
            onClick={loadAllVideos}
            disabled={loadingMore}
          >
            Load All Videos
          </button>
        )}
      </div>

      {error && !loading && (
        <div className="videos-error">
          <p>{error}</p>
          <button onClick={handleRetry} className="retry-button">
            Retry
          </button>
        </div>
      )}

      <VideoGrid
        videos={videos}
        onVideoClick={handleVideoClick}
        loading={loading}
        error={!loading ? error : null}
      />

      {/* Sentinel element for infinite scroll */}
      {hasMore && !error && (
        <div 
          ref={sentinelRef} 
          className="scroll-sentinel"
          aria-label="Loading more videos"
        >
          {loadingMore && (
            <div className="loading-more">
              <div className="spinner"></div>
              <span>Loading more videos...</span>
            </div>
          )}
        </div>
      )}

      {!hasMore && videos.length > 0 && (
        <div className="end-of-list">
          <span>All {videos.length} videos loaded</span>
        </div>
      )}

      {/* Progress indicator */}
      {videos.length > 0 && (
        <div className="scroll-progress">
          <div 
            className="progress-bar"
            style={{ 
              width: `${Math.min((videos.length / (totalVideos || videos.length)) * 100, 100)}%` 
            }}
          />
        </div>
      )}
    </div>
  );
};

InfiniteScrollVideos.propTypes = {
  channelId: PropTypes.string.isRequired,
  onVideoSelect: PropTypes.func,
  initialPageSize: PropTypes.number,
  scrollThreshold: PropTypes.number
};

InfiniteScrollVideos.defaultProps = {
  onVideoSelect: null,
  initialPageSize: 20,
  scrollThreshold: 0.8
};

export default InfiniteScrollVideos;