#!/usr/bin/env python
"""
Test script to verify the enhanced YouTube comment fetching integration.

This script tests that all the enhanced features are properly integrated
and working together in the application.
"""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.enhanced_youtube_service import EnhancedYouTubeService
from app.science.sentiment_analyzer import SentimentAnalyzer
from app.main.forms import EnhancedYouTubeURLForm
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_enhanced_service():
    """Test the enhanced YouTube service."""
    print("\n" + "="*60)
    print("Testing Enhanced YouTube Service")
    print("="*60)
    
    try:
        service = EnhancedYouTubeService()
        print("✓ Enhanced service initialized successfully")
        
        # Test with a sample video ID (you can change this)
        test_video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
        
        print(f"\nTesting with video ID: {test_video_id}")
        
        # Test video info fetching
        video_info = service.get_video_info(test_video_id)
        print(f"✓ Video found: {video_info['title']}")
        print(f"  Total comments available: {video_info['statistics']['comments']:,}")
        
        # Test enhanced comment fetching (with small limit for testing)
        result = service.get_all_available_comments(
            video_id=test_video_id,
            target_comments=50,  # Small number for testing
            include_replies=True,
            use_cache=False
        )
        
        print(f"✓ Comments fetched: {len(result['comments'])}")
        print(f"  Fetch percentage: {result['statistics']['fetch_percentage']:.1f}%")
        print(f"  Fetch time: {result['statistics']['fetch_time_seconds']:.2f}s")
        print(f"  Comments per second: {result['statistics']['comments_per_second']:.1f}")
        
    except Exception as e:
        print(f"✗ Error testing enhanced service: {e}")
        assert False, f"Error testing enhanced service: {e}"


def test_batch_sentiment_analysis():
    """Test batch processing in sentiment analyzer."""
    print("\n" + "="*60)
    print("Testing Batch Sentiment Analysis")
    print("="*60)
    
    try:
        # Initialize analyzer with batch processing
        analyzer = SentimentAnalyzer(batch_size=10)
        print("✓ Sentiment analyzer initialized with batch processing")
        
        # Create test texts
        test_texts = [
            "This video is absolutely amazing!",
            "I hate this content",
            "Not sure how I feel about this",
            "Best video ever!",
            "Terrible quality",
            "It's okay I guess",
            "Love it so much!",
            "Worst thing I've ever seen",
            "Pretty good overall",
            "Could be better",
            "Fantastic work!",
            "Disappointing",
            "Average content",
            "Excellent presentation!",
            "Not my cup of tea"
        ]
        
        print(f"\nAnalyzing {len(test_texts)} test comments...")
        
        # Test batch analysis
        results = analyzer.analyze_batch(test_texts)
        
        print(f"✓ Batch analysis completed")
        print(f"  Total analyzed: {results['total_analyzed']}")
        print(f"  Positive: {results['sentiment_counts']['positive']}")
        print(f"  Neutral: {results['sentiment_counts']['neutral']}")
        print(f"  Negative: {results['sentiment_counts']['negative']}")
        print(f"  Average confidence: {results['average_confidence']:.2f}")
        
        # Check if batch processing was used for large dataset
        if 'batch_processing' in results:
            print(f"  Batch processing: {results['batch_processing']}")
            print(f"  Batch size: {results.get('batch_size', 'N/A')}")
        
    except Exception as e:
        print(f"✗ Error testing batch sentiment analysis: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Error testing batch sentiment analysis: {e}"


def test_forms():
    """Test the enhanced forms."""
    print("\n" + "="*60)
    print("Testing Enhanced Forms")
    print("="*60)
    
    try:
        # Test that enhanced form exists and has new fields
        from flask import Flask
        from app.config import Config
        
        app = Flask(__name__)
        app.config.from_object(Config)
        
        with app.test_request_context():
            form = EnhancedYouTubeURLForm()
            
            # Check that new fields exist
            assert hasattr(form, 'max_comments'), "Missing max_comments field"
            assert hasattr(form, 'sort_order'), "Missing sort_order field"
            assert hasattr(form, 'include_replies'), "Missing include_replies field"
            assert hasattr(form, 'use_cache'), "Missing use_cache field"
            
            print("✓ Enhanced form has all required fields:")
            print(f"  - max_comments (default: {form.max_comments.default})")
            print(f"  - sort_order (default: {form.sort_order.default})")
            print(f"  - include_replies (default: {form.include_replies.default})")
            print(f"  - use_cache (default: {form.use_cache.default})")
            
    except Exception as e:
        print(f"✗ Error testing forms: {e}")
        assert False, f"Error testing forms: {e}"


def test_integration():
    """Test full integration of enhanced features."""
    print("\n" + "="*60)
    print("Testing Full Integration")
    print("="*60)
    
    try:
        # Initialize services
        youtube_service = EnhancedYouTubeService()
        sentiment_analyzer = SentimentAnalyzer(batch_size=32)
        
        print("✓ Services initialized")
        
        # Test with a small video
        test_video_id = "dQw4w9WgXcQ"
        
        # Fetch comments using enhanced service
        print(f"\nFetching comments for video: {test_video_id}")
        result = youtube_service.get_all_available_comments(
            video_id=test_video_id,
            target_comments=30,  # Small number for quick test
            include_replies=False,
            use_cache=False
        )
        
        comments = result['comments']
        print(f"✓ Fetched {len(comments)} comments")
        
        # Extract text for sentiment analysis
        comment_texts = [c['text'] for c in comments[:20]]  # Analyze first 20
        
        # Perform sentiment analysis
        print(f"\nAnalyzing sentiment for {len(comment_texts)} comments...")
        sentiment_results = sentiment_analyzer.analyze_batch(comment_texts)
        
        print(f"✓ Sentiment analysis completed")
        print(f"  Overall sentiment: {sentiment_results['overall_sentiment']}")
        print(f"  Sentiment score: {sentiment_results['sentiment_score']:.2f}")
        
        # Verify the integration worked
        assert len(comments) > 0, "No comments fetched"
        assert sentiment_results['total_analyzed'] > 0, "No comments analyzed"
        
        print("\n✓ Full integration test passed!")
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Integration test failed: {e}"


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  Enhanced YouTube Comment Analyzer Integration Test")
    print("="*60)
    
    tests = [
        ("Enhanced Service", test_enhanced_service),
        ("Batch Sentiment Analysis", test_batch_sentiment_analysis),
        ("Enhanced Forms", test_forms),
        ("Full Integration", test_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\nUnexpected error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 All tests passed! The enhanced features are properly integrated.")
        print("\nYou can now:")
        print("1. Run the app: python run.py")
        print("2. Visit http://localhost:5000")
        print("3. Analyze videos with up to 10,000 comments!")
        print("4. Get comprehensive fetching statistics")
        print("5. Use batch processing for efficient sentiment analysis")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
