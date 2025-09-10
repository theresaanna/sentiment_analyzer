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
    
    def get_reset_password_token(self, expires_in=600):
        """Generate a password reset token that expires in `expires_in` seconds."""
        payload = {
            'reset_password': self.id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
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
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            user_id = payload['reset_password']
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
            return None
        return User.query.get(user_id)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
