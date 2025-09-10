#!/usr/bin/env python3
"""
Comment Preview Tool

Quick tool to preview comments from the training data CSV in a readable format
"""

import csv
import argparse
import random
from pathlib import Path


def preview_comments(csv_file: str, num_samples: int = 10, random_sample: bool = True):
    """
    Preview comments from the training data CSV
    
    Args:
        csv_file: Path to the CSV file
        num_samples: Number of comments to show
        random_sample: Whether to randomly sample or show first N
    """
    
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"❌ File not found: {csv_file}")
        return
    
    comments = []
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        comments = list(reader)
    
    print(f"📊 Total comments in dataset: {len(comments)}")
    print(f"📋 Preview of {num_samples} comments:\n")
    
    # Select comments to show
    if random_sample and len(comments) > num_samples:
        selected_comments = random.sample(comments, num_samples)
    else:
        selected_comments = comments[:num_samples]
    
    # Display comments
    for i, comment in enumerate(selected_comments, 1):
        print(f"--- Comment {i} ---")
        print(f"Author: {comment['author']}")
        print(f"Likes: {comment['likes']}")
        print(f"Is Reply: {'Yes' if comment['is_reply'] == '1' else 'No'}")
        print(f"Published: {comment['published_date']} {comment['published_time']}")
        print(f"Text: {comment['comment_text']}")
        
        # Show text features
        print(f"Features: {comment['word_count']} words, {comment['char_count']} chars")
        if int(comment['exclamation_count']) > 0:
            print(f"  • {comment['exclamation_count']} exclamation marks")
        if int(comment['question_count']) > 0:
            print(f"  • {comment['question_count']} question marks")
        if float(comment['caps_ratio']) > 0.1:
            print(f"  • {float(comment['caps_ratio']):.1%} caps")
        
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Preview comments from training data CSV"
    )
    parser.add_argument(
        "csv_file",
        help="Path to the training data CSV file"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=10,
        help="Number of comments to preview (default: 10)"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Show first N comments instead of random sample"
    )
    
    args = parser.parse_args()
    
    preview_comments(
        csv_file=args.csv_file,
        num_samples=args.num_samples,
        random_sample=not args.sequential
    )


if __name__ == "__main__":
    main()
