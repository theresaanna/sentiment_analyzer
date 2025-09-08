"""
YouTube utility functions for extracting video information.
"""
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from various YouTube URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    
    Args:
        url: YouTube URL string
        
    Returns:
        Video ID string if found, None otherwise
    """
    if not url:
        return None
    
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Handle youtu.be short URLs
    if 'youtu.be' in parsed_url.netloc:
        # Video ID is in the path
        video_id = parsed_url.path.lstrip('/')
        if video_id:
            return video_id.split('?')[0]  # Remove any query parameters
    
    # Handle standard youtube.com URLs
    elif 'youtube.com' in parsed_url.netloc or 'm.youtube.com' in parsed_url.netloc:
        # Check for /watch path with v parameter
        if '/watch' in parsed_url.path:
            query_params = parse_qs(parsed_url.query)
            if 'v' in query_params:
                return query_params['v'][0]
        
        # Check for /embed/ or /v/ paths
        elif '/embed/' in parsed_url.path or '/v/' in parsed_url.path:
            # Extract ID from path
            pattern = r'(?:/embed/|/v/)([^/?&]+)'
            match = re.search(pattern, url)
            if match:
                return match.group(1)
    
    # Try regex as fallback for edge cases
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&\?\/]+)',
        r'youtube\.com\/watch\?.*&v=([^&]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def validate_video_id(video_id: str) -> bool:
    """
    Validate YouTube video ID format.
    
    YouTube video IDs are typically 11 characters long and contain
    alphanumeric characters, hyphens, and underscores.
    
    Args:
        video_id: Video ID string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not video_id:
        return False
    
    # YouTube video IDs are typically 11 characters
    # but can vary, so we check for reasonable length and characters
    pattern = r'^[a-zA-Z0-9_-]{10,12}$'
    return bool(re.match(pattern, video_id))


def build_youtube_url(video_id: str) -> str:
    """
    Build a standard YouTube URL from a video ID.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Full YouTube URL
    """
    return f'https://www.youtube.com/watch?v={video_id}'
