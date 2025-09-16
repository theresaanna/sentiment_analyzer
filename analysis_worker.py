#!/usr/bin/env python3
"""
Background worker for processing sentiment analysis jobs.
Run this as a separate process to handle queued analysis jobs.
"""
import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import AnalysisJob
from app.services.enhanced_youtube_service import EnhancedYouTubeService
from app.services.sentiment_api import get_sentiment_client
from app.cache import cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalysisWorker:
    """Worker class for processing analysis jobs."""
    
    def __init__(self, app):
        self.app = app
        self.youtube_service = EnhancedYouTubeService()
        self.sentiment_client = get_sentiment_client()
        self.running = True
        
    def process_job(self, job: AnalysisJob) -> None:
        """Process a single analysis job."""
        logger.info(f"Starting processing for job {job.job_id}")
        start_time = time.time()
        
        # Check if this is a PRO preload job
        is_preload = False
        if job.results and isinstance(job.results, dict):
            is_preload = job.results.get('job_type') == 'pro_preload'
        
        try:
            # Update job status to processing
            job.status = 'processing'
            job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.progress = 5
            db.session.commit()
            
            # Check for cancellation
            if self._is_cancelled(job.job_id):
                self._cancel_job(job)
                return
            
            # Step 1: Fetch video info and comments
            job_type = "PRO Preload" if is_preload else "Analysis"
            logger.info(f"[{job_type}] Fetching comments for video {job.video_id}")
            job.progress = 10
            db.session.commit()
            
            result = self.youtube_service.get_all_available_comments(
                video_id=job.video_id,
                target_comments=job.comment_count_requested,
                include_replies=getattr(job, 'include_replies', True),  # Use job setting, default to True
                sort_order='relevance'
            )
            
            video_info = result.get('video', {})
            comments = result.get('comments', [])
            fetch_stats = result.get('statistics', {})
            
            # Update job with video info
            job.video_title = video_info.get('title', 'Unknown Title')
            job.channel_name = video_info.get('channel_title', 'Unknown Channel')
            job.comment_count_processed = len(comments)
            job.progress = 30
            db.session.commit()
            
            logger.info(f"Fetched {len(comments)} comments for job {job.job_id}")
            
            # Check for cancellation
            if self._is_cancelled(job.job_id):
                self._cancel_job(job)
                return
            
            # Step 2: Analyze sentiment
            if comments:
                logger.info(f"Analyzing sentiment for {len(comments)} comments")
                job.progress = 40
                db.session.commit()
                
                comment_texts = [c['text'] for c in comments]
                
                # Batch analysis with progress updates
                batch_size = 100
                all_results = []
                
                for i in range(0, len(comment_texts), batch_size):
                    batch = comment_texts[i:i+batch_size]
                    batch_result = self.sentiment_client.analyze_batch(batch)
                    
                    if batch_result and batch_result.get('results'):
                        all_results.extend(batch_result['results'])
                    
                    # Update progress
                    progress = 40 + int((i / len(comment_texts)) * 40)
                    job.progress = min(progress, 80)
                    db.session.commit()
                    
                    # Check for cancellation
                    if self._is_cancelled(job.job_id):
                        self._cancel_job(job)
                        return
                
                # Calculate statistics
                sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
                total_confidence = 0
                
                for result in all_results:
                    sentiment = result.get('predicted_sentiment', 'neutral')
                    sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
                    total_confidence += result.get('confidence', 0)
                
                total_analyzed = len(all_results)
                sentiment_percentages = {
                    k: (v / total_analyzed * 100) if total_analyzed > 0 else 0
                    for k, v in sentiment_counts.items()
                }
                
                # Determine overall sentiment
                if sentiment_percentages['positive'] >= 50:
                    overall_sentiment = 'positive'
                elif sentiment_percentages['negative'] >= 40:
                    overall_sentiment = 'negative'
                else:
                    overall_sentiment = 'neutral'
                
                # Calculate sentiment score (-1 to 1)
                sentiment_score = (sentiment_counts['positive'] - sentiment_counts['negative']) / total_analyzed if total_analyzed > 0 else 0
                
                # Calculate additional stats from comments
                unique_commenters = set()
                total_length = 0
                replies_count = 0
                top_level_count = 0
                
                for comment in comments:
                    if 'author_channel_id' in comment:
                        unique_commenters.add(comment['author_channel_id'])
                    total_length += len(comment.get('text', ''))
                    if comment.get('is_reply', False):
                        replies_count += 1
                    else:
                        top_level_count += 1
                
                avg_comment_length = round(total_length / len(comments)) if comments else 0
                
                # Calculate top commenters
                commenter_frequency = {}
                for comment in comments:
                    author = comment.get('author', 'Anonymous')
                    commenter_frequency[author] = commenter_frequency.get(author, 0) + 1
                
                top_commenters = sorted(
                    commenter_frequency.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                # Calculate analysis depth percentage
                total_available = video_info.get('statistics', {}).get('comments', len(comments))
                analysis_depth_percentage = round((len(comments) / total_available * 100), 1) if total_available > 0 else 100
                
                # Prepare results
                results = {
                    'video_info': video_info,
                    'comment_stats': {
                        'total_comments': len(comments),
                        'fetched_comments': len(comments),
                        'total_analyzed': total_analyzed,
                        'unique_commenters': len(unique_commenters),
                        'avg_comment_length': avg_comment_length,
                        'replies_count': replies_count,
                        'top_level_count': top_level_count,
                        'threads_fetched': fetch_stats.get('threads_fetched', top_level_count),
                        'total_top_level_comments': fetch_stats.get('total_top_level_comments', top_level_count),
                        'fetch_stats': fetch_stats
                    },
                    # Include updated_stats for JavaScript updateCommentStatistics function
                    'updated_stats': {
                        'total_analyzed': total_analyzed,
                        'unique_commenters': len(unique_commenters),
                        'avg_comment_length': avg_comment_length,
                        'replies_count': replies_count,
                        'top_level_count': top_level_count,
                        'top_commenters': top_commenters,
                        'analysis_depth_percentage': analysis_depth_percentage
                    },
                    'sentiment_analysis': {
                        'overall_sentiment': overall_sentiment,
                        'sentiment_score': sentiment_score,
                        'distribution': sentiment_counts,
                        'percentages': sentiment_percentages,
                        'average_confidence': total_confidence / total_analyzed if total_analyzed > 0 else 0,
                        'individual_results': all_results[:500],  # Store up to 500 for display
                        'summary': f"Analysis of {total_analyzed} comments shows {overall_sentiment} sentiment overall. "
                                  f"{sentiment_percentages.get('positive', 0):.1f}% positive, "
                                  f"{sentiment_percentages.get('neutral', 0):.1f}% neutral, "
                                  f"{sentiment_percentages.get('negative', 0):.1f}% negative."
                    },
                    'processing_metadata': {
                        'model': 'enhanced-sentiment-v1',
                        'analyzed_at': datetime.now(timezone.utc).isoformat()
                    }
                }
                
            else:
                # No comments found
                results = {
                    'video_info': video_info,
                    'comment_stats': {'total_comments': 0, 'total_analyzed': 0},
                    'sentiment_analysis': {
                        'overall_sentiment': 'neutral',
                        'sentiment_score': 0,
                        'distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
                        'percentages': {'positive': 0, 'neutral': 0, 'negative': 0},
                        'average_confidence': 0,
                        'individual_results': []
                    }
                }
            
            # Step 3: Save results
            job.results = results
            job.status = 'completed'
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.processing_time_seconds = time.time() - start_time
            db.session.commit()
            
            logger.info(f"Successfully completed job {job.job_id} in {job.processing_time_seconds:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error processing job {job.job_id}: {str(e)}")
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.processing_time_seconds = time.time() - start_time
            db.session.commit()
    
    def _is_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled."""
        if cache.enabled:
            cancel_key = f'analysis_jobs:cancel:{job_id}'
            return cache.redis_client.exists(cancel_key)
        return False
    
    def _cancel_job(self, job: AnalysisJob) -> None:
        """Mark a job as cancelled."""
        job.status = 'cancelled'
        job.error_message = 'Job cancelled by user'
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        logger.info(f"Job {job.job_id} cancelled")
    
    def get_next_job(self) -> Optional[AnalysisJob]:
        """Get the next queued job from database or Redis."""
        # Try Redis queue first if available
        if cache.enabled:
            job_id = cache.redis_client.rpop('analysis_jobs:queue')
            if job_id:
                job_id = job_id.decode('utf-8') if isinstance(job_id, bytes) else job_id
                job = AnalysisJob.query.filter_by(job_id=job_id, status='queued').first()
                if job:
                    return job
        
        # Fall back to database query
        return AnalysisJob.query.filter_by(status='queued').order_by(
            AnalysisJob.created_at.asc()
        ).first()
    
    def run(self):
        """Main worker loop."""
        logger.info("Analysis worker started")
        
        with self.app.app_context():
            while self.running:
                try:
                    # Get next job
                    job = self.get_next_job()
                    
                    if job:
                        self.process_job(job)
                    else:
                        # No jobs available, wait before checking again
                        time.sleep(5)
                        
                except KeyboardInterrupt:
                    logger.info("Worker interrupted by user")
                    self.running = False
                except Exception as e:
                    logger.error(f"Worker error: {str(e)}")
                    time.sleep(10)  # Wait before retrying
        
        logger.info("Analysis worker stopped")


def main():
    """Main entry point for the worker."""
    # Create Flask app
    app = create_app()
    
    # Create and run worker
    worker = AnalysisWorker(app)
    
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("Shutting down worker...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()