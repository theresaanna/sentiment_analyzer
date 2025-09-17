"""
YouTube API Service Module
Handles all interactions with the YouTube Data API v3
"""
import os
import re
from typing import Dict, List, Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import urlparse, parse_qs
from app.cache import cache


class YouTubeService:
    """Service class for YouTube API operations"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the YouTube service with API key
        
        Args:
            api_key: YouTube Data API key (optional, will use env variable if not provided)
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key is required. Set YOUTUBE_API_KEY in .env file")
        
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.max_results_per_page = 100  # YouTube API maximum
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID if found, None otherwise
        """
        # Handle different YouTube URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&\n\?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n\?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, check if it's already a video ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
            
        return None
    
    def get_video_comments(self, video_id: str, max_results: Optional[int] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get video comments.

        Args:
            video_id: YouTube video ID
            max_results: Maximum number of comments to fetch.
            use_cache: Whether to use cache (default: True)

        Returns:
            List of video comments
        """
        try:
            return self.get_all_comments_flat(video_id, max_comments=max_results, use_cache=use_cache)
        except Exception as e:
            # Return empty list on error for backward compatibility
            print(f"Error fetching comments for video {video_id}: {e}")
            return []

    def get_channel_info(self, channel_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get basic channel information.

        Args:
            channel_id: YouTube channel ID
            use_cache: Whether to use cache (default: True)

        Returns:
            Dictionary containing channel metadata
        """
        if use_cache:
            cached_data = cache.get('channel_info', channel_id)
            if cached_data:
                print(f"Cache hit for channel info: {channel_id}")
                return cached_data
        try:
            request = self.youtube.channels().list(
                part='snippet,contentDetails,statistics',
                id=channel_id
            )
            response = request.execute()

            if not response.get('items'):
                raise ValueError(f"Channel with ID {channel_id} not found")

            channel = response['items'][0]
            channel_data = {
                'id': channel_id,
                'title': channel['snippet']['title'],
                'description': channel['snippet']['description'],
                'published_at': channel['snippet']['publishedAt'],
                'subscribers': int(channel['statistics'].get('subscriberCount', 0)),
                'views': int(channel['statistics'].get('viewCount', 0)),
                'video_count': int(channel['statistics'].get('videoCount', 0)),
                'uploads_playlist_id': channel['contentDetails']['relatedPlaylists']['uploads'],
                'thumbnail': channel['snippet']['thumbnails'].get('high', {}).get('url')
            }
            if use_cache:
                cache.set('channel_info', channel_id, channel_data, ttl_hours=24)
                print(f"Cached channel info for: {channel_id}")
            return channel_data
        except HttpError as e:
            if e.resp.status == 403:
                raise ValueError("API quota exceeded or invalid API key")
            raise

    def get_video_info(self, video_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get basic video information
        
        Args:
            video_id: YouTube video ID
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Dictionary containing video metadata
        """
        # Try to get from cache first
        if use_cache:
            cached_data = cache.get('video_info', video_id)
            if cached_data:
                print(f"Cache hit for video info: {video_id}")
                return cached_data
        
        try:
            request = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                raise ValueError(f"Video with ID {video_id} not found")
            
            video = response['items'][0]
            video_data = {
                'id': video_id,
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'channel': video['snippet']['channelTitle'],
                'published_at': video['snippet']['publishedAt'],
                'duration': video['contentDetails']['duration'],
                'statistics': {
                    'views': int(video['statistics'].get('viewCount', 0)),
                    'likes': int(video['statistics'].get('likeCount', 0)),
                    'comments': int(video['statistics'].get('commentCount', 0))
                },
                'thumbnail': video['snippet']['thumbnails'].get('high', {}).get('url')
            }
            
            # Cache the result for 24 hours
            if use_cache:
                cache.set('video_info', video_id, video_data, ttl_hours=24)
                print(f"Cached video info for: {video_id}")
            
            return video_data
        except HttpError as e:
            if e.resp.status == 403:
                raise ValueError("API quota exceeded or invalid API key")
            raise
    
    def get_comment_threads(self, video_id: str, max_comments: Optional[int] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get all comment threads for a video, including replies
        
        Args:
            video_id: YouTube video ID
            max_comments: Maximum number of top-level comments to fetch (None for all)
            use_cache: Whether to use cache (default: True)
            
        Returns:
            List of comment threads with replies
        """
        # Create a cache key that includes the max_comments parameter
        cache_key = f"{video_id}:{max_comments or 'all'}"
        
        # Try to get from cache first
        if use_cache:
            cached_data = cache.get('comments_threaded', cache_key)
            if cached_data:
                print(f"Cache hit for comment threads: {video_id} (max: {max_comments})")
                return cached_data
        
        comment_threads = []
        next_page_token = None
        comments_fetched = 0
        
        try:
            while True:
                # Prepare request for comment threads
                request = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=min(self.max_results_per_page, 
                                 max_comments - comments_fetched if max_comments else self.max_results_per_page),
                    pageToken=next_page_token,
                    textFormat='plainText',
                    order='relevance'  # Can be changed to 'time' for chronological order
                )
                
                response = request.execute()
                
                # Process each comment thread
                for item in response.get('items', []):
                    thread = self._process_comment_thread(item)
                    comment_threads.append(thread)
                    comments_fetched += 1
                    
                    if max_comments and comments_fetched >= max_comments:
                        break
                
                # Check for next page
                next_page_token = response.get('nextPageToken')
                
                # Break if we've reached the limit or no more pages
                if not next_page_token or (max_comments and comments_fetched >= max_comments):
                    break
            
            # Cache the result for 6 hours
            if use_cache:
                cache.set('comments_threaded', cache_key, comment_threads, ttl_hours=6)
                print(f"Cached {len(comment_threads)} comment threads for: {video_id}")
                    
            return comment_threads
            
        except HttpError as e:
            # Log detailed error information for debugging
            print(f"YouTube API HttpError for video {video_id}:")
            print(f"  Status: {e.resp.status}")
            print(f"  Reason: {e.resp.reason}")
            print(f"  Error content: {e.content.decode('utf-8') if e.content else 'No content'}")
            print(f"  Request URI: {request.uri if 'request' in locals() else 'Unknown'}")
            
            # More detailed error handling
            error_msg = str(e)
            status = e.resp.status
            
            if status == 403:
                if 'commentsDisabled' in error_msg or 'disabled comments' in error_msg:
                    raise ValueError("Comments are disabled for this video")
                elif 'quota' in error_msg.lower():
                    raise ValueError("YouTube API quota exceeded")
                elif 'processingFailure' in error_msg:
                    # This is the specific error we're seeing
                    if 'commentThread' in error_msg:
                        raise ValueError(f"YouTube API processing failure for video {video_id}: This may be due to temporary restrictions, rate limiting, or the video having special access controls. Please try again later or use a different video.")
                    else:
                        raise ValueError(f"YouTube API processing failure: {error_msg}")
                else:
                    raise ValueError(f"YouTube API access forbidden (status 403): {error_msg}")
            elif status == 404:
                raise ValueError(f"Video with ID {video_id} not found or is private")
            elif status == 400:
                raise ValueError(f"Invalid request for video {video_id}: {error_msg}")
            else:
                raise ValueError(f"YouTube API error (status {status}) for video {video_id}: {error_msg}")
    
    def _process_comment_thread(self, thread_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single comment thread and format it
        
        Args:
            thread_data: Raw comment thread data from API
            
        Returns:
            Formatted comment thread dictionary
        """
        top_level_comment = thread_data['snippet']['topLevelComment']['snippet']
        
        thread = {
            'id': thread_data['id'],
            'comment': {
                'id': thread_data['snippet']['topLevelComment']['id'],
                'text': top_level_comment['textDisplay'],
                'author': top_level_comment['authorDisplayName'],
                'author_channel_id': top_level_comment['authorChannelId']['value'],
                'author_profile_image': top_level_comment['authorProfileImageUrl'],
                'likes': top_level_comment.get('likeCount', 0),
                'published_at': top_level_comment['publishedAt'],
                'updated_at': top_level_comment.get('updatedAt', top_level_comment['publishedAt'])
            },
            'reply_count': thread_data['snippet'].get('totalReplyCount', 0),
            'replies': []
        }
        
        # Fetch all replies if they exist
        if 'replies' in thread_data:
            replies = thread_data['replies']['comments']
            
            # If there are more replies than what's returned, fetch them all
            if thread['reply_count'] > len(replies):
                replies = self._fetch_all_replies(thread_data['id'])
            
            for reply_data in replies:
                reply = reply_data['snippet']
                thread['replies'].append({
                    'id': reply_data['id'],
                    'text': reply['textDisplay'],
                    'author': reply['authorDisplayName'],
                    'author_channel_id': reply['authorChannelId']['value'],
                    'author_profile_image': reply['authorProfileImageUrl'],
                    'likes': reply.get('likeCount', 0),
                    'published_at': reply['publishedAt'],
                    'updated_at': reply.get('updatedAt', reply['publishedAt']),
                    'parent_id': reply.get('parentId')
                })
        
        return thread
    
    def _fetch_all_replies(self, parent_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all replies for a comment thread when there are more than initially returned
        
        Args:
            parent_id: The parent comment thread ID
            
        Returns:
            List of all reply comments
        """
        all_replies = []
        next_page_token = None
        
        while True:
            request = self.youtube.comments().list(
                part='snippet',
                parentId=parent_id,
                maxResults=self.max_results_per_page,
                pageToken=next_page_token,
                textFormat='plainText'
            )
            
            response = request.execute()
            all_replies.extend(response.get('items', []))
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        return all_replies
    
    def get_all_comments_flat(self, video_id: str, max_comments: Optional[int] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get all comments in a flat list (easier for sentiment analysis)
        
        Args:
            video_id: YouTube video ID
            max_comments: Maximum number of comments to fetch
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Flat list of all comments (top-level and replies)
        """
        # Create a cache key that includes the max_comments parameter
        cache_key = f"{video_id}:{max_comments or 'all'}"
        
        # Try to get from cache first
        if use_cache:
            cached_data = cache.get('comments_flat', cache_key)
            if cached_data:
                print(f"Cache hit for comments: {video_id} (max: {max_comments})")
                return cached_data
        
        # Don't use cache for get_comment_threads since we're caching the flat result
        threads = self.get_comment_threads(video_id, max_comments, use_cache=False)
        all_comments = []
        
        for thread in threads:
            # Add top-level comment
            comment = thread['comment'].copy()
            comment['is_reply'] = False
            comment['thread_id'] = thread['id']
            all_comments.append(comment)
            
            # Add all replies
            for reply in thread['replies']:
                reply_comment = reply.copy()
                reply_comment['is_reply'] = True
                reply_comment['thread_id'] = thread['id']
                all_comments.append(reply_comment)
        
        # Cache the result for 6 hours (comments change more frequently than video info)
        if use_cache:
            cache.set('comments_flat', cache_key, all_comments, ttl_hours=6)
            print(f"Cached {len(all_comments)} comments for: {video_id}")
        
        return all_comments
    
    def get_video_comments_summary(self, video_id: str, max_comments: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a comprehensive summary of video and its comments
        
        Args:
            video_id: YouTube video ID
            max_comments: Maximum number of comments to fetch
            
        Returns:
            Dictionary containing video info and all comments
        """
        # Get video information
        video_info = self.get_video_info(video_id)
        
        # Get all comment threads
        comment_threads = self.get_comment_threads(video_id, max_comments)
        
        # Calculate statistics
        total_comments = sum(1 + thread['reply_count'] for thread in comment_threads)
        total_likes = sum(thread['comment']['likes'] for thread in comment_threads)
        total_likes += sum(reply['likes'] for thread in comment_threads for reply in thread['replies'])
        
        return {
            'video': video_info,
            'comments': {
                'threads': comment_threads,
                'statistics': {
                    'total_threads': len(comment_threads),
                    'total_comments': total_comments,
                    'total_likes': total_likes,
                    'fetched_threads': len(comment_threads),
                    'api_limit_reached': max_comments and len(comment_threads) >= max_comments
                }
            }
        }
