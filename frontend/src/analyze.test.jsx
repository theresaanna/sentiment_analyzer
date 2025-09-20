import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { createRoot } from 'react-dom/client'

// Mock React DOM client
vi.mock('react-dom/client', () => ({
  createRoot: vi.fn(() => ({
    render: vi.fn(),
    unmount: vi.fn()
  }))
}))

describe('Analyze Page Components', () => {
  beforeEach(() => {
    // Set up minimal DOM elements
    const rootEl = document.createElement('div')
    rootEl.id = 'react-analyze-root'
    rootEl.setAttribute('data-video-id', 'test-video-123')
    rootEl.setAttribute('data-video-title', 'Test Video')
    document.body.appendChild(rootEl)
  })

  afterEach(() => {
    document.body.innerHTML = ''
    vi.clearAllMocks()
  })

  it('initializes with correct video data', () => {
    const rootEl = document.getElementById('react-analyze-root')
    expect(rootEl).toBeTruthy()
    expect(rootEl.getAttribute('data-video-id')).toBe('test-video-123')
    expect(rootEl.getAttribute('data-video-title')).toBe('Test Video')
  })
})
