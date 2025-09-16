#!/usr/bin/env python
"""
Unified Railway startup script that handles everything.
Combines database setup, PORT handling, and server startup.
"""
import os
import sys
import subprocess
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_database_url():
    """Fix Railway's postgres:// URL to postgresql://"""
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)
        logger.info("Fixed DATABASE_URL for PostgreSQL compatibility")

def get_clean_port():
    """Get and validate PORT from environment."""
    port_value = os.environ.get('PORT', '8000')
    
    # Remove any non-numeric characters that might have been added
    # This handles cases where PORT might be "$PORT" or have quotes
    import re
    cleaned_port = re.sub(r'[^0-9]', '', str(port_value))
    
    # If we couldn't extract a number, use default
    if not cleaned_port:
        logger.warning(f"Could not parse PORT value '{port_value}', using default 8000")
        return '8000'
    
    # Validate the port number
    try:
        port_int = int(cleaned_port)
        if port_int < 1 or port_int > 65535:
            logger.warning(f"Port {port_int} out of valid range, using default 8000")
            return '8000'
        return str(port_int)
    except ValueError:
        logger.warning(f"Invalid PORT value '{cleaned_port}', using default 8000")
        return '8000'

def run_migrations():
    """Run database migrations."""
    logger.info("Running database migrations...")
    try:
        result = subprocess.run(
            ['flask', 'db', 'upgrade'],
            capture_output=True,
            text=True,
            env=os.environ
        )
        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
        else:
            logger.warning(f"Migration warning: {result.stderr}")
            # Don't fail - the app might still work
    except Exception as e:
        logger.warning(f"Migration failed: {e}")
        logger.info("Continuing anyway - app may still function")

def main():
    logger.info("Railway startup script initializing...")
    
    # Step 1: Fix database URL
    fix_database_url()
    
    # Step 2: Get clean port
    port = get_clean_port()
    logger.info(f"Using PORT: {port}")
    
    # Step 3: Run migrations (non-blocking)
    run_migrations()
    
    # Step 4: Start gunicorn
    gunicorn_cmd = [
        'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--timeout', '120',
        '--workers', '1',
        '--threads', '4',
        '--worker-class', 'gthread',
        '--log-level', 'info',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'run:app'
    ]
    
    logger.info(f"Starting Gunicorn with command: {' '.join(gunicorn_cmd)}")
    
    # Replace current process with gunicorn
    os.execvp('gunicorn', gunicorn_cmd)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        sys.exit(1)