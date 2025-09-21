import React, { useState, useMemo, useCallback } from 'react';
import PropTypes from 'prop-types';
import { api } from '../../services/api';
import { useToast } from '../../hooks/useToast';

export function SampleComments({ comments, videoId }) {
  const [corrections, setCorrections] = useState({});
  const [submitting, setSubmitting] = useState({});
  const { showSuccess, showError } = useToast();

  // Group comments by sentiment
  const groupedComments = useMemo(() => {
    const groups = {
      positive: [],
      neutral: [],
      negative: []
    };

    comments.forEach(comment => {
      const sentiment = corrections[comment.id] || comment.predicted_sentiment || comment.sentiment || 'neutral';
      const item = {
        ...comment,
        currentSentiment: sentiment,
        confidence: typeof comment.confidence === 'number' 
          ? (comment.confidence > 1 ? comment.confidence : comment.confidence * 100)
          : 0
      };

      groups[sentiment].push(item);
    });

    // Sort by confidence
    Object.keys(groups).forEach(key => {
      groups[key].sort((a, b) => b.confidence - a.confidence);
    });

    return groups;
  }, [comments, corrections]);

  const handleSentimentCorrection = useCallback(async (commentId, originalSentiment, newSentiment) => {
    if (newSentiment === originalSentiment) return;

    setSubmitting(prev => ({ ...prev, [commentId]: true }));

    try {
      // Update local state immediately for better UX
      setCorrections(prev => ({ ...prev, [commentId]: newSentiment }));

      // Send to API
      await api.submitFeedback(videoId, commentId, originalSentiment, newSentiment);
      
      showSuccess('Thank you for your feedback!');
    } catch (error) {
      // Revert on error
      setCorrections(prev => {
        const newCorrections = { ...prev };
        delete newCorrections[commentId];
        return newCorrections;
      });
      
      showError('Failed to submit feedback. Please try again.');
      console.error('Feedback submission error:', error);
    } finally {
      setSubmitting(prev => {
        const newSubmitting = { ...prev };
        delete newSubmitting[commentId];
        return newSubmitting;
      });
    }
  }, [videoId, showSuccess, showError]);

  const truncateText = (text, maxLength = 300) => {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const renderCommentGroup = (sentiment, items, emoji, colorClass) => {
    const maxDisplay = 10;
    const displayItems = items.slice(0, maxDisplay);

    return (
      <div className="sentiment-section mb-4">
        <div className={`sentiment-header-section sentiment-${sentiment}`}>
          <h5 className="d-flex justify-content-between align-items-center mb-0">
            <span>
              {emoji} {sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}
            </span>
            <span className="badge bg-primary">{items.length}</span>
          </h5>
        </div>
        
        <div className="comment-samples-container">
          {displayItems.length === 0 ? (
            <p className="text-muted text-center py-3">No {sentiment} comments found</p>
          ) : (
            <>
              {displayItems.map((item, index) => (
                <div 
                  key={item.id || `${sentiment}-${index}`}
                  className={`comment-sample ${sentiment} ${corrections[item.id] ? 'manually-corrected' : ''}`}
                >
                  {corrections[item.id] && (
                    <div className="manual-correction-badge">
                      <i className="fas fa-user-check"></i> Manually Corrected
                    </div>
                  )}
                  
                  <div className="comment-text">
                    {truncateText(item.text)}
                  </div>
                  
                  <div className="comment-meta">
                    <span className="text-muted">
                      <i className="fas fa-user-circle me-1"></i>
                      {item.author || 'Anonymous'}
                    </span>
                    <span className="confidence-badge">
                      {item.confidence.toFixed(1)}% confidence
                    </span>
                  </div>
                  
                  <div className="feedback-buttons mt-2">
                    <span className="text-muted small me-2">Correct sentiment:</span>
                    <button 
                      className={`btn btn-sm ${item.currentSentiment === 'positive' ? 'btn-success' : 'btn-outline-success'} me-1`}
                      onClick={() => handleSentimentCorrection(item.id, item.currentSentiment, 'positive')}
                      disabled={submitting[item.id] || item.currentSentiment === 'positive'}
                    >
                      <i className="fas fa-smile"></i> Positive
                    </button>
                    <button 
                      className={`btn btn-sm ${item.currentSentiment === 'neutral' ? 'btn-secondary' : 'btn-outline-secondary'} me-1`}
                      onClick={() => handleSentimentCorrection(item.id, item.currentSentiment, 'neutral')}
                      disabled={submitting[item.id] || item.currentSentiment === 'neutral'}
                    >
                      <i className="fas fa-meh"></i> Neutral
                    </button>
                    <button 
                      className={`btn btn-sm ${item.currentSentiment === 'negative' ? 'btn-danger' : 'btn-outline-danger'}`}
                      onClick={() => handleSentimentCorrection(item.id, item.currentSentiment, 'negative')}
                      disabled={submitting[item.id] || item.currentSentiment === 'negative'}
                    >
                      <i className="fas fa-frown"></i> Negative
                    </button>
                    {submitting[item.id] && (
                      <span className="spinner-border spinner-border-sm ms-2" role="status">
                        <span className="visually-hidden">Submitting...</span>
                      </span>
                    )}
                  </div>
                </div>
              ))}
              
              {items.length > maxDisplay && (
                <div className="text-center text-muted py-2">
                  <small>
                    <i className="fas fa-info-circle"></i> Showing {maxDisplay} of {items.length} {sentiment} comments
                  </small>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  };

  if (!comments || comments.length === 0) {
    return null;
  }

  return (
    <div className="vibe-card mb-4">
      <div className="card-header-vibe">
        <h3 className="mb-0">
          <span className="emoji-icon">💬</span> Sample Comments by Sentiment
        </h3>
      </div>
      <div className="card-body">
        {renderCommentGroup('positive', groupedComments.positive, '😊', 'success')}
        {renderCommentGroup('neutral', groupedComments.neutral, '😐', 'secondary')}
        {renderCommentGroup('negative', groupedComments.negative, '😔', 'danger')}
        
        <div className="feedback-notice mt-3">
          <i className="fas fa-robot me-2"></i>
          Your feedback helps us improve our AI models. Click the sentiment buttons to correct any misclassifications.
        </div>
      </div>
    </div>
  );
}

SampleComments.propTypes = {
  comments: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string,
    text: PropTypes.string,
    author: PropTypes.string,
    sentiment: PropTypes.string,
    predicted_sentiment: PropTypes.string,
    confidence: PropTypes.number
  })),
  videoId: PropTypes.string.isRequired
};

SampleComments.defaultProps = {
  comments: []
};

export default SampleComments;