"""
Updated Sentiment Analyzer using centralized Model Manager
Optimized for Railway deployment with model caching
"""
import os
import math
import numpy as np
from typing import List, Dict, Tuple, Optional
import torch
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import logging
from app.cache import cache
from app.utils.model_manager import get_model_manager

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Ensemble sentiment analyzer using cached models from Model Manager."""

    def __init__(self, batch_size: int = 32):
        """Initialize the sentiment analyzer with cached models.

        Args:
            batch_size: Number of texts to process in each batch for efficiency
        """
        self.batch_size = batch_size
        self.model_manager = get_model_manager()

        # Model weights for ensemble (prefer RoBERTa as requested)
        self.roberta_weight = 0.7  # Higher weight for RoBERTa
        self.gb_weight = 0.3

        # Sentiment labels
        self.sentiment_labels = ['negative', 'neutral', 'positive']

        # Gradient Boosting components (if trained)
        self.gb_model = None
        self.gb_vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))

        # Load custom ML model if available
        self._load_gb_model()

    def _load_gb_model(self):
        """Load pre-trained Gradient Boosting model if available."""
        gb_model_path = os.path.join(os.path.dirname(__file__), 'models', 'gb_model.pkl')
        gb_vectorizer_path = os.path.join(os.path.dirname(__file__), 'models', 'gb_vectorizer.pkl')

        if os.path.exists(gb_model_path) and os.path.exists(gb_vectorizer_path):
            logger.info("Loading pre-trained Gradient Boosting model...")
            try:
                with open(gb_model_path, 'rb') as f:
                    self.gb_model = pickle.load(f)
                with open(gb_vectorizer_path, 'rb') as f:
                    self.gb_vectorizer = pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load GB model: {e}")

    @cache.memoize(timeout=3600)  # Cache results for 1 hour
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of a single text using cached models.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment label, scores, and confidence
        """
        # Get RoBERTa model from manager (already cached)
        tokenizer, model = self.model_manager.get_roberta_sentiment()

        # Tokenize and predict
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )

        # Move inputs to same device as model
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            scores = torch.nn.functional.softmax(outputs.logits, dim=-1)
            scores = scores.cpu().numpy()[0]

        # Get prediction
        predicted_label_idx = np.argmax(scores)
        predicted_label = self.sentiment_labels[predicted_label_idx]
        confidence = float(scores[predicted_label_idx])

        # Combine with GB model if available
        if self.gb_model is not None:
            try:
                # Get GB prediction
                features = self.gb_vectorizer.transform([text])
                gb_proba = self.gb_model.predict_proba(features)[0]

                # Weighted ensemble
                final_scores = (
                    scores * self.roberta_weight +
                    gb_proba * self.gb_weight
                )

                predicted_label_idx = np.argmax(final_scores)
                predicted_label = self.sentiment_labels[predicted_label_idx]
                confidence = float(final_scores[predicted_label_idx])

            except Exception as e:
                logger.warning(f"GB model prediction failed, using RoBERTa only: {e}")

        return {
            'label': predicted_label,
            'scores': {
                'negative': float(scores[0]),
                'neutral': float(scores[1]),
                'positive': float(scores[2])
            },
            'confidence': confidence,
            'model': 'ensemble' if self.gb_model else 'roberta'
        }

    def analyze_batch(self, texts: List[str], use_cache: bool = True) -> List[Dict]:
        """
        Analyze sentiment of multiple texts in batches.

        Args:
            texts: List of texts to analyze
            use_cache: Whether to use cached results

        Returns:
            List of sentiment analysis results
        """
        results = []

        # Process in batches for efficiency
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            # Analyze each text (will use cache if available)
            batch_results = []
            for text in batch:
                if use_cache:
                    result = self.analyze_sentiment(text)
                else:
                    # Bypass cache for fresh analysis
                    result = self._analyze_single_no_cache(text)
                batch_results.append(result)

            results.extend(batch_results)

        return results

    def _analyze_single_no_cache(self, text: str) -> Dict:
        """Analyze sentiment without using cache."""
        # Temporarily clear the cache for this function call
        # This is the same implementation as analyze_sentiment but without @cache decorator
        tokenizer, model = self.model_manager.get_roberta_sentiment()

        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )

        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            scores = torch.nn.functional.softmax(outputs.logits, dim=-1)
            scores = scores.cpu().numpy()[0]

        predicted_label_idx = np.argmax(scores)
        predicted_label = self.sentiment_labels[predicted_label_idx]
        confidence = float(scores[predicted_label_idx])

        return {
            'label': predicted_label,
            'scores': {
                'negative': float(scores[0]),
                'neutral': float(scores[1]),
                'positive': float(scores[2])
            },
            'confidence': confidence,
            'model': 'roberta'
        }

    def calculate_aggregate_sentiment(self, sentiments: List[Dict]) -> Dict:
        """
        Calculate aggregate sentiment statistics from multiple sentiment results.

        Args:
            sentiments: List of sentiment analysis results

        Returns:
            Dictionary with aggregate statistics
        """
        if not sentiments:
            return {
                'overall_sentiment': 'neutral',
                'distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
                'average_confidence': 0,
                'total_comments': 0
            }

        # Count sentiments
        distribution = {'positive': 0, 'neutral': 0, 'negative': 0}
        total_confidence = 0

        for sentiment in sentiments:
            label = sentiment.get('label', 'neutral')
            distribution[label] += 1
            total_confidence += sentiment.get('confidence', 0)

        # Calculate percentages
        total = len(sentiments)
        distribution_pct = {
            k: (v / total) * 100 for k, v in distribution.items()
        }

        # Determine overall sentiment
        if distribution_pct['positive'] >= 50:
            overall = 'positive'
        elif distribution_pct['negative'] >= 40:
            overall = 'negative'
        else:
            overall = 'neutral'

        return {
            'overall_sentiment': overall,
            'distribution': distribution,
            'distribution_percentage': distribution_pct,
            'average_confidence': total_confidence / total,
            'total_comments': total
        }


# Global analyzer instance for reuse
_analyzer = None

def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create the global sentiment analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer