#!/usr/bin/env python
"""
Clear all user data including channels, videos, and Redis jobs.
Usage: python scripts/clear_user_data.py <user_email>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Channel, Video, UserChannel
from app.cache import cache

def clear_user_data(email):
    """Clear all data for a specific user."""
    app = create_app()
    
    with app.app_context():
        # Find the user
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ User with email '{email}' not found")
            return
        
        print(f"🔍 Found user: {user.name} ({user.email})")
        
        # Get all user's channels
        user_channels = db.session.query(UserChannel, Channel).join(
            Channel, UserChannel.channel_id == Channel.id
        ).filter(
            UserChannel.user_id == user.id
        ).all()
        
        channels_deleted = 0
        videos_deleted = 0
        
        for uc, channel in user_channels:
            print(f"  📺 Removing channel: {channel.title}")
            
            # Count videos
            video_count = Video.query.filter_by(channel_id=channel.id).count()
            videos_deleted += video_count
            
            # Delete videos for this channel
            Video.query.filter_by(channel_id=channel.id).delete()
            
            # Delete user-channel association
            db.session.delete(uc)
            
            # Check if other users have this channel
            other_users = UserChannel.query.filter_by(channel_id=channel.id).count()
            if other_users == 0:
                # No other users, delete the channel
                db.session.delete(channel)
            
            channels_deleted += 1
        
        # Clear Redis jobs
        jobs_cleared = 0
        if cache.enabled:
            try:
                # Clear user's job list
                user_key = f"jobs:by_user:{user.id}"
                job_ids = cache.redis_client.lrange(user_key, 0, -1) or []
                
                for job_id in job_ids:
                    # Delete job status
                    cache.delete('preload_status', job_id)
                    
                    # Set cancel marker if job might be running
                    cancel_key = f"jobs:cancel:{job_id}"
                    cache.redis_client.setex(cancel_key, 3600, '1')
                    
                    jobs_cleared += 1
                
                # Clear the user's job list
                cache.redis_client.delete(user_key)
                
                # Clear active jobs set
                active_key = f"jobs:active:{user.id}"
                cache.redis_client.delete(active_key)
                
                print(f"  🗑️  Cleared {jobs_cleared} Redis jobs")
            except Exception as e:
                print(f"  ⚠️  Error clearing Redis jobs: {e}")
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n✅ Successfully cleared data for {user.name}:")
        print(f"  - {channels_deleted} channels removed")
        print(f"  - {videos_deleted} videos deleted")
        print(f"  - {jobs_cleared} jobs cleared")
        print(f"\n🎉 Fresh start ready!")

def clear_all_jobs():
    """Clear ALL jobs from Redis (use with caution)."""
    app = create_app()
    
    with app.app_context():
        if not cache.enabled:
            print("❌ Redis cache is not enabled")
            return
        
        try:
            # Get all job keys
            pattern = "youtube:preload_status:*"
            keys = cache.redis_client.keys(pattern)
            
            jobs_deleted = 0
            for key in keys:
                cache.redis_client.delete(key)
                jobs_deleted += 1
            
            # Clear all user job lists
            pattern = "jobs:by_user:*"
            keys = cache.redis_client.keys(pattern)
            for key in keys:
                cache.redis_client.delete(key)
            
            # Clear all active job sets
            pattern = "jobs:active:*"
            keys = cache.redis_client.keys(pattern)
            for key in keys:
                cache.redis_client.delete(key)
            
            # Clear the main job queue
            cache.redis_client.delete("jobs:preload")
            
            print(f"✅ Cleared {jobs_deleted} jobs from Redis")
            print("✅ Cleared all user job lists and active sets")
            print("✅ Cleared main job queue")
            
        except Exception as e:
            print(f"❌ Error clearing jobs: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clear_user_data.py <user_email>")
        print("   or: python scripts/clear_user_data.py --all-jobs")
        sys.exit(1)
    
    if sys.argv[1] == "--all-jobs":
        print("⚠️  Clearing ALL jobs from Redis...")
        clear_all_jobs()
    else:
        email = sys.argv[1]
        print(f"🧹 Clearing all data for user: {email}")
        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() == 'yes':
            clear_user_data(email)
        else:
            print("❌ Cancelled")
