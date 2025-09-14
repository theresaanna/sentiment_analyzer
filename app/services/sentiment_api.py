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
        self.base_url = base_url or os.getenv('SENTIMENT_API_URL', '')
        self.timeout = timeout
        
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
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract result from response
            result = data.get('result', {})
            return {
                'sentiment': result.get('predicted_sentiment', 'neutral'),
                'confidence': result.get('confidence', 0.5),
                'success': True
            }
        except Exception as e:
            # Return fallback response on error
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'success': False,
                'error': str(e)
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
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Process results
            results = []
            for item in data.get('results', []):
                results.append({
                    'text': item.get('text', ''),
                    'sentiment': item.get('predicted_sentiment', 'neutral'),
                    'confidence': item.get('confidence', 0.5)
                })
            
            # Calculate statistics
            stats = data.get('statistics', {})
            distribution = stats.get('sentiment_distribution', {})
            
            return {
                'results': results,
                'total_analyzed': len(results),
                'sentiment_distribution': distribution,
                'success': True
            }
        except Exception as e:
            # Return fallback response on error
            return {
                'results': [],
                'total_analyzed': 0,
                'sentiment_distribution': {},
                'success': False,
                'error': str(e)
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
            'mock': True
        }
    
    def _mock_analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """Mock response for batch analysis."""
        results = []
        distribution = {'positive': 0, 'neutral': 0, 'negative': 0}
        
        for text in texts:
            result = self._mock_analyze_text(text)
            results.append({
                'text': text[:100],  # Truncate for display
                'sentiment': result['sentiment'],
                'confidence': result['confidence']
            })
            distribution[result['sentiment']] += 1
        
        return {
            'results': results,
            'total_analyzed': len(results),
            'sentiment_distribution': distribution,
            'success': True,
            'mock': True
        }


# Singleton instance
_client = None

def get_sentiment_client() -> SentimentAPIClient:
    """Get or create the sentiment API client."""
    global _client
    if _client is None:
        _client = SentimentAPIClient()
    return _client