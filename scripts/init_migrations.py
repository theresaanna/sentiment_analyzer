#!/usr/bin/env python
"""
Initialize database migrations for the Sentiment Analyzer application.
This script sets up Flask-Migrate and creates the initial migration.
"""
import os
import sys
import subprocess

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User


def init_migrations():
    """Initialize the migration repository."""
    print("Initializing database migrations...")
    
    # Check if migrations folder exists
    if os.path.exists('migrations'):
        response = input("Migrations folder already exists. Do you want to reinitialize? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
        
        # Remove existing migrations folder
        import shutil
        shutil.rmtree('migrations')
        print("Removed existing migrations folder.")
    
    # Initialize Flask-Migrate
    result = subprocess.run(['flask', 'db', 'init'], 
                          env={**os.environ, 'FLASK_APP': 'run.py'},
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Migration repository initialized successfully.")
        print(result.stdout)
    else:
        print("✗ Failed to initialize migrations:")
        print(result.stderr)
        return
    
    # Create initial migration
    print("\nCreating initial migration...")
    result = subprocess.run(['flask', 'db', 'migrate', '-m', 'Initial migration'], 
                          env={**os.environ, 'FLASK_APP': 'run.py'},
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Initial migration created successfully.")
        print(result.stdout)
    else:
        print("✗ Failed to create initial migration:")
        print(result.stderr)
        return
    
    # Apply the migration
    print("\nApplying migration to database...")
    result = subprocess.run(['flask', 'db', 'upgrade'], 
                          env={**os.environ, 'FLASK_APP': 'run.py'},
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Migration applied successfully.")
        print(result.stdout)
    else:
        print("✗ Failed to apply migration:")
        print(result.stderr)
        return
    
    print("\n✅ Database migrations initialized successfully!")
    print("\nYou can now use the following commands:")
    print("  flask db migrate -m 'description'  # Create a new migration")
    print("  flask db upgrade                   # Apply migrations")
    print("  flask db downgrade                 # Rollback migrations")
    print("  flask db history                   # View migration history")
    print("  flask db current                   # Show current migration")


if __name__ == '__main__':
    # Change to project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # Create app context
    app = create_app()
    with app.app_context():
        init_migrations()
