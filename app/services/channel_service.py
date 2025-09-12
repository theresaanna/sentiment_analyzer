"""
ChannelService: Resolve YouTube channel from URL/handle and list videos.

Uses YouTube Data API v3 via googleapiclient. Results are cached in Redis via app.cache.
"""
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.cache import cache
from app import db
from app.models import Channel, Video, UserChannel
from datetime import datetime, timezone


class ChannelService:
    """Service for fetching a channel and its videos."""

    def check_and_sync_channel(self, yt_channel_id: str, refresh: bool = False, max_new: int = 100) -> Dict[str, Any]:
        """
        Cheap freshness check using uploads playlist head or channel videoCount.
        If new uploads detected or refresh=True, fetch deltas and upsert into DB.
        Returns summary with counts.
        """
        ch = Channel.query.filter_by(yt_channel_id=yt_channel_id).first()
        if not ch or not ch.uploads_playlist_id:
            return {'synced': False, 'reason': 'channel_missing'}

        # If recently checked and not forced, skip
        if not refresh and ch.last_checked_at and (datetime.utcnow() - ch.last_checked_at).total_seconds() < 600:
            return {'synced': False, 'reason': 'recently_checked'}

        # Get newest upload from playlist
        req = self.youtube.playlistItems().list(part='contentDetails', playlistId=ch.uploads_playlist_id, maxResults=1)
        resp = req.execute()
        items = resp.get('items', [])
        newest = items[0]['contentDetails']['videoId'] if items else None

        ch.last_checked_at = datetime.utcnow()
        if not newest or newest == ch.latest_video_id:
            db.session.commit()
            return {'synced': False, 'reason': 'no_new_uploads'}

        # Walk playlist until we hit known latest_video_id or max_new
        new_videos: List[str] = []
        next_page_token = None
        stop = False
        while not stop and len(new_videos) < max_new:
            req = self.youtube.playlistItems().list(
                part='contentDetails,snippet',
                playlistId=ch.uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            resp = req.execute()
            for it in resp.get('items', []):
                vid = it['contentDetails']['videoId']
                if vid == ch.latest_video_id:
                    stop = True
                    break
                new_videos.append(vid)
            next_page_token = resp.get('nextPageToken')
            if not next_page_token:
                break

        if not new_videos:
            db.session.commit()
            return {'synced': False, 'reason': 'no_delta'}

        # Fetch stats for new vids
        # Also get titles/publishedAt from snippet by reusing last response? Simpler: fetch videos().list
        batches = [new_videos[i:i+50] for i in range(0, len(new_videos), 50)]
        added = 0
        for b in batches:
            ids = ','.join(b)
            req = self.youtube.videos().list(part='snippet,statistics', id=ids)
            vresp = req.execute()
            for item in vresp.get('items', []):
                vid = item['id']
                snippet = item.get('snippet', {})
                stats = item.get('statistics', {})
                row = Video.query.filter_by(yt_video_id=vid).first()
                if not row:
                    row = Video(
                        yt_video_id=vid,
                        channel_id=ch.id,
                        title=snippet.get('title', ''),
                        published_at=datetime.fromisoformat(snippet.get('publishedAt', '').replace('Z', '+00:00')) if snippet.get('publishedAt') else None,
                        views=int(stats.get('viewCount', 0) or 0),
                        likes=int(stats.get('likeCount', 0) or 0),
                        comments=int(stats.get('commentCount', 0) or 0),
                        last_synced_at=datetime.utcnow()
                    )
                    db.session.add(row)
                    added += 1
                else:
                    row.title = snippet.get('title', row.title)
                    row.views = int(stats.get('viewCount', row.views) or 0)
                    row.likes = int(stats.get('likeCount', row.likes) or 0)
                    row.comments = int(stats.get('commentCount', row.comments) or 0)
                    row.last_synced_at = datetime.utcnow()
        ch.latest_video_id = newest
        ch.video_count = (ch.video_count or 0) + added
        ch.last_synced_at = datetime.utcnow()
        db.session.commit()

        # Bust Redis snapshots for this channel
        try:
            if cache.enabled:
                pattern = cache._make_key('channel_videos', f"{yt_channel_id}:") + "*"
                keys = cache.redis_client.keys(pattern)
                if keys:
                    cache.redis_client.delete(*keys)
        except Exception:
            pass

        return {'synced': True, 'added': added, 'new_latest_video_id': newest}

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key is required. Set YOUTUBE_API_KEY in .env file")
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    @staticmethod
    def _parse_channel_input(input_str: str) -> Dict[str, str]:
        """
        Parse various forms of channel input into hints for resolution.
        Supports:
        - https://www.youtube.com/channel/UCxxxx
        - https://www.youtube.com/@handle
        - https://www.youtube.com/user/username
        - https://www.youtube.com/c/customName (fallback search)
        - @handle
        - UCxxxx (channel ID)
        - plain string (fallback search)
        """
        input_str = (input_str or '').strip()
        hints: Dict[str, str] = {}
        if not input_str:
            return hints

        # Handle raw channel ID
        if re.match(r'^UC[0-9A-Za-z_-]{22}$', input_str):
            hints['channel_id'] = input_str
            return hints

        # Handle handle-only input like @myhandle
        if input_str.startswith('@'):
            hints['handle'] = input_str
            return hints

        # Parse URL forms
        try:
            parsed = urlparse(input_str)
            if parsed.netloc and ('youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc):
                path = parsed.path or ''
                # /channel/UCxxxx
                m = re.search(r'/channel/(UC[0-9A-Za-z_-]{22})', path)
                if m:
                    hints['channel_id'] = m.group(1)
                    return hints
                # /@handle
                m = re.search(r'/@([\w\-\.]+)', path)
                if m:
                    hints['handle'] = '@' + m.group(1)
                    return hints
                # /user/username
                m = re.search(r'/user/([^/]+)', path)
                if m:
                    hints['username'] = m.group(1)
                    return hints
                # /c/customName → fallback search
                m = re.search(r'/c/([^/]+)', path)
                if m:
                    hints['search'] = m.group(1)
                    return hints
                # /@handle in URL query sometimes
                if '@' in input_str:
                    h = '@' + input_str.split('@', 1)[1].split('/', 1)[0]
                    hints['handle'] = h
                    return hints
        except Exception:
            pass

        # Fallback: plain text; try as handle if startswith @, else search
        if input_str.startswith('@'):
            hints['handle'] = input_str
        else:
            hints['search'] = input_str
        return hints

    def _resolve_channel(self, hints: Dict[str, str]) -> Dict[str, Any]:
        """
        Resolve a channel and return {channel_id, title, uploads_playlist_id}.
        Tries channel_id, forHandle, forUsername, then search.
        """
        # 1) Direct channel ID
        if 'channel_id' in hints:
            channel_id = hints['channel_id']
            req = self.youtube.channels().list(part='snippet,contentDetails', id=channel_id)
            resp = req.execute()
            items = resp.get('items', [])
            if items:
                ch = items[0]
                return {
                    'channel_id': ch['id'],
                    'title': ch['snippet']['title'],
                    'uploads_playlist_id': ch['contentDetails']['relatedPlaylists']['uploads']
                }

        # 2) Handle (@handle) via channels.list forHandle if available; fallback to search
        if 'handle' in hints:
            handle = hints['handle']
            try:
                # Some client libs support forHandle; if not, this will raise
                req = self.youtube.channels().list(part='snippet,contentDetails', forHandle=handle)
                resp = req.execute()
                items = resp.get('items', [])
                if items:
                    ch = items[0]
                    return {
                        'channel_id': ch['id'],
                        'title': ch['snippet']['title'],
                        'uploads_playlist_id': ch['contentDetails']['relatedPlaylists']['uploads']
                    }
            except Exception:
                # Fallback to search
                pass
            # search fallback
            req = self.youtube.search().list(part='snippet', q=handle.lstrip('@'), type='channel', maxResults=1)
            resp = req.execute()
            items = resp.get('items', [])
            if items:
                ch_id = items[0]['id']['channelId']
                return self._resolve_channel({'channel_id': ch_id})

        # 3) Username via forUsername
        if 'username' in hints:
            username = hints['username']
            req = self.youtube.channels().list(part='snippet,contentDetails', forUsername=username)
            resp = req.execute()
            items = resp.get('items', [])
            if items:
                ch = items[0]
                return {
                    'channel_id': ch['id'],
                    'title': ch['snippet']['title'],
                    'uploads_playlist_id': ch['contentDetails']['relatedPlaylists']['uploads']
                }

        # 4) Fallback to search term
        if 'search' in hints:
            term = hints['search']
            req = self.youtube.search().list(part='snippet', q=term, type='channel', maxResults=1)
            resp = req.execute()
            items = resp.get('items', [])
            if items:
                ch_id = items[0]['id']['channelId']
                return self._resolve_channel({'channel_id': ch_id})

        raise ValueError("Could not resolve channel from input")

    def get_channel_videos(self, channel_input: str, max_results: int = 100, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Return channel metadata and up to max_results videos with basic stats.
        Persist in DB forever; use Redis snapshot for speed.
        """
        hints = self._parse_channel_input(channel_input)
        channel_meta = self._resolve_channel(hints)
        yt_channel_id = channel_meta['channel_id']

        # 1) Look up or create Channel in DB
        channel_row = Channel.query.filter_by(yt_channel_id=yt_channel_id).first()
        if not channel_row:
            channel_row = Channel(
                yt_channel_id=yt_channel_id,
                title=channel_meta['title'],
                uploads_playlist_id=channel_meta.get('uploads_playlist_id'),
                handle=hints.get('handle')
            )
            db.session.add(channel_row)
            db.session.commit()
        else:
            # Keep title and uploads playlist updated
            updated = False
            if channel_row.title != channel_meta['title']:
                channel_row.title = channel_meta['title']
                updated = True
            if channel_meta.get('uploads_playlist_id') and channel_row.uploads_playlist_id != channel_meta['uploads_playlist_id']:
                channel_row.uploads_playlist_id = channel_meta['uploads_playlist_id']
                updated = True
            if updated:
                db.session.commit()

        # 2) Optionally remember that the user follows this channel
        if user_id:
            try:
                exists = UserChannel.query.filter_by(user_id=user_id, channel_id=channel_row.id).first()
                if not exists:
                    db.session.add(UserChannel(user_id=user_id, channel_id=channel_row.id))
                    db.session.commit()
            except Exception:
                db.session.rollback()

        # 3) Serve from Redis snapshot if present
        cache_key = f"{yt_channel_id}:{max_results}"
        cached = cache.get('channel_videos', cache_key)
        if cached:
            return cached

        # 4) If DB already has some videos, serve those immediately (stale-while-revalidate strategy)
        existing = Video.query.filter_by(channel_id=channel_row.id).order_by(Video.published_at.desc().nullslast()).limit(max_results).all()
        if existing:
            payload = {
                'channel': {
                    'id': yt_channel_id,
                    'title': channel_row.title,
                    'uploads_playlist_id': channel_row.uploads_playlist_id
                },
                'videos': [
                    {
                        'id': v.yt_video_id,
                        'title': v.title,
                        'published_at': v.published_at.isoformat() if v.published_at else None,
                        'statistics': {'views': v.views, 'likes': v.likes, 'comments': v.comments}
                    }
                    for v in existing
                ],
                'count': len(existing)
            }
            cache.set('channel_videos', cache_key, payload, ttl_hours=12)
            # Trigger a lightweight freshness check asynchronously by returning payload now
            # The endpoint can choose to call check_and_sync_channel in background if desired.
            return payload

        # 5) If fresh channel (no videos in DB), fetch list and populate DB
        uploads = channel_meta['uploads_playlist_id']
        videos: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None

        while True and len(videos) < max_results:
            req = self.youtube.playlistItems().list(
                part='contentDetails,snippet',
                playlistId=uploads,
                maxResults=min(50, max_results - len(videos)),
                pageToken=next_page_token
            )
            resp = req.execute()
            items = resp.get('items', [])
            for it in items:
                vid = it['contentDetails']['videoId']
                snippet = it.get('snippet', {})
                videos.append({
                    'id': vid,
                    'title': snippet.get('title', ''),
                    'published_at': snippet.get('publishedAt', '')
                })
                if len(videos) >= max_results:
                    break
            next_page_token = resp.get('nextPageToken')
            if not next_page_token:
                break

        # Fetch stats in batches of 50
        for i in range(0, len(videos), 50):
            batch = videos[i:i+50]
            ids = ','.join(v['id'] for v in batch)
            req = self.youtube.videos().list(part='statistics', id=ids)
            stats_resp = req.execute()
            stats_by_id: Dict[str, Any] = {item['id']: item.get('statistics', {}) for item in stats_resp.get('items', [])}
            for v in batch:
                s = stats_by_id.get(v['id'], {})
                v['statistics'] = {
                    'views': int(s.get('viewCount', 0)) if s.get('viewCount') else 0,
                    'likes': int(s.get('likeCount', 0)) if s.get('likeCount') else 0,
                    'comments': int(s.get('commentCount', 0)) if s.get('commentCount') else 0
                }

        # Upsert into DB
        newest_video_id = videos[0]['id'] if videos else None
        for v in videos:
            row = Video.query.filter_by(yt_video_id=v['id']).first()
            if not row:
                row = Video(
                    yt_video_id=v['id'],
                    channel_id=channel_row.id,
                    title=v['title'] or '',
                    published_at=datetime.fromisoformat(v['published_at'].replace('Z', '+00:00')) if v.get('published_at') else None,
                    views=v['statistics']['views'],
                    likes=v['statistics']['likes'],
                    comments=v['statistics']['comments'],
                    last_synced_at=datetime.utcnow()
                )
                db.session.add(row)
            else:
                row.title = v['title'] or row.title
                row.views = v['statistics']['views']
                row.likes = v['statistics']['likes']
                row.comments = v['statistics']['comments']
                row.last_synced_at = datetime.utcnow()
        channel_row.latest_video_id = newest_video_id or channel_row.latest_video_id
        channel_row.video_count = max(channel_row.video_count or 0, len(videos))
        channel_row.last_synced_at = datetime.utcnow()
        channel_row.last_checked_at = datetime.utcnow()
        db.session.commit()

        result = {
            'channel': {
                'id': yt_channel_id,
                'title': channel_row.title,
                'uploads_playlist_id': channel_row.uploads_playlist_id
            },
            'videos': videos,
            'count': len(videos)
        }

        cache.set('channel_videos', cache_key, result, ttl_hours=12)
        return result
