#!/usr/bin/env python
"""
Railway startup script - Handles database setup and model preloading
Run this before starting the main application
"""
import os
import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fix_database_url():
    """Fix Railway's postgres:// URL to postgresql://"""
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)
        logger.info("Fixed DATABASE_URL for PostgreSQL compatibility")
        return True
    return False


def setup_cache_directories():
    """Create cache directories for models."""
    cache_dirs = [
        Path(os.environ.get('MODEL_CACHE_DIR', '/app/model_cache')),
        Path(os.environ.get('TRANSFORMERS_CACHE', '/app/.cache/huggingface')),
        Path('model_cache'),
        Path('models')
    ]

    for cache_dir in cache_dirs:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created cache directory: {cache_dir}")
        except Exception as e:
            logger.warning(f"Could not create {cache_dir}: {e}")


def run_migrations():
    """Run database migrations."""
    logger.info("Running database migrations...")

    # Skip model preloading during migrations
    os.environ['SKIP_MODEL_PRELOAD'] = '1'

    try:
        # Try Flask-Migrate first
        result = subprocess.run(
            ['flask', 'db', 'upgrade'],
            capture_output=True,
            text=True,
            env=os.environ
        )

        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
            return True
        else:
            logger.warning(f"Flask-Migrate failed: {result.stderr}")

            # Fallback: Create tables directly
            logger.info("Attempting fallback: creating tables directly...")
            from app import create_app, db
            app = create_app()
            with app.app_context():
                db.create_all()
                logger.info("Database tables created successfully")
            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    finally:
        # Re-enable model preloading
        os.environ.pop('SKIP_MODEL_PRELOAD', None)


def preload_models():
    """Preload ML models into cache."""
    logger.info("Preloading ML models...")

    try:
        from app import create_app
        from app.utils.model_manager import get_model_manager

        app = create_app()
        with app.app_context():
            model_manager = get_model_manager()

            # Check available memory (Railway specific)
            if os.environ.get('RAILWAY_ENVIRONMENT'):
                import psutil
                available_memory = psutil.virtual_memory().available / (1024 ** 3)  # GB
                logger.info(f"Available memory: {available_memory:.2f} GB")

                if available_memory < 2:
                    logger.warning("Low memory detected, using minimal models")
                    os.environ['MINIMAL_MODELS'] = '1'

            # Preload models
            model_manager.preload_all_models()

            # Get statistics
            stats = model_manager.get_model_stats()
            logger.info(f"Preloaded models: {stats.get('loaded_models', [])}")

            # Warm up models with sample predictions
            logger.info("Warming up models with sample predictions...")

            # Warm up sentiment analyzer
            from app.science.sentiment_analyzer import get_sentiment_analyzer
            analyzer = get_sentiment_analyzer()
            analyzer.analyze_sentiment("This is a test")

            # Warm up fast analyzer
            from app.science.fast_sentiment_analyzer import get_fast_analyzer
            fast_analyzer = get_fast_analyzer()
            fast_analyzer.analyze_batch_fast(["Test comment"])

            logger.info("Model warm-up completed")
            return True

    except Exception as e:
        logger.error(f"Model preloading failed: {e}")
        # Don't fail startup if models can't be preloaded
        # They will be loaded on-demand
        return False


def optimize_for_railway():
    """Apply Railway-specific optimizations."""
    logger.info("Applying Railway optimizations...")

    # Set environment variables for optimization
    optimizations = {
        'TOKENIZERS_PARALLELISM': 'false',  # Avoid tokenizer warnings
        'TF_CPP_MIN_LOG_LEVEL': '2',  # Reduce TensorFlow logging
        'PYTHONUNBUFFERED': '1',  # Ensure logs are visible
        'TRANSFORMERS_OFFLINE': '0',  # Allow model downloads if needed
        'TORCH_HOME': '/app/.cache/torch',  # Set torch cache location
    }

    for key, value in optimizations.items():
        if key not in os.environ:
            os.environ[key] = value
            logger.info(f"Set {key}={value}")


def check_environment():
    """Check and log environment configuration."""
    logger.info("Environment Configuration:")
    logger.info(f"  Railway Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'Not set')}")
    logger.info(f"  Database URL: {'Set' if os.environ.get('DATABASE_URL') else 'Not set'}")
    logger.info(f"  Port: {os.environ.get('PORT', '8000')}")
    logger.info(f"  Python Version: {sys.version}")

    # Check for required environment variables
    required_vars = ['DATABASE_URL']
    missing = [var for var in required_vars if not os.environ.get(var)]

    if missing:
        logger.warning(f"Missing environment variables: {missing}")
        logger.warning("The application may not function correctly")

    # Check optional API keys
    optional_vars = ['YOUTUBE_API_KEY', 'OPENAI_API_KEY']
    for var in optional_vars:
        if os.environ.get(var):
            logger.info(f"  {var}: Configured")
        else:
            logger.info(f"  {var}: Not configured (some features may be limited)")


def main():
    """Main startup sequence."""
    logger.info("=" * 60)
    logger.info("Railway Startup Script - Initializing Application")
    logger.info("=" * 60)

    try:
        # Step 1: Check environment
        check_environment()

        # Step 2: Fix database URL
        fix_database_url()

        # Step 3: Setup cache directories
        setup_cache_directories()

        # Step 4: Apply optimizations
        optimize_for_railway()

        # Step 5: Run migrations
        if not run_migrations():
            logger.error("Database setup failed, but continuing...")

        # Step 6: Preload models (optional, non-critical)
        if not os.environ.get('SKIP_MODEL_PRELOAD'):
            if not preload_models():
                logger.warning("Model preloading failed, models will load on-demand")

        logger.info("=" * 60)
        logger.info("Startup sequence completed successfully!")
        logger.info("Application is ready to serve requests")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Startup failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())