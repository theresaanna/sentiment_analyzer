"""
Email utility module for sending emails including password reset emails.
"""
from flask import render_template, current_app
from flask_mail import Mail, Message
from threading import Thread

mail = Mail()


def send_async_email(app, msg):
    """Send email asynchronously in a background thread."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            # Log the error but don't raise it to prevent app crashes
            app.logger.error(f'Failed to send email: {str(e)}')


def send_email(subject, sender, recipients, text_body, html_body):
    """
    Send an email with the given subject and body to the specified recipients.
    
    Args:
        subject: Email subject
        sender: Sender email address
        recipients: List of recipient email addresses
        text_body: Plain text version of the email
        html_body: HTML version of the email
    """
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    
    # Send email asynchronously to avoid blocking the request
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()


def send_password_reset_email(user):
    """
    Send a password reset email to the user.
    
    Args:
        user: User model instance
    """
    token = user.get_reset_password_token()
    send_email(
        subject='[Sentiment Analyzer] Reset Your Password',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt',
                                   user=user, token=token),
        html_body=render_template('email/reset_password.html',
                                   user=user, token=token)
    )
