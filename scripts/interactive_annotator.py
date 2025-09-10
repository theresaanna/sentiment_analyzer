#!/usr/bin/env python3
"""
Interactive Sentiment Annotator

Command-line tool for annotating YouTube comments with sentiment labels.
Shows comments one by one and saves annotations directly to the CSV.
"""

import csv
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime


class InteractiveAnnotator:
    def __init__(self, csv_file: str):
        self.csv_file = Path(csv_file)
        self.comments = []
        self.current_index = 0
        self.changes_made = False
        
        # Load comments
        self.load_comments()
        
        # Find where to resume (first unannotated comment)
        self.find_resume_point()
    
    def load_comments(self):
        """Load comments from CSV file"""
        if not self.csv_file.exists():
            print(f"❌ File not found: {self.csv_file}")
            sys.exit(1)
        
        with open(self.csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            self.comments = list(reader)
        
        print(f"📊 Loaded {len(self.comments)} comments from {self.csv_file.name}")
    
    def find_resume_point(self):
        """Find the first comment that hasn't been annotated"""
        for i, comment in enumerate(self.comments):
            if not comment['sentiment_label'].strip():
                self.current_index = i
                if i > 0:
                    print(f"📍 Resuming from comment #{i+1} (found {i} already annotated)")
                return
        
        # All comments are annotated
        if len(self.comments) > 0:
            print(f"✅ All {len(self.comments)} comments are already annotated!")
            self.show_summary()
            sys.exit(0)
    
    def save_comments(self):
        """Save annotations back to CSV file"""
        if not self.changes_made:
            return
        
        # Create backup
        backup_file = self.csv_file.with_suffix('.backup.csv')
        if not backup_file.exists():
            import shutil
            shutil.copy2(self.csv_file, backup_file)
            print(f"💾 Backup created: {backup_file.name}")
        
        # Write updated data
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as file:
            if self.comments:
                writer = csv.DictWriter(file, fieldnames=self.comments[0].keys())
                writer.writeheader()
                writer.writerows(self.comments)
        
        print(f"💾 Saved annotations to {self.csv_file.name}")
    
    def show_comment(self, comment):
        """Display a comment for annotation"""
        print("\n" + "="*80)
        print(f"📝 Comment #{self.current_index + 1} of {len(self.comments)}")
        print("="*80)
        
        # Basic info
        print(f"👤 Author: {comment['author']}")
        print(f"👍 Likes: {comment['likes']}")
        print(f"📅 Date: {comment['published_date']} {comment['published_time']}")
        print(f"💬 Reply: {'Yes' if comment['is_reply'] == '1' else 'No'}")
        
        # Text features
        features = []
        if int(comment['word_count']) > 50:
            features.append(f"{comment['word_count']} words (long)")
        elif int(comment['word_count']) < 5:
            features.append(f"{comment['word_count']} words (short)")
        
        if int(comment['exclamation_count']) > 0:
            features.append(f"{comment['exclamation_count']}!")
        if int(comment['question_count']) > 0:
            features.append(f"{comment['question_count']}?")
        if float(comment['caps_ratio']) > 0.3:
            features.append(f"{float(comment['caps_ratio']):.0%} CAPS")
        if int(comment['emoji_count']) > 0:
            features.append(f"{comment['emoji_count']} emoji")
        
        if features:
            print(f"📊 Features: {', '.join(features)}")
        
        print("\n" + "-"*80)
        print(f"💭 COMMENT TEXT:")
        print(f'"{comment["comment_text"]}"')
        print("-"*80)
        
        # Show existing annotation if any
        if comment['sentiment_label'].strip():
            print(f"📌 Current annotation: {comment['sentiment_label']}")
            if comment['sentiment_score'].strip():
                print(f"📊 Score: {comment['sentiment_score']}")
            if comment['notes'].strip():
                print(f"📝 Notes: {comment['notes']}")
    
    def get_annotation(self):
        """Get annotation input from user"""
        print("\n🎯 Choose sentiment:")
        print("  [p] Positive")
        print("  [n] Negative") 
        print("  [z] Neutral")
        print("  [s] Skip this comment")
        print("  [b] Go back to previous")
        print("  [q] Quit and save")
        print("  [?] Show help")
        
        while True:
            try:
                choice = input("\nYour choice: ").lower().strip()
                
                if choice == 'p':
                    return self.get_detailed_annotation('positive')
                elif choice == 'n':
                    return self.get_detailed_annotation('negative')
                elif choice == 'z':
                    return self.get_detailed_annotation('neutral')
                elif choice == 's':
                    return 'skip'
                elif choice == 'b':
                    return 'back'
                elif choice == 'q':
                    return 'quit'
                elif choice == '?':
                    self.show_help()
                    continue
                else:
                    print("❌ Invalid choice. Please use p/n/z/s/b/q/?")
                    continue
                    
            except (KeyboardInterrupt, EOFError):
                print("\n\n👋 Goodbye!")
                return 'quit'
    
    def get_detailed_annotation(self, sentiment_label):
        """Get detailed annotation including score and notes"""
        # Get sentiment score
        if sentiment_label == 'positive':
            print("📊 How positive? [1] Somewhat positive  [2] Very positive")
            score_map = {'1': 1, '2': 2}
            default_score = 1
        elif sentiment_label == 'negative':
            print("📊 How negative? [1] Somewhat negative  [2] Very negative")
            score_map = {'1': -1, '2': -2}
            default_score = -1
        else:  # neutral
            score_map = {'0': 0}
            default_score = 0
        
        if sentiment_label != 'neutral':
            while True:
                score_input = input(f"Score (default={default_score}): ").strip()
                if not score_input:
                    sentiment_score = default_score
                    break
                elif score_input in score_map:
                    sentiment_score = score_map[score_input]
                    break
                else:
                    print(f"❌ Please enter {'/'.join(score_map.keys())}")
        else:
            sentiment_score = 0
        
        # Get confidence
        while True:
            conf_input = input("Confidence 1-5 (default=4): ").strip()
            if not conf_input:
                confidence = 4
                break
            try:
                confidence = int(conf_input)
                if 1 <= confidence <= 5:
                    break
                else:
                    print("❌ Confidence must be 1-5")
            except ValueError:
                print("❌ Please enter a number 1-5")
        
        # Get optional notes
        notes = input("Notes (optional): ").strip()
        
        return {
            'sentiment_label': sentiment_label,
            'sentiment_score': str(sentiment_score),
            'confidence': str(confidence),
            'notes': notes
        }
    
    def show_help(self):
        """Show help information"""
        print("\n" + "="*60)
        print("📚 ANNOTATION GUIDE")
        print("="*60)
        print("POSITIVE: Praise, agreement, joy, satisfaction, support")
        print("  • 'Love this!', 'She's amazing', 'Great point'")
        print("\nNEGATIVE: Criticism, anger, sadness, disagreement")
        print("  • 'This is stupid', 'I hate this', 'Wrong!'")
        print("\nNEUTRAL: Facts, questions, mixed sentiment, unclear")
        print("  • 'What song is this?', 'Posted in 2020', mixed opinions")
        print("\nCONFIDENCE:")
        print("  5 = Very confident    3 = Moderately confident")
        print("  4 = Confident         2 = Low confidence") 
        print("  1 = Very unsure")
        print("="*60)
    
    def show_progress(self):
        """Show annotation progress"""
        annotated = sum(1 for c in self.comments if c['sentiment_label'].strip())
        total = len(self.comments)
        percentage = (annotated / total * 100) if total > 0 else 0
        
        print(f"\n📊 Progress: {annotated}/{total} ({percentage:.1f}%) annotated")
    
    def show_summary(self):
        """Show annotation summary statistics"""
        annotated_comments = [c for c in self.comments if c['sentiment_label'].strip()]
        
        if not annotated_comments:
            print("📊 No annotations found.")
            return
        
        # Count by sentiment
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        confidence_sum = 0
        confidence_count = 0
        
        for comment in annotated_comments:
            label = comment['sentiment_label'].lower()
            if label in sentiment_counts:
                sentiment_counts[label] += 1
            
            if comment['confidence'].strip():
                try:
                    confidence_sum += int(comment['confidence'])
                    confidence_count += 1
                except ValueError:
                    pass
        
        print(f"\n📊 ANNOTATION SUMMARY")
        print(f"Total annotated: {len(annotated_comments)}")
        print(f"Positive: {sentiment_counts['positive']}")
        print(f"Negative: {sentiment_counts['negative']}")
        print(f"Neutral: {sentiment_counts['neutral']}")
        
        if confidence_count > 0:
            avg_confidence = confidence_sum / confidence_count
            print(f"Average confidence: {avg_confidence:.1f}/5")
    
    def run(self):
        """Main annotation loop"""
        print(f"\n🎯 Starting interactive annotation session")
        print(f"Use Ctrl+C anytime to quit and save")
        self.show_progress()
        
        try:
            while self.current_index < len(self.comments):
                comment = self.comments[self.current_index]
                self.show_comment(comment)
                
                annotation = self.get_annotation()
                
                if annotation == 'quit':
                    break
                elif annotation == 'skip':
                    self.current_index += 1
                    continue
                elif annotation == 'back':
                    if self.current_index > 0:
                        self.current_index -= 1
                    else:
                        print("❌ Already at first comment")
                    continue
                elif isinstance(annotation, dict):
                    # Apply annotation
                    for key, value in annotation.items():
                        comment[key] = value
                    
                    self.changes_made = True
                    print(f"✅ Annotated as {annotation['sentiment_label']}")
                    self.current_index += 1
                    
                    # Show progress every 10 annotations
                    if (self.current_index) % 10 == 0:
                        self.show_progress()
            
            # Finished all comments
            if self.current_index >= len(self.comments):
                print(f"\n🎉 Congratulations! You've finished annotating all comments!")
                
        except KeyboardInterrupt:
            print(f"\n\n⏸️  Annotation paused at comment #{self.current_index + 1}")
        
        finally:
            self.save_comments()
            self.show_summary()
            print(f"\n👋 Session ended. Resume anytime with the same command!")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive sentiment annotation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python interactive_annotator.py data/training_data.csv
  
Tips:
  - The tool automatically resumes from where you left off
  - A backup file is created on first save
  - Use Ctrl+C anytime to quit and save progress
        """
    )
    parser.add_argument(
        "csv_file",
        help="Path to the training data CSV file"
    )
    
    args = parser.parse_args()
    
    annotator = InteractiveAnnotator(args.csv_file)
    annotator.run()


if __name__ == "__main__":
    main()
