"""
Unit tests for database models.
"""
import pytest
from datetime import datetime, timedelta, timezone
from app import db
from app.models import User, Channel, Video, UserChannel, SentimentFeedback


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self, app):
        """Test creating a new user."""
        user = User(
            name='John Doe',
            email='john@example.com',
            is_subscribed=False
        )
        user.set_password('password123')
        
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.name == 'John Doe'
        assert user.email == 'john@example.com'
        assert user.is_subscribed is False
        assert user.password_hash is not None
        assert user.password_hash != 'password123'  # Should be hashed
    
    def test_password_hashing(self, app):
        """Test password hashing and verification."""
        user = User(name='Test', email='test@test.com')
        user.set_password('mypassword')
        
        assert user.password_hash is not None
        assert user.check_password('mypassword') is True
        assert user.check_password('wrongpassword') is False
    
    def test_reset_password_token(self, app):
        """Test password reset token generation and verification."""
        user = User(name='Test', email='test@test.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = user.get_reset_password_token(expires_in=3600)
        assert token is not None
        assert len(token) == 64
        assert user.reset_token == token
        assert user.reset_token_expires is not None
        
        # Verify valid token
        verified_user = User.verify_reset_password_token(token)
        assert verified_user is not None
        assert verified_user.id == user.id
        
        # Test expired token
        user.reset_token_expires = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        db.session.commit()
        
        verified_user = User.verify_reset_password_token(token)
        assert verified_user is None
        
        # Test invalid token
        verified_user = User.verify_reset_password_token('invalid_token')
        assert verified_user is None
    
    def test_clear_reset_token(self, app):
        """Test clearing reset token."""
        user = User(name='Test', email='test@test.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        token = user.get_reset_password_token()
        assert user.reset_token is not None
        
        user.clear_reset_token()
        assert user.reset_token is None
        assert user.reset_token_expires is None
    
    def test_user_subscription_status(self, app):
        """Test user subscription fields."""
        user = User(
            name='Premium User',
            email='premium@example.com',
            is_subscribed=True,
            provider='stripe',
            customer_id='cus_123456'
        )
        user.set_password('test_password')  # Add password
        db.session.add(user)
        db.session.commit()
        
        assert user.is_subscribed is True
        assert user.provider == 'stripe'
        assert user.customer_id == 'cus_123456'
    
    def test_user_timestamps(self, app):
        """Test user timestamp fields."""
        user = User(name='Test', email='test@test.com')
        user.set_password('test_password')  # Add password
        db.session.add(user)
        db.session.commit()
        
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)


class TestChannelModel:
    """Test Channel model functionality."""
    
    def test_channel_creation(self, app):
        """Test creating a new channel."""
        channel = Channel(
            yt_channel_id='UC_abc123',
            title='Test Channel',
            handle='@testchannel',
            uploads_playlist_id='UU_abc123',
            video_count=100,
            last_synced_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.session.add(channel)
        db.session.commit()
        
        assert channel.id is not None
        assert channel.yt_channel_id == 'UC_abc123'
        assert channel.title == 'Test Channel'
        assert channel.handle == '@testchannel'
        assert channel.video_count == 100
    
    def test_channel_unique_constraint(self, app):
        """Test channel YouTube ID uniqueness."""
        channel1 = Channel(
            yt_channel_id='UC_unique',
            title='Channel 1'
        )
        channel2 = Channel(
            yt_channel_id='UC_unique',
            title='Channel 2'
        )
        
        db.session.add(channel1)
        db.session.commit()
        
        db.session.add(channel2)
        with pytest.raises(Exception):  # Should raise integrity error
            db.session.commit()
    
    def test_channel_timestamps(self, app):
        """Test channel timestamp fields."""
        channel = Channel(
            yt_channel_id='UC_test',
            title='Test'
        )
        db.session.add(channel)
        db.session.commit()
        
        assert channel.created_at is not None
        assert channel.updated_at is not None
        
        # Test last_checked_at
        channel.last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        assert channel.last_checked_at is not None


class TestVideoModel:
    """Test Video model functionality."""
    
    def test_video_creation(self, app, test_channel):
        """Test creating a new video."""
        video = Video(
            yt_video_id='vid_123',
            channel_id=test_channel.id,
            title='Test Video',
            published_at=datetime.now(timezone.utc).replace(tzinfo=None),
            views=1000,
            likes=100,
            comments=50
        )
        db.session.add(video)
        db.session.commit()
        
        assert video.id is not None
        assert video.yt_video_id == 'vid_123'
        assert video.channel_id == test_channel.id
        assert video.views == 1000
        assert video.likes == 100
        assert video.comments == 50
    
    def test_video_channel_relationship(self, app, test_channel):
        """Test video-channel foreign key relationship."""
        video = Video(
            yt_video_id='vid_456',
            channel_id=test_channel.id,
            title='Related Video'
        )
        db.session.add(video)
        db.session.commit()
        
        # Query video and check relationship
        queried_video = Video.query.filter_by(yt_video_id='vid_456').first()
        assert queried_video.channel_id == test_channel.id
    
    def test_video_unique_constraint(self, app, test_channel):
        """Test video YouTube ID uniqueness."""
        video1 = Video(
            yt_video_id='vid_unique',
            channel_id=test_channel.id,
            title='Video 1'
        )
        video2 = Video(
            yt_video_id='vid_unique',
            channel_id=test_channel.id,
            title='Video 2'
        )
        
        db.session.add(video1)
        db.session.commit()
        
        db.session.add(video2)
        with pytest.raises(Exception):  # Should raise integrity error
            db.session.commit()


class TestUserChannelModel:
    """Test UserChannel association model."""
    
    def test_user_channel_association(self, app, test_user, test_channel):
        """Test creating user-channel association."""
        user_channel = UserChannel(
            user_id=test_user.id,
            channel_id=test_channel.id
        )
        db.session.add(user_channel)
        db.session.commit()
        
        assert user_channel.id is not None
        assert user_channel.user_id == test_user.id
        assert user_channel.channel_id == test_channel.id
        assert user_channel.created_at is not None
    
    def test_user_channel_unique_constraint(self, app, test_user, test_channel):
        """Test unique constraint on user-channel pairs."""
        uc1 = UserChannel(
            user_id=test_user.id,
            channel_id=test_channel.id
        )
        uc2 = UserChannel(
            user_id=test_user.id,
            channel_id=test_channel.id
        )
        
        db.session.add(uc1)
        db.session.commit()
        
        db.session.add(uc2)
        with pytest.raises(Exception):  # Should raise integrity error
            db.session.commit()
    
    def test_multiple_channels_per_user(self, app, test_user):
        """Test user can have multiple channels."""
        channel1 = Channel(yt_channel_id='UC_1', title='Channel 1')
        channel2 = Channel(yt_channel_id='UC_2', title='Channel 2')
        db.session.add_all([channel1, channel2])
        db.session.commit()
        
        uc1 = UserChannel(user_id=test_user.id, channel_id=channel1.id)
        uc2 = UserChannel(user_id=test_user.id, channel_id=channel2.id)
        db.session.add_all([uc1, uc2])
        db.session.commit()
        
        user_channels = UserChannel.query.filter_by(user_id=test_user.id).all()
        assert len(user_channels) == 2


class TestSentimentFeedbackModel:
    """Test SentimentFeedback model functionality."""
    
    def test_feedback_creation(self, app, test_user):
        """Test creating sentiment feedback."""
        feedback = SentimentFeedback(
            user_id=test_user.id,
            video_id='vid_789',
            comment_id='comment_123',
            comment_text='Great video!',
            comment_author='John',
            predicted_sentiment='positive',
            corrected_sentiment='neutral',
            confidence_score=0.85,
            session_id='session_123',
            ip_hash='hash_123'
        )
        db.session.add(feedback)
        db.session.commit()
        
        assert feedback.id is not None
        assert feedback.user_id == test_user.id
        assert feedback.predicted_sentiment == 'positive'
        assert feedback.corrected_sentiment == 'neutral'
        assert feedback.confidence_score == 0.85
        assert feedback.used_for_training is False
    
    def test_anonymous_feedback(self, app):
        """Test feedback without user (anonymous)."""
        feedback = SentimentFeedback(
            user_id=None,  # Anonymous
            video_id='vid_anon',
            comment_text='Anonymous comment',
            predicted_sentiment='negative',
            corrected_sentiment='positive',
            session_id='anon_session'
        )
        db.session.add(feedback)
        db.session.commit()
        
        assert feedback.id is not None
        assert feedback.user_id is None
    
    def test_feedback_training_status(self, app, test_user):
        """Test feedback training status fields."""
        feedback = SentimentFeedback(
            user_id=test_user.id,
            video_id='vid_train',
            comment_text='Training comment',
            predicted_sentiment='positive',
            corrected_sentiment='positive',
            used_for_training=True,
            training_batch='batch_001'
        )
        db.session.add(feedback)
        db.session.commit()
        
        assert feedback.used_for_training is True
        assert feedback.training_batch == 'batch_001'
    
    def test_feedback_unique_constraints(self, app, test_user):
        """Test unique constraints for feedback."""
        # Test user-video-comment uniqueness
        feedback1 = SentimentFeedback(
            user_id=test_user.id,
            video_id='vid_unique',
            comment_text='Same comment',
            predicted_sentiment='positive',
            corrected_sentiment='negative'
        )
        feedback2 = SentimentFeedback(
            user_id=test_user.id,
            video_id='vid_unique',
            comment_text='Same comment',
            predicted_sentiment='negative',
            corrected_sentiment='positive'
        )
        
        db.session.add(feedback1)
        db.session.commit()
        
        db.session.add(feedback2)
        with pytest.raises(Exception):  # Should raise integrity error
            db.session.commit()
        
        db.session.rollback()
        
        # Test session-video-comment uniqueness
        feedback3 = SentimentFeedback(
            session_id='session_unique',
            video_id='vid_unique',
            comment_text='Session comment',
            predicted_sentiment='positive',
            corrected_sentiment='negative'
        )
        feedback4 = SentimentFeedback(
            session_id='session_unique',
            video_id='vid_unique',
            comment_text='Session comment',
            predicted_sentiment='negative',
            corrected_sentiment='positive'
        )
        
        db.session.add(feedback3)
        db.session.commit()
        
        db.session.add(feedback4)
        with pytest.raises(Exception):  # Should raise integrity error
            db.session.commit()
    
    def test_feedback_queries(self, app, test_user):
        """Test querying feedback for training."""
        # Create mix of used and unused feedback
        for i in range(5):
            feedback = SentimentFeedback(
                user_id=test_user.id if i % 2 == 0 else None,
                video_id=f'vid_{i}',
                comment_text=f'Comment {i}',
                predicted_sentiment='positive',
                corrected_sentiment='negative',
                used_for_training=(i < 3)
            )
            db.session.add(feedback)
        db.session.commit()
        
        # Query unused feedback
        unused = SentimentFeedback.query.filter_by(used_for_training=False).all()
        assert len(unused) == 2
        
        # Query by user
        user_feedback = SentimentFeedback.query.filter_by(user_id=test_user.id).all()
        assert len(user_feedback) == 3