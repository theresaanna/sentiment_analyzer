#!/usr/bin/env python
"""
Clean up orphaned channels (channels with no user associations).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Channel, Video, UserChannel

def clean_orphaned_channels():
    """Remove channels that have no user associations."""
    app = create_app()
    
    with app.app_context():
        # Find all channels that don't have any user associations
        orphaned_channels = db.session.query(Channel).outerjoin(
            UserChannel, Channel.id == UserChannel.channel_id
        ).filter(
            UserChannel.id == None
        ).all()
        
        if not orphaned_channels:
            print("✅ No orphaned channels found")
            return
        
        print(f"🔍 Found {len(orphaned_channels)} orphaned channels:")
        
        total_videos = 0
        for channel in orphaned_channels:
            video_count = Video.query.filter_by(channel_id=channel.id).count()
            total_videos += video_count
            print(f"  - {channel.title} ({channel.yt_channel_id}): {video_count} videos")
        
        confirm = input(f"\n⚠️  Delete {len(orphaned_channels)} channels and {total_videos} videos? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ Cancelled")
            return
        
        # Delete videos and channels
        for channel in orphaned_channels:
            # Delete all videos for this channel
            Video.query.filter_by(channel_id=channel.id).delete()
            # Delete the channel
            db.session.delete(channel)
        
        db.session.commit()
        
        print(f"✅ Deleted {len(orphaned_channels)} orphaned channels and {total_videos} videos")
        print("🎉 Database cleaned!")

if __name__ == "__main__":
    clean_orphaned_channels()
