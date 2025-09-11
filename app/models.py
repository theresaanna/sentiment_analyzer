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
        try:
            # Add debugging
            current_app.logger.info(f'🔍 Verifying token: {token[:50]}...')
            
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            user_id = payload['reset_password']
            current_app.logger.info(f'✅ Token decoded successfully for user_id: {user_id}')
            
            # Check expiration manually for debugging
            from datetime import datetime
            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
                now_utc = datetime.utcnow()
                current_app.logger.info(f'⏰ Token expires at: {exp_datetime} UTC')
                current_app.logger.info(f'⏰ Current time is: {now_utc} UTC')
                current_app.logger.info(f'⏰ Time remaining: {exp_datetime - now_utc}')
            
            user = User.query.get(user_id)
            if user:
                current_app.logger.info(f'✅ User found: {user.email}')
            else:
                current_app.logger.error(f'❌ No user found with ID: {user_id}')
            return user
            
        except jwt.ExpiredSignatureError as e:
            current_app.logger.warning(f'⏰ Token expired: {str(e)}')
            return None
        except jwt.InvalidTokenError as e:
            current_app.logger.error(f'❌ Invalid token: {str(e)}')
            return None
        except KeyError as e:
            current_app.logger.error(f'❌ Missing key in token payload: {str(e)}')
            return None
        except Exception as e:
            current_app.logger.error(f'❌ Unexpected error verifying token: {str(e)}')
            return None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
