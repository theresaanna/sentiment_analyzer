import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AnalysisProvider } from './contexts/AnalysisContext';
import { VideoInfo } from './components/Analysis/VideoInfo';
import { AnalysisControls } from './components/Analysis/AnalysisControls';
import { SentimentAnalysis } from './components/Analysis/SentimentAnalysis';
import { SampleComments } from './components/Analysis/SampleComments';
import { useToast } from './hooks/useToast';
import { api } from './services/api';
import './styles/analyze.css';

// Production-grade Analyze Application
export function AnalyzeApp() {
  const [isLoading, setIsLoading] = useState(true);
  const [videoData, setVideoData] = useState(null);
  const [analysisState, setAnalysisState] = useState('idle');
  const [analysisResults, setAnalysisResults] = useState(null);
  const [error, setError] = useState(null);
  
  const { showToast } = useToast();

  // Initialize from server-side data
  useEffect(() => {
    const initializeApp = () => {
      try {
        const rootEl = document.getElementById('react-analyze-root');
        if (!rootEl) {
          throw new Error('Root element not found');
        }

        // Parse all data attributes safely
        const parseAttribute = (name, defaultValue = null) => {
          try {
            const value = rootEl.getAttribute(name);
            return value ? JSON.parse(value) : defaultValue;
          } catch {
            return rootEl.getAttribute(name) || defaultValue;
          }
        };

        const videoData = {
          id: rootEl.getAttribute('data-video-id') || '',
          title: rootEl.getAttribute('data-video-title') || '',
          channel: rootEl.getAttribute('data-video-channel') || '',
          published: rootEl.getAttribute('data-video-published') || '',
          duration: rootEl.getAttribute('data-video-duration') || '',
          url: rootEl.getAttribute('data-video-url') || '',
          statistics: {
            views: parseInt(rootEl.getAttribute('data-video-views') || '0', 10),
            likes: parseInt(rootEl.getAttribute('data-video-likes') || '0', 10),
            comments: parseInt(rootEl.getAttribute('data-video-comments') || '0', 10),
          },
        };

        const appState = {
          isAuthenticated: rootEl.getAttribute('data-is-auth') === 'true',
          isProUser: rootEl.getAttribute('data-is-pro') === 'true',
          commentStats: parseAttribute('data-comment-stats', {}),
          precomputedResults: parseAttribute('data-precomputed-results'),
          updatedStats: parseAttribute('data-updated-stats'),
        };

        setVideoData(videoData);
        
        // Store app state in context or global state management
        window.__APP_STATE__ = appState;
        
        setIsLoading(false);
      } catch (error) {
        console.error('[AnalyzeApp] Initialization error:', error);
        setError(error.message);
        setIsLoading(false);
      }
    };

    initializeApp();
  }, []);

  const handleAnalysisStart = useCallback(async (config) => {
    try {
      setAnalysisState('loading');
      setError(null);
      
      const result = await api.startAnalysis(videoData.id, config);
      
      if (result.success) {
        setAnalysisState('analyzing');
        // Start polling for results
        pollAnalysisStatus(result.analysisId);
      } else {
        throw new Error(result.error || 'Failed to start analysis');
      }
    } catch (error) {
      console.error('Analysis error:', error);
      setError(error.message);
      setAnalysisState('error');
      showToast('Failed to start analysis', 'error');
    }
  }, [videoData, showToast]);

  const pollAnalysisStatus = useCallback(async (analysisId) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await api.getAnalysisStatus(analysisId);
        
        if (status.status === 'completed') {
          clearInterval(pollInterval);
          const results = await api.getAnalysisResults(analysisId);
          setAnalysisResults(results);
          setAnalysisState('completed');
        } else if (status.status === 'error') {
          clearInterval(pollInterval);
          throw new Error(status.error || 'Analysis failed');
        }
      } catch (error) {
        clearInterval(pollInterval);
        setError(error.message);
        setAnalysisState('error');
      }
    }, 1000);
  }, []);

  if (isLoading) {
    return (
      <div className="analyze-loading">
        <div className="spinner-border text-primary" role="status">
          <span className="sr-only">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analyze-error">
        <div className="alert alert-danger" role="alert">
          <h4 className="alert-heading">Error</h4>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>
            Reload Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <AnalysisProvider value={{ videoData, analysisState, analysisResults }}>
        <div className="analyze-app">
          <div className="container">
            {/* Video Information Card */}
            <VideoInfo data={videoData} />
            
            {/* Analysis Controls */}
            <AnalysisControls 
              onAnalyze={handleAnalysisStart}
              isLoading={analysisState === 'loading' || analysisState === 'analyzing'}
            />
            
            {/* Sentiment Analysis Section */}
            {analysisState !== 'idle' && (
              <SentimentAnalysis 
                state={analysisState}
                results={analysisResults}
              />
            )}
            
            {/* Sample Comments Section */}
            {analysisResults && (
              <SampleComments 
                comments={analysisResults.sentiment?.individual_results || []}
                videoId={videoData.id}
              />
            )}
          </div>
        </div>
      </AnalysisProvider>
    </ErrorBoundary>
  );
}

// Initialize the app
function initializeAnalyzeApp() {
  const rootElement = document.getElementById('react-analyze-root');
  if (rootElement) {
    const root = createRoot(rootElement);
    root.render(<AnalyzeApp />);
  } else {
    console.error('Could not find react-analyze-root element');
  }
}

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeAnalyzeApp);
} else {
  initializeAnalyzeApp();
}

export default AnalyzeApp;