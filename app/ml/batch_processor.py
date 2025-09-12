"""
Batch Processor Module for Optimized Inference

Handles dynamic batch sizing, memory management, and parallel processing
for sentiment analysis models.
"""
import os
import logging
import numpy as np
import torch
from typing import List, Dict, Any, Optional, Callable, Tuple, Generator
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil
from dataclasses import dataclass
from collections import deque
import time

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    min_batch_size: int = 8
    max_batch_size: int = 128
    optimal_batch_size: int = 32
    memory_threshold: float = 0.8  # Use max 80% of available memory
    enable_dynamic_batching: bool = True
    enable_gpu_optimization: bool = True
    max_sequence_length: int = 512
    num_workers: int = 4


class DynamicBatchProcessor:
    """
    Dynamic batch processor that optimizes batch sizes based on available resources.
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """
        Initialize the batch processor with configuration.
        
        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.memory_monitor = MemoryMonitor()
        self.batch_queue = deque()
        self.processing_stats = {
            'total_processed': 0,
            'total_batches': 0,
            'average_batch_size': 0,
            'total_time': 0
        }
        
        logger.info(f"Initialized DynamicBatchProcessor with device: {self.device}")
    
    def calculate_optimal_batch_size(self, 
                                    text_lengths: List[int],
                                    model_size_mb: float = 500) -> int:
        """
        Calculate optimal batch size based on available memory and text lengths.
        
        Args:
            text_lengths: List of text lengths in the dataset
            model_size_mb: Estimated model size in MB
            
        Returns:
            Optimal batch size
        """
        if not self.config.enable_dynamic_batching:
            return self.config.optimal_batch_size
        
        # Get available memory
        available_memory_mb = self.memory_monitor.get_available_memory_mb()
        
        # Calculate average text length
        avg_text_length = np.mean(text_lengths) if text_lengths else 256
        
        # Estimate memory per sample (rough approximation)
        memory_per_sample_mb = (avg_text_length * 4 * 2) / (1024 * 1024)  # tokens * bytes * overhead
        
        # Calculate maximum batch size based on memory
        max_batch_from_memory = int(
            (available_memory_mb * self.config.memory_threshold - model_size_mb) 
            / memory_per_sample_mb
        )
        
        # Apply constraints
        optimal_batch = min(
            max(self.config.min_batch_size, max_batch_from_memory),
            self.config.max_batch_size
        )
        
        logger.info(f"Calculated optimal batch size: {optimal_batch} "
                   f"(available memory: {available_memory_mb:.1f}MB)")
        
        return optimal_batch
    
    def create_batches(self, 
                      texts: List[str], 
                      dynamic_sizing: bool = True) -> Tuple[List[List[str]], List[int]]:
        """
        Create optimized batches from input texts.
        
        Args:
            texts: List of input texts
            dynamic_sizing: Whether to use dynamic batch sizing
            
        Returns:
            Tuple of (list of text batches, sorted indices)
        """
        if not texts:
            return [], []
        
        # Calculate text lengths
        text_lengths = [len(text) for text in texts]
        
        # Determine batch size
        if dynamic_sizing and self.config.enable_dynamic_batching:
            batch_size = self.calculate_optimal_batch_size(text_lengths)
        else:
            batch_size = self.config.optimal_batch_size
        
        # Sort texts by length for more efficient batching (padding optimization)
        sorted_indices = np.argsort(text_lengths).tolist()
        sorted_texts = [texts[i] for i in sorted_indices]
        
        # Create batches
        batches = []
        for i in range(0, len(sorted_texts), batch_size):
            batch = sorted_texts[i:i + batch_size]
            batches.append(batch)
        
        logger.info(f"Created {len(batches)} batches from {len(texts)} texts "
                   f"(batch size: {batch_size})")
        
        return batches, sorted_indices
    
    def process_batch_parallel(self,
                              batch: List[str],
                              process_func: Callable,
                              num_workers: Optional[int] = None) -> List[Any]:
        """
        Process a batch in parallel using multiple workers.
        
        Args:
            batch: Batch of texts to process
            process_func: Function to apply to each text
            num_workers: Number of parallel workers
            
        Returns:
            List of processed results
        """
        num_workers = num_workers or self.config.num_workers
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(process_func, batch))
        
        return results
    
    def update_stats(self, batch_size: int, processing_time: float):
        """Update processing statistics."""
        self.processing_stats['total_processed'] += batch_size
        self.processing_stats['total_batches'] += 1
        self.processing_stats['total_time'] += processing_time
        
        # Update running average
        self.processing_stats['average_batch_size'] = (
            self.processing_stats['total_processed'] / 
            self.processing_stats['total_batches']
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = self.processing_stats.copy()
        if stats['total_time'] > 0:
            stats['throughput'] = stats['total_processed'] / stats['total_time']
        else:
            stats['throughput'] = 0
        return stats


class MemoryMonitor:
    """Monitor system memory for dynamic batch sizing."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
    
    def get_available_memory_mb(self) -> float:
        """Get available system memory in MB."""
        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 * 1024)
        return available_mb
    
    def get_process_memory_mb(self) -> float:
        """Get current process memory usage in MB."""
        mem_info = self.process.memory_info()
        return mem_info.rss / (1024 * 1024)
    
    def get_gpu_memory_mb(self) -> Optional[float]:
        """Get available GPU memory if CUDA is available."""
        if torch.cuda.is_available():
            # Get GPU memory stats
            allocated = torch.cuda.memory_allocated() / (1024 * 1024)
            reserved = torch.cuda.memory_reserved() / (1024 * 1024)
            return reserved - allocated
        return None


class BatchInferenceOptimizer:
    """
    Main class for optimized batch inference combining all techniques.
    """
    
    def __init__(self, 
                 model,
                 config: Optional[BatchConfig] = None):
        """
        Initialize the batch inference optimizer.
        
        Args:
            model: The ML model to use for inference
            config: Batch processing configuration
        """
        self.model = model
        self.config = config or BatchConfig()
        self.processor = DynamicBatchProcessor(config)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Move model to device and set to eval mode
        if hasattr(self.model, 'to'):
            self.model.to(self.device)
        if hasattr(self.model, 'eval'):
            self.model.eval()
        
        # Enable GPU optimizations if available
        if self.config.enable_gpu_optimization and torch.cuda.is_available():
            self._enable_gpu_optimizations()
    
    def _enable_gpu_optimizations(self):
        """Enable GPU-specific optimizations."""
        # Enable TensorCore operations for faster computation
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        
        # Enable mixed precision if available
        try:
            from torch.cuda.amp import autocast
            self.use_amp = True
            logger.info("Enabled mixed precision training (AMP)")
        except ImportError:
            self.use_amp = False
    
    def batch_predict(self, 
                     texts: List[str],
                     progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Perform optimized batch prediction on texts.
        
        Args:
            texts: List of texts to analyze
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of prediction results
        """
        if not texts:
            return []
        
        start_time = time.time()
        
        # Create optimized batches
        batches, sorted_indices = self.processor.create_batches(texts, dynamic_sizing=True)
        
        all_results = []
        total_batches = len(batches)
        
        for batch_idx, batch in enumerate(batches):
            batch_start_time = time.time()
            
            # Process batch
            if hasattr(self.model, 'predict_batch'):
                # Model has native batch support
                batch_results = self.model.predict_batch(batch)
            elif hasattr(self.model, 'analyze_batch'):
                # Alternative batch method
                batch_results = self.model.analyze_batch(batch)
            else:
                # Fall back to sequential processing
                batch_results = []
                for text in batch:
                    if hasattr(self.model, 'analyze_sentiment'):
                        result = self.model.analyze_sentiment(text)
                    elif hasattr(self.model, 'predict'):
                        result = self.model.predict(text)
                    else:
                        result = {'text': text, 'sentiment': 'neutral', 'confidence': 0.5}
                    batch_results.append(result)
            
            all_results.extend(batch_results)
            
            # Update statistics
            batch_time = time.time() - batch_start_time
            self.processor.update_stats(len(batch), batch_time)
            
            # Call progress callback
            if progress_callback:
                progress = (batch_idx + 1) / total_batches
                progress_callback(batch_idx + 1, total_batches, progress)
            
            logger.debug(f"Processed batch {batch_idx + 1}/{total_batches} "
                        f"({len(batch)} samples) in {batch_time:.2f}s")
        
        # Restore original order
        original_order_results = [None] * len(texts)
        for idx, result in zip(sorted_indices, all_results):
            original_order_results[idx] = result
        
        total_time = time.time() - start_time
        throughput = len(texts) / total_time if total_time > 0 else 0
        
        logger.info(f"Batch inference completed: {len(texts)} texts in {total_time:.2f}s "
                   f"({throughput:.1f} texts/sec)")
        
        return original_order_results