"""
Routes for queued sentiment analysis jobs.
"""
from flask import render_template, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone
import uuid

from app.main import bp
from app.models import db, AnalysisJob
from app.utils.youtube import extract_video_id, build_youtube_url
from app.cache import cache


@bp.route('/api/analyze/queue', methods=['POST'])
@login_required
def api_queue_analysis():
    """Queue a sentiment analysis job for background processing."""
    # Check if user is authenticated
    if not current_user.is_authenticated:
        return jsonify({
            'success': False, 
            'error': 'Authentication required',
            'redirect_to_login': True
        }), 401
    
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        video_id = data.get('video_id')
        comment_count = data.get('comment_count', 500)
        include_replies = False  # Never include replies
        
        # Extract video ID if URL provided
        if video_url and not video_id:
            video_id = extract_video_id(video_url)
        
        if not video_id:
            return jsonify({'success': False, 'error': 'Valid video ID or URL required'}), 400
        
        # Check if user already has this video in queue or recently completed
        existing_job = AnalysisJob.query.filter_by(
            user_id=current_user.id,
            video_id=video_id
        ).filter(
            AnalysisJob.status.in_(['queued', 'processing'])
        ).first()
        
        if existing_job:
            return jsonify({
                'success': False, 
                'error': 'Analysis already in progress for this video',
                'job_id': existing_job.job_id
            }), 409
        
        # Create new analysis job
        job = AnalysisJob(
            user_id=current_user.id,
            video_id=video_id,
            video_url=build_youtube_url(video_id),
            comment_count_requested=min(comment_count, 10000),  # Cap at 10000 for Pro users
            status='queued',
            include_replies=False  # Never include replies
        )
        
        db.session.add(job)
        db.session.commit()
        
        # Optional: Add to Redis queue for faster processing
        if cache.enabled:
            cache.redis_client.lpush('analysis_jobs:queue', job.job_id)
        
        return jsonify({
            'success': True,
            'job_id': job.job_id,
            'message': 'Analysis job queued successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/analyze/job/<job_id>')
@login_required
def api_get_job_status(job_id):
    """Get the status of a specific analysis job."""
    try:
        job = AnalysisJob.query.filter_by(
            job_id=job_id,
            user_id=current_user.id
        ).first()
        
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        return jsonify({
            'success': True,
            'job': job.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/analyze/status/<job_id>')
def view_analysis_status_testing(job_id):
    """
    Test-only route to render the analysis status page without authentication.
    This is enabled only when TESTING config is true to support E2E tests.
    """
    if not current_app.config.get('TESTING'):
        abort(404)
    # Minimal job-like object for template rendering
    class Job:
        pass
    job = Job()
    job.job_id = job_id
    job.video_title = 'Test Video Title'
    job.channel_name = 'Test Channel'
    # Derive initial status from job_id for testing routes
    if 'queued' in job_id:
        job.status = 'queued'
        job.progress = 0
    elif 'completed' in job_id:
        job.status = 'completed'
        job.progress = 100
    elif 'error' in job_id or 'failed' in job_id:
        job.status = 'failed'
        job.progress = 0
    else:
        job.status = 'processing'
        job.progress = 25
    job.comment_count_processed = 50
    job.comment_count_requested = 200
    job.started_at = datetime.now()
    return render_template('analysis_status.html', job=job)


@bp.route('/api/user/analysis-jobs')
@login_required
def api_list_user_jobs():
    """List all analysis jobs for the current user."""
    try:
        # Get filter parameters
        status = request.args.get('status')
        limit = request.args.get('limit', type=int, default=20)
        offset = request.args.get('offset', type=int, default=0)
        
        # Build query
        query = AnalysisJob.query.filter_by(user_id=current_user.id)
        
        if status:
            if status == 'active':
                query = query.filter(AnalysisJob.status.in_(['queued', 'processing']))
            else:
                query = query.filter_by(status=status)
        
        # Order by created_at descending (newest first)
        query = query.order_by(AnalysisJob.created_at.desc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        jobs = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'jobs': [job.to_dict() for job in jobs],
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/analyze/job/<job_id>', methods=['DELETE'])
@login_required
def api_cancel_analysis_job(job_id):
    """Cancel a queued or processing analysis job."""
    try:
        job = AnalysisJob.query.filter_by(
            job_id=job_id,
            user_id=current_user.id
        ).first()
        
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        if job.status not in ['queued', 'processing']:
            return jsonify({
                'success': False, 
                'error': f'Cannot cancel job with status: {job.status}'
            }), 400
        
        # Update job status
        job.status = 'cancelled'
        job.error_message = 'Cancelled by user'
        db.session.commit()
        
        # Also mark in Redis if available
        if cache.enabled:
            cache.redis_client.setex(f'analysis_jobs:cancel:{job_id}', 3600, '1')
        
        return jsonify({
            'success': True,
            'message': 'Job cancelled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/analyze/job/<job_id>/results')
@login_required
def api_get_job_results(job_id):
    """Get the results of a completed analysis job."""
    try:
        job = AnalysisJob.query.filter_by(
            job_id=job_id,
            user_id=current_user.id
        ).first()
        
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        if job.status != 'completed':
            return jsonify({
                'success': False, 
                'error': f'Job not completed. Current status: {job.status}'
            }), 400
        
        if not job.results:
            return jsonify({
                'success': False,
                'error': 'No results available for this job'
            }), 404
        
        return jsonify({
            'success': True,
            'job_id': job.job_id,
            'video_id': job.video_id,
            'video_title': job.video_title,
            'channel_name': job.channel_name,
            'results': job.results,
            'comment_count': job.comment_count_processed,
            'processing_time': job.processing_time_seconds,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/analysis/<job_id>')
@login_required
def view_analysis_results(job_id):
    """View the results of a completed or in-progress analysis job."""
    from app.utils.youtube import build_youtube_url
    
    job = AnalysisJob.query.filter_by(
        job_id=job_id,
        user_id=current_user.id
    ).first()
    
    if not job:
        abort(404)
    
    # If job is not completed, show status page
    if job.status in ['queued', 'processing', 'failed', 'cancelled']:
        return render_template('analysis_status.html', job=job)
    
    # For completed jobs, prepare data for the analyze template
    if job.status == 'completed' and job.results:
        results = job.results
        
        # Extract data from job results
        video_info = results.get('video_info', {})
        comment_stats = results.get('comment_stats', {
            'total_comments': job.comment_count_processed,
            'fetched_comments': job.comment_count_processed,
            'total_analyzed': job.comment_count_processed
        })
        
        # Merge with fetch_stats if available
        fetch_stats = comment_stats.get('fetch_stats', {})
        
        # Add all stats that the template expects
        comment_stats.update({
            'unique_commenters': comment_stats.get('unique_commenters', 0),
            'avg_comment_length': comment_stats.get('avg_comment_length', 0),
            'replies_count': comment_stats.get('replies_count', 0),
            'top_level_count': comment_stats.get('top_level_count', job.comment_count_processed),
            'top_commenters': comment_stats.get('top_commenters', []),
            'total_available': comment_stats.get('total_available', job.comment_count_requested),
            'fetch_percentage': comment_stats.get('fetch_percentage', 100.0),
            'fetch_time': comment_stats.get('fetch_time', job.processing_time_seconds or 0),
            'comments_per_second': comment_stats.get('comments_per_second', 
                job.comment_count_processed / max(job.processing_time_seconds, 1) if job.processing_time_seconds else 0),
            'quota_used': comment_stats.get('quota_used', 0),
            # Add the missing threads_fetched field
            'threads_fetched': fetch_stats.get('threads_fetched', comment_stats.get('threads_fetched', 0)),
            'total_top_level_comments': fetch_stats.get('total_top_level_comments', 
                comment_stats.get('total_top_level_comments', job.comment_count_processed))
        })
        
        # Use the analyze template with the job data
        sentiment_data = results.get('sentiment_analysis', {})
        
        # Ensure all required fields are present for the template
        if sentiment_data:
            # Ensure the summary field exists
            if 'summary' not in sentiment_data:
                dist = sentiment_data.get('distribution', {})
                pct = sentiment_data.get('percentages', {})
                sentiment_data['summary'] = (
                    f"Analysis of {sentiment_data.get('total_analyzed', 0)} comments shows "
                    f"{sentiment_data.get('overall_sentiment', 'neutral')} sentiment overall. "
                    f"{pct.get('positive', 0):.1f}% positive, "
                    f"{pct.get('neutral', 0):.1f}% neutral, "
                    f"{pct.get('negative', 0):.1f}% negative."
                )
        
        return render_template(
            'analyze.html',
            video_id=job.video_id,
            video_url=job.video_url or build_youtube_url(job.video_id),
            video_info=video_info,
            comment_stats=comment_stats,
            cache_status={'enabled': True, 'hits': ['job_results']},
            success=True,
            # Pass the job results for sentiment display
            analysis_job=job,
            precomputed_results=sentiment_data,
            # Pass updated_stats for the JavaScript updateCommentStatistics function
            updated_stats=results.get('updated_stats')
        )
    
    # Fallback for incomplete data
    return render_template('analysis_status.html', job=job)
