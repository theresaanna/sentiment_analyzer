"""
Redis cache service for YouTube API responses.
"""
import os
import json
import redis
from typing import Optional, Any
from datetime import timedelta

class CacheService:
    """Service for caching YouTube API responses using Redis."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis connection."""
        # Get Redis URL from environment or use default
        if not redis_url:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        # Get TTL settings from environment
        self.default_ttl_hours = int(os.getenv('REDIS_CACHE_TTL_HOURS', '24'))
        self.comments_ttl_hours = int(os.getenv('REDIS_COMMENTS_TTL_HOURS', '6'))
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            print(f"Redis cache connected successfully to {redis_url}")
            print(f"Cache TTL: Video info={self.default_ttl_hours}h, Comments={self.comments_ttl_hours}h")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"Redis connection failed: {e}. Running without cache.")
            self.redis_client = None
            self.enabled = False
    
    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create a cache key."""
        return f"youtube:{prefix}:{identifier}"
    
    def get(self, prefix: str, identifier: str) -> Optional[Any]:
        """Get cached data."""
        if not self.enabled:
            print(f"Cache disabled - skipping get for {prefix}:{identifier}")
            return None
            
        try:
            key = self._make_key(prefix, identifier)
            data = self.redis_client.get(key)
            if data:
                print(f"✅ Cache HIT: {key}")
                return json.loads(data)
            else:
                print(f"❌ Cache MISS: {key}")
        except Exception as e:
            print(f"Cache get error: {e}")
        return None
    
    def set(self, prefix: str, identifier: str, data: Any, ttl_hours: int = 24) -> bool:
        """Set cached data with TTL."""
        if not self.enabled:
            print(f"Cache disabled - skipping set for {prefix}:{identifier}")
            return False
            
        try:
            key = self._make_key(prefix, identifier)
            serialized = json.dumps(data)
            result = self.redis_client.setex(
                key, 
                timedelta(hours=ttl_hours), 
                serialized
            )
            if result:
                print(f"💾 Cache SET: {key} (TTL: {ttl_hours}h)")
            return result
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, prefix: str, identifier: str) -> bool:
        """Delete cached data."""
        if not self.enabled:
            return False
            
        try:
            key = self._make_key(prefix, identifier)
            return self.redis_client.delete(key) > 0
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all cache entries matching a pattern."""
        if not self.enabled:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear pattern error: {e}")
            return 0
    
    def clear_video_cache(self, video_id: str) -> int:
        """Clear all cache entries for a specific video."""
        if not self.enabled:
            return 0
            
        try:
            # Clear video info and comments cache
            deleted = 0
            for prefix in ['video_info', 'comments_flat', 'comments_threaded']:
                pattern = self._make_key(prefix, video_id) + "*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted += self.redis_client.delete(*keys)
            return deleted
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}
            
        try:
            info = self.redis_client.info('stats')
            keys = self.redis_client.dbsize()
            return {
                "enabled": True,
                "total_keys": keys,
                "hits": info.get('keyspace_hits', 0),
                "misses": info.get('keyspace_misses', 0),
                "hit_rate": round(info.get('keyspace_hits', 0) / 
                                (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1)) * 100, 2)
            }
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {"enabled": False, "error": str(e)}

# Global cache instance
cache = CacheService()
