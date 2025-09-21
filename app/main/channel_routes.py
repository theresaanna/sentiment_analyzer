"""Routes for managing user channels."""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db, cache
from app.models import Channel, UserChannel, Video, AnalysisJob
from app.services.async_youtube_service import AsyncYouTubeService
import re
from datetime import datetime, timezone
import asyncio

bp = Blueprint('channel', __name__)


def require_pro():
    """Ensure user is PRO; return a JSON error response for API routes.
    Returns None if OK, or a (response, status) tuple to return from the view.
    """
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    if not getattr(current_user, 'is_subscribed', False):
        return jsonify({'success': False, 'error': 'Pro subscription required'}), 403
    return None


def extract_channel_info(channel_url):
    """Extract channel ID or handle from URL."""
    # Handle direct @handle
    if channel_url.startswith('@'):
        return {'handle': channel_url}
    
    # Handle various YouTube URL formats
    patterns = {
        'channel_id': r'youtube\.com/channel/(UC[\w-]+)',
        'user': r'youtube\.com/user/([\w-]+)',
        'c_name': r'youtube\.com/c/([\w-]+)',
        'handle': r'youtube\.com/@([\w-]+)',
        'custom': r'youtube\.com/([\w-]+)(?:/|$)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, channel_url)
        if match:
            value = match.group(1)
            if key == 'handle' or key == 'c_name':
                return {'handle': f'@{value}'}
            elif key == 'channel_id':
                return {'channel_id': value}
            else:
                return {'handle': f'@{value}'}
    
    # If no pattern matches, assume it's a handle
    if not channel_url.startswith('http'):
        return {'handle': f'@{channel_url}' if not channel_url.startswith('@') else channel_url}
    
    return None


@bp.route('/api/channel/add', methods=['POST'])
@login_required
def add_channel():
    """Add a channel to user's tracked channels."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        data = request.get_json()
        channel_url = data.get('channel_url', '').strip()
        
        if not channel_url:
            return jsonify({'success': False, 'error': 'Channel URL is required'}), 400
        
        # Extract channel info
        channel_info = extract_channel_info(channel_url)
        if not channel_info:
            return jsonify({'success': False, 'error': 'Invalid channel URL format'}), 400
        
        # Check if channel already exists
        existing_channel = None
        if 'channel_id' in channel_info:
            existing_channel = Channel.query.filter_by(yt_channel_id=channel_info['channel_id']).first()
        elif 'handle' in channel_info:
            existing_channel = Channel.query.filter_by(handle=channel_info['handle']).first()
        
        if existing_channel:
            # Check if user already has this channel
            user_channel = UserChannel.query.filter_by(
                user_id=current_user.id,
                channel_id=existing_channel.id
            ).first()
            
            if user_channel:
                return jsonify({'success': False, 'error': 'Channel already added'}), 400
            
            # Add to user's channels
            user_channel = UserChannel(user_id=current_user.id, channel_id=existing_channel.id)
            db.session.add(user_channel)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'channel': {
                    'id': existing_channel.yt_channel_id,
                    'title': existing_channel.title,
                    'handle': existing_channel.handle,
                    'url': channel_url
                }
            })
        
        # Fetch channel info from YouTube
        try:
            # Use async service to get channel details
            async def fetch_channel():
                async with AsyncYouTubeService() as youtube:
                    # This would need implementation in the service
                    # For now, return a placeholder
                    return {
                        'id': channel_info.get('channel_id', 'UC_placeholder'),
                        'title': 'Channel Title',
                        'handle': channel_info.get('handle', '@channel')
                    }
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            channel_data = loop.run_until_complete(fetch_channel())
            
            # Create new channel
            new_channel = Channel(
                yt_channel_id=channel_data['id'],
                title=channel_data['title'],
                handle=channel_data.get('handle'),
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.session.add(new_channel)
            db.session.flush()
            
            # Add to user's channels
            user_channel = UserChannel(user_id=current_user.id, channel_id=new_channel.id)
            db.session.add(user_channel)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'channel': {
                    'id': new_channel.yt_channel_id,
                    'title': new_channel.title,
                    'handle': new_channel.handle,
                    'url': channel_url
                }
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error fetching channel from YouTube: {e}')
            return jsonify({'success': False, 'error': 'Failed to fetch channel information'}), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error adding channel: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/channel/list')
@login_required
def list_channels():
    """List all channels for the current user."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        # Get user's channels
        user_channels = db.session.query(Channel).join(UserChannel).filter(
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
        current_app.logger.error(f'Error listing channels: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/channel/<channel_id>/delete', methods=['DELETE'])
@login_required
def delete_channel(channel_id):
    """Remove a channel from user's tracked channels."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        # Find the channel
        channel = Channel.query.filter_by(yt_channel_id=channel_id).first()
        if not channel:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404
        
        # Check if user has this channel
        user_channel = UserChannel.query.filter_by(
            user_id=current_user.id,
            channel_id=channel.id
        ).first()
        
        if not user_channel:
            return jsonify({'success': False, 'error': 'Channel not in your list'}), 404
        
        # Delete user-channel association
        db.session.delete(user_channel)
        
        # Delete related videos and jobs for this user and channel
        videos = Video.query.filter_by(channel_id=channel.id).all()
        video_ids = [v.yt_video_id for v in videos]
        
        deleted_jobs = 0
        if video_ids:
            # Delete analysis jobs for these videos by this user
            jobs = AnalysisJob.query.filter(
                AnalysisJob.user_id == current_user.id,
                AnalysisJob.video_id.in_(video_ids)
            ).all()
            
            for job in jobs:
                db.session.delete(job)
                deleted_jobs += 1
        
        # Check if any other users have this channel
        other_users = UserChannel.query.filter(
            UserChannel.channel_id == channel.id,
            UserChannel.user_id != current_user.id
        ).count()
        
        deleted_videos = 0
        if other_users == 0:
            # No other users have this channel, safe to delete videos
            for video in videos:
                db.session.delete(video)
                deleted_videos += 1
            
            # Also delete the channel if no one else is using it
            db.session.delete(channel)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Channel removed successfully',
            'deleted_videos': deleted_videos,
            'deleted_jobs': deleted_jobs
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting channel: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/channel/<channel_id>/sync', methods=['POST'])
@login_required
def sync_channel(channel_id):
    """Sync channel videos."""
    guard = require_pro()
    if guard:
        return guard
    
    try:
        # Find the channel
        channel = Channel.query.filter_by(yt_channel_id=channel_id).first()
        if not channel:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404
        
        # Check if user has this channel
        user_channel = UserChannel.query.filter_by(
            user_id=current_user.id,
            channel_id=channel.id
        ).first()
        
        if not user_channel:
            return jsonify({'success': False, 'error': 'Channel not in your list'}), 404
        
        # Update last synced time
        channel.last_synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        
        # TODO: Implement actual video sync logic here
        # This would fetch latest videos from YouTube and update the database
        
        return jsonify({
            'success': True,
            'message': 'Channel sync initiated',
            'channel_id': channel_id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error syncing channel: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500