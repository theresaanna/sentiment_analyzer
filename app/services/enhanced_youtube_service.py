"""
Enhanced YouTube Service for Maximum Comment Retrieval

This module provides optimized methods to fetch the maximum number of comments
from YouTube videos while respecting API quotas and rate limits.
"""
import os
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.cache import cache
from app.services.youtube_service import YouTubeService
from app.services.async_youtube_service import AsyncYouTubeService

logger = logging.getLogger(__name__)


class EnhancedYouTubeService(YouTubeService):
    """Enhanced YouTube service that maximizes comment retrieval."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the enhanced YouTube service.
        
        Args:
            api_key: YouTube Data API key
        """
        super().__init__(api_key)
        
        # Enhanced settings for maximum retrieval
        self.max_results_per_page = 100  # YouTube API maximum per page
        self.max_pages_per_request = 50  # Limit pages to avoid quota issues
        self.max_replies_per_thread = 500  # Limit replies per thread
        
        # Quota management
        self.quota_cost_per_request = {
            'commentThreads': 1,  # Each commentThreads.list costs 1 unit
            'comments': 1,  # Each comments.list costs 1 unit
            'videos': 1  # Each videos.list costs 1 unit
        }
        self.daily_quota_limit = 10000  # YouTube default daily quota
        self.quota_used = 0
        
        logger.info("EnhancedYouTubeService initialized with maximum retrieval settings")
    
    def get_all_available_comments(self, video_id: str, 
                                  target_comments: Optional[int] = None,
                                  include_replies: bool = True,
                                  use_cache: bool = True,
                                  sort_order: str = 'relevance') -> Dict[str, Any]:
        """
        Fetch maximum available comments from a video.
        
        Args:
            video_id: YouTube video ID
            target_comments: Target number of comments (None for all available)
            include_replies: Whether to fetch replies to comments
            use_cache: Whether to use cache
            sort_order: 'relevance' or 'time' for comment ordering
            
        Returns:
            Dictionary with comments and statistics
        """
        cache_key = f"{video_id}:max:{target_comments or 'all'}:{include_replies}:{sort_order}"
        
        if use_cache:
            cached_data = cache.get('enhanced_comments', cache_key)
            if cached_data:
                logger.info(f"Cache hit for enhanced comments: {video_id}")
                return cached_data
        
        start_time = time.time()
        
        # Get video info first to know total comment count
        video_info = self.get_video_info(video_id, use_cache=use_cache)
        total_comment_count = video_info['statistics']['comments']
        
        logger.info(f"Video has {total_comment_count} total comments. Starting retrieval...")
        
        # Calculate how many comments we can realistically fetch
        max_feasible = self._calculate_feasible_comments(total_comment_count, target_comments)
        
        # Fetch comment threads
        all_comments = []
        all_threads = []
        next_page_token = None
        pages_fetched = 0
        comments_fetched = 0
        quota_used = 0
        
        try:
            while True:
                # Check quota limits
                if quota_used >= self.daily_quota_limit * 0.8:  # Use max 80% of quota
                    logger.warning(f"Approaching quota limit. Stopping at {comments_fetched} comments")
                    break
                
                # Make API request
                request = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=self.max_results_per_page,
                    pageToken=next_page_token,
                    textFormat='plainText',
                    order=sort_order
                )
                
                response = request.execute()
                quota_used += self.quota_cost_per_request['commentThreads']
                
                # Process comment threads
                for item in response.get('items', []):
                    thread = self._process_comment_thread_enhanced(item, include_replies)
                    all_threads.append(thread)
                    
                    # Add top-level comment
                    comment = thread['comment'].copy()
                    comment['is_reply'] = False
                    comment['thread_id'] = thread['id']
                    all_comments.append(comment)
                    comments_fetched += 1
                    
                    # Add replies if requested
                    if include_replies:
                        for reply in thread['replies']:
                            reply_comment = reply.copy()
                            reply_comment['is_reply'] = True
                            reply_comment['thread_id'] = thread['id']
                            all_comments.append(reply_comment)
                            comments_fetched += 1
                    
                    # Check if we've reached target
                    if max_feasible and comments_fetched >= max_feasible:
                        break
                
                pages_fetched += 1
                next_page_token = response.get('nextPageToken')
                
                # Log progress
                if pages_fetched % 10 == 0:
                    logger.info(f"Fetched {pages_fetched} pages, {comments_fetched} comments...")
                
                # Stop conditions
                if not next_page_token:
                    logger.info("No more pages available")
                    break
                if pages_fetched >= self.max_pages_per_request:
                    logger.info(f"Reached max pages limit ({self.max_pages_per_request})")
                    break
                if max_feasible and comments_fetched >= max_feasible:
                    logger.info(f"Reached target comments ({max_feasible})")
                    break
            
            # Prepare comprehensive result
            fetch_time = time.time() - start_time
            result = {
                'video': video_info,
                'comments': all_comments,
                'threads': all_threads,
                'statistics': {
                    'total_comments_available': total_comment_count,
                    'comments_fetched': comments_fetched,
                    'threads_fetched': len(all_threads),
                    'replies_fetched': sum(1 for c in all_comments if c.get('is_reply', False)),
                    'pages_fetched': pages_fetched,
                    'fetch_time_seconds': fetch_time,
                    'comments_per_second': comments_fetched / fetch_time if fetch_time > 0 else 0,
                    'quota_used': quota_used,
                    'sort_order': sort_order,
                    'fetch_percentage': (comments_fetched / total_comment_count * 100) if total_comment_count > 0 else 0
                },
                'fetch_metadata': {
                    'incomplete': next_page_token is not None,
                    'limited_by': self._get_limiting_factor(pages_fetched, comments_fetched, quota_used, max_feasible)
                }
            }
            
            # Cache the result
            if use_cache:
                cache.set('enhanced_comments', cache_key, result, ttl_hours=12)
                logger.info(f"Cached {comments_fetched} comments for video {video_id}")
            
            logger.info(f"Successfully fetched {comments_fetched}/{total_comment_count} comments "
                       f"({result['statistics']['fetch_percentage']:.1f}%) in {fetch_time:.2f}s")
            
            return result
            
        except HttpError as e:
            logger.error(f"API error: {e}")
            raise
    
    def _process_comment_thread_enhanced(self, thread_data: Dict[str, Any], 
                                        include_replies: bool) -> Dict[str, Any]:
        """
        Enhanced comment thread processing with better reply handling.
        
        Args:
            thread_data: Raw thread data from API
            include_replies: Whether to fetch all replies
            
        Returns:
            Processed thread with all available data
        """
        thread = super()._process_comment_thread(thread_data)
        
        # Fetch additional replies if there are more than initially returned
        if include_replies and thread['reply_count'] > len(thread['replies']):
            if thread['reply_count'] <= self.max_replies_per_thread:
                try:
                    all_replies = self._fetch_all_replies(thread_data['id'])
                    thread['replies'] = []
                    for reply_data in all_replies:
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
                except Exception as e:
                    logger.warning(f"Failed to fetch all replies for thread {thread_data['id']}: {e}")
        
        return thread
    
    def _calculate_feasible_comments(self, total_available: int, 
                                    target: Optional[int]) -> Optional[int]:
        """
        Calculate feasible number of comments to fetch based on constraints.
        
        Args:
            total_available: Total comments available on video
            target: User-specified target
            
        Returns:
            Feasible number of comments to fetch
        """
        # API constraints
        max_api_comments = self.max_pages_per_request * self.max_results_per_page  # 5000 with default settings
        
        # Quota constraints (reserve 20% quota for other operations)
        max_quota_comments = int(self.daily_quota_limit * 0.8 / self.quota_cost_per_request['commentThreads'])
        
        # Calculate minimum of all constraints
        constraints = [total_available, max_api_comments, max_quota_comments]
        if target:
            constraints.append(target)
        
        feasible = min(constraints)
        
        logger.info(f"Feasible comments calculation: "
                   f"available={total_available}, "
                   f"target={target}, "
                   f"api_limit={max_api_comments}, "
                   f"quota_limit={max_quota_comments}, "
                   f"feasible={feasible}")
        
        return feasible
    
    def _get_limiting_factor(self, pages: int, comments: int, 
                            quota: int, target: Optional[int]) -> str:
        """Determine what limited the comment fetching."""
        if quota >= self.daily_quota_limit * 0.8:
            return "quota_limit"
        elif pages >= self.max_pages_per_request:
            return "page_limit"
        elif target and comments >= target:
            return "target_reached"
        else:
            return "all_fetched"
    
    def get_comment_batches_async(self, video_id: str, 
                                 batch_size: int = 1000) -> List[List[Dict[str, Any]]]:
        """
        Fetch comments in batches for memory-efficient processing.
        
        Args:
            video_id: YouTube video ID
            batch_size: Size of each batch
            
        Returns:
            Generator yielding batches of comments
        """
        all_data = self.get_all_available_comments(video_id)
        comments = all_data['comments']
        
        # Split into batches
        batches = []
        for i in range(0, len(comments), batch_size):
            batch = comments[i:i + batch_size]
            batches.append(batch)
            logger.info(f"Created batch {len(batches)} with {len(batch)} comments")
        
        return batches
    
    def estimate_api_usage(self, video_id: str) -> Dict[str, Any]:
        """
        Estimate API quota usage for fetching all comments from a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with usage estimates
        """
        video_info = self.get_video_info(video_id)
        total_comments = video_info['statistics']['comments']
        
        # Estimate based on averages
        avg_replies_per_thread = 2  # Conservative estimate
        estimated_threads = total_comments / (1 + avg_replies_per_thread)
        estimated_pages = estimated_threads / self.max_results_per_page
        
        # Calculate quota costs
        thread_requests = estimated_pages
        reply_requests = estimated_threads * 0.3  # Assume 30% threads need extra reply fetching
        total_quota = thread_requests + reply_requests
        
        return {
            'video_id': video_id,
            'total_comments': total_comments,
            'estimated_api_calls': int(thread_requests + reply_requests),
            'estimated_quota_usage': int(total_quota),
            'percentage_of_daily_quota': (total_quota / self.daily_quota_limit) * 100,
            'feasible_with_current_quota': total_quota < self.daily_quota_limit * 0.8,
            'estimated_fetch_time_seconds': estimated_pages * 0.5,  # ~0.5s per request
            'recommendations': self._get_recommendations(total_comments, total_quota)
        }
    
    def _get_recommendations(self, total_comments: int, quota_needed: int) -> List[str]:
        """Generate recommendations for fetching strategy."""
        recommendations = []
        
        if quota_needed > self.daily_quota_limit * 0.8:
            recommendations.append("Consider fetching in multiple sessions across days")
            recommendations.append("Use caching to avoid repeated API calls")
            recommendations.append("Focus on most relevant comments (sort by relevance)")
        
        if total_comments > 10000:
            recommendations.append("Video has many comments - consider sampling strategy")
            recommendations.append("Fetch top-level comments only for initial analysis")
        
        if total_comments < 1000:
            recommendations.append("Can fetch all comments in single session")
            recommendations.append("Include all replies for comprehensive analysis")
        
        return recommendations


async def fetch_maximum_comments_async(video_id: str, target: Optional[int] = None) -> Dict[str, Any]:
    """
    Async wrapper to fetch maximum comments using concurrent requests.
    
    Args:
        video_id: YouTube video ID
        target: Target number of comments
        
    Returns:
        Dictionary with all fetched data
    """
    async with AsyncYouTubeService(max_concurrent_requests=10) as service:
        result = await service.get_all_comments_fast(video_id, target)
        return result


def analyze_comment_coverage(video_id: str) -> Dict[str, Any]:
    """
    Analyze how many comments can be fetched and provide strategy.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Analysis and recommendations
    """
    service = EnhancedYouTubeService()
    
    # Get video info
    video_info = service.get_video_info(video_id)
    total_comments = video_info['statistics']['comments']
    
    # Estimate API usage
    estimates = service.estimate_api_usage(video_id)
    
    # Generate strategy
    strategy = {
        'video_info': {
            'title': video_info['title'],
            'total_comments': total_comments,
            'channel': video_info['channel']
        },
        'fetching_strategy': {
            'can_fetch_all': estimates['feasible_with_current_quota'],
            'recommended_approach': 'full' if total_comments < 5000 else 'sampling',
            'estimated_coverage': min(100, (5000 / total_comments * 100)) if total_comments > 0 else 100,
            'time_estimate': estimates['estimated_fetch_time_seconds']
        },
        'api_usage': estimates,
        'recommendations': estimates['recommendations']
    }
    
    return strategy
