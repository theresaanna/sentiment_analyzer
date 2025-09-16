# YouTube Sentiment Analyzer

![Tests](https://github.com/theresaanna/sentiment_analyzer/actions/workflows/test.yml/badge.svg)
![Railway Deploy](https://img.shields.io/badge/Railway-Deployed-blueviolet)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A Flask web application that analyzes the sentiment of YouTube video comments using the YouTube Data API v3.

**GitHub Repository:** https://github.com/theresaanna/sentiment_analyzer

> **Note:** The sentiment analysis mechanisms are powered by a separate microservice that runs on Modal cloud GPUs. See the [sentiment_ml_service](https://github.com/theresaanna/sentiment_ml_service) repository for the machine learning implementation details.

## Features

- 📹 Extract video ID from various YouTube URL formats
- 💬 Fetch comments from YouTube videos (API integration ready)
- 📊 Perform sentiment analysis on comments (coming soon)
- 📈 Visualize sentiment distribution (coming soon)
- 🎨 Clean, modern, responsive UI with Bootstrap 5
- ✅ Form validation with WTForms
- 🔧 Environment-based configuration
- 📱 Fully responsive design

## Tech Stack

- **Backend**: Python 3.9+, Flask
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **APIs**: YouTube Data API v3
- **Deployment**: Gunicorn (production server)

## Quick Start

### Local Setup (macOS/Linux)

```bash
# 1. Clone the repository
cd /Users/theresa/PycharmProjects/sentiment_analyzer
# Or if cloning fresh:
# git clone https://github.com/theresaanna/sentiment_analyzer.git
# cd sentiment_analyzer

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your YouTube API key and Google OAuth credentials:
# YOUTUBE_API_KEY=your-actual-api-key-here
# GOOGLE_CLIENT_ID=your-google-client-id
# GOOGLE_CLIENT_SECRET=your-google-client-secret
# (Optional) OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback

# 5. Run the application
python run.py
```

The application will be available at **http://localhost:5000**

## Installation

### Prerequisites

- Python 3.9 or higher
- YouTube Data API key ([Get one here](https://console.cloud.google.com/))

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/sentiment_analyzer.git
cd sentiment_analyzer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your YouTube API key and Google OAuth credentials
# GOOGLE_CLIENT_ID=your-google-client-id
# GOOGLE_CLIENT_SECRET=your-google-client-secret
# (Optional) OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

5. Run the application:
```bash
python run.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
sentiment_analyzer/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration settings
│   ├── main/               # Main blueprint
│   │   ├── __init__.py
│   │   ├── routes.py       # Route handlers
│   │   └── forms.py        # WTForms definitions
│   ├── utils/              # Utility modules
│   │   ├── __init__.py
│   │   └── youtube.py      # YouTube URL parsing
│   ├── templates/          # HTML templates
│   │   ├── base.html       # Base template with navigation
│   │   ├── index.html      # Homepage with URL input form
│   │   ├── analyze.html    # Analysis results page
│   │   └── about.html      # About page
│   └── static/            # Static files
│       └── css/
│           └── style.css   # Custom styles
├── tests/                 # Test modules (to be added)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .env                  # Your local environment (not in git)
├── .gitignore           # Git ignore file
├── README.md            # This file
└── run.py              # Application entry point
```

### Key Components

- **Application Factory Pattern**: Clean Flask app initialization in `app/__init__.py`
- **Blueprints**: Modular route organization using Flask blueprints
- **Configuration Management**: Environment-based config in `app/config.py`
- **URL Parsing**: Robust YouTube URL parsing in `app/utils/youtube.py`
- **Form Validation**: WTForms with CSRF protection in `app/main/forms.py`
- **Responsive UI**: Bootstrap 5 templates with custom CSS

## Usage

1. Navigate to the homepage
2. Enter a YouTube video URL in the input field
3. Click "Analyze Comments"
4. View the extracted video ID (full analysis coming soon)

### Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://m.youtube.com/watch?v=VIDEO_ID`

## Development

### Running Tests

```bash
pytest tests/
# With coverage report
pytest --cov=app --cov-report=html
```

### Code Formatting

```bash
black app/
flake8 app/
```

## CI/CD Pipeline

### Continuous Integration and Testing

#### Railway Integrated Testing (Recommended)
Railway now runs unit tests directly during the build phase. If tests fail, the deployment is automatically aborted.

**Features:**
- Tests run automatically on every deployment
- No separate CI service needed
- Build fails fast if tests don't pass
- Integration tests can be skipped for faster builds

**Configuration:**
Tests are configured in `railway.json` and use `scripts/run_tests_railway.py`

**Environment Variables for Railway Testing:**
```bash
RAILWAY_SKIP_TESTS=false     # Set to true to skip all tests
SKIP_INTEGRATION_TESTS=true  # Skip tests requiring external services
RAILWAY_COVERAGE=false       # Set to true for coverage reports
```

#### GitHub Actions (Alternative)
You can also use GitHub Actions for testing before Railway deployment.

**Features:**
- **Multi-version testing**: Runs tests on Python 3.11, 3.12, and 3.13
- **Redis service**: Spins up Redis container for integration tests
- **Coverage reporting**: Generates test coverage reports
- **Dependency caching**: Speeds up builds by caching pip dependencies
- **Test artifacts**: Stores test results and coverage reports for 30 days

#### Setting up GitHub Secrets:
Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```yaml
YOUTUBE_API_KEY         # Your YouTube Data API key
GOOGLE_CLIENT_ID        # Google OAuth client ID
GOOGLE_CLIENT_SECRET    # Google OAuth client secret
STRIPE_PUBLIC_KEY       # Stripe publishable key (optional)
STRIPE_SECRET_KEY       # Stripe secret key (optional)
STRIPE_WEBHOOK_SECRET   # Stripe webhook secret (optional)
PAYPAL_CLIENT_ID        # PayPal client ID (optional)
PAYPAL_CLIENT_SECRET    # PayPal client secret (optional)
```

### Continuous Deployment with Railway

#### Railway Integration:
1. **Automatic deployments**: Railway automatically deploys when changes are pushed to `main`
2. **Check requirements**: Railway waits for all GitHub Actions tests to pass before deploying
3. **Health checks**: Railway performs health checks before marking deployment as successful

#### Setting up Railway:

1. **Connect GitHub repository**:
   - In Railway dashboard, create new project
   - Choose "Deploy from GitHub repo"
   - Select your repository

2. **Configure environment variables** in Railway:
   ```
   DATABASE_URL          # Automatically provided by Railway PostgreSQL
   REDIS_URL            # Automatically provided by Railway Redis
   YOUTUBE_API_KEY      # Your YouTube API key
   GOOGLE_CLIENT_ID     # Google OAuth credentials
   GOOGLE_CLIENT_SECRET
   SECRET_KEY           # Flask secret key
   # Add any other production environment variables
   ```

3. **Enable GitHub Checks** (Railway Settings):
   - Go to Settings → GitHub
   - Enable "Wait for CI checks"
   - Select required checks:
     - `Test Status Check`
     - `test (3.11)`
     - `test (3.12)`
     - `test (3.13)`

4. **Deployment flow**:
   ```
   Push to main → GitHub Actions run tests → Tests pass → Railway deploys → Health check → Live!
   ```

### Status Badges

Add these badges to show your CI/CD status:

```markdown
![Tests](https://github.com/theresaanna/sentiment_analyzer/actions/workflows/test.yml/badge.svg)
![Railway Deploy](https://img.shields.io/badge/Railway-Deployed-blueviolet)
```

## Next Steps for API Integration

The application is ready for YouTube API integration. To complete the setup:

1. **Get your YouTube API Key:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable YouTube Data API v3
   - Create credentials (API Key)
   - Add the key to your `.env` file

2. **Test the Application:**
   - Navigate to http://localhost:5000
   - Enter any YouTube URL
   - The app will extract and display the video ID
   - API integration will fetch comments in the next phase

## Future Enhancements

- [x] Extract video ID from YouTube URLs
- [x] Bootstrap UI with forms
- [ ] Complete YouTube API integration for fetching comments
- [ ] Implement sentiment analysis using TextBlob/VADER
- [ ] Add data visualization with charts
- [ ] Implement caching with Redis
- [ ] Add export functionality (CSV/JSON)
- [ ] Support for playlist analysis
- [ ] User authentication and saved analyses

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- YouTube Data API v3 for providing access to video data
- Flask community for the excellent web framework
- Bootstrap for the responsive UI components
