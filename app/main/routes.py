"""
Routes for the main blueprint.
"""
import os
from flask import render_template, flash, redirect, url_for, session, jsonify, request
from app.main import bp
from app.main.forms import YouTubeURLForm
from app.utils.youtube import extract_video_id, build_youtube_url
from app.services import YouTubeService
from app.cache import cache


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
        # Initialize YouTube service
        youtube_service = YouTubeService()
        
        # Use fewer comments for faster loading
        max_comments = 20
        
        # Check if data is in cache first
        video_cached = cache.get('video_info', video_id) is not None
        comments_cached = cache.get('comments_flat', f"{video_id}:{max_comments}") is not None
        
        if video_cached:
            cache_status['hits'].append('video_info')
        if comments_cached:
            cache_status['hits'].append('comments')
        
        # Fetch video info (will use cache if available)
        video_info = youtube_service.get_video_info(video_id)
        
        # Fetch sample of comments for analysis (will use cache if available)
        comments = youtube_service.get_all_comments_flat(video_id, max_comments=max_comments)
        
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
        
        # Prepare stats for template
        comment_stats = {
            'total_comments': len(comments),
            'unique_commenters': len(unique_commenters),
            'avg_comment_length': avg_comment_length,
            'replies_count': replies_count,
            'top_level_count': top_level_count,
            'top_commenters': top_commenters
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


@bp.route('/api/comments/<video_id>')
def api_get_comments(video_id):
    """
    API endpoint to fetch all comments for a video as JSON.
    
    Query parameters:
        - max_comments: Maximum number of top-level comments to fetch (default: from .env)
        - format: 'threaded' (default) or 'flat'
    """
    try:
        # Initialize YouTube service
        youtube_service = YouTubeService()
        
        # Get parameters
        max_comments = request.args.get('max_comments', type=int)
        if not max_comments:
            max_comments = int(os.getenv('MAX_COMMENTS_PER_VIDEO', 100))
        
        format_type = request.args.get('format', 'threaded')
        
        # Fetch comments based on format
        if format_type == 'flat':
            comments = youtube_service.get_all_comments_flat(video_id, max_comments)
            return jsonify({
                'success': True,
                'video_id': video_id,
                'format': 'flat',
                'comments': comments,
                'total_comments': len(comments)
            })
        else:
            # Get comprehensive summary with threads
            data = youtube_service.get_video_comments_summary(video_id, max_comments)
            return jsonify({
                'success': True,
                'video_id': video_id,
                'format': 'threaded',
                'data': data
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
