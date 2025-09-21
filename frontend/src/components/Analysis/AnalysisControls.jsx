import React, { useState, useCallback } from 'react';
import PropTypes from 'prop-types';

export function AnalysisControls({ onAnalyze, isLoading }) {
  const [config, setConfig] = useState({
    maxComments: 100,
    includeReplies: false,
    analysisMode: 'instant'
  });

  const isAuthenticated = window.__APP_STATE__?.isAuthenticated || false;
  const isProUser = window.__APP_STATE__?.isProUser || false;

  const getMaxLimit = () => {
    if (isProUser) return 5000;
    if (isAuthenticated) return 2500;
    return 500;
  };

  const handleSliderChange = (e) => {
    setConfig(prev => ({
      ...prev,
      maxComments: parseInt(e.target.value, 10)
    }));
  };

  const handleModeChange = (mode) => {
    setConfig(prev => ({
      ...prev,
      analysisMode: mode
    }));
  };

  const handleAnalyze = useCallback(() => {
    onAnalyze(config);
  }, [config, onAnalyze]);

  const maxLimit = getMaxLimit();
  const percentage = Math.round((config.maxComments / maxLimit) * 100);

  return (
    <div className="vibe-card mb-4">
      <div className="card-header-vibe">
        <h3 className="mb-0">
          <span className="emoji-icon">💬</span> Comment Analysis Settings
        </h3>
      </div>
      <div className="card-body">
        {/* Analysis Mode Selector */}
        <div className="mb-4">
          <label className="form-label fw-semibold">Analysis Mode</label>
          <div className="row g-3">
            <div className="col-md-4">
              <div 
                className={`card cursor-pointer ${config.analysisMode === 'instant' ? 'border-primary shadow-sm' : ''}`}
                onClick={() => handleModeChange('instant')}
                role="button"
                tabIndex={0}
              >
                <div className="card-body text-center">
                  <i className="fas fa-bolt fa-2x text-primary mb-2"></i>
                  <h6>Instant Analysis</h6>
                  <small className="text-muted">Quick results, up to {maxLimit} comments</small>
                </div>
              </div>
            </div>
            
            {isAuthenticated && (
              <div className="col-md-4">
                <div 
                  className={`card cursor-pointer ${config.analysisMode === 'queue' ? 'border-warning shadow-sm' : ''}`}
                  onClick={() => handleModeChange('queue')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="card-body text-center">
                    <i className="fas fa-clock fa-2x text-warning mb-2"></i>
                    <h6>Queue Analysis</h6>
                    <small className="text-muted">Background processing, up to 2,500 comments</small>
                  </div>
                </div>
              </div>
            )}
            
            {isProUser && (
              <div className="col-md-4">
                <div 
                  className={`card cursor-pointer ${config.analysisMode === 'deep' ? 'border-success shadow-sm' : ''}`}
                  onClick={() => handleModeChange('deep')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="card-body text-center">
                    <i className="fas fa-microscope fa-2x text-success mb-2"></i>
                    <h6>Deep Analysis</h6>
                    <small className="text-muted">Complete analysis, up to 5,000 comments</small>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Comment Coverage Slider */}
        <div className="mb-4">
          <label className="form-label fw-semibold">
            Comment Coverage: <span className="text-primary">{config.maxComments.toLocaleString()}</span> comments
            <span className="ms-2 badge bg-info">{percentage}%</span>
          </label>
          <input
            type="range"
            className="form-range"
            min="5"
            max={maxLimit}
            step="5"
            value={config.maxComments}
            onChange={handleSliderChange}
            disabled={isLoading}
          />
          <div className="d-flex justify-content-between text-muted small">
            <span>5 comments</span>
            <span>{Math.floor(maxLimit / 2).toLocaleString()} comments</span>
            <span>{maxLimit.toLocaleString()} comments</span>
          </div>
        </div>

        {/* Include Replies Toggle */}
        <div className="mb-4">
          <div className="form-check form-switch">
            <input
              className="form-check-input"
              type="checkbox"
              id="includeReplies"
              checked={config.includeReplies}
              onChange={(e) => setConfig(prev => ({ ...prev, includeReplies: e.target.checked }))}
              disabled={isLoading}
            />
            <label className="form-check-label" htmlFor="includeReplies">
              Include reply threads
              <small className="text-muted d-block">Analyze replies to top-level comments (may take longer)</small>
            </label>
          </div>
        </div>

        {/* Analysis Stats Preview */}
        <div className="alert alert-info mb-4">
          <h6 className="alert-heading">
            <i className="fas fa-info-circle me-2"></i>
            Analysis Preview
          </h6>
          <div className="row mt-3">
            <div className="col-6 col-md-3">
              <div className="text-center">
                <div className="h4 mb-0">{config.maxComments}</div>
                <small className="text-muted">Comments</small>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="text-center">
                <div className="h4 mb-0">~{Math.ceil(config.maxComments / 100)}</div>
                <small className="text-muted">Seconds</small>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="text-center">
                <div className="h4 mb-0">{percentage}%</div>
                <small className="text-muted">Coverage</small>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="text-center">
                <div className="h4 mb-0">
                  {config.analysisMode === 'instant' ? '⚡' : config.analysisMode === 'queue' ? '📋' : '🔬'}
                </div>
                <small className="text-muted">Mode</small>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="d-grid gap-2">
          <button 
            className="btn-primary-gradient"
            onClick={handleAnalyze}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                Analyzing...
              </>
            ) : (
              <>
                <i className="fas fa-brain me-2"></i>
                Start Sentiment Analysis
              </>
            )}
          </button>

          {!isAuthenticated && (
            <div className="text-center mt-3">
              <p className="text-muted mb-2">
                <i className="fas fa-lock me-2"></i>
                Want to analyze more comments?
              </p>
              <a href="/login" className="btn btn-outline-primary me-2">
                Sign In
              </a>
              <a href="/register" className="btn btn-link">
                Create Free Account
              </a>
            </div>
          )}

          {isAuthenticated && !isProUser && (
            <div className="text-center mt-3">
              <p className="text-muted mb-2">
                <i className="fas fa-crown me-2"></i>
                Upgrade to Pro for up to 5,000 comments
              </p>
              <a href="/subscribe" className="btn btn-warning">
                <i className="fas fa-rocket me-2"></i>
                Upgrade to Pro
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

AnalysisControls.propTypes = {
  onAnalyze: PropTypes.func.isRequired,
  isLoading: PropTypes.bool
};

AnalysisControls.defaultProps = {
  isLoading: false
};

export default AnalysisControls;