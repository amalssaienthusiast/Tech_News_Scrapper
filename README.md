# Tech News Scraper

An enterprise-grade, AI-powered news aggregation system designed to scrape, analyze, and distribute technology news from multiple sources. Features sophisticated anti-bot bypass mechanisms, real-time capabilities, and intelligent content processing.

## Features

- **Multi-Source Aggregation**: Scrapes from RSS feeds, Google News, Bing News, NewsAPI, Reddit, Twitter/X, and more
- **AI-Powered Analysis**: LLM-based summarization, sentiment analysis, and disruption detection using Google Gemini
- **Anti-Bot Bypass**: Multi-layered bypass system including browser automation, proxy rotation, and stealth techniques
- **Real-Time Feeds**: WebSocket support for live news updates
- **Intelligent Deduplication**: Semantic deduplication using MinHash LSH and sentence transformers
- **Newsletter Generation**: Automated newsletter creation with editorial workflow
- **REST API**: FastAPI-based API with authentication and rate limiting
- **Resilience System**: Auto-healing, health monitoring, and fault tolerance

## Quick Start

### Prerequisites

- Python 3.8+
- pip or poetry
- (Optional) Redis for real-time features
- (Optional) Playwright for advanced bypass

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd tech_news_scraper
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright (optional, for bypass features):**
   ```bash
   playwright install
   ```

5. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Configuration

Create a `.env` file in the project root:

```env
# Required for basic functionality
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_custom_search_engine_id

# Optional - for AI features
GEMINI_API_KEY=your_gemini_api_key

# Optional - for additional sources
NEWSAPI_KEY=your_newsapi_key
BING_API_KEY=your_bing_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret

# Optional - for notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook

# Database (defaults to SQLite)
# DATABASE_URL=postgresql://user:pass@localhost/technews

# Redis (optional, for real-time features)
REDIS_URL=redis://localhost:6379/0
```

### Running the Application

**CLI Mode:**
```bash
python cli.py
```

**API Mode:**
```bash
python -m src.api.main
# Or with uvicorn directly:
uvicorn src.api.main:app --reload --port 8000
```

**GUI Mode:**
```bash
python gui/app.py
```

**Basic Scraper:**
```bash
python main.py
```

## Project Structure

```
tech_news_scraper/
├── src/
│   ├── api/              # FastAPI REST API & WebSocket endpoints
│   ├── bypass/           # Anti-bot & paywall bypass mechanisms
│   ├── core/             # Types, protocols, and exceptions
│   ├── engine/           # Core business logic (orchestrator, scrapers)
│   ├── intelligence/     # AI/ML processing (LLM summarization, sentiment)
│   ├── sources/          # External source integrations
│   ├── scrapers/         # Scraper implementations
│   ├── queue/            # Celery distributed task queue
│   ├── newsletter/       # Newsletter generation & publishing
│   ├── resilience/       # Auto-healing & fault tolerance
│   └── monitoring/       # Health checks & metrics
├── config/               # Configuration files
├── tests/                # Test suite
├── data/                 # Data storage (SQLite DB)
├── logs/                 # Log files
├── docs/                 # Documentation
├── cli.py                # Interactive TUI
├── main.py               # Main entry point
└── requirements.txt      # Python dependencies
```

## API Documentation

Once running, API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

- `POST /api/v1/search` - Search for tech news
- `GET /api/v1/articles` - List articles with filters
- `POST /api/v1/analyze` - Analyze a specific URL
- `GET /api/v1/sentiment` - Get sentiment analysis
- `GET /api/v1/health` - Health check
- `WS /ws` - WebSocket for real-time updates

## Architecture

### Core Components

1. **TechNewsOrchestrator** - Central coordinator managing all scraping operations
2. **DeepScraper** - Multi-layer content extraction with rate limiting
3. **QueryEngine** - Query intent classification and tech-relevance scoring
4. **AntiBotBypass** - Detection and bypass of anti-bot protections
5. **Database** - SQLite persistence with singleton pattern

### Data Flow

```
Sources → Scraper → Deduplicator → Analyzer → Database → API/Newsletter
                ↓
         Bypass (if blocked)
                ↓
         AI Intelligence (LLM)
```

## Development

### Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=src tests/
```

### Code Style

The project uses consistent code style. Please ensure your changes follow existing patterns:
- Type hints for function signatures
- Docstrings for public methods
- Async/await for I/O operations

### Database Migrations

The application uses SQLite with automatic schema creation. For production PostgreSQL:

```python
# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:pass@localhost/technews
```

## Troubleshooting

### Common Issues

**Import errors:**
Ensure you're running from the project root and using the virtual environment.

**Database locked:**
SQLite has concurrency limitations. For high-traffic scenarios, migrate to PostgreSQL.

**Bypass failures:**
Install Playwright and enable browser automation in config.

**API rate limits:**
Configure multiple API keys and enable fallback providers.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[License information here]

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in `docs/`
- Review API docs at `/docs` when running the server

## Roadmap

- [ ] PostgreSQL support for production scaling
- [ ] Kubernetes deployment configs
- [ ] GraphQL API endpoint
- [ ] Mobile app integration
- [ ] Advanced analytics dashboard
