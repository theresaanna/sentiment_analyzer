import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { JobsList } from './JobsList'

describe('JobsList Component - Props Tests', () => {
  const mockJobs = [
    {
      job_id: 'job-1',
      id: 'job-1',
      status: 'completed',
      video_id: 'vid-1',
      video_metadata: {
        title: 'Test Video 1',
        views: 1000,
        comments: 100,
        published: '2024-01-01T10:00:00Z'
      },
      created_at: '2024-01-01T10:00:00Z',
      completed_at: '2024-01-01T10:05:00Z'
    },
    {
      job_id: 'job-2',
      id: 'job-2',
      status: 'processing',
      video_id: 'vid-2',
      video_metadata: {
        title: 'Test Video 2',
        views: 500,
        comments: 50,
        published: '2024-01-01T11:00:00Z'
      },
      progress: 25,
      created_at: '2024-01-01T11:00:00Z',
      completed_at: null
    }
  ]

  it('renders empty state when no jobs provided', () => {
    render(<JobsList jobs={[]} isLoading={false} onCancelJob={vi.fn()} />)
    expect(screen.getByText(/No active jobs/i)).toBeInTheDocument()
  })

  it('renders loading state when isLoading is true', () => {
    render(<JobsList jobs={[]} isLoading={true} onCancelJob={vi.fn()} />)
    const loadingElements = screen.getAllByText(/Loading.../i)
    expect(loadingElements.length).toBeGreaterThan(0)
  })

  it('renders jobs list when jobs provided', () => {
    render(<JobsList jobs={mockJobs} isLoading={false} onCancelJob={vi.fn()} />)
    // The component shows "View Analysis" for completed jobs and shows the title for processing jobs
    expect(screen.getByText(/View Analysis/i)).toBeInTheDocument()
    expect(screen.getByText(/Test Video 2/i)).toBeInTheDocument()
  })

  it('shows completed status correctly', () => {
    render(<JobsList jobs={[mockJobs[0]]} isLoading={false} onCancelJob={vi.fn()} />)
    expect(screen.getByText(/completed/i)).toBeInTheDocument()
  })

  it('shows processing status with progress', () => {
    render(<JobsList jobs={[mockJobs[1]]} isLoading={false} onCancelJob={vi.fn()} />)
    expect(screen.getByText(/processing/i)).toBeInTheDocument()
    expect(screen.getByText(/25/)).toBeInTheDocument()
  })
})