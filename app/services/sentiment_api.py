"""
Simple API client for external sentiment analysis service.
This is a lightweight client that only makes HTTP requests.
"""
import os
import requests
from typing import Dict, List, Any, Optional


class SentimentAPIClient:
    """Simple client for calling external sentiment analysis API."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize the sentiment API client.

        Args:
            base_url: The base URL of the sentiment service
            timeout: Request timeout in seconds
        """
        # Prefer SENTIMENT_API_URL, fall back to MODAL_ML_BASE_URL for compatibility
        env_base = os.getenv('SENTIMENT_API_URL') or os.getenv('MODAL_ML_BASE_URL') or ''
        self.base_url = (base_url or env_base).strip()
        self.timeout = timeout

        # Optional API key support
        self.api_key = os.getenv('MODAL_ML_API_KEY') or os.getenv('SENTIMENT_API_KEY')
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        if self.api_key:
            # Support either Bearer or X-API-Key styles
            self.headers['Authorization'] = f'Bearer {self.api_key}'
            self.headers['X-API-Key'] = self.api_key

        if not self.base_url:
            # If no URL configured, use a mock response
            self.mock_mode = True
        else:
            self.mock_mode = False
            self.base_url = self.base_url.rstrip('/')

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single text.

        Args:
            text: The text to analyze

        Returns:
            Dictionary with sentiment analysis results
        """
        if self.mock_mode:
            return self._mock_analyze_text(text)

        try:
            response = requests.post(
                f"{self.base_url}/analyze-text",
                json={"text": text},
                timeout=self.timeout,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

            # Extract result from response (support multiple shapes)
            result = data.get('result') or data
            return {
                'sentiment': result.get('predicted_sentiment', result.get('sentiment', 'neutral')),
                'confidence': result.get('confidence', 0.5),
                'models_used': result.get('models_used') or data.get('models_used'),
                'success': True,
            }
        except Exception as e:
            # Return fallback response on error
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'success': False,
                'error': str(e),
            }

    def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment of multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            Dictionary with batch analysis results
        """
        if self.mock_mode:
            return self._mock_analyze_batch(texts)

        try:
            response = requests.post(
                f"{self.base_url}/analyze-batch",
                json={"texts": texts},
                timeout=self.timeout,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

            # Normalize results
            raw_results = data.get('results') or []
            results = []
            for item in raw_results:
                results.append({
                    'text': item.get('text', ''),
                    # Preserve both keys for downstream compatibility
                    'predicted_sentiment': item.get('predicted_sentiment') or item.get('sentiment', 'neutral'),
                    'sentiment': item.get('predicted_sentiment') or item.get('sentiment', 'neutral'),
                    'confidence': item.get('confidence', 0.5),
                    # Pass through any additional scores if provided
                    'sentiment_scores': item.get('sentiment_scores', {}),
                    'comment_id': item.get('comment_id'),
                })

            total = len(results)
            stats = data.get('statistics') or {}
            dist = stats.get('sentiment_distribution') or {}
            if not dist and results:
                # Compute distribution if service didn't return one
                dist = {'positive': 0, 'neutral': 0, 'negative': 0}
                for r in results:
                    s = r.get('predicted_sentiment') or r.get('sentiment') or 'neutral'
                    if s not in dist:
                        s = 'neutral'
                    dist[s] += 1
            avg_conf = stats.get('average_confidence')
            if avg_conf is None:
                avg_conf = sum(r.get('confidence', 0.0) for r in results) / total if total else 0.0
            pct = stats.get('sentiment_percentages') or {
                k: (v / total * 100.0 if total else 0.0) for k, v in dist.items()
            }

            return {
                'results': results,
                'total_analyzed': total,
                'statistics': {
                    'sentiment_distribution': dist,
                    'sentiment_percentages': pct,
                    'average_confidence': avg_conf,
                },
                'success': True,
            }
        except Exception as e:
            # Return fallback response on error
            return {
                'results': [],
                'total_analyzed': 0,
                'statistics': {
                    'sentiment_distribution': {},
                    'sentiment_percentages': {},
                    'average_confidence': 0.0,
                },
                'success': False,
                'error': str(e),
            }

    def _mock_analyze_text(self, text: str) -> Dict[str, Any]:
        """Mock response for single text analysis."""
        # Simple mock logic based on keywords
        text_lower = text.lower()
        if any(word in text_lower for word in ['good', 'great', 'excellent', 'love', 'amazing']):
            sentiment = 'positive'
            confidence = 0.85
        elif any(word in text_lower for word in ['bad', 'terrible', 'hate', 'awful', 'worst']):
            sentiment = 'negative'
            confidence = 0.85
        else:
            sentiment = 'neutral'
            confidence = 0.70

        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'success': True,
            'mock': True,
        }

    def _mock_analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """Mock response for batch analysis."""
        results = []
        distribution = {'positive': 0, 'neutral': 0, 'negative': 0}

        for text in texts:
            result = self._mock_analyze_text(text)
            results.append({
                'text': text[:100],  # Truncate for display
                'predicted_sentiment': result['sentiment'],
                'sentiment': result['sentiment'],
                'confidence': result['confidence'],
            })
            distribution[result['sentiment']] += 1
        total = len(results)
        pct = {k: (v / total * 100.0 if total else 0.0) for k, v in distribution.items()}
        avg_conf = sum(r.get('confidence', 0.0) for r in results) / total if total else 0.0

        return {
            'results': results,
            'total_analyzed': total,
            'statistics': {
                'sentiment_distribution': distribution,
                'sentiment_percentages': pct,
                'average_confidence': avg_conf,
            },
            'success': True,
            'mock': True,
        }

    def summarize(self, comments: List[Dict[str, Any]], sentiment: Optional[Dict[str, Any]] = None, method: str = "auto") -> Dict[str, Any]:
        """Request comment summary from the external ML service."""
        if self.mock_mode:
            # Simple local fallback summary
            dist = sentiment.get('sentiment_distribution', {}) if sentiment else {}
            pos = dist.get('positive', 0)
            neu = dist.get('neutral', 0)
            neg = dist.get('negative', 0)
            total = sentiment.get('total_analyzed', 0) if sentiment else 0
            def pct(x):
                return round((x / total * 100), 1) if total else 0.0
            return {
                'summary': {
                    'summary': f"Viewer reactions are mixed. Distribution — positive: {pct(pos)}%, neutral: {pct(neu)}%, negative: {pct(neg)}%.",
                    'method': 'mock',
                    'comments_analyzed': total,
                }
            }
        try:
            response = requests.post(
                f"{self.base_url}/summarize",
                json={
                    'comments': comments,
                    'sentiment': sentiment,
                    'method': method,
                },
                timeout=self.timeout,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            return {
                'summary': {
                    'summary': 'Unable to generate summary at this time.',
                    'method': 'error',
                    'error': str(e),
                }
            }


# Singleton instance
_client = None

def get_sentiment_client() -> SentimentAPIClient:
    """Get or create the sentiment API client."""
    global _client
    if _client is None:
        _client = SentimentAPIClient()
    return _client
