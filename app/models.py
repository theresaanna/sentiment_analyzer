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

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def get_reset_password_token(self, expires_in=3600):
        """Generate a password reset token that expires in `expires_in` seconds (default: 60 minutes)."""
        import time
        # Use explicit UTC timestamp to avoid timezone issues
        payload = {
            'reset_password': self.id,
            'exp': int(time.time()) + expires_in,  # Use Unix timestamp for better reliability
            'iat': int(time.time())  # Add issued at time
        }
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    
    @staticmethod
    def verify_reset_password_token(token):
        """Verify a password reset token and return the user if valid."""
        import time
        
        try:
            current_app.logger.info(f'🔍 Verifying token: {token[:50]}...')
            
            # Try multiple verification approaches for maximum compatibility
            payload = None
            
            # Method 1: Standard JWT decode
            try:
                payload = jwt.decode(
                    token,
                    current_app.config['SECRET_KEY'],
                    algorithms=['HS256']
                )
                current_app.logger.info('✅ Standard JWT decode successful')
            except jwt.ExpiredSignatureError:
                # Method 2: Decode without verification to check if it's just expired
                try:
                    unverified_payload = jwt.decode(
                        token,
                        options={"verify_signature": False, "verify_exp": False}
                    )
                    exp_time = unverified_payload.get('exp', 0)
                    current_time = time.time()
                    
                    current_app.logger.warning(f'⏰ Token expired. Exp: {exp_time}, Now: {current_time}, Diff: {exp_time - current_time}')
                    
                    # Give a small grace period (5 minutes) for clock differences
                    if (exp_time - current_time) > -300:  # Less than 5 minutes expired
                        current_app.logger.info('🕐 Token recently expired, allowing with grace period')
                        payload = unverified_payload
                    else:
                        current_app.logger.warning('⏰ Token too old, rejecting')
                        return None
                        
                except Exception as e:
                    current_app.logger.error(f'❌ Failed to decode unverified token: {e}')
                    return None
            except Exception as e:
                current_app.logger.error(f'❌ JWT decode failed: {str(e)}')
                return None
            
            if not payload:
                return None
                
            user_id = payload.get('reset_password')
            if not user_id:
                current_app.logger.error('❌ No user_id in token payload')
                return None
                
            current_app.logger.info(f'✅ Token decoded successfully for user_id: {user_id}')
            
            user = User.query.get(user_id)
            if user:
                current_app.logger.info(f'✅ User found: {user.email}')
            else:
                current_app.logger.error(f'❌ No user found with ID: {user_id}')
            return user
            
        except Exception as e:
            current_app.logger.error(f'❌ Unexpected error verifying token: {str(e)}')
            return None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
