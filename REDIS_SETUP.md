# Redis Cache Setup

Redis caching significantly improves the performance of the YouTube Sentiment Analyzer by caching API responses.

## Performance Benefits
- **Video Info**: ~30x faster (0.4s → 0.01s)
- **Comments**: ~500x faster (15s → 0.03s)
- Reduces YouTube API quota usage
- Instant page loads for previously analyzed videos

## Local Redis Setup

### macOS
```bash
# Install Redis using Homebrew
brew install redis

# Start Redis service
brew services start redis

# Or run Redis in foreground
redis-server

# Test Redis connection
redis-cli ping
# Should return: PONG
```

### Ubuntu/Debian
```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis

# Test connection
redis-cli ping
```

### Windows
Use WSL2 or Docker:
```bash
# Using Docker
docker run -d -p 6379:6379 redis

# Or install in WSL2
wsl
sudo apt install redis-server
```

## Environment Variables

Add these to your `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0  # Local Redis (default)

# Cache TTL Settings (in hours)
REDIS_CACHE_TTL_HOURS=24   # Video info cache duration
REDIS_COMMENTS_TTL_HOURS=6  # Comments cache duration
```

## Using Redis Cloud (Free Tier)

1. Sign up at [Redis Cloud](https://redis.com/try-free/)
2. Create a free database (30MB)
3. Copy your connection string
4. Update `.env`:
```env
REDIS_URL=redis://default:your-password@your-endpoint.ec2.cloud.redislabs.com:12345
```

## Disable Redis (Fallback Mode)

If Redis is not available, the app will work without caching:
```env
# Comment out or remove REDIS_URL to disable caching
# REDIS_URL=redis://localhost:6379/0
```

## Cache Management

### View Cache Statistics
```bash
curl http://localhost:8000/api/cache/stats
```

### Clear Cache for a Video
```bash
curl -X POST http://localhost:8000/api/cache/clear/VIDEO_ID
```

### Clear All Cache (Redis CLI)
```bash
redis-cli FLUSHDB
```

## Monitoring

### Check Redis is Running
```bash
redis-cli ping
```

### Monitor Redis in Real-time
```bash
redis-cli monitor
```

### View Cache Keys
```bash
redis-cli KEYS "youtube:*"
```

### View Specific Cached Item
```bash
redis-cli GET "youtube:video_info:dQw4w9WgXcQ"
```

## Troubleshooting

### Redis Connection Failed
- Check Redis is running: `redis-cli ping`
- Check port 6379 is not blocked
- Verify REDIS_URL in `.env`

### Cache Not Working
- Check Flask console for "Redis cache connected successfully"
- Verify cache stats: `curl http://localhost:8000/api/cache/stats`
- Check Redis has available memory: `redis-cli INFO memory`

### Clear Corrupted Cache
```bash
redis-cli
> KEYS youtube:*
> DEL youtube:video_info:VIDEO_ID
> DEL youtube:comments_flat:VIDEO_ID:100
```

## Default Settings
- **Video Info TTL**: 24 hours
- **Comments TTL**: 6 hours
- **Cache Key Format**: `youtube:type:video_id:params`
- **Max Memory Policy**: allkeys-lru (recommended)

## Performance Testing
Run the included test script:
```bash
python test_cache.py
```

This will show before/after cache performance metrics.
