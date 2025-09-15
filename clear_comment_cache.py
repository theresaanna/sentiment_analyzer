#!/usr/bin/env python3
"""
Clear all enhanced comment caches to force recalculation with fixed statistics.
"""
from app.cache import cache

def clear_all_comment_caches():
    """Clear all enhanced comment caches."""
    if not cache.enabled:
        print("Cache is not enabled")
        return
    
    print("Clearing all enhanced comment caches...")
    
    # Clear all enhanced_comments entries
    pattern = "enhanced_comments:*"
    deleted_count = 0
    
    try:
        # Get all keys matching the pattern
        keys = cache.redis_client.keys(pattern)
        if keys:
            for key in keys:
                cache.redis_client.delete(key)
                deleted_count += 1
                print(f"  Deleted: {key.decode() if isinstance(key, bytes) else key}")
        
        # Also clear preload_status entries
        pattern2 = "youtube:preload_status:*"
        keys2 = cache.redis_client.keys(pattern2)
        if keys2:
            for key in keys2:
                cache.redis_client.delete(key)
                deleted_count += 1
                print(f"  Deleted: {key.decode() if isinstance(key, bytes) else key}")
        
        print(f"\nCleared {deleted_count} cache entries")
        print("\nThe next time you load any video, it will:")
        print("  1. Recalculate with the fixed coverage percentage")
        print("  2. Show '100% coverage' when all comments are fetched")
        print("  3. Display accurate statistics")
        
    except Exception as e:
        print(f"Error clearing cache: {e}")

if __name__ == "__main__":
    clear_all_comment_caches()