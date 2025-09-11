from datetime import datetime, timedelta
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
        self.reset_token_expires = datetime.utcnow() + timedelta(seconds=expires_in)
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
            if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
