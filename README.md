# Tech News Scraper - Comprehensive Documentation

**Version:** 1.0.0  
**Python Version:** 3.8+  
**License:** [Add License Information]  
**Last Updated:** 2026-02-06

---

## Executive Summary

Tech News Scraper is an **enterprise-grade, AI-powered news aggregation system** designed to intelligently collect, analyze, and distribute technology news from hundreds of sources. It features sophisticated anti-detection mechanisms, real-time streaming capabilities, and machine learning-based content analysis using Google's Gemini LLM.

---

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
python run_qt.py
```

**Basic Scraper:**
```bash
python main.py
```



## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Configuration](#configuration)
5. [API Reference](#api-reference)
6. [Data Structures](#data-structures)
7. [Bypass System](#bypass-system)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)
10. [Development Guide](#development-guide)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TECH NEWS SCRAPER ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │   CLI TUI   │    │  FastAPI    │    │  C++ Qt GUI │    │  WebSocket  │    │
│  │   (cli.py)  │    │   Server    │    │  (gui_qt/)  │    │   Clients   │    │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    │
│         └────────────────────┴────────────────────┴────────────────┘          │
│                              │                                                │
│                              ▼                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │              TECH NEWS ORCHESTRATOR (src/engine/orchestrator.py)      │    │
│  │                  Central coordination layer                            │    │
│  └──────────────────────────────┬───────────────────────────────────────┘    │
│                                 │                                             │
│         ┌───────────────────────┼───────────────────────┐                     │
│         ▼                       ▼                       ▼                     │
│  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐               │
│  │QueryEngine  │        │ DeepScraper │        │URLAnalyzer  │               │
│  │ (Intent     │        │ (Multi-layer│        │ (Deep link  │               │
│  │  Analysis)  │        │  extraction)│        │  analysis)  │               │
│  └──────┬──────┘        └──────┬──────┘        └─────────────┘               │
│         │                      │                                              │
│         ▼                      ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                       BYPASS SYSTEM (src/bypass/)                      │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │    │
│  │  │AntiBotBypass│  │ContentPlatf │  │PaywallBypass│  │ ProxyManager │ │    │
│  │  │             │  │ormBypass    │  │             │  │              │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘ │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                 │                                             │
│                                 ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                   DATA STRUCTURES (src/data_structures/)               │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │    │
│  │  │ PriorityQueue│  │BloomFilter  │  │   LRUCache  │  │   Trie       │ │    │
│  │  │(Scheduling) │  │(Deduplicatn)│  │(Response   │  │(Keyword      │ │    │
│  │  │             │  │             │  │  caching)   │  │ matching)    │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘ │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                 │                                             │
│                                 ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                         DATABASE LAYER                                 │    │
│  │              SQLite (default) / PostgreSQL (production)                │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **HTTP Client** | `aiohttp` | Async HTTP requests |
| **HTML Parsing** | `beautifulsoup4` | Content extraction |
| **RSS Parsing** | `feedparser` | RSS/Atom feed handling |
| **Browser Automation** | `playwright` | Anti-bot bypass |
| **Web Framework** | `fastapi` | REST API |
| **AI/ML** | `google-generativeai` | LLM summarization |
| **Database** | `sqlite3` / `asyncpg` | Data persistence |
| **Rate Limiting** | Token Bucket | Request throttling |
| **Serialization** | `pydantic` | Data validation |

---

## Core Components

### 1. TechNewsOrchestrator (`src/engine/orchestrator.py`)

**Purpose:** Central coordination layer for all scraping operations.

**Key Responsibilities:**
- Query understanding and validation
- Multi-source deep scraping coordination
- URL analysis and ranking
- Source priority management
- Result aggregation and ranking

**Initialization Parameters:**
```python
TechNewsOrchestrator(
    enable_cache: bool = True,          # Enable HTTP response caching
    max_concurrent_scrapes: int = 5,    # Max parallel scraping operations
)
```

**Core Methods:**
- `search(query: str) -> SearchResult` - Main search interface
- `analyze_url(url: str) -> URLAnalysisResult` - Deep URL analysis
- `get_feed_status() -> FeedStatus` - Real-time feed monitoring

**Source Tier System:**
- **Tier 1** (Priority 0.25): Premium sources (TechCrunch, The Verge, Ars Technica, Wired, MIT Tech Review)
- **Tier 2** (Priority 0.50): High-quality sources (Hacker News, Engadget, Gizmodo, VentureBeat, ZDNet)
- **Tier 3** (Priority 0.75): Medium-quality sources
- **Tier 4** (Priority 1.00): Discovered/unverified sources

### 2. DeepScraper (`src/engine/deep_scraper.py`)

**Purpose:** Advanced multi-layer content extraction engine.

**Architecture:**
- **NO RSS SUPPORT** - Direct web scraping only
- Multi-layer link discovery algorithm
- Content quality scoring
- Source reputation tracking
- Async batch processing with rate limiting

**Key Classes:**

#### ContentExtractor
Intelligent HTML content extraction with:
- Paywall detection (returns None if content restricted)
- Sidebar/Related Post noise removal
- Density-based extraction
- Priority-ordered content selectors

**Content Selectors (Priority Order):**
```python
CONTENT_SELECTORS = [
    '[itemprop="articleBody"]',        # Schema.org markup
    '[property="articleBody"]',        # Open Graph
    'article .content',                 # Generic article
    'article .post-content',            # WordPress
    '[data-testid="postContent"]',     # Medium-specific
    'article[data-testid="postArticle"]',
    '.postArticle-content',
    'article',                           # Fallback
    '[role="main"]',                   # ARIA main
    'main',                              # HTML5 main
]
```

**Remove Selectors (Noise Reduction):**
```python
REMOVE_SELECTORS = [
    'script', 'style', 'noscript', 'iframe',
    'nav', 'header', 'footer', 'aside',
    '.advertisement', '.ad-slot', '.ads',
    '.social-share', '.share-buttons',
    '.comments', '.comment-section',
    '.related-posts', '.sidebar', '.widget',
    '.newsletter', '.subscription',
]
```

**Paywall Detection Indicators:**
- "subscribe to read"
- "subscribe to continue"
- "log in to continue"
- "premium content"
- "this article is for subscribers only"

### 3. QueryEngine (`src/engine/query_engine.py`)

**Purpose:** Intelligent query analysis and intent classification.

**Features:**
- Intent classification (search, analyze, discover, reject)
- Tech relevance scoring using ML and keyword matching
- Query expansion with synonyms and related terms
- Strict non-tech content rejection

**Query Types:**
```python
class QueryType(Enum):
    KEYWORD_SEARCH = auto()      # General tech keyword search
    URL_ANALYSIS = auto()        # Analyze specific URL
    SOURCE_DISCOVERY = auto()    # Find new sources
    TRENDING = auto()            # Get trending topics
    HELP = auto()                # Help/usage query
    UNKNOWN = auto()             # Cannot classify
```

**Tech Relevance Scoring:**
- Uses Trie-based TechKeywordMatcher for O(m) keyword lookup
- Tech threshold: 0.1 (configurable, lowered from 0.3)
- Non-tech indicators block queries (recipes, weather, sports, etc.)

**Tech Synonyms for Query Expansion:**
```python
TECH_SYNONYMS = {
    "ai": ["artificial intelligence", "machine learning", "deep learning"],
    "llm": ["large language model", "gpt", "chatgpt", "language model"],
    "ml": ["machine learning", "ai", "neural networks"],
    "programming": ["coding", "software development", "development"],
    "cybersecurity": ["security", "infosec", "cyber security", "hacking"],
    "cloud": ["cloud computing", "aws", "azure", "gcp"],
    "blockchain": ["crypto", "web3", "decentralized"],
}
```

### 4. TechNewsScraper (`src/scraper.py`)

**Purpose:** Main scraper module for RSS feeds and web pages.

**Features:**
- Async-capable web scraping (aiohttp)
- Concurrent HTTP requests with rate limiting
- Intelligent retry logic with exponential backoff
- Both RSS/Atom feeds and HTML page scraping

**Rate Limiting:**
```python
RATE_LIMIT_TOKENS_PER_SECOND = 2.0  # Refill rate
RATE_LIMIT_BUCKET_SIZE = 10         # Max burst capacity
SOURCE_SCRAPE_DELAY = 2.0          # Delay between sources
ARTICLE_SCRAPE_DELAY = 1.0         # Delay between articles
```

**Retry Logic:**
- Max retries: 3
- Initial delay: 5 seconds
- Exponential backoff (doubles each retry)
- Status 429 (rate limited): Wait 2x delay

---

## Data Flow

### Standard Scraping Flow

```
┌─────────────────┐
│  User Query or  │
│  Scheduled Job  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  QueryEngine    │────▶│  Intent Class.  │
│  (Validation)   │     └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  DeepScraper    │────▶│  Rate Limiter   │
│  (URL Fetch)    │     │  (Token Bucket) │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Anti-Bot       │────▶│  Playwright/    │
│  Detection?     │     │  Stealth Mode   │
└────────┬────────┘     └─────────────────┘
         │ No
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Paywall        │────▶│  Content Platf. │
│  Detected?      │     │  Bypass         │
└────────┬────────┘     │  (Medium/etc)   │
         │ No           └─────────────────┘
         ▼
┌─────────────────┐
│ ContentExtractor│
│ (HTML Parsing)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  AI Processor   │────▶│  Google Gemini  │
│  (Summarization)│     │  LLM API        │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  BloomFilter    │────▶│  MinHash LSH    │
│  (Deduplication)│     │  (Semantic)     │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│   Database      │
│  (SQLite/PG)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  API/Newsletter │────▶│  FastAPI/       │
│  Distribution   │     │  WebSocket      │
└─────────────────┘     └─────────────────┘
```

### Real-Time Feed Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    REAL-TIME FEED PIPELINE                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐                                            │
│  │  Scheduler  │  Triggers every CHECK_INTERVAL (3600s)     │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   Source    │───▶│   Source    │───▶│   Source    │      │
│  │   Queue     │    │   Queue     │    │   Queue     │      │
│  │ (Priority)  │    │ (Priority)  │    │ (Priority)  │      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘      │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ASYNC GATHER (max 5 concurrent)          │  │
│  └────────────────────────┬─────────────────────────────┘  │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐               │
│         ▼                 ▼                 ▼               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │   Article   │   │   Article   │   │   Article   │       │
│  │   Fetch     │   │   Fetch     │   │   Fetch     │       │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              PROCESSING PIPELINE                      │  │
│  │  Extract → AI Summary → Deduplicate → Store          │  │
│  └────────────────────────┬─────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              EVENT BROADCAST (WebSocket)              │  │
│  │  Connected clients receive new articles in real-time  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### File Locations

| File | Purpose | Format |
|------|---------|--------|
| `config/settings.py` | Main configuration module | Python |
| `config.yaml` | Application-level settings | YAML |
| `config/news_sources.json` | Source definitions | JSON |
| `config/industries.yaml` | Industry categories | YAML |
| `config/categories.yaml` | Content categories | YAML |
| `config/resilience.yaml` | Fault tolerance settings | YAML |
| `.env` | Environment variables | Dotenv |

### Core Settings (`config/settings.py`)

#### Directory Configuration
```python
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
LOGS_DIR: Path = BASE_DIR / "logs"
CACHE_DIR: Path = BASE_DIR / "cache"
SOURCES_DIR: Path = BASE_DIR / "discovered_sources"
```

#### Scraping Settings
```python
CHECK_INTERVAL: int = 3600          # 1 hour between scrape cycles
MAX_AGE_HOURS: int = 72             # Only fetch articles within 72 hours
MAX_RETRIES: int = 3                # Retry count for failed requests
RETRY_DELAY: int = 5                # Initial retry delay (doubles each retry)
MAX_WORKERS: int = 5                # Max concurrent scraping tasks
```

#### Rate Limiting
```python
SOURCE_SCRAPE_DELAY: float = 2.0      # Delay between sources (sync mode)
ARTICLE_SCRAPE_DELAY: float = 1.0     # Delay between articles (sync mode)
DISCOVERY_RATE_LIMIT: float = 2.0     # Discovery requests per second
RATE_LIMIT_TOKENS_PER_SECOND: float = 2.0  # Refill rate
RATE_LIMIT_BUCKET_SIZE: int = 10           # Max burst capacity
```

#### User Agent
```python
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
```

#### Tech Keywords (35+)
```python
TECH_KEYWORDS: List[str] = [
    "technology", "tech", "artificial intelligence", "AI", "machine learning",
    "software", "hardware", "cybersecurity", "blockchain", "cloud computing",
    "programming", "coding", "data science", "robotics", "IoT", "5G",
    "quantum computing", "virtual reality", "augmented reality", "startup",
    "innovation", "digital", "computer", "electronics", "semiconductor",
    "neural network", "deep learning", "automation", "API", "SaaS",
    "open source", "developer", "DevOps", "infrastructure", "microservices"
]
```

#### Discovery Configuration
```python
DISCOVERY_QUERIES: List[str] = [
    "latest technology news",
    "tech news websites",
    "artificial intelligence news",
    "software development news",
    "cybersecurity news today",
    "tech startups news",
    "programming news",
    "cloud computing updates",
    "machine learning articles",
    "data science blog",
]
```

#### Global Topics (20 topics)
```python
GLOBAL_TOPICS: List[str] = [
    "Artificial Intelligence", "Machine Learning", "Cybersecurity",
    "Blockchain", "Cloud Computing", "Data Science", "Internet of Things",
    "5G Technology", "Quantum Computing", "Virtual Reality",
    "Augmented Reality", "Robotics", "Software Engineering",
    "Web Development", "Mobile App Development", "DevOps",
    "Big Data", "Cryptocurrency", "Tech Startups", "Consumer Electronics",
]
```

#### Default Sources (Curated)
```python
DEFAULT_SOURCES: List[Dict[str, Any]] = [
    {
        "url": "https://techcrunch.com/feed/",
        "type": "rss",
        "name": "TechCrunch",
        "verified": True
    },
    {
        "url": "https://feeds.feedburner.com/thenextweb",
        "type": "rss",
        "name": "The Next Web",
        "verified": True
    },
    # ... more sources
]
```

### Application Settings (`config.yaml`)

```yaml
# Application Settings
app:
  name: "Tech News Scraper"
  version: "1.0.0"
  debug: false
  log_level: "INFO"

# Scraping Configuration
scraping:
  request_delay: 5           # Default request delay (seconds)
  max_concurrent: 3          # Maximum concurrent requests
  timeout: 30                # Request timeout (seconds)
  user_agent_rotation: true  # User agent rotation enabled
  blocked_domains:           # Sites that aggressively block
    - "analyticsindiamag.com"

# Refresh Settings
refresh:
  cooldown_seconds: 300      # 5 minutes between refreshes
  auto_refresh_interval: 0   # 0 = disabled

# Data Retention
retention:
  article_max_age_days: 30   # Maximum article age
  max_articles: 10000        # Maximum articles to keep
  cleanup_interval_hours: 24 # Clean frequency

# Redis Configuration (Optional)
redis:
  enabled: false
  url: "redis://localhost:6379/0"

# GUI Settings
gui:
  theme: "dark"
  width: 1400
  height: 900
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google Custom Search API key |
| `GOOGLE_CSE_ID` | Yes | Google Custom Search Engine ID |
| `GEMINI_API_KEY` | No | Google Gemini API for AI features |
| `NEWSAPI_KEY` | No | NewsAPI.org API key |
| `BING_API_KEY` | No | Bing Search API key |
| `REDDIT_CLIENT_ID` | No | Reddit API client ID |
| `REDDIT_CLIENT_SECRET` | No | Reddit API client secret |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot for notifications |
| `TELEGRAM_CHAT_ID` | No | Telegram chat ID |
| `DISCORD_WEBHOOK_URL` | No | Discord webhook for notifications |
| `DATABASE_URL` | No | PostgreSQL connection string |
| `REDIS_URL` | No | Redis connection string |

---

## API Reference

### FastAPI Application (`api/main.py`)

**Base URL:** `http://localhost:8000`

#### Feed Endpoints

**Start Feed**
```http
POST /api/feed/start
Content-Type: application/json

{
  "max_articles": 500,
  "max_age_hours": 48,
  "enable_discovery": true
}
```

**Stop Feed**
```http
POST /api/feed/stop
```

**Get Feed Status**
```http
GET /api/feed/status

Response:
{
  "running": true,
  "article_count": 42,
  "last_update": "2026-02-06T10:30:00",
  "sources_active": 10
}
```

#### Articles Endpoints

**List Articles**
```http
GET /api/articles?offset=0&limit=50&source=TechCrunch&tier=standard

Response:
[
  {
    "title": "...",
    "summary": "...",
    "url": "...",
    "source": "TechCrunch",
    "timestamp": "2026-02-06T10:00:00",
    "tech_score": 0.95,
    "tier": "standard",
    "topics": ["AI", "Machine Learning"]
  }
]
```

**Get Article Count**
```http
GET /api/articles/count

Response:
{
  "count": 42
}
```

#### Metrics Endpoints

**Get System Metrics**
```http
GET /api/metrics

Response:
{
  "cpu_percent": 15.2,
  "memory_percent": 45.8,
  "articles_processed": 150,
  "sources_active": 10,
  "errors_last_hour": 0,
  "uptime_seconds": 3600
}
```

#### Configuration Endpoints

**Get Config Section**
```http
GET /api/config/{section}

Response:
{
  "section": "scraping",
  "data": {
    "request_delay": 5,
    "max_concurrent": 3
  }
}
```

**Update Config Section**
```http
PUT /api/config/{section}
Content-Type: application/json

{
  "request_delay": 10
}
```

#### WebSocket Endpoint

**Real-Time Events**
```http
WS /ws/events

# Client -> Server
ping

# Server -> Client
pong

# New Article Event
{
  "type": "article",
  "data": {
    "title": "...",
    "summary": "...",
    "url": "...",
    "source": "...",
    "timestamp": "...",
    "tech_score": 0.95,
    "tier": "standard"
  }
}
```

#### Health Check

```http
GET /health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "running": true
}
```

---

## Data Structures

### 1. Priority Queue (`src/data_structures/priority_queue.py`)

**Time Complexity:**
- `push`: O(log n)
- `pop`: O(log n) amortized
- `peek`: O(1)
- `update_priority`: O(log n)

**Space Complexity:** O(n)

**Features:**
- Thread-safe (RLock)
- Lazy deletion for priority updates
- Stable sorting via counter

### 2. Bloom Filter (`src/data_structures/bloom_filter.py`)

**Purpose:** Probabilistic duplicate URL detection

**Properties:**
- False positive rate: configurable (default ~1%)
- False negative rate: 0%
- Memory efficient: ~10 bits per element

**Configuration:**
```python
expected_elements = 100_000
false_positive_rate = 0.01
```

### 3. LRU Cache (`src/data_structures/lru_cache.py`)

**Purpose:** HTTP response caching

**Time Complexity:**
- `get`: O(1)
- `put`: O(1)

**Features:**
- Thread-safe
- TTL support
- Automatic eviction

### 4. Trie (`src/data_structures/trie.py`)

**Purpose:** Fast tech keyword matching

**Time Complexity:**
- Insert: O(m) where m = word length
- Search: O(m)
- Prefix search: O(m + k) where k = results

**Features:**
- Case-insensitive matching
- Prefix suggestions
- Keyword counting

### 5. URL Deduplicator

**Purpose:** Semantic deduplication using MinHash LSH

**Technique:**
- Shingles: 3-grams
- Hash functions: 128
- Similarity threshold: 0.85

---

## Bypass System

### 1. AntiBotBypass (`src/bypass/anti_bot.py`)

**Purpose:** Detect and bypass anti-bot protections

**Detection Methods:**
- CAPTCHA indicators (recaptcha, hcaptcha, etc.)
- Challenge pages
- Bot detection scripts
- Rate limiting responses

**Bypass Strategies:**

#### Stealth Mode (Default)
```python
stealth_config = StealthConfig(
    user_agent_rotation=True,
    viewport_randomization=True,
    javascript_injection=True,
    fingerprint_randomization=True
)
```

#### Browser Automation
```python
# Using Playwright
browser = await playwright.chromium.launch(
    headless=True,
    args=['--disable-blink-features=AutomationControlled']
)
```

**Bypass Flow:**
1. Try regular HTTP request with stealth headers
2. If blocked (403/429/CAPTCHA), enable stealth mode
3. If still blocked, use browser automation (Playwright)
4. If paywall detected, invoke paywall bypass

### 2. ContentPlatformBypass (`src/bypass/content_platform_bypass.py`)

**Purpose:** Platform-specific content extraction

**Supported Platforms:**

| Platform | Detection Pattern | Strategy |
|----------|------------------|----------|
| Medium | `medium.com`, `towardsdatascience.com` | Playwright-first, scroll simulation |
| Substack | `substack.com` | API endpoint detection |
| Ghost | `ghost.io` | JavaScript rendering |
| Dev.to | `dev.to` | Direct API access |
| Hashnode | `hashnode.dev` | GraphQL API |

**Medium-Specific Extraction:**
```python
# Selectors for Medium
MEDIUM_SELECTORS = [
    '[data-testid="postContent"]',
    'article[data-testid="postArticle"]',
    '.postArticle-content',
    'article section',
]

# Scroll simulation for lazy-loaded content
await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
await page.wait_for_timeout(1000)
```

### 3. PaywallBypass (`src/bypass/paywall_bypass.py`)

**Purpose:** Detect and bypass paywalls

**Paywall Detection:**
- DOM analysis for paywall indicators
- Content length validation
- Keyword matching ("subscribe", "premium", etc.)

**Bypass Techniques:**
- Archive.org (Wayback Machine)
- Archive.today
- Textise dot iitty
- Reader mode simulation

**Paywall Indicators:**
```python
PAYWALL_INDICATORS = [
    'subscribe to read',
    'subscribe to continue',
    'log in to continue',
    'premium content',
    'this article is for subscribers only',
]
```

### 4. ProxyManager (`src/bypass/proxy_manager.py`)

**Purpose:** Rotate proxies for IP diversification

**Features:**
- Round-robin rotation
- Health checking
- Geographic targeting
- Authentication support

**Configuration:**
```python
proxy_manager.add_proxies_from_list([
    "http://user:pass@proxy1:8080",
    "http://proxy2:8080",
    "socks5://proxy3:1080"
])
```

---

## Deployment

### Prerequisites

- Python 3.8+
- pip or poetry
- (Optional) Redis 6.0+ for real-time features
- (Optional) PostgreSQL 12+ for production

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd tech_news_scraper

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright (for bypass features)
playwright install

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 6. Run verification
python tests/verify_system.py
```

### Running the Application

#### CLI Mode
```bash
python cli.py
```

#### API Mode
```bash
# Using module
python -m api.main

# Using uvicorn
uvicorn api.main:app --reload --port 8000 --host 0.0.0.0

# Production
uvicorn api.main:app --workers 4 --port 8000
```

#### GUI Mode
```bash
# Python GUI (if available)
python gui/app.py

# C++ Qt GUI
cd gui_qt && ./build/tech_news_gui
```

#### Basic Scraper
```bash
python main.py
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t tech-news-scraper .
docker run -p 8000:8000 --env-file .env tech-news-scraper
```

### Production Checklist

- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure Redis for real-time features
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log rotation
- [ ] Set up SSL/TLS
- [ ] Configure firewall rules
- [ ] Set up backups
- [ ] Configure rate limiting at load balancer
- [ ] Enable request caching
- [ ] Set up error tracking (Sentry)

---

## Troubleshooting

### Common Issues

#### Import Errors
**Symptom:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Ensure running from project root
cd /path/to/tech_news_scraper
python -m src.scraper

# Or set PYTHONPATH
export PYTHONPATH=/path/to/tech_news_scraper:$PYTHONPATH
```

#### Database Locked (SQLite)
**Symptom:** `sqlite3.OperationalError: database is locked`

**Causes:**
- Concurrent writes from multiple processes
- Long-running transactions
- SQLite's single-writer limitation

**Solutions:**
```python
# 1. Increase timeout
connection = sqlite3.connect('tech_news.db', timeout=30)

# 2. Enable WAL mode
cursor.execute('PRAGMA journal_mode=WAL')

# 3. Migrate to PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost/technews
```

#### Bypass Failures
**Symptom:** Content extraction fails with "Could not fetch content"

**Solutions:**
```bash
# 1. Install Playwright
playwright install

# 2. Enable browser automation in config
ENABLE_ANTI_BOT_BYPASS=true
USE_BROWSER_AUTOMATION=true

# 3. Check proxy configuration
PROXY_ENABLED=true
PROXY_LIST=["http://proxy:8080"]

# 4. Increase retry count
MAX_BYPASS_RETRIES=5
```

#### API Rate Limits
**Symptom:** `429 Too Many Requests` from APIs

**Solutions:**
```python
# 1. Configure multiple API keys
GOOGLE_API_KEY_1=...
GOOGLE_API_KEY_2=...

# 2. Enable fallback providers
ENABLE_FALLBACK_PROVIDERS=true

# 3. Increase delays
RATE_LIMIT_TOKENS_PER_SECOND=1.0
RETRY_DELAY=10
```

#### High Memory Usage
**Symptom:** Process consumes excessive memory

**Solutions:**
```python
# 1. Limit concurrent operations
MAX_WORKERS=3
max_concurrent_scrapes=3

# 2. Enable response caching
enable_cache=true

# 3. Reduce article retention
article_max_age_days=7
max_articles=5000

# 4. Run cleanup
python -c "from src.database import Database; db = Database(); db.cleanup_old_articles()"
```

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src tests/

# Specific test
pytest tests/test_bypass.py -v

# Debug specific issue
python tests/debug_medium.py
```

---

## Development Guide

### Code Style

- Type hints for function signatures
- Docstrings for public methods (Google style)
- Async/await for I/O operations
- Black formatting (line length 88)
- isort for imports

### Project Structure

```
tech_news_scraper/
├── api/                    # FastAPI REST API & WebSocket
│   ├── main.py            # Main FastAPI app
│   ├── events.py          # Event handlers
│   └── __init__.py
├── config/                # Configuration files
│   ├── settings.py        # Main config module
│   ├── config.yaml        # App settings
│   ├── news_sources.json  # Source definitions
│   ├── industries.yaml    # Industry categories
│   └── categories.yaml    # Content categories
├── gui_qt/                # C++ Qt GUI
├── src/
│   ├── api/               # API-specific logic
│   ├── bypass/            # Anti-bot mechanisms
│   │   ├── anti_bot.py
│   │   ├── content_platform_bypass.py
│   │   ├── paywall_bypass.py
│   │   └── proxy_manager.py
│   ├── core/              # Types, protocols, exceptions
│   │   ├── types.py
│   │   ├── exceptions.py
│   │   └── events.py
│   ├── data_structures/   # Efficient data structures
│   │   ├── priority_queue.py
│   │   ├── bloom_filter.py
│   │   ├── lru_cache.py
│   │   └── trie.py
│   ├── engine/            # Core business logic
│   │   ├── orchestrator.py
│   │   ├── deep_scraper.py
│   │   ├── query_engine.py
│   │   ├── url_analyzer.py
│   │   └── quality_filter.py
│   ├── intelligence/      # AI/ML processing
│   │   └── llm_client.py
│   ├── sources/           # External source integrations
│   ├── scrapers/          # Scraper implementations
│   ├── queue/             # Celery distributed task queue
│   ├── newsletter/        # Newsletter generation
│   ├── resilience/        # Auto-healing & fault tolerance
│   └── monitoring/        # Health checks & metrics
├── tests/                 # Test suite
├── data/                  # Data storage (SQLite DB)
├── logs/                  # Log files
├── docs/                  # Documentation
├── cli.py                 # Interactive TUI
├── main.py                # Main entry point
└── requirements.txt       # Python dependencies
```

### Adding a New Bypass Strategy

1. Create file in `src/bypass/`
2. Implement bypass class:
```python
class NewBypass:
    async def bypass(self, url: str) -> BypassResult:
        # Implementation
        return BypassResult(success=True, content=html)
```
3. Register in `DeepScraper`:
```python
if self.new_bypass.can_handle(url):
    result = await self.new_bypass.bypass(url)
```
4. Add tests in `tests/test_new_bypass.py`

### Adding a New Source

1. Edit `config/news_sources.json`:
```json
{
  "url": "https://example.com/feed",
  "type": "rss",
  "name": "Example Source",
  "verified": false,
  "tier": 3
}
```

2. Or use discovery:
```python
from src.discovery import WebDiscoveryAgent
agent = WebDiscoveryAgent(db)
new_sources = agent.discover_new_sources(query="example tech news")
```

### Database Schema

```sql
-- Articles table
CREATE TABLE articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    published TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ai_summary TEXT,
    full_content TEXT,
    tech_score REAL,
    tier TEXT DEFAULT 'standard',
    topics TEXT  -- JSON array
);

-- Sources table
CREATE TABLE sources (
    url TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'rss',
    verified BOOLEAN DEFAULT 0,
    tier INTEGER DEFAULT 3,
    article_count INTEGER DEFAULT 0,
    last_scraped TIMESTAMP,
    success_rate REAL DEFAULT 0.5
);

-- URL cache table
CREATE TABLE url_cache (
    url TEXT PRIMARY KEY,
    hash TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Performance Metrics

### Benchmarks

| Operation | Performance | Notes |
|-----------|-------------|-------|
| RSS Feed Parse | ~50 articles/sec | Depends on feed size |
| Web Page Scrape | ~5 pages/sec | With anti-bot bypass |
| AI Summarization | ~2 articles/sec | Gemini API latency |
| Deduplication | ~10,000 URLs/sec | Bloom filter |
| Semantic Deduplication | ~1,000 URLs/sec | MinHash LSH |
| Query Analysis | ~1,000 queries/sec | Trie-based matching |

### Resource Usage

| Component | Memory | CPU | Notes |
|-----------|--------|-----|-------|
| Idle | ~50 MB | <1% | Base process |
| Scraping | ~200 MB | 20-40% | With browser automation |
| AI Processing | ~100 MB | 10% | API-bound, not CPU |
| API Server | ~75 MB | <5% | Per worker |

### Optimization Tips

1. **Enable Response Caching**: Reduces redundant requests by 60-80%
2. **Use Async Mode**: 5-10x faster than synchronous scraping
3. **Limit Concurrent Operations**: Prevents rate limiting and memory issues
4. **Configure Bloom Filter**: Memory-efficient duplicate detection
5. **Use PostgreSQL**: Better concurrency than SQLite for high traffic

---

## Security Considerations

### Data Protection

- API keys stored in `.env` (never commit to git)
- `.env` in `.gitignore`
- Database file permissions: 600
- Log rotation to prevent disk fill

### Rate Limiting

- Token bucket algorithm prevents abuse
- Per-source rate limiting
- Global request throttling
- Automatic retry with backoff

### Content Safety

- HTML sanitization before storage
- XSS protection in API responses
- Content length limits
- Malicious URL detection

---

## Roadmap

### Version 1.1 (Planned)
- [ ] PostgreSQL support for production scaling
- [ ] Kubernetes deployment configs
- [ ] GraphQL API endpoint
- [ ] Advanced analytics dashboard

### Version 1.2 (Planned)
- [ ] Machine learning model for source quality prediction
- [ ] Automatic source discovery with ML
- [ ] Sentiment analysis improvements
- [ ] Multi-language support

### Version 2.0 (Future)
- [ ] Distributed scraping with Celery
- [ ] Real-time collaboration features
- [ ] Mobile app integration
- [ ] Blockchain-based content verification

---

## License

[Add License Information Here]

---

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in `docs/`
- Review API docs at `/docs` when running the server
- Email: [Add support email]

---

## Acknowledgments

- Built with Python 3.11
- Uses Google's Gemini for AI features
- FastAPI for API framework
- Playwright for browser automation
- SQLite/PostgreSQL for data storage

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-02-06  
**Maintainer:** [Add Maintainer Name]


## Architecture Updates

---
## Final Senior Architectural Breakdown

### **1. Core System Architecture**
The "Tech News Scraper" is a highly concurrent, multi-tier intelligence pipeline designed to aggregate, scrape, bypass anti-bot mechanisms, process, and serve tech news. It employs a hybrid language approach (Python + Rust) and a dual-backend database strategy to maximize throughput and flexibility.

#### A. **Orchestration & Asynchronous Event Loop**
- **The Brain**: `TechNewsOrchestrator` (`src/engine/orchestrator.py`) handles the lifecycle of discovery, scraping, and deep analysis.
- **Task Queues**: Scaling is managed by **Celery** (`src/queue/celery_app.py`), backed by **Redis**, to distribute workload across workers for parallel source scraping (`google`, `bing`, `newsapi`, `reddit`, etc.) and heavy deep-dive analysis.
- **GUI Bridge**: The PyQt6 UI operates on a distinct thread loop. It uses an `AsyncBridge` (`gui_qt/utils/async_bridge.py`) that marries QThreads with `asyncio`, keeping the UI perfectly responsive while heavy scraping or LLM extraction occurs in the background.

#### B. **Scraping & Paywall Bypass Engines**
A multi-layered defense penetration strategy ensures content is extracted even from highly fortified domains:
- **Rust Quantum Bypass**: `QuantumPaywallBypass` uses native Rust bindings (`src/bypass/lib.rs` via PyO3) for high-performance, TLS-fingerprint-randomized HTTP fetching.
- **Playwright Stealth Browser**: `StealthBrowserBypass` fires up a headless browser injected with anti-bot defeating scripts (mimicking human interactions, spoofing `navigator.webdriver`, intercepting API calls via `api_sniffer.py`).
- **Fallbacks**: If standard CSS selectors fail, `LLMContentExtractor` triggers, utilizing a local **Llama-3-8B-Q4** quantized model (via `llama_cpp`) to semantically strip headers, ads, and sidebars from raw HTML dumps.

#### C. **Intelligence & Processing Layer**
- **Semantic Search Engine**: Converts article titles/summaries into vector embeddings using **Sentence-BERT** (`all-MiniLM-L6-v2`) via HuggingFace `sentence_transformers`.
- **Abstractive Summarization**: Utilizes **DistilBART** (`sshleifer/distilbart-cnn-6-6`) for fast, local summarizations.
- **Multi-Method Deduplication**: Ensures data purity.
  - **Fuzzy Text Matching**: (`fuzzywuzzy`) for near-identical titles.
  - **URL Normalization**: Strips tracking IDs (`utm_source`, etc.).
  - **MinHash LSH**: (`datasketch`) Shingles article content into n-grams to detect heavily syndicated content across entirely different domains.

#### D. **Storage & State**
- **Database Engine**: Implements an async-first data layer (`src/db_storage/async_database.py`) using `asyncpg` (PostgreSQL) for production clusters and `aiosqlite` (SQLite) for localized setups. 
- **Analytics Schema**: Highly enriched schemas. `article_intelligence` table tracks LLM-assigned properties like `criticality`, `disruptive` flags, `affected_markets`, and `sentiment`.
- **Full Text Search**: Relies on PostgreSQL `GIN` indexing over `tsvector` types for instantaneous document search at scale.

---

### **2. Procedures for Recreating/Refactoring the Project**

If you need to recreate, refactor, or clone this architecture, execute these steps sequentially:

#### **Phase 1: Environment & Rust Infrastructure**
1. **Initialize Environments:** Setup a Python virtual environment and ensure `Cargo` (Rust) is installed.
2. **Compile the Bypass Engine:** 
   - Navigate to `src/bypass/` and write the `Cargo.toml`.
   - Compile `lib.rs` into a shared library using PyO3 (`maturin develop --release`). 
   - Integrate it into Python as `quantum_bypass`.
3. **Setup Redis & Celery:** Ensure Redis is running locally or via Docker to act as the Celery broker (`celery -A src.queue.celery_app worker`).

#### **Phase 2: Database & Storage**
1. **Implement Dual-Backend Async DB:** Build `async_database.py`. 
2. **Schema Generation:** Write the raw SQL migrations to build the tables (`articles`, `sources`, `article_intelligence`, `newsletters`).
3. **Indexing:** Apply `GIN` indexes and `tsvector` configs specifically for the PostgreSQL adapter to ensure full-text search scales.

#### **Phase 3: The Intelligence Pipeline**
1. **Local LLM Integrations:** Download quantized GGUF models (`Llama-3-8B-Q4`) and map them using `llama_cpp` for the `LLMContentExtractor`.
2. **Transformers Setup:** Initialize `SentenceTransformer` and `pipeline("summarization")` inside `ai_processor.py`. Cache these globally so they don't block the async loop.
3. **Deduplication Engine:** Implement `URLNormalizer`, Title string fuzzy matching, and MinHash LSH (`datasketch`) into the `DeduplicationEngine`.

#### **Phase 4: Orchestration & Concurrency**
1. **Build the Aggregator:** Code `DiscoveryAggregator` to handle the broad-stroke scraping (NewsAPI, Google, Bing, Reddit). 
2. **Celery Task Binding:** Wrap the broad-stroke scrapers into `@task` decorators inside `src/queue/tasks.py`. 
3. **TechNewsOrchestrator:** Map out the `TechNewsOrchestrator` to act as the main async switchboard, taking discovered URLs, throwing them at the Quantum Bypass, falling back to Playwright, pushing them through LLM Extraction, and inserting them into the database.

#### **Phase 5: User Interface**
1. **Qt Layout Setup:** Develop the main window in PyQt6.
2. **Async Bridge Integration:** Crucially, implement `AsyncBridge` (inheriting from `QThread`). Create a background `asyncio` event loop that talks to the `TechNewsOrchestrator` and signals the main UI thread via standard Qt Signals when new data is ready or scraped.

---
**End of Report.**