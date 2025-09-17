#!/usr/bin/env python3
"""
Debug script to diagnose YouTube API commentThread errors.

This script tests various YouTube API calls to identify the source of the 
"commentThread resource in the request body" error.
"""
import os
import sys
import traceback
from pprint import pprint

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.youtube_service import YouTubeService
from app.utils.youtube import extract_video_id, validate_video_id
from googleapiclient.errors import HttpError


def test_video_id_extraction():
    """Test video ID extraction from various URL formats."""
    print("=== Testing Video ID Extraction ===")
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ", 
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "dQw4w9WgXcQ",  # Direct ID
        "https://www.youtube.com/watch?v=invalid_id_123",  # Invalid
        "not_a_url_at_all",  # Invalid
    ]
    
    for url in test_urls:
        video_id = extract_video_id(url)
        valid = validate_video_id(video_id) if video_id else False
        print(f"URL: {url}")
        print(f"  Extracted ID: {video_id}")
        print(f"  Valid: {valid}")
        print()


def test_video_info(youtube_service, video_id):
    """Test getting video information."""
    print(f"=== Testing Video Info for {video_id} ===")
    
    try:
        video_info = youtube_service.get_video_info(video_id, use_cache=False)
        print(f"✓ Video info retrieved successfully")
        print(f"  Title: {video_info['title']}")
        print(f"  Channel: {video_info['channel']}")
        print(f"  Views: {video_info['statistics']['views']:,}")
        print(f"  Comments: {video_info['statistics']['comments']:,}")
        print(f"  Likes: {video_info['statistics']['likes']:,}")
        return video_info
        
    except Exception as e:
        print(f"✗ Error getting video info: {e}")
        print(f"  Exception type: {type(e).__name__}")
        traceback.print_exc()
        return None


def test_comment_threads_direct_api(youtube_service, video_id):
    """Test direct API call to commentThreads."""
    print(f"=== Testing Direct commentThreads API for {video_id} ===")
    
    try:
        # Make a minimal request to commentThreads
        request = youtube_service.youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=5,
            textFormat='plainText',
            order='relevance'
        )
        
        print(f"API Request URL: {request.uri}")
        print(f"Request method: {request.method}")
        print(f"Request body: {request.body}")
        
        response = request.execute()
        print(f"✓ Direct API call successful")
        print(f"  Items returned: {len(response.get('items', []))}")
        print(f"  Total results: {response.get('pageInfo', {}).get('totalResults', 'unknown')}")
        
        if response.get('items'):
            first_comment = response['items'][0]['snippet']['topLevelComment']['snippet']
            print(f"  First comment author: {first_comment['authorDisplayName']}")
            print(f"  First comment text: {first_comment['textDisplay'][:100]}...")
        
        return True
        
    except HttpError as e:
        print(f"✗ HTTP Error: {e}")
        print(f"  Status: {e.resp.status}")
        print(f"  Reason: {e.resp.reason}")
        
        # Try to get detailed error info
        try:
            error_details = e.error_details
            print(f"  Error details: {error_details}")
        except:
            pass
            
        # Print the raw response for debugging
        try:
            print(f"  Raw response: {e.resp}")
        except:
            pass
            
        return False
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        print(f"  Exception type: {type(e).__name__}")
        traceback.print_exc()
        return False


def test_service_method(youtube_service, video_id):
    """Test the service's get_comment_threads method."""
    print(f"=== Testing Service get_comment_threads for {video_id} ===")
    
    try:
        threads = youtube_service.get_comment_threads(video_id, max_comments=5, use_cache=False)
        print(f"✓ Service method successful")
        print(f"  Threads returned: {len(threads)}")
        
        if threads:
            first_thread = threads[0]
            print(f"  First thread ID: {first_thread['id']}")
            print(f"  First comment author: {first_thread['comment']['author']}")
            print(f"  Reply count: {first_thread['reply_count']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Service method error: {e}")
        print(f"  Exception type: {type(e).__name__}")
        traceback.print_exc()
        return False


def test_known_videos():
    """Test with known working YouTube videos."""
    print("=== Testing Known Videos ===")
    
    # Known working videos (popular, public, comments enabled)
    test_videos = [
        "dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up
        "9bZkp7q19f0",  # PSY - GANGNAM STYLE
        "kJQP7kiw5Fk",  # Luis Fonsi - Despacito
        "fJ9rUzIMcZQ",  # Queen - Bohemian Rhapsody
    ]
    
    try:
        youtube_service = YouTubeService()
        print(f"✓ YouTube service initialized")
        print(f"  API Key present: {'Yes' if youtube_service.api_key else 'No'}")
        print()
        
        for video_id in test_videos:
            print(f"--- Testing video: {video_id} ---")
            
            # Test video info first
            video_info = test_video_info(youtube_service, video_id)
            if not video_info:
                print(f"Skipping comment tests for {video_id} (video info failed)")
                continue
            
            # Test direct API call
            direct_success = test_comment_threads_direct_api(youtube_service, video_id)
            
            # Test service method
            if direct_success:
                service_success = test_service_method(youtube_service, video_id)
            
            print("-" * 50)
            print()
            
            # If one video works, we can stop testing
            if direct_success:
                print(f"✓ Found working video: {video_id}")
                break
                
    except Exception as e:
        print(f"✗ Failed to initialize YouTube service: {e}")
        traceback.print_exc()


def check_environment():
    """Check environment configuration."""
    print("=== Environment Check ===")
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    print(f"YOUTUBE_API_KEY present: {'Yes' if api_key else 'No'}")
    if api_key:
        print(f"API Key length: {len(api_key)}")
        print(f"API Key starts with: {api_key[:10]}...")
    print()


def main():
    """Main diagnostic function."""
    print("YouTube API Diagnostic Script")
    print("=" * 50)
    print()
    
    # Check environment
    check_environment()
    
    # Test video ID extraction
    test_video_id_extraction()
    
    # Test known videos
    test_known_videos()
    
    print("Diagnostic complete!")


if __name__ == "__main__":
    main()