"""
Routes for the main blueprint.
"""
import os
import threading
import json
from flask import render_template, flash, redirect, url_for, session, jsonify, request
from app.main import bp
from app.main.forms import YouTubeURLForm
from app.utils.youtube import extract_video_id, build_youtube_url
from app.services import YouTubeService
from app.services.enhanced_youtube_service import EnhancedYouTubeService, analyze_comment_coverage
from app.cache import cache
from app.science import SentimentAnalyzer
from app.science.comment_summarizer import EnhancedCommentSummarizer

# Import fast routes to register them
try:
    from app.main import fast_routes
except ImportError as e:
    print(f"Warning: Could not import fast routes: {e}")


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    """Homepage with YouTube URL submission form."""
    form = YouTubeURLForm()
    
    if form.validate_on_submit():
        url = form.url.data
        video_id = extract_video_id(url)
        
        if video_id:
            # Store video ID in session
            session['video_id'] = video_id
            session['video_url'] = build_youtube_url(video_id)
            
            # Redirect to analysis page
            return redirect(url_for('main.analyze', video_id=video_id))
        else:
            flash('Could not extract video ID from URL', 'danger')
    
    return render_template('index.html', form=form)


@bp.route('/analyze/<video_id>')
def analyze(video_id):
    """Analyze comments for a given video ID."""
    video_url = build_youtube_url(video_id)
    cache_status = {'enabled': cache.enabled, 'hits': []}
    
    try:
        # Initialize Enhanced YouTube service for maximum comment retrieval
        youtube_service = EnhancedYouTubeService()
        
        # Get more comments for better analysis (configurable)
        max_comments = request.args.get('max_comments', type=int, default=1000)
        
        # Check if data is in cache first
        video_cached = cache.get('video_info', video_id) is not None
        comments_cached = cache.get('enhanced_comments', f"{video_id}:max:{max_comments}:True:relevance") is not None
        
        if video_cached:
            cache_status['hits'].append('video_info')
        if comments_cached:
            cache_status['hits'].append('comments')
        
        # Fetch video info (will use cache if available)
        video_info = youtube_service.get_video_info(video_id)
        
        # Fetch maximum available comments using enhanced service
        result = youtube_service.get_all_available_comments(
            video_id=video_id,
            target_comments=max_comments,
            include_replies=True,
            sort_order='relevance'
        )
        comments = result['comments']
        fetch_stats = result['statistics']
        
        # Calculate statistics
        unique_commenters = set()
        commenter_frequency = {}
        total_length = 0
        replies_count = 0
        
        for comment in comments:
            unique_commenters.add(comment['author_channel_id'])
            author = comment['author']
            commenter_frequency[author] = commenter_frequency.get(author, 0) + 1
            total_length += len(comment['text'])
            if comment.get('is_reply', False):
                replies_count += 1
        
        # Find top commenters
        top_commenters = sorted(
            commenter_frequency.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Calculate averages
        avg_comment_length = round(total_length / len(comments)) if comments else 0
        top_level_count = len(comments) - replies_count
        
        # Prepare stats for template with enhanced metrics
        comment_stats = {
            'total_comments': len(comments),
            'unique_commenters': len(unique_commenters),
            'avg_comment_length': avg_comment_length,
            'replies_count': replies_count,
            'top_level_count': top_level_count,
            'top_commenters': top_commenters,
            # Enhanced statistics
            'total_available': fetch_stats['total_comments_available'],
            'fetch_percentage': fetch_stats['fetch_percentage'],
            'fetch_time': fetch_stats['fetch_time_seconds'],
            'comments_per_second': fetch_stats['comments_per_second'],
            'quota_used': fetch_stats['quota_used']
        }
        
        return render_template(
            'analyze.html',
            video_id=video_id,
            video_url=video_url,
            video_info=video_info,
            comment_stats=comment_stats,
            cache_status=cache_status,
            success=True
        )
        
    except Exception as e:
        flash(f'Error analyzing video: {str(e)}', 'danger')
        return render_template(
            'analyze.html',
            video_id=video_id,
            video_url=video_url,
            success=False,
            error=str(e)
        )


@bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')


@bp.route('/privacy')
def privacy():
    """Privacy policy page."""
    return render_template('privacy.html')


@bp.route('/terms')
def terms():
    """Terms of service page."""
    return render_template('terms.html')


@bp.route('/api/comments/<video_id>')
def api_get_comments(video_id):
    """
    API endpoint to fetch all comments for a video as JSON.
    
    Query parameters:
        - max_comments: Maximum number of top-level comments to fetch (default: from .env)
        - format: 'threaded' (default) or 'flat'
    """
    try:
        # Initialize Enhanced YouTube service
        youtube_service = EnhancedYouTubeService()
        
        # Get parameters with higher default
        max_comments = request.args.get('max_comments', type=int)
        if not max_comments:
            max_comments = int(os.getenv('MAX_COMMENTS_PER_VIDEO', 10000))
        
        format_type = request.args.get('format', 'threaded')
        
        # Fetch comments using enhanced service
        if format_type == 'flat':
            result = youtube_service.get_all_available_comments(
                video_id=video_id,
                target_comments=max_comments,
                include_replies=True,
                sort_order='relevance'
            )
            return jsonify({
                'success': True,
                'video_id': video_id,
                'format': 'flat',
                'comments': result['comments'],
                'total_comments': len(result['comments']),
                'statistics': result['statistics'],
                'metadata': result['fetch_metadata']
            })
        else:
            # Get comprehensive summary with threads
            result = youtube_service.get_all_available_comments(
                video_id=video_id,
                target_comments=max_comments,
                include_replies=True,
                sort_order='relevance'
            )
            return jsonify({
                'success': True,
                'video_id': video_id,
                'format': 'threaded',
                'threads': result['threads'],
                'statistics': result['statistics'],
                'metadata': result['fetch_metadata']
            })
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An unexpected error occurred: {str(e)}'
        }), 500


@bp.route('/api/video/<video_id>')
def api_get_video_info(video_id):
    """
    API endpoint to fetch video information only.
    """
    try:
        youtube_service = YouTubeService()
        video_info = youtube_service.get_video_info(video_id)
        
        return jsonify({
            'success': True,
            'video': video_info
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An unexpected error occurred: {str(e)}'
        }), 500


@bp.route('/api/extract-video-id', methods=['POST'])
def api_extract_video_id():
    """
    API endpoint to extract video ID from a YouTube URL.
    """
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({
            'success': False,
            'error': 'URL is required'
        }), 400
    
    url = data['url']
    video_id = extract_video_id(url)
    
    if video_id:
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_url': build_youtube_url(video_id)
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Could not extract video ID from URL'
        }), 400


@bp.route('/api/cache/clear/<video_id>', methods=['POST'])
def api_clear_cache(video_id):
    """
    API endpoint to clear cache for a specific video.
    """
    try:
        deleted = cache.clear_video_cache(video_id)
        return jsonify({
            'success': True,
            'message': f'Cleared {deleted} cache entries for video {video_id}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/cache/stats')
def api_cache_stats():
    """
    API endpoint to get cache statistics.
    """
    try:
        stats = cache.get_cache_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/analyze/sentiment/<video_id>', methods=['POST'])
def api_analyze_sentiment(video_id):
    """
    API endpoint to trigger sentiment analysis for video comments.
    """
    try:
        # Get analysis parameters
        data = request.get_json() or {}
        max_comments = data.get('max_comments', 100)
        percentage_selected = data.get('percentage_selected', 10)
        
        # Generate analysis_id based on percentage and video_id for consistency
        # This ensures the same ID is used regardless of exact comment count
        analysis_id = f"sentiment_{video_id}_{percentage_selected}pct_{max_comments}"
        
        print(f"API: Received request - video_id: {video_id}, max_comments: {max_comments}, percentage: {percentage_selected}")
        print(f"API: Generated analysis_id: {analysis_id}")
        
        # Check if analysis already exists in cache
        cached_result = cache.get('sentiment_analysis', analysis_id)
        if cached_result:
            return jsonify({
                'success': True,
                'analysis_id': analysis_id,
                'status': 'completed',
                'cached': True
            })
        
        # Set initial status
        cache.set('analysis_status', analysis_id, {'status': 'started', 'progress': 0}, ttl_hours=1)
        
        # Start analysis in background thread
        thread = threading.Thread(
            target=run_sentiment_analysis,
            args=(video_id, max_comments, analysis_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'status': 'started',
            'message': 'Sentiment analysis started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def run_sentiment_analysis(video_id: str, max_comments: int, analysis_id: str):
    """
    Run sentiment analysis in background.
    """
    try:
        print(f"Starting sentiment analysis for {video_id} with {max_comments} comments, ID: {analysis_id}")
        
        # Update status
        cache.set('analysis_status', analysis_id, {'status': 'fetching_comments', 'progress': 10}, ttl_hours=1)
        
        # Fetch video info for context
        youtube_service = YouTubeService()
        video_info = youtube_service.get_video_info(video_id)
        
        # Fetch comments
        comments = youtube_service.get_all_comments_flat(video_id, max_comments=max_comments)
        print(f"Fetched {len(comments)} comments for analysis")
        
        # Update status
        cache.set('analysis_status', analysis_id, {'status': 'analyzing_sentiment', 'progress': 30}, ttl_hours=1)
        
        # Initialize analyzer
        analyzer = SentimentAnalyzer()
        
        # Progress callback
        def progress_callback(current, total):
            progress = 30 + int((current / total) * 50)  # 30-80% for sentiment analysis
            cache.set('analysis_status', analysis_id, 
                     {'status': 'analyzing_sentiment', 'progress': progress, 
                      'current': current, 'total': total}, ttl_hours=1)
        
        # Analyze sentiment
        comment_texts = [c['text'] for c in comments]
        print(f"Analyzing sentiment for {len(comment_texts)} comments...")
        sentiment_results = analyzer.analyze_batch(
            comment_texts,
            progress_callback=progress_callback
        )
        
        # Add comment IDs to individual results for YouTube linking
        if 'individual_results' in sentiment_results:
            for i, result in enumerate(sentiment_results['individual_results']):
                if i < len(comments):
                    result['comment_id'] = comments[i].get('id', comments[i].get('comment_id', None))
        
        print(f"Sentiment analysis complete. Overall: {sentiment_results.get('overall_sentiment', 'unknown')}")
        
        # Update status
        cache.set('analysis_status', analysis_id, {'status': 'generating_summary', 'progress': 85}, ttl_hours=1)
        
        # Generate enhanced summary with video context
        print("Generating enhanced summary with intelligent filtering...")
        summarizer = EnhancedCommentSummarizer(use_openai=os.getenv('OPENAI_API_KEY') is not None)
        summary_results = summarizer.generate_enhanced_summary(comments, sentiment_results, video_info)
        
        # Debug: Check if social media themes were generated
        print(f"DEBUG: Summary keys: {list(summary_results.keys())}")
        if 'social_media_themes' in summary_results:
            themes_count = len(summary_results['social_media_themes'].get('themes', []))
            print(f"DEBUG: Generated {themes_count} social media themes")
        else:
            print("DEBUG: No social_media_themes found in summary_results")
        
        # Get sentiment timeline
        timeline = analyzer.get_sentiment_timeline(comments[:50])  # Limit timeline to 50 comments
        
        # Calculate updated comment statistics based on analyzed comments
        unique_commenters = set()
        commenter_frequency = {}
        total_length = 0
        replies_count = 0
        
        for comment in comments:
            unique_commenters.add(comment.get('author_channel_id', comment.get('author', 'unknown')))
            author = comment.get('author', 'Anonymous')
            commenter_frequency[author] = commenter_frequency.get(author, 0) + 1
            total_length += len(comment.get('text', ''))
            if comment.get('is_reply', False):
                replies_count += 1
        
        # Find top commenters
        top_commenters = sorted(
            commenter_frequency.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Calculate averages
        avg_comment_length = round(total_length / len(comments)) if comments else 0
        top_level_count = len(comments) - replies_count
        
        # Updated stats based on analyzed dataset
        updated_stats = {
            'total_analyzed': len(comments),
            'unique_commenters': len(unique_commenters),
            'avg_comment_length': avg_comment_length,
            'replies_count': replies_count,
            'top_level_count': top_level_count,
            'top_commenters': top_commenters,
            'analysis_depth_percentage': round((len(comments) / video_info.get('statistics', {}).get('comments', len(comments))) * 100, 1) if video_info else 100
        }
        
        # Prepare final results
        results = {
            'video_id': video_id,
            'analysis_id': analysis_id,
            'sentiment': sentiment_results,
            'summary': summary_results,
            'timeline': timeline,
            'comments_sample': comments[:10],  # Include sample of analyzed comments
            'updated_stats': updated_stats  # Include updated statistics
        }
        
        # Debug: Check final results before caching
        print(f"DEBUG: Final results keys: {list(results.keys())}")
        if 'summary' in results:
            summary_keys = list(results['summary'].keys())
            print(f"DEBUG: Final summary keys: {summary_keys}")
            if 'social_media_themes' in results['summary']:
                print(f"DEBUG: Social media themes preserved in final results")
            else:
                print(f"DEBUG: Social media themes MISSING from final results")
        
        # Cache results
        success = cache.set('sentiment_analysis', analysis_id, results, ttl_hours=24)  # Cache for 24 hours
        
        if success:
            print(f"Results cached successfully for {analysis_id}")
            # Update status to completed only after results are cached
            cache.set('analysis_status', analysis_id, {'status': 'completed', 'progress': 100}, ttl_hours=1)
            print(f"Analysis completed for {analysis_id}")
        else:
            print(f"ERROR: Failed to cache results for {analysis_id}")
            raise Exception("Failed to cache analysis results")
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in sentiment analysis for {analysis_id}: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Update status to error
        cache.set('analysis_status', analysis_id, 
                 {'status': 'error', 'progress': 0, 'error': error_msg}, ttl_hours=1)


@bp.route('/api/analyze/status/<analysis_id>')
def api_analysis_status(analysis_id):
    """
    Get the status of a sentiment analysis job.
    """
    try:
        print(f"Status check for analysis_id: {analysis_id}")
        status = cache.get('analysis_status', analysis_id)
        
        # Backward compatibility: try old format if new format not found
        if not status and '_pct_' not in analysis_id:
            # Try to extract video_id from old format: sentiment_<video_id>_<number>
            if analysis_id.startswith('sentiment_'):
                # Remove 'sentiment_' prefix and get the rest
                remainder = analysis_id[10:]  # len('sentiment_') = 10
                # Find the last underscore (before the number)
                last_underscore = remainder.rfind('_')
                if last_underscore > 0:
                    video_id = remainder[:last_underscore]
                    number_str = remainder[last_underscore + 1:]
                    # Try common rounded values
                    for rounded in [50, 100, 200, 500, 1000]:
                        old_id = f"sentiment_{video_id}_{rounded}"
                        status = cache.get('analysis_status', old_id)
                        if status:
                            print(f"Found status with old format: {old_id}")
                            break
        
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


@bp.route('/api/analyze/results/<analysis_id>')
def api_analysis_results(analysis_id):
    """
    Get the results of a completed sentiment analysis.
    """
    try:
        print(f"Results request for analysis_id: {analysis_id}")
        # Check if analysis is complete
        status = cache.get('analysis_status', analysis_id)
        
        # Backward compatibility: try old format if new format not found
        actual_id = analysis_id
        if not status and '_pct_' not in analysis_id:
            if analysis_id.startswith('sentiment_'):
                remainder = analysis_id[10:]
                last_underscore = remainder.rfind('_')
                if last_underscore > 0:
                    video_id = remainder[:last_underscore]
                    for rounded in [50, 100, 200, 500, 1000]:
                        old_id = f"sentiment_{video_id}_{rounded}"
                        status = cache.get('analysis_status', old_id)
                        if status:
                            actual_id = old_id
                            print(f"Found status with old format: {old_id}")
                            break
        if not status:
            return jsonify({
                'success': False,
                'error': 'Analysis not found',
                'details': f'No status found for {analysis_id}'
            }), 404
        
        if status.get('status') == 'error':
            return jsonify({
                'success': False,
                'error': 'Analysis failed',
                'details': status.get('error', 'Unknown error'),
                'status': status
            }), 500
        
        if status.get('status') != 'completed':
            return jsonify({
                'success': False,
                'error': 'Analysis not yet completed',
                'status': status
            }), 202
        
        # Get results using the actual ID (might be different after backward compat check)
        results = cache.get('sentiment_analysis', actual_id)
        if not results:
            # Log this issue
            print(f"WARNING: Status shows completed but no results found for {analysis_id}")
            print(f"Status: {status}")
            
            # Try to restart the analysis
            return jsonify({
                'success': False,
                'error': 'Results not found despite completed status. Please try again.',
                'restart_needed': True
            }), 404
        
        # Debug: Check retrieved results from cache
        print(f"DEBUG: Retrieved results keys: {list(results.keys())}")
        if 'summary' in results:
            summary_keys = list(results['summary'].keys())
            print(f"DEBUG: Retrieved summary keys: {summary_keys}")
            if 'social_media_themes' in results['summary']:
                print(f"DEBUG: Social media themes found in retrieved results")
            else:
                print(f"DEBUG: Social media themes MISSING from retrieved results")
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
