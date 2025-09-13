"""
Fast Sentiment Analyzer using centralized Model Manager
Optimized for speed with model caching
"""
import logging
import torch
import torch.nn.functional as F
from concurrent.futures import ThreadPoolExecutor
from app.cache import cache
from app.utils.model_manager import get_model_manager

logger = logging.getLogger(__name__)


class FastSentimentAnalyzer:
    """Fast sentiment analyzer using cached pipeline from Model Manager."""

    def __init__(self, batch_size=32):
        """Initialize the fast sentiment analyzer."""
        self.model_manager = get_model_manager()
        self.max_length = 512
        self.batch_size = batch_size
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Get pipeline on initialization (it will be cached)
        self.pipeline = self.model_manager.get_fast_sentiment_pipeline()
        
        # Try to get the underlying model and tokenizer for GPU optimization
        self.model = None
        self.tokenizer = None
        self.label_mapping = {'POSITIVE': 'positive', 'NEGATIVE': 'negative', 'NEUTRAL': 'neutral'}
        
        try:
            if hasattr(self.pipeline, 'model'):
                self.model = self.pipeline.model
                self.tokenizer = self.pipeline.tokenizer
                if self.model and torch.cuda.is_available():
                    self.model.to(self.device)
        except Exception as e:
            logger.warning(f"Could not extract model for GPU optimization: {e}")
        
        logger.info(f"Fast sentiment analyzer initialized with device: {self.device}")

    def _preprocess_texts(self, texts):
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

    def analyze_batch_fast(self, texts,
                          progress_callback=None):
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
                    current = i + 1
                    total = len(texts)
                    try:
                        progress_callback(current, total)
                    except TypeError:
                        # Backward compatibility: single-arg callbacks (percentage)
                        progress = current / total * 100
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

    def analyze_with_cache(self, texts, cache_key,
                          progress_callback=None):
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

    def get_sentiment_score(self, text):
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

    def filter_by_sentiment(self, texts,
                           sentiment_filter='all'):
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
    
    def analyze_batch_gpu_optimized(self, 
                                   texts,
                                   max_length=512):
        """
        GPU-optimized batch processing using tensor batching.
        
        Args:
            texts: List of texts to analyze
            max_length: Maximum sequence length
            
        Returns:
            List of sentiment results
        """
        if not texts:
            return []
        
        # Fall back to pipeline if model/tokenizer not available
        if not self.model or not self.tokenizer:
            results = self.pipeline(texts)
            formatted_results = []
            for i, result in enumerate(results):
                label = result['label'].lower()
                if 'pos' in label:
                    label = 'positive'
                elif 'neg' in label:
                    label = 'negative'
                else:
                    label = 'neutral'
                
                formatted_results.append({
                    'text': texts[i],
                    'sentiment': label,
                    'confidence': result['score'],
                    'method': 'pipeline_batch'
                })
            return formatted_results
        
        # Tokenize all texts at once
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt"
        )
        
        # Move to GPU if available
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        
        # Perform inference with no gradient calculation
        with torch.no_grad():
            # Use mixed precision if available
            if torch.cuda.is_available():
                try:
                    with torch.cuda.amp.autocast():
                        outputs = self.model(**encoded)
                except:
                    outputs = self.model(**encoded)
            else:
                outputs = self.model(**encoded)
        
        # Process outputs
        logits = outputs.logits
        probabilities = F.softmax(logits, dim=-1)
        predictions = torch.argmax(logits, dim=-1)
        
        # Convert to CPU for processing
        probabilities = probabilities.cpu().numpy()
        predictions = predictions.cpu().numpy()
        
        # Format results
        results = []
        for i, (text, pred, probs) in enumerate(zip(texts, predictions, probabilities)):
            # Map prediction to label
            if hasattr(self.model.config, 'id2label'):
                sentiment_label = self.model.config.id2label[pred]
                sentiment = self.label_mapping.get(sentiment_label, 'neutral')
            else:
                sentiment = ['negative', 'neutral', 'positive'][pred] if pred < 3 else 'neutral'
            
            result = {
                'text': text,
                'sentiment': sentiment,
                'confidence': float(probs[pred]),
                'probabilities': {
                    'negative': float(probs[0]) if len(probs) > 0 else 0,
                    'neutral': float(probs[1]) if len(probs) > 1 else 0,
                    'positive': float(probs[2]) if len(probs) > 2 else 0
                },
                'method': 'gpu_optimized_batch'
            }
            results.append(result)
        
        return results
    
    def analyze_with_prefetch(self,
                             texts,
                             prefetch_size=2):
        """
        Analyze with data prefetching for improved throughput.
        
        Args:
            texts: List of texts to analyze
            prefetch_size: Number of batches to prefetch
            
        Returns:
            List of analysis results
        """
        if not self.tokenizer:
            # Fall back to standard batch processing
            return self.analyze_batch_gpu_optimized(texts)
        
        # Create batches
        batches = [texts[i:i+self.batch_size] 
                  for i in range(0, len(texts), self.batch_size)]
        
        # Prefetch queue
        results = []
        
        def prefetch_batch(batch):
            """Prefetch and tokenize batch."""
            return self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Start prefetching
            futures = []
            for i in range(min(prefetch_size, len(batches))):
                future = executor.submit(prefetch_batch, batches[i])
                futures.append(future)
            
            batch_idx = 0
            while batch_idx < len(batches):
                # Get prefetched batch
                if futures:
                    encoded = futures.pop(0).result()
                    
                    # Start prefetching next batch
                    next_idx = batch_idx + prefetch_size
                    if next_idx < len(batches):
                        future = executor.submit(prefetch_batch, batches[next_idx])
                        futures.append(future)
                    
                    # Process current batch
                    encoded = {k: v.to(self.device) for k, v in encoded.items()}
                    
                    with torch.no_grad():
                        outputs = self.model(**encoded)
                    
                    # Process outputs
                    batch_results = self._process_outputs(
                        outputs, 
                        batches[batch_idx]
                    )
                    results.extend(batch_results)
                    
                    batch_idx += 1
        
        return results
    
    def _process_outputs(self, outputs, texts):
        """
        Process model outputs into formatted results.
        
        Args:
            outputs: Model outputs
            texts: Original input texts
            
        Returns:
            List of formatted results
        """
        logits = outputs.logits
        probabilities = F.softmax(logits, dim=-1)
        predictions = torch.argmax(logits, dim=-1)
        
        probabilities = probabilities.cpu().numpy()
        predictions = predictions.cpu().numpy()
        
        results = []
        for text, pred, probs in zip(texts, predictions, probabilities):
            if hasattr(self.model.config, 'id2label'):
                sentiment_label = self.model.config.id2label[pred]
                sentiment = self.label_mapping.get(sentiment_label, 'neutral')
            else:
                sentiment = ['negative', 'neutral', 'positive'][pred] if pred < 3 else 'neutral'
            
            result = {
                'text': text,
                'sentiment': sentiment,
                'confidence': float(probs[pred]),
                'probabilities': {
                    'negative': float(probs[0]) if len(probs) > 0 else 0,
                    'neutral': float(probs[1]) if len(probs) > 1 else 0,
                    'positive': float(probs[2]) if len(probs) > 2 else 0
                },
                'method': 'prefetch_batch'
            }
            results.append(result)
        
        return results


# Global instance for reuse across the application
_fast_analyzer = None

def get_fast_analyzer():
    """Get or create the global fast sentiment analyzer instance."""
    global _fast_analyzer
    if _fast_analyzer is None:
        _fast_analyzer = FastSentimentAnalyzer()
    return _fast_analyzer