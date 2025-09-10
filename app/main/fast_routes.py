"""
Fast API routes optimized for speed and performance.

This module provides high-performance API endpoints that use:
- Async YouTube API calls
- Batch sentiment analysis
- Intelligent caching
- Concurrent processing
"""
import os
import asyncio
import threading
import time
from flask import jsonify, request
from app.main import bp
from app.cache import cache
from app.science.fast_sentiment_analyzer import get_fast_analyzer
from app.services.async_youtube_service import get_video_and_comments_fast
from app.services.enhanced_youtube_service import fetch_maximum_comments_async
import logging

logger = logging.getLogger(__name__)


@bp.route('/api/analyze/fast/<video_id>', methods=['POST'])
def api_fast_analyze_sentiment(video_id):
    """
    Fast sentiment analysis endpoint using optimized processing.
    
    This endpoint provides significantly faster sentiment analysis by using:
    - Async YouTube API calls
    - Batch processing for sentiment analysis
    - Concurrent processing
    - Intelligent caching
    """
    try:
        # Get analysis parameters with higher defaults
        data = request.get_json() or {}
        max_comments = data.get('max_comments', 1000)  # Higher default for better analysis
        use_enhanced = data.get('use_enhanced', True)  # Use enhanced service by default
        
        # Create unique analysis ID for fast processing
        analysis_id = f"fast_sentiment_{video_id}_{max_comments}"
        
        # Check if analysis already exists in cache
        cached_result = cache.get('fast_sentiment_analysis', analysis_id)
        if cached_result:
            return jsonify({
                'success': True,
                'analysis_id': analysis_id,
                'status': 'completed',
                'cached': True,
                'results': cached_result
            })
        
        # Set initial status
        cache.set('fast_analysis_status', analysis_id, {
            'status': 'started', 
            'progress': 0,
            'message': 'Starting fast analysis...'
        }, ttl_hours=1)
        
        # Start fast analysis in background thread
        thread = threading.Thread(
            target=run_fast_sentiment_analysis,
            args=(video_id, max_comments, analysis_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'status': 'started',
            'message': 'Fast sentiment analysis started',
            'estimated_time': f"{max_comments * 0.02:.1f}s"  # Rough estimate
        })
        
    except Exception as e:
        logger.error(f"Error starting fast analysis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def run_fast_sentiment_analysis(video_id: str, max_comments: int, analysis_id: str):
    """
    Run fast sentiment analysis using async services and batch processing.
    """
    start_time = time.time()
    
    try:
        # Update status
        cache.set('fast_analysis_status', analysis_id, {
            'status': 'fetching_data', 
            'progress': 10,
            'message': 'Fetching video and comments concurrently...'
        }, ttl_hours=1)
        
        # Use async function in thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Use enhanced service for maximum comment retrieval
            data = loop.run_until_complete(
                fetch_maximum_comments_async(video_id, max_comments)
            )
        finally:
            loop.close()
        
        video_info = data['video']
        comments = data['comments']
        
        # Update status
        cache.set('fast_analysis_status', analysis_id, {
            'status': 'analyzing_sentiment', 
            'progress': 40,
            'message': f'Analyzing {len(comments)} comments with batch processing...',
            'comments_fetched': len(comments)
        }, ttl_hours=1)
        
        # Initialize fast analyzer
        analyzer = get_fast_analyzer()
        
        # Progress callback for sentiment analysis
        def progress_callback(current, total):
            progress = 40 + int((current / total) * 45)  # 40-85% for sentiment analysis
            cache.set('fast_analysis_status', analysis_id, {
                'status': 'analyzing_sentiment',
                'progress': progress,
                'message': f'Processing batch {current}/{total}...',
                'current': current,
                'total': total
            }, ttl_hours=1)
        
        # Extract comment texts
        comment_texts = [comment['text'] for comment in comments]
        
        # Run fast batch sentiment analysis
        sentiment_results = analyzer.analyze_batch_fast(
            comment_texts,
            progress_callback=progress_callback
        )
        
        # Update status
        cache.set('fast_analysis_status', analysis_id, {
            'status': 'finalizing', 
            'progress': 90,
            'message': 'Finalizing results...'
        }, ttl_hours=1)
        
        # Get top positive and negative comments
        top_comments = get_top_sentiment_comments(comments, sentiment_results['individual_results'])
        
        # Calculate processing metrics
        processing_time = time.time() - start_time
        throughput = len(comments) / processing_time if processing_time > 0 else 0
        
        # Prepare final results
        results = {
            'video_id': video_id,
            'analysis_id': analysis_id,
            'video_info': video_info,
            'sentiment': sentiment_results,
            'top_comments': top_comments,
            'performance_metrics': {
                'total_processing_time': processing_time,
                'comments_processed': len(comments),
                'throughput_comments_per_second': throughput,
                'model_info': sentiment_results.get('model_info', {}),
                'optimization_used': 'fast_batch_processing'
            },
            'timestamp': time.time()
        }
        
        # Cache results for 6 hours (shorter due to speed)
        cache.set('fast_sentiment_analysis', analysis_id, results, ttl_hours=6)
        
        # Update status to completed
        cache.set('fast_analysis_status', analysis_id, {
            'status': 'completed', 
            'progress': 100,
            'message': f'Analysis completed in {processing_time:.2f}s',
            'processing_time': processing_time,
            'throughput': throughput
        }, ttl_hours=1)
        
        logger.info(f"Fast sentiment analysis completed for {video_id}: "
                   f"{len(comments)} comments in {processing_time:.2f}s "
                   f"({throughput:.1f} comments/sec)")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Fast sentiment analysis failed for {video_id}: {error_msg}")
        
        # Update status to error
        cache.set('fast_analysis_status', analysis_id, {
            'status': 'error',
            'progress': 0,
            'error': error_msg,
            'message': f'Analysis failed: {error_msg}'
        }, ttl_hours=1)


def get_top_sentiment_comments(comments: list, sentiment_results: list, top_n: int = 5) -> dict:
    """
    Get top positive and negative comments based on sentiment analysis.
    
    Args:
        comments: List of comment dictionaries
        sentiment_results: List of sentiment analysis results
        top_n: Number of top comments to return for each sentiment
        
    Returns:
        Dictionary with top positive and negative comments
    """
    if len(comments) != len(sentiment_results):
        return {'positive': [], 'negative': [], 'error': 'Mismatched comment and result counts'}
    
    # Combine comments with their sentiment results
    combined = []
    for comment, result in zip(comments, sentiment_results):
        if result['predicted_sentiment'] in ['positive', 'negative']:
            combined.append({
                'comment': comment,
                'sentiment': result['predicted_sentiment'],
                'confidence': result['confidence'],
                'sentiment_scores': result['sentiment_scores']
            })
    
    # Sort by confidence and get top comments for each sentiment
    positive_comments = [c for c in combined if c['sentiment'] == 'positive']
    negative_comments = [c for c in combined if c['sentiment'] == 'negative']
    
    positive_comments.sort(key=lambda x: x['confidence'], reverse=True)
    negative_comments.sort(key=lambda x: x['confidence'], reverse=True)
    
    return {
        'positive': positive_comments[:top_n],
        'negative': negative_comments[:top_n],
        'total_positive': len(positive_comments),
        'total_negative': len(negative_comments)
    }


@bp.route('/api/analyze/fast/status/<analysis_id>')
def api_fast_analysis_status(analysis_id):
    """Get the status of a fast sentiment analysis job."""
    try:
        status = cache.get('fast_analysis_status', analysis_id)
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/analyze/fast/results/<analysis_id>')
def api_fast_analysis_results(analysis_id):
    """Get the results of a completed fast sentiment analysis."""
    try:
        # Check if analysis is complete
        status = cache.get('fast_analysis_status', analysis_id)
        if not status:
            return jsonify({
                'success': False,
                'error': 'Analysis not found'
            }), 404
        
        if status.get('status') != 'completed':
            return jsonify({
                'success': False,
                'error': 'Analysis not yet completed',
                'status': status
            }), 202
        
        # Get results
        results = cache.get('fast_sentiment_analysis', analysis_id)
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/test/fast-analyzer')
def api_test_fast_analyzer():
    """Test endpoint to verify fast analyzer is working."""
    try:
        analyzer = get_fast_analyzer()
        
        test_texts = [
            "This is amazing! Love it!",
            "I hate this so much",
            "This is okay, nothing special",
            "Best video ever, thanks for sharing!",
            "Terrible content, waste of time"
        ]
        
        start_time = time.time()
        results = analyzer.analyze_batch_fast(test_texts)
        processing_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'test_results': {
                'processing_time': processing_time,
                'throughput': len(test_texts) / processing_time,
                'sentiment_summary': {
                    'total_analyzed': results['total_analyzed'],
                    'sentiment_counts': results['sentiment_counts'],
                    'overall_sentiment': results['overall_sentiment'],
                    'average_confidence': results['average_confidence']
                },
                'model_info': results.get('model_info', {})
            },
            'message': f'Fast analyzer test completed in {processing_time:.3f}s'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/compare/speed/<video_id>', methods=['POST'])
def api_compare_analysis_speed(video_id):
    """
    Compare the speed of fast vs regular sentiment analysis.
    """
    try:
        data = request.get_json() or {}
        max_comments = data.get('max_comments', 20)  # Keep it small for comparison
        
        results = {
            'video_id': video_id,
            'max_comments': max_comments,
            'fast_analysis': None,
            'regular_analysis': None,
            'speed_improvement': None
        }
        
        # Run fast analysis
        try:
            start_time = time.time()
            
            # Get comments with async service
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                data_result = loop.run_until_complete(
                    get_video_and_comments_fast(video_id, max_comments)
                )
            finally:
                loop.close()
            
            comments = data_result['comments']
            comment_texts = [c['text'] for c in comments]
            
            # Fast sentiment analysis
            analyzer = get_fast_analyzer()
            fast_results = analyzer.analyze_batch_fast(comment_texts)
            
            fast_time = time.time() - start_time
            
            results['fast_analysis'] = {
                'processing_time': fast_time,
                'throughput': len(comments) / fast_time if fast_time > 0 else 0,
                'comments_processed': len(comments),
                'sentiment_summary': {
                    'overall_sentiment': fast_results['overall_sentiment'],
                    'sentiment_score': fast_results['sentiment_score'],
                    'average_confidence': fast_results['average_confidence']
                }
            }
            
        except Exception as e:
            results['fast_analysis'] = {'error': str(e)}
        
        # Run regular analysis for comparison (import here to avoid circular imports)
        try:
            from app.science import SentimentAnalyzer
            from app.services import YouTubeService
            
            start_time = time.time()
            
            youtube_service = YouTubeService()
            comments_regular = youtube_service.get_all_comments_flat(video_id, max_comments)
            
            analyzer_regular = SentimentAnalyzer()
            regular_results = analyzer_regular.analyze_batch([c['text'] for c in comments_regular])
            
            regular_time = time.time() - start_time
            
            results['regular_analysis'] = {
                'processing_time': regular_time,
                'throughput': len(comments_regular) / regular_time if regular_time > 0 else 0,
                'comments_processed': len(comments_regular),
                'sentiment_summary': {
                    'overall_sentiment': regular_results['overall_sentiment'],
                    'sentiment_score': regular_results['sentiment_score'],
                    'average_confidence': regular_results['average_confidence']
                }
            }
            
            # Calculate speed improvement
            if results['fast_analysis'] and 'processing_time' in results['fast_analysis']:
                speed_improvement = regular_time / fast_time if fast_time > 0 else float('inf')
                results['speed_improvement'] = {
                    'factor': speed_improvement,
                    'time_saved': regular_time - fast_time,
                    'percentage_faster': ((regular_time - fast_time) / regular_time * 100) if regular_time > 0 else 0
                }
            
        except Exception as e:
            results['regular_analysis'] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'comparison': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
