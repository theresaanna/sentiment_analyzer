#!/usr/bin/env python3
"""
YouTube Comments Training Data Extractor

This script extracts comments from a specific YouTube video and formats them
into a CSV file for manual sentiment annotation. The resulting file contains
all necessary features for training a sentiment analysis model.
"""

import os
import sys
import csv
import argparse
import re
from datetime import datetime
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.services.youtube_service import YouTubeService


def clean_text(text: str) -> str:
    """
    Clean comment text by removing excessive whitespace and normalizing
    
    Args:
        text: Raw comment text
        
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def calculate_text_features(text: str) -> dict:
    """
    Calculate text-based features that might be useful for sentiment analysis
    
    Args:
        text: Comment text
        
    Returns:
        Dictionary of text features
    """
    # Basic text statistics
    char_count = len(text)
    word_count = len(text.split())
    sentence_count = len(re.findall(r'[.!?]+', text))
    
    # Character-based features
    exclamation_count = text.count('!')
    question_count = text.count('?')
    caps_count = sum(1 for c in text if c.isupper())
    caps_ratio = caps_count / char_count if char_count > 0 else 0
    
    # Emoji/emoticon patterns (basic)
    emoji_patterns = [
        r':\)',  # :)
        r':\(',  # :(
        r':D',   # :D
        r';D',   # ;D
        r':\/',  # :/
        r':\|',  # :|
        r'<3',   # <3
        r'>:\(',  # >:(
        r':\*',  # :*
    ]
    
    emoji_count = 0
    for pattern in emoji_patterns:
        emoji_count += len(re.findall(pattern, text))
    
    return {
        'char_count': char_count,
        'word_count': word_count,
        'sentence_count': max(sentence_count, 1),  # At least 1
        'exclamation_count': exclamation_count,
        'question_count': question_count,
        'caps_ratio': round(caps_ratio, 3),
        'emoji_count': emoji_count,
        'avg_word_length': round(char_count / word_count, 2) if word_count > 0 else 0
    }


def extract_training_data(video_id: str, max_comments: int = None, output_file: str = None) -> str:
    """
    Extract comments from a YouTube video and create a training dataset CSV
    
    Args:
        video_id: YouTube video ID
        max_comments: Maximum number of comments to fetch
        output_file: Output CSV filename
        
    Returns:
        Path to the created CSV file
    """
    # Initialize YouTube service
    youtube_service = YouTubeService()
    
    # Get video info first
    print(f"Fetching video information for: {video_id}")
    video_info = youtube_service.get_video_info(video_id)
    print(f"Video: {video_info['title']}")
    print(f"Channel: {video_info['channel']}")
    print(f"Total comments: {video_info['statistics']['comments']}")
    
    # Get all comments (flat list)
    print(f"Fetching comments... (max: {max_comments or 'all'})")
    comments = youtube_service.get_all_comments_flat(video_id, max_comments)
    print(f"Retrieved {len(comments)} comments")
    
    # Create output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r'[^\w\-_\. ]', '', video_info['title'])[:30]
        output_file = f"training_data_{video_id}_{safe_title}_{timestamp}.csv"
    
    # Ensure output directory exists
    output_path = Path("data") / output_file
    output_path.parent.mkdir(exist_ok=True)
    
    # Define CSV headers
    headers = [
        # Identifiers
        'comment_id',
        'thread_id',
        'video_id',
        
        # Comment content
        'comment_text',
        'cleaned_text',
        
        # Author information
        'author',
        'author_channel_id',
        
        # Engagement metrics
        'likes',
        'is_reply',
        
        # Temporal information
        'published_at',
        'published_date',
        'published_time',
        
        # Text features for ML
        'char_count',
        'word_count',
        'sentence_count',
        'exclamation_count',
        'question_count',
        'caps_ratio',
        'emoji_count',
        'avg_word_length',
        
        # Manual annotation columns (empty for you to fill)
        'sentiment_label',  # positive, negative, neutral
        'sentiment_score',  # -2 to +2 (very negative to very positive)
        'emotion_primary',  # joy, anger, fear, sadness, surprise, disgust, neutral
        'emotion_secondary', # secondary emotion if applicable
        'confidence',       # your confidence in the label (1-5)
        'notes',           # any additional notes
        
        # Context flags (for edge cases)
        'is_sarcastic',    # 1 if sarcastic, 0 if not
        'is_spam',         # 1 if spam, 0 if not
        'is_off_topic',    # 1 if off-topic, 0 if not
        'language_other',  # 1 if not English, 0 if English
    ]
    
    # Write CSV file
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for comment in comments:
            # Clean the comment text
            cleaned_text = clean_text(comment['text'])
            
            # Calculate text features
            text_features = calculate_text_features(cleaned_text)
            
            # Parse publication date
            pub_datetime = datetime.fromisoformat(comment['published_at'].replace('Z', '+00:00'))
            
            # Create row data
            row = {
                # Identifiers
                'comment_id': comment['id'],
                'thread_id': comment['thread_id'],
                'video_id': video_id,
                
                # Comment content
                'comment_text': comment['text'],
                'cleaned_text': cleaned_text,
                
                # Author information
                'author': comment['author'],
                'author_channel_id': comment['author_channel_id'],
                
                # Engagement metrics
                'likes': comment['likes'],
                'is_reply': 1 if comment['is_reply'] else 0,
                
                # Temporal information
                'published_at': comment['published_at'],
                'published_date': pub_datetime.strftime('%Y-%m-%d'),
                'published_time': pub_datetime.strftime('%H:%M:%S'),
                
                # Text features
                **text_features,
                
                # Manual annotation columns (empty)
                'sentiment_label': '',
                'sentiment_score': '',
                'emotion_primary': '',
                'emotion_secondary': '',
                'confidence': '',
                'notes': '',
                
                # Context flags (empty)
                'is_sarcastic': '',
                'is_spam': '',
                'is_off_topic': '',
                'language_other': '',
            }
            
            writer.writerow(row)
    
    print(f"\nTraining data CSV created: {output_path}")
    print(f"Total rows: {len(comments)}")
    print(f"\nColumns for manual annotation:")
    print("- sentiment_label: positive, negative, neutral")
    print("- sentiment_score: -2 (very negative) to +2 (very positive)")
    print("- emotion_primary: joy, anger, fear, sadness, surprise, disgust, neutral")
    print("- confidence: 1-5 (your confidence in the labeling)")
    print("- Additional context flags for edge cases")
    
    return str(output_path)


def main():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(
        description="Extract YouTube comments for manual sentiment annotation"
    )
    parser.add_argument(
        "video_id",
        help="YouTube video ID (e.g., habpdmFSTOo)"
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        help="Maximum number of comments to fetch (default: all)"
    )
    parser.add_argument(
        "--output",
        help="Output CSV filename (default: auto-generated)"
    )
    
    args = parser.parse_args()
    
    try:
        output_path = extract_training_data(
            video_id=args.video_id,
            max_comments=args.max_comments,
            output_file=args.output
        )
        
        print(f"\n✅ Success! Training data ready for annotation: {output_path}")
        print("\nNext steps:")
        print("1. Open the CSV file in your preferred spreadsheet application")
        print("2. Fill in the sentiment_label, sentiment_score, and other annotation columns")
        print("3. Save the file for use in model training")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
