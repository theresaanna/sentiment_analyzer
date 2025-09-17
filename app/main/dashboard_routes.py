"""
Routes and APIs for the PRO dashboard.
"""
from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user

from app.main import bp
# Lazy import heavy services within endpoints to speed startup
from app.cache import cache
from app.models import db, UserChannel, Channel, Video, AnalysisJob


def require_pro():
    """Ensure user is PRO; return a JSON error response for API routes.
    Returns None if OK, or a (response, status) tuple to return from the view.
    """
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    if not getattr(current_user, 'is_subscribed', False):
        return jsonify({'success': False, 'error': 'Subscription required'}), 402
    return None


@bp.route('/dashboard')
@login_required
def dashboard():
    # Restrict to subscribed users
    if not current_user.is_subscribed:
        return render_template('auth/subscribe.html'), 402
    return render_template('dashboard.html')


@bp.route('/api/youtube/channel-videos')
@login_required
def api_channel_videos():
    guard = require_pro()
    if guard:
        return guard
    channel_input = request.args.get('channel')
    max_results = request.args.get('max', type=int, default=100)
    force_refresh = request.args.get('refresh', 'false').lower() in ('1', 'true', 'yes')
    try:
        from app.services.channel_service import ChannelService
        service = ChannelService()
        # Persist channel/videos and serve DB snapshot; associate channel with user
        data = service.get_channel_videos(channel_input, max_results=max_results, user_id=current_user.id)
        sync_enqueued = False
        if force_refresh:
            # Queue channel_sync job for the resolved channel
            sync_enqueued = _enqueue_channel_sync_job(data['channel']['id'], current_user.id, max_results)
        else:
            # Trigger lightweight freshness check without blocking
            try:
                service.check_and_sync_channel(data['channel']['id'], refresh=False)
            except Exception:
                pass
        return jsonify({'success': True, 'sync_enqueued': sync_enqueued, **data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# Simple Redis-backed job queue using lists and sets

@bp.route('/api/channel-sync/<channel_id>', methods=['POST'])
@login_required
def api_channel_sync(channel_id):
    guard = require_pro()
    if guard:
        return guard
    user_id = current_user.id
    max_results = request.args.get('max', type=int, default=100)

    # Enforce concurrency limit against active jobs
    try:
        if cache.enabled and cache.redis_client.scard(_active_key(user_id)) >= MAX_CONCURRENT_JOBS_PER_USER:
            return jsonify({'success': False, 'error': 'Too many active jobs. Please wait for some to finish.'}), 429
    except Exception:
        pass

    enq = _enqueue_channel_sync_job(channel_id, user_id, max_results)
    if not enq:
        return jsonify({'success': False, 'error': 'Failed to queue sync job'}), 500
    return jsonify({'success': True})
# Keys:
# - jobs:preload (list)            → global FIFO of job JSON
# - jobs:active:<user_id> (set)    → video_ids currently running for user
# - jobs:by_user:<user_id> (list)  → job ids history (optional)
# - preload_status (prefix)        → youtube:preload_status:<job_id>

import json
from datetime import datetime

MAX_CONCURRENT_JOBS_PER_USER = 3


def _job_key(job_id: str) -> str:
    return f"youtube:preload_status:{job_id}"


def _enqueue_channel_sync_job(yt_channel_id: str, user_id: int, max_results: int = 100) -> bool:
    """Push a channel_sync job into the queue and track it by user."""
    try:
        if not cache.enabled:
            return False
        import uuid
        job_id = f"sync_{uuid.uuid4().hex}"
        payload = {
            'type': 'channel_sync',
            'job_id': job_id,
            'user_id': user_id,
            'yt_channel_id': yt_channel_id,
            'max_results': max_results,
            'requested_at': datetime.utcnow().isoformat() + 'Z'
        }
        cache.set('preload_status', job_id, {
            'status': 'queued',
            'progress': 0,
            'channel_id': yt_channel_id,
            'job_type': 'channel_sync'
        }, ttl_hours=6)
        cache.redis_client.lpush(_queue_key(), json.dumps(payload))
        user_list = f"jobs:by_user:{user_id}"
        cache.redis_client.lpush(user_list, job_id)
        cache.redis_client.ltrim(user_list, 0, 99)
        return True
    except Exception:
        return False


def _active_key(user_id: int) -> str:
    return f"jobs:active:{user_id}"


def _queue_key() -> str:
    return "jobs:preload"


@bp.route('/api/preload/comments/<video_id>', methods=['POST'])
@login_required
def api_preload_comments(video_id):
    """Queue a comment preload job (PRO feature) using the unified AnalysisJob system."""
    guard = require_pro()
    if guard:
        return guard
    
    # Get target comment count
    body = request.get_json(silent=True) or {}
    raw_target = body.get('target_comments', None)
    target_comments = 5000  # Default for PRO preload
    if raw_target not in (None, '', 'null', 'None'):
        try:
            target_comments = min(int(raw_target), 10000)  # Cap at 10k
        except Exception:
            return jsonify({'success': False, 'error': 'target_comments must be an integer or null'}), 400
    
    # Check if job already exists
    from app.utils.youtube import build_youtube_url
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
    
    # Create new analysis job with PRO preload metadata
    job = AnalysisJob(
        user_id=current_user.id,
        video_id=video_id,
        video_url=build_youtube_url(video_id),
        comment_count_requested=target_comments,
        status='queued'
    )
    
    # Store metadata to indicate this is a PRO preload
    job.results = {'job_type': 'pro_preload', 'preload_only': True}
    
    db.session.add(job)
    db.session.commit()
    
    # Add to Redis queue for faster processing
    if cache.enabled:
        cache.redis_client.lpush('analysis_jobs:queue', job.job_id)
        # Also maintain backward compatibility with old status tracking
        cache.set('preload_status', job.job_id, {
            'status': 'queued',
            'progress': 0,
            'video_id': video_id,
            'job_type': 'preload'
        }, ttl_hours=6)
    
    return jsonify({'success': True, 'job_id': job.job_id})


@bp.route('/api/jobs/status')
@login_required
def api_jobs_status():
    """Get job status from unified AnalysisJob system with enhanced video metadata."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        # Get jobs from database
        jobs = AnalysisJob.query.filter_by(user_id=current_user.id)\
            .order_by(AnalysisJob.created_at.desc())\
            .limit(20).all()
        
        # Get video metadata for all video IDs
        video_ids = [job.video_id for job in jobs if job.video_id]
        video_metadata_map = {}
        
        if video_ids:
            # Try to get video metadata from Video table
            from app.models import Video
            videos = Video.query.filter(
                Video.yt_video_id.in_(video_ids)
            ).all()
            
            for video in videos:
                video_metadata_map[video.yt_video_id] = {
                    'title': video.title,
                    'views': video.views or 0,
                    'comments': video.comments or 0,
                    'published': video.published_at.isoformat() if video.published_at else '',
                    'channel_title': '',  # Would need to join with Channel table
                    'duration': ''
                }
        
        # Convert to status format expected by dashboard
        statuses = []
        for job in jobs:
            # Determine job type from comment count or metadata
            is_pro = job.comment_count_requested > 2500
            job_type = 'preload' if is_pro else 'analysis'
            
            # Get video metadata if available
            metadata = video_metadata_map.get(job.video_id)
            
            status = {
                'job_id': job.job_id,
                'status': job.status,
                'progress': job.progress or 0,
                'video_id': job.video_id,
                'job_type': job_type,
                'channel_id': None,  # Could be extracted from video
                'video_title': job.video_title,
                'comment_count': job.comment_count_requested,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'video_metadata': metadata  # Include enhanced metadata
            }
            statuses.append(status)
        
        return jsonify({'success': True, 'jobs': statuses})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/jobs/cancel/<job_id>', methods=['POST'])
@login_required
def api_cancel_job(job_id):
    """Cancel a running or queued job."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        if not cache.enabled:
            return jsonify({'success': False, 'error': 'Cache disabled'}), 500
        
        # Verify the job belongs to the current user
        user_key = f"jobs:by_user:{current_user.id}"
        user_jobs = cache.redis_client.lrange(user_key, 0, 99) or []
        
        if job_id not in user_jobs:
            return jsonify({'success': False, 'error': 'Job not found or access denied'}), 404
        
        # Get current job status
        status = cache.get('preload_status', job_id)
        if not status:
            return jsonify({'success': False, 'error': 'Job status not found'}), 404
        
        # Only allow cancelling jobs that are queued, pending, or running
        if status.get('status') not in ['queued', 'pending', 'running']:
            return jsonify({'success': False, 'error': f'Job cannot be cancelled (status: {status.get("status")})'}), 400
        
        # Update job status to cancelled
        status['status'] = 'cancelled'
        status['cancelled_at'] = datetime.utcnow().isoformat() + 'Z'
        cache.set('preload_status', job_id, status, ttl_hours=6)
        
        # Remove from active jobs set if present
        try:
            cache.redis_client.srem(_active_key(current_user.id), job_id)
        except Exception:
            pass
        
        # Add a cancel marker for the worker to check
        cancel_key = f"jobs:cancel:{job_id}"
        cache.redis_client.setex(cancel_key, 3600, '1')  # Expire after 1 hour
        
        return jsonify({'success': True, 'message': 'Job cancellation requested'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/jobs/clear-old', methods=['POST'])
@login_required
def api_clear_old_jobs():
    """Clear completed and cancelled jobs from the user's job list."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        if not cache.enabled:
            return jsonify({'success': False, 'error': 'Cache disabled'}), 500
        
        user_key = f"jobs:by_user:{current_user.id}"
        job_ids = cache.redis_client.lrange(user_key, 0, 99) or []
        
        cleared_count = 0
        jobs_to_keep = []
        
        for job_id in job_ids:
            status = cache.get('preload_status', job_id)
            if status:
                # Keep only jobs that are queued, pending, or running
                if status.get('status') in ['queued', 'pending', 'running', 'fetching', 'syncing']:
                    jobs_to_keep.append(job_id)
                else:
                    # Job is completed, failed, cancelled, or error - remove it
                    cleared_count += 1
                    # Also delete the status data to free up memory
                    cache.delete('preload_status', job_id)
            else:
                # No status found, remove from list
                cleared_count += 1
        
        # Update the user's job list with only active jobs
        if cleared_count > 0:
            cache.redis_client.delete(user_key)
            if jobs_to_keep:
                # Re-add only the jobs we want to keep
                for job_id in reversed(jobs_to_keep):  # Reverse to maintain order
                    cache.redis_client.rpush(user_key, job_id)
        
        return jsonify({
            'success': True,
            'cleared': cleared_count,
            'remaining': len(jobs_to_keep)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/user/channels')
@login_required
def api_user_channels():
    """Get all channels for the current user."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        user_channels = db.session.query(Channel).join(
            UserChannel, UserChannel.channel_id == Channel.id
        ).filter(
            UserChannel.user_id == current_user.id
        ).all()
        
        channels = []
        for channel in user_channels:
            channels.append({
                'id': channel.yt_channel_id,
                'title': channel.title,
                'handle': channel.handle,
                'video_count': channel.video_count,
                'last_synced': channel.last_synced_at.isoformat() if channel.last_synced_at else None
            })
        
        return jsonify({
            'success': True,
            'channels': channels,
            'count': len(channels)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/user/channels', methods=['POST'])
@login_required
def api_add_user_channel():
    """Add a channel to the user's list (max 5)."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        # Check current channel count
        current_count = UserChannel.query.filter_by(user_id=current_user.id).count()
        if current_count >= 5:
            return jsonify({'success': False, 'error': 'Maximum 5 channels allowed'}), 400
        
        # Get channel URL/handle from request
        data = request.get_json()
        channel_input = data.get('channel')
        if not channel_input:
            return jsonify({'success': False, 'error': 'Channel URL or handle required'}), 400
        
        # Use ChannelService to resolve and persist the channel
        service = ChannelService()
        channel_data = service.get_channel_videos(channel_input, max_results=10, user_id=current_user.id)
        
        return jsonify({
            'success': True,
            'channel': {
                'id': channel_data['channel']['id'],
                'title': channel_data['channel']['title'],
                'handle': channel_data['channel'].get('handle'),
                'video_count': channel_data['count']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/user/channels/<channel_id>', methods=['DELETE'])
@login_required
def api_remove_user_channel(channel_id):
    """Remove a channel from the user's list."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        # Find the channel
        channel = Channel.query.filter_by(yt_channel_id=channel_id).first()
        if not channel:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404
        
        # Remove the user-channel association
        user_channel = UserChannel.query.filter_by(
            user_id=current_user.id,
            channel_id=channel.id
        ).first()
        
        if not user_channel:
            return jsonify({'success': False, 'error': 'Channel not in user list'}), 404
        
        db.session.delete(user_channel)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Channel removed'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/channel/<channel_id>/delete', methods=['DELETE'])
@login_required
def api_delete_channel_data(channel_id):
    """Delete a channel and all its associated data (videos, comments, jobs)."""
    guard = require_pro()
    if guard:
        return guard
    
    deleted_videos = 0
    deleted_jobs = 0
    
    try:
        # Find the channel
        channel = Channel.query.filter_by(yt_channel_id=channel_id).first()
        if not channel:
            # Channel doesn't exist in DB, but still clean up jobs
            pass
        else:
            # Verify user has access to this channel
            user_channel = UserChannel.query.filter_by(
                user_id=current_user.id,
                channel_id=channel.id
            ).first()
            
            if not user_channel:
                return jsonify({'success': False, 'error': 'Channel not in user list'}), 404
            
            # Get all videos for this channel
            videos = Video.query.filter_by(channel_id=channel.id).all()
            deleted_videos = len(videos)
            
            # Clean up cached comments for these videos
            if cache.enabled:
                for video in videos:
                    # Delete cached comments data
                    cache.delete('youtube_comments', video.yt_video_id)
                    # Delete any preload status for this video
                    cache.delete('preload_status', video.yt_video_id)
            
            # Delete all videos from database
            Video.query.filter_by(channel_id=channel.id).delete()
            
            # Remove user-channel association
            db.session.delete(user_channel)
            
            # Check if any other users have this channel
            other_users = UserChannel.query.filter_by(channel_id=channel.id).count()
            if other_users == 0:
                # No other users have this channel, delete it completely
                db.session.delete(channel)
        
        # Clean up Redis jobs for this channel
        if cache.enabled:
            user_key = f"jobs:by_user:{current_user.id}"
            job_ids = cache.redis_client.lrange(user_key, 0, 99) or []
            
            jobs_to_remove = []
            for job_id in job_ids:
                status = cache.get('preload_status', job_id)
                if status:
                    # Check if job is related to this channel
                    if (status.get('channel_id') == channel_id or 
                        status.get('yt_channel_id') == channel_id):
                        jobs_to_remove.append(job_id)
                        deleted_jobs += 1
                        
                        # Cancel if running
                        if status.get('status') in ['queued', 'pending', 'running']:
                            cancel_key = f"jobs:cancel:{job_id}"
                            cache.redis_client.setex(cancel_key, 3600, '1')
                            status['status'] = 'cancelled'
                            cache.set('preload_status', job_id, status, ttl_hours=1)
                        
                        # Delete job status
                        cache.delete('preload_status', job_id)
                    # Also check videos belonging to this channel
                    elif status.get('video_id') and channel:
                        # Check if this video belongs to the channel
                        video = Video.query.filter_by(
                            yt_video_id=status.get('video_id'),
                            channel_id=channel.id
                        ).first()
                        if video:
                            jobs_to_remove.append(job_id)
                            deleted_jobs += 1
                            
                            # Cancel if running
                            if status.get('status') in ['queued', 'pending', 'running']:
                                cancel_key = f"jobs:cancel:{job_id}"
                                cache.redis_client.setex(cancel_key, 3600, '1')
                                status['status'] = 'cancelled'
                                cache.set('preload_status', job_id, status, ttl_hours=1)
                            
                            # Delete job status
                            cache.delete('preload_status', job_id)
            
            # Remove jobs from user's list
            if jobs_to_remove:
                for job_id in jobs_to_remove:
                    cache.redis_client.lrem(user_key, 0, job_id)
                    # Also remove from active set if present
                    cache.redis_client.srem(_active_key(current_user.id), job_id)
        
        # Commit all database changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Channel and all associated data deleted',
            'deleted_videos': deleted_videos,
            'deleted_jobs': deleted_jobs
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
