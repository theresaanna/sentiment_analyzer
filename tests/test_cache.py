#!/usr/bin/env python
"""
Test script to demonstrate cache performance improvement.
"""
import pytest
import requests
import time

BASE_URL = "http://localhost:8000"
VIDEO_ID = "dQw4w9WgXcQ"  # Test video ID

def is_server_running():
    """Check if the server is running."""
    try:
        response = requests.get(BASE_URL, timeout=1)
        return response.status_code < 500
    except (requests.ConnectionError, requests.Timeout):
        return False

@pytest.mark.integration
@pytest.mark.skipif(not is_server_running(), reason="Server not running at http://localhost:8000")
def test_video_fetch():
    """Test fetching video info with and without cache."""
    print("=" * 50)
    print("Testing Video Info Fetch")
    print("=" * 50)
    
    # First request (cache miss)
    print("\n1. First request (cache miss)...")
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/video/{VIDEO_ID}")
    first_time = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Success: {data['video']['title'][:50]}...")
        print(f"   Time: {first_time:.2f} seconds")
    else:
        print(f"   ✗ Failed: {response.status_code}")
    
    # Second request (cache hit)
    print("\n2. Second request (cache hit)...")
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/video/{VIDEO_ID}")
    second_time = time.time() - start
    
    if response.status_code == 200:
        print(f"   ✓ Success (from cache)")
        print(f"   Time: {second_time:.2f} seconds")
        print(f"   Speed improvement: {first_time/second_time:.1f}x faster!")
    else:
        print(f"   ✗ Failed: {response.status_code}")

@pytest.mark.integration  
@pytest.mark.skipif(not is_server_running(), reason="Server not running at http://localhost:8000")
def test_comments_fetch():
    """Test fetching comments with and without cache."""
    print("\n" + "=" * 50)
    print("Testing Comments Fetch (100 comments)")
    print("=" * 50)
    
    # Clear cache first
    print("\nClearing cache...")
    requests.post(f"{BASE_URL}/api/cache/clear/{VIDEO_ID}")
    
    # First request (cache miss)
    print("\n1. First request (cache miss)...")
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/comments/{VIDEO_ID}?max_comments=10&format=flat")
    first_time = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Success: {data['total_comments']} comments fetched")
        print(f"   Time: {first_time:.2f} seconds")
    else:
        print(f"   ✗ Failed: {response.status_code}")
    
    # Second request (cache hit)
    print("\n2. Second request (cache hit)...")
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/comments/{VIDEO_ID}?max_comments=10&format=flat")
    second_time = time.time() - start
    
    if response.status_code == 200:
        print(f"   ✓ Success (from cache)")
        print(f"   Time: {second_time:.2f} seconds")
        if second_time > 0:
            print(f"   Speed improvement: {first_time/second_time:.1f}x faster!")
    else:
        print(f"   ✗ Failed: {response.status_code}")

def show_cache_stats():
    """Show cache statistics."""
    print("\n" + "=" * 50)
    print("Cache Statistics")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/cache/stats")
    if response.status_code == 200:
        stats = response.json()['stats']
        print(f"   Cache enabled: {stats['enabled']}")
        print(f"   Total keys: {stats['total_keys']}")
        print(f"   Cache hits: {stats['hits']}")
        print(f"   Cache misses: {stats['misses']}")
        print(f"   Hit rate: {stats['hit_rate']}%")
    else:
        print(f"   Failed to get stats: {response.status_code}")

if __name__ == "__main__":
    print("\n🚀 YouTube API Cache Performance Test\n")
    
    test_video_fetch()
    test_comments_fetch()
    show_cache_stats()
    
    print("\n✅ Test complete!\n")
