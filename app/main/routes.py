"""
Routes for the main blueprint.
"""
from flask import render_template, flash, redirect, url_for, session
from app.main import bp
from app.main.forms import YouTubeURLForm
from app.utils.youtube import extract_video_id, build_youtube_url


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    """Homepage with YouTube URL submission form."""
    form = YouTubeURLForm()
    
    if form.validate_on_submit():
        url = form.url.data
        video_id = extract_video_id(url)
        
        if video_id:
            # Store video ID in session for now
            session['video_id'] = video_id
            session['video_url'] = build_youtube_url(video_id)
            
            flash(f'Video ID extracted: {video_id}', 'success')
            flash('API integration coming in next step!', 'info')
            
            # In future, redirect to analysis page
            return redirect(url_for('main.analyze', video_id=video_id))
        else:
            flash('Could not extract video ID from URL', 'danger')
    
    return render_template('index.html', form=form)


@bp.route('/analyze/<video_id>')
def analyze(video_id):
    """Analyze comments for a given video ID."""
    # Placeholder for now - will implement API calls here
    video_url = build_youtube_url(video_id)
    
    return render_template(
        'analyze.html',
        video_id=video_id,
        video_url=video_url,
        message="YouTube API integration will be added in the next step!"
    )


@bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')
