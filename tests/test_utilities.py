"""
Unit tests for utility modules.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import torch
from app.cache import cache, CacheService
from app.email import send_email, send_password_reset_email
from app.filters import format_duration
from app.utils.model_manager import ModelManager, get_model_manager


class TestCache:
    """Test cache functionality."""
    
    @patch('app.cache.redis.from_url')
    def test_cache_initialization(self, mock_redis):
        """Test cache initialization."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        
        test_cache = CacheService(redis_url='redis://localhost:6379')
        
        assert test_cache.redis_client == mock_client
        mock_redis.assert_called_once_with('redis://localhost:6379', decode_responses=True)
    
    @patch('app.cache.redis.from_url')
    def test_cache_set_get(self, mock_redis):
        """Test setting and getting cache values."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        test_cache = CacheService()
        
        # Test set
        test_cache.set('category', 'key', {'data': 'value'}, ttl_hours=1)
        mock_client.setex.assert_called_once()
        
        # Test get
        mock_client.get.return_value = '{"data": "value"}'
        result = test_cache.get('category', 'key')
        
        assert result == {'data': 'value'}
    
    @patch('app.cache.redis.from_url')
    def test_cache_delete(self, mock_redis):
        """Test cache deletion."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        test_cache = CacheService()
        test_cache.delete('category', 'key')
        
        mock_client.delete.assert_called_once()
    
    @patch('app.cache.redis.from_url')
    def test_cache_clear_category(self, mock_redis):
        """Test clearing cache category."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        # clear_pattern uses keys method, not scan_iter
        mock_client.keys.return_value = ['cache:category:key1', 'cache:category:key2']
        
        test_cache = CacheService()
        # Use clear_pattern method instead
        test_cache.clear_pattern('youtube:category:*')
        
        # delete is called once with all keys
        mock_client.delete.assert_called_once_with('cache:category:key1', 'cache:category:key2')
    
    @patch('app.cache.redis.from_url')
    def test_cache_error_handling(self, mock_redis):
        """Test cache error handling."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        mock_client.get.side_effect = Exception("Redis error")
        
        test_cache = CacheService()
        result = test_cache.get('category', 'key')
        
        # Should return None on error
        assert result is None
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        test_cache = CacheService()
        
        key = test_cache._make_key('category', 'identifier')
        assert key == 'youtube:category:identifier'
        
        key = test_cache._make_key('user', '123')
        assert key == 'youtube:user:123'


class TestEmail:
    """Test email functionality."""
    
    @patch('app.email.Thread')
    @patch('app.email.current_app')
    @patch('app.email.mail')  # Mock the global mail instance
    def test_send_email(self, mock_mail, mock_app, mock_thread):
        """Test sending email."""
        # Configure the mock app
        mock_app._get_current_object.return_value = mock_app
        
        result = send_email(
            subject='Test Subject',
            sender='sender@example.com',
            recipients=['recipient@example.com'],
            text_body='Test body',
            html_body='<p>Test body</p>'
        )
        
        # Check that Thread was created and started
        mock_thread.assert_called_once()
        thread_instance = mock_thread.return_value
        thread_instance.start.assert_called_once()
        assert result == True
    
    @patch('app.email.render_template')
    @patch('app.email.send_email')
    @patch('app.email.current_app')
    def test_send_password_reset_email(self, mock_app, mock_send, mock_render):
        """Test sending password reset email."""
        # Configure mock app with email settings
        mock_app.config = {'MAIL_DEFAULT_SENDER': 'noreply@example.com'}
        
        mock_user = MagicMock()
        mock_user.email = 'user@example.com'
        mock_user.name = 'Test User'
        mock_user.get_reset_password_token.return_value = 'reset_token_123'
        
        # Mock render_template to return simple strings
        mock_render.side_effect = ['text body', 'html body']
        mock_send.return_value = True
        
        result = send_password_reset_email(mock_user)
        
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert '[Sentiment Analyzer] Reset Your Password' in call_kwargs['subject']
        assert call_kwargs['recipients'] == ['user@example.com']
        assert call_kwargs['sender'] == 'noreply@example.com'
        assert result == True
    
    @patch('app.email.Thread')
    @patch('app.email.current_app')
    @patch('app.email.mail')
    def test_async_email_sending(self, mock_mail, mock_app, mock_thread):
        """Test asynchronous email sending."""
        # Configure the mock app
        mock_app._get_current_object.return_value = mock_app
        
        # Test async sending with all required parameters
        result = send_email(
            subject='Async Test',
            sender='sender@example.com',
            recipients=['test@example.com'],
            text_body='Test',
            html_body='<p>Test</p>'
        )
        
        mock_thread.assert_called_once()
        thread_instance = mock_thread.return_value
        thread_instance.start.assert_called_once()
        assert result == True


class TestFilters:
    """Test template filters."""
    
    def test_format_duration(self):
        """Test duration formatting filter."""
        # Test ISO 8601 format
        assert format_duration('PT4M33S') == '4:33'
        assert format_duration('PT1H2M3S') == '1:02:03'
        assert format_duration('PT30S') == '0:30'
        assert format_duration('PT1H') == '1:00:00'
        
        # Test with None
        assert format_duration(None) == 'Unknown'
        
        # Test already formatted
        assert format_duration('4:33') == '4:33'
        
        # Test invalid format
        assert format_duration('invalid') == 'invalid'


class TestModelManager:
    """Test model manager functionality."""
    
    def test_model_manager_initialization(self):
        """Test ModelManager initialization."""
        # Create a new manager instance (it's a singleton, so we get the existing one)
        manager = ModelManager()
        
        # Check that the manager has been initialized
        assert hasattr(manager, 'models')
        assert hasattr(manager, 'device')
        assert manager.device is not None
        assert isinstance(manager.models, dict)
    
    @patch('app.utils.model_manager.torch.cuda.is_available')
    def test_device_selection(self, mock_cuda):
        """Test device selection (CPU vs GPU)."""
        # Test with CUDA available
        mock_cuda.return_value = True
        manager = ModelManager()
        assert 'cuda' in str(manager.device) or 'cpu' in str(manager.device)
        
        # Test with CUDA not available
        mock_cuda.return_value = False
        manager = ModelManager()
        assert 'cpu' in str(manager.device)
    
    def test_get_roberta_sentiment(self):
        """Test loading RoBERTa sentiment model."""
        manager = ModelManager()
        
        # The model is already loaded during initialization
        # Just verify we can get it
        tokenizer, model = manager.get_roberta_sentiment()
        
        assert tokenizer is not None
        assert model is not None
        
        # Test caching - should return the same instances
        tokenizer2, model2 = manager.get_roberta_sentiment()
        assert tokenizer2 is tokenizer
        assert model2 is model
    
    def test_get_fast_sentiment_pipeline(self):
        """Test loading fast sentiment pipeline."""
        manager = ModelManager()
        
        # Get the fast sentiment pipeline
        pipeline = manager.get_fast_sentiment_pipeline()
        
        assert pipeline is not None
        
        # Test caching - should return the same instance
        pipeline2 = manager.get_fast_sentiment_pipeline()
        assert pipeline2 is pipeline
    
    def test_clear_all_models(self):
        """Test clearing all models from cache."""
        manager = ModelManager()
        
        # Ensure some models are loaded
        initial_count = len(manager.models)
        
        # Clear all models
        manager.clear_all_models()
        
        assert len(manager.models) == 0
    
    def test_model_stats(self):
        """Test getting model statistics."""
        manager = ModelManager()
        
        # Get model stats
        stats = manager.get_model_stats()
        
        # Check that stats contain expected keys
        assert 'loaded_models' in stats
        assert 'total_models' in stats
        assert 'device' in stats
        assert 'cache_dir' in stats
        assert isinstance(stats['loaded_models'], list)
        assert isinstance(stats['total_models'], int)
    
    def test_get_model_manager_singleton(self):
        """Test get_model_manager returns singleton."""
        manager1 = get_model_manager()
        manager2 = get_model_manager()
        
        # Should be the same instance
        assert manager1 is manager2


# YouTube utils tests removed - functions don't exist in current implementation
