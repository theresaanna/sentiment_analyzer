import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

// Analyze page script ported from inline JS to a React-managed module
// This file intentionally manipulates the DOM directly to work with existing Jinja markup.

// --- Safety & diagnostics helpers ---
function escapeHtml(str) {
  try {
    return String(str).replace(/[&<>"']/g, (s) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[s]));
  } catch {
    return String(str);
  }
}

function showFatalError(message, error) {
  try {
    // Log for developers
    // eslint-disable-next-line no-console
    console.error('[Analyze Fatal]', message, error);
    const container = document.querySelector('.analyze-page .container') || document.body;
    const box = document.createElement('div');
    box.className = 'vibe-card';
    box.style.marginTop = '20px';
    const details = error ? escapeHtml(error.stack || error.message || String(error)) : '';
    box.innerHTML = `
      <div class="card-header-vibe">
        <h3 class="mb-0"><span class="emoji-icon">⚠️</span> Analyze UI Error</h3>
      </div>
      <div class="card-body">
        <div class="alert alert-danger"><strong>${escapeHtml(message)}</strong></div>
        ${details ? `<pre style="white-space:pre-wrap; background:#f8f9fa; padding:12px; border-radius:8px;">${details}</pre>` : ''}
      </div>
    `;
    container.insertBefore(box, container.firstChild);
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('Failed to render fatal error box', e);
  }
}

// Global runtime guards
if (typeof window !== 'undefined') {
  // Only register once
  if (!window.__ANALYZE_ERROR_GUARDS__) {
    window.__ANALYZE_ERROR_GUARDS__ = true;
    window.addEventListener('error', (e) => {
      try { showFatalError('A runtime error occurred on the Analyze page.', e?.error || e?.message); } catch {}
    });
    window.addEventListener('unhandledrejection', (e) => {
      try { showFatalError('An async error occurred on the Analyze page.', e?.reason); } catch {}
    });
  }
}

function AnalyzeApp() {
  useEffect(() => {
  // Safe scrollIntoView wrapper that works in jsdom
  function safeScrollIntoView(element) {
    if (!element) return;
    if (typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      // Fallback for jsdom - just ensure element is visible
      element.style.display = 'block';
      if (typeof window !== 'undefined' && window.scrollTo) {
        window.scrollTo(0, element.offsetTop || 0);
      }
    }
  }

  try {
    console.log('[AnalyzeApp] Starting initialization for comment analysis...');
    if (!rootEl) { showFatalError('React analyze root element is missing.'); return; }

    // Parse server-provided context from data attributes
    const videoId = rootEl.getAttribute('data-video-id') || '';
    const isAuthenticated = (rootEl.getAttribute('data-is-auth') || 'false') === 'true';
    const isProUser = (rootEl.getAttribute('data-is-pro') || 'false') === 'true';
    const videoStatsComments = parseInt(rootEl.getAttribute('data-video-comments') || '0', 10) || 0;
    const videoViews = parseInt(rootEl.getAttribute('data-video-views') || '0', 10) || 0;
    const videoLikes = parseInt(rootEl.getAttribute('data-video-likes') || '0', 10) || 0;
    const videoTitle = rootEl.getAttribute('data-video-title') || '';
    const videoChannel = rootEl.getAttribute('data-video-channel') || '';
    const videoPublished = rootEl.getAttribute('data-video-published') || '';
    const videoDuration = rootEl.getAttribute('data-video-duration') || '';
    const videoUrl = rootEl.getAttribute('data-video-url') || '';

    let commentStats;
    try { commentStats = JSON.parse(rootEl.getAttribute('data-comment-stats') || '{}'); } catch { commentStats = {}; }
    let precomputedResults;
    try { precomputedResults = JSON.parse(rootEl.getAttribute('data-precomputed-results') || 'null'); } catch { precomputedResults = null; }
    let updatedStats;
    try { updatedStats = JSON.parse(rootEl.getAttribute('data-updated-stats') || 'null'); } catch { updatedStats = null; }

    // Globals (scoped to this module) that used to be inline
    let analysisId = null;
    let statusCheckInterval = null;
    let charts = {};
    let currentAnalysisMode = 'instant';
    let commentData = { positive: [], neutral: [], negative: [] };
    let analysisStartTs = null;

    // Loading message rotation state
    let messageRotationInterval = null;
    let currentMessageIndex = 0;
    let factRotationInterval = null;
    let currentFactIndex = 0;
    let lastProgressValue = 0;
    let targetProgress = 0;
    let progressAnimationFrame = null;

    // Function to handle analyze button click
    function handleAnalyzeClick() {
      // Show the sentiment analysis section
      const sentimentSection = document.getElementById('sentimentAnalysisSection');
      if (sentimentSection) {
        sentimentSection.style.display = 'block';
        
        // Smooth scroll to the section
        setTimeout(() => {
          safeScrollIntoView(sentimentSection);
        }, 100);
        
        // Start the analysis after a brief delay for visual effect
        setTimeout(() => {
          startSentimentAnalysis();
        }, 500);
      }
    }
    
    // Expose a few globals for inline onclicks we still generate in HTML strings
    // Keep the API surface similar to the original inline code
    window.submitFeedback = submitFeedback;
    window.showLoginPrompt = showLoginPrompt;
    window.showProUpgradePrompt = showProUpgradePrompt;
    window.startSentimentAnalysis = startSentimentAnalysis;
    window.handleAnalyzeClick = handleAnalyzeClick;

    // Make user flags globally accessible (referenced in logic)
    window.isAuthenticated = isAuthenticated;
    window.isProUser = isProUser;
    
    // Add manual scroll test function
    window.testScroll = function() {
      safeScrollIntoView(document.getElementById('analysisProgress'));
    };

    // Initialize totals
    const fetchedTopLevel = Number(commentStats?.top_level_count || 0);
    const totalTopLevel = Number(commentStats?.total_top_level_comments || commentStats?.total_available || 0);
    const totalAvailableComments = totalTopLevel || fetchedTopLevel || 5000;
    window.currentTotalComments = totalAvailableComments;

    // Video info is now rendered server-side, no need to mount it here
    
    // Mount Comment Analysis Controls - Use direct DOM for reliability
    const commentAnalysisMount = document.querySelector('#analysis-controls-root');
    console.log('[AnalyzeApp] Comment analysis mount found:', commentAnalysisMount);
    if (commentAnalysisMount) {
      console.log('[AnalyzeApp] Inserting analyze button directly');
      // Skip React for the button - use direct DOM manipulation for reliability
      commentAnalysisMount.innerHTML = `
        <div class="text-center py-3">
          <button id="mainAnalyzeBtn" class="btn btn-lg" 
                  style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                         color: white; 
                         border: none; 
                         border-radius: 25px; 
                         padding: 12px 40px; 
                         font-size: 1.1rem; 
                         font-weight: 600; 
                         box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4); 
                         cursor: pointer;
                         transition: all 0.3s ease;">
            <span>🧠</span> Analyze Sentiment
          </button>
        </div>
      `;
      
      // Add click handler
      const btn = document.getElementById('mainAnalyzeBtn');
      if (btn) {
        btn.onclick = function(e) {
          e.preventDefault();
          
          // Show the section first
          const section = document.getElementById('sentimentAnalysisSection');
          if (section) {
            section.style.display = 'block';
            
            // Start analysis immediately
            if (typeof startSentimentAnalysis === 'function') {
                startSentimentAnalysis();
                safeScrollIntoView(document.getElementById('sentimentAnalysisSection'));
            }
          }
        };
        
        // Add hover effect
        btn.addEventListener('mouseenter', () => {
          btn.style.transform = 'translateY(-2px)';
          btn.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.5)';
        });
        btn.addEventListener('mouseleave', () => {
          btn.style.transform = 'translateY(0)';
          btn.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
        });
      }
    }

    // Mount React progress and results shells
    const progressContainer = document.getElementById('analysisProgress');
    if (progressContainer) {
      progressContainer.innerHTML = '';
      const mount = document.createElement('div');
      progressContainer.appendChild(mount);
      const pr = createRoot(mount);
      let progressScrolled = 0;
      if (progressScrolled === 0) {
        safeScrollIntoView(document.getElementById('analysisProgress'));
        progressScrolled = 1;
      }

      function AnalysisProgress() {
        const [percent, setPercent] = useState(0);
        const [status, setStatus] = useState('Initializing vibe check...');
        const [subStatus, setSubStatus] = useState('Warming up the sentiment engines...');
        const [detail, setDetail] = useState('');
        const [funFact, setFunFact] = useState('Did you know? The average YouTube comment is 27 words long!');

        useEffect(() => {
          const handler = (e) => {
            const d = e.detail || {};
            if (typeof d.progress === 'number') setPercent(Math.max(0, Math.min(100, d.progress)));
            if (d.status) setStatus(d.status);
            if (d.subStatus) setSubStatus(d.subStatus);
            if (typeof d.detail === 'string') setDetail(d.detail);
          };
          const fun = setInterval(() => {
            setFunFact((prev) => {
              const idx = (funFacts.indexOf(prev) + 1 + funFacts.length) % funFacts.length;
              return funFacts[idx] || prev;
            });
          }, 5000);
          window.addEventListener('analysis:progress', handler);
          return () => { window.removeEventListener('analysis:progress', handler); clearInterval(fun); };
        }, []);

        return (
          <div className="analysis-loading-content">
            <div className="vibe-spinner mb-4">
              <div className="vibe-spinner-inner">
                <span className="vibe-emoji">🎭</span>
                <span className="vibe-emoji">😊</span>
                <span className="vibe-emoji">😐</span>
                <span className="vibe-emoji">😔</span>
              </div>
            </div>
            <h4 className="loading-status" id="progressStatus">{status}</h4>
            <p className="loading-substatus" id="progressSubStatus">{subStatus}</p>
            <div className="vibe-progress-container">
              <div className="vibe-progress-bar">
                <div className="vibe-progress-fill" style={{width: `${Math.round(percent)}%`}}>
                  <div className="vibe-progress-glow"></div>
                </div>
              </div>
            <div className="vibe-progress-text" style={{textAlign: 'center'}}>
              <span id="progressText" style={{fontSize: '1.2rem', fontWeight: 600, color: '#667eea'}}>
                {Math.round(percent)}%
              </span>
            </div>
            </div>
            <div className="loading-fun-fact" id="loadingFunFact">
              <i className="fas fa-lightbulb"></i>
              <span id="funFactText">{funFact}</span>
            </div>
          </div>
        );
      }
      pr.render(<AnalysisProgress />);
    }

    // Mount React results shell
    const resultsContainer = document.getElementById('analysisResults');
    if (resultsContainer) {
      resultsContainer.innerHTML = '';
      const mount = document.createElement('div');
      resultsContainer.appendChild(mount);
      const rr = createRoot(mount);
      function AnalysisResults() {
        const [data, setData] = useState(null);
        const [retryingSum, setRetryingSum] = useState(false);
        const barRef = React.useRef(null);
        const timelineRef = React.useRef(null);

        useEffect(() => {
          const handler = (e) => { setData(e.detail || null); };
          window.addEventListener('analysis:results', handler);
          return () => window.removeEventListener('analysis:results', handler);
        }, []);

        // Render charts when data changes
        useEffect(() => {
          if (!data || !window.Chart) return;
          const sentiment = data.sentiment || {};
          const barEl = barRef.current;
          if (barEl) {
            const ctx = barEl.getContext('2d');
            const counts = sentiment.sentiment_counts || sentiment.distribution || { positive: 0, neutral: 0, negative: 0 };
            const total = counts.positive + counts.neutral + counts.negative;
            const percentages = total > 0 ? {
              positive: ((counts.positive / total) * 100).toFixed(1),
              neutral: ((counts.neutral / total) * 100).toFixed(1),
              negative: ((counts.negative / total) * 100).toFixed(1)
            } : { positive: 0, neutral: 0, negative: 0 };
            
            if (charts.bar) charts.bar.destroy();
            charts.bar = new window.Chart(ctx, {
              type: 'bar',
              data: {
                labels: ['Sentiment Distribution'],
                datasets: [
                  { 
                    label: `Positive (${percentages.positive}%)`, 
                    data: [counts.positive||0], 
                    backgroundColor: 'rgba(34,197,94,0.9)',
                    borderColor: 'rgba(34,197,94,1)',
                    borderWidth: 1,
                    barPercentage: 1.0,
                    categoryPercentage: 1.0
                  },
                  { 
                    label: `Neutral (${percentages.neutral}%)`, 
                    data: [counts.neutral||0], 
                    backgroundColor: 'rgba(156,163,175,0.9)',
                    borderColor: 'rgba(156,163,175,1)',
                    borderWidth: 1,
                    barPercentage: 1.0,
                    categoryPercentage: 1.0
                  },
                  { 
                    label: `Negative (${percentages.negative}%)`, 
                    data: [counts.negative||0], 
                    backgroundColor: 'rgba(239,68,68,0.9)',
                    borderColor: 'rgba(239,68,68,1)',
                    borderWidth: 1,
                    barPercentage: 1.0,
                    categoryPercentage: 1.0
                  }
                ]
              },
              options: { 
                indexAxis: 'y',
                responsive: true, 
                maintainAspectRatio: false,
                scales: {
                  x: {
                    stacked: true,
                    display: false,
                    grid: { display: false }
                  },
                  y: {
                    stacked: true,
                    display: false,
                    grid: { display: false }
                  }
                },
                plugins: { 
                  legend: { 
                    display: true,
                    position: 'bottom',
                    labels: {
                      boxWidth: 15,
                      padding: 10,
                      font: { size: 12 }
                    }
                  },
                  tooltip: {
                    callbacks: {
                      label: function(context) {
                        const label = context.dataset.label || '';
                        const value = context.parsed.x || 0;
                        return `${label}: ${value} comments`;
                      }
                    }
                  }
                } 
              }
            });
          }

          const timelineEl = timelineRef.current;
          if (timelineEl) {
            if (charts.timeline) charts.timeline.destroy();
            let timeline = data.timeline;
            if (!timeline || timeline.length === 0) {
              if (sentiment.individual_results?.length > 0) {
                timeline = sentiment.individual_results.map((item, i) => ({
                  sentiment: item.predicted_sentiment || item.sentiment || 'neutral',
                  score: item.sentiment_scores || { positive: item.predicted_sentiment==='positive'?0.8:0.1, neutral: item.predicted_sentiment==='neutral'?0.8:0.1, negative: item.predicted_sentiment==='negative'?0.8:0.1 },
                  text_preview: (item.text || '').substring(0, 100), index: i,
                }));
              }
            }
            if (timeline && timeline.length > 0) {
              const groups = [];
              const groupSize = Math.max(1, Math.ceil(timeline.length / 20));
              for (let i=0;i<timeline.length;i+=groupSize){
                const group = timeline.slice(i, Math.min(i+groupSize, timeline.length));
                let ap=0, an=0, ag=0, c=0;
                group.forEach(item => { const s=item.score||item.sentiment_scores||{}; const lab=item.sentiment||item.predicted_sentiment||'neutral'; const ss = Object.keys(s).length? s : (lab==='positive'?{positive:0.8,neutral:0.15,negative:0.05}: lab==='negative'?{positive:0.05,neutral:0.15,negative:0.8}:{positive:0.1,neutral:0.8,negative:0.1}); ap+=ss.positive||0; an+=ss.neutral||0; ag+=ss.negative||0; c++; });
                c=Math.max(c,1); groups.push({positive:(ap/c)*100, neutral:(an/c)*100, negative:(ag/c)*100, index:i});
              }
              const labels=[], pd=[], nd=[], gd=[];
              groups.forEach((g, idx)=>{ const pos=(g.index/timeline.length)*100; if(idx===0) labels.push('Early'); else if(idx===groups.length-1) labels.push('Recent'); else if(Math.abs(pos-25)<5) labels.push('25%'); else if(Math.abs(pos-50)<5) labels.push('Midpoint'); else if(Math.abs(pos-75)<5) labels.push('75%'); else labels.push(`${Math.round(pos)}%`); pd.push(g.positive); nd.push(g.neutral); gd.push(g.negative); });
              const ctx2 = timelineEl.getContext('2d');
              charts.timeline = new window.Chart(ctx2, {
                type: 'line',
                data: {
                  labels,
                  datasets: [
                    { label: 'Positive', data: pd, borderColor: 'rgba(25,135,84,1)', backgroundColor: 'rgba(209,231,221,0.35)', tension: 0.4 },
                    { label: 'Neutral', data: nd, borderColor: 'rgba(160,165,170,1)', backgroundColor: 'rgba(206,212,218,0.35)', tension: 0.4 },
                    { label: 'Negative', data: gd, borderColor: 'rgba(176,42,55,1)', backgroundColor: 'rgba(227,93,106,0.25)', tension: 0.4 }
                  ]
                },
                options: {
                  responsive: true,
                  maintainAspectRatio: false,
                  scales: {
                    x: {
                      title: { display: true, text: 'Comment Timeline (Early → Recent)', font: { size: 12 } },
                      ticks: { autoSkip: false, maxRotation: 0, font: { size: 11 } }
                    },
                    y: {
                      beginAtZero: true,
                      max: 100,
                      title: { display: true, text: 'Sentiment Score', font: { size: 12 } },
                      ticks: { callback: (v) => `${v}%` }
                    }
                  },
                  plugins: { legend: { position: 'bottom' } }
                }
              });
            }
          }
        }, [data]);

        if (!data) return null;
        const sentiment = data.sentiment || {};
        const totalAnalyzed = sentiment.total_analyzed || (sentiment.individual_results?.length || 0);
        const pos = sentiment.distribution?.positive||0, neg = sentiment.distribution?.negative||0, neu = sentiment.distribution?.neutral||0;
        const total = pos+neg+neu; let overall='neutral'; if (total>0){ if (pos>neg && pos>neu) overall='positive'; else if (neg>pos && neg>neu) overall='negative'; }
        const conf = (typeof sentiment.average_confidence==='number' ? (sentiment.average_confidence>1?sentiment.average_confidence:sentiment.average_confidence*100):0).toFixed(1);

        const stats = data.updated_stats || null;
        const engagement = videoViews > 0 ? ((videoLikes / videoViews) * 100).toFixed(1) : '0.0';
        
        // Calculate percentages for display
        const counts = sentiment.sentiment_counts || sentiment.distribution || { positive: 0, neutral: 0, negative: 0 };
        const countTotal = counts.positive + counts.neutral + counts.negative;
        const percentages = countTotal > 0 ? {
          positive: ((counts.positive / countTotal) * 100).toFixed(1),
          neutral: ((counts.neutral / countTotal) * 100).toFixed(1),
          negative: ((counts.negative / countTotal) * 100).toFixed(1)
        } : { positive: 0, neutral: 0, negative: 0 };
        
        return (
          <>
            <div className="row mb-4"><div className="col-md-12"><div className="alert alert-info"><h4 className="alert-heading"><i className="fas fa-chart-line"></i> Overall Sentiment</h4><p className="mb-0"><strong>{overall[0]?.toUpperCase()+overall.slice(1)}</strong> — analyzed {totalAnalyzed} comments (confidence {conf}%)</p></div></div></div>
            <div className="row mb-4">
              <div className="col-md-12">
                <div className="card">
                  <div className="card-header header-muted-blue">
                    <h5 className="mb-0"><i className="fas fa-chart-bar"></i> Sentiment Distribution</h5>
                  </div>
                  <div className="card-body" style={{paddingTop: '20px', paddingBottom: '10px'}}>
                    <div style={{height: '80px', marginBottom: '10px'}}>
                      <canvas ref={barRef}></canvas>
                    </div>
                    <div className="sentiment-stats-row" style={{display: 'flex', justifyContent: 'space-around', marginTop: '15px', paddingTop: '15px', borderTop: '1px solid #e9ecef'}}>
                      <div style={{textAlign: 'center'}}>
                        <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#22c55e'}}>😊 {percentages.positive}%</div>
                        <div style={{fontSize: '0.9rem', color: '#6b7280'}}>{counts.positive.toLocaleString()} positive</div>
                      </div>
                      <div style={{textAlign: 'center'}}>
                        <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#9ca3af'}}>😐 {percentages.neutral}%</div>
                        <div style={{fontSize: '0.9rem', color: '#6b7280'}}>{counts.neutral.toLocaleString()} neutral</div>
                      </div>
                      <div style={{textAlign: 'center'}}>
                        <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#ef4444'}}>😔 {percentages.negative}%</div>
                        <div style={{fontSize: '0.9rem', color: '#6b7280'}}>{counts.negative.toLocaleString()} negative</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* AI Analysis Summary */}
            <div className="card mb-4">
              <div className="card-header header-muted-blue">
                <h5 className="mb-0"><i className="fas fa-robot"></i> AI Analysis Summary</h5>
              </div>
              <div className="card-body">
                <div className="lead" style={{fontSize: '16px', lineHeight: '1.6'}}>
                  {(data.summary?.summary) ? (
                    <div>
                      {data.summary.summary.split('\n').map((paragraph, idx) => (
                        <p key={idx}>{paragraph}</p>
                      ))}
                    </div>
                  ) : (
                    <div>
                      {retryingSum ? (
                        <p className="text-info">
                          <i className="fas fa-spinner fa-spin"></i> Regenerating summary...
                        </p>
                      ) : (
                        <>
                          <p className="text-muted">
                            Summary not available yet. The AI is processing the analysis results.
                          </p>
                          <button 
                            className="btn btn-sm btn-outline-primary mt-2"
                            disabled={retryingSum}
                            onClick={() => {
                              // Use global analysisId if available
                              const currentAnalysisId = window.currentAnalysisId || analysisId;
                              if (currentAnalysisId) {
                                setRetryingSum(true);
                                fetch(`/api/analyze/retry-summary/${currentAnalysisId}`, { method: 'POST' })
                                  .then(r => r.json())
                                  .then(result => {
                                    if (result.success && result.summary) {
                                      setData(prev => ({...prev, summary: result.summary}));
                                    }
                                    setRetryingSum(false);
                                  })
                                  .catch(err => {
                                    console.error('Failed to retry summary:', err);
                                    setRetryingSum(false);
                                  });
                              }
                            }}
                          >
                            <i className="fas fa-redo"></i> Generate Summary
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            <div className="card mb-4"><div className="card-header header-muted-blue"><h5 className="mb-0"><i className="fas fa-clock"></i> Sentiment Timeline</h5></div><div className="card-body"><canvas ref={timelineRef} width="400" height="200"></canvas></div></div>
            {stats && (
              <div className="card mb-4">
                <div className="card-header header-muted-blue"><h5 className="mb-0"><i className="fas fa-chart-bar"></i> Comment Coverage & Stats</h5></div>
                <div className="card-body">
                  <div className="coverage-summary mb-3">
                    <div className="coverage-main" style={{display:'flex',alignItems:'baseline',gap:'8px'}}>
                      <span className="coverage-number">{(stats.total_analyzed||totalAnalyzed).toLocaleString()}</span>
                      <span className="coverage-text">comments analyzed</span>
                      {'analysis_depth_percentage' in stats && (<span className="badge badge-info ml-2">{stats.analysis_depth_percentage}% coverage</span>)}
                    </div>
                    <div className="coverage-details" style={{display:'flex',gap:'16px',flexWrap:'wrap'}}>
                      {'top_level_count' in stats && (<span className="detail-item"><i className="fas fa-comments"></i> {(stats.top_level_count||0).toLocaleString()} threads</span>)}
                    </div>
                  </div>
                  <div className="comment-stats-grid mb-3">
                    <div className="stat-item"><div className="stat-icon text-primary"><i className="fas fa-users"></i></div><div className="stat-content"><div className="stat-value">{(stats.unique_commenters||0).toLocaleString()}</div><div className="stat-label">Unique Users</div></div></div>
                    <div className="stat-item"><div className="stat-icon text-success"><i className="fas fa-text-width"></i></div><div className="stat-content"><div className="stat-value">{stats.avg_comment_length||0}</div><div className="stat-label">Avg Length</div></div></div>
                    <div className="stat-item"><div className="stat-icon text-info"><i className="fas fa-comment-dots"></i></div><div className="stat-content"><div className="stat-value">{(stats.top_level_count||0).toLocaleString()}</div><div className="stat-label">Comments</div></div></div>
                    <div className="stat-item"><div className="stat-icon text-warning"><i className="fas fa-percentage"></i></div><div className="stat-content"><div className="stat-value">{engagement}%</div><div className="stat-label">Engagement</div></div></div>
                  </div>
                  {Array.isArray(stats.top_commenters) && stats.top_commenters.length>0 && (
                    <div className="card bg-light">
                      <div className="card-header"><h6 className="mb-0"><i className="fas fa-trophy"></i> Most Active Commenters</h6></div>
                      <div className="card-body">
                        <ol className="list-group list-group-flush">
                          {stats.top_commenters.slice(0, 10).map((c, idx) => (
                            <li key={idx} className="list-group-item d-flex justify-content-between align-items-center">
                              <span><strong>#{idx+1}</strong> {String(c[0])}</span>
                              <span className="badge badge-primary badge-pill">{(c[1]||0).toLocaleString()} comments</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        );
      }
      rr.render(<AnalysisResults />);
    }

    // Mount React Sample Comments
    const samplesContainer = document.getElementById('sampleCommentsSection');
    if (samplesContainer) {
      const inner = document.createElement('div');
      samplesContainer.innerHTML = '';
      samplesContainer.appendChild(inner);
      const sr = createRoot(inner);
      function SampleComments() {
        const [groups, setGroups] = useState({ positive: [], neutral: [], negative: [] });
        const [corrections, setCorrections] = useState({});
        const [userFeedback, setUserFeedback] = useState({});

        // Load user feedback on mount
        useEffect(() => {
          loadUserFeedback().then(feedback => {
            const feedbackMap = {};
            Object.keys(feedback).forEach(key => {
              feedbackMap[key] = feedback[key];
            });
            setUserFeedback(feedbackMap);
          });
        }, []);

        useEffect(() => {
          const handler = (e) => {
            const list = Array.isArray(e.detail) ? e.detail : [];
            const pos=[], neu=[], neg=[];
            list.forEach(r => {
              const s = r.predicted_sentiment || r.sentiment;
              const item = { 
                text: r.text || '', 
                confidence: (typeof r.confidence==='number' ? (r.confidence>1?r.confidence:(r.confidence*100)) : 0), 
                commentId: r.commentId || r.comment_id || null, 
                author: r.author || 'Anonymous',
                originalSentiment: s
              };
              if (s==='positive') pos.push(item); else if (s==='negative') neg.push(item); else neu.push(item);
            });
            pos.sort((a,b)=>b.confidence-a.confidence); neu.sort((a,b)=>b.confidence-a.confidence); neg.sort((a,b)=>b.confidence-a.confidence);
            setGroups({ positive: pos, neutral: neu, negative: neg });
            
            // Apply stored corrections
            const storageKey = `sentiment_corrections_${videoId}`;
            try {
              const storedCorrections = JSON.parse(localStorage.getItem(storageKey) || '{}');
              setCorrections(storedCorrections);
            } catch {}
          };
          window.addEventListener('analysis:samples', handler);
          return () => window.removeEventListener('analysis:samples', handler);
        }, []);

        function CommentList({ items, tone }) {
          const [localCorrections, setLocalCorrections] = useState({});
          const [submitting, setSubmitting] = useState({});
          
          async function sendFeedback(index, corrected) {
            const item = items[index]; 
            if (!item || corrected === tone) return;
            
            const commentKey = (item.text || '').substring(0, 100);
            
            try {
              setSubmitting(prev => ({...prev, [index]: true}));
              const resp = await fetch('/api/sentiment-feedback', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ 
                  video_id: videoId, 
                  comment_id: item.commentId, 
                  comment_text: item.text, 
                  comment_author: item.author, 
                  predicted_sentiment: tone, 
                  corrected_sentiment: corrected, 
                  confidence_score: (item.confidence||0)/100 
                }) 
              });
              const data = await resp.json();
              
              if (data.success) {
                showToast(data.message || 'Thank you for your feedback!', 'success', 3000);
                
                // Update local state to reflect the correction
                setLocalCorrections(prev => ({
                  ...prev,
                  [index]: { original: tone, corrected: corrected }
                }));
                
                // Store in localStorage
                const storageKey = `sentiment_corrections_${videoId}`;
                let allCorrections = {};
                try { 
                  allCorrections = JSON.parse(localStorage.getItem(storageKey) || '{}'); 
                } catch {}
                allCorrections[commentKey] = { 
                  original: tone, 
                  corrected: corrected, 
                  timestamp: new Date().toISOString() 
                };
                localStorage.setItem(storageKey, JSON.stringify(allCorrections));
                setCorrections(allCorrections);
              } else {
                if (data.error && data.error.includes('already submitted')) {
                  showToast("You've already provided feedback for this comment", 'info');
                  // Still update UI to show the correction
                  setLocalCorrections(prev => ({
                    ...prev,
                    [index]: { original: tone, corrected: corrected }
                  }));
                } else {
                  showToast(data.error || 'Failed to submit feedback', 'warning');
                }
              }
            } catch (e) {
              showToast('Failed to submit feedback', 'danger');
            } finally {
              setSubmitting(prev => ({...prev, [index]: false}));
            }
          }
          
          return (
            <div className="comment-samples-container">
              {items.length===0 ? (<p className="text-muted text-center py-3">No samples available</p>) : items.slice(0,50).map((s, idx) => {
                const confColor = s.confidence>=80 ? 'success' : s.confidence>=60 ? 'warning' : 'secondary';
                const truncated = (s.text||'').length<=300 ? s.text : (s.text||'').substring(0,300)+'...';
                const commentKey = (s.text || '').substring(0, 100);
                const correction = localCorrections[idx] || corrections[commentKey] || userFeedback[commentKey];
                const isSubmitting = submitting[idx];
                
                return (
                  <div key={idx} className={`comment-sample-item ${tone} ${correction ? 'manually-corrected' : ''}`}>
                    <div className="comment-sample-text">{truncated}</div>
                    <div className="comment-sample-meta">
                      <span className="text-muted"><i className="fas fa-user-circle"></i> {(s.author||'Anonymous').substring(0,20)}</span>
                      <span className={`confidence-badge bg-${confColor}`}>{s.confidence.toFixed(1)}%</span>
                    </div>
                    {correction && (
                      <div className="correction-info" style={{padding:'8px', background:'#f0f9ff', borderRadius:'4px', marginTop:'8px', marginBottom:'8px', fontSize:'0.85rem'}}>
                        <i className="fas fa-user-check" style={{color:'#3b82f6', marginRight:'6px'}}></i>
                        <span style={{color:'#64748b'}}>AI predicted: <strong>{correction.original}</strong></span>
                        <span style={{color:'#3b82f6', marginLeft:'8px', marginRight:'8px'}}>→</span>
                        <span style={{color:'#16a34a'}}>You corrected to: <strong>{correction.corrected}</strong></span>
                      </div>
                    )}
                    <div className="feedback-buttons">
                      <span className="text-muted" style={{fontSize:'0.7rem', marginRight:8}}>AI thinks: <strong>{tone}</strong></span>
                      <button 
                        className={`vibe-button small ${tone==='positive'?'current-sentiment':''} ${correction?.corrected==='positive'?'highlighted-correction':''}`} 
                        disabled={tone==='positive'||isSubmitting||!!correction} 
                        onClick={()=>sendFeedback(idx,'positive')}
                      >
                        👍 Positive
                      </button>
                      <button 
                        className={`vibe-button small ${tone==='neutral'?'current-sentiment':''} ${correction?.corrected==='neutral'?'highlighted-correction':''}`} 
                        disabled={tone==='neutral'||isSubmitting||!!correction} 
                        onClick={()=>sendFeedback(idx,'neutral')}
                      >
                        👐 Neutral
                      </button>
                      <button 
                        className={`vibe-button small ${tone==='negative'?'current-sentiment':''} ${correction?.corrected==='negative'?'highlighted-correction':''}`} 
                        disabled={tone==='negative'||isSubmitting||!!correction} 
                        onClick={()=>sendFeedback(idx,'negative')}
                      >
                        👎 Negative
                      </button>
                    </div>
                  </div>
                );
              })}
              {items.length>50 && (<div className="text-center text-muted py-2"><small><i className="fas fa-info-circle"></i> Showing 50 of {items.length} {tone} comments</small></div>)}
            </div>
          );
        }

        const totalComments = groups.positive.length + groups.neutral.length + groups.negative.length;
        
        return (
          <>
            {/* Container heading */}
            <div className="card-header-vibe d-flex justify-content-between align-items-center" style={{marginBottom: '20px'}}>
              <h3 className="mb-0">
                <span className="emoji-icon">💬</span> Sample Comments by Sentiment
              </h3>
              <span className="badge" style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
                color: 'white', 
                fontSize: '0.9rem',
                padding: '6px 12px'
              }}>
                {totalComments} total
              </span>
            </div>
            
            <div className="card-body">
              <div className="sentiment-section mb-4">
                <div className="sentiment-positive sentiment-header-section"><h5><span><i className="fas fa-smile"></i> Positive</span><span className="badge" style={{background:'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color:'white'}}>{groups.positive.length}</span></h5></div>
                <CommentList items={groups.positive} tone="positive" />
              </div>
              <div className="sentiment-section mb-4">
                <div className="sentiment-neutral sentiment-header-section"><h5><span><i className="fas fa-meh"></i> Neutral</span><span className="badge" style={{background:'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color:'white'}}>{groups.neutral.length}</span></h5></div>
                <CommentList items={groups.neutral} tone="neutral" />
              </div>
              <div className="sentiment-section mb-4">
                <div className="sentiment-negative sentiment-header-section"><h5><span><i className="fas fa-frown"></i> Negative</span><span className="badge" style={{background:'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color:'white'}}>{groups.negative.length}</span></h5></div>
                <CommentList items={groups.negative} tone="negative" />
              </div>
              <div className="feedback-notice mt-3"><i className="fas fa-robot"></i> Your feedback helps us improve our AI models. Click the sentiment buttons to correct any misclassifications.</div>
            </div>
          </>
        );
      }
      sr.render(<SampleComments />);
    }

    // If server provided precomputed results (from a completed job), render immediately
    if (precomputedResults) {
      const section = document.getElementById('sentimentAnalysisSection');
      const progressDiv = document.getElementById('analysisProgress');
      const resultsDiv = document.getElementById('analysisResults');
      if (section) { section.style.display = 'block'; section.classList.add('active'); }
      if (progressDiv) progressDiv.style.display = 'none';
      if (resultsDiv) resultsDiv.style.display = 'block';

      const formatted = {
        sentiment: {
          overall_sentiment: precomputedResults.overall_sentiment || 'neutral',
          distribution: precomputedResults.distribution || { positive: 0, neutral: 0, negative: 0 },
          distribution_percentage: precomputedResults.percentages || { positive: 0, neutral: 0, negative: 0 },
          sentiment_counts: precomputedResults.distribution || { positive: 0, neutral: 0, negative: 0 },
          sentiment_percentages: precomputedResults.percentages || { positive: 0, neutral: 0, negative: 0 },
          average_confidence: precomputedResults.average_confidence || 0,
          sentiment_score: precomputedResults.sentiment_score || 0,
          total_analyzed: precomputedResults.total_analyzed || 0,
          individual_results: precomputedResults.individual_results || [],
          model: precomputedResults.model || 'enhanced-sentiment-v1',
        },
        summary: {
          summary: precomputedResults.summary || 'Analysis completed successfully.',
        },
      };
      displayResults(formatted);
      const samplesSection = document.getElementById('sampleCommentsSection');
      if (samplesSection) samplesSection.style.display = 'block';
      // Also notify React components
      window.dispatchEvent(new CustomEvent('analysis:results', { detail: formatted }));
      if (formatted && formatted.sentiment && Array.isArray(formatted.sentiment.individual_results)) {
        window.dispatchEvent(new CustomEvent('analysis:samples', { detail: formatted.sentiment.individual_results }));
      }
    }

    // Load user's previous feedback (to restore local corrections UI)
    (async () => { await loadUserFeedback(); })();

    // Hook up UI events for legacy button
    const startButton = document.getElementById('startSentimentAnalysis');
    if (startButton) startButton.addEventListener('click', startSentimentAnalysis);

    // Mount React controls UI
    const controlsMount = document.getElementById('analysis-controls-root');
    if (controlsMount) {
      const controlsRoot = createRoot(controlsMount);
      function AnalysisControls() {
        const effectiveTotal = window.currentTotalComments || totalAvailableComments;
        const instantMax = Math.min(500, effectiveTotal);
        const queueMax = Math.min(isProUser ? 5000 : 2500, effectiveTotal);
        const [activeTab, setActiveTab] = useState('instant');
        const [instantValue, setInstantValue] = useState(Math.min(100, instantMax));
        const [queueValue, setQueueValue] = useState(Math.min(1000, queueMax));

        const instantCoverage = Math.min(100, Math.round((instantValue / (effectiveTotal || 1)) * 100));
        const queueCoverage = Math.min(100, Math.round((queueValue / (effectiveTotal || 1)) * 100));

        function onInstantAnalyze() {
          currentAnalysisMode = 'instant';
          startAnalysisWithMode('instant', instantValue);
          safeScrollIntoView(document.getElementById('analysisProgress'));
        }
        function onQueueAnalyze() {
          currentAnalysisMode = 'queue';
          // Enforce auth
          if (!isAuthenticated) { showToast('Please sign in to queue analysis', 'warning'); showLoginPrompt(); return; }
          // Post to queue endpoint
          const btn = document.getElementById('queueAnalyzeBtnReact');
          if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Queueing...'; }
          fetch('/api/analyze/queue', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: videoId, comment_count: queueValue, include_replies: false })
          })
            .then(r => r.json())
            .then(data => {
              if (data.success) {
                const estMin = Math.max(1, Math.round((queueValue / 100) * 1.5 / 60));
                showToast(`Analysis queued! Estimated time: ~${estMin} min`, 'success');
                setTimeout(() => { window.location.href = '/profile'; }, 1200);
              } else {
                showToast(data.error || 'Failed to queue analysis', 'danger');
                if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-clock"></i> Queue Analysis'; }
              }
            })
            .catch(err => {
              console.error('Queue error:', err);
              showToast('Failed to queue analysis', 'danger');
              if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-clock"></i> Queue Analysis'; }
            });
        }

        return (
          <div className="coverage-card">
            <div className="coverage-header">
              <h5 className="coverage-title"><span className="coverage-icon">📊</span> Analysis Coverage</h5>
            </div>
            <div className="coverage-body">
              <ul className="nav nav-tabs analysis-tabs" role="tablist">
                <li className="nav-item" role="presentation">
                  <button className={`nav-link ${activeTab==='instant'?'active':''}`} type="button" onClick={() => setActiveTab('instant')}>
                    <i className="fas fa-bolt"></i> Instant
                  </button>
                </li>
                <li className="nav-item" role="presentation">
                  <button className={`nav-link ${activeTab==='queue'?'active':''}`} type="button" onClick={() => setActiveTab('queue')}>
                    <i className="fas fa-clock"></i> Queue
                  </button>
                </li>
              </ul>

              {activeTab==='instant' ? (
                <div className="analysis-form mt-4">
                  <h6 className="text-muted mb-3">Instant Analysis</h6>
                  <div className="slider-container mb-3">
                    <label className="slider-label">Comments: <span>{instantValue}</span></label>
                    <input className="form-range coverage-slider" type="range" min={1} max={instantMax} step={1}
                      value={instantValue} onChange={(e)=>setInstantValue(parseInt(e.target.value||'0',10))}/>
                    <div className="slider-limits"><small>1</small><small>{instantMax}</small></div>
                  </div>
                  <div className="analysis-stats mb-3">
                    <span className="stat-item"><i className="fas fa-percentage"></i> Coverage: <strong>{instantCoverage}%</strong></span>
                    <span className="stat-item"><i className="fas fa-clock"></i> Time: <strong>{instantValue<=100?'~5s':instantValue<=300?'~15s':'~30s'}</strong></span>
                  </div>
                  <button className="vibe-button" onClick={onInstantAnalyze}><span className="button-icon">⚡</span><span className="button-text">Analyze</span></button>
                </div>
              ) : (
                <div className="analysis-form mt-4">
                  <h6 className="text-muted mb-3">Queue Analysis</h6>
                  {!isAuthenticated ? (
                    <div className="alert alert-info">
                      <i className="fas fa-lock"></i> Sign in to queue analysis
                      <div className="mt-3">
                        <a href="/login" className="btn btn-sm btn-primary">Sign In</a>
                        <a href="/register" className="btn btn-sm btn-outline-primary">Create Account</a>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="slider-container mb-3">
                        <label className="slider-label">Comments: <span>{queueValue.toLocaleString()}</span></label>
                        <input className="form-range coverage-slider" type="range" min={1} max={queueMax} step={queueMax<100?1:10}
                          value={queueValue} onChange={(e)=>setQueueValue(parseInt(e.target.value||'1',10))}/>
                        <div className="slider-limits"><small>1</small><small>{queueMax<1000?queueMax:`${(queueMax/1000).toFixed(1).replace('.0','')}k`}</small></div>
                      </div>
                      <div className="analysis-stats mb-3">
                        <span className="stat-item"><i className="fas fa-percentage"></i> Coverage: <strong>{queueCoverage}%</strong></span>
                        <span className="stat-item"><i className="fas fa-clock"></i> Time: <strong>{Math.round(queueValue*0.12)<60?`~${Math.round(queueValue*0.12)}s`:`~${Math.round(queueValue*0.12/60)} min`}</strong></span>
                      </div>
                      <button id="queueAnalyzeBtnReact" className="vibe-button" onClick={onQueueAnalyze}><span className="button-icon">⏱</span><span className="button-text">Queue Analysis</span></button>
                      {!isProUser && (<div className="mt-3 text-center"><small className="text-muted"><i className="fas fa-crown"></i> Upgrade to Pro for up to 5,000 comments (currently 2,500 limit) <br/><a href="/subscribe">Learn More</a></small></div>)}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      }
      controlsRoot.render(<AnalysisControls />);
    }

    function startAnalysisWithMode(mode, commentsToAnalyze) {
      currentAnalysisMode = mode;
      if (mode === 'queue') {
        if (!isAuthenticated) {
          showToast('Please sign in to use Queue mode', 'warning');
          if (typeof window.showLoginPrompt === 'function') window.showLoginPrompt();
          return;
        }
        const button = queueAnalyzeBtn;
        if (button) { button.disabled = true; button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Queueing...'; }
        fetch('/api/analyze/queue', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_id: videoId, comment_count: commentsToAnalyze, include_replies: false })
        })
          .then(r => r.json())
          .then(data => {
            if (data.success) {
              const estimatedMinutes = Math.round((commentsToAnalyze / 100) * 1.5 / 60);
              const timeText = estimatedMinutes > 1 ? `${estimatedMinutes} minutes` : '1 minute';
              showToast(`Analysis queued! Estimated time: ~${timeText}`, 'success');
              setTimeout(() => { window.location.href = `/analysis/${data.job_id}`; }, 1500);
            } else {
              showToast(`Error: ${data.error}`, 'danger');
              if (button) { button.disabled = false; button.innerHTML = '<i class="fas fa-clock"></i> Queue Analysis'; }
            }
          })
          .catch(err => {
            console.error('Error queueing analysis:', err);
            showToast('Failed to queue analysis', 'danger');
            if (button) { button.disabled = false; button.innerHTML = '<i class="fas fa-clock"></i> Queue Analysis'; }
          });
      } else {
        // Instant mode
        const section = document.getElementById('sentimentAnalysisSection');
        const progressDiv = document.getElementById('analysisProgress');
        const resultsDiv = document.getElementById('analysisResults');
        if (section) { section.style.display = 'block'; section.classList.add('active'); }
        if (progressDiv) progressDiv.style.display = 'flex';
        if (resultsDiv) resultsDiv.style.display = 'none';
        analysisStartTs = Date.now();
        initiateAnalysis(videoId, commentsToAnalyze, Math.round((commentsToAnalyze / (window.currentTotalComments || 5000)) * 100));
      }
    }

    function startSentimentAnalysis() {
      // Provide legacy button support (instant mode by default)
      const instantSliderEl = document.getElementById('instantSlider');
      const value = parseInt((instantSliderEl && instantSliderEl.value) || '100', 10);
      currentAnalysisMode = 'instant';
      // Reset loading state
      if (messageRotationInterval) clearInterval(messageRotationInterval);
      if (factRotationInterval) clearInterval(factRotationInterval);
      if (progressAnimationFrame) cancelAnimationFrame(progressAnimationFrame);
      lastProgressValue = 0; targetProgress = 0; currentMessageIndex = 0; currentFactIndex = 0;

      const section = document.getElementById('sentimentAnalysisSection');
      const progressDiv = document.getElementById('analysisProgress');
      const resultsDiv = document.getElementById('analysisResults');
      const analysisActionButton = document.getElementById('analysisActionButton');

      const totalAvailable = Number(commentStats?.total_available || 0);
      const fetchedCommentsCount = Number(commentStats?.total_comments || 0);
      const effectiveTotal = totalAvailable || videoStatsComments || fetchedCommentsCount || 0;

      let commentsToAnalyze = Math.min(value, isAuthenticated ? (isProUser ? 5000 : 2500) : 500);
      commentsToAnalyze = Math.max(commentsToAnalyze, 5);

      // Show section & set loading text
      if (section) { section.style.display = 'block'; section.classList.add('active'); }
      if (progressDiv) progressDiv.style.display = 'flex';
      if (resultsDiv) resultsDiv.style.display = 'none';

      const funFactText = document.getElementById('funFactText');
      if (funFactText) funFactText.textContent = funFacts[0];
      if (analysisActionButton) { analysisActionButton.disabled = true; analysisActionButton.innerHTML = '<i class=\"fas fa-spinner fa-spin\"></i> Analyzing...'; }
      safeScrollIntoView(section);

      const selectedPercentage = Math.round((commentsToAnalyze / (window.currentTotalComments || 5000)) * 100);
      analysisStartTs = Date.now();
      initiateAnalysis(videoId, commentsToAnalyze, selectedPercentage);
    }

    function initiateAnalysis(videoId, commentsToAnalyze, selectedPercentage) {
      const includeReplies = false;
      fetch(`/api/analyze/sentiment/${videoId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          max_comments: commentsToAnalyze,
          percentage_selected: selectedPercentage,
          include_replies: includeReplies,
        }),
      })
        .then(response => {
          if (response.status === 507) {
            showError('The analysis cache is currently full. Please wait a moment while we clear some space and try again.');
            setTimeout(() => { showError('Retrying analysis...'); startSentimentAnalysis(); }, 3000);
            return null;
          }
          return response.json();
        })
        .then(data => {
          if (!data) return;
          if (data.success) {
            analysisId = data.analysis_id;
            window.currentAnalysisId = analysisId; // Expose globally for React components
            if (data.cached) fetchAnalysisResults();
            else statusCheckInterval = setInterval(checkAnalysisStatus, 1000);
          } else {
            showError(data.error || 'Failed to start analysis');
          }
        })
        .catch(err => showError('Failed to start analysis: ' + err));
    }

    function checkAnalysisStatus() {
      if (!analysisId) return;
      fetch(`/api/analyze/status/${analysisId}`)
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            updateProgress(data.status);
            if (data.status.status === 'completed') {
              clearInterval(statusCheckInterval); fetchAnalysisResults();
            } else if (data.status.status === 'error') {
              clearInterval(statusCheckInterval); showError(data.status.error);
            }
          } else if (!data.success && data.error === 'Analysis not found') {
            clearInterval(statusCheckInterval);
            showError('Analysis data was cleared. Restarting...');
            analysisId = null; setTimeout(() => startSentimentAnalysis(), 1500);
          }
        })
        .catch(err => console.error('Status check error:', err));
    }

    function fetchAnalysisResults() {
      if (!analysisId) return;
      fetch(`/api/analyze/results/${analysisId}`)
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            // Dispatch to React results and samples components
            window.dispatchEvent(new CustomEvent('analysis:results', { detail: data.results }));
            if (data.results?.sentiment?.individual_results) {
              window.dispatchEvent(new CustomEvent('analysis:samples', { detail: data.results.sentiment.individual_results }));
            }
            displayResults(data.results);
          } else if (data.restart_needed || (data.error && data.error.includes('Analysis not found'))) {
            showError('This analysis has expired or been cleared. Starting a new analysis...');
            analysisId = null;
            setTimeout(() => {
              const progressDiv = document.getElementById('analysisProgress');
              const resultsDiv = document.getElementById('analysisResults');
              if (progressDiv) progressDiv.style.display = 'flex';
              if (resultsDiv) resultsDiv.style.display = 'none';
              startSentimentAnalysis();
            }, 1500);
          } else {
            showError(data.error + (data.details ? ': ' + data.details : ''));
          }
        })
        .catch(err => showError('Failed to fetch results: ' + err));
    }

    function updateProgress(status) {
      targetProgress = status.progress || 0;
      let mainStatus = 'Initializing vibe check...';
      let subStatus = '';
      let messagePool = [];

      switch (status.status) {
        case 'fetching_comments':
          mainStatus = 'Downloading Comments';
          subStatus = loadingMessages.fetching_comments[0];
          messagePool = loadingMessages.fetching_comments;
          break;
        case 'using_cached':
          mainStatus = 'Loading Cached Data';
          subStatus = 'Retrieving pre-analyzed vibes...';
          break;
        case 'analyzing_sentiment':
          mainStatus = 'Analyzing Sentiment';
          subStatus = loadingMessages.analyzing_sentiment[0];
          messagePool = loadingMessages.analyzing_sentiment;
          break;
        case 'generating_summary':
          mainStatus = 'Generating Insights';
          subStatus = loadingMessages.generating_summary[0];
          messagePool = loadingMessages.generating_summary;
          break;
        case 'completed':
          mainStatus = '✨ Analysis Complete!';
          subStatus = 'Your results are ready!';
          break;
      }
      lastProgressValue = targetProgress;
      window.dispatchEvent(new CustomEvent('analysis:progress', { detail: { progress: targetProgress, status: mainStatus, subStatus } }));

      if (messagePool.length > 0 && status.status !== 'completed') {
        if (messageRotationInterval) clearInterval(messageRotationInterval);
        currentMessageIndex = 0;
        messageRotationInterval = setInterval(() => {
          currentMessageIndex = (currentMessageIndex + 1) % messagePool.length;
          window.dispatchEvent(new CustomEvent('analysis:progress', { detail: { subStatus: messagePool[currentMessageIndex] } }));
        }, 3000);
      }

      if (!factRotationInterval && status.status !== 'completed') {
        const ff = setInterval(() => {
          window.dispatchEvent(new CustomEvent('analysis:progress', { detail: {} }));
        }, 5000);
        factRotationInterval = ff;
      }
    }

    function retrySummary() {
      if (!analysisId) return;
      const aiSummaryEl = document.getElementById('aiSummary');
      if (aiSummaryEl) aiSummaryEl.innerHTML = '<p>Retrying summary... <i class="fas fa-spinner fa-spin"></i></p>';
      fetch(`/api/analyze/retry-summary/${analysisId}`, { method: 'POST' })
        .then(r => r.json())
        .then(data => { if (data.success && data.summary && data.summary.summary) fetchAnalysisResults(); })
        .catch(err => { if (aiSummaryEl) aiSummaryEl.innerHTML = `<p>Summary retry failed: ${err}</p>`; });
    }

    function displayResults(results) {
      const progressDiv = document.getElementById('analysisProgress');
      const resultsDiv = document.getElementById('analysisResults');
      const samplesSection = document.getElementById('sampleCommentsSection');
      const startButton = document.getElementById('startSentimentAnalysis');
      if (!results || !results.sentiment) { showError('No results returned. Please try again.'); return; }

      if (progressDiv) progressDiv.style.display = 'none';
      if (resultsDiv) resultsDiv.style.display = 'block';
      if (samplesSection) samplesSection.style.display = 'block';
      if (startButton) { startButton.innerHTML = '<i class=\"fas fa-sync\"></i> Re-analyze'; startButton.disabled = false; }

      const sentiment = results.sentiment;
      const overallEl = document.getElementById('overallSentiment');
      let overallSentiment = 'neutral';
      let sentimentScore = 50;
      if (sentiment.distribution) {
        const pos = sentiment.distribution.positive || 0;
        const neg = sentiment.distribution.negative || 0;
        const neu = sentiment.distribution.neutral || 0;
        const total = pos + neg + neu;
        if (total > 0) {
          sentimentScore = ((pos - neg) / total * 50) + 50;
          if (pos > neg && pos > neu) overallSentiment = 'positive';
          else if (neg > pos && neg > neu) overallSentiment = 'negative';
          else overallSentiment = 'neutral';
        }
      }
      const rawConf = (typeof sentiment.average_confidence === 'number') ? sentiment.average_confidence : 0;
      const confPercent = rawConf > 1 ? rawConf.toFixed(1) : (rawConf * 100).toFixed(1);
      const totalAnalyzed = sentiment.total_analyzed || (Array.isArray(sentiment.individual_results) ? sentiment.individual_results.length : 0);
      if (overallEl) {
        overallEl.innerHTML = `
          <strong>${overallSentiment.charAt(0).toUpperCase() + overallSentiment.slice(1)}</strong>
          (Score: ${sentimentScore.toFixed(1)}%, Confidence: ${confPercent}%)<br>
          <small>Analyzed ${totalAnalyzed} comments using advanced sentiment analysis</small>
        `;
      }

      const aiSummaryEl = document.getElementById('aiSummary');
      const summary = results.summary;
      if (aiSummaryEl && summary) {
        if (summary.summary) {
          aiSummaryEl.innerHTML = `<p>${summary.summary}</p>`;
        } else {
          aiSummaryEl.innerHTML = '<p>Summary not available. <a href="#" id="retrySummaryLink">Try again</a></p>';
          const retryLink = document.getElementById('retrySummaryLink');
          if (retryLink) {
            retryLink.addEventListener('click', (e) => { e.preventDefault(); retryLink.innerHTML = 'Retrying... <i class="fas fa-spinner fa-spin"></i>'; retrySummary(); });
          }
        }
      }

        setTimeout(() => {
          try { createSentimentPieChart(sentiment); } catch (e) { console.error('bar chart error', e); }
          try {
          let timelineData = results.timeline;
          if (!timelineData || timelineData.length === 0) {
            if (sentiment.individual_results && sentiment.individual_results.length > 0) {
              timelineData = sentiment.individual_results.map((item, index) => ({
                sentiment: item.predicted_sentiment || item.sentiment || 'neutral',
                score: item.sentiment_scores || {
                  positive: item.predicted_sentiment === 'positive' ? 0.8 : 0.1,
                  neutral: item.predicted_sentiment === 'neutral' ? 0.8 : 0.1,
                  negative: item.predicted_sentiment === 'negative' ? 0.8 : 0.1,
                },
                text_preview: (item.text || '').substring(0, 100),
                index,
              }));
            }
          }
          if (timelineData && timelineData.length > 0) createTimelineChart(timelineData);
          else {
            const timelineCard = document.querySelector('#sentimentTimelineChart')?.closest('.card');
            if (timelineCard) timelineCard.style.display = 'none';
          }
        } catch (e) { console.error('timeline chart error', e); }
      }, 300);

      // React-based sample comments rendering will handle this now

      if (results.updated_stats) {
        const elapsedSeconds = analysisStartTs ? Math.max(1, Math.round((Date.now() - analysisStartTs) / 1000)) : null;
        updateCommentStatistics(results.updated_stats, { elapsedSeconds, totalAnalyzed: results.updated_stats.total_analyzed, videoViews, videoLikes });
      }
    }

    function createSentimentPieChart(sentiment) {
      const canvas = document.getElementById('sentimentPieChart');
      if (!canvas || !window.Chart) return;
      const ctx = canvas.getContext('2d');
      if (charts.bar) charts.bar.destroy();
      const counts = sentiment.sentiment_counts || sentiment.distribution || { positive: 0, neutral: 0, negative: 0 };
      const total = counts.positive + counts.neutral + counts.negative;
      const percentages = total > 0 ? {
        positive: ((counts.positive / total) * 100).toFixed(1),
        neutral: ((counts.neutral / total) * 100).toFixed(1),
        negative: ((counts.negative / total) * 100).toFixed(1)
      } : { positive: 0, neutral: 0, negative: 0 };
      
      charts.bar = new window.Chart(ctx, {
        type: 'bar',
        data: {
          labels: [''],
          datasets: [
            { 
              label: `Positive (${percentages.positive}%)`, 
              data: [counts.positive || 0], 
              backgroundColor: 'rgba(34,197,94,0.9)',
              borderColor: 'rgba(34,197,94,1)',
              borderWidth: 1
            },
            { 
              label: `Neutral (${percentages.neutral}%)`, 
              data: [counts.neutral || 0], 
              backgroundColor: 'rgba(156,163,175,0.9)',
              borderColor: 'rgba(156,163,175,1)',
              borderWidth: 1
            },
            { 
              label: `Negative (${percentages.negative}%)`, 
              data: [counts.negative || 0], 
              backgroundColor: 'rgba(239,68,68,0.9)',
              borderColor: 'rgba(239,68,68,1)',
              borderWidth: 1
            }
          ],
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              stacked: true,
              display: false,
              grid: { display: false }
            },
            y: {
              stacked: true,
              display: false,
              grid: { display: false }
            }
          },
          plugins: {
            legend: { 
              display: true,
              position: 'bottom',
              labels: {
                boxWidth: 15,
                padding: 8,
                font: { size: 11 }
              }
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const label = context.dataset.label || '';
                  const value = context.parsed.x || 0;
                  return `${value} comments`;
                },
              },
            },
          },
        },
      });
    }

    function createTimelineChart(timeline) {
      const canvas = document.getElementById('sentimentTimelineChart');
      if (!canvas || !window.Chart) return;
      const ctx = canvas.getContext('2d');
      if (charts.timeline) charts.timeline.destroy();

      if (!timeline || timeline.length === 0) {
        const timelineCard = canvas.closest('.card');
        if (timelineCard) {
          const cardBody = timelineCard.querySelector('.card-body');
          if (cardBody) cardBody.innerHTML = '<p class="text-muted text-center py-3">Timeline data not available for this analysis</p>';
        }
        return;
      }

      const groups = [];
      const groupSize = Math.max(1, Math.ceil(timeline.length / 20));
      for (let i = 0; i < timeline.length; i += groupSize) {
        const group = timeline.slice(i, Math.min(i + groupSize, timeline.length));
        let avgPositive = 0, avgNeutral = 0, avgNegative = 0, valid = 0;
        group.forEach(item => {
          const sc = item.score || item.sentiment_scores || {};
          let s = sc;
          if (!s || Object.keys(s).length === 0) {
            const lab = item.sentiment || item.predicted_sentiment || 'neutral';
            s = lab === 'positive' ? { positive: 0.8, neutral: 0.15, negative: 0.05 }
              : lab === 'negative' ? { positive: 0.05, neutral: 0.15, negative: 0.8 }
              : { positive: 0.1, neutral: 0.8, negative: 0.1 };
          }
          avgPositive += (s.positive || 0); avgNeutral += (s.neutral || 0); avgNegative += (s.negative || 0); valid++;
        });
        const c = Math.max(valid, 1);
        groups.push({ positive: (avgPositive / c) * 100, neutral: (avgNeutral / c) * 100, negative: (avgNegative / c) * 100, index: i });
      }

      const labels = [], positiveData = [], neutralData = [], negativeData = [];
      groups.forEach((g, idx) => {
        const position = (g.index / timeline.length) * 100;
        if (idx === 0) labels.push('Early');
        else if (idx === groups.length - 1) labels.push('Recent');
        else if (Math.abs(position - 25) < 5) labels.push('25%');
        else if (Math.abs(position - 50) < 5) labels.push('Midpoint');
        else if (Math.abs(position - 75) < 5) labels.push('75%');
        else labels.push(`${Math.round(position)}%`);
        positiveData.push(g.positive); neutralData.push(g.neutral); negativeData.push(g.negative);
      });

      charts.timeline = new window.Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            { label: 'Positive', data: positiveData, borderColor: 'rgba(25,135,84,1)', backgroundColor: 'rgba(209,231,221,0.35)', tension: 0.4 },
            { label: 'Neutral', data: neutralData, borderColor: 'rgba(160,165,170,1)', backgroundColor: 'rgba(206,212,218,0.35)', tension: 0.4 },
            { label: 'Negative', data: negativeData, borderColor: 'rgba(176,42,55,1)', backgroundColor: 'rgba(227,93,106,0.25)', tension: 0.4 },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { title: { display: true, text: 'Comment Timeline (Early → Recent)', font: { size: 12 } }, ticks: { autoSkip: false, maxRotation: 0, font: { size: 11 } } },
            y: { beginAtZero: true, max: 100, title: { display: true, text: 'Sentiment Score', font: { size: 12 } }, ticks: { callback: (v) => `${v}%` } },
          },
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { position: 'bottom' } },
        },
      });
    }

    function displaySampleComments(results) {
      if (!results || !Array.isArray(results)) return;
      const positive = [], neutral = [], negative = [];
      results.forEach(r => {
        const comment = {
          text: r.text || '',
          confidence: ((typeof r.confidence === 'number' ? (r.confidence > 1 ? r.confidence : r.confidence * 100) : 0)).toFixed(1),
          commentId: (r.commentId || r.comment_id || null),
          author: r.author || 'Anonymous',
        };
        const s = r.predicted_sentiment || r.sentiment;
        if (s === 'positive') positive.push(comment);
        else if (s === 'neutral') neutral.push(comment);
        else if (s === 'negative') negative.push(comment);
      });
      positive.sort((a,b) => parseFloat(b.confidence) - parseFloat(a.confidence));
      neutral.sort((a,b) => parseFloat(b.confidence) - parseFloat(a.confidence));
      negative.sort((a,b) => parseFloat(b.confidence) - parseFloat(a.confidence));
      const setCounts = () => {
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = String(v); };
        set('positiveCount', positive.length);
        set('neutralCount', neutral.length);
        set('negativeCount', negative.length);
      };
      setCounts();

      const displaySamples = (samples, elementId, sentimentClass) => {
        const el = document.getElementById(elementId);
        if (!el) return;
        if (samples.length === 0) { el.innerHTML = '<p class="text-muted text-center py-3">No samples available</p>'; return; }
        const displayLimit = Math.min(samples.length, 50);
        const truncate = (t, n=300) => (t.length <= n ? t : t.substring(0, n) + '...');
        const escapeHtml = (text) => text.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#039;'}[m]));
        el.innerHTML = samples.slice(0, displayLimit).map((s, index) => {
          const truncated = escapeHtml(truncate(s.text));
          const confColor = parseFloat(s.confidence) >= 80 ? 'success' : (parseFloat(s.confidence) >= 60 ? 'warning' : 'secondary');
          const commentDomId = `comment-${sentimentClass}-${index}`;
          return `
            <div class="comment-sample-item ${sentimentClass}" id="${commentDomId}" data-comment-index="${index}">
              <div class="comment-sample-text">${truncated}</div>
              <div class="comment-sample-meta">
                <span class="text-muted"><i class="fas fa-user-circle"></i> ${escapeHtml((s.author || 'Anonymous').substring(0, 20))}</span>
                <span class="confidence-badge bg-${confColor}">${s.confidence}%</span>
              </div>
              <div class="feedback-buttons">
                <span class="text-muted" style="font-size: 0.7rem; margin-right: 8px;">AI thinks:</span>
                <button class="feedback-btn positive ${sentimentClass === 'positive' ? 'current-sentiment' : ''}" ${sentimentClass === 'positive' ? 'disabled' : ''} onclick="submitFeedback('${commentDomId}', '${sentimentClass}', 'positive', ${index})">👍 Positive</button>
                <button class="feedback-btn neutral ${sentimentClass === 'neutral' ? 'current-sentiment' : ''}" ${sentimentClass === 'neutral' ? 'disabled' : ''} onclick="submitFeedback('${commentDomId}', '${sentimentClass}', 'neutral', ${index})">👐 Neutral</button>
                <button class="feedback-btn negative ${sentimentClass === 'negative' ? 'current-sentiment' : ''}" ${sentimentClass === 'negative' ? 'disabled' : ''} onclick="submitFeedback('${commentDomId}', '${sentimentClass}', 'negative', ${index})">👎 Negative</button>
              </div>
            </div>
          `;
        }).join('');
        if (samples.length > displayLimit) {
          el.innerHTML += `<div class="text-center text-muted py-2"><small><i class="fas fa-info-circle"></i> Showing ${displayLimit} of ${samples.length} ${sentimentClass} comments</small></div>`;
        }
      };

      commentData.positive = positive; commentData.neutral = neutral; commentData.negative = negative;
      displaySamples(positive, 'positiveSamples', 'positive');
      displaySamples(neutral, 'neutralSamples', 'neutral');
      displaySamples(negative, 'negativeSamples', 'negative');
      setTimeout(applyStoredCorrections, 100);
    }

    async function submitFeedback(commentDomId, predictedSentiment, correctedSentiment, commentIndex) {
      if (predictedSentiment === correctedSentiment) return;
      const commentElement = document.getElementById(commentDomId);
      const commentObj = (commentData[predictedSentiment] || [])[commentIndex];
      if (!commentObj) return;
      try {
        const buttons = commentElement?.querySelectorAll('.feedback-btn') || [];
        buttons.forEach(btn => (btn.disabled = true));
        const response = await fetch('/api/sentiment-feedback', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            video_id: videoId, comment_id: commentObj.commentId, comment_text: commentObj.text,
            comment_author: commentObj.author, predicted_sentiment: predictedSentiment,
            corrected_sentiment: correctedSentiment, confidence_score: parseFloat(commentObj.confidence) / 100,
          })
        });
        const data = await response.json();
        if (data.success) {
          showToast(data.message || 'Thank you for your feedback!', 'success', 3000);
          applyManualCorrectionUI(commentElement, predictedSentiment, correctedSentiment);
          storeCorrectionLocally(commentObj.text, predictedSentiment, correctedSentiment);
        } else {
          buttons.forEach(btn => (btn.disabled = false));
          if (data.error && data.error.includes('already submitted')) showToast("You've already provided feedback for this comment", 'info');
          else showToast(data.error || 'Failed to submit feedback', 'warning');
        }
      } catch (err) {
        console.error('Error submitting feedback:', err);
        showToast('Failed to submit feedback. Please try again.', 'danger');
        const buttons = commentElement?.querySelectorAll('.feedback-btn') || [];
        buttons.forEach(btn => (btn.disabled = false));
      }
    }

    function applyManualCorrectionUI(commentElement, originalSentiment, correctedSentiment) {
      if (!commentElement) return;
      commentElement.classList.add('manually-corrected');
      if (!commentElement.querySelector('.manual-correction-badge')) {
        const badge = document.createElement('div');
        badge.className = 'manual-correction-badge';
        badge.innerHTML = '<i class="fas fa-user-check"></i> Manually Corrected';
        commentElement.appendChild(badge);
      }
      const buttons = commentElement.querySelectorAll('.feedback-btn');
      buttons.forEach(btn => {
        btn.disabled = true;
        btn.classList.remove('current-sentiment', 'highlighted-correction', 'disabled-original');
        if (btn.classList.contains(originalSentiment)) btn.classList.add('disabled-original');
        else if (btn.classList.contains(correctedSentiment)) btn.classList.add('highlighted-correction');
      });
      if (!commentElement.querySelector('.correction-info')) {
        const correctionInfo = document.createElement('div');
        correctionInfo.className = 'correction-info';
        correctionInfo.innerHTML = `
          <i class="fas fa-info-circle"></i>
          <span class="original-prediction">AI predicted: ${capitalizeFirst(originalSentiment)}</span>
          <span class="user-correction">→ You corrected to: ${capitalizeFirst(correctedSentiment)}</span>
        `;
        commentElement.appendChild(correctionInfo);
      }
    }

    function storeCorrectionLocally(commentText, originalSentiment, correctedSentiment) {
      const storageKey = `sentiment_corrections_${videoId}`;
      let corrections = {};
      try { corrections = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch { corrections = {}; }
      const commentKey = (commentText || '').substring(0, 100);
      corrections[commentKey] = { original: originalSentiment, corrected: correctedSentiment, timestamp: new Date().toISOString() };
      localStorage.setItem(storageKey, JSON.stringify(corrections));
    }

    async function loadUserFeedback() {
      try {
        const response = await fetch(`/api/sentiment-feedback?video_id=${videoId}`);
        const data = await response.json();
        if (data.success && data.feedback.length > 0) {
          const storageKey = `sentiment_corrections_${videoId}`;
          const corrections = {};
          data.feedback.forEach(fb => {
            const commentKey = (fb.comment_text || '').substring(0, 100);
            corrections[commentKey] = { original: fb.predicted_sentiment, corrected: fb.corrected_sentiment, timestamp: fb.created_at };
          });
          localStorage.setItem(storageKey, JSON.stringify(corrections));
          return corrections;
        }
      } catch (e) { console.error('Error loading user feedback:', e); }
      return {};
    }

    function applyStoredCorrections() {
      const storageKey = `sentiment_corrections_${videoId}`;
      let corrections = {};
      try { corrections = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch { corrections = {}; }
      Object.keys(commentData).forEach(sentiment => {
        (commentData[sentiment] || []).forEach((comment, index) => {
          const commentKey = (comment.text || '').substring(0, 100);
          const correction = corrections[commentKey];
          if (correction) {
            const commentId = `comment-${sentiment}-${index}`;
            const commentElement = document.getElementById(commentId);
            if (commentElement) applyManualCorrectionUI(commentElement, correction.original, correction.corrected);
          }
        });
      });
    }

    function updateCommentStatistics(stats, extras = {}) {
      if (!stats) return;
      const mount = document.getElementById('react-comment-metrics');
      if (!mount) return;

      const { elapsedSeconds, totalAnalyzed, videoViews = 0, videoLikes = 0 } = extras;
      const root = createRoot(mount);

      const analyzed = totalAnalyzed ?? stats.total_analyzed ?? 0;
      const coverage = stats.analysis_depth_percentage ?? 0;
      const threads = stats.top_level_count ?? 0;
      const seconds = elapsedSeconds ?? null;
      const rate = seconds ? Math.max(0, (analyzed / seconds)).toFixed(1) : null;
      const engagement = videoViews > 0 ? ((videoLikes / videoViews) * 100).toFixed(1) : '0.0';

      const topCommenters = Array.isArray(stats.top_commenters) ? stats.top_commenters : [];

      function MetricsCard() {
        return (
          <div className="card">
            <div className="card-header header-muted-blue">
              <h5 className="mb-0"><i className="fas fa-chart-bar"></i> Comment Coverage & Stats</h5>
            </div>
            <div className="card-body">
              {/* Header summary */}
              <div className="coverage-summary mb-3">
                <div className="coverage-main" style={{display:'flex',alignItems:'baseline',gap:'8px'}}>
                  <span className="coverage-number">{analyzed.toLocaleString()}</span>
                  <span className="coverage-text">comments analyzed</span>
                  <span className="badge badge-info ml-2">{coverage}% coverage</span>
                </div>
                <div className="coverage-details" style={{display:'flex',gap:'16px',flexWrap:'wrap'}}>
                  <span className="detail-item"><i className="fas fa-comments"></i> {threads.toLocaleString()} threads</span>
                  {seconds ? <span className="detail-item"><i className="fas fa-clock"></i> {seconds}s</span> : null}
                  {rate ? <span className="detail-item"><i className="fas fa-tachometer-alt"></i> {rate} /sec</span> : null}
                </div>
              </div>

              {/* Stats grid */}
              <div className="comment-stats-grid mb-3">
                <div className="stat-item"><div className="stat-icon text-primary"><i className="fas fa-users"></i></div><div className="stat-content"><div className="stat-value">{(stats.unique_commenters||0).toLocaleString()}</div><div className="stat-label">Unique Users</div></div></div>
                <div className="stat-item"><div className="stat-icon text-success"><i className="fas fa-text-width"></i></div><div className="stat-content"><div className="stat-value">{stats.avg_comment_length||0}</div><div className="stat-label">Avg Length</div></div></div>
                <div className="stat-item"><div className="stat-icon text-info"><i className="fas fa-comment-dots"></i></div><div className="stat-content"><div className="stat-value">{(stats.top_level_count||0).toLocaleString()}</div><div className="stat-label">Comments</div></div></div>
                <div className="stat-item"><div className="stat-icon text-warning"><i className="fas fa-percentage"></i></div><div className="stat-content"><div className="stat-value">{engagement}%</div><div className="stat-label">Engagement</div></div></div>
              </div>

              {/* Top commenters */}
              {topCommenters.length > 0 && (
                <div className="card bg-light">
                  <div className="card-header"><h6 className="mb-0"><i className="fas fa-trophy"></i> Most Active Commenters</h6></div>
                  <div className="card-body">
                    <ol className="list-group list-group-flush">
                      {topCommenters.slice(0, 10).map((c, idx) => (
                        <li key={idx} className="list-group-item d-flex justify-content-between align-items-center">
                          <span><strong>#{idx+1}</strong> {String(c[0])}</span>
                          <span className="badge badge-primary badge-pill">{(c[1]||0).toLocaleString()} comments</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      }

      root.render(<MetricsCard />);
    }

    function showToast(message, type = 'info', duration = 3000) {
      let container = document.getElementById('toastContainer');
      if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
        document.body.appendChild(container);
      }
      const toast = document.createElement('div');
      const bs = type === 'success' ? 'success' : type === 'danger' ? 'danger' : type === 'warning' ? 'warning' : 'info';
      toast.className = `alert alert-${bs} alert-dismissible fade show`;
      toast.style.cssText = 'min-width: 250px; margin-bottom: 10px; animation: slideIn 0.3s ease-out;';
      toast.setAttribute('role', 'alert');
      const icon = type === 'success' ? '✓' : type === 'danger' ? '✕' : type === 'warning' ? '⚠' : 'ℹ';
      toast.innerHTML = `<strong>${icon}</strong> ${message}<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>`;
      container.appendChild(toast);
      setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 150); }, duration);
    }

    function showError(error) {
      const progressDiv = document.getElementById('analysisProgress');
      const startButton = document.getElementById('startSentimentAnalysis');
      if (messageRotationInterval) { clearInterval(messageRotationInterval); messageRotationInterval = null; }
      if (factRotationInterval) { clearInterval(factRotationInterval); factRotationInterval = null; }
      if (progressAnimationFrame) { cancelAnimationFrame(progressAnimationFrame); progressAnimationFrame = null; }

      let errorTitle = 'Oops! Something went wrong';
      let errorMessage = error || 'Unknown error';
      let errorIcon = 'fas fa-exclamation-triangle';
      let suggestions = [];
      const e = String(error || '').toLowerCase();
      if (e.includes('unfinished') || e.includes('timeout')) {
        errorTitle = 'Analysis Timeout'; errorIcon = 'fas fa-clock';
        errorMessage = 'The analysis is taking longer than expected. This usually happens when processing many comments.';
        suggestions = ['Try analyzing fewer comments', 'Wait a moment for the service to recover', 'Try again in a few minutes'];
      } else if (e.includes('memory') || e.includes('cache')) {
        errorTitle = 'Service Temporarily Busy'; errorIcon = 'fas fa-server';
        errorMessage = 'Our servers are experiencing high demand right now.';
        suggestions = ['Please wait and try again', 'Consider analyzing fewer comments', 'Try during off-peak hours'];
      } else if (e.includes('not found')) {
        errorTitle = 'Analysis Not Found'; errorIcon = 'fas fa-search';
        errorMessage = "The analysis results couldn't be found. They may have expired.";
        suggestions = ['Start a fresh analysis', "Make sure you haven't waited too long"];
      } else if (e.includes('network') || e.includes('fetch')) {
        errorTitle = 'Connection Issue'; errorIcon = 'fas fa-wifi';
        errorMessage = 'There was a problem connecting to our analysis service.';
        suggestions = ['Check your internet', 'Refresh the page', 'Disable any blockers that might interfere'];
      } else if (e.includes('high load') || e.includes('service')) {
        errorTitle = 'Service Under Load'; errorIcon = 'fas fa-chart-line';
        errorMessage = 'Our sentiment analysis service is experiencing high demand.';
        suggestions = ['Try with fewer comments', 'Wait a few minutes', 'Consider queue option if available'];
      }
      const suggestionsHtml = suggestions.length > 0 ? `<div class="mt-3"><h6 class="font-weight-bold">What you can try:</h6><ul class="mb-0">${suggestions.map(s => `<li>${s}</li>`).join('')}</ul></div>` : '';
      if (progressDiv) {
        progressDiv.innerHTML = `
          <div class="error-container animated fadeIn">
            <div class="alert alert-danger border-0 shadow-sm" style="border-radius:12px; background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);">
              <div class="d-flex align-items-start">
                <div class="error-icon-wrapper mr-3" style="font-size:2rem; color:#dc2626;"><i class="${errorIcon}"></i></div>
                <div class="flex-grow-1">
                  <h5 class="alert-heading mb-2" style="color:#991b1b;">${errorTitle}</h5>
                  <p class="mb-0" style="color:#7f1d1d;">${errorMessage}</p>
                  ${suggestionsHtml}
                  <details class="mt-3"><summary style="cursor:pointer; color:#991b1b; font-size:0.85rem;"><i class="fas fa-bug"></i> Technical details</summary><pre class="mt-2 p-2 bg-white rounded" style="font-size:0.75rem; color:#6b7280; max-height:100px; overflow-y:auto;">${error}</pre></details>
                </div>
              </div>
            </div>
            <div class="text-center mt-3">
              <button class="btn btn-lg" onclick="location.reload()" style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white; border-radius:25px; padding:12px 30px; border:none; box-shadow:0 4px 15px rgba(102,126,234,0.4);"> <i class="fas fa-redo mr-2"></i> Refresh & Try Again</button>
            </div>
          </div>
        `;
      }
      if (startButton) { startButton.innerHTML = '<i class="fas fa-brain"></i> Retry Analysis'; startButton.disabled = false; }
      if (statusCheckInterval) clearInterval(statusCheckInterval);
    }

    function showLoginPrompt() {
      const existing = document.getElementById('loginPromptModal');
      if (existing) existing.remove();
      const modalHtml = `
        <div class="modal fade" id="loginPromptModal" tabindex="-1" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content" style="border-radius:15px; border:none; box-shadow:0 10px 30px rgba(0,0,0,0.2);">
              <div class="modal-header" style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white; border-radius:15px 15px 0 0;">
                <h5 class="modal-title"><i class="fas fa-sign-in-alt mr-2"></i>Sign In Required</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" style="filter: brightness(0) invert(1); opacity: 0.8;"></button>
              </div>
              <div class="modal-body text-center" style="padding:2rem;">
                <div class="mb-3"><i class="fas fa-lock" style="font-size:3rem; color:#667eea; opacity:0.7;"></i></div>
                <h5 class="mb-3">Want to analyze more comments?</h5>
                <p class="text-muted mb-4">Sign in to queue analysis jobs and analyze up to 2,500 comments!</p>
                <div class="mb-3">
                  <div class="alert alert-info" style="border-radius: 10px;">
                    <strong>Free Account Benefits:</strong><br>
                    <small>✓ Analyze up to 2,500 comments<br>✓ Queue background jobs<br>✓ Save analysis history<br>✓ Export results</small>
                  </div>
                </div>
              </div>
              <div class="modal-footer" style="border-top:none; padding:0 2rem 2rem 2rem;">
                <a href="/login" class="btn btn-primary btn-lg" style="border-radius:25px; width:100%; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); border:none;"><i class="fas fa-sign-in-alt mr-2"></i>Sign In for Free Analysis</a>
                <div class="text-center mt-2"><small class="text-muted">Don't have an account? <a href="/register" class="text-primary">Create one free</a></small></div>
              </div>
            </div>
          </div>
        </div>`;
      document.body.insertAdjacentHTML('beforeend', modalHtml);
      if (window.bootstrap) {
        const modal = new window.bootstrap.Modal(document.getElementById('loginPromptModal'));
        modal.show();
      }
    }

    function showProUpgradePrompt() {
      const existing = document.getElementById('proUpgradePromptModal');
      if (existing) existing.remove();
      const modalHtml = `
        <div class="modal fade" id="proUpgradePromptModal" tabindex="-1" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content" style="border-radius:15px; border:none; box-shadow:0 10px 30px rgba(0,0,0,0.2);">
              <div class="modal-header" style="background:linear-gradient(135deg,#f59e0b 0%, #d97706 100%); color:white; border-radius:15px 15px 0 0;">
                <h5 class="modal-title"><i class="fas fa-crown mr-2"></i>Upgrade to Pro</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" style="filter: brightness(0) invert(1); opacity: 0.8;"></button>
              </div>
              <div class="modal-body text-center" style="padding:2rem;">
                <div class="mb-3"><i class="fas fa-star" style="font-size:3rem; color:#f59e0b;"></i></div>
                <h5 class="mb-3">Unlock Advanced Analysis</h5>
                <p class="text-muted mb-4">Upgrade to Pro to analyze up to 5,000 comments!</p>
                <div class="mb-3">
                  <div class="alert alert-warning" style="border-radius: 10px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: none;">
                    <strong>Pro Account Benefits:</strong><br>
                    <small style="color:#92400e;">✓ Analyze up to 5,000 comments<br>✓ Process entire videos<br>✓ Advanced filtering options<br>✓ Priority processing<br>✓ Detailed analytics reports</small>
                  </div>
                </div>
              </div>
              <div class="modal-footer" style="border-top:none; padding:0 2rem 2rem 2rem;">
                <a href="/subscribe" class="btn btn-warning btn-lg" style="border-radius:25px; width:100%; background:linear-gradient(135deg,#f59e0b 0%, #d97706 100%); border:none; color:white;"><i class="fas fa-crown mr-2"></i>Upgrade to Pro</a>
                <div class="text-center mt-2"><small class="text-muted"><a href="#" class="text-warning" data-bs-dismiss="modal">Maybe later</a></small></div>
              </div>
            </div>
          </div>
        </div>`;
      document.body.insertAdjacentHTML('beforeend', modalHtml);
      if (window.bootstrap) {
        const modal = new window.bootstrap.Modal(document.getElementById('proUpgradePromptModal'));
        modal.show();
      }
    }

    function capitalizeFirst(str) { return (str || '').charAt(0).toUpperCase() + (str || '').slice(1); }

    const loadingMessages = {
      fetching_comments: [
        'Reticulating comment splines...', 'Downloading hot takes from the cloud...', 'Harvesting fresh opinions...',
        'Summoning the comment spirits...', 'Deploying YouTube API ninjas...', 'Gathering digital discourse...',
        'Extracting text vibes from the matrix...'
      ],
      analyzing_sentiment: [
        'Calibrating emotional sensors...', 'Teaching AI about human feelings...', 'Decoding sentiment wavelengths...',
        'Consulting the vibe oracle...', 'Computing emotional algorithms...', 'Analyzing the mood spectrum...',
        'Processing digital emotions...', 'Calculating happiness quotients...', 'Measuring sentiment particles...'
      ],
      generating_summary: [
        'Crafting wisdom from chaos...', 'Distilling comment essence...', 'Generating insight crystals...',
        'Compiling the final verdict...', 'Preparing your custom report...', 'Assembling thought molecules...',
        'Weaving the narrative tapestry...'
      ],
    };

    const funFacts = [
      'Did you know? The average YouTube comment is 27 words long!',
      'Fun fact: 70% of YouTube comments are positive or neutral!',
      'YouTube gets over 500 hours of video uploaded every minute!',
      "The first YouTube comment ever was 'Interesting...' in 2005!",
      'Comments with emojis get 33% more engagement! 😊',
      'YouTube comments support over 75 languages worldwide!',
      'The most liked YouTube comment has over 4 million likes!',
      'Did you know? Comments peak within the first 2 hours of upload!',
      "YouTube's algorithm considers comment sentiment for recommendations!",
    ];

    // Cleanup on unmount
    return () => {
      window.submitFeedback = undefined;
      window.showLoginPrompt = undefined;
      window.showProUpgradePrompt = undefined;
      window.startSentimentAnalysis = undefined;
      if (statusCheckInterval) clearInterval(statusCheckInterval);
      if (messageRotationInterval) clearInterval(messageRotationInterval);
      if (factRotationInterval) clearInterval(factRotationInterval);
      if (progressAnimationFrame) cancelAnimationFrame(progressAnimationFrame);
      Object.values(charts).forEach(ch => { try { ch.destroy(); } catch {} });
    };
  } catch (err) {
    showFatalError('Failed to initialize the Analyze UI.', err);
  }
  }, []);

  // No visible React UI; we strictly orchestrate DOM interactions
  return null;
}

export function mountAnalyzeApp(mountId = 'react-analyze-root') {
  const node = document.getElementById(mountId);
  if (!node) return;
  const root = createRoot(node);
  root.render(<AnalyzeApp />);
}

// Auto-mount
if (typeof window !== 'undefined') {
  const doMount = () => {
    const defaultNode = document.getElementById('react-analyze-root');
    if (defaultNode) mountAnalyzeApp('react-analyze-root');
  };
  if (document.readyState === 'loading') window.addEventListener('DOMContentLoaded', doMount);
  else doMount();
}
