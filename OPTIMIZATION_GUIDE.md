# Analyze Page Performance Optimization Guide

## Current Performance Issues

### Page Load Analysis
- **Anonymous users**: Loading 2,500 comments on page load (~5-10 seconds)
- **Logged-in users**: Loading 5,000 comments on page load (~10-20 seconds)
- **Pro users**: Loading up to 50,000 comments (~30-60+ seconds)

### Key Bottlenecks
1. Synchronous comment fetching blocks page render
2. Processing all comments for statistics in memory
3. Large JSON payloads transferred to client
4. Multiple sequential API calls to YouTube

## Optimization Strategy

### 1. Progressive Loading (Immediate Implementation)
```python
# app/main/routes.py

@bp.route('/analyze/<video_id>')
def analyze_video(video_id):
    """Optimized analyze page with progressive loading."""
    
    # QUICK: Only fetch video info and basic stats
    video_info = youtube_service.get_video_info(video_id)
    
    # Don't fetch comments on initial page load
    # Just pass metadata
    comment_stats = {
        'total_available': video_info['statistics']['comments'],
        'fetched_comments': 0,  # Will be loaded via AJAX
        'status': 'ready_to_load'
    }
    
    return render_template(
        'analyze.html',
        video_id=video_id,
        video_info=video_info,
        comment_stats=comment_stats,
        defer_comments=True  # Flag to trigger AJAX load
    )
```

### 2. AJAX-Based Comment Loading
```javascript
// analyze.html
document.addEventListener('DOMContentLoaded', function() {
    if (deferComments) {
        // Show loading indicator
        showCommentLoadingState();
        
        // Fetch comments asynchronously
        fetch(`/api/comments/${videoId}?max=100`)  // Start with 100
            .then(response => response.json())
            .then(data => {
                updateCommentStats(data);
                hideLoadingState();
            });
    }
});
```

### 3. Smart Caching Strategy
```python
def get_video_analysis_cached(video_id, max_comments=100):
    """Multi-tier caching for faster loads."""
    
    # Tier 1: Quick stats cache (1 hour)
    quick_stats = cache.get(f'quick_stats:{video_id}')
    if quick_stats:
        return quick_stats
    
    # Tier 2: Sample comments (24 hours)
    sample = cache.get(f'sample:{video_id}:100')
    if sample:
        return sample
    
    # Tier 3: Fetch fresh
    return fetch_minimal_comments(video_id, 100)
```

### 4. Lazy Loading Comments
```python
class OptimizedYouTubeService:
    def get_video_preview(self, video_id):
        """Get just enough data for initial page load."""
        video_info = self.get_video_info(video_id)
        
        # Fetch only 50-100 comments for preview
        preview_comments = self.get_comments(
            video_id, 
            max_results=100,
            include_replies=False
        )
        
        return {
            'video': video_info,
            'preview_comments': preview_comments,
            'total_available': video_info['statistics']['comments']
        }
```

### 5. Database-First Approach
```python
def analyze_video_optimized(video_id):
    """Check database before API calls."""
    
    # Check if we have recent analysis
    recent_analysis = db.session.query(Analysis)\
        .filter_by(video_id=video_id)\
        .filter(Analysis.created_at > datetime.now() - timedelta(hours=24))\
        .first()
    
    if recent_analysis:
        # Serve from database (instant)
        return render_from_analysis(recent_analysis)
    
    # Otherwise, show preview and queue full analysis
    return render_preview_mode(video_id)
```

## Implementation Steps

### Phase 1: Quick Wins (1-2 hours)
1. **Reduce default comment load**
   ```python
   # Change defaults in routes.py
   DEFAULT_PREVIEW_COMMENTS = 100  # Instead of 2500+
   ```

2. **Add loading states**
   ```javascript
   // Show skeleton loaders while fetching
   function showCommentSkeleton() {
       document.getElementById('commentStats').innerHTML = `
           <div class="skeleton-loader">Loading comments...</div>
       `;
   }
   ```

3. **Implement basic caching**
   ```python
   @cache.memoize(timeout=3600)  # 1 hour cache
   def get_video_stats(video_id):
       return youtube_service.get_video_info(video_id)
   ```

### Phase 2: Progressive Enhancement (3-4 hours)
1. **Split page load and analysis**
   - Page loads instantly with video info
   - Comments load via AJAX after page render
   - User can start analysis when ready

2. **Implement infinite scroll**
   ```javascript
   let offset = 0;
   const BATCH_SIZE = 100;
   
   function loadMoreComments() {
       fetch(`/api/comments/${videoId}?offset=${offset}&limit=${BATCH_SIZE}`)
           .then(response => response.json())
           .then(data => {
               appendComments(data.comments);
               offset += BATCH_SIZE;
           });
   }
   ```

3. **Add "Quick Analysis" mode**
   - Analyze first 100-500 comments instantly
   - Offer "Deep Analysis" for full dataset

### Phase 3: Advanced Optimization (1-2 days)
1. **Precompute popular videos**
   ```python
   # Background job to precompute trending videos
   def precompute_trending():
       trending = get_trending_videos()
       for video in trending:
           cache_analysis(video.id)
   ```

2. **WebSocket for real-time updates**
   ```javascript
   const socket = io.connect();
   socket.on('analysis_progress', (data) => {
       updateProgressBar(data.percentage);
   });
   ```

3. **CDN for static assets**
   - Move large JS/CSS to CDN
   - Compress and minify all assets

## Expected Improvements

### Current Performance
- Initial page load: 5-60 seconds
- Time to interactive: 5-60 seconds
- Total page weight: 1-5 MB

### After Optimization
- Initial page load: <1 second
- Time to interactive: <2 seconds
- Progressive data load: 100 comments/second
- Total page weight: <500 KB initial

## Quick Implementation

### Option 1: Minimal Change (30 minutes)
```python
# In routes.py, change line 115
max_comments = request.args.get('max_comments', type=int, default=100)  # Was 2500+
```

### Option 2: Two-Stage Loading (1 hour)
```python
# New route for deferred loading
@bp.route('/analyze/<video_id>')
def analyze_video(video_id):
    # Only fetch video info
    video_info = youtube_service.get_video_info(video_id)
    return render_template(
        'analyze.html',
        video_id=video_id,
        video_info=video_info,
        load_comments_async=True
    )

@bp.route('/api/video/<video_id>/comments')
def get_comments_async(video_id):
    # Fetch comments separately
    comments = youtube_service.get_comments(video_id, max_results=500)
    return jsonify(comments)
```

### Option 3: Smart Defaults (2 hours)
```python
def get_smart_comment_limit(video_id, user):
    """Dynamically determine optimal comment load."""
    video_info = get_video_info(video_id)
    total_comments = video_info['statistics']['comments']
    
    # For videos with few comments, load all
    if total_comments < 500:
        return total_comments
    
    # For popular videos, start small
    if total_comments > 10000:
        return 100
    
    # Default to 10% of total, max 1000
    return min(1000, int(total_comments * 0.1))
```

## Monitoring & Metrics

### Key Metrics to Track
1. **Page Load Time**: Time to first byte (TTFB)
2. **Time to Interactive**: When user can interact
3. **API Calls**: Number and duration
4. **Cache Hit Rate**: Percentage served from cache
5. **User Engagement**: Bounce rate on slow loads

### Implementation
```python
import time
from flask import g

@app.before_request
def before_request():
    g.start = time.time()

@app.after_request
def after_request(response):
    if hasattr(g, 'start'):
        load_time = time.time() - g.start
        response.headers['X-Load-Time'] = str(load_time)
        
        # Log slow requests
        if load_time > 2:
            logger.warning(f"Slow request: {request.path} took {load_time}s")
    
    return response
```

## Recommended Priority

1. **IMMEDIATE**: Reduce default comment load to 100-500
2. **HIGH**: Implement video info caching (1 hour TTL)
3. **HIGH**: Add AJAX comment loading after page render
4. **MEDIUM**: Create preview mode with sample comments
5. **LOW**: Implement infinite scroll for comments
6. **LOW**: Add WebSocket for real-time updates

This optimization strategy will reduce initial page load time by 80-90% while maintaining full functionality through progressive enhancement.