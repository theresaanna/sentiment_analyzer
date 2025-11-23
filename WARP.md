# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**YouTube Sentiment Analyzer (VibeCheckAI)** - A production-ready Flask web application that analyzes sentiment of YouTube video and channel comments using advanced ML models via an external Modal-hosted microservice. Features real-time analysis, comprehensive dashboards, and social media theme detection.

**Key Technologies:**
- Backend: Flask with blueprints, PostgreSQL, Redis, RQ (Redis Queue)
- Frontend: Bootstrap 5 with Vite-bundled React components
- ML Service: External Modal cloud deployment (separate repository: `sentiment_ml_service`)
- Infrastructure: Railway deployment with automated CI/CD

## Common Development Commands

### Testing

```bash
# Quick unit tests (~30 seconds)
./run_local_tests.sh quick
# or: make test-quick

# Standard unit + integration tests (~2 minutes)
./run_local_tests.sh standard
# or: make test

# Full test suite including slow tests (~5 minutes)
./run_local_tests.sh full
# or: make test-full

# Test Modal ML service integration
./run_local_tests.sh modal
# or: make test-modal

# Run with coverage report
./run_local_tests.sh coverage
# or: make coverage

# Pre-push tests (Python + React + Playwright E2E)
./run_pre_push_tests.sh
# or: npm run pre-push

# Run specific test file
pytest tests/test_routes.py

# Run specific test category (uses pytest markers)
pytest -m "not integration"  # Skip integration tests
pytest -m "not slow"         # Skip slow tests
pytest -k "not redis"        # Skip Redis-dependent tests
```

### Running the Application

```bash
# Start local development server (port 5000)
python run.py

# Start background worker for async job processing
python analysis_worker.py

# Start Redis (required for caching and job queue)
redis-server
```

### Frontend Development

```bash
# Install frontend dependencies
npm run web:install

# Build frontend assets
npm run web:build

# Development mode with hot reload
npm run web:dev

# Run React unit tests
npm run web:test

# Run React tests with coverage
npm run web:test:coverage
```

### Database Management

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations to database
flask db upgrade

# Rollback last migration
flask db downgrade

# Run migration script (Railway-compatible)
python run_migration.py
```

### Code Quality

```bash
# Format Python code
black app/ tests/

# Lint Python code
flake8 app/ tests/

# Type checking
mypy app/

# Clean cache and temp files
make clean
```

### Deployment

```bash
# Deploy all services to Railway
./deploy_all.sh

# Deploy worker only
./deploy_worker.sh

# View Railway logs
railway logs

# Check Railway service status
railway status
```

## Architecture Overview

### Application Structure

```
app/
├── __init__.py          # Application factory with extensions
├── config.py            # Multi-environment configuration
├── models.py            # SQLAlchemy models (User, AnalysisJob, Channel, Video)
├── cache.py             # Redis caching utilities
├── auth/                # Authentication blueprint
│   ├── routes.py        # Login, OAuth, subscriptions
│   └── forms.py         # Auth forms
├── main/                # Main application blueprint
│   ├── routes.py        # Core analysis routes
│   ├── dashboard_routes.py   # User dashboard
│   ├── analysis_queue_routes.py  # Job queue management
│   ├── channel_routes.py     # Channel analysis
│   ├── batch_routes.py       # Batch operations
│   └── fast_routes.py        # Fast preview mode
├── services/            # Business logic layer (service pattern)
│   ├── enhanced_youtube_service.py  # Optimized YouTube API client
│   ├── sentiment_api.py             # External ML service client
│   ├── async_youtube_service.py     # Async YouTube operations
│   └── channel_service.py           # Channel-specific operations
├── utils/               # Utility functions
│   ├── youtube.py       # YouTube URL parsing
│   └── time_formatter.py  # Time formatting helpers
├── templates/           # Jinja2 templates
└── static/              # CSS, JavaScript, images
```

### Key Architectural Patterns

**Service Layer Pattern:**
- All business logic is encapsulated in `app/services/`
- Routes in blueprints handle HTTP concerns only
- Services are stateless and testable in isolation
- Examples: `EnhancedYouTubeService`, `SentimentAPIClient`

**Asynchronous Job Processing:**
- User submits analysis request → creates `AnalysisJob` in database
- Returns `job_id` immediately for tracking
- Background worker (`analysis_worker.py`) processes jobs from Redis queue
- Frontend polls `/analysis/status/<job_id>` for progress updates
- Results stored in `AnalysisJob.results` JSON field

**Multi-Level Caching:**
- Redis: 24-hour cache for YouTube API responses (quota management)
- Database: Persistent storage for analysis results
- In-memory: Flask session data
- Cache keys use pattern: `{video_id}:max:{comment_count}:{include_replies}:{sort_order}`

**External ML Service Integration:**
- Sentiment analysis performed by separate Modal cloud service
- `SentimentAPIClient` handles HTTP communication with timeouts
- Batch processing with fallback to individual analysis on errors
- Configuration via `SENTIMENT_API_URL` environment variable

**Database Models:**
- `User`: Authentication, subscriptions, OAuth
- `AnalysisJob`: Job queue tracking, status, results storage
- `Channel`: YouTube channel metadata and sync state
- `Video`: Video metadata linked to channels
- `UserChannel`: Many-to-many relationship for saved channels

**Comment Limits by User Tier:**
- Anonymous: 2,500 comments (MAX_COMMENTS_ANONYMOUS)
- Free (logged in): 5,000 comments (MAX_COMMENTS_FREE)
- Pro (subscribed): 50,000 comments (MAX_COMMENTS_PRO)

### Frontend Architecture

- **React Components:** Vite-bundled, located in `frontend/src/`
- **Bootstrap 5:** Primary UI framework with custom CSS
- **Visualizations:** Chart.js for charts, custom canvas for word clouds
- **Build Process:** Vite bundles React → outputs to `app/static/dist/`

### Railway Deployment Architecture

**Services:**
1. **Web Service:** Main Flask app (runs `railway_start.py`)
2. **Worker Service:** Background job processor (`analysis_worker.py`)
3. **PostgreSQL:** Primary database (Railway-managed)
4. **Redis:** Cache and job queue (Railway-managed)
5. **Modal ML Service:** External GPU-accelerated sentiment analysis

**Database URL Handling:**
- Railway uses `postgres://` but SQLAlchemy needs `postgresql://`
- Auto-converted in `app/config.py` and `run.py`
- Railway internal host: `postgres.railway.internal`
- Default database name: `railway` (auto-corrected in config)

**Environment Variables:**
- Required: `DATABASE_URL`, `REDIS_URL`, `YOUTUBE_API_KEY`, `SENTIMENT_API_URL`, `SECRET_KEY`
- OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- Payments: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- See `.env.example` for full list

### Testing Architecture

**Test Organization:**
- `tests/` - Python pytest suite
- `tests/e2e/` - Playwright end-to-end tests
- `frontend/src/` - React component tests (Vitest)
- `tests/conftest.py` - Pytest fixtures and configuration

**Pytest Markers:**
- `@pytest.mark.integration` - Requires external services
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.youtube` - Requires YouTube API
- `@pytest.mark.redis` - Requires Redis connection

**Test Database:**
- Uses SQLite in-memory for unit tests: `sqlite:///test.db`
- Set via `DATABASE_URL` in test environment
- Reset between test runs for isolation

**Mocking Strategy:**
- External APIs mocked in tests via `SentimentAPIClient.mock_mode`
- YouTube API responses cached or mocked
- Redis optional for many tests (mock via environment flag)

## Important Development Notes

### YouTube API Integration

**Comment Fetching Logic:**
- Uses `EnhancedYouTubeService` for optimized retrieval
- Fetches comment threads with pagination (100 per page)
- YouTube's `commentCount` includes ALL replies
- Uses `commentThreads.list` API (1 quota unit per request)
- Respects 80% of daily quota limit (10,000 units) to avoid API blocking
- Cache key format: `{video_id}:max:{target}:{include_replies}:{sort_order}`

**Comment Limits:**
- Max pages fetched: 50 (configurable via `max_pages_per_request`)
- Max replies per thread: 500 (configurable via `max_replies_per_thread`)
- Sort orders: `relevance` (default) or `time`

### Worker Process

**Job Processing Flow:**
1. Check job cancellation flag in Redis
2. Fetch YouTube comments (progress: 10-30%)
3. Batch sentiment analysis via Modal API (progress: 40-80%)
4. Calculate statistics and themes (progress: 80-95%)
5. Store results in `AnalysisJob.results` JSON field (progress: 100%)
6. Update job status to `completed` with processing time

**Status Values:**
- `queued` - Waiting in queue
- `processing` - Currently being processed
- `completed` - Successfully finished
- `failed` - Error occurred (see `error_message` field)
- `cancelled` - User cancelled job

### Configuration Management

**Multi-Environment Config:**
- `Config` (base), `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`
- Selected via `FLASK_ENV` environment variable
- Configuration class stored in `app/config.py`
- Use `config_dict` to access: `config_dict['production']`

**Database URL Fixes:**
- Railway Postgres uses `postgres://` but SQLAlchemy requires `postgresql://`
- Auto-corrected in two places: `app/config.py` and `run.py`
- Prefers psycopg3 driver if available: `postgresql+psycopg://`

### External API Service

**Modal ML Service:**
- Separate repository: https://github.com/theresaanna/sentiment_ml_service
- GPU-accelerated transformer models (RoBERTa)
- Endpoints: `/analyze-batch`, `/analyze-text`, `/health`
- Timeout: 10 seconds (configurable via `SENTIMENT_API_TIMEOUT`)
- Batch size: 100 comments per request
- Fallback: Individual analysis on batch failures

**Sentiment API Client:**
- Located in `app/services/sentiment_api.py`
- Mock mode enabled when `SENTIMENT_API_URL` not configured
- Supports API key authentication via `MODAL_ML_API_KEY`
- Retry logic with exponential backoff for failed requests
- Handles multiple response formats from external service

### Migration Best Practices

**Creating Migrations:**
1. Modify models in `app/models.py`
2. Generate migration: `flask db migrate -m "Add field X to Y"`
3. Review generated migration in `migrations/versions/`
4. Test migration: `flask db upgrade` then `flask db downgrade`
5. Commit migration file to version control

**Railway Migrations:**
- Run via `python run_migration.py` (Railway-compatible script)
- Auto-runs on deployment if configured in Railway
- Checks database connectivity before running
- Logs migration status for debugging

## Development Workflow

1. **Feature Development:**
   - Create feature branch from `main`
   - Implement changes in appropriate service/route
   - Write tests for new functionality
   - Run `./run_local_tests.sh quick` during development
   - Run `./run_pre_push_tests.sh` before pushing

2. **Database Changes:**
   - Update models in `app/models.py`
   - Generate migration: `flask db migrate -m "Description"`
   - Test migration locally with upgrade/downgrade
   - Commit migration file

3. **Service Layer Changes:**
   - Modify service classes in `app/services/`
   - Keep services stateless and independent
   - Add unit tests in `tests/test_<service_name>.py`
   - Mock external dependencies in tests

4. **Frontend Changes:**
   - Edit React components in `frontend/src/`
   - Run `npm run web:dev` for hot reload
   - Run `npm run web:test` to verify tests pass
   - Build with `npm run web:build` before deploying

5. **Deployment:**
   - Push to `main` branch triggers Railway auto-deployment
   - Monitor logs: `railway logs`
   - Check health endpoint: `https://<app-url>/health`
   - Verify worker status in Railway dashboard

## Troubleshooting

**Redis Connection Errors:**
```bash
# Check if Redis is running
redis-cli ping  # Should return PONG

# Start Redis if not running
redis-server

# Check Redis connection from Python
python -c "import redis; r = redis.from_url('redis://localhost:6379'); print(r.ping())"
```

**Database Migration Issues:**
```bash
# Reset migration state
flask db stamp head

# Force migration to specific version
flask db upgrade <revision_id>

# Check current migration version
flask db current
```

**Worker Not Processing Jobs:**
```bash
# Check worker logs
tail -f worker.log

# Kill and restart worker
pkill -f analysis_worker.py
python analysis_worker.py

# Verify Redis queue
redis-cli LLEN rq:queue:default
```

**Modal API Timeout:**
- Check `SENTIMENT_API_URL` is correct
- Test endpoint: `curl <SENTIMENT_API_URL>/health`
- Increase timeout: Set `SENTIMENT_API_TIMEOUT=30` in environment
- Check Modal service status in Modal dashboard

**Railway Deployment Issues:**
- Check build logs: `railway logs --build`
- Verify environment variables set correctly
- Ensure database migrations ran: Check logs for "flask db upgrade"
- Health check failing: Verify `/health` endpoint accessible

## Additional Resources

- **README.md:** Full feature list, setup instructions, API documentation
- **Makefile:** Quick command reference
- **pytest.ini:** Test marker definitions
- **scripts/:** Utility scripts for data management, backups, testing
- **Railway Dashboard:** Monitor deployments, logs, metrics
- **Modal Dashboard:** Check ML service status and GPU usage
