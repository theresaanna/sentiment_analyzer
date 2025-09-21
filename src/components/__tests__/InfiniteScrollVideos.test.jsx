import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import InfiniteScrollVideos from '../InfiniteScrollVideos';
import VideoGrid from '../VideoGrid';
import useIntersectionObserver from '../../hooks/useIntersectionObserver';

// Mock the intersection observer hook
vi.mock('../../hooks/useIntersectionObserver');

// Mock fetch
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(() => 'mock-auth-token'),
  setItem: vi.fn(),
  clear: vi.fn()
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('InfiniteScrollVideos', () => {
  const mockChannelId = 'UCtest123';
  const mockOnVideoSelect = vi.fn();
  
  const mockVideosPage1 = [
    {
      video_id: 'video1',
      title: 'First Video',
      thumbnail: 'https://example.com/thumb1.jpg',
      duration: 'PT10M30S',
      views: 1500000,
      channel_title: 'Test Channel',
      published_at: '2024-01-15T10:00:00Z'
    },
    {
      video_id: 'video2',
      title: 'Second Video',
      thumbnail: 'https://example.com/thumb2.jpg',
      duration: 'PT5M15S',
      views: 500000,
      channel_title: 'Test Channel',
      published_at: '2024-01-14T10:00:00Z'
    }
  ];

  const mockVideosPage2 = [
    {
      video_id: 'video3',
      title: 'Third Video',
      thumbnail: 'https://example.com/thumb3.jpg',
      duration: 'PT15M00S',
      views: 2000000,
      channel_title: 'Test Channel',
      published_at: '2024-01-13T10:00:00Z'
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock the intersection observer hook to return a ref
    useIntersectionObserver.mockReturnValue({ current: null });
  });

  describe('Initial Load', () => {
    it('should render loading state initially', async () => {
      fetch.mockImplementationOnce(() => new Promise(() => {})); // Never resolves
      
      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      expect(screen.getByText('Your Videos')).toBeInTheDocument();
    });

    it('should load and display videos on mount', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          videos: mockVideosPage1,
          total: 10,
          has_more: true
        })
      });

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('First Video')).toBeInTheDocument();
        expect(screen.getByText('Second Video')).toBeInTheDocument();
      });

      expect(screen.getByText('2 of 10 videos loaded')).toBeInTheDocument();
    });

    it('should display error when API call fails', async () => {
      fetch.mockRejectedValueOnce(new Error('Network error'));

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    it('should retry loading when retry button is clicked', async () => {
      fetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: mockVideosPage1,
            total: 2,
            has_more: false
          })
        });

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Retry'));

      await waitFor(() => {
        expect(screen.getByText('First Video')).toBeInTheDocument();
        expect(screen.queryByText(/Network error/)).not.toBeInTheDocument();
      });
    });
  });

  describe('Infinite Scroll', () => {
    it('should load more videos when scrolling', async () => {
      let loadMoreCallback;
      useIntersectionObserver.mockImplementation((callback) => {
        loadMoreCallback = callback;
        return { current: null };
      });

      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: mockVideosPage1,
            total: 3,
            has_more: true
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: mockVideosPage2,
            total: 3,
            has_more: false
          })
        });

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('First Video')).toBeInTheDocument();
      });

      // Trigger loading more videos
      loadMoreCallback();

      await waitFor(() => {
        expect(screen.getByText('Third Video')).toBeInTheDocument();
        expect(screen.getByText('All 3 videos loaded')).toBeInTheDocument();
      });
    });

    it('should not load more when all videos are loaded', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          videos: mockVideosPage1,
          total: 2,
          has_more: false
        })
      });

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('All 2 videos loaded')).toBeInTheDocument();
      });

      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('should handle duplicate videos correctly', async () => {
      let loadMoreCallback;
      useIntersectionObserver.mockImplementation((callback) => {
        loadMoreCallback = callback;
        return { current: null };
      });

      const duplicateVideo = { ...mockVideosPage1[0], video_id: 'video1' };

      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: mockVideosPage1,
            total: 3,
            has_more: true
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: [duplicateVideo, mockVideosPage2[0]],
            total: 3,
            has_more: false
          })
        });

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('First Video')).toBeInTheDocument();
      });

      loadMoreCallback();

      await waitFor(() => {
        expect(screen.getByText('Third Video')).toBeInTheDocument();
      });

      // Should only have one instance of "First Video"
      const firstVideoElements = screen.getAllByText('First Video');
      expect(firstVideoElements).toHaveLength(1);
    });
  });

  describe('Load All Videos', () => {
    it('should load all videos when button is clicked', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: mockVideosPage1,
            total: 5,
            has_more: true
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: mockVideosPage2,
            total: 5,
            has_more: false
          })
        });

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Load All Videos')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Load All Videos'));

      await waitFor(() => {
        expect(screen.getByText('All 3 videos loaded')).toBeInTheDocument();
      });

      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('should disable load all button while loading', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: mockVideosPage1,
            total: 100,
            has_more: true
          })
        })
        .mockImplementationOnce(() => new Promise(() => {})); // Never resolves

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Load All Videos')).toBeInTheDocument();
      });

      const loadAllButton = screen.getByText('Load All Videos');
      fireEvent.click(loadAllButton);

      expect(loadAllButton).toBeDisabled();
    });
  });

  describe('Video Selection', () => {
    it('should call onVideoSelect when a video is clicked', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          videos: mockVideosPage1,
          total: 2,
          has_more: false
        })
      });

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('First Video')).toBeInTheDocument();
      });

      const firstVideoCard = screen.getByText('First Video').closest('.video-card');
      fireEvent.click(firstVideoCard);

      expect(mockOnVideoSelect).toHaveBeenCalledWith(mockVideosPage1[0]);
    });
  });

  describe('Channel Change', () => {
    it('should reload videos when channel ID changes', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: mockVideosPage1,
            total: 2,
            has_more: false
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            videos: [{
              ...mockVideosPage2[0],
              title: 'New Channel Video'
            }],
            total: 1,
            has_more: false
          })
        });

      const { rerender } = render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('First Video')).toBeInTheDocument();
      });

      rerender(
        <InfiniteScrollVideos 
          channelId="UCnewchannel"
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        expect(screen.queryByText('First Video')).not.toBeInTheDocument();
        expect(screen.getByText('New Channel Video')).toBeInTheDocument();
      });
    });
  });

  describe('Progress Indicator', () => {
    it('should display progress bar', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          videos: mockVideosPage1,
          total: 10,
          has_more: true
        })
      });

      render(
        <InfiniteScrollVideos 
          channelId={mockChannelId}
          onVideoSelect={mockOnVideoSelect}
        />
      );

      await waitFor(() => {
        const progressBar = document.querySelector('.progress-bar');
        expect(progressBar).toBeInTheDocument();
        expect(progressBar.style.width).toBe('20%'); // 2 of 10 videos
      });
    });
  });
});

describe('VideoGrid', () => {
  const mockVideos = [
    {
      video_id: 'video1',
      title: 'Test Video 1',
      thumbnail: 'https://example.com/thumb1.jpg',
      duration: 'PT10M30S',
      views: 1500000,
      channel_title: 'Test Channel',
      published_at: '2024-01-15T10:00:00Z',
      sentiment_data: {
        overall_sentiment: 'positive',
        comment_count: 150
      }
    },
    {
      video_id: 'video2',
      title: 'Test Video 2',
      duration: 'PT1H5M15S',
      views: 500,
      channel_title: 'Test Channel 2',
      published_at: new Date().toISOString()
    }
  ];

  const mockOnVideoClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render video cards', () => {
      render(
        <VideoGrid 
          videos={mockVideos}
          onVideoClick={mockOnVideoClick}
        />
      );

      expect(screen.getByText('Test Video 1')).toBeInTheDocument();
      expect(screen.getByText('Test Video 2')).toBeInTheDocument();
    });

    it('should format video duration correctly', () => {
      render(
        <VideoGrid 
          videos={mockVideos}
          onVideoClick={mockOnVideoClick}
        />
      );

      expect(screen.getByText('10:30')).toBeInTheDocument();
      expect(screen.getByText('1:05:15')).toBeInTheDocument();
    });

    it('should format view count correctly', () => {
      render(
        <VideoGrid 
          videos={mockVideos}
          onVideoClick={mockOnVideoClick}
        />
      );

      expect(screen.getByText('1.5M views')).toBeInTheDocument();
      expect(screen.getByText('500 views')).toBeInTheDocument();
    });

    it('should display sentiment data when available', () => {
      render(
        <VideoGrid 
          videos={mockVideos}
          onVideoClick={mockOnVideoClick}
        />
      );

      expect(screen.getByText('positive')).toBeInTheDocument();
      expect(screen.getByText('150 comments analyzed')).toBeInTheDocument();
    });

    it('should use default thumbnail when not provided', () => {
      const videoWithoutThumb = [{
        ...mockVideos[1],
        thumbnail: null
      }];

      render(
        <VideoGrid 
          videos={videoWithoutThumb}
          onVideoClick={mockOnVideoClick}
        />
      );

      const thumbnail = screen.getByAltText('Test Video 2');
      expect(thumbnail.src).toContain('i.ytimg.com/vi/video2/mqdefault.jpg');
    });
  });

  describe('Loading State', () => {
    it('should show loading skeletons', () => {
      render(
        <VideoGrid 
          videos={[]}
          onVideoClick={mockOnVideoClick}
          loading={true}
        />
      );

      const skeletons = document.querySelectorAll('.video-card-skeleton');
      expect(skeletons).toHaveLength(6);
    });
  });

  describe('Empty State', () => {
    it('should show empty message when no videos', () => {
      render(
        <VideoGrid 
          videos={[]}
          onVideoClick={mockOnVideoClick}
          loading={false}
        />
      );

      expect(screen.getByText('No videos found')).toBeInTheDocument();
      expect(screen.getByText('Videos from your channel will appear here')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error message', () => {
      render(
        <VideoGrid 
          videos={[]}
          onVideoClick={mockOnVideoClick}
          error="Failed to load videos"
        />
      );

      expect(screen.getByText('Error loading videos: Failed to load videos')).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should call onVideoClick when video is clicked', () => {
      render(
        <VideoGrid 
          videos={mockVideos}
          onVideoClick={mockOnVideoClick}
        />
      );

      const firstVideo = screen.getByText('Test Video 1').closest('.video-card');
      fireEvent.click(firstVideo);

      expect(mockOnVideoClick).toHaveBeenCalledWith(mockVideos[0]);
    });

    it('should handle keyboard navigation', () => {
      render(
        <VideoGrid 
          videos={mockVideos}
          onVideoClick={mockOnVideoClick}
        />
      );

      const firstVideo = screen.getByText('Test Video 1').closest('.video-card');
      fireEvent.keyPress(firstVideo, { key: 'Enter' });

      expect(mockOnVideoClick).toHaveBeenCalledWith(mockVideos[0]);
    });
  });
});