#!/usr/bin/env python3
"""
Preload worker: consumes jobs from Redis and preloads comments into cache.
- Enforces per-user concurrency (max 3 active).
- Writes progress to youtube:preload_status:<job_id> via CacheService.

Run with: python scripts/preload_worker.py
"""
import os
import sys
import json
import time
from datetime import datetime

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.cache import cache  # noqa: E402
from app.services.enhanced_youtube_service import EnhancedYouTubeService  # noqa: E402

QUEUE_KEY = 'jobs:preload'
ACTIVE_KEY = 'jobs:active:{user_id}'
STATUS_PREFIX = 'preload_status'
MAX_CONCURRENT_PER_USER = 3


def set_status(job_id: str, status: str, progress: int, video_id: str, extra: dict = None):
    data = {'status': status, 'progress': progress, 'video_id': video_id}
    if extra:
        data.update(extra)
    cache.set(STATUS_PREFIX, job_id, data, ttl_hours=6)


def with_active(user_id: int, video_id: str):
    key = ACTIVE_KEY.format(user_id=user_id)
    cache.redis_client.sadd(key, video_id)


def remove_active(user_id: int, video_id: str):
    key = ACTIVE_KEY.format(user_id=user_id)
    cache.redis_client.srem(key, video_id)


def active_count(user_id: int) -> int:
    key = ACTIVE_KEY.format(user_id=user_id)
    try:
        return cache.redis_client.scard(key)
    except Exception:
        return 0


def check_cancelled(job_id: str) -> bool:
    """Check if a job has been cancelled."""
    cancel_key = f"jobs:cancel:{job_id}"
    try:
        return cache.redis_client.exists(cancel_key) > 0
    except Exception:
        return False


def process_job(job: dict):
    job_type = job.get('type', 'preload')
    job_id = job['job_id']
    user_id = int(job['user_id'])

    try:
        # Check if job was cancelled before starting
        if check_cancelled(job_id):
            set_status(job_id, 'cancelled', 0, job.get('video_id') or job.get('yt_channel_id', ''), {
                'job_type': job_type,
                'cancelled_at': datetime.utcnow().isoformat() + 'Z'
            })
            print(f"Job {job_id} was cancelled before starting")
            return
        
        # Enforce per-user concurrency gate
        if active_count(user_id) >= MAX_CONCURRENT_PER_USER:
            cache.redis_client.rpush(QUEUE_KEY, json.dumps(job))
            time.sleep(1)
            return

        if job_type == 'preload':
            video_id = job['video_id']
            target = job.get('target_comments')
            with_active(user_id, video_id)
            set_status(job_id, 'fetching', 10, video_id, {'job_type': 'preload'})
            
            # Check for cancellation again after marking as active
            if check_cancelled(job_id):
                set_status(job_id, 'cancelled', 10, video_id, {
                    'job_type': 'preload',
                    'cancelled_at': datetime.utcnow().isoformat() + 'Z'
                })
                remove_active(user_id, video_id)
                print(f"Job {job_id} was cancelled during processing")
                return

            # Run comment fetching with progress updates
            import threading
            yt = EnhancedYouTubeService()
            result = None
            fetch_complete = threading.Event()
            
            def fetch_comments():
                nonlocal result
                result = yt.get_all_available_comments(
                    video_id=video_id,
                    target_comments=target,
                    include_replies=True,
                    use_cache=True,
                    sort_order='relevance'
                )
                fetch_complete.set()
            
            # Start fetching in a thread
            fetch_thread = threading.Thread(target=fetch_comments)
            fetch_thread.start()
            
            # Update progress while fetching
            progress = 10
            while not fetch_complete.is_set():
                # Check for cancellation
                if check_cancelled(job_id):
                    set_status(job_id, 'cancelled', progress, video_id, {
                        'job_type': 'preload',
                        'cancelled_at': datetime.utcnow().isoformat() + 'Z'
                    })
                    remove_active(user_id, video_id)
                    print(f"Job {job_id} was cancelled during fetching")
                    return
                
                # Increment progress gradually (up to 90%)
                if progress < 90:
                    progress += 5
                    set_status(job_id, 'fetching', progress, video_id, {'job_type': 'preload'})
                
                # Wait a bit before next update
                fetch_complete.wait(timeout=2)
            
            # Wait for thread to complete
            fetch_thread.join(timeout=60)  # Max 60 seconds
            
            if result is None:
                raise Exception("Failed to fetch comments")

            comments = result['comments']
            stats = result['statistics']
            
            # Check for cancellation after fetching
            if check_cancelled(job_id):
                set_status(job_id, 'cancelled', 90, video_id, {
                    'job_type': 'preload',
                    'cancelled_at': datetime.utcnow().isoformat() + 'Z',
                    'note': 'Cancelled after fetching comments'
                })
                remove_active(user_id, video_id)
                print(f"Job {job_id} was cancelled after fetching")
                return

            preload_key = f"{video_id}:max:{target or 'all'}:True:relevance"
            cache.set('enhanced_comments', preload_key, result, ttl_hours=12)
            alias_targets = []
            if target:
                alias_targets.append(str(target))
            else:
                alias_targets.extend(['1000'])
            for t in alias_targets:
                alias_key = f"{video_id}:max:{t}:True:relevance"
                cache.set('enhanced_comments', alias_key, result, ttl_hours=12)

            set_status(job_id, 'completed', 100, video_id, {
                'fetched': len(comments),
                'percentage': stats.get('fetch_percentage', 0),
                'job_type': 'preload'
            })
            remove_active(user_id, video_id)

        elif job_type == 'channel_sync':
            yt_channel_id = job['yt_channel_id']
            
            # Check for cancellation before syncing
            if check_cancelled(job_id):
                set_status(job_id, 'cancelled', 0, yt_channel_id, {
                    'job_type': 'channel_sync',
                    'cancelled_at': datetime.utcnow().isoformat() + 'Z'
                })
                print(f"Channel sync job {job_id} was cancelled")
                return
            
            # Use ChannelService incremental sync in-process
            from app.services.channel_service import ChannelService
            svc = ChannelService()
            set_status(job_id, 'syncing', 10, yt_channel_id, {'job_type': 'channel_sync'})
            
            # Check again after starting
            if check_cancelled(job_id):
                set_status(job_id, 'cancelled', 10, yt_channel_id, {
                    'job_type': 'channel_sync',
                    'cancelled_at': datetime.utcnow().isoformat() + 'Z'
                })
                print(f"Channel sync job {job_id} was cancelled during sync")
                return
            
            result = svc.check_and_sync_channel(yt_channel_id, refresh=True)
            set_status(job_id, 'completed', 100, yt_channel_id, {
                'job_type': 'channel_sync',
                'synced': result.get('synced', False),
                'added': result.get('added', 0),
                'new_latest_video_id': result.get('new_latest_video_id')
            })
        else:
            # Unknown type: mark as error
            set_status(job_id, 'error', 0, job.get('video_id') or job.get('yt_channel_id', ''), {
                'error': f"Unknown job type: {job_type}",
                'job_type': job_type
            })
    except Exception as e:
        set_status(job_id, 'error', 0, job.get('video_id') or job.get('yt_channel_id', ''), {'error': str(e), 'job_type': job_type})


def main():
    print('🚀 Preload Worker started')
    if not cache.enabled:
        print('Redis cache not enabled; exiting.')
        return
    while True:
        try:
            # BRPOP blocks; use timeout to allow graceful loop
            item = cache.redis_client.brpop(QUEUE_KEY, timeout=5)
            if not item:
                continue
            _, raw = item
            try:
                job = json.loads(raw)
            except Exception:
                print('Invalid job JSON, skipping')
                continue
            process_job(job)
        except KeyboardInterrupt:
            print('Shutdown requested, exiting worker.')
            break
        except Exception as e:
            print(f'Worker error: {e}')
            time.sleep(1)


if __name__ == '__main__':
    main()
