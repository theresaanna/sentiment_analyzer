# YouTube Sentiment Analyzer

A Flask web application that analyzes the sentiment of YouTube video comments using the YouTube Data API v3.

**GitHub Repository:** https://github.com/theresaanna/sentiment_analyzer

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
```

### Code Formatting

```bash
black app/
flake8 app/
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
