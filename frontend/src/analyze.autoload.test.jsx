import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { createRoot } from 'react-dom/client';
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock fetch globally
global.fetch = vi.fn();

// Mock window.location
delete window.location;
window.location = { 
  search: '',
  pathname: '/analyze/test-video',
  hash: '',
  replaceState: vi.fn()
};

// Mock window.history
window.history = {
  replaceState: vi.fn()
};

describe('Analyze Page Auto-Load Feature', () => {
  let container;
  let root;

  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks();
    fetch.mockClear();
    
    // Create a container for the React app
    container = document.createElement('div');
    container.setAttribute('id', 'react-analyze-root');
    container.setAttribute('data-video-id', 'test-video');
    container.setAttribute('data-is-auth', 'true');
    container.setAttribute('data-is-pro', 'true');
    container.setAttribute('data-video-comments', '1000');
    document.body.appendChild(container);

    // Create sections that the app expects
    const sentimentSection = document.createElement('div');
    sentimentSection.setAttribute('id', 'sentimentAnalysisSection');
    document.body.appendChild(sentimentSection);

    const progressDiv = document.createElement('div');
    progressDiv.setAttribute('id', 'analysisProgress');
    document.body.appendChild(progressDiv);

    const resultsDiv = document.createElement('div');
    resultsDiv.setAttribute('id', 'analysisResults');
    document.body.appendChild(resultsDiv);

    const samplesSection = document.createElement('div');
    samplesSection.setAttribute('id', 'sampleCommentsSection');
    document.body.appendChild(samplesSection);
  });

  afterEach(() => {
    // Clean up
    document.body.innerHTML = '';
    window.location.search = '';
  });

  test('should auto-load results when auto_load=true and from_job parameters are present', async () => {
    // Set URL parameters
    window.location.search = '?auto_load=true&from_job=job_123';
    
    // Mock the API response
    const mockResults = {
      success: true,
      results: {
        sentiment_analysis: {
          overall_sentiment: 'positive',
          distribution: { positive: 60, neutral: 30, negative: 10 },
          average_confidence: 0.85,
          individual_results: [
            { text: 'Great video!', predicted_sentiment: 'positive', confidence: 0.9 },
            { text: 'Not bad', predicted_sentiment: 'neutral', confidence: 0.7 }
          ]
        },
        summary: 'This is a test summary',
        comment_stats: {
          total_analyzed: 100,
          unique_commenters: 50
        }
      }
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResults
    });

    // Import and execute the analyze app
    const AnalyzeApp = require('./analyze.jsx').default;
    
    // Check that fetch was called with the correct endpoint
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/analyze/job/job_123/results');
    });

    // Check that sections are displayed correctly
    await waitFor(() => {
      const sentimentSection = document.getElementById('sentimentAnalysisSection');
      expect(sentimentSection.style.display).toBe('block');
      
      const progressDiv = document.getElementById('analysisProgress');
      expect(progressDiv.style.display).toBe('none');
      
      const resultsDiv = document.getElementById('analysisResults');
      expect(resultsDiv.style.display).toBe('block');
    });

    // Check that URL was cleaned up
    expect(window.history.replaceState).toHaveBeenCalledWith(
      {}, 
      '', 
      '/analyze/test-video'
    );
  });

  test('should not auto-load when auto_load parameter is missing', async () => {
    // Set URL parameters without auto_load
    window.location.search = '?from_job=job_123';
    
    // Import and execute the analyze app
    const AnalyzeApp = require('./analyze.jsx').default;
    
    // Wait a bit to ensure no fetch is called
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Check that fetch was NOT called
    expect(fetch).not.toHaveBeenCalled();
  });

  test('should not auto-load when from_job parameter is missing', async () => {
    // Set URL parameters without from_job
    window.location.search = '?auto_load=true';
    
    // Import and execute the analyze app
    const AnalyzeApp = require('./analyze.jsx').default;
    
    // Wait a bit to ensure no fetch is called
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Check that fetch was NOT called
    expect(fetch).not.toHaveBeenCalled();
  });

  test('should handle API errors gracefully', async () => {
    // Set URL parameters
    window.location.search = '?auto_load=true&from_job=job_123';
    
    // Mock console.error to suppress error logs in test
    const originalError = console.error;
    console.error = vi.fn();
    
    // Mock the API to return an error
    fetch.mockRejectedValueOnce(new Error('API Error'));
    
    // Import and execute the analyze app
    const AnalyzeApp = require('./analyze.jsx').default;
    
    // Check that fetch was called
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/analyze/job/job_123/results');
    });
    
    // Check that error was logged
    await waitFor(() => {
      expect(console.error).toHaveBeenCalledWith(
        '[AnalyzeApp] Failed to auto-load job results:',
        expect.any(Error)
      );
    });
    
    // Restore console.error
    console.error = originalError;
  });

  test('should use precomputed results when available and no auto-load params', async () => {
    // No URL parameters
    window.location.search = '';
    
    // Set precomputed results
    container.setAttribute('data-precomputed-results', JSON.stringify({
      overall_sentiment: 'positive',
      distribution: { positive: 70, neutral: 20, negative: 10 },
      average_confidence: 0.9,
      individual_results: []
    }));
    
    // Import and execute the analyze app
    const AnalyzeApp = require('./analyze.jsx').default;
    
    // Wait a bit
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Check that fetch was NOT called (using precomputed results)
    expect(fetch).not.toHaveBeenCalled();
    
    // Check that results section is displayed
    const resultsDiv = document.getElementById('analysisResults');
    expect(resultsDiv.style.display).toBe('block');
  });
});