#!/usr/bin/env python
"""
Test Redis Cloud connection
"""
import os
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_redis_cloud():
    """Test connection to Redis Cloud."""
    redis_url = os.getenv('REDIS_URL')
    
    if not redis_url:
        print("❌ REDIS_URL not found in .env file")
        assert False, "REDIS_URL not found in .env file"
    
    # Mask password in output
    if '@' in redis_url:
        display_url = redis_url.split('@')[1]
        print(f"🔗 Connecting to Redis Cloud: {display_url}")
    else:
        print(f"🔗 Connecting to: {redis_url}")
    
    try:
        # Create connection
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Test ping
        r.ping()
        print("✅ Successfully connected to Redis Cloud!")
        
        # Get server info
        info = r.info('server')
        print(f"📊 Redis Version: {info.get('redis_version', 'Unknown')}")
        
        # Test basic operations
        test_key = "test:connection"
        r.set(test_key, "Hello from Python!", ex=60)  # Expires in 60 seconds
        value = r.get(test_key)
        print(f"✅ Write/Read test successful: {value}")
        
        # Check memory usage
        memory_info = r.info('memory')
        used_memory = memory_info.get('used_memory_human', 'Unknown')
        max_memory = memory_info.get('maxmemory_human', 'Unknown')
        print(f"💾 Memory: {used_memory} used")
        if max_memory != '0B':
            print(f"💾 Max Memory: {max_memory}")
        
        # Count existing keys
        key_count = r.dbsize()
        print(f"🔑 Total keys in database: {key_count}")
        
        # List YouTube cache keys if any
        youtube_keys = r.keys("youtube:*")
        if youtube_keys:
            print(f"📺 YouTube cache keys found: {len(youtube_keys)}")
            for key in youtube_keys[:5]:  # Show first 5
                print(f"   - {key}")
            if len(youtube_keys) > 5:
                print(f"   ... and {len(youtube_keys) - 5} more")
        
    except redis.ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your password is correct in .env")
        print("2. Verify the Redis Cloud instance is active")
        print("3. Check firewall/network settings")
        assert False, f"Connection failed: {e}"
        
    except redis.AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("\n🔧 Make sure your password is correct in .env:")
        print("   REDIS_URL=redis://default:YOUR_PASSWORD@redis-18130...")
        assert False, f"Authentication failed: {e}"
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        assert False, f"Unexpected error: {e}"

if __name__ == "__main__":
    print("🚀 Redis Cloud Connection Test\n")
    print("-" * 50)
    
    success = test_redis_cloud()
    
    print("-" * 50)
    if success:
        print("\n✅ Redis Cloud is ready to use!")
        print("\n📝 Next steps:")
        print("1. Restart your Flask app to use Redis Cloud")
        print("2. Access http://localhost:8000")
        print("3. Analyze a video - it will be cached in Redis Cloud")
        print("4. Check cache stats: curl http://localhost:8000/api/cache/stats")
    else:
        print("\n❌ Redis Cloud connection failed")
        print("\n📝 Please check:")
        print("1. Your password is correctly set in .env")
        print("2. The Redis Cloud instance is active")
        print("3. No quotes around the password in .env")
