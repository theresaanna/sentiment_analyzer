"""
Custom Jinja2 filters for the application.
"""
import re


def format_duration(duration_str):
    """
    Convert ISO 8601 duration format to human-readable format.
    
    Args:
        duration_str: Duration in ISO 8601 format (e.g., 'PT4M33S', 'PT1H2M10S')
        
    Returns:
        Human-readable duration string (e.g., '4:33', '1:02:10')
    """
    if not duration_str:
        return "Unknown"
    
    # Handle if it's already formatted
    if ':' in duration_str:
        return duration_str
    
    # Parse ISO 8601 duration format (PT#H#M#S)
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    
    if not match:
        return duration_str  # Return as-is if not in expected format
    
    hours = match.group(1)
    minutes = match.group(2) or '0'
    seconds = match.group(3) or '0'
    
    # Format the output
    if hours:
        # Format: H:MM:SS
        return f"{hours}:{int(minutes):02d}:{int(seconds):02d}"
    else:
        # Format: M:SS
        return f"{int(minutes)}:{int(seconds):02d}"


def register_filters(app):
    """
    Register custom filters with the Flask app.
    
    Args:
        app: Flask application instance
    """
    app.jinja_env.filters['format_duration'] = format_duration
