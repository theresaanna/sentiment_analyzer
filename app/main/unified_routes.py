"""
Unified API Routes for Sentiment Analysis

This module provides unified API endpoints that use the UnifiedSentimentAnalyzer
for consistent sentiment analysis with feedback integration.
"""

import logging
import threading
from flask import jsonify, request
from app.main import bp
# Lazy import heavy analyzers/services inside endpoints to speed startup
# from app.ml.unified_sentiment_analyzer import get_unified_analyzer
# from app.services.enhanced_youtube_service import EnhancedYouTubeService
from app.cache import cache
import time

logger = logging.getLogger(__name__)


@bp.route('/api/unified/analyze/<video_id>', methods=['POST'])
def api_unified_analyze_video(video_id):
    """
    Unified sentiment analysis endpoint for YouTube videos.
    
    This endpoint uses the unified analyzer with ensemble methods
    and feedback collection capabilities.
    """
    try:
        # Get request parameters
        data = request.get_json() or {}
        max_comments = data.get('max_comments', 1000)
        analysis_method = data.get('method', 'auto')  # auto, ensemble, roberta, fast, ml
        enable_feedback = data.get('enable_feedback', True)
        use_cache = data.get('use_cache', True)
        
        # Create analysis ID
        analysis_id = f"unified_{video_id}_{max_comments}_{analysis_method}"
        
        # Check cache first
        if use_cache:
            cached_result = cache.get('unified_analysis', analysis_id)
            if cached_result:
                return jsonify({
                    'success': True,
                    'analysis_id': analysis_id,
                    'cached': True,
                    'results': cached_result
                })
        
        # Set initial status
        cache.set('unified_analysis_status', analysis_id, {
            'status': 'started',
            'progress': 0,
            'message': 'Initializing unified analysis...'
        }, ttl_hours=1)
        
        # Start analysis in background
        thread = threading.Thread(
            target=run_unified_analysis,
            args=(video_id, max_comments, analysis_method, enable_feedback, analysis_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'status': 'started',
            'message': 'Unified sentiment analysis started',
            'method': analysis_method,
            'feedback_enabled': enable_feedback
        })
        
    except Exception as e:
        logger.error(f"Error starting unified analysis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/unified/analyze', methods=['POST'])
def api_unified_analyze():
    """Unified sentiment analysis for text."""
    try:
        data = request.get_json()
        text = data.get('text')
        if not text:
            return jsonify({'success': False, 'error': 'Text required'}), 400
        
        # Call external ML service on Modal
        from app.services.ml_service_client import MLServiceClient
        client = MLServiceClient()
        result = client.analyze_text(text)
        
        return jsonify({
            'success': True,
            'sentiment': result.get('predicted_sentiment', 'neutral'),
            'confidence': result.get('confidence', 0.5),
            'models_used': result.get('models_used', ['distilbert'])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/unified/batch', methods=['POST'])
def api_unified_batch():
    """Unified batch sentiment analysis."""
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        if not texts:
            return jsonify({'success': False, 'error': 'Texts required'}), 400
        
        # Call external ML service on Modal for batch analysis
        from app.services.ml_service_client import MLServiceClient
        client = MLServiceClient()
        results = client.analyze_batch(texts)
        
        # Normalize response for client
        return jsonify({
            'success': True,
            'total': results.get('total_analyzed', len(texts)),
            'results': results.get('results', [])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def run_unified_analysis(video_id: str, max_comments: int, method: str, 
                         enable_feedback: bool, analysis_id: str):
    """
    Run unified sentiment analysis in background.
    
    Args:
        video_id: YouTube video ID
        max_comments: Maximum comments to analyze
        method: Analysis method
        enable_feedback: Whether to enable feedback collection
        analysis_id: Unique analysis identifier
    """
    start_time = time.time()
    
    try:
        # Update status
        cache.set('unified_analysis_status', analysis_id, {
            'status': 'fetching_comments',
            'progress': 10,
            'message': f'Fetching up to {max_comments} comments...'
        }, ttl_hours=1)
        
        # Initialize services
        from app.services.enhanced_youtube_service import EnhancedYouTubeService
        youtube_service = EnhancedYouTubeService()
        
        # Fetch comments using enhanced service
        result = youtube_service.get_all_available_comments(
            video_id=video_id,
            target_comments=max_comments,
            include_replies=True,
            sort_order='relevance'
        )
        
        video_info = result['video']
        comments = result['comments']
        fetch_stats = result['statistics']
        
        # Update status
        cache.set('unified_analysis_status', analysis_id, {
            'status': 'analyzing_sentiment',
            'progress': 40,
            'message': f'Analyzing {len(comments)} comments using {method} method...',
            'comments_fetched': len(comments)
        }, ttl_hours=1)
        
        # Extract comment texts and prepare context
        comment_data = []
        for comment in comments:
            comment_data.append({
                'text': comment['text'],
                'context': {
                    'video_id': video_id,
                    'comment_id': comment.get('id', ''),
                    'author': comment.get('author', ''),
                    'likes': comment.get('likes', 0),
                    'is_reply': comment.get('is_reply', False)
                }
            })
        
        # Perform batch analysis via external ML service on Modal
        texts = [c['text'] for c in comment_data]
        from app.services.ml_service_client import MLServiceClient
        client = MLServiceClient()
        batch_results = client.analyze_batch(texts, method=method)
        
        # Add context to results
        for i, result in enumerate(batch_results.get('results', [])):
            if i < len(comment_data):
                result['context'] = comment_data[i]['context']
                # Enable feedback for each result (flag only)
                if enable_feedback:
                    result['feedback_enabled'] = True
        
        # Update status
        cache.set('unified_analysis_status', analysis_id, {
            'status': 'generating_insights',
            'progress': 85,
            'message': 'Generating insights and statistics...'
        }, ttl_hours=1)
        
        # Generate comprehensive insights
        insights = generate_insights(batch_results, video_info, fetch_stats)
        
        # Calculate performance metrics
        processing_time = time.time() - start_time
        
        # Prepare final results
        final_results = {
            'video_id': video_id,
            'analysis_id': analysis_id,
            'video_info': video_info,
            'fetch_statistics': fetch_stats,
            'sentiment_analysis': batch_results,
            'insights': insights,
            'performance': {
                'total_processing_time': processing_time,
                'comments_analyzed': len(comments),
                'throughput': len(comments) / processing_time if processing_time > 0 else 0,
                'method_used': method,
                'feedback_enabled': enable_feedback
            },
            'timestamp': time.time()
        }
        
        # Cache results
        cache.set('unified_analysis', analysis_id, final_results, ttl_hours=12)
        
        # Update status to completed
        cache.set('unified_analysis_status', analysis_id, {
            'status': 'completed',
            'progress': 100,
            'message': f'Analysis completed in {processing_time:.2f}s',
            'processing_time': processing_time
        }, ttl_hours=1)
        
        logger.info(f"Unified analysis completed for {video_id}: "
                   f"{len(comments)} comments in {processing_time:.2f}s")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unified analysis failed for {video_id}: {error_msg}")
        
        # Update status to error
        cache.set('unified_analysis_status', analysis_id, {
            'status': 'error',
            'progress': 0,
            'error': error_msg,
            'message': f'Analysis failed: {error_msg}'
        }, ttl_hours=1)


def generate_insights(batch_results: dict, video_info: dict, fetch_stats: dict) -> dict:
    """
    Generate comprehensive insights from analysis results.
    
    Args:
        batch_results: Batch sentiment analysis results
        video_info: Video metadata
        fetch_stats: Comment fetching statistics
        
    Returns:
        Dictionary of insights
    """
    stats = batch_results.get('statistics', {})
    results = batch_results.get('results', [])
    
    # Calculate sentiment trends
    positive_comments = [r for r in results if r.get('predicted_sentiment') == 'positive']
    negative_comments = [r for r in results if r.get('predicted_sentiment') == 'negative']
    
    # Find most confident predictions
    high_confidence = sorted(results, key=lambda x: x.get('confidence', 0), reverse=True)[:5]
    low_confidence = sorted(results, key=lambda x: x.get('confidence', 0))[:5]
    
    # Calculate engagement correlation
    engaged_comments = [r for r in results if r.get('context', {}).get('likes', 0) > 0]
    engaged_sentiment = {}
    if engaged_comments:
        for comment in engaged_comments:
            sentiment = comment.get('predicted_sentiment', 'neutral')
            engaged_sentiment[sentiment] = engaged_sentiment.get(sentiment, 0) + 1
    
    return {
        'summary': {
            'dominant_sentiment': max(stats.get('sentiment_distribution', {}), 
                                    key=stats.get('sentiment_distribution', {}).get)
                                    if stats.get('sentiment_distribution') else 'neutral',
            'sentiment_score': calculate_sentiment_score(stats.get('sentiment_distribution', {})),
            'confidence_level': 'high' if stats.get('average_confidence', 0) > 0.7 else 
                              'medium' if stats.get('average_confidence', 0) > 0.5 else 'low',
            'agreement_level': 'strong' if stats.get('average_agreement', 0) > 0.8 else
                             'moderate' if stats.get('average_agreement', 0) > 0.6 else 'weak'
        },
        'coverage': {
            'comments_analyzed': len(results),
            'total_available': fetch_stats.get('total_comments_available', 0),
            'coverage_percentage': fetch_stats.get('fetch_percentage', 0),
            'fetch_time': fetch_stats.get('fetch_time_seconds', 0)
        },
        'confidence_analysis': {
            'average': stats.get('average_confidence', 0),
            'std_dev': stats.get('confidence_std', 0),
            'high_confidence_ratio': stats.get('high_confidence_count', 0) / len(results) 
                                    if results else 0,
            'low_confidence_ratio': stats.get('low_confidence_count', 0) / len(results)
                                   if results else 0
        },
        'engagement_correlation': engaged_sentiment,
        'top_sentiments': {
            'most_positive': [{'text': c.get('text', ''), 
                             'confidence': c.get('confidence', 0)}
                            for c in positive_comments[:3]],
            'most_negative': [{'text': c.get('text', ''),
                             'confidence': c.get('confidence', 0)}
                            for c in negative_comments[:3]],
            'most_confident': [{'text': c.get('text', ''),
                              'sentiment': c.get('predicted_sentiment', ''),
                              'confidence': c.get('confidence', 0)}
                             for c in high_confidence],
            'least_confident': [{'text': c.get('text', ''),
                               'sentiment': c.get('predicted_sentiment', ''),
                               'confidence': c.get('confidence', 0)}
                              for c in low_confidence]
        }
    }


def calculate_sentiment_score(distribution: dict) -> float:
    """
    Calculate overall sentiment score from distribution.
    
    Args:
        distribution: Sentiment count distribution
        
    Returns:
        Score from -1 (very negative) to 1 (very positive)
    """
    total = sum(distribution.values())
    if total == 0:
        return 0
    
    positive = distribution.get('positive', 0)
    negative = distribution.get('negative', 0)
    
    return (positive - negative) / total


@bp.route('/api/unified/feedback', methods=['POST'])
def api_submit_feedback():
    """
    Submit feedback for a sentiment analysis.
    
    This endpoint allows users to correct sentiment predictions,
    which are then used to improve the models.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Extract feedback data
        analysis_id = data.get('analysis_id')
        correct_sentiment = data.get('correct_sentiment')
        confidence = data.get('confidence', 4)
        notes = data.get('notes', '')
        
        # Validate required fields
        if not analysis_id or not correct_sentiment:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: analysis_id and correct_sentiment'
            }), 400
        
        # Validate sentiment value
        valid_sentiments = ['positive', 'neutral', 'negative']
        if correct_sentiment not in valid_sentiments:
            return jsonify({
                'success': False,
                'error': f'Invalid sentiment. Must be one of: {valid_sentiments}'
            }), 400
        
        # Get analyzer and submit feedback
        analyzer = get_unified_analyzer()
        success = analyzer.collect_user_feedback(
            analysis_id=analysis_id,
            correct_sentiment=correct_sentiment,
            confidence=confidence,
            notes=notes
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Feedback collected successfully',
                'analysis_id': analysis_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to collect feedback'
            }), 500
            
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/unified/retrain', methods=['POST'])
def api_retrain_model():
    """
    Manually trigger model retraining with collected feedback.
    
    This endpoint allows administrators to retrain the ML models
    using the feedback collected from users.
    """
    try:
        data = request.get_json() or {}
        algorithm = data.get('algorithm', 'logistic_regression')
        
        # Get analyzer and trigger retraining
        analyzer = get_unified_analyzer()
        result = analyzer.retrain_with_feedback(algorithm=algorithm)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Model retrained successfully',
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Retraining failed')
            }), 500
            
    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/unified/performance', methods=['GET'])
def api_get_performance():
    """
    Get performance report for the unified analyzer.
    
    This endpoint returns comprehensive performance metrics
    and statistics for the unified sentiment analyzer.
    """
    try:
        analyzer = get_unified_analyzer()
        report = analyzer.get_performance_report()
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Error getting performance report: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/unified/weights', methods=['POST'])
def api_update_weights():
    """
    Update model weights for ensemble voting.
    
    This endpoint allows fine-tuning the weights used in
    ensemble sentiment analysis.
    """
    try:
        data = request.get_json()
        
        if not data or 'weights' not in data:
            return jsonify({
                'success': False,
                'error': 'No weights provided'
            }), 400
        
        weights = data['weights']
        
        # Validate weights
        valid_models = ['roberta', 'fast', 'ml']
        for model in weights.keys():
            if model not in valid_models:
                return jsonify({
                    'success': False,
                    'error': f'Invalid model: {model}. Must be one of: {valid_models}'
                }), 400
        
        # Update weights
        analyzer = get_unified_analyzer()
        analyzer.update_model_weights(weights)
        
        return jsonify({
            'success': True,
            'message': 'Model weights updated successfully',
            'new_weights': analyzer.model_weights
        })
        
    except Exception as e:
        logger.error(f"Error updating weights: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/unified/status/<analysis_id>', methods=['GET'])
def api_get_analysis_status(analysis_id):
    """
    Get status of a running analysis.
    
    Args:
        analysis_id: Unique analysis identifier
        
    Returns:
        Current status and progress
    """
    try:
        status = cache.get('unified_analysis_status', analysis_id)
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'Analysis not found'
            }), 404
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/unified/results/<analysis_id>', methods=['GET'])
def api_get_analysis_results(analysis_id):
    """
    Get results of a completed analysis.
    
    Args:
        analysis_id: Unique analysis identifier
        
    Returns:
        Analysis results if available
    """
    try:
        results = cache.get('unified_analysis', analysis_id)
        
        if not results:
            return jsonify({
                'success': False,
                'error': 'Results not found'
            }), 404
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
