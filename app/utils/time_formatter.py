"""
Time formatting utilities for the sentiment analyzer application.
"""


def format_estimated_time(seconds: float) -> str:
    """
    Format estimated time in a human-readable format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string (e.g., "45s" or "2.5 minutes")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = seconds / 60
        if minutes < 2:
            return f"~{minutes:.1f} minute"
        else:
            return f"~{minutes:.1f} minutes"


def format_duration(seconds: float) -> str:
    """
    Format a duration in a more detailed human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "1h 23m 45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        if remaining_seconds < 1:
            return f"{minutes}m"
        return f"{minutes}m {remaining_seconds:.0f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        if remaining_minutes == 0:
            return f"{hours}h"
        return f"{hours}h {remaining_minutes}m"