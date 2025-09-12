#!/usr/bin/env python
"""
Add SentimentFeedback table to the database.
Run this script to create the table for storing user feedback on sentiment predictions.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import SentimentFeedback

def create_feedback_table():
    """Create the SentimentFeedback table if it doesn't exist."""
    app = create_app()
    
    with app.app_context():
        # Create the table
        db.create_all()
        
        # Verify it was created
        try:
            # Try a simple query to confirm table exists
            count = SentimentFeedback.query.count()
            print(f"✅ SentimentFeedback table created successfully!")
            print(f"   Current feedback records: {count}")
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🔧 Creating SentimentFeedback table...")
    if create_feedback_table():
        print("🎉 Database is ready for sentiment feedback collection!")
        print("\nUsers can now:")
        print("  • Correct misclassified comments")
        print("  • Help improve the AI model")
        print("  • Provide training data for future improvements")
    else:
        print("❌ Failed to create table. Please check your database configuration.")
