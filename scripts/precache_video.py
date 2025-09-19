#!/usr/bin/env python3
"""
Precache a YouTube video's metadata and initial comments into Redis for fast analyze-page loads.

This warms:
- youtube:video_info:<video_id> (24h)
- youtube:enhanced_comments:<video_id>:max:2500:False:relevance (24h)
- Optionally: youtube:comments_flat:<video_id>:2500 (6h default)

Usage:
  python scripts/precache_video.py dQw4w9WgXcQ [--comments 2500] [--include-replies false] [--sort relevance]
  python scripts/precache_video.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

Environment:
  - Requires YOUTUBE_API_KEY set
  - Uses REDIS_URL (defaults to redis://localhost:6379/0)
  - Honors REDIS_CACHE_TTL_HOURS for video info; this script forces 24h for the enhanced payload by re-setting it
"""
import argparse
import os
import sys
from typing import Optional

# Ensure app package is importable when run as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.cache import cache  # noqa: E402
from app.services.youtube_service import YouTubeService  # noqa: E402
from app.services.enhanced_youtube_service import EnhancedYouTubeService  # noqa: E402
from app.utils.youtube import extract_video_id as extract_id  # noqa: E402


def normalize_video_id(input_str: str) -> Optional[str]:
    # Accept either a raw ID or a URL
    if not input_str:
        return None
    if len(input_str) in (11, 12) and all(c.isalnum() or c in ['-', '_'] for c in input_str):
        return input_str[:11]
    return extract_id(input_str)


def main():
    parser = argparse.ArgumentParser(description="Precache YouTube data into Redis")
    parser.add_argument("video", help="YouTube video ID or URL")
    parser.add_argument("--comments", type=int, default=2500, help="Target number of comments to warm (default: 2500)")
    parser.add_argument("--include-replies", dest="include_replies", default="false",
                        choices=["true", "false", "1", "0"], help="Include replies in warm cache (default: false)")
    parser.add_argument("--sort", default="relevance", choices=["relevance", "time"], help="Sort order for comments")
    parser.add_argument("--also-flat", action="store_true", help="Also warm comments_flat cache (optional)")
    args = parser.parse_args()

    video_id = normalize_video_id(args.video)
    if not video_id:
        print("Error: could not extract a valid video ID from input")
        sys.exit(2)

    include_replies = str(args.include_replies).lower() in ("true", "1")
    target = max(5, int(args.comments))

    if not cache.enabled:
        print("Redis cache is not enabled; set REDIS_URL or start Redis.")
        sys.exit(1)

    # Ensure API key present
    if not os.getenv("YOUTUBE_API_KEY"):
        print("Error: YOUTUBE_API_KEY is not set in environment")
        sys.exit(3)

    print(f"🔥 Prewarming cache for video {video_id} → {target} comments (include_replies={include_replies}, sort={args.sort})")

    yt = YouTubeService()
    eyt = EnhancedYouTubeService()

    # 1) Warm video info (24h via service default)
    info = yt.get_video_info(video_id, use_cache=True)
    print(f"  ✓ video_info cached: {info.get('title','<unknown>')} by {info.get('channel','<unknown>')}")

    # 2) Warm enhanced comments result used by analyze flow
    result = eyt.get_all_available_comments(
        video_id=video_id,
        target_comments=target,
        include_replies=include_replies,
        use_cache=True,
        sort_order=args.sort,
    )
    comments_count = len(result.get("comments", []))
    print(f"  ✓ enhanced_comments cached: {comments_count} comments")

    # Force a 24h TTL on the enhanced payload so daily refresh keeps it hot all day
    # Key format must match EnhancedYouTubeService implementation
    enhanced_key = f"{video_id}:max:{target or 'all'}:{include_replies}:{args.sort}"
    cache.set("enhanced_comments", enhanced_key, result, ttl_hours=24)

    # 3) Optionally warm comments_flat for 2500 as a secondary cache path
    if args.also_flat:
        flat = yt.get_all_comments_flat(video_id, max_comments=target, use_cache=True)
        print(f"  ✓ comments_flat cached: {len(flat)} comments")

    print("✅ Precache complete")


if __name__ == "__main__":
    main()