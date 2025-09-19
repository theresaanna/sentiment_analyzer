# YouTube Sentiment Analyzer (VibeCheckAI)

![Tests](https://img.shields.io/badge/tests-passing-green)
![Railway Deploy](https://img.shields.io/badge/Railway-Deployed-blueviolet)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A production-ready Flask web application that analyzes the sentiment of YouTube video and channel comments using advanced machine learning models. Features real-time analysis, comprehensive dashboards, and social media theme detection.

**GitHub Repository:** https://github.com/theresaanna/sentiment_analyzer

> **Note:** The sentiment analysis is powered by a separate microservice running on Modal cloud GPUs using state-of-the-art transformer models. See the [sentiment_ml_service](https://github.com/theresaanna/sentiment_ml_service) repository for ML implementation details.

## Features

### Core Functionality
- 📹 **YouTube Integration**: Extract and analyze videos/channels from various URL formats
- 💬 **Comment Analysis**: Fetch and analyze comments (2.5K free / 5K logged-in / 50K pro)
- 🤖 **Advanced ML Models**: Transformer-based sentiment analysis with confidence scoring
- 📊 **Rich Visualizations**: Interactive charts, word clouds, and sentiment distributions
- 🎯 **Social Media Themes**: Detect trends like mental health, relationships, career discussions
- ⚡ **Real-time Processing**: Asynchronous analysis with Redis queue management
- 🔐 **User Authentication**: Google OAuth integration with secure sessions
- 💳 **Subscription System**: Stripe integration for premium features
- 📈 **User Dashboard**: Track analysis history and manage saved results
- 🎨 **Modern UI**: Responsive design with Bootstrap 5 and custom animations

## Tech Stack

### Backend
- **Framework**: Flask with blueprints architecture
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for session management and queue processing
- **Task Queue**: Redis Queue (RQ) for asynchronous processing
- **ML Service**: Modal cloud deployment with GPU acceleration
- **Authentication**: Flask-Login with Google OAuth 2.0
- **Payments**: Stripe API for subscription management

### Frontend
- **UI Framework**: Bootstrap 5 with custom CSS
- **JavaScript**: Vanilla JS with modern ES6+ features
- **Visualizations**: Chart.js for interactive charts
- **Word Clouds**: Custom canvas-based implementation

### Infrastructure
- **Deployment**: Railway with automated CI/CD
- **Testing**: Pytest with 85%+ coverage
- **Monitoring**: Health checks and error tracking
- **Security**: CSRF protection, secure sessions, rate limiting

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- YouTube Data API key
- Google OAuth credentials
- Stripe API keys (for payment features)

### Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/theresaanna/sentiment_analyzer.git
cd sentiment_analyzer

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your credentials (see Environment Variables section)

# 5. Set up the database
flask db upgrade

# 6. Start Redis (in a separate terminal)
redis-server

# 7. Start the worker (in another terminal)
python analysis_worker.py

# 8. Run the application
python run.py
```

The application will be available at **http://localhost:5000**

## Environment Variables

### Required Variables

```bash
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development  # or production
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost/sentiment_analyzer

# Redis
REDIS_URL=redis://localhost:6379/0

# YouTube API
YOUTUBE_API_KEY=your-youtube-api-key

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# ML Service
MODAL_ML_BASE_URL=https://your-modal-endpoint.modal.run
SENTIMENT_API_URL=https://your-modal-endpoint.modal.run

# Stripe (Optional)
STRIPE_PUBLIC_KEY=your-stripe-publishable-key
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
```

### Optional Variables

```bash
# Performance
PRECOMPUTE_ANALYSIS_ON_PRELOAD=true
PRELOAD_ANALYSIS_LIMIT=2500

# Email (for notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

## Project Structure

```
sentiment_analyzer/
├── app/
│   ├── __init__.py             # Application factory with extensions
│   ├── config.py               # Configuration management
│   ├── models.py               # Database models (User, Analysis, etc.)
│   ├── cache.py                # Redis caching utilities
│   ├── auth/                   # Authentication blueprint
│   │   ├── routes.py           # Login, OAuth, subscription routes
│   │   └── forms.py            # Authentication forms
│   ├── main/                   # Main application blueprint
│   │   ├── routes.py           # Core analysis routes
│   │   ├── dashboard_routes.py # User dashboard
│   │   ├── analysis_queue_routes.py # Queue management
│   │   └── forms.py            # Analysis forms
│   ├── services/               # Business logic layer
│   │   ├── youtube_service.py  # YouTube API integration
│   │   ├── sentiment_api_service.py # ML service client
│   │   ├── analysis_service.py # Analysis orchestration
│   │   └── channel_service.py  # Channel analysis
│   ├── templates/              # Jinja2 templates
│   │   ├── analyze.html        # Main analysis page
│   │   ├── dashboard.html      # User dashboard
│   │   └── analysis_results.html # Results display
│   └── static/                 # CSS, JS, images
├── migrations/                 # Database migrations
├── tests/                      # Comprehensive test suite
├── scripts/                    # Utility scripts
├── analysis_worker.py          # Background job processor
├── railway.json                # Railway deployment config
├── requirements.txt            # Python dependencies
└── run.py                      # Application entry point
```

### Architecture Highlights

- **Service Layer**: Clean separation of business logic from routes
- **Queue Architecture**: Redis-based async processing for scalability
- **Database Models**: User management, analysis history, subscriptions
- **ML Integration**: RESTful API client for Modal-hosted ML service
- **Caching Strategy**: Multi-level caching for performance
- **Testing**: 85%+ test coverage with unit and integration tests

## Usage

### For Anonymous Users
1. Visit the homepage
2. Enter a YouTube video or channel URL
3. Click "Analyze Comments"
4. View real-time analysis progress
5. Explore sentiment charts, word clouds, and theme detection

### For Registered Users
1. Sign in with Google OAuth
2. Access your personal dashboard
3. View analysis history
4. Save and manage favorite analyses
5. Export results as JSON/CSV
6. Subscribe for premium features (higher limits, priority processing)

### Supported URL Formats

#### Videos
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://m.youtube.com/watch?v=VIDEO_ID`

#### Channels
- `https://www.youtube.com/channel/CHANNEL_ID`
- `https://www.youtube.com/@username`
- `https://www.youtube.com/c/channelname`

### Analysis Features

- **Sentiment Distribution**: Positive, negative, neutral percentages
- **Confidence Scores**: Model confidence for each prediction
- **Word Clouds**: Visual representation of common themes
- **Time-based Analysis**: Sentiment trends over time
- **Theme Detection**: Identifies social media discussion topics
- **Export Options**: Download results in multiple formats

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_routes.py
pytest tests/test_sentiment_api_service.py
pytest -m "not integration"  # Skip integration tests
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint
flake8 app/ tests/

# Type checking (if using)
mypy app/
```

### Database Management

```bash
# Create migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

### Local Development Tips

1. **Hot Reload**: Flask debug mode enables automatic reloading
2. **Test Data**: Use `scripts/generate_test_data.py` for sample data
3. **API Mocking**: Set `MOCK_SENTIMENT_API=true` for offline development
4. **Debug Mode**: Set `FLASK_DEBUG=1` for detailed error pages

## Deployment

### Production Architecture

The application is deployed on Railway with the following services:

1. **Web Service**: Main Flask application
2. **Worker Service**: Background job processor
3. **PostgreSQL**: Primary database
4. **Redis**: Cache and job queue
5. **Modal ML Service**: GPU-accelerated sentiment analysis

### Railway Deployment

#### Automated Deployment

```bash
# Deploy all services
./deploy_all.sh

# Deploy worker only
./deploy_worker.sh
```

#### Manual Setup

1. **Create Railway Project**
   ```bash
   railway login
   railway link [project-id]
   ```

2. **Add Services**
   - PostgreSQL: Add from Railway dashboard
   - Redis: Add from Railway dashboard
   - Web: Deploy from GitHub
   - Worker: Deploy with custom start command

3. **Configure Environment**
   - Copy variables from `.env.production.template`
   - Set production values in Railway dashboard
   - Enable health checks

### CI/CD Pipeline

#### GitHub Actions
- **Test Matrix**: Python 3.11, 3.12, 3.13
- **Services**: PostgreSQL and Redis for integration tests
- **Coverage**: Reports uploaded to artifacts
- **Security**: Secrets scanning and dependency checks

#### Railway Integration
- **Auto-deploy**: Pushes to main trigger deployment
- **Health Checks**: Ensures zero-downtime deployments
- **Rollback**: Automatic rollback on failures
- **Scaling**: Horizontal scaling for high traffic

### Monitoring

```bash
# View logs
railway logs

# Check service status
railway status

# Run production shell
railway run python
```

## API Documentation

### REST Endpoints

#### Public Endpoints
- `GET /` - Homepage
- `POST /analyze` - Start analysis (returns job ID)
- `GET /analysis/status/<job_id>` - Check analysis progress
- `GET /analysis/results/<job_id>` - Get analysis results

#### Authenticated Endpoints
- `GET /dashboard` - User dashboard
- `GET /api/analyses` - List user's analyses
- `DELETE /api/analyses/<id>` - Delete analysis
- `GET /api/export/<id>` - Export results

#### WebSocket Events
- `analysis_progress` - Real-time progress updates
- `analysis_complete` - Analysis completion notification

### External APIs

#### YouTube Data API v3
- Comment fetching with pagination
- Video/channel metadata
- Rate limit handling

#### Modal ML Service
- `POST /analyze` - Batch sentiment analysis
- `POST /analyze/themes` - Theme detection
- `GET /health` - Service health check

## Recent Features & Improvements

### Completed ✅
- [x] Full YouTube API integration with up to 50K comment support
- [x] Transformer-based sentiment analysis (RoBERTa)
- [x] Real-time analysis with progress tracking
- [x] Interactive visualizations (charts, word clouds)
- [x] Google OAuth authentication
- [x] User dashboard with history
- [x] Redis caching and queue management
- [x] CSV/JSON export functionality
- [x] Social media theme detection
- [x] Stripe payment integration
- [x] Channel analysis support
- [x] Mobile-responsive design
- [x] Production deployment on Railway

### Planned Enhancements 🚀
- [ ] Playlist batch analysis
- [ ] Sentiment trend predictions
- [ ] Multi-language support
- [ ] API rate limit dashboard
- [ ] Advanced filtering options
- [ ] Collaborative analysis sharing
- [ ] Email notifications
- [ ] Webhook integrations
- [ ] A/B testing for UI improvements

## Performance Optimization

### Caching Strategy
- **Redis**: 24-hour cache for YouTube data
- **In-memory**: Frequently accessed analysis results
- **Database**: Persistent storage with indexed queries

### Scalability
- **Horizontal scaling**: Multiple worker processes
- **Queue management**: Priority queues for subscribers
- **Rate limiting**: Prevents API abuse
- **CDN**: Static asset delivery (planned)

## Security

### Implemented Measures
- **CSRF Protection**: All forms protected
- **SQL Injection**: Parameterized queries via SQLAlchemy
- **XSS Prevention**: Template auto-escaping
- **Secure Sessions**: HTTPOnly cookies
- **Rate Limiting**: API and analysis endpoints
- **Input Validation**: Server-side validation

### Best Practices
- Regular dependency updates
- Security headers (CSP, HSTS)
- Environment variable encryption
- Audit logging for sensitive actions

## Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check Redis is running
   redis-cli ping
   # Should return: PONG
   ```

2. **Database Migration Issues**
   ```bash
   # Reset migrations
   flask db stamp head
   flask db migrate
   flask db upgrade
   ```

3. **Worker Not Processing Jobs**
   ```bash
   # Check worker logs
   tail -f worker.log
   # Restart worker
   pkill -f analysis_worker.py
   python analysis_worker.py
   ```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

### Development Process
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest`)
5. Commit changes (`git commit -m 'Add AmazingFeature'`)
6. Push to branch (`git push origin feature/AmazingFeature`)
7. Open a Pull Request

### Code Style
- Follow PEP 8
- Use Black for formatting
- Add type hints where applicable
- Write comprehensive docstrings

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **[YouTube Data API v3](https://developers.google.com/youtube/v3)** for video data access
- **[Hugging Face](https://huggingface.co/)** for transformer models
- **[Modal](https://modal.com/)** for GPU infrastructure and ML service hosting
- **[Railway](https://railway.app/)** for seamless deployment and application hosting
- **[Flask](https://flask.palletsprojects.com/)** community for the excellent framework
- **[Bootstrap](https://getbootstrap.com/)** team for UI components
- All contributors and users of VibeCheckAI

## Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/theresaanna/sentiment_analyzer/issues)
- **Discussions**: [Join the conversation](https://github.com/theresaanna/sentiment_analyzer/discussions)
