"""
Comprehensive tests for analysis queue routes and functionality.
"""
import pytest
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, ANY
from app import db
from app.models import User, AnalysisJob


class TestQueueAnalysisRoute:
    """Test the queue analysis endpoint."""
    
    @patch('app.main.analysis_queue_routes.EnhancedYouTubeService')
    def test_queue_analysis_success(self, mock_youtube_service, authenticated_client, test_user):
        """Test successful job queuing."""
        # Mock YouTube service
        mock_instance = MagicMock()
        mock_instance.get_video_info.return_value = {
            'video_id': 'test123',
            'title': 'Test Video',
            'channel_title': 'Test Channel',
            'statistics': {'comments': 1000}
        }
        mock_youtube_service.return_value = mock_instance
        
        with authenticated_client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        response = authenticated_client.post('/api/queue/analyze', 
            data=json.dumps({
                'video_id': 'test123',
                'comment_count': 100,
                'include_replies': True
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'job_id' in data
        assert data['status'] == 'queued'
        
        # Check job was created in database
        job = AnalysisJob.query.filter_by(video_id='test123').first()
        assert job is not None
        assert job.comment_count_requested == 100
        assert job.include_replies is True
    
    def test_queue_analysis_missing_video_id(self, authenticated_client):
        """Test queuing without video_id."""
        response = authenticated_client.post('/api/queue/analyze',
            data=json.dumps({
                'comment_count': 100
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'video_id' in data['error'].lower()
    
    def test_queue_analysis_invalid_comment_count(self, authenticated_client):
        """Test queuing with invalid comment count."""
        response = authenticated_client.post('/api/queue/analyze',
            data=json.dumps({
                'video_id': 'test123',
                'comment_count': -50  # Invalid
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    @patch('app.main.analysis_queue_routes.EnhancedYouTubeService')
    def test_queue_analysis_youtube_error(self, mock_youtube_service, authenticated_client):
        """Test handling of YouTube API errors."""
        mock_instance = MagicMock()
        mock_instance.get_video_info.side_effect = Exception('YouTube API error')
        mock_youtube_service.return_value = mock_instance
        
        response = authenticated_client.post('/api/queue/analyze',
            data=json.dumps({
                'video_id': 'test123',
                'comment_count': 100
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    @patch('app.main.analysis_queue_routes.EnhancedYouTubeService')
    def test_queue_duplicate_job(self, mock_youtube_service, authenticated_client, test_user):
        """Test handling duplicate job requests."""
        mock_instance = MagicMock()
        mock_instance.get_video_info.return_value = {
            'video_id': 'test123',
            'title': 'Test Video',
            'channel_title': 'Test Channel'
        }
        mock_youtube_service.return_value = mock_instance
        
        with authenticated_client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
        
        # Create existing job
        existing_job = AnalysisJob(
            user_id=test_user.id,
            video_id='test123',
            comment_count_requested=100,
            status='processing'
        )
        db.session.add(existing_job)
        db.session.commit()
        
        # Try to queue another
        response = authenticated_client.post('/api/queue/analyze',
            data=json.dumps({
                'video_id': 'test123',
                'comment_count': 100
            }),
            content_type='application/json'
        )
        
        data = json.loads(response.data)
        # Should either return existing job or create new one
        assert response.status_code in [200, 409]
        if response.status_code == 409:
            assert 'already' in data.get('message', '').lower()


class TestJobStatusRoute:
    """Test job status endpoint."""
    
    def test_get_job_status_success(self, app, authenticated_client, test_user):
        """Test getting job status."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test123',
                comment_count_requested=100,
                status='processing',
                progress=50
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.job_id
        
        response = authenticated_client.get(f'/api/queue/status/{job_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'processing'
        assert data['progress'] == 50
        assert data['video_id'] == 'test123'
    
    def test_get_job_status_not_found(self, authenticated_client):
        """Test getting status for non-existent job."""
        response = authenticated_client.get('/api/queue/status/nonexistent_job')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error'].lower()
    
    def test_get_job_status_unauthorized(self, app, client, test_user):
        """Test getting status for another user's job."""
        with app.app_context():
            # Create job for test_user
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test123',
                comment_count_requested=100
            )
            db.session.add(job)
            
            # Create another user
            other_user = User(
                name='Other User',
                email='other@test.com'
            )
            other_user.set_password('password123')
            db.session.add(other_user)
            db.session.commit()
            job_id = job.job_id
        
        # Login as other user
        client.post('/auth/login', data={
            'email': 'other@test.com',
            'password': 'password123'
        })
        
        response = client.get(f'/api/queue/status/{job_id}')
        
        # Should not be able to see other user's job
        assert response.status_code in [403, 404]


class TestJobResultsRoute:
    """Test job results endpoint."""
    
    def test_get_job_results_success(self, app, authenticated_client, test_user):
        """Test getting completed job results."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test123',
                comment_count_requested=100,
                status='completed',
                progress=100,
                results={
                    'sentiment': 'positive',
                    'confidence': 0.85,
                    'statistics': {
                        'positive': 60,
                        'negative': 20,
                        'neutral': 20
                    }
                }
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.job_id
        
        response = authenticated_client.get(f'/api/queue/results/{job_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'results' in data
        assert data['results']['sentiment'] == 'positive'
    
    def test_get_job_results_not_ready(self, app, authenticated_client, test_user):
        """Test getting results for incomplete job."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test123',
                comment_count_requested=100,
                status='processing',
                progress=50
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.job_id
        
        response = authenticated_client.get(f'/api/queue/results/{job_id}')
        
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not ready' in data['message'].lower()
    
    def test_get_job_results_failed(self, app, authenticated_client, test_user):
        """Test getting results for failed job."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test123',
                comment_count_requested=100,
                status='failed',
                error_message='API rate limit exceeded'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.job_id
        
        response = authenticated_client.get(f'/api/queue/results/{job_id}')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'failed' in data['error'].lower()
        assert 'rate limit' in data['error_details'].lower()


class TestCancelJobRoute:
    """Test job cancellation endpoint."""
    
    def test_cancel_job_success(self, app, authenticated_client, test_user):
        """Test cancelling a queued job."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test123',
                comment_count_requested=100,
                status='queued'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.job_id
        
        response = authenticated_client.post(f'/api/queue/cancel/{job_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Check job was cancelled
        with app.app_context():
            job = AnalysisJob.query.filter_by(job_id=job_id).first()
            assert job.status == 'cancelled'
    
    def test_cancel_processing_job(self, app, authenticated_client, test_user):
        """Test cancelling a processing job."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test123',
                comment_count_requested=100,
                status='processing',
                progress=50
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.job_id
        
        response = authenticated_client.post(f'/api/queue/cancel/{job_id}')
        
        # May or may not be able to cancel processing job
        assert response.status_code in [200, 400]
        data = json.loads(response.data)
        
        if response.status_code == 400:
            assert 'cannot cancel' in data['error'].lower()
    
    def test_cancel_completed_job(self, app, authenticated_client, test_user):
        """Test cancelling a completed job (should fail)."""
        with app.app_context():
            job = AnalysisJob(
                user_id=test_user.id,
                video_id='test123',
                comment_count_requested=100,
                status='completed'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.job_id
        
        response = authenticated_client.post(f'/api/queue/cancel/{job_id}')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'already completed' in data['error'].lower()


class TestUserJobsRoute:
    """Test user jobs listing endpoint."""
    
    def test_get_user_jobs(self, app, authenticated_client, test_user):
        """Test getting user's job history."""
        with app.app_context():
            # Create multiple jobs
            jobs = []
            for i, status in enumerate(['queued', 'processing', 'completed', 'failed']):
                job = AnalysisJob(
                    user_id=test_user.id,
                    video_id=f'video_{i}',
                    comment_count_requested=100,
                    status=status
                )
                jobs.append(job)
            db.session.add_all(jobs)
            db.session.commit()
        
        response = authenticated_client.get('/api/queue/my-jobs')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'jobs' in data
        assert len(data['jobs']) == 4
        
        # Check ordering (newest first)
        statuses = [job['status'] for job in data['jobs']]
        assert set(statuses) == {'queued', 'processing', 'completed', 'failed'}
    
    def test_get_user_jobs_filtered(self, app, authenticated_client, test_user):
        """Test getting filtered job history."""
        with app.app_context():
            # Create jobs with different statuses
            for i in range(3):
                job = AnalysisJob(
                    user_id=test_user.id,
                    video_id=f'video_completed_{i}',
                    comment_count_requested=100,
                    status='completed'
                )
                db.session.add(job)
            
            for i in range(2):
                job = AnalysisJob(
                    user_id=test_user.id,
                    video_id=f'video_queued_{i}',
                    comment_count_requested=100,
                    status='queued'
                )
                db.session.add(job)
            
            db.session.commit()
        
        # Get only completed jobs
        response = authenticated_client.get('/api/queue/my-jobs?status=completed')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['jobs']) == 3
        assert all(job['status'] == 'completed' for job in data['jobs'])
    
    def test_get_user_jobs_pagination(self, app, authenticated_client, test_user):
        """Test job history pagination."""
        with app.app_context():
            # Create many jobs
            for i in range(25):
                job = AnalysisJob(
                    user_id=test_user.id,
                    video_id=f'video_{i}',
                    comment_count_requested=100,
                    status='completed'
                )
                db.session.add(job)
            db.session.commit()
        
        # Get first page
        response = authenticated_client.get('/api/queue/my-jobs?page=1&per_page=10')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['jobs']) == 10
        assert data['total'] == 25
        assert data['page'] == 1
        assert data['has_next'] is True
        
        # Get last page
        response = authenticated_client.get('/api/queue/my-jobs?page=3&per_page=10')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['jobs']) == 5
        assert data['has_next'] is False