import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VideoList } from './VideoList'
import { ToastProvider } from '../Toast/ToastContext'
import { JobStatusProvider } from '../../contexts/JobStatusContext'

describe('VideoList Component - Props Tests', () => {
  const mockVideos = [
    {
      id: 1,
      video_id: 'abc123',
      title: 'Amazing Video',
      channel_title: 'Test Channel',
      published_at: '2024-01-15T10:00:00Z',
      view_count: 10000,
      like_count: 500,
      comment_count: 100,
      thumbnail_url: 'https://example.com/thumb1.jpg',
      saved: true
    },
    {
      id: 2,
      video_id: 'def456',
      title: 'Another Great Video',
      channel_title: 'Another Channel',
      published_at: '2024-01-10T15:00:00Z',
      view_count: 5000,
      like_count: 200,
      comment_count: 50,
      thumbnail_url: 'https://example.com/thumb2.jpg',
      saved: false
    }
  ]

  it('renders empty state when no videos provided', () => {
    render(
      <JobStatusProvider>
        <ToastProvider>
          <VideoList videos={[]} isLoading={false} />
        </ToastProvider>
      </JobStatusProvider>
    )
    expect(screen.getByText(/No videos found/i)).toBeInTheDocument()
  })

  it('renders loading state when isLoading is true', () => {
    render(
      <JobStatusProvider>
        <ToastProvider>
          <VideoList videos={[]} isLoading={true} />
        </ToastProvider>
      </JobStatusProvider>
    )
    const loadingElements = screen.getAllByText(/Loading.../i)
    expect(loadingElements.length).toBeGreaterThan(0)
  })

  it('renders videos list when videos provided', () => {
    render(
      <JobStatusProvider>
        <ToastProvider>
          <VideoList videos={mockVideos} isLoading={false} />
        </ToastProvider>
      </JobStatusProvider>
    )
    expect(screen.getByText('Amazing Video')).toBeInTheDocument()
    expect(screen.getByText('Another Great Video')).toBeInTheDocument()
    // The component shows video.id (numeric) as code elements
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows preload button for videos', () => {
    render(
      <JobStatusProvider>
        <ToastProvider>
          <VideoList videos={[mockVideos[0]]} isLoading={false} />
        </ToastProvider>
      </JobStatusProvider>
    )
    expect(screen.getByText('Preload')).toBeInTheDocument()
  })

  it('displays video statistics correctly', () => {
    const testVideos = [{
      ...mockVideos[0],
      statistics: {
        views: 10000,
        comments: 100
      }
    }]
    render(
      <JobStatusProvider>
        <ToastProvider>
          <VideoList videos={testVideos} isLoading={false} />
        </ToastProvider>
      </JobStatusProvider>
    )
    expect(screen.getByText(/10,000 views/i)).toBeInTheDocument()
    expect(screen.getByText(/100 comments/i)).toBeInTheDocument()
  })

  it('shows video links for each video', () => {
    render(
      <JobStatusProvider>
        <ToastProvider>
          <VideoList videos={mockVideos} isLoading={false} />
        </ToastProvider>
      </JobStatusProvider>
    )
    // The component creates links with the video titles
    const videoLinks = screen.getAllByRole('link')
    expect(videoLinks).toHaveLength(2)
    expect(videoLinks[0]).toHaveAttribute('href', '/analyze/1')
    expect(videoLinks[1]).toHaveAttribute('href', '/analyze/2')
  })
})