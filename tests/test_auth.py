"""
Unit tests for authentication functionality.
"""
import pytest
from flask import url_for
from unittest.mock import patch, MagicMock
from app import db
from app.models import User
from app.auth.forms import LoginForm, RegisterForm, PasswordResetRequestForm, PasswordResetForm


class TestAuthForms:
    """Test authentication forms."""
    
    def test_login_form_validation(self, app):
        """Test login form validation."""
        with app.test_request_context():
            # Valid form
            form = LoginForm(data={
                'email': 'test@example.com',
                'password': 'password123',
                'remember_me': True
            })
            assert form.validate() is True
            
            # Invalid email
            form = LoginForm(data={
                'email': 'invalid-email',
                'password': 'password123'
            })
            assert form.validate() is False
            
            # Missing password
            form = LoginForm(data={
                'email': 'test@example.com'
            })
            assert form.validate() is False
    
    def test_registration_form_validation(self, app):
        """Test registration form validation."""
        with app.test_request_context():
            # Valid form
            form = RegisterForm(data={
                'name': 'John Doe',
                'email': 'john@example.com',
                'password': 'SecurePass123!',
                'confirm_password': 'SecurePass123!'
            })
            assert form.validate() is True
            
            # Password mismatch
            form = RegisterForm(data={
                'name': 'John Doe',
                'email': 'john@example.com',
                'password': 'SecurePass123!',
                'confirm_password': 'DifferentPass123!'
            })
            assert form.validate() is False
            
            # Invalid email
            form = RegisterForm(data={
                'name': 'John Doe',
                'email': 'not-an-email',
                'password': 'SecurePass123!',
                'confirm_password': 'SecurePass123!'
            })
            assert form.validate() is False
    
    def test_reset_password_request_form(self, app):
        """Test password reset request form."""
        with app.test_request_context():
            # Valid form
            form = PasswordResetRequestForm(data={
                'email': 'test@example.com'
            })
            assert form.validate() is True
            
            # Invalid email
            form = PasswordResetRequestForm(data={
                'email': 'invalid-email'
            })
            assert form.validate() is False
    
    def test_reset_password_form(self, app):
        """Test password reset form."""
        with app.test_request_context():
            # Valid form
            form = PasswordResetForm(data={
                'password': 'NewSecurePass123!',
                'confirm_password': 'NewSecurePass123!'
            })
            assert form.validate() is True
            
            # Password mismatch
            form = PasswordResetForm(data={
                'password': 'NewSecurePass123!',
                'confirm_password': 'DifferentPass123!'
            })
            assert form.validate() is False


class TestAuthRoutes:
    """Test authentication routes."""
    
    def test_login_get(self, client):
        """Test GET request to login page redirects to Google OAuth."""
        response = client.get('/auth/login')
        assert response.status_code == 302  # Redirect to Google OAuth
        assert 'accounts.google.com' in response.location or 'google' in response.location.lower()
    
    def test_login_post_success(self, client, test_user):
        """Test that login redirects to OAuth (no form-based login)."""
        # Since we're using OAuth, POST to login should also redirect
        response = client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'test_password'
        })
        
        # Should redirect to Google OAuth or show an error
        assert response.status_code in [302, 405]  # Redirect or Method Not Allowed
    
    def test_login_post_invalid_credentials(self, client, test_user):
        """Test that OAuth doesn't accept form credentials."""
        response = client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'wrong_password'
        })
        
        # Should redirect to OAuth or reject the POST
        assert response.status_code in [302, 405]
    
    def test_login_post_nonexistent_user(self, client):
        """Test that OAuth doesn't accept form credentials."""
        response = client.post('/auth/login', data={
            'email': 'nonexistent@example.com',
            'password': 'password123'
        })
        
        # Should redirect to OAuth or reject the POST
        assert response.status_code in [302, 405]
    
    def test_logout(self, authenticated_client):
        """Test logout functionality."""
        response = authenticated_client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Try to access protected route after logout
        response = authenticated_client.get('/dashboard')
        assert response.status_code in [302, 401]  # Redirect to login or unauthorized
    
    def test_register_get(self, client):
        """Test that registration redirects to login (OAuth only)."""
        response = client.get('/auth/register')
        # Registration is disabled, should redirect to login
        assert response.status_code == 404 or response.status_code == 302
    
    def test_register_post_success(self, client, mock_email):
        """Test that registration is disabled (OAuth only)."""
        response = client.post('/auth/register', data={
            'name': 'New User',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!'
        })
        
        # Registration should be disabled
        assert response.status_code in [404, 302, 405]
        
        # User should NOT be created via form registration
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is None
    
    def test_register_post_duplicate_email(self, client, test_user):
        """Test that registration is disabled (OAuth only)."""
        response = client.post('/auth/register', data={
            'name': 'Another User',
            'email': test_user.email,  # Existing email
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!'
        })
        
        # Registration should be disabled
        assert response.status_code in [404, 302, 405]
    
    def test_reset_password_request_get(self, client):
        """Test that password reset is disabled (OAuth only)."""
        response = client.get('/auth/reset_password_request')
        # Password reset should be disabled
        assert response.status_code in [404, 302]
    
    @patch('app.email.send_email')
    def test_reset_password_request_post(self, mock_send_email, client, test_user):
        """Test that password reset is disabled (OAuth only)."""
        mock_send_email.return_value = True
        
        response = client.post('/auth/reset_password_request', data={
            'email': test_user.email
        })
        
        # Password reset should be disabled
        assert response.status_code in [404, 302]
    
    def test_reset_password_request_nonexistent_email(self, client):
        """Test that password reset is disabled (OAuth only)."""
        response = client.post('/auth/reset_password_request', data={
            'email': 'nonexistent@example.com'
        })
        
        # Password reset should be disabled
        assert response.status_code in [404, 302]
    
    def test_reset_password_get_valid_token(self, client, test_user):
        """Test that password reset is disabled (OAuth only)."""
        token = test_user.get_reset_password_token()
        
        response = client.get(f'/auth/reset_password/{token}')
        # Password reset should be disabled
        assert response.status_code in [404, 302]
    
    def test_reset_password_get_invalid_token(self, client):
        """Test that password reset is disabled (OAuth only)."""
        response = client.get('/auth/reset_password/invalid_token_123')
        # Password reset should be disabled
        assert response.status_code in [404, 302]
    
    def test_reset_password_post_success(self, client, test_user):
        """Test that password reset is disabled (OAuth only)."""
        token = test_user.get_reset_password_token()
        
        response = client.post(f'/auth/reset_password/{token}', data={
            'password': 'NewSecurePass123!',
            'confirm_password': 'NewSecurePass123!'
        })
        
        # Password reset should be disabled
        assert response.status_code in [404, 302]
    
    def test_reset_password_post_expired_token(self, client, test_user):
        """Test that password reset is disabled (OAuth only)."""
        from datetime import datetime, timedelta, timezone
        
        token = test_user.get_reset_password_token()
        # Manually expire the token
        test_user.reset_token_expires = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        db.session.commit()
        
        response = client.post(f'/auth/reset_password/{token}', data={
            'password': 'NewSecurePass123!',
            'confirm_password': 'NewSecurePass123!'
        })
        
        # Password reset should be disabled
        assert response.status_code in [404, 302]


class TestAuthenticationFlow:
    """Test complete authentication flows."""
    
    def test_registration_to_login_flow(self, client, mock_email):
        """Test that OAuth is the only authentication method."""
        # Registration is disabled
        response = client.post('/auth/register', data={
            'name': 'Flow User',
            'email': 'flow@example.com',
            'password': 'FlowPass123!',
            'confirm_password': 'FlowPass123!'
        })
        assert response.status_code in [404, 302, 405]
        
        # Form login is disabled
        response = client.post('/auth/login', data={
            'email': 'flow@example.com',
            'password': 'FlowPass123!'
        })
        assert response.status_code in [302, 405]
        
        # Dashboard requires auth
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect to login
    
    def test_password_reset_flow(self, client, test_user, mock_email):
        """Test that password reset is disabled (OAuth only)."""
        # Request reset - should be disabled
        response = client.post('/auth/reset_password_request', data={
            'email': test_user.email
        })
        assert response.status_code in [404, 302]
        
        # Direct token access - should be disabled
        token = test_user.get_reset_password_token()
        response = client.post(f'/auth/reset_password/{token}', data={
            'password': 'ResetPass123!',
            'confirm_password': 'ResetPass123!'
        })
        assert response.status_code in [404, 302]
        
        # Form login - should redirect to OAuth
        response = client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'ResetPass123!'
        })
        assert response.status_code in [302, 405]
    
    def test_authenticated_redirect(self, authenticated_client):
        """Test that authenticated users are redirected from auth pages."""
        # Login page redirects to OAuth even for authenticated users
        response = authenticated_client.get('/auth/login')
        assert response.status_code in [302, 200]
        
        # Register page doesn't exist (OAuth only)
        response = authenticated_client.get('/auth/register')
        assert response.status_code in [404, 302]
    
    def test_remember_me_functionality(self, client, test_user):
        """Test that form login is disabled (OAuth only)."""
        # Login form is disabled
        response = client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'test_password',
            'remember_me': True
        })
        # Should redirect to OAuth
        assert response.status_code in [302, 405]
    
    def test_login_required_decorator(self, client):
        """Test that protected routes require authentication."""
        protected_routes = [
            '/dashboard',
            '/analyze',
            '/batch'
        ]
        
        for route in protected_routes:
            response = client.get(route)
            # Should redirect to login, return unauthorized, or not exist
            assert response.status_code in [302, 401, 404]
            
            if response.status_code == 302:
                assert '/auth/login' in response.location or 'login' in response.location or 'google' in response.location.lower()
