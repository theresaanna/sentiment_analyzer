#!/usr/bin/env python3
"""
Test script to verify the sentiment analysis API is working.
"""

import pytest
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def is_server_running():
    """Check if the server is running."""
    try:
        response = requests.get(BASE_URL, timeout=1)
        return response.status_code < 500
    except (requests.ConnectionError, requests.Timeout):
        return False

@pytest.mark.integration
@pytest.mark.skipif(not is_server_running(), reason="Server not running at http://localhost:8000")
def test_sentiment_analysis():
    """Test the sentiment analysis API."""
    
    # Use a simple test video ID (you can replace with a real one)
    video_id = "zpx4FI8WMOc"  # Test video
    
    print(f"Testing sentiment analysis for video: {video_id}")
    print("-" * 60)
    
    # Step 1: Start sentiment analysis
    print("1. Starting sentiment analysis...")
    response = requests.post(
        f"{BASE_URL}/api/analyze/sentiment/{video_id}",
        json={"max_comments": 20}  # Use fewer comments for testing
    )
    
    if response.status_code != 200:
        print(f"   ERROR: Failed to start analysis. Status: {response.status_code}")
        print(f"   Response: {response.text}")
        assert False, "Failed to start analysis"
    
    data = response.json()
    if not data.get('success'):
        print(f"   ERROR: {data.get('error', 'Unknown error')}")
        assert False, f"Analysis failed: {data.get('error', 'Unknown error')}"
    
    analysis_id = data.get('analysis_id')
    print(f"   SUCCESS: Analysis started with ID: {analysis_id}")
    
    if data.get('cached'):
        print("   INFO: Using cached results")
    
    # Step 2: Check status (poll until complete)
    print("\n2. Checking analysis status...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(2)  # Wait 2 seconds between checks
        
        response = requests.get(f"{BASE_URL}/api/analyze/status/{analysis_id}")
        
        if response.status_code == 404:
            print(f"   ERROR: Analysis not found (ID: {analysis_id})")
            assert False, f"Analysis not found (ID: {analysis_id})"
        
        if response.status_code != 200:
            print(f"   ERROR: Failed to get status. Status: {response.status_code}")
            assert False, "Failed to get status"
        
        status_data = response.json()
        if not status_data.get('success'):
            print(f"   ERROR: {status_data.get('error', 'Unknown error')}")
            assert False, f"Status check failed: {status_data.get('error', 'Unknown error')}"
        
        status = status_data.get('status', {})
        current_status = status.get('status', 'unknown')
        progress = status.get('progress', 0)
        
        print(f"   Status: {current_status} ({progress}%)")
        
        if current_status == 'completed':
            print("   SUCCESS: Analysis completed!")
            break
        elif current_status == 'error':
            print(f"   ERROR: Analysis failed - {status.get('error', 'Unknown error')}")
            assert False, f"Analysis failed - {status.get('error', 'Unknown error')}"
        
        attempt += 1
    
    if attempt >= max_attempts:
        print("   ERROR: Analysis timed out")
        assert False, "Analysis timed out"
    
    # Step 3: Get results
    print("\n3. Fetching analysis results...")
    response = requests.get(f"{BASE_URL}/api/analyze/results/{analysis_id}")
    
    if response.status_code != 200:
        print(f"   ERROR: Failed to get results. Status: {response.status_code}")
        assert False, "Failed to get results"
    
    results_data = response.json()
    if not results_data.get('success'):
        print(f"   ERROR: {results_data.get('error', 'Unknown error')}")
        assert False, f"Failed to fetch results: {results_data.get('error', 'Unknown error')}"
    
    results = results_data.get('results', {})
    sentiment = results.get('sentiment', {})
    
    print("   SUCCESS: Got results!")
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS:")
    print("=" * 60)
    print(f"Total analyzed: {sentiment.get('total_analyzed', 0)} comments")
    print(f"Overall sentiment: {sentiment.get('overall_sentiment', 'Unknown')}")
    print(f"Sentiment score: {sentiment.get('sentiment_score', 0):.3f}")
    print(f"Average confidence: {sentiment.get('average_confidence', 0):.3f}")
    
    if 'average_confidence_metrics' in sentiment:
        print("\nConfidence Metrics:")
        for metric, value in sentiment['average_confidence_metrics'].items():
            print(f"  - {metric}: {value:.3f}")
    
    print("\nSentiment Distribution:")
    percentages = sentiment.get('sentiment_percentages', {})
    for sent_type in ['positive', 'neutral', 'negative']:
        count = sentiment.get('sentiment_counts', {}).get(sent_type, 0)
        percent = percentages.get(sent_type, 0)
        print(f"  - {sent_type.capitalize()}: {count} ({percent:.1f}%)")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    success = test_sentiment_analysis()
    exit(0 if success else 1)
