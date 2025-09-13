from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import current_app
import jwt
from app import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_subscribed = db.Column(db.Boolean, default=False)
    provider = db.Column(db.String(50))  # 'stripe' or 'paypal'
    customer_id = db.Column(db.String(255))  # Stripe customer ID or PayPal subscriber ID
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    # Database-based password reset fields
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def get_reset_password_token(self, expires_in=3600):
        """Generate a password reset token that expires in `expires_in` seconds (default: 60 minutes)."""
        import secrets
        import string
        
        # Generate a secure random token
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        # Store in database with expiration
        self.reset_token = token
        self.reset_token_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=expires_in)
        db.session.commit()
        
        current_app.logger.info(f'✅ Generated database reset token for {self.email}')
        return token
    
    @staticmethod
    def verify_reset_password_token(token):
        """Verify a password reset token and return the user if valid."""
        try:
            current_app.logger.info(f'🔍 Verifying database token: {token[:20]}...')
            
            # Look up user by token in database
            user = User.query.filter_by(reset_token=token).first()
            
            if not user:
                current_app.logger.warning('❌ No user found with this reset token')
                return None
            
            # Check if token has expired
            if user.reset_token_expires and user.reset_token_expires < datetime.now(timezone.utc).replace(tzinfo=None):
                current_app.logger.warning(f'⏰ Reset token expired for {user.email}')
                # Clear expired token
                user.reset_token = None
                user.reset_token_expires = None
                db.session.commit()
                return None
            
            current_app.logger.info(f'✅ Valid reset token found for {user.email}')
            return user
            
        except Exception as e:
            current_app.logger.error(f'❌ Error verifying reset token: {str(e)}')
            return None
    
    def clear_reset_token(self):
        """Clear the password reset token after use."""
        self.reset_token = None
        self.reset_token_expires = None
        db.session.commit()
        current_app.logger.info(f'✅ Cleared reset token for {self.email}')


class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    yt_channel_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    handle = db.Column(db.String(255), nullable=True, index=True)
    uploads_playlist_id = db.Column(db.String(255), nullable=True)
    latest_video_id = db.Column(db.String(64), nullable=True)
    video_count = db.Column(db.Integer, default=0)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    last_checked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    yt_video_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False)
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    comments = db.Column(db.Integer, default=0)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class UserChannel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'channel_id', name='uq_user_channel'),
    )


class SentimentFeedback(db.Model):
    """Store user feedback on sentiment predictions for model training."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  # Nullable for anonymous feedback
    video_id = db.Column(db.String(64), nullable=False, index=True)
    comment_id = db.Column(db.String(128), nullable=True, index=True)  # YouTube comment ID if available
    comment_text = db.Column(db.Text, nullable=False)  # Store the actual comment text
    comment_author = db.Column(db.String(255), nullable=True)  # Store author for context
    
    # Sentiment labels
    predicted_sentiment = db.Column(db.String(20), nullable=False)  # What our model predicted
    corrected_sentiment = db.Column(db.String(20), nullable=False)  # What the user says it should be
    confidence_score = db.Column(db.Float, nullable=True)  # Model's confidence in its prediction
    
    # Metadata
    session_id = db.Column(db.String(128), nullable=True)  # Track feedback within a session
    ip_hash = db.Column(db.String(64), nullable=True)  # Hashed IP for spam prevention
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
    
    # Training status
    used_for_training = db.Column(db.Boolean, default=False, index=True)  # Track if used in model retraining
    training_batch = db.Column(db.String(64), nullable=True)  # Batch ID when used for training
    
    __table_args__ = (
        # Prevent duplicate feedback for the same comment from the same user/session
        db.UniqueConstraint('user_id', 'video_id', 'comment_text', name='uq_user_comment_feedback'),
        db.UniqueConstraint('session_id', 'video_id', 'comment_text', name='uq_session_comment_feedback'),
        # Index for efficient training data queries
        db.Index('idx_training_queries', 'used_for_training', 'created_at'),
    )


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
