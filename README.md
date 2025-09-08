# YouTube Sentiment Analyzer

A Flask web application that analyzes the sentiment of YouTube video comments using the YouTube Data API v3.

## Features

- 📹 Extract video ID from various YouTube URL formats
- 💬 Fetch comments from YouTube videos (API integration pending)
- 📊 Perform sentiment analysis on comments
- 📈 Visualize sentiment distribution
- 🎨 Clean, modern, responsive UI with Bootstrap 5

## Tech Stack

- **Backend**: Python 3.9+, Flask
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **APIs**: YouTube Data API v3
- **Deployment**: Gunicorn (production server)

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
# Edit .env and add your YouTube API key
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
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── analyze.html
│   │   └── about.html
│   └── static/            # Static files
│       └── css/
│           └── style.css
├── tests/                 # Test modules
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore           # Git ignore file
├── README.md            # This file
└── run.py              # Application entry point
```

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

## Future Enhancements

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
