"""
Fast Sentiment Analyzer using centralized Model Manager
Optimized for speed with model caching
"""
import logging
from typing import List, Dict, Optional, Callable
import numpy as np
from app.cache import cache
from app.utils.model_manager import get_model_manager

logger = logging.getLogger(__name__)


class FastSentimentAnalyzer:
    """Fast sentiment analyzer using cached pipeline from Model Manager."""

    def __init__(self):
        """Initialize the fast sentiment analyzer."""
        self.model_manager = get_model_manager()
        self.max_length = 512

        # Get pipeline on initialization (it will be cached)
        self.pipeline = self.model_manager.get_fast_sentiment_pipeline()
        logger.info("Fast sentiment analyzer initialized with cached model")

    def _preprocess_texts(self, texts: List[str]) -> List[str]:
        """
        Preprocess texts for better sentiment analysis.

        Args:
            texts: List of raw text strings

        Returns:
            List of preprocessed text strings
        """
        processed_texts = []

        for text in texts:
            # Remove excessive whitespace
            text = ' '.join(text.split())

            # Truncate very long texts to save processing time
            if len(text) > self.max_length:
                text = text[:self.max_length]

            # Skip empty texts
            if not text.strip():
                text = "neutral comment"

            processed_texts.append(text)

        return processed_texts

    def analyze_batch_fast(self, texts: List[str],
                          progress_callback: Optional[Callable] = None) -> Dict:
        """
        Quickly analyze sentiment of multiple texts using cached pipeline.

        Args:
            texts: List of texts to analyze
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with aggregated results and individual sentiments
        """
        if not texts:
            return {
                'overall_sentiment': 'neutral',
                'distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
                'sentiments': [],
                'processing_time': 0
            }

        # Preprocess texts
        processed_texts = self._preprocess_texts(texts)

        # Get results from pipeline (already batched internally)
        try:
            results = self.pipeline(processed_texts)

            # Process results
            sentiments = []
            distribution = {'positive': 0, 'neutral': 0, 'negative': 0}

            for i, result in enumerate(results):
                # Map pipeline labels to our standard labels
                label = result['label'].lower()
                if 'pos' in label:
                    label = 'positive'
                elif 'neg' in label:
                    label = 'negative'
                else:
                    label = 'neutral'

                sentiment = {
                    'text': texts[i][:100],  # First 100 chars for reference
                    'label': label,
                    'confidence': result['score']
                }

                sentiments.append(sentiment)
                distribution[label] += 1

                # Update progress if callback provided
                if progress_callback:
                    progress = (i + 1) / len(texts) * 100
                    progress_callback(progress)

            # Calculate overall sentiment
            total = len(sentiments)
            if distribution['positive'] >= total * 0.5:
                overall_sentiment = 'positive'
            elif distribution['negative'] >= total * 0.4:
                overall_sentiment = 'negative'
            else:
                overall_sentiment = 'neutral'

            return {
                'overall_sentiment': overall_sentiment,
                'distribution': distribution,
                'distribution_percentage': {
                    k: (v / total) * 100 for k, v in distribution.items()
                },
                'sentiments': sentiments,
                'total_analyzed': total,
                'model': 'distilbert-fast'
            }

        except Exception as e:
            logger.error(f"Fast sentiment analysis failed: {e}")
            raise

    def analyze_with_cache(self, texts: List[str], cache_key: str,
                          progress_callback: Optional[Callable] = None) -> Dict:
        """
        Analyze texts with caching support.

        Args:
            texts: List of text strings to analyze
            cache_key: Unique key for caching results
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with results (from cache or fresh analysis)
        """
        # Check cache first
        cached_result = cache.get('fast_sentiment', cache_key)
        if cached_result:
            logger.info(f"Using cached sentiment analysis for key: {cache_key}")
            return cached_result

        # Run fresh analysis
        result = self.analyze_batch_fast(texts, progress_callback)

        # Cache the result for 12 hours
        cache.set('fast_sentiment', cache_key, result, ttl_hours=12)

        return result

    def get_sentiment_score(self, text: str) -> float:
        """
        Get a sentiment score for a single text (-1 to 1).

        Args:
            text: Text to analyze

        Returns:
            Float score where -1 is most negative, 0 is neutral, 1 is most positive
        """
        result = self.pipeline([text])[0]

        label = result['label'].lower()
        score = result['score']

        if 'pos' in label:
            return score  # 0 to 1
        elif 'neg' in label:
            return -score  # -1 to 0
        else:
            return 0  # Neutral

    def filter_by_sentiment(self, texts: List[str],
                           sentiment_filter: str = 'all') -> List[str]:
        """
        Filter texts by sentiment.

        Args:
            texts: List of texts to filter
            sentiment_filter: 'positive', 'negative', 'neutral', or 'all'

        Returns:
            Filtered list of texts
        """
        if sentiment_filter == 'all':
            return texts

        filtered = []
        results = self.pipeline(texts)

        for text, result in zip(texts, results):
            label = result['label'].lower()

            if sentiment_filter == 'positive' and 'pos' in label:
                filtered.append(text)
            elif sentiment_filter == 'negative' and 'neg' in label:
                filtered.append(text)
            elif sentiment_filter == 'neutral' and 'neu' in label:
                filtered.append(text)

        return filtered


# Global instance for reuse across the application
_fast_analyzer = None

def get_fast_analyzer() -> FastSentimentAnalyzer:
    """Get or create the global fast sentiment analyzer instance."""
    global _fast_analyzer
    if _fast_analyzer is None:
        _fast_analyzer = FastSentimentAnalyzer()
    return _fast_analyzer