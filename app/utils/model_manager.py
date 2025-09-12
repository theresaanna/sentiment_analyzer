"""
Model Manager - Centralized model loading and caching system
Ensures models are loaded once at startup and cached properly with versioning
"""
import os
import logging
import hashlib
import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import threading
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoModelForSeq2SeqLM,
    pipeline
)
import joblib

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton model manager that handles loading, caching, and versioning of all ML models.
    Ensures models are loaded once at application startup and reused across requests.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Ensure only one instance of ModelManager exists (Singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the model manager (only runs once due to singleton)."""
        if self._initialized:
            return

        self._initialized = True
        self.models = {}
        self.model_metadata = {}
        self.cache_dir = Path("model_cache")
        self.cache_dir.mkdir(exist_ok=True)

        # Model versioning
        self.version_file = self.cache_dir / "model_versions.json"
        self.versions = self._load_versions()

        # Device configuration
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Model Manager initialized with device: {self.device}")

        # Performance monitoring
        self.load_times = {}
        self.model_usage_count = {}

    def _load_versions(self) -> Dict[str, str]:
        """Load model version information from disk."""
        if self.version_file.exists():
            with open(self.version_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_versions(self):
        """Save model version information to disk."""
        with open(self.version_file, 'w') as f:
            json.dump(self.versions, f, indent=2)

    def _get_model_hash(self, model_name: str, model_path: Optional[str] = None) -> str:
        """Generate a unique hash for a model based on name and optional path."""
        hash_input = model_name
        if model_path and os.path.exists(model_path):
            # Include file modification time in hash for local models
            stat = os.stat(model_path)
            hash_input += f"_{stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:8]

    def get_roberta_sentiment(self) -> Tuple[Any, Any]:
        """
        Get RoBERTa sentiment analysis model and tokenizer.
        Loads once on first call, returns cached version on subsequent calls.
        """
        model_key = "roberta_sentiment"

        if model_key in self.models:
            self.model_usage_count[model_key] = self.model_usage_count.get(model_key, 0) + 1
            return self.models[model_key]["tokenizer"], self.models[model_key]["model"]

        logger.info("Loading RoBERTa sentiment model...")
        start_time = datetime.now()

        model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"

        try:
            # Check if we have a cached version
            cache_path = self.cache_dir / f"{model_key}_cache.pkl"
            version_hash = self._get_model_hash(model_name)

            if cache_path.exists() and self.versions.get(model_key) == version_hash:
                logger.info(f"Loading {model_key} from cache...")
                with open(cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                    tokenizer = cached_data["tokenizer"]
                    model = cached_data["model"]
            else:
                logger.info(f"Downloading/updating {model_key}...")
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForSequenceClassification.from_pretrained(model_name)

                # Cache the model
                with open(cache_path, 'wb') as f:
                    pickle.dump({"tokenizer": tokenizer, "model": model}, f)

                # Update version
                self.versions[model_key] = version_hash
                self._save_versions()

            # Move model to device and set to eval mode
            model.to(self.device)
            model.eval()

            # Store in memory
            self.models[model_key] = {
                "tokenizer": tokenizer,
                "model": model,
                "loaded_at": datetime.now(),
                "version": version_hash
            }

            load_time = (datetime.now() - start_time).total_seconds()
            self.load_times[model_key] = load_time
            logger.info(f"RoBERTa sentiment model loaded in {load_time:.2f}s")

            return tokenizer, model

        except Exception as e:
            logger.error(f"Failed to load RoBERTa sentiment model: {e}")
            raise

    def get_fast_sentiment_pipeline(self) -> Any:
        """
        Get fast sentiment analysis pipeline.
        Optimized for speed with distilled models.
        """
        model_key = "fast_sentiment_pipeline"

        if model_key in self.models:
            self.model_usage_count[model_key] = self.model_usage_count.get(model_key, 0) + 1
            return self.models[model_key]["pipeline"]

        logger.info("Loading fast sentiment pipeline...")
        start_time = datetime.now()

        model_name = "distilbert-base-uncased-finetuned-sst-2-english"

        try:
            sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1,
                batch_size=32,
                truncation=True,
                max_length=512
            )

            # Warm up the pipeline
            sentiment_pipeline(["test"], batch_size=1)

            self.models[model_key] = {
                "pipeline": sentiment_pipeline,
                "loaded_at": datetime.now(),
                "version": self._get_model_hash(model_name)
            }

            load_time = (datetime.now() - start_time).total_seconds()
            self.load_times[model_key] = load_time
            logger.info(f"Fast sentiment pipeline loaded in {load_time:.2f}s")

            return sentiment_pipeline

        except Exception as e:
            logger.error(f"Failed to load fast sentiment pipeline: {e}")
            raise

    def get_summarization_model(self) -> Tuple[Any, Any]:
        """
        Get BART summarization model and tokenizer.
        """
        model_key = "bart_summarization"

        if model_key in self.models:
            self.model_usage_count[model_key] = self.model_usage_count.get(model_key, 0) + 1
            return self.models[model_key]["tokenizer"], self.models[model_key]["model"]

        logger.info("Loading BART summarization model...")
        start_time = datetime.now()

        model_name = "facebook/bart-large-cnn"

        try:
            # Use smaller model for Railway deployment if memory is limited
            if os.environ.get('RAILWAY_ENVIRONMENT'):
                model_name = "facebook/bart-base"
                logger.info("Using bart-base for Railway deployment")

            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

            # Move to device
            model.to(self.device)
            model.eval()

            self.models[model_key] = {
                "tokenizer": tokenizer,
                "model": model,
                "loaded_at": datetime.now(),
                "version": self._get_model_hash(model_name)
            }

            load_time = (datetime.now() - start_time).total_seconds()
            self.load_times[model_key] = load_time
            logger.info(f"BART summarization model loaded in {load_time:.2f}s")

            return tokenizer, model

        except Exception as e:
            logger.error(f"Failed to load BART summarization model: {e}")
            raise

    def get_custom_ml_model(self, model_path: Optional[str] = None) -> Any:
        """
        Get custom trained ML model (sklearn/gradient boosting).
        """
        model_key = "custom_ml_model"

        # Use provided path or default to latest
        if model_path is None:
            model_path = "models/latest_model.pkl"

        # Check if model needs reloading (file changed)
        model_hash = self._get_model_hash(model_key, model_path)

        if model_key in self.models:
            if self.models[model_key].get("version") == model_hash:
                self.model_usage_count[model_key] = self.model_usage_count.get(model_key, 0) + 1
                return self.models[model_key]["model"]

        logger.info(f"Loading custom ML model from {model_path}...")
        start_time = datetime.now()

        try:
            if not os.path.exists(model_path):
                logger.warning(f"Custom model not found at {model_path}")
                return None

            model = joblib.load(model_path)

            # Load metadata if available
            metadata_path = Path(model_path).with_suffix('') + '_metadata.json'
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

            self.models[model_key] = {
                "model": model,
                "metadata": metadata,
                "loaded_at": datetime.now(),
                "version": model_hash,
                "path": model_path
            }

            load_time = (datetime.now() - start_time).total_seconds()
            self.load_times[model_key] = load_time
            logger.info(f"Custom ML model loaded in {load_time:.2f}s")

            return model

        except Exception as e:
            logger.error(f"Failed to load custom ML model: {e}")
            return None

    def preload_all_models(self):
        """
        Preload all models at application startup.
        This should be called once during app initialization.
        """
        logger.info("Preloading all models at startup...")
        start_time = datetime.now()

        try:
            # Load sentiment models
            self.get_roberta_sentiment()
            self.get_fast_sentiment_pipeline()

            # Load summarization model (optional for memory-constrained environments)
            if not os.environ.get('MINIMAL_MODELS'):
                self.get_summarization_model()

            # Load custom ML model if exists
            self.get_custom_ml_model()

            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"All models preloaded in {total_time:.2f}s")

            # Log memory usage
            if torch.cuda.is_available():
                logger.info(f"GPU memory allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

        except Exception as e:
            logger.error(f"Error during model preloading: {e}")
            # Don't crash the app if preloading fails

    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded models."""
        stats = {
            "loaded_models": list(self.models.keys()),
            "total_models": len(self.models),
            "load_times": self.load_times,
            "usage_counts": self.model_usage_count,
            "device": str(self.device),
            "cache_dir": str(self.cache_dir),
            "versions": self.versions
        }

        # Add memory usage if available
        if torch.cuda.is_available():
            stats["gpu_memory_gb"] = torch.cuda.memory_allocated() / 1e9

        # Add model-specific info
        for key, model_info in self.models.items():
            stats[f"{key}_loaded_at"] = model_info.get("loaded_at", "").isoformat() if model_info.get(
                "loaded_at") else ""
            stats[f"{key}_version"] = model_info.get("version", "unknown")

        return stats

    def clear_model(self, model_key: str):
        """Clear a specific model from memory."""
        if model_key in self.models:
            del self.models[model_key]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"Cleared model: {model_key}")

    def clear_all_models(self):
        """Clear all models from memory."""
        self.models.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Cleared all models from memory")


# Global model manager instance
model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """Get the global model manager instance."""
    return model_manager