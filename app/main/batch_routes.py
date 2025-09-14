"""
Batch processing routes for handling multiple videos or large datasets.
"""
from flask import jsonify, request
from app.main import bp
# Lazy import heavy modules in functions to speed startup
# from app.ml.batch_processor import BatchInferenceOptimizer, BatchConfig
# from app.services.enhanced_youtube_service import EnhancedYouTubeService
import logging
import threading
import time

logger = logging.getLogger(__name__)


@bp.route('/api/batch/analyze', methods=['POST'])
def batch_analyze_videos():
    """
    Analyze multiple YouTube videos in an optimized batch.
    
    Request body:
    {
        "video_ids": ["video_id1", "video_id2", ...],
        "max_comments_per_video": 100,
        "batch_size": 32,
        "use_dynamic_batching": true
    }
    """
    try:
        data = request.get_json()
        video_ids = data.get('video_ids', [])
        max_comments = data.get('max_comments_per_video', 100)
        batch_size = data.get('batch_size', 32)
        use_dynamic = data.get('use_dynamic_batching', True)
        
        if not video_ids:
            return jsonify({'error': 'No video IDs provided'}), 400
        
        # Create batch analysis ID
        batch_id = f"batch_{len(video_ids)}_{int(time.time())}"
        
        # Start batch processing in background
        thread = threading.Thread(
            target=process_video_batch,
            args=(video_ids, max_comments, batch_size, use_dynamic, batch_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'video_count': len(video_ids),
            'status': 'started',
            'estimated_time': f"{len(video_ids) * max_comments * 0.01:.1f}s"
        })
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        return jsonify({'error': str(e)}), 500


def process_video_batch(video_ids, max_comments, batch_size, use_dynamic, batch_id):
    """
    Process a batch of videos with optimized inference.
    """
    from app.cache import cache
    
    try:
        # Initialize services
        from app.services.enhanced_youtube_service import EnhancedYouTubeService
        youtube_service = EnhancedYouTubeService()
        from app.ml.unified_sentiment_analyzer import get_unified_analyzer
        analyzer = get_unified_analyzer()
        
        # Configure batch processing
        from app.ml.batch_processor import BatchInferenceOptimizer, BatchConfig
        config = BatchConfig(
            optimal_batch_size=batch_size,
            enable_dynamic_batching=use_dynamic,
            max_batch_size=128,
            enable_gpu_optimization=True
        )
        
        optimizer = BatchInferenceOptimizer(analyzer, config)
        
        # Collect all comments
        all_comments = []
        video_mapping = {}
        
        for idx, video_id in enumerate(video_ids):
            # Update status
            cache.set('batch_status', batch_id, {
                'status': 'fetching',
                'current_video': idx + 1,
                'total_videos': len(video_ids),
                'message': f'Fetching comments for video {idx + 1}/{len(video_ids)}'
            }, ttl_hours=1)
            
            # Fetch comments
            result = youtube_service.get_all_available_comments(
                video_id=video_id,
                target_comments=max_comments
            )
            
            comments = result['comments']
            for comment in comments:
                all_comments.append(comment['text'])
                video_mapping[len(all_comments) - 1] = video_id
        
        # Update status
        cache.set('batch_status', batch_id, {
            'status': 'analyzing',
            'message': f'Analyzing {len(all_comments)} comments in optimized batches'
        }, ttl_hours=1)
        
        # Perform batch analysis
        def progress_callback(current, total, progress):
            cache.set('batch_status', batch_id, {
                'status': 'analyzing',
                'progress': progress * 100,
                'message': f'Processing batch {current}/{total}'
            }, ttl_hours=1)
        
        results = optimizer.batch_predict(all_comments, progress_callback)
        
        # Aggregate results by video
        video_results = {}
        for idx, result in enumerate(results):
            video_id = video_mapping[idx]
            if video_id not in video_results:
                video_results[video_id] = []
            video_results[video_id].append(result)
        
        # Calculate statistics for each video
        final_results = {}
        for video_id, video_comments in video_results.items():
            sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
            total_confidence = 0
            
            for comment in video_comments:
                sentiment_counts[comment['sentiment']] += 1
                total_confidence += comment.get('confidence', 0)
            
            final_results[video_id] = {
                'total_comments': len(video_comments),
                'sentiment_distribution': sentiment_counts,
                'average_confidence': total_confidence / len(video_comments) if video_comments else 0,
                'processing_stats': optimizer.processor.get_stats()
            }
        
        # Store results
        cache.set('batch_results', batch_id, final_results, ttl_hours=24)
        
        # Update final status
        cache.set('batch_status', batch_id, {
            'status': 'completed',
            'message': 'Batch analysis completed successfully',
            'results_available': True
        }, ttl_hours=1)
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        cache.set('batch_status', batch_id, {
            'status': 'error',
            'error': str(e)
        }, ttl_hours=1)


@bp.route('/api/batch/status/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    """Get the status of a batch analysis job."""
    from app.cache import cache
    
    status = cache.get('batch_status', batch_id)
    if not status:
        return jsonify({'error': 'Batch ID not found'}), 404
    
    return jsonify(status)


@bp.route('/api/batch/results/<batch_id>', methods=['GET'])
def get_batch_results(batch_id):
    """Get the results of a completed batch analysis."""
    from app.cache import cache
    
    results = cache.get('batch_results', batch_id)
    if not results:
        return jsonify({'error': 'Results not found or not ready'}), 404
    
    return jsonify({
        'batch_id': batch_id,
        'results': results
    })


@bp.route('/api/batch/analyze_texts', methods=['POST'])
def batch_analyze_texts():
    """
    Analyze a batch of texts directly (without YouTube fetching).
    
    Request body:
    {
        "texts": ["text1", "text2", ...],
        "batch_size": 32,
        "use_dynamic_batching": true,
        "use_gpu": true
    }
    """
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        batch_size = data.get('batch_size', 32)
        use_dynamic = data.get('use_dynamic_batching', True)
        use_gpu = data.get('use_gpu', True)
        
        if not texts:
            return jsonify({'error': 'No texts provided'}), 400
        
        # Get appropriate analyzer
        if use_gpu:
            from app.science.fast_sentiment_analyzer import get_fast_analyzer
            analyzer = get_fast_analyzer()
            results = analyzer.analyze_batch_gpu_optimized(texts)
        else:
            from app.ml.ml_sentiment_analyzer import get_ml_analyzer
            analyzer = get_ml_analyzer()
            results = analyzer.analyze_batch_optimized(
                texts, 
                batch_size=batch_size,
                use_dynamic_batching=use_dynamic
            )
        
        # Calculate aggregate statistics
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        total_confidence = 0
        
        for result in results:
            sentiment_counts[result['sentiment']] += 1
            total_confidence += result.get('confidence', 0)
        
        return jsonify({
            'success': True,
            'total_analyzed': len(texts),
            'sentiment_distribution': sentiment_counts,
            'average_confidence': total_confidence / len(results) if results else 0,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in batch text analysis: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/batch/streaming', methods=['POST'])
def streaming_analysis():
    """
    Enable streaming analysis for real-time comment processing.
    
    Request body:
    {
        "video_id": "video_id",
        "buffer_size": 100,
        "flush_interval": 1.0
    }
    """
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        buffer_size = data.get('buffer_size', 100)
        flush_interval = data.get('flush_interval', 1.0)
        
        if not video_id:
            return jsonify({'error': 'No video ID provided'}), 400
        
        # Create streaming session ID
        session_id = f"stream_{video_id}_{int(time.time())}"
        
        # Start streaming processing in background
        thread = threading.Thread(
            target=process_streaming_comments,
            args=(video_id, buffer_size, flush_interval, session_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'video_id': video_id,
            'status': 'streaming_started'
        })
        
    except Exception as e:
        logger.error(f"Error in streaming analysis: {e}")
        return jsonify({'error': str(e)}), 500


def process_streaming_comments(video_id, buffer_size, flush_interval, session_id):
    """
    Process comments in streaming fashion.
    """
    from app.cache import cache
    from app.ml.ml_sentiment_analyzer import get_ml_analyzer
    from app.services.enhanced_youtube_service import EnhancedYouTubeService
    
    try:
        from app.services.enhanced_youtube_service import EnhancedYouTubeService
        youtube_service = EnhancedYouTubeService()
        from app.ml.ml_sentiment_analyzer import get_ml_analyzer
        analyzer = get_ml_analyzer()
        
        # Create comment generator
        def comment_generator():
            result = youtube_service.get_all_available_comments(
                video_id=video_id,
                target_comments=1000  # Get more comments for streaming
            )
            for comment in result['comments']:
                yield comment['text']
        
        # Process in streaming fashion
        for batch_results in analyzer.analyze_streaming(
            comment_generator(),
            buffer_size=buffer_size,
            flush_interval=flush_interval
        ):
            # Store batch results
            cache.set('stream_batch', f"{session_id}_{time.time()}", batch_results, ttl_hours=1)
            
            # Update status
            cache.set('stream_status', session_id, {
                'status': 'processing',
                'last_batch_size': len(batch_results),
                'last_update': time.time()
            }, ttl_hours=1)
        
        # Mark as completed
        cache.set('stream_status', session_id, {
            'status': 'completed',
            'last_update': time.time()
        }, ttl_hours=1)
        
    except Exception as e:
        logger.error(f"Error in streaming processing: {e}")
        cache.set('stream_status', session_id, {
            'status': 'error',
            'error': str(e)
        }, ttl_hours=1)