#!/usr/bin/env python
"""
Test script to demonstrate maximum comment fetching capabilities.

Usage:
    python scripts/test_max_comments.py <video_url_or_id>
"""
import sys
import os
import asyncio
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.enhanced_youtube_service import (
    EnhancedYouTubeService, 
    analyze_comment_coverage,
    fetch_maximum_comments_async
)
from app.services.youtube_service import YouTubeService


def print_separator(title=""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print(f"{'='*60}")


def format_number(num):
    """Format large numbers with commas."""
    return f"{num:,}"


def format_time(seconds):
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.1f} minutes"
    else:
        return f"{seconds/3600:.1f} hours"


def demo_video_analysis(video_id: str):
    """
    Demo video analysis and comment coverage estimation.
    
    Args:
        video_id: YouTube video ID
    """
    print_separator("VIDEO ANALYSIS")
    
    # Extract video ID if URL provided
    if 'youtube.com' in video_id or 'youtu.be' in video_id:
        service = YouTubeService()
        video_id = service.extract_video_id(video_id)
        print(f"Extracted Video ID: {video_id}")
    
    # Analyze comment coverage
    print("\nAnalyzing video and comment feasibility...")
    analysis = analyze_comment_coverage(video_id)
    
    # Display video info
    print_separator("VIDEO INFORMATION")
    print(f"Title: {analysis['video_info']['title']}")
    print(f"Channel: {analysis['video_info']['channel']}")
    print(f"Total Comments: {format_number(analysis['video_info']['total_comments'])}")
    
    # Display fetching strategy
    print_separator("FETCHING STRATEGY")
    strategy = analysis['fetching_strategy']
    print(f"Can Fetch All: {strategy['can_fetch_all']}")
    print(f"Recommended Approach: {strategy['recommended_approach'].upper()}")
    print(f"Estimated Coverage: {strategy['estimated_coverage']:.1f}%")
    print(f"Time Estimate: {format_time(strategy['time_estimate'])}")
    
    # Display API usage
    print_separator("API QUOTA USAGE ESTIMATE")
    api_usage = analysis['api_usage']
    print(f"Estimated API Calls: {format_number(api_usage['estimated_api_calls'])}")
    print(f"Estimated Quota Usage: {format_number(api_usage['estimated_quota_usage'])} units")
    print(f"Percentage of Daily Quota: {api_usage['percentage_of_daily_quota']:.1f}%")
    
    # Display recommendations
    print_separator("RECOMMENDATIONS")
    for i, rec in enumerate(analysis['recommendations'], 1):
        print(f"{i}. {rec}")
    
    return analysis


def demo_fetch_comments(video_id: str, max_comments: int = None):
    """
    Demo fetching maximum comments from a video.
    
    Args:
        video_id: YouTube video ID
        max_comments: Maximum comments to fetch (None for all feasible)
    """
    print_separator("FETCHING COMMENTS")
    
    # Extract video ID if URL provided
    if 'youtube.com' in video_id or 'youtu.be' in video_id:
        service = YouTubeService()
        video_id = service.extract_video_id(video_id)
    
    service = EnhancedYouTubeService()
    
    print(f"Starting comment fetch for video: {video_id}")
    if max_comments:
        print(f"Target: {format_number(max_comments)} comments")
    else:
        print("Target: Maximum feasible comments")
    
    # Fetch comments
    start_time = datetime.now()
    result = service.get_all_available_comments(
        video_id=video_id,
        target_comments=max_comments,
        include_replies=True,
        use_cache=False,  # Don't use cache for testing
        sort_order='relevance'
    )
    end_time = datetime.now()
    
    # Display results
    print_separator("FETCH RESULTS")
    stats = result['statistics']
    print(f"Comments Fetched: {format_number(stats['comments_fetched'])}")
    print(f"Threads Fetched: {format_number(stats['threads_fetched'])}")
    print(f"Replies Fetched: {format_number(stats['replies_fetched'])}")
    print(f"Pages Fetched: {stats['pages_fetched']}")
    print(f"Fetch Time: {format_time(stats['fetch_time_seconds'])}")
    print(f"Speed: {stats['comments_per_second']:.1f} comments/second")
    print(f"Coverage: {stats['fetch_percentage']:.1f}% of total comments")
    print(f"Quota Used: {stats['quota_used']} units")
    
    # Display metadata
    print_separator("FETCH METADATA")
    metadata = result['fetch_metadata']
    print(f"Fetch Complete: {not metadata['incomplete']}")
    print(f"Limited By: {metadata['limited_by'].replace('_', ' ').title()}")
    
    # Sample comments
    print_separator("SAMPLE COMMENTS")
    comments = result['comments'][:5]  # Show first 5 comments
    for i, comment in enumerate(comments, 1):
        print(f"\n{i}. Author: {comment['author']}")
        print(f"   Type: {'Reply' if comment['is_reply'] else 'Top-level'}")
        print(f"   Likes: {comment['likes']}")
        print(f"   Text: {comment['text'][:100]}...")
    
    return result


async def demo_async_fetch(video_id: str, max_comments: int = None):
    """
    Demo async comment fetching for maximum speed.
    
    Args:
        video_id: YouTube video ID
        max_comments: Maximum comments to fetch
    """
    print_separator("ASYNC COMMENT FETCHING")
    
    # Extract video ID if URL provided
    if 'youtube.com' in video_id or 'youtu.be' in video_id:
        service = YouTubeService()
        video_id = service.extract_video_id(video_id)
    
    print(f"Starting async fetch for video: {video_id}")
    
    # Fetch comments asynchronously
    start_time = datetime.now()
    result = await fetch_maximum_comments_async(video_id, max_comments)
    end_time = datetime.now()
    
    # Display results
    print_separator("ASYNC FETCH RESULTS")
    print(f"Total Comments Fetched: {format_number(len(result['comments']))}")
    print(f"Fetch Time: {(end_time - start_time).total_seconds():.2f} seconds")
    print(f"Speed: {len(result['comments']) / (end_time - start_time).total_seconds():.1f} comments/second")
    
    return result


def demo_batch_processing(video_id: str):
    """
    Demo batch processing for memory-efficient analysis.
    
    Args:
        video_id: YouTube video ID
    """
    print_separator("BATCH PROCESSING TEST")
    
    # Extract video ID if URL provided
    if 'youtube.com' in video_id or 'youtu.be' in video_id:
        service = YouTubeService()
        video_id = service.extract_video_id(video_id)
    
    service = EnhancedYouTubeService()
    
    print(f"Fetching comments in batches for video: {video_id}")
    
    # Get comments in batches
    batches = service.get_comment_batches_async(video_id, batch_size=1000)
    
    print(f"Total Batches Created: {len(batches)}")
    
    # Process each batch
    total_processed = 0
    for i, batch in enumerate(batches, 1):
        print(f"Processing Batch {i}: {len(batch)} comments")
        # Here you would run sentiment analysis on each batch
        total_processed += len(batch)
    
    print(f"Total Comments Processed: {format_number(total_processed)}")
    
    return batches


def main():
    """Main function to run tests."""
    if len(sys.argv) < 2:
        print("Usage: python test_max_comments.py <video_url_or_id> [max_comments]")
        print("\nExamples:")
        print("  python test_max_comments.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print("  python test_max_comments.py dQw4w9WgXcQ 5000")
        sys.exit(1)
    
    video_id = sys.argv[1]
    max_comments = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        # Run analysis
        print("\n" + "="*60)
        print("  YouTube Comment Maximum Fetching Test")
        print("="*60)
        
        # Step 1: Analyze video
        analysis = demo_video_analysis(video_id)
        
        # Step 2: Ask user if they want to proceed with fetching
        if analysis['video_info']['total_comments'] > 0:
            print_separator()
            response = input("\nDo you want to fetch comments? (y/n): ")
            
            if response.lower() == 'y':
                # Step 3: Fetch comments
                result = demo_fetch_comments(video_id, max_comments)
                
                # Step 4: Test batch processing
                print_separator()
                response = input("\nTest batch processing? (y/n): ")
                if response.lower() == 'y':
                    demo_batch_processing(video_id)
                
                # Step 5: Test async fetching
                print_separator()
                response = input("\nTest async fetching? (y/n): ")
                if response.lower() == 'y':
                    asyncio.run(demo_async_fetch(video_id, max_comments))
        
        print_separator("TEST COMPLETE")
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
