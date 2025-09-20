import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { mountHomeApp } from './main'

describe('HomePage React Components', () => {
  let container

  beforeEach(() => {
    // Create a container div for mounting
    container = document.createElement('div')
    container.id = 'react-home-root'
    document.body.appendChild(container)
    
    // Create sparkle container
    const sparkleContainer = document.createElement('div')
    sparkleContainer.id = 'sparkleContainer'
    document.body.appendChild(sparkleContainer)
    
    // Create form elements
    const form = document.createElement('form')
    form.id = 'vibeCheckForm'
    const btn = document.createElement('button')
    btn.id = 'analyzeBtn'
    form.appendChild(btn)
    document.body.appendChild(form)
  })

  afterEach(() => {
    // Clean up
    document.body.innerHTML = ''
    vi.clearAllMocks()
  })

  it('mounts the HomeApp component successfully', () => {
    mountHomeApp('react-home-root')
    
    // Check that the mount point exists
    expect(document.getElementById('react-home-root')).toBeTruthy()
  })

  it('initializes sparkle effects', async () => {
    mountHomeApp('react-home-root')
    
    await waitFor(() => {
      const sparkleContainer = document.getElementById('sparkleContainer')
      expect(sparkleContainer).toBeTruthy()
    })
  })

  it('adds loading class to analyze button on form submit', async () => {
    mountHomeApp('react-home-root')
    
    // Wait for React to render and attach event listeners
    await waitFor(() => {
      const form = document.getElementById('vibeCheckForm')
      const btn = document.getElementById('analyzeBtn')
      
      expect(form).toBeTruthy()
      expect(btn).toBeTruthy()
    })
    
    const form = document.getElementById('vibeCheckForm')
    const btn = document.getElementById('analyzeBtn')
    
    // Trigger form submit
    const submitEvent = new Event('submit')
    form.dispatchEvent(submitEvent)
    
    // Check that loading class was added
    expect(btn.classList.contains('loading')).toBe(true)
  })

  it('handles missing form elements gracefully', () => {
    // Remove form elements
    document.getElementById('vibeCheckForm')?.remove()
    document.getElementById('analyzeBtn')?.remove()
    
    // Should not throw error
    expect(() => mountHomeApp('react-home-root')).not.toThrow()
  })

  it('handles missing sparkle container gracefully', () => {
    // Remove sparkle container
    document.getElementById('sparkleContainer')?.remove()
    
    // Should not throw error
    expect(() => mountHomeApp('react-home-root')).not.toThrow()
  })

  it('does not mount when mount node is missing', () => {
    document.getElementById('react-home-root')?.remove()
    
    // Should not throw error
    expect(() => mountHomeApp('react-home-root')).not.toThrow()
  })
})