"""
Comprehensive tests for the sentiment API service integration.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from requests.exceptions import RequestException, Timeout, ConnectionError
from app.services.sentiment_api import SentimentAPIClient, get_sentiment_client


class TestSentimentAPIClient:
    """Test the SentimentAPIClient class."""
    
    def test_client_initialization(self):
        """Test client initialization with API URL."""
        client = SentimentAPIClient(api_url='https://test.api.com')
        assert client.api_url == 'https://test.api.com'
        assert client.timeout == 30  # Default timeout
    
    def test_client_initialization_with_timeout(self):
        """Test client initialization with custom timeout."""
        client = SentimentAPIClient(api_url='https://test.api.com', timeout=60)
        assert client.timeout == 60
    
    @patch('requests.post')
    def test_analyze_text_success(self, mock_post):
        """Test successful text analysis."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sentiment': 'positive',
            'confidence': 0.92,
            'label': 'POSITIVE',
            'score': 0.92
        }
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        result = client.analyze_text('This is amazing!')
        
        assert result['sentiment'] == 'positive'
        assert result['confidence'] == 0.92
        mock_post.assert_called_once()
        
        # Check the call arguments
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://test.api.com/analyze'
        assert call_args[1]['json'] == {'text': 'This is amazing!'}
        assert call_args[1]['timeout'] == 30
    
    @patch('requests.post')
    def test_analyze_batch_success(self, mock_post):
        """Test successful batch analysis."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'predicted_sentiment': 'positive', 'confidence': 0.9},
                {'predicted_sentiment': 'negative', 'confidence': 0.85},
                {'predicted_sentiment': 'neutral', 'confidence': 0.7}
            ],
            'total_analyzed': 3,
            'statistics': {
                'sentiment_distribution': {'positive': 1, 'negative': 1, 'neutral': 1}
            }
        }
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        texts = ['Great!', 'Terrible!', 'Okay']
        result = client.analyze_batch(texts)
        
        assert result['total_analyzed'] == 3
        assert len(result['results']) == 3
        assert result['results'][0]['predicted_sentiment'] == 'positive'
        
        # Check the call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://test.api.com/analyze/batch'
        assert call_args[1]['json'] == {'texts': texts}
    
    @patch('requests.post')
    def test_handle_timeout(self, mock_post):
        """Test handling of timeout errors."""
        mock_post.side_effect = Timeout('Request timed out')
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        result = client.analyze_text('Test text')
        
        # Should return fallback result
        assert result['sentiment'] == 'neutral'
        assert result['confidence'] == 0.5
        assert 'error' in result
        assert 'timeout' in result['error'].lower()
    
    @patch('requests.post')
    def test_handle_connection_error(self, mock_post):
        """Test handling of connection errors."""
        mock_post.side_effect = ConnectionError('Connection refused')
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        result = client.analyze_text('Test text')
        
        # Should return fallback result
        assert result['sentiment'] == 'neutral'
        assert result['confidence'] == 0.5
        assert 'error' in result
        assert 'connection' in result['error'].lower()
    
    @patch('requests.post')
    def test_handle_api_error_response(self, mock_post):
        """Test handling of API error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        result = client.analyze_text('Test text')
        
        # Should return fallback result
        assert result['sentiment'] == 'neutral'
        assert result['confidence'] == 0.5
        assert 'error' in result
        assert '500' in str(result['error'])
    
    @patch('requests.post')
    def test_handle_invalid_json_response(self, mock_post):
        """Test handling of invalid JSON responses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        result = client.analyze_text('Test text')
        
        # Should return fallback result
        assert result['sentiment'] == 'neutral'
        assert result['confidence'] == 0.5
        assert 'error' in result
    
    @patch('requests.post')
    def test_batch_analysis_with_empty_list(self, mock_post):
        """Test batch analysis with empty text list."""
        client = SentimentAPIClient(api_url='https://test.api.com')
        result = client.analyze_batch([])
        
        # Should return empty results
        assert result['total_analyzed'] == 0
        assert result['results'] == []
        
        # Should not make API call
        mock_post.assert_not_called()
    
    @patch('requests.post')
    def test_batch_analysis_partial_failure(self, mock_post):
        """Test batch analysis with partial failures."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'predicted_sentiment': 'positive', 'confidence': 0.9},
                {'error': 'Processing failed for this text'},
                {'predicted_sentiment': 'neutral', 'confidence': 0.6}
            ],
            'total_analyzed': 2,
            'total_errors': 1
        }
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        result = client.analyze_batch(['Text 1', 'Text 2', 'Text 3'])
        
        assert result['total_analyzed'] == 2
        assert 'total_errors' in result
        assert result['total_errors'] == 1
    
    def test_normalize_sentiment_labels(self):
        """Test normalization of different sentiment label formats."""
        client = SentimentAPIClient(api_url='https://test.api.com')
        
        # Test various label formats
        test_cases = [
            ('POSITIVE', 'positive'),
            ('NEGATIVE', 'negative'),
            ('NEUTRAL', 'neutral'),
            ('Positive', 'positive'),
            ('neg', 'negative'),
            ('neu', 'neutral'),
            ('pos', 'positive'),
            ('unknown', 'neutral')  # Fallback to neutral
        ]
        
        for input_label, expected in test_cases:
            result = client._normalize_sentiment(input_label)
            assert result == expected, f"Failed for {input_label}"
    
    @patch('requests.post')
    def test_retry_on_rate_limit(self, mock_post):
        """Test retry logic for rate limit errors."""
        # First call returns 429 (rate limit)
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '1'}
        
        # Second call succeeds
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            'sentiment': 'positive',
            'confidence': 0.8
        }
        
        mock_post.side_effect = [mock_response_429, mock_response_200]
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client.analyze_text('Test text')
        
        assert result['sentiment'] == 'positive'
        assert mock_post.call_count == 2


class TestGetSentimentClient:
    """Test the get_sentiment_client factory function."""
    
    @patch('os.environ.get')
    def test_get_client_with_env_url(self, mock_env_get):
        """Test getting client with environment variable URL."""
        mock_env_get.return_value = 'https://env.api.com'
        
        client = get_sentiment_client()
        
        assert isinstance(client, SentimentAPIClient)
        assert client.api_url == 'https://env.api.com'
        mock_env_get.assert_called_with('SENTIMENT_API_URL', 
                                        'https://theresaanna--sentiment-ml-service-fastapi-app.modal.run')
    
    def test_get_client_with_default_url(self):
        """Test getting client with default URL."""
        with patch('os.environ.get', return_value=None):
            client = get_sentiment_client()
            
            assert isinstance(client, SentimentAPIClient)
            assert 'modal.run' in client.api_url
    
    @patch('os.environ.get')
    def test_get_client_singleton(self, mock_env_get):
        """Test that get_sentiment_client returns singleton instance."""
        mock_env_get.return_value = 'https://test.api.com'
        
        client1 = get_sentiment_client()
        client2 = get_sentiment_client()
        
        # Should be the same instance
        assert client1 is client2


class TestSentimentAPIEdgeCases:
    """Test edge cases and error scenarios."""
    
    @patch('requests.post')
    def test_very_long_text(self, mock_post):
        """Test handling of very long text."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sentiment': 'positive',
            'confidence': 0.75
        }
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        
        # Create a very long text (10000 characters)
        long_text = 'This is a test. ' * 625
        result = client.analyze_text(long_text)
        
        assert result['sentiment'] == 'positive'
        
        # Verify the text was sent
        call_args = mock_post.call_args
        assert len(call_args[1]['json']['text']) > 9000
    
    @patch('requests.post')
    def test_special_characters_in_text(self, mock_post):
        """Test handling of special characters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sentiment': 'neutral',
            'confidence': 0.6
        }
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        
        # Text with various special characters
        special_text = 'Test with émojis 😀 and symbols @#$% & quotes "test" and \'test\''
        result = client.analyze_text(special_text)
        
        assert result['sentiment'] == 'neutral'
        
        # Verify the text was properly sent
        call_args = mock_post.call_args
        assert call_args[1]['json']['text'] == special_text
    
    @patch('requests.post')
    def test_batch_with_mixed_languages(self, mock_post):
        """Test batch analysis with mixed language texts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'predicted_sentiment': 'positive', 'confidence': 0.8},
                {'predicted_sentiment': 'negative', 'confidence': 0.7},
                {'predicted_sentiment': 'neutral', 'confidence': 0.6}
            ],
            'total_analyzed': 3
        }
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        
        texts = [
            'This is great!',  # English
            'C\'est terrible!',  # French
            '这很好'  # Chinese
        ]
        result = client.analyze_batch(texts)
        
        assert result['total_analyzed'] == 3
        assert len(result['results']) == 3
    
    @patch('requests.post')
    def test_batch_with_none_values(self, mock_post):
        """Test batch analysis with None values in list."""
        client = SentimentAPIClient(api_url='https://test.api.com')
        
        # Should filter out None values
        texts = ['Text 1', None, 'Text 2', None, 'Text 3']
        filtered_texts = [t for t in texts if t is not None]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'predicted_sentiment': 'positive', 'confidence': 0.8},
                {'predicted_sentiment': 'negative', 'confidence': 0.7},
                {'predicted_sentiment': 'neutral', 'confidence': 0.6}
            ],
            'total_analyzed': 3
        }
        mock_post.return_value = mock_response
        
        result = client.analyze_batch(texts)
        
        # Should only analyze non-None texts
        call_args = mock_post.call_args
        assert call_args[1]['json']['texts'] == filtered_texts
    
    @patch('requests.post')
    def test_concurrent_requests(self, mock_post):
        """Test handling of concurrent requests."""
        import threading
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sentiment': 'positive',
            'confidence': 0.8
        }
        mock_post.return_value = mock_response
        
        client = SentimentAPIClient(api_url='https://test.api.com')
        results = []
        
        def make_request():
            result = client.analyze_text('Test text')
            results.append(result)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(r['sentiment'] == 'positive' for r in results)
        assert mock_post.call_count == 5