#!/usr/bin/env python
"""
Minimal startup script that directly starts gunicorn.
No shell expansion, reads PORT at runtime.
"""
import os
import sys

# Get port from environment
port = os.environ.get('PORT', '8000')

# Clean the port value - remove any quotes, dollar signs, etc.
port = port.strip().strip('"').strip("'").replace('$', '').replace('PORT', '').strip()

# If port is empty or invalid, use default
if not port or not port.isdigit():
    print(f"Invalid PORT value detected: '{os.environ.get('PORT')}', using 8000")
    port = '8000'

print(f"Starting server on port {port}")

# Direct exec to gunicorn
os.execvp('gunicorn', [
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
])