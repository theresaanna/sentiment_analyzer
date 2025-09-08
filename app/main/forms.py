"""
Forms for the sentiment analyzer application.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, ValidationError
from app.utils.youtube import extract_video_id


class YouTubeURLForm(FlaskForm):
    """Form for submitting YouTube URLs."""
    url = StringField(
        'YouTube URL',
        validators=[DataRequired(), URL()],
        render_kw={
            'placeholder': 'https://www.youtube.com/watch?v=VIDEO_ID',
            'class': 'form-control',
            'autofocus': True
        }
    )
    submit = SubmitField('Analyze Comments', render_kw={'class': 'btn btn-primary'})
    
    def validate_url(self, field):
        """Validate that the URL is a valid YouTube URL."""
        if not field.data:
            return
            
        # Check if it's a YouTube URL
        valid_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
        if not any(domain in field.data.lower() for domain in valid_domains):
            raise ValidationError('Please enter a valid YouTube URL.')
        
        # Try to extract video ID
        video_id = extract_video_id(field.data)
        if not video_id:
            raise ValidationError('Could not extract video ID from the provided URL.')
