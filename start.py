#!/usr/bin/env python
"""
Simple startup script for Railway deployment.
Handles PORT environment variable properly.
"""
import os
import sys
import subprocess

def main():
    # Get PORT from environment, with fallback
    port = os.environ.get('PORT', '8000')
    
    # Validate port
    try:
        port_int = int(port)
        if port_int < 1 or port_int > 65535:
            raise ValueError(f"Port {port_int} out of valid range")
    except (ValueError, TypeError):
        print(f"Warning: Invalid PORT value '{port}', using default 8000")
        port = '8000'
        os.environ['PORT'] = port
    
    print(f"Starting web server on port {port}...")
    
    # Run database migrations
    print("Running database migrations...")
    try:
        subprocess.run(['flask', 'db', 'upgrade'], check=True)
        print("Database migrations completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Database migration failed: {e}")
        print("Continuing with startup anyway...")
    
    # Start gunicorn
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
    
    print(f"Starting Gunicorn: {' '.join(gunicorn_cmd)}")
    
    # Replace current process with gunicorn
    os.execvp('gunicorn', gunicorn_cmd)

if __name__ == '__main__':
    main()