import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JobCard } from './JobCard';

describe('JobCard Component', () => {
  const mockJob = {
    job_id: 'job123',
    status: 'processing',
    progress: 45,
    video_id: 'video456',
    video_title: 'Test Video Title',
    job_type: 'preload',
    comment_count_requested: 500,
    created_at: '2024-01-01T10:00:00Z',
    video_metadata: {
      title: 'Test Video Title',
      description: 'This is a test video description',
      duration: 'PT10M30S',
      views: 1000000,
      likes: 50000,
      comments: 5000,
      channel_title: 'Test Channel',
      published_at: '2023-12-01T00:00:00Z',
      thumbnail: 'https://example.com/thumb.jpg'
    }
  };

  const mockHandlers = {
    onCancel: vi.fn(),
    onRetry: vi.fn(),
    onViewAnalysis: vi.fn(),
    onToggleExpand: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render job card with basic information', () => {
      render(<JobCard job={mockJob} {...mockHandlers} />);
      
      expect(screen.getByText('Test Video Title')).toBeInTheDocument();
      expect(screen.getByText('Test Channel')).toBeInTheDocument();
      expect(screen.getByText('PRELOAD')).toBeInTheDocument();
      expect(screen.getByText('PROCESSING')).toBeInTheDocument();
    });

    it('should display video thumbnail when available', () => {
      render(<JobCard job={mockJob} {...mockHandlers} />);
      
      const thumbnail = screen.getByAltText('Test Video Title');
      expect(thumbnail).toBeInTheDocument();
      expect(thumbnail).toHaveAttribute('src', 'https://example.com/thumb.jpg');
    });

    it('should show progress bar for active jobs', () => {
      render(<JobCard job={mockJob} {...mockHandlers} />);
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveStyle({ width: '45%' });
      expect(screen.getByText('45%')).toBeInTheDocument();
    });

    it('should format duration correctly', () => {
      render(<JobCard job={mockJob} {...mockHandlers} />);
      
      expect(screen.getByText('10m 30s')).toBeInTheDocument();
    });

    it('should format numbers with commas', () => {
      render(<JobCard job={mockJob} {...mockHandlers} expanded={true} />);
      
      expect(screen.getByText('1,000,000')).toBeInTheDocument(); // Views
      expect(screen.getByText('50,000')).toBeInTheDocument(); // Likes
      expect(screen.getByText('5,000')).toBeInTheDocument(); // Comments
    });
  });

  describe('Job Type Display', () => {
    it('should show correct icon and label for preload job', () => {
      render(<JobCard job={{ ...mockJob, job_type: 'preload' }} {...mockHandlers} />);
      
      expect(screen.getByText('PRELOAD')).toBeInTheDocument();
    });

    it('should show correct icon and label for analysis job', () => {
      render(<JobCard job={{ ...mockJob, job_type: 'analysis' }} {...mockHandlers} />);
      
      expect(screen.getByText('ANALYSIS')).toBeInTheDocument();
    });

    it('should show correct icon and label for channel sync job', () => {
      render(<JobCard job={{ ...mockJob, job_type: 'channel_sync' }} {...mockHandlers} />);
      
      expect(screen.getByText('CHANNEL SYNC')).toBeInTheDocument();
    });
  });

  describe('Status Display', () => {
    it('should display queued status correctly', () => {
      render(<JobCard job={{ ...mockJob, status: 'queued' }} {...mockHandlers} />);
      
      expect(screen.getByText('QUEUED')).toBeInTheDocument();
    });

    it('should display completed status correctly', () => {
      render(<JobCard job={{ ...mockJob, status: 'completed' }} {...mockHandlers} />);
      
      expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    });

    it('should display failed status correctly', () => {
      render(<JobCard job={{ ...mockJob, status: 'failed' }} {...mockHandlers} />);
      
      expect(screen.getByText('FAILED')).toBeInTheDocument();
    });
  });

  describe('Expanding/Collapsing', () => {
    it('should expand when header is clicked', () => {
      render(<JobCard job={mockJob} {...mockHandlers} />);
      
      const header = screen.getByTestId('job-card').querySelector('.job-card-header');
      fireEvent.click(header);
      
      expect(screen.getByText('Video Statistics')).toBeInTheDocument();
      expect(screen.getByText('Job Information')).toBeInTheDocument();
    });

    it('should call onToggleExpand when provided', () => {
      render(<JobCard job={mockJob} {...mockHandlers} />);
      
      const header = screen.getByTestId('job-card').querySelector('.job-card-header');
      fireEvent.click(header);
      
      expect(mockHandlers.onToggleExpand).toHaveBeenCalledWith('job123');
    });

    it('should respect expanded prop', () => {
      render(<JobCard job={mockJob} {...mockHandlers} expanded={true} />);
      
      expect(screen.getByText('Video Statistics')).toBeInTheDocument();
    });

    it('should show description when expanded and available', () => {
      render(<JobCard job={mockJob} {...mockHandlers} expanded={true} />);
      
      expect(screen.getByText('This is a test video description')).toBeInTheDocument();
    });
  });

  describe('Action Buttons', () => {
    it('should show cancel button for active jobs', () => {
      render(<JobCard job={{ ...mockJob, status: 'processing' }} {...mockHandlers} />);
      
      const header = screen.getByTestId('job-card').querySelector('.job-card-header');
      fireEvent.click(header);
      
      const cancelButton = screen.getByText('Cancel');
      expect(cancelButton).toBeInTheDocument();
      
      fireEvent.click(cancelButton);
      expect(mockHandlers.onCancel).toHaveBeenCalledWith('job123');
    });

    it('should show view analysis button for completed jobs', () => {
      render(
        <JobCard 
          job={{ ...mockJob, status: 'completed' }} 
          {...mockHandlers} 
          expanded={true}
        />
      );
      
      const viewButton = screen.getByText('View Analysis');
      expect(viewButton).toBeInTheDocument();
      
      fireEvent.click(viewButton);
      expect(mockHandlers.onViewAnalysis).toHaveBeenCalledWith('video456');
    });

    it('should show retry button for failed jobs', () => {
      render(
        <JobCard 
          job={{ ...mockJob, status: 'failed' }} 
          {...mockHandlers} 
          expanded={true}
        />
      );
      
      const retryButton = screen.getByText('Retry');
      expect(retryButton).toBeInTheDocument();
      
      fireEvent.click(retryButton);
      expect(mockHandlers.onRetry).toHaveBeenCalledWith('job123');
    });

    it('should show YouTube link when video_id is present', () => {
      render(<JobCard job={mockJob} {...mockHandlers} expanded={true} />);
      
      const youtubeLink = screen.getByText('View on YouTube');
      expect(youtubeLink).toBeInTheDocument();
      expect(youtubeLink.closest('a')).toHaveAttribute(
        'href', 
        'https://youtube.com/watch?v=video456'
      );
    });

    it('should not show actions when showActions is false', () => {
      render(
        <JobCard 
          job={mockJob} 
          {...mockHandlers} 
          expanded={true} 
          showActions={false}
        />
      );
      
      expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
      expect(screen.queryByText('View on YouTube')).not.toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should display error message for failed jobs', () => {
      const failedJob = {
        ...mockJob,
        status: 'failed',
        error_message: 'Failed to fetch video data'
      };
      
      render(<JobCard job={failedJob} {...mockHandlers} expanded={true} />);
      
      expect(screen.getByText('Failed to fetch video data')).toBeInTheDocument();
    });

    it('should handle missing metadata gracefully', () => {
      const jobWithoutMetadata = {
        ...mockJob,
        video_metadata: null
      };
      
      render(<JobCard job={jobWithoutMetadata} {...mockHandlers} />);
      
      expect(screen.getByText('Test Video Title')).toBeInTheDocument();
    });

    it('should handle missing thumbnail gracefully', () => {
      const jobWithoutThumb = {
        ...mockJob,
        video_metadata: { ...mockJob.video_metadata, thumbnail: null }
      };
      
      render(<JobCard job={jobWithoutThumb} {...mockHandlers} />);
      
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    });
  });

  describe('Date Formatting', () => {
    it('should format recent dates as relative time', () => {
      const recentJob = {
        ...mockJob,
        created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString() // 2 hours ago
      };
      
      render(<JobCard job={recentJob} {...mockHandlers} />);
      
      expect(screen.getByText('2h ago')).toBeInTheDocument();
    });

    it('should format old dates as absolute dates', () => {
      const oldJob = {
        ...mockJob,
        video_metadata: {
          ...mockJob.video_metadata,
          published_at: '2020-01-01T00:00:00Z'
        }
      };
      
      render(<JobCard job={oldJob} {...mockHandlers} />);
      
      expect(screen.getByText(/Jan 1, 2020/)).toBeInTheDocument();
    });
  });

  describe('Custom Styling', () => {
    it('should apply custom className', () => {
      render(<JobCard job={mockJob} {...mockHandlers} className="custom-class" />);
      
      const card = screen.getByTestId('job-card');
      expect(card).toHaveClass('custom-class');
    });

    it('should apply status-specific className', () => {
      render(<JobCard job={{ ...mockJob, status: 'failed' }} {...mockHandlers} />);
      
      const card = screen.getByTestId('job-card');
      expect(card).toHaveClass('status-failed');
    });

    it('should apply expanded className when expanded', () => {
      render(<JobCard job={mockJob} {...mockHandlers} expanded={true} />);
      
      const card = screen.getByTestId('job-card');
      expect(card).toHaveClass('expanded');
    });
  });
});