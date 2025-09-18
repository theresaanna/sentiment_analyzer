import React, { useEffect } from 'react';
import { createRoot } from 'react-dom/client';

// Analyze page script ported from inline JS to a React-managed module
// This file intentionally manipulates the DOM directly to work with existing Jinja markup.

function AnalyzeApp() {
  useEffect(() => {
    const rootEl = document.getElementById('react-analyze-root');
    if (!rootEl) return;

    // Parse server-provided context from data attributes
    const videoId = rootEl.getAttribute('data-video-id') || '';
    const isAuthenticated = (rootEl.getAttribute('data-is-auth') || 'false') === 'true';
    const isProUser = (rootEl.getAttribute('data-is-pro') || 'false') === 'true';
    const videoStatsComments = parseInt(rootEl.getAttribute('data-video-comments') || '0', 10) || 0;

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

    // Loading message rotation state
    let messageRotationInterval = null;
    let currentMessageIndex = 0;
    let factRotationInterval = null;
    let currentFactIndex = 0;
    let lastProgressValue = 0;
    let targetProgress = 0;
    let progressAnimationFrame = null;

    // Expose a few globals for inline onclicks we still generate in HTML strings
    // Keep the API surface similar to the original inline code
    window.submitFeedback = submitFeedback;
    window.showLoginPrompt = showLoginPrompt;
    window.showProUpgradePrompt = showProUpgradePrompt;
    window.startSentimentAnalysis = startSentimentAnalysis;

    // Make user flags globally accessible (referenced in logic)
    window.isAuthenticated = isAuthenticated;
    window.isProUser = isProUser;

    // Initialize totals
    const fetchedTopLevel = Number(commentStats?.top_level_count || 0);
    const totalTopLevel = Number(commentStats?.total_top_level_comments || commentStats?.total_available || 0);
    const totalAvailableComments = totalTopLevel || fetchedTopLevel || 5000;
    window.currentTotalComments = totalAvailableComments;

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
      if (updatedStats) updateCommentStatistics(updatedStats);
      const samplesSection = document.getElementById('sampleCommentsSection');
      if (samplesSection) samplesSection.style.display = 'block';
    }

    // Load user's previous feedback (to restore local corrections UI)
    (async () => { await loadUserFeedback(); })();

    // Hook up UI events
    const startButton = document.getElementById('startSentimentAnalysis');
    if (startButton) startButton.addEventListener('click', startSentimentAnalysis);

    const instantSlider = document.getElementById('instantSlider');
    const queueSlider = document.getElementById('queueSlider');
    const instantValue = document.getElementById('instantValue');
    const queueValue = document.getElementById('queueValue');
    const instantCoverage = document.getElementById('instantCoverage');
    const queueCoverage = document.getElementById('queueCoverage');
    const instantAnalyzeBtn = document.getElementById('instantAnalyzeBtn');
    const queueAnalyzeBtn = document.getElementById('queueAnalyzeBtn');

    configureSlidersForUser();
    if (instantSlider) {
      instantSlider.addEventListener('input', updateInstantSlider);
      instantSlider.addEventListener('change', updateInstantSlider);
      updateInstantSlider();
    }
    if (queueSlider) {
      queueSlider.addEventListener('input', updateQueueSlider);
      queueSlider.addEventListener('change', updateQueueSlider);
      updateQueueSlider();
    }

    const instantTab = document.getElementById('instant-tab');
    const queueTab = document.getElementById('queue-tab');
    if (instantTab) {
      instantTab.addEventListener('shown.bs.tab', () => {
        currentAnalysisMode = 'instant';
        const header = document.getElementById('analysisTypeHeader');
        if (header) header.textContent = 'Instant Analysis';
        updateInstantSlider();
      });
    }
    if (queueTab) {
      queueTab.addEventListener('shown.bs.tab', () => {
        currentAnalysisMode = 'queue';
        const header = document.getElementById('queueAnalysisHeader');
        if (header) header.textContent = 'Queue Analysis';
        updateQueueSlider();
      });
    }

    if (instantAnalyzeBtn) {
      instantAnalyzeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const value = parseInt((instantSlider && instantSlider.value) || '100', 10);
        startAnalysisWithMode('instant', value);
      });
    }
    if (queueAnalyzeBtn) {
      queueAnalyzeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const value = parseInt((queueSlider && queueSlider.value) || '1000', 10);
        startAnalysisWithMode('queue', value);
      });
    }

    function configureSlidersForUser() {
      const effectiveTotal = window.currentTotalComments || totalAvailableComments;
      if (instantSlider) {
        const instantMax = Math.min(500, effectiveTotal);
        instantSlider.max = String(instantMax);
        const maxLbl = document.getElementById('instantMax');
        if (maxLbl) maxLbl.textContent = String(instantMax);
        updateInstantSlider();
      }
      if (queueSlider && isAuthenticated) {
        const queueMax = Math.min(isProUser ? 5000 : 2500, effectiveTotal);
        queueSlider.max = String(queueMax);
        queueSlider.min = '1';
        if (queueMax < 100) {
          queueSlider.value = String(Math.min(queueMax, 10));
          queueSlider.step = '1';
        } else if (queueMax < 1000) {
          queueSlider.value = String(Math.min(100, queueMax));
          queueSlider.step = '10';
        } else {
          queueSlider.value = '1000';
          queueSlider.step = '10';
        }
        const queueMaxLabel = document.getElementById('queueMax');
        if (queueMaxLabel) {
          if (queueMax < 1000) queueMaxLabel.textContent = String(queueMax);
          else queueMaxLabel.textContent = `${(queueMax/1000).toFixed(1).replace('.0','')}k`;
        }
        updateQueueSlider();
      }
    }

    function updateInstantSlider() {
      if (!instantSlider) return;
      const value = parseInt(instantSlider.value || '0', 10);
      const effectiveTotal = window.currentTotalComments || totalAvailableComments;
      const percentage = Math.min(100, Math.round((value / effectiveTotal) * 100));
      if (instantValue) instantValue.textContent = String(value);
      if (instantCoverage) instantCoverage.textContent = `${percentage}%`;
      const timeEstimate = value <= 100 ? '~5s' : value <= 300 ? '~15s' : '~30s';
      const timeSpan = document.querySelector('#instant .analysis-stats .stat-item:nth-child(2) strong');
      if (timeSpan) timeSpan.textContent = timeEstimate;
    }

    function updateQueueSlider() {
      if (!queueSlider) return;
      const value = parseInt(queueSlider.value || '1', 10);
      const effectiveTotal = window.currentTotalComments || totalAvailableComments;
      const percentage = Math.min(100, Math.round((value / effectiveTotal) * 100));
      if (queueValue) queueValue.textContent = value < 1000 ? String(value) : value.toLocaleString();
      if (queueCoverage) queueCoverage.textContent = `${percentage}%`;
      const seconds = Math.round(value * 0.12);
      const timeSpan = document.querySelector('#queue .analysis-stats .stat-item:nth-child(2) strong');
      if (timeSpan) timeSpan.textContent = seconds < 60 ? `~${seconds}s` : `~${Math.round(seconds/60)} min`;
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
      if (analysisActionButton) { analysisActionButton.disabled = true; analysisActionButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...'; }
      section?.scrollIntoView({ behavior: 'smooth', block: 'start' });

      const selectedPercentage = Math.round((commentsToAnalyze / (window.currentTotalComments || 5000)) * 100);
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
      const progressBar = document.getElementById('progressBar');
      const progressText = document.getElementById('progressText');
      const progressStatus = document.getElementById('progressStatus');
      const progressSubStatus = document.getElementById('progressSubStatus');
      const progressDetail = document.getElementById('progressDetail');
      const funFactText = document.getElementById('funFactText');

      targetProgress = status.progress || 0;
      const animateProgress = () => {
        if (Math.abs(lastProgressValue - targetProgress) > 0.5) {
          lastProgressValue += (targetProgress - lastProgressValue) * 0.1;
          if (progressBar) progressBar.style.width = lastProgressValue + '%';
          if (progressText) progressText.textContent = String(Math.round(lastProgressValue)) + '%';
          progressAnimationFrame = requestAnimationFrame(animateProgress);
        } else {
          lastProgressValue = targetProgress;
          if (progressBar) progressBar.style.width = targetProgress + '%';
          if (progressText) progressText.textContent = String(Math.round(targetProgress)) + '%';
        }
      };
      if (progressAnimationFrame) cancelAnimationFrame(progressAnimationFrame);
      animateProgress();

      let mainStatus = 'Initializing vibe check...';
      let subStatus = '';
      let messagePool = [];

      switch (status.status) {
        case 'fetching_comments':
          mainStatus = 'Downloading Comments';
          subStatus = loadingMessages.fetching_comments[0];
          messagePool = loadingMessages.fetching_comments;
          if (progressDetail) progressDetail.textContent = `${status.current || 0} fetched`;
          break;
        case 'using_cached':
          mainStatus = 'Loading Cached Data';
          subStatus = 'Retrieving pre-analyzed vibes...';
          if (progressDetail) progressDetail.textContent = 'Fast mode activated';
          break;
        case 'analyzing_sentiment':
          mainStatus = 'Analyzing Sentiment';
          subStatus = loadingMessages.analyzing_sentiment[0];
          messagePool = loadingMessages.analyzing_sentiment;
          if (progressDetail) progressDetail.textContent = `${status.current || 0}/${status.total || 0} comments`;
          break;
        case 'generating_summary':
          mainStatus = 'Generating Insights';
          subStatus = loadingMessages.generating_summary[0];
          messagePool = loadingMessages.generating_summary;
          if (progressDetail) progressDetail.textContent = 'Almost there!';
          break;
        case 'completed':
          mainStatus = '✨ Analysis Complete!';
          subStatus = 'Your results are ready!';
          if (progressDetail) progressDetail.textContent = '';
          if (messageRotationInterval) clearInterval(messageRotationInterval);
          if (factRotationInterval) clearInterval(factRotationInterval);
          break;
      }
      if (progressStatus) progressStatus.textContent = mainStatus;
      if (progressSubStatus) progressSubStatus.textContent = subStatus;

      if (messagePool.length > 0 && status.status !== 'completed') {
        if (messageRotationInterval) clearInterval(messageRotationInterval);
        currentMessageIndex = 0;
        messageRotationInterval = setInterval(() => {
          currentMessageIndex = (currentMessageIndex + 1) % messagePool.length;
          if (progressSubStatus) {
            progressSubStatus.textContent = messagePool[currentMessageIndex];
            progressSubStatus.style.animation = 'none';
            setTimeout(() => { progressSubStatus.style.animation = 'fadeInOut 4s ease-in-out infinite'; }, 10);
          }
        }, 3000);
      }

      if (!factRotationInterval && status.status !== 'completed' && funFactText) {
        factRotationInterval = setInterval(() => {
          currentFactIndex = (currentFactIndex + 1) % funFacts.length;
          funFactText.style.opacity = '0';
          setTimeout(() => {
            funFactText.textContent = funFacts[currentFactIndex];
            funFactText.style.opacity = '1';
          }, 300);
        }, 5000);
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
      if (startButton) { startButton.innerHTML = '<i class="fas fa-sync"></i> Re-analyze'; startButton.disabled = false; }

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
        try { createSentimentPieChart(sentiment); } catch (e) { console.error('pie chart error', e); }
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

      try { displaySampleComments(sentiment.individual_results || []); } catch (e) { console.error('sample comments error', e); }

      if (results.updated_stats) updateCommentStatistics(results.updated_stats);
    }

    function createSentimentPieChart(sentiment) {
      const canvas = document.getElementById('sentimentPieChart');
      if (!canvas || !window.Chart) return;
      const ctx = canvas.getContext('2d');
      if (charts.pie) charts.pie.destroy();
      const counts = sentiment.sentiment_counts || sentiment.distribution || { positive: 0, neutral: 0, negative: 0 };
      charts.pie = new window.Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Positive', 'Neutral', 'Negative'],
          datasets: [{
            data: [counts.positive || 0, counts.neutral || 0, counts.negative || 0],
            backgroundColor: ['rgba(209,231,221,0.9)', 'rgba(206,212,218,0.9)', 'rgba(227,93,106,0.85)'],
            borderColor: ['rgba(25,135,84,1)', 'rgba(160,165,170,1)', 'rgba(176,42,55,1)'],
            borderWidth: 2,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const label = context.label || '';
                  const value = context.parsed || 0;
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                  return `${label}: ${value} (${percentage}%)`;
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

    function updateCommentStatistics(stats) {
      if (!stats) return;
      const headers = document.querySelectorAll('.card-header-vibe h3');
      const hdr = headers && headers[1];
      if (hdr && !hdr.querySelector('.updated-badge')) {
        const badge = document.createElement('span');
        badge.className = 'badge badge-success ml-2 updated-badge';
        badge.textContent = 'Updated';
        badge.style.fontSize = '0.6em';
        badge.style.verticalAlign = 'middle';
        badge.style.animation = 'fadeIn 0.5s';
        hdr.appendChild(badge);
      }
      const alertInfo = document.querySelector('.alert-info');
      if (alertInfo && stats.total_analyzed) {
        alertInfo.innerHTML = `
          <i class="fas fa-info-circle"></i>
          <strong>Analysis Updated:</strong> Analyzed <strong>${stats.total_analyzed}</strong> comments
          (<strong>${stats.analysis_depth_percentage}%</strong> of total available)<br>
          <small class="text-muted"><i class="fas fa-chart-line"></i> Statistics below reflect the expanded analysis dataset</small>
        `;
        alertInfo.classList.add('alert-success');
        alertInfo.classList.remove('alert-info');
      }
      const grid = document.querySelector('.comment-stats-grid');
      if (grid) {
        const u = grid.querySelector('.stat-item:nth-child(1) .stat-value'); if (u) u.textContent = String(stats.unique_commenters || 0);
        const a = grid.querySelector('.stat-item:nth-child(2) .stat-value'); if (a) a.textContent = String(stats.avg_comment_length || 0);
        const t = grid.querySelector('.stat-item:nth-child(3) .stat-value'); if (t) t.textContent = String(stats.top_level_count || 0);
        const r = grid.querySelector('.stat-item:nth-child(4) .stat-value'); if (r) r.textContent = String(stats.replies_count || 0);
      }
      if (stats.top_commenters && stats.top_commenters.length > 0) {
        const list = document.querySelector('.list-group-flush');
        if (list) {
          list.innerHTML = '';
          stats.top_commenters.forEach((c, idx) => {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.innerHTML = `<span><strong>#${idx + 1}</strong> ${c[0]}</span><span class="badge badge-primary badge-pill">${c[1]} comments</span>`;
            list.appendChild(li);
          });
        }
      }
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
