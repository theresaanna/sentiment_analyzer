#!/usr/bin/env python3
"""
Quick Training Script for ML Sentiment Model

Train a sentiment analysis model from annotated CSV data.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.ml.model_trainer import train_from_csv


def main():
    """Main training function"""
    
    # Find training data
    data_dir = project_root / "data"
    training_files = []
    
    # Look for annotated training data
    for csv_file in data_dir.glob("training_data_*.csv"):
        if "backup" not in str(csv_file):
            training_files.append(str(csv_file))
            print(f"Found training file: {csv_file.name}")
    
    if not training_files:
        print("❌ No training data found in data/ directory")
        print("Please annotate some data first using:")
        print("  python scripts/interactive_annotator.py data/training_data_*.csv")
        return 1
    
    print(f"\n📊 Found {len(training_files)} training file(s)")
    
    # Train model
    print("\n🚀 Starting model training...")
    
    try:
        model_path = train_from_csv(
            csv_files=training_files,
            algorithm='logistic_regression',  # Good for small datasets
            output_dir='models',
            tune_hyperparameters=False  # Not enough data yet
        )
        
        print(f"\n✅ Model training complete!")
        print(f"Model saved to: {model_path}")
        
        # Test the model
        print("\n🧪 Testing the model...")
        test_model(model_path)
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return 1
    
    return 0


def test_model(model_path: str):
    """Test the trained model with sample texts"""
    from app.ml.ml_sentiment_analyzer import MLSentimentAnalyzer
    
    # Load the model
    analyzer = MLSentimentAnalyzer(model_path=model_path)
    
    # Test sentences
    test_texts = [
        "Lady Gaga is absolutely amazing! I love her so much!",
        "This is terrible and I hate it",
        "The video was posted in 2020",
        "What a waste of time, absolutely horrible",
        "Great interview, she makes excellent points",
        "I don't understand what she's saying",
        "BEST ARTIST EVER!!!",
        "meh, not impressed"
    ]
    
    print("\n📝 Sample predictions:")
    print("-" * 60)
    
    for text in test_texts:
        result = analyzer.analyze_sentiment(text)
        sentiment = result['sentiment']
        confidence = result.get('confidence', 0)
        
        # Emoji for sentiment
        emoji = {'positive': '😊', 'negative': '😞', 'neutral': '😐'}.get(sentiment, '❓')
        
        print(f"{emoji} {sentiment:8s} (conf: {confidence:.2f}) | {text[:50]}")
    
    print("-" * 60)
    
    # Show model stats
    stats = analyzer.get_performance_stats()
    print(f"\n📊 Model Statistics:")
    print(f"  Model accuracy: {stats['model_accuracy']:.3f}")
    print(f"  Has ML model: {stats['has_ml_model']}")
    print(f"  Has fallback: {stats['has_fallback']}")


if __name__ == "__main__":
    sys.exit(main())
