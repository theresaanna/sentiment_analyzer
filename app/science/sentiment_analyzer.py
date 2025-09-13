"""
Updated Sentiment Analyzer using centralized Model Manager
Optimized for Railway deployment with model caching
"""
import os
import numpy as np
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import logging
from app.cache import cache
from app.utils.model_manager import get_model_manager

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Ensemble sentiment analyzer using cached models from Model Manager."""

    def __init__(self, batch_size=32):
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

    def analyze_sentiment(self, text):
        """
        Analyze sentiment of a single text using cached models.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment label, scores, and confidence
        """
        # Try to get cached result
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cached_result = cache.get('sentiment', text_hash)
        if cached_result:
            return cached_result
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

        result = {
            'label': predicted_label,
            'scores': {
                'negative': float(scores[0]),
                'neutral': float(scores[1]),
                'positive': float(scores[2])
            },
            'confidence': confidence,
            'model': 'ensemble' if self.gb_model else 'roberta'
        }
        
        # Cache the result
        cache.set('sentiment', text_hash, result, ttl_hours=1)
        
        return result

    def analyze_batch(self, 
        texts, 
        use_cache=True,
        progress_callback=None
    ):
        """
        Analyze sentiment of multiple texts in batches.

        Args:
            texts: List of texts to analyze
            use_cache: Whether to use cached results
            progress_callback: Optional callback receiving (current, total)

        Returns:
            Dictionary with overall stats and individual results compatible with routes
        """
        if not texts:
            return {
                'overall_sentiment': 'neutral',
                'distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
                'distribution_percentage': {'positive': 0.0, 'neutral': 0.0, 'negative': 0.0},
                'sentiment_counts': {'positive': 0, 'neutral': 0, 'negative': 0},
                'sentiment_percentages': {'positive': 0.0, 'neutral': 0.0, 'negative': 0.0},
                'average_confidence': 0.0,
                'total_analyzed': 0,
                'individual_results': []
            }

        total = len(texts)
        processed = 0
        individual_results = []
        counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        total_confidence = 0.0

        # Process in batches for efficiency
        for i in range(0, total, self.batch_size):
            batch = texts[i:i + self.batch_size]

            # Analyze each text (will use cache if available)
            for text in batch:
                if use_cache:
                    result = self.analyze_sentiment(text)
                else:
                    # Bypass cache for fresh analysis
                    result = self._analyze_single_no_cache(text)

                label = result.get('label', 'neutral')
                confidence = float(result.get('confidence', 0.0))
                scores = result.get('scores', {}) or {}

                # Normalize scores to include all keys
                sentiment_scores = {
                    'negative': float(scores.get('negative', scores.get(0, 0.0))) if isinstance(scores, dict) else float(scores[0]) if isinstance(scores, (list, tuple, np.ndarray)) and len(scores) > 0 else 0.0,
                    'neutral': float(scores.get('neutral', scores.get(1, 0.0))) if isinstance(scores, dict) else float(scores[1]) if isinstance(scores, (list, tuple, np.ndarray)) and len(scores) > 1 else 0.0,
                    'positive': float(scores.get('positive', scores.get(2, 0.0))) if isinstance(scores, dict) else float(scores[2]) if isinstance(scores, (list, tuple, np.ndarray)) and len(scores) > 2 else 0.0,
                }

                individual_results.append({
                    'text': text[:100],
                    'predicted_sentiment': label,
                    'confidence': confidence,
                    'sentiment_scores': sentiment_scores,
                    'model': result.get('model', 'roberta')
                })

                counts[label] = counts.get(label, 0) + 1
                total_confidence += confidence

                processed += 1
                if progress_callback:
                    try:
                        progress_callback(processed, total)
                    except Exception:
                        # Do not fail analysis due to callback errors
                        pass

        # Calculate percentages and overall sentiment
        total_nonzero = max(processed, 1)
        percentages = {
            'positive': counts['positive'] / total_nonzero * 100.0,
            'neutral': counts['neutral'] / total_nonzero * 100.0,
            'negative': counts['negative'] / total_nonzero * 100.0,
        }

        # Determine overall sentiment (similar heuristic as calculate_aggregate_sentiment)
        if percentages['positive'] >= 50:
            overall = 'positive'
        elif percentages['negative'] >= 40:
            overall = 'negative'
        else:
            overall = 'neutral'

        average_confidence = total_confidence / total_nonzero if total_nonzero else 0.0

        # Also provide fields some routes expect
        sentiment_score = (percentages['positive'] - percentages['negative']) / 100.0

        return {
            'overall_sentiment': overall,
            'distribution': counts.copy(),
            'distribution_percentage': percentages.copy(),
            'sentiment_counts': counts.copy(),
            'sentiment_percentages': percentages.copy(),
            'average_confidence': average_confidence,
            'sentiment_score': sentiment_score,
            'total_analyzed': processed,
            'individual_results': individual_results,
            'model': 'ensemble' if self.gb_model else 'roberta'
        }

    def _analyze_single_no_cache(self, text):
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

    def calculate_aggregate_sentiment(self, sentiments):
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

    def get_sentiment_timeline(self, comments_or_texts, window=5, limit=50):
        """
        Build a sentiment timeline from a sequence of comments or texts.
        Accepts a list of strings or dicts with a 'text' field and returns a
        list of points like [{'score': {'positive': p, 'neutral': n, 'negative': g}}].
        Scores are normalized to sum to 1.
        """
        if not comments_or_texts:
            return []

        # Normalize inputs to a list of texts
        texts = []
        for item in comments_or_texts[:limit]:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                txt = item.get('text') or item.get('comment') or ''
                texts.append(txt)
            else:
                texts.append(str(item) or '')

        # Collect per-comment sentiment scores
        raw_scores = []
        for t in texts:
            try:
                res = self.analyze_sentiment(t)
                s = res.get('scores') or {}
                pos = float(s.get('positive', s.get(2, 0.0))) if isinstance(s, dict) else 0.0
                neu = float(s.get('neutral', s.get(1, 0.0))) if isinstance(s, dict) else 0.0
                neg = float(s.get('negative', s.get(0, 0.0))) if isinstance(s, dict) else 0.0
                raw_scores.append((pos, neu, neg))
            except Exception:
                raw_scores.append((0.33, 0.34, 0.33))

        # Rolling average over a window
        timeline = []
        w = max(int(window), 1)
        for i in range(len(raw_scores)):
            start = max(0, i - w + 1)
            window_slice = raw_scores[start:i+1]
            count = len(window_slice)
            pos = sum(s[0] for s in window_slice) / count
            neu = sum(s[1] for s in window_slice) / count
            neg = sum(s[2] for s in window_slice) / count
            total = pos + neu + neg
            if total > 0:
                pos /= total
                neu /= total
                neg /= total
            timeline.append({
                'score': {
                    'positive': pos,
                    'neutral': neu,
                    'negative': neg
                }
            })

        return timeline


# Global analyzer instance for reuse
_analyzer = None

def get_sentiment_analyzer():
    """Get or create the global sentiment analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer
