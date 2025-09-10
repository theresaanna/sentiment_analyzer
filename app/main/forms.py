"""
Forms for the sentiment analyzer application.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField, BooleanField
from wtforms.validators import DataRequired, URL, ValidationError, Optional, NumberRange
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


class EnhancedYouTubeURLForm(FlaskForm):
    """Enhanced form with additional options for comment fetching and analysis."""
    url = StringField(
        'YouTube URL',
        validators=[DataRequired(), URL()],
        render_kw={
            'placeholder': 'https://www.youtube.com/watch?v=VIDEO_ID',
            'class': 'form-control',
            'autofocus': True
        }
    )
    
    max_comments = IntegerField(
        'Maximum Comments',
        validators=[
            Optional(),
            NumberRange(min=10, max=50000, message='Must be between 10 and 50,000')
        ],
        default=1000,
        render_kw={
            'class': 'form-control',
            'placeholder': '1000',
            'min': '10',
            'max': '50000'
        }
    )
    
    sort_order = SelectField(
        'Sort Comments By',
        choices=[
            ('relevance', 'Relevance (Most relevant first)'),
            ('time', 'Time (Newest first)')
        ],
        default='relevance',
        render_kw={'class': 'form-select'}
    )
    
    include_replies = BooleanField(
        'Include Replies',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    use_cache = BooleanField(
        'Use Cached Data (if available)',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    submit = SubmitField(
        'Analyze Comments',
        render_kw={'class': 'btn btn-primary btn-lg'}
    )
    
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
