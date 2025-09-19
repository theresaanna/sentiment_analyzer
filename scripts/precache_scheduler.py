#!/usr/bin/env python3
"""
Railway-friendly scheduler to warm Redis caches for YouTube videos on a cadence.

Runs inside a dedicated Railway service (separate from web/worker) and calls
scripts/precache_video.py for one or more video IDs at startup and then daily.

Configuration via environment variables:
- PRECACHE_VIDEO_IDS: CSV of video IDs or URLs (default: dQw4w9WgXcQ)
- PRECACHE_COMMENTS: integer (default: 500)
- PRECACHE_INCLUDE_REPLIES: 'true'|'false' (default: false)
- PRECACHE_SORT: 'relevance'|'time' (default: relevance)
- PRECACHE_AT: 'HH:MM' in 24h UTC to run daily (default: 03:00)
  or
- PRECACHE_INTERVAL_HOURS: integer > 0 to run every N hours (overrides PRECACHE_AT)

Required environment:
- YOUTUBE_API_KEY
- REDIS_URL (if not using default)

Start command (Railway service):
  python scripts/precache_scheduler.py
"""
import os
import sys
import time
import shlex
import subprocess
from datetime import datetime

# Local schedule runner (already in requirements.txt)
import schedule  # type: ignore

# Ensure project root is importable (for cache/YouTube services if needed)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _bool(val: str, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y")


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def run_precache_once():
    video_list = [v.strip() for v in _env("PRECACHE_VIDEO_IDS", "dQw4w9WgXcQ").split(",") if v.strip()]
    comments = int(_env("PRECACHE_COMMENTS", "500"))
    include_replies = _bool(_env("PRECACHE_INCLUDE_REPLIES", "false"))
    sort = _env("PRECACHE_SORT", "relevance")

    # Verify YOUTUBE_API_KEY present
    if not os.getenv("YOUTUBE_API_KEY"):
        print("[precache] ERROR: YOUTUBE_API_KEY not set in environment", flush=True)
        return

    # Build base command
    base = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "precache_video.py")]

    for vid in video_list:
        cmd = base + [vid, "--comments", str(comments), "--include-replies", ("true" if include_replies else "false"), "--sort", sort]
        print(f"[precache] {datetime.utcnow().isoformat()}Z → Running: {' '.join(shlex.quote(p) for p in cmd)}", flush=True)
        try:
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if proc.stdout:
                print(proc.stdout, end="", flush=True)
            if proc.stderr:
                print(proc.stderr, end="", flush=True)
            if proc.returncode != 0:
                print(f"[precache] ERROR: precache returned code {proc.returncode} for {vid}", flush=True)
        except Exception as e:
            print(f"[precache] EXCEPTION while precaching {vid}: {e}", flush=True)


def main():
    print("🚂 Precache Scheduler starting...", flush=True)
    print(f"Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')} | UTC now: {datetime.utcnow().isoformat()}Z", flush=True)

    # Run immediately at start (warm right away)
    run_precache_once()

    # Configure schedule
    interval_hours = int(_env("PRECACHE_INTERVAL_HOURS", "0"))
    if interval_hours > 0:
        print(f"[precache] Scheduling every {interval_hours} hours", flush=True)
        schedule.every(interval_hours).hours.do(run_precache_once)
    else:
        at = _env("PRECACHE_AT", "03:00")
        print(f"[precache] Scheduling daily at {at} UTC", flush=True)
        try:
            schedule.every().day.at(at).do(run_precache_once)
        except schedule.ScheduleValueError:
            print(f"[precache] Invalid PRECACHE_AT '{at}', falling back to 24h interval", flush=True)
            schedule.every(24).hours.do(run_precache_once)

    # Loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            print("[precache] Scheduler exiting (KeyboardInterrupt)")
            break
        except Exception as e:
            print(f"[precache] Scheduler loop error: {e}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()