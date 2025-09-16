"""
Comprehensive tests for AnalysisJob model and queue functionality.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from app import db
from app.models import User, AnalysisJob


class TestAnalysisJobModel:
    """Test AnalysisJob model functionality."""
    
    def test_job_creation(self, app, test_user):
        """Test creating a new analysis job."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video_123',
                video_title='Test Video',
                channel_name='Test Channel',
                comment_count_requested=100,
                include_replies=True
            )
            db.session.add(job)
            db.session.commit()
            
            assert job.id is not None
            assert job.job_id.startswith('job_')
            assert 'test_video_123' in job.job_id
            assert job.status == 'queued'
            assert job.progress == 0
            assert job.include_replies is True
            assert job.comment_count_processed == 0
    
    def test_job_id_generation(self, app, test_user):
        """Test automatic job_id generation."""
        with app.app_context():
            job1 = AnalysisJob(
                user_id=test_user.id,
                video_id='video_1',
                comment_count_requested=50
            )
            job2 = AnalysisJob(
                user_id=test_user.id,
                video_id='video_2',
                comment_count_requested=50
            )
            db.session.add_all([job1, job2])
            db.session.commit()
            
            assert job1.job_id != job2.job_id
            assert 'video_1' in job1.job_id
            assert 'video_2' in job2.job_id
    
    def test_job_status_transitions(self, app, test_user):
        """Test job status transitions."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video',
                comment_count_requested=100
            )
            db.session.add(job)
            db.session.commit()
            
            # Initial state
            assert job.status == 'queued'
            
            # Transition to processing
            job.status = 'processing'
            job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.progress = 25
            db.session.commit()
            assert job.status == 'processing'
            assert job.started_at is not None
            
            # Transition to completed
            job.status = 'completed'
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.progress = 100
            job.comment_count_processed = 95
            job.processing_time_seconds = 12.5
            job.results = {'sentiment': 'positive', 'confidence': 0.85}
            db.session.commit()
            
            assert job.status == 'completed'
            assert job.completed_at is not None
            assert job.results is not None
    
    def test_job_failure_handling(self, app, test_user):
        """Test job failure states."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video',
                comment_count_requested=100
            )
            db.session.add(job)
            db.session.commit()
            
            # Mark as failed
            job.status = 'failed'
            job.error_message = 'API rate limit exceeded'
            db.session.commit()
            
            assert job.status == 'failed'
            assert 'rate limit' in job.error_message
            assert job.completed_at is None
    
    def test_job_to_dict(self, app, test_user):
        """Test job serialization to dictionary."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video',
                video_title='Test Video Title',
                channel_name='Test Channel',
                comment_count_requested=100,
                include_replies=False
            )
            db.session.add(job)
            db.session.commit()
            
            job_dict = job.to_dict()
            
            assert job_dict['job_id'] == job.job_id
            assert job_dict['video_id'] == 'test_video'
            assert job_dict['video_title'] == 'Test Video Title'
            assert job_dict['channel_name'] == 'Test Channel'
            assert job_dict['comment_count_requested'] == 100
            assert job_dict['include_replies'] is False
            assert job_dict['status'] == 'queued'
            assert job_dict['progress'] == 0
            assert job_dict['has_results'] is False
    
    def test_queue_position_calculation(self, app, test_user):
        """Test queue position calculation for queued jobs."""
        with app.app_context():
            # Create multiple queued jobs
            earlier_job = AnalysisJob(
                user_id=test_user.id,
                video_id='video_1',
                comment_count_requested=50
            )
            db.session.add(earlier_job)
            db.session.commit()
            
            # Add a small delay to ensure different timestamps
            import time
            time.sleep(0.1)
            
            later_job = AnalysisJob(
                user_id=test_user.id,
                video_id='video_2',
                comment_count_requested=50
            )
            db.session.add(later_job)
            db.session.commit()
            
            # Check queue positions
            earlier_dict = earlier_job.to_dict()
            later_dict = later_job.to_dict()
            
            assert earlier_dict['queue_position'] == 1
            assert later_dict['queue_position'] == 2
    
    def test_estimated_time_calculations(self, app, test_user):
        """Test estimated processing time calculations."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video',
                comment_count_requested=1000,  # Large job
                status='queued'
            )
            db.session.add(job)
            db.session.commit()
            
            job_dict = job.to_dict()
            
            # Should have time estimates
            assert job_dict['estimated_processing_time'] is not None
            assert job_dict['estimated_processing_time'] > 0
            
            # For 1000 comments, expect ~15 seconds (1.5s per 100)
            assert job_dict['estimated_processing_time'] >= 10
            assert job_dict['estimated_processing_time'] <= 20
    
    def test_processing_job_progress(self, app, test_user):
        """Test progress tracking for processing jobs."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video',
                comment_count_requested=200,
                status='processing',
                started_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5),
                progress=50  # 50% complete
            )
            db.session.add(job)
            db.session.commit()
            
            job_dict = job.to_dict()
            
            # Should estimate remaining time based on progress
            assert job_dict['estimated_processing_time'] is not None
            # Should be roughly 5 more seconds if 50% took 5 seconds
            assert 3 <= job_dict['estimated_processing_time'] <= 10


class TestAnalysisJobRelationships:
    """Test relationships between AnalysisJob and other models."""
    
    def test_user_relationship(self, app, test_user):
        """Test user-job relationship."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video',
                comment_count_requested=50
            )
            db.session.add(job)
            db.session.commit()
            
            # Check relationship
            assert job.user.id == test_user.id
            assert job.id in [j.id for j in test_user.analysis_jobs.all()]
    
    def test_multiple_jobs_per_user(self, app, test_user):
        """Test user can have multiple jobs."""
        with app.app_context():
            jobs = []
            for i in range(3):
                job = AnalysisJob(
                    user_id=test_user.id,
                    video_id=f'video_{i}',
                    comment_count_requested=50
                )
                jobs.append(job)
            
            db.session.add_all(jobs)
            db.session.commit()
            
            assert test_user.analysis_jobs.count() == 3
            
            # Check filtering
            queued_jobs = test_user.analysis_jobs.filter_by(status='queued').all()
            assert len(queued_jobs) == 3


class TestAnalysisJobConstraints:
    """Test database constraints and validation."""
    
    def test_unique_job_id(self, app, test_user):
        """Test job_id uniqueness constraint."""
        with app.app_context():
            job1 = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video',
                comment_count_requested=50,
                job_id='unique_job_123'
            )
            db.session.add(job1)
            db.session.commit()
            
            # Try to create duplicate
            job2 = AnalysisJob(
                user_id=test_user.id,
                video_id='test_video',
                comment_count_requested=50,
                job_id='unique_job_123'  # Same job_id
            )
            db.session.add(job2)
            
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()
    
    def test_required_fields(self, app):
        """Test required field validation."""
        with app.app_context():
            # Missing user_id
            job = AnalysisJob(
                video_id='test_video',
                comment_count_requested=50
            )
            db.session.add(job)
            
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()
    
    def test_status_values(self, app, test_user):
        """Test valid status values."""
        with app.app_context():
            valid_statuses = ['queued', 'processing', 'completed', 'failed', 'cancelled']
            
            for status in valid_statuses:
                job = AnalysisJob(
                    user_id=test_user.id,
                    video_id=f'video_{status}',
                    comment_count_requested=50,
                    status=status
                )
                db.session.add(job)
            
            db.session.commit()
            
            # All should be saved successfully
            jobs = AnalysisJob.query.filter_by(user_id=test_user.id).all()
            assert len(jobs) == len(valid_statuses)
            assert set(j.status for j in jobs) == set(valid_statuses)


class TestAnalysisJobQueries:
    """Test common query patterns for AnalysisJob."""
    
    def test_find_queued_jobs(self, app, test_user):
        """Test finding queued jobs."""
        with app.app_context():
            # Create mix of job statuses
            queued_job = AnalysisJob(
                user_id=test_user.id,
                video_id='queued_video',
                comment_count_requested=50,
                status='queued'
            )
            processing_job = AnalysisJob(
                user_id=test_user.id,
                video_id='processing_video',
                comment_count_requested=50,
                status='processing'
            )
            completed_job = AnalysisJob(
                user_id=test_user.id,
                video_id='completed_video',
                comment_count_requested=50,
                status='completed'
            )
            
            db.session.add_all([queued_job, processing_job, completed_job])
            db.session.commit()
            
            # Query queued jobs
            queued = AnalysisJob.query.filter_by(status='queued').all()
            assert len(queued) == 1
            assert queued[0].video_id == 'queued_video'
    
    def test_find_jobs_by_video(self, app, test_user):
        """Test finding jobs for a specific video."""
        with app.app_context():
            # Create multiple jobs for same video
            job1 = AnalysisJob(
                user_id=test_user.id,
                video_id='popular_video',
                comment_count_requested=50
            )
            job2 = AnalysisJob(
                user_id=test_user.id,
                video_id='popular_video',
                comment_count_requested=100
            )
            job3 = AnalysisJob(
                user_id=test_user.id,
                video_id='other_video',
                comment_count_requested=50
            )
            
            db.session.add_all([job1, job2, job3])
            db.session.commit()
            
            # Query by video_id
            video_jobs = AnalysisJob.query.filter_by(video_id='popular_video').all()
            assert len(video_jobs) == 2
    
    def test_find_recent_completed_jobs(self, app, test_user):
        """Test finding recently completed jobs."""
        with app.app_context():
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Create jobs with different completion times
            old_job = AnalysisJob(
                user_id=test_user.id,
                video_id='old_video',
                comment_count_requested=50,
                status='completed',
                completed_at=now - timedelta(days=7),
                processing_time_seconds=10.5
            )
            recent_job = AnalysisJob(
                user_id=test_user.id,
                video_id='recent_video',
                comment_count_requested=50,
                status='completed',
                completed_at=now - timedelta(hours=1),
                processing_time_seconds=8.2
            )
            pending_job = AnalysisJob(
                user_id=test_user.id,
                video_id='pending_video',
                comment_count_requested=50,
                status='queued'
            )
            
            db.session.add_all([old_job, recent_job, pending_job])
            db.session.commit()
            
            # Query recent completed jobs
            recent_completed = AnalysisJob.query.filter(
                AnalysisJob.status == 'completed',
                AnalysisJob.processing_time_seconds.isnot(None)
            ).order_by(AnalysisJob.completed_at.desc()).limit(5).all()
            
            assert len(recent_completed) == 2
            assert recent_completed[0].video_id == 'recent_video'
            assert recent_completed[1].video_id == 'old_video'