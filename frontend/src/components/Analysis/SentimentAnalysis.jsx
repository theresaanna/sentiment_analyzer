import React, { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import Chart from 'chart.js/auto';

export function SentimentAnalysis({ state, results }) {
  const pieChartRef = useRef(null);
  const timelineChartRef = useRef(null);
  const chartsRef = useRef({});

  useEffect(() => {
    if (results && results.sentiment) {
      renderCharts(results.sentiment);
    }
    
    return () => {
      // Cleanup charts on unmount
      Object.values(chartsRef.current).forEach(chart => chart?.destroy());
    };
  }, [results]);

  const renderCharts = (sentiment) => {
    // Destroy existing charts
    Object.values(chartsRef.current).forEach(chart => chart?.destroy());
    
    // Render Pie Chart
    if (pieChartRef.current) {
      const ctx = pieChartRef.current.getContext('2d');
      const distribution = sentiment.distribution || sentiment.sentiment_counts || {};
      
      chartsRef.current.pie = new Chart(ctx, {
        type: 'pie',
        data: {
          labels: ['Positive', 'Neutral', 'Negative'],
          datasets: [{
            data: [
              distribution.positive || 0,
              distribution.neutral || 0,
              distribution.negative || 0
            ],
            backgroundColor: [
              'rgba(16, 185, 129, 0.8)',
              'rgba(156, 163, 175, 0.8)',
              'rgba(239, 68, 68, 0.8)'
            ],
            borderColor: [
              'rgba(16, 185, 129, 1)',
              'rgba(156, 163, 175, 1)',
              'rgba(239, 68, 68, 1)'
            ],
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                padding: 15,
                font: { size: 12 }
              }
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = ((context.parsed / total) * 100).toFixed(1);
                  return `${context.label}: ${context.parsed} (${percentage}%)`;
                }
              }
            }
          }
        }
      });
    }

    // Render Timeline Chart
    if (timelineChartRef.current && sentiment.timeline?.length > 0) {
      const ctx = timelineChartRef.current.getContext('2d');
      const timeline = sentiment.timeline;
      
      chartsRef.current.timeline = new Chart(ctx, {
        type: 'line',
        data: {
          labels: timeline.map((_, i) => `Comment ${i + 1}`),
          datasets: [{
            label: 'Sentiment Score',
            data: timeline.map(item => {
              const scores = item.sentiment_scores || {};
              return scores.positive - scores.negative;
            }),
            borderColor: 'rgba(102, 126, 234, 1)',
            backgroundColor: 'rgba(102, 126, 234, 0.1)',
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              min: -1,
              max: 1,
              title: {
                display: true,
                text: 'Sentiment Score'
              }
            }
          },
          plugins: {
            legend: {
              display: false
            }
          }
        }
      });
    }
  };

  if (state === 'idle') {
    return null;
  }

  if (state === 'loading' || state === 'analyzing') {
    return (
      <div className="vibe-card mb-4">
        <div className="card-header-vibe">
          <h3 className="mb-0">
            <span className="emoji-icon">🧠</span> Sentiment Analysis
          </h3>
        </div>
        <div className="card-body">
          <div className="text-center py-5">
            <div className="vibe-spinner mb-4">
              <div className="spinner-border text-primary" role="status" style={{ width: '3rem', height: '3rem' }}>
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
            <h4 className="loading-status">
              {state === 'loading' ? 'Initializing analysis...' : 'Analyzing comments...'}
            </h4>
            <p className="loading-substatus text-muted">
              This may take a few moments depending on the number of comments
            </p>
            <div className="progress mt-4" style={{ height: '25px' }}>
              <div 
                className="progress-bar progress-bar-striped progress-bar-animated"
                role="progressbar"
                style={{ width: state === 'loading' ? '25%' : '75%' }}
                aria-valuenow={state === 'loading' ? 25 : 75}
                aria-valuemin="0"
                aria-valuemax="100"
              >
                {state === 'loading' ? '25%' : '75%'}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="vibe-card mb-4">
        <div className="card-header-vibe bg-danger">
          <h3 className="mb-0">
            <span className="emoji-icon">⚠️</span> Analysis Error
          </h3>
        </div>
        <div className="card-body">
          <div className="alert alert-danger">
            <h5 className="alert-heading">Unable to complete analysis</h5>
            <p>An error occurred while analyzing the comments. Please try again.</p>
            <button 
              className="btn btn-outline-danger"
              onClick={() => window.location.reload()}
            >
              <i className="fas fa-redo me-2"></i>
              Retry Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!results || !results.sentiment) {
    return null;
  }

  const { sentiment } = results;
  const totalAnalyzed = sentiment.total_analyzed || 0;
  const distribution = sentiment.distribution || sentiment.sentiment_counts || {};
  const confidence = sentiment.average_confidence || 0;
  
  // Calculate overall sentiment
  const total = (distribution.positive || 0) + (distribution.neutral || 0) + (distribution.negative || 0);
  let overallSentiment = 'Neutral';
  if (total > 0) {
    if (distribution.positive > distribution.negative && distribution.positive > distribution.neutral) {
      overallSentiment = 'Positive';
    } else if (distribution.negative > distribution.positive && distribution.negative > distribution.neutral) {
      overallSentiment = 'Negative';
    }
  }

  return (
    <div className="vibe-card mb-4">
      <div className="card-header-vibe">
        <h3 className="mb-0">
          <span className="emoji-icon">🧠</span> Sentiment Analysis Results
        </h3>
      </div>
      <div className="card-body">
        {/* Overall Sentiment */}
        <div className="alert alert-info mb-4">
          <h4 className="alert-heading">
            <i className="fas fa-chart-line me-2"></i>
            Overall Sentiment: <strong>{overallSentiment}</strong>
          </h4>
          <p className="mb-0">
            Analyzed {totalAnalyzed.toLocaleString()} comments with {(confidence * 100).toFixed(1)}% average confidence
          </p>
        </div>

        {/* Charts Row */}
        <div className="row mb-4">
          <div className="col-md-6">
            <div className="card">
              <div className="card-header">
                <h5 className="mb-0">
                  <i className="fas fa-chart-pie me-2"></i>
                  Sentiment Distribution
                </h5>
              </div>
              <div className="card-body">
                <div style={{ height: '300px', position: 'relative' }}>
                  <canvas ref={pieChartRef}></canvas>
                </div>
              </div>
            </div>
          </div>

          <div className="col-md-6">
            <div className="card">
              <div className="card-header">
                <h5 className="mb-0">
                  <i className="fas fa-chart-line me-2"></i>
                  Sentiment Timeline
                </h5>
              </div>
              <div className="card-body">
                <div style={{ height: '300px', position: 'relative' }}>
                  <canvas ref={timelineChartRef}></canvas>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="row g-3 mb-4">
          <div className="col-6 col-md-3">
            <div className="stat-card text-center p-3 bg-light rounded">
              <div className="stat-icon text-success mb-2">
                <i className="fas fa-smile fa-2x"></i>
              </div>
              <div className="stat-value h4 mb-0">
                {distribution.positive || 0}
              </div>
              <div className="stat-label text-muted small">Positive</div>
            </div>
          </div>
          <div className="col-6 col-md-3">
            <div className="stat-card text-center p-3 bg-light rounded">
              <div className="stat-icon text-secondary mb-2">
                <i className="fas fa-meh fa-2x"></i>
              </div>
              <div className="stat-value h4 mb-0">
                {distribution.neutral || 0}
              </div>
              <div className="stat-label text-muted small">Neutral</div>
            </div>
          </div>
          <div className="col-6 col-md-3">
            <div className="stat-card text-center p-3 bg-light rounded">
              <div className="stat-icon text-danger mb-2">
                <i className="fas fa-frown fa-2x"></i>
              </div>
              <div className="stat-value h4 mb-0">
                {distribution.negative || 0}
              </div>
              <div className="stat-label text-muted small">Negative</div>
            </div>
          </div>
          <div className="col-6 col-md-3">
            <div className="stat-card text-center p-3 bg-light rounded">
              <div className="stat-icon text-info mb-2">
                <i className="fas fa-percentage fa-2x"></i>
              </div>
              <div className="stat-value h4 mb-0">
                {(confidence * 100).toFixed(1)}%
              </div>
              <div className="stat-label text-muted small">Confidence</div>
            </div>
          </div>
        </div>

        {/* AI Summary */}
        {results.summary && (
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">
                <i className="fas fa-robot me-2"></i>
                AI Analysis Summary
              </h5>
            </div>
            <div className="card-body">
              <div className="lead">
                {results.summary.summary || 'Summary is being generated...'}
              </div>
              {results.summary.themes && results.summary.themes.length > 0 && (
                <div className="mt-3">
                  <h6>Key Themes:</h6>
                  <div className="d-flex flex-wrap gap-2">
                    {results.summary.themes.map((theme, idx) => (
                      <span key={idx} className="badge bg-primary">
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

SentimentAnalysis.propTypes = {
  state: PropTypes.oneOf(['idle', 'loading', 'analyzing', 'completed', 'error']).isRequired,
  results: PropTypes.shape({
    sentiment: PropTypes.shape({
      total_analyzed: PropTypes.number,
      distribution: PropTypes.object,
      sentiment_counts: PropTypes.object,
      average_confidence: PropTypes.number,
      timeline: PropTypes.array,
      individual_results: PropTypes.array
    }),
    summary: PropTypes.shape({
      summary: PropTypes.string,
      themes: PropTypes.arrayOf(PropTypes.string)
    })
  })
};

export default SentimentAnalysis;