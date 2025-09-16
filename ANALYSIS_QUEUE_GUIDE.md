# Analysis Queue System Guide

## Overview
The sentiment analysis queueing system allows users to queue longer-running analysis jobs for background processing. This is particularly useful for analyzing videos with thousands of comments.

## Features

### 1. Queue Analysis Jobs
- **Instant Analysis**: Up to 2,500 comments, processed immediately
- **Queued Analysis**: 2,501 to 10,000 comments, processed in background
- Users can queue multiple analysis jobs
- Jobs are processed sequentially by the background worker

### 2. Job Status Tracking
- Real-time progress monitoring
- Automatic page refresh every 5 seconds
- Progress bar showing completion percentage
- Ability to cancel running jobs

### 3. Analysis History
- View all past analyses on the Profile page
- See completed, processing, and failed jobs
- Access full results for completed analyses
- Quick overview with sentiment badges and comment counts

## How to Use

### For Users

1. **Queue an Analysis**:
   - Go to the analyze page for any YouTube video
   - If logged in, use the slider to select > 2,500 comments
   - Click the "Queue Analysis" button
   - You'll be redirected to a status page

2. **Monitor Progress**:
   - The status page auto-refreshes every 5 seconds
   - Shows current progress percentage
   - Displays number of comments processed
   - Automatically redirects to results when complete

3. **View Results**:
   - Completed analyses appear in your Profile
   - Click "View Results" to see full analysis
   - Results include sentiment distribution, sample comments, and statistics

### For Developers

1. **Start the Worker**:
   ```bash
   # In a separate terminal
   ./start_worker.sh
   # Or directly:
   python analysis_worker.py
   ```

2. **Monitor Worker Logs**:
   - Worker logs show job processing status
   - Includes timing information
   - Error messages for failed jobs

3. **Database Schema**:
   - Jobs are stored in the `AnalysisJob` table
   - Results are stored as JSON in the `results` column
   - Status values: `queued`, `processing`, `completed`, `failed`, `cancelled`

## API Endpoints

### Queue a Job
```
POST /api/analyze/queue
{
    "video_id": "VIDEO_ID",
    "comment_count": 5000
}
```

### Check Job Status
```
GET /api/analyze/job/{job_id}
```

### List User's Jobs
```
GET /api/user/analysis-jobs?status=active&limit=10
```

### Cancel a Job
```
DELETE /api/analyze/job/{job_id}
```

### Get Job Results
```
GET /api/analyze/job/{job_id}/results
```

## Configuration

### Worker Settings
- Default batch size: 100 comments
- Progress updates: Every batch
- Timeout: None (jobs run to completion)
- Concurrent jobs per user: 1 (sequential processing)

### Redis Integration (Optional)
- If Redis is enabled, jobs are also queued in Redis
- Provides faster job retrieval
- Enables distributed processing (future feature)

## Troubleshooting

### Job Stuck in "Queued"
- Check if the worker is running
- Look for errors in worker logs
- Verify database connectivity

### Job Failed
- Check the `error_message` field in the job
- Review worker logs for detailed error
- Common issues: API rate limits, network errors

### Results Not Showing
- Ensure job status is "completed"
- Check if results JSON is properly stored
- Verify user authentication

## Future Enhancements
- Email notifications when jobs complete
- Batch job processing
- Priority queue for Pro users
- Export results to CSV/PDF
- Scheduled recurring analyses