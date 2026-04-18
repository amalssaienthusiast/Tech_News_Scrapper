# Tech News Scraper

> **Enterprise-grade, AI-powered news aggregation system** — scrapes, analyzes, and distributes technology news from hundreds of sources in real-time, with a Rust-powered bypass layer, a full-featured PyQt6 desktop dashboard, and a LangGraph-orchestrated newsletter pipeline.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-purple)](https://pypi.org/project/PyQt6/)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange)](https://ai.google.dev)

---

## Table of Contents

1. [Project Overview](#-project-overview)
2. [Feature Summary](#-feature-summary)
3. [System Architecture](#-system-architecture)
4. [Module Reference](#-module-reference)
 - [Sources](#sources---srcscources)
 - [Engine](#engine---srcengine)
 - [Bypass System](#bypass-system---srcbypass)
 - [Intelligence](#intelligence---srcintelligence)
 - [Feed Generator & Processing](#feed-generator--processing)
 - [Newsletter Pipeline](#newsletter-pipeline---srcnewsletter)
 - [Notifications](#notifications---srcnotifications)
 - [Real-Time Infrastructure](#real-time-infrastructure---srcrealtime)
 - [Distributed Queue](#distributed-queue---srcqueue)
 - [Search](#search---srcsearch)
 - [Resilience System](#resilience-system---srcresilience)
 - [Monitoring](#monitoring---srcmonitoring)
 - [Cache & Infrastructure](#cache--infrastructure)
 - [Security & Compliance](#security--compliance)
 - [Personalization](#personalization---srcpersonalization)
 - [Performance](#performance---srcperformance)
 - [Database Layer](#database-layer)
 - [REST API](#rest-api---srcapi)
 - [PyQt6 GUI Dashboard](#pyqt6-gui-dashboard---gui_qt)
5. [Quick Start](#-quick-start)
6. [Configuration Reference](#-configuration-reference)
7. [Running the Application](#-running-the-application)
8. [Project Structure](#-project-structure)
9. [Test Suite](#-test-suite)
10. [Dependencies](#-dependencies)
11. [Roadmap](#-roadmap)
12. [License](#-license)

---

## Project Overview

**Tech News Scraper** is a production-grade, modular news intelligence platform that continuously discovers, fetches, analyzes, personalizes, and distributes technology news. It was built across 10 development phases, growing from a basic RSS scraper into a full-stack AI news system.

### Key Highlights

| Capability | Detail |
|---|---|
| **Sources** | Google News, Bing News, NewsAPI, Reddit, Twitter/X, DuckDuckGo, Google Trends, RSS Feeds |
| **AI Analysis** | Google Gemini (via direct API + LangChain), DistilBART local fallback |
| **Bypass** | Rust-native compiled extension + TLS fingerprint impersonation via `curl-cffi` |
| **Real-Time** | Redis pub/sub + WebSocket + SSE dual delivery stack |
| **GUI** | Full PyQt6 dashboard with 7 live monitoring widgets |
| **Newsletter** | LangGraph-orchestrated AI writing pipeline |
| **API** | FastAPI REST API with auth, rate limiting, and OpenAPI docs |
| **Resilience** | Auto-healing source health monitor + deprecation manager |

---

## Feature Summary

- **Multi-Source Aggregation** — Fetches from 10+ sources including RSS, Google News RSS + API, Bing News API, NewsAPI.org (70k+ outlets), Reddit (tech subreddits), Twitter/X (Tweepy v2), DuckDuckGo (no API key), and Google Trends.
- **Advanced Anti-Bot Bypass** — High-performance Rust compiled extension (`advanced_web_scraper`) + TLS fingerprint randomization (JA3 spoofing) via `curl-cffi` + Playwright browser automation for Cloudflare bypass + proxy rotation + fake user-agent rotation.
- **AI-Powered Intelligence** — Google Gemini 1.5 Flash for market disruption analysis and news classification. LangChain wrapper for prompt chaining. Local DistilBART fallback for summarization with zero API cost.
- **25-Category News Classification** — Pre-defined taxonomy covering AI/ML, Cybersecurity, Cloud, Semiconductors, Quantum Computing, Robotics, Fintech, Blockchain, Space Tech, Healthcare, and more.
- **Sentiment Analysis** — Five-tier scoring (Very Positive → Very Negative) with emoji indicators and trend tracking.
- **Smart Deduplication** — Four-layer deduplication: exact URL match → fuzzy title similarity (FuzzyWuzzy) → MinHash LSH semantic hashing → cross-source story linking.
- **PyQt6 Desktop Dashboard** — Full-screen live monitor with 7 composited widgets including network throughput graph, pipeline visualizer, source activity matrix, and real-time article stream.
- **Newsletter Pipeline** — LangGraph state-machine workflow: `load_stories → editor_selects → writer_drafts → schedule_send`. Publishes to Beehiiv or Slack.
- **Email Digest** — SMTP-based personalized HTML email digests using Tokyo Night styling, scheduled daily/weekly.
- **REST API** — FastAPI endpoints for article search, retrieval, analysis, sentiment, and health. Built-in API key authentication and per-tier rate limiting.
- **Celery Distributed Queue** — Async tasks for source scraping, article analysis, feed refresh, and database maintenance.
- **Elasticsearch Full-Text Search** — Index creation, article ingestion, and query-builder with graceful fallback when ES is unavailable.
- **Resilience System** — Source health monitoring (HEALTHY/DEGRADED/UNHEALTHY), auto-fixer for common issues, deprecation manager, and warning orchestrator.
- **Prometheus Metrics** — Counter, Gauge, and Histogram metrics exposed at `/metrics` in Prometheus text format.
- **GDPR/CCPA Compliance** — Right-to-be-forgotten, data portability, consent management, and configurable retention policies.
- **Personalization Engine** — User preference-based article scoring connected to topic subscriptions and watchlists.
- **Redis Caching** — AI summary caching (saves API costs), rate-limit coordination across workers, pub/sub for live article distribution.

---

## System Architecture

```

 TECH NEWS SCRAPER v10.0 

 CLI TUI FastAPI PyQt6 GUI WebSocket/SSE 
 (cli.py) REST API Dashboard Clients 





 TechNewsOrchestrator 
 (src/engine/orchestrator.py) 





 Discovery DeepScraper Intelligence 
 Aggregator + Bypass (LLM/Sentiment) 
 (10 sources (Rust+TLS) (Gemini/Local) 





 Deduplication Engine (4-layer) 
 URL → Title Fuzzy → MinHash → Cross 



 Database (SQLite / PostgreSQL) 
 + Redis Cache + Elasticsearch Index 



 Output Layer 
 REST API WebSocket Newsletter 
 Email Digest Slack Telegram 

```

### Data Flow

```
Sources → Orchestrator → Bypass (if blocked) → DeepScraper
 → Deduplicator → AI Intelligence (Gemini/Local)
 → Database → Redis Pub/Sub → WebSocket / SSE / API
 → Newsletter Pipeline (LangGraph) → Beehiiv / Slack / Email
```

---

## Module Reference

### Sources — `src/sources/`

All source integrations implement a unified article format with automatic deduplication and rate-limit management.

| Module | Class | Description |
|---|---|---|
| `aggregator.py` | `DiscoveryAggregator` | Single-interface aggregator combining all sources. Handles automatic source selection based on available API keys. |
| `google_news.py` | `GoogleNewsClient` | 4 strategies: RSS feeds (free, 15-30min delay), Google Custom Search API (100 queries/day free), SerpAPI (real-time, paid), Google Trends for topic discovery. |
| `bing_news.py` | `BingNewsClient` | Bing News Search API (Azure). Real-time search, trending news, category-based queries. Free tier: 1000 queries/month. |
| `newsapi_client.py` | `NewsAPIClient` | NewsAPI.org integration. 70,000+ sources. Top headlines by country/category + full-archive search. Free: 100 requests/day. |
| `reddit_client.py` | `RedditClient` | Fetches trending posts from `r/technology`, `r/programming`, `r/machinelearning`, `r/artificial`, `r/startups`. Supports both PRAW (authenticated) and JSON API (unauthenticated). |
| `twitter_client.py` | `TwitterClient` | Twitter/X API v2 via Tweepy. App-only bearer token auth. Rate limit: 450 requests/15min for recent search. |
| `duckduckgo_search.py` | `DuckDuckGoClient` | No API key required. Uses `ddgs` library with exponential backoff to avoid 202 rate-limit errors. |
| `google_trends.py` | `GoogleTrendsClient` | `pytrends` integration for discovering trending tech topics and related query expansion. |
| `reddit_stream.py` | `RedditStream` | Real-time Reddit streaming for continuous updates. |
| `streaming_client.py` | `StreamingClient` | Generic streaming interface for continuous source monitoring. |

---

### Engine — `src/engine/`

| Module | Class | Description |
|---|---|---|
| `orchestrator.py` | `TechNewsOrchestrator` | Central coordinator. Manages all scraping operations, schedules source fetches, and routes articles through the full pipeline. |
| `deep_scraper.py` | `DeepScraper` | Multi-layer content extractor with built-in rate limiting, retry logic, and cache integration. Falls back through extraction methods. |
| `url_analyzer.py` | `URLAnalyzer` / `QueryEngine` | Query intent classification and tech-relevance scoring. Filters out non-tech URLs before full scraping. |
| `quality_filter.py` | `QualityFilter` | Post-processing filter to score article quality before storage. |
| `quantum_scraper.py` | `QuantumScraper` | Experimental high-concurrency parallelized scraper variant. |
| `conscious_filter.py` | `ConsciousFilter` | Context-aware content filtering with configurable rules. |
| `realtime_feeder.py` | `RealtimeFeeder` | Continuous live feed pusher that routes new articles to Redis pub/sub and connected clients. |
| `enhanced_feeder.py` | `EnhancedFeeder` | Extended feeder with additional pre-processing and enrichment steps. |
| `directory_scraper.py` | `DirectoryScraper` | Scraper for directory-style pages with CSS-selector driven extraction. |
| `scrape_queue.py` | `ScrapeQueue` | Internal async queue for managing in-flight scrape tasks. |
| `time_engine.py` | `TimeEngine` | Temporal scheduling engine for coordinating timed scrape intervals. |

---

### Bypass System — `src/bypass/`

The bypass system is a multi-layered stack for evading anti-bot protections on paywalled and bot-detecting sites.

| Module | Description |
|---|---|
| `advanced_bypass.py` | High-level orchestrator that selects the appropriate bypass strategy (Rust, TLS, Playwright, or fallback). |
| `tls_client.py` | **TLS Fingerprint Randomization** — Uses `curl-cffi` to impersonate Chrome/Firefox/Safari TLS signatures. Evades JA3-based bot detection. Supports HTTP/2, cookie jars, async sessions, and automatic browser rotation. |
| `target/` (Rust) | **Compiled Rust Extension** — `advanced_web_scraper` native library compiled via `maturin`. Provides maximum-performance, low-level HTTP scraping with zero Python overhead. Distributed as a macOS `.dylib` + Python `.whl`. |

**Bypass Strategies (in priority order):**
1. Rust native extension (fastest, lowest detection fingerprint)
2. TLS fingerprint impersonation via `curl-cffi`
3. Playwright browser automation (for Cloudflare/JS challenges)
4. Proxy rotation + fake user-agent headers
5. Standard `aiohttp` (fallback)

---

### Intelligence — `src/intelligence/`

| Module | Class | Description |
|---|---|---|
| `llm_provider.py` | `LLMProvider` | Abstract base class for all LLM backends. Supports `GEMINI`, `LANGCHAIN`, `LOCAL`, and `AUTO` provider types with automatic selection and fallback. |
| `llm_summarizer.py` | `LLMSummarizer` | Article summarization. Uses Gemini 1.5 Flash for rich summaries; falls back to DistilBART for free local inference. |
| `disruption_analyzer.py` | `DisruptionAnalyzer` | Market disruption analysis via LLM structured output. Returns `DisruptionAnalysis` (Pydantic model) with: `disruptive` (bool), `criticality` (1–10), `justification`, `affected_markets`, `affected_companies`, `sentiment`. |
| `sentiment_analyzer.py` | `SentimentAnalyzer` | Five-tier sentiment scoring: `VERY_POSITIVE `, `POSITIVE `, `NEUTRAL `, `NEGATIVE `, `VERY_NEGATIVE `. |
| `news_classifier.py` | `NewsClassifier` | 25-category taxonomy classification. Fast local keyword matching with LLM fallback. Categories configurable via YAML. |
| `alert_engine.py` | `AlertEngine` | Criticality-based alerting (1–10 score → `LOW/MEDIUM/HIGH/CRITICAL`). Supports GUI, Telegram, Discord, and Email channels. Built-in deduplication to suppress repeated alerts. |
| `custom_rules.py` | `CustomRulesEngine` | User-defined rules for custom filtering, categorization overrides, and alert triggers. |

**25 Built-in News Categories:**

| Group | Categories |
|---|---|
| Core Technology | Technology & Innovation, Artificial Intelligence, Machine Learning, Cybersecurity, Cloud Computing |
| Software & Platforms | Enterprise Software, Developer Tools, Open Source |
| Hardware & Infrastructure | Semiconductors, Consumer Electronics, Telecommunications |
| Emerging Tech | Quantum Computing, Robotics & Automation, AR/VR (Metaverse), Autonomous Vehicles, Space Tech |
| Finance & Business | Fintech & Payments, Blockchain/Crypto, Startups & Funding, Big Tech (FAANG+) |
| Vertical Markets | Healthcare Tech, Gov Tech, EdTech, SustainTech |

---

### Feed Generator & Processing

| Module | Class | Description |
|---|---|---|
| `src/feed_generator/deduplicator.py` | `FeedDeduplicator` | Four-layer article deduplication: exact URL → fuzzy title (FuzzyWuzzy Levenshtein) → MinHash LSH semantic hash → cross-source story linking. |
| `src/feed_generator/live_feed.py` | `LiveFeed` | Manages the active article feed buffer for live clients. |
| `src/processing/deduplication.py` | `DeduplicationEngine` | Deep deduplication engine with cross-source canonical version selection. |
| `src/crawler/crawler.py` | `WebCrawler` | Link-following crawler for deep article discovery. |
| `src/crawler/enhanced_crawler.py` | `EnhancedCrawler` | Crawler with JavaScript rendering support and DOM extraction. |
| `src/crawler/link_extractor.py` | `LinkExtractor` | Extracts and filters article URLs from crawled pages. |
| `src/extraction/api_sniffer.py` | `APISniffer` | Detects hidden API endpoints on paywalled sites for direct JSON extraction. |
| `src/extraction/llm_content_extractor.py` | `LLMContentExtractor` | Uses LLM to extract article content from complex DOM structures. |
| `src/extraction/medium_extractor.py` | `MediumExtractor` | Specialized extractor for Medium.com articles. |
| `src/extraction/multi_source_reconstructor.py` | `MultiSourceReconstructor` | Reconstructs full article from multiple partial source extractions. |

---

### Newsletter Pipeline — `src/newsletter/`

The newsletter system uses a **LangGraph** state-machine workflow for end-to-end AI-drafted newsletter generation.

```
load_stories → editor_selects_stories → writer_drafts_sections
 → generate_subject_lines → schedule_send → publish
```

| Module | Class | Description |
|---|---|---|
| `workflow.py` | `NewsletterWorkflow` | LangGraph `StateGraph` orchestrating the full pipeline. Uses `MemorySaver` for checkpoint resumption. |
| `state.py` | `NewsletterState` | Typed state model (`StorySelection`, `target_date`, draft sections, subject lines). |
| `editor.py` | `NewsletterEditor` | LLM-powered editorial selector. Ranks top stories by disruption score, sentiment, and diversity. |
| `writer.py` | `NewsletterWriter` | Generates structured newsletter sections (`headline`, `body`, `key_insight`) and subject lines via `LLMProvider`. Output: "Tech Intelligence Daily". |
| `scheduler.py` | `NewsletterScheduler` | APScheduler-based scheduling for daily/weekly automated sends. |
| `slack.py` | `SlackApprovalWorkflow` | Sends draft to a Slack channel for human approval before publishing via Slack SDK. |
| `state.py` | — | State types and `create_initial_state` factory. |
| `publishers/beehiiv.py` | `BeehiivPublisher` | Beehiiv REST API v2 integration. Creates draft posts, schedules sends, retrieves publication stats. |

---

### Notifications — `src/notifications/`

| Module | Class | Description |
|---|---|---|
| `email_digest.py` | `EmailDigestService` | SMTP email delivery with TLS. Sends HTML email digests styled with **Tokyo Night** theme. Supports personalization by topic subscriptions. Daily/weekly scheduling via APScheduler. |

**Supported Notification Channels (via Alert Engine):**
- **Email** — SMTP (Gmail, custom server)
- **Telegram** — Bot token + chat ID
- **Discord** — Webhook URL
- **Slack** — SDK + workspace token
- **GUI** — In-app toast / overlay alert

---

### Real-Time Infrastructure — `src/realtime/`

| Module | Class | Description |
|---|---|---|
| `websocket_server.py` | `WebSocketServer` | Push-based news delivery over WebSocket. Connection management, heartbeat, Redis pub/sub integration, message batching. Supports auto-reconnection. |
| `sse_server.py` | `SSEServer` | Server-Sent Events fallback for clients that don't support WebSocket. JSON event format, heartbeat keep-alive, per-channel filtering. Endpoint: `GET /events/stream` |
| `src/infrastructure/redis_event_bus.py` | `RedisEventBus` | Redis pub/sub event bus. Publishers (scrapers) → Redis channels → Subscribers (WebSocket/SSE servers). Channel schema: `news:all`, `news:breaking`, `news:topic:{name}`, `news:source:{id}`. |

---

### Distributed Queue — `src/queue/`

| Module | Description |
|---|---|
| `celery_app.py` | Celery factory configured with Redis broker. Start worker: `celery -A src.queue.celery_app worker`. Start beat: `celery -A src.queue.celery_app beat`. Gracefully degrades if Celery is not installed. |
| `tasks.py` | Task definitions: source scraping per-source, deep article analysis, feed refresh, and database maintenance/cleanup. |

---

### Search — `src/search/`

| Module | Class | Description |
|---|---|---|
| `elastic_client.py` | `ElasticsearchClient` | Elasticsearch 8.x client. Article index creation with proper mappings, ingestion, and search. Falls back gracefully when ES is unavailable. |
| `indexer.py` | `ArticleIndexer` | Manages incremental article indexing into Elasticsearch. |
| `query_builder.py` | `QueryBuilder` | Builds structured ES queries from natural language search parameters. |

---

### Resilience System — `src/resilience/`

| Module | Class | Description |
|---|---|---|
| `source_health.py` | `SourceHealthMonitor` | Tracks per-source success rate, average response time, consecutive failures, and articles per fetch. States: `HEALTHY`, `DEGRADED`, `UNHEALTHY`, `UNKNOWN`. |
| `auto_fixer.py` | `AutoFixer` | Self-healing system. Detects common issues (import errors, config drift, stale sources) and applies automated fixes. Issues classified by `IssueSeverity`: CRITICAL/HIGH/MEDIUM/LOW. |
| `deprecation_manager.py` | `DeprecationManager` | Tracks deprecated dependencies and APIs, emits warnings, and schedules replacements. |
| `warning_orchestrator.py` | `WarningOrchestrator` | Aggregates warnings from all subsystems and forwards to the alert engine based on severity thresholds. |

---

### Monitoring — `src/monitoring/`

| Module | Class | Description |
|---|---|---|
| `health_check_endpoints.py` | `HealthChecker` | Liveness (`GET /health`), readiness (`GET /health/readiness`), and detailed component-level health (`GET /health/detailed`) checks covering database, Redis, external APIs, and system resources via `psutil`. |
| `metrics_collector.py` | `MetricsCollector` | Prometheus-style metrics: Counter (request totals, errors), Gauge (queue sizes, active workers), Histogram (latencies). Custom metrics: LLM API cost, articles per source. Exported at `GET /metrics`. |
| `logging_configuration.py` | — | Centralized structured logging configuration for all subsystems. |

---

### Cache & Infrastructure

| Module | Class | Description |
|---|---|---|
| `src/cache/redis_cache.py` | `RedisCache` | AI summary caching (saves Gemini API costs), rate-limit coordination across workers, pub/sub for real-time article distribution, TTL-based expiration. |
| `src/db_storage/async_database.py` | `AsyncDatabase` | Async SQLite/PostgreSQL wrapper built on `aiosqlite`. |
| `src/db_storage/db_handler.py` | `DBHandler` | Synchronous database handler for compatibility with non-async contexts. |
| `src/db_storage/unified_storage.py` | `UnifiedStorage` | Abstraction layer supporting both SQLite (dev) and PostgreSQL (production). |
| `src/db_storage/migration.py` | `MigrationManager` | Schema versioning and database migration utilities. |
| `src/db_storage/ephemeral_store.py` | `EphemeralStore` | In-memory temporary storage for short-lived article states during pipeline processing. |
| `src/scheduler/task_scheduler.py` | `TaskScheduler` | APScheduler-based cron and interval-based scheduling for all periodic jobs. |

---

### Security & Compliance

| Module | Class | Description |
|---|---|---|
| `src/security/api_key_manager.py` | `SecureAPIKeyManager` | Secure API key loading from environment. Format validation via regex for: Google, Gemini, OpenAI, NewsAPI, Bing, SerpAPI, Reddit, Telegram, Discord. Safe masking for logs. |
| `src/compliance/data_privacy_manager.py` | `DataPrivacyManager` | GDPR/CCPA compliance: right-to-be-forgotten (Art. 17), data portability (Art. 20), configurable retention policies, consent management. |
| `src/compliance/data_anonymization.py` | `DataAnonymizer` | PII scrubbing and data anonymization utilities for exported datasets. |

---

### Personalization — `src/personalization/`

| Module | Class | Description |
|---|---|---|
| `engine.py` | `PersonalizationEngine` | Content-based recommendation scoring. Connects `UserPreferences` (topic subscriptions, watchlists, interests) to article relevance scoring and ranked feed filtering. |
| `src/user/preferences.py` | `UserPreferences` | User profile model with subscribed topics, blocked sources, keyword watchlists, and preferred categories. |

---

### Performance — `src/performance/`

| Module | Class | Description |
|---|---|---|
| `parallel_scraper.py` | `ParallelScraper` | `asyncio` + `aiohttp` concurrent HTTP scraper with configurable concurrency (default: 50 simultaneous requests), connection pooling, retry with exponential backoff, and compression support (Brotli). |
| `cache.py` | `PerformanceCache` | In-process LRU cache layer for frequently accessed articles and processed results. |

---

### Database Layer

| File | Description |
|---|---|
| `src/database.py` | Main `Database` class — SQLite singleton providing primary article persistence. Auto-creates schema on first run. Thread-safe with WAL mode. |
| `data/tech_news.db` | Production SQLite database file. |
| `live_feed.db` | Live feed database (real-time article buffer). |

For production deployments, set `DATABASE_URL` in `.env` to switch to PostgreSQL.

---

### REST API — `src/api/`

The FastAPI-based developer API with built-in auth, rate limiting, and OpenAPI documentation.

**Base URL:** `http://localhost:8000` 
**Docs:** `http://localhost:8000/docs` (Swagger UI) 
**ReDoc:** `http://localhost:8000/redoc`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/articles` | List articles with filters (source, category, date range, sentiment) |
| `POST` | `/api/v1/search` | Full-text article search |
| `POST` | `/api/v1/analyze` | Analyze and enrich a specific URL on demand |
| `GET` | `/api/v1/sentiment` | Aggregate sentiment statistics |
| `GET` | `/api/v1/categories` | List all categories with article counts |
| `GET` | `/api/v1/sources` | List monitored sources with health status |
| `GET` | `/health` | Basic liveness probe |
| `GET` | `/health/readiness` | Readiness probe (checks DB, Redis) |
| `GET` | `/health/detailed` | Full component health breakdown |
| `GET` | `/metrics` | Prometheus metrics export |
| `WS` | `/ws` | WebSocket connection for real-time article push |
| `GET` | `/events/stream` | SSE stream (WebSocket fallback) |

**Authentication:** API key via `X-API-Key` header. 
**Rate Limiting:** Configured per tier (free/pro/enterprise).

---

### PyQt6 GUI Dashboard — `gui_qt/`

Full-featured native desktop application built with PyQt6. Launch with:
```bash
python run_qt.py
```

#### Main Window — `gui_qt/app_qt_migrated.py`
Dark-themed main window with sidebar navigation, source filter combo box, category tabs, and article list panel. Includes Apple Silicon multi-threading fix (`import numpy` before Qt).

#### Widgets — `gui_qt/widgets/`

| Widget | Description |
|---|---|
| `live_monitor_overlay.py` | **Full-screen live monitor overlay (v8.0).** Composites 7 sub-widgets in a single QDialog: source heartbeat, article stream, activity log, statistics panel (8 metrics + trend arrows), pipeline visualizer, source matrix, network graph. |
| `live_activity_log.py` | Real-time color-coded log display. Levels: DEBUG (grey), INFO (blue), SUCCESS (green), WARNING (amber), ERROR (red). With timestamps, icons, auto-scroll, and max-entry limit. |
| `pipeline_visualizer.py` | 6-stage horizontal pipeline: `Discovery → Fetch → Process → Score → Filter → Display`. Visual progress indicators with color coding for active/completed stages. Animated transitions. |
| `source_activity_matrix.py` | Grid of all news sources with per-source progress bars, pulsing activity dot indicators, and success/failure counters. |
| `network_graph.py` | Real-time network throughput bar graph. Gradient-colored bars with live throughput metrics. PyQt6 `QPainter`-rendered. |
| `live_article_stream.py` | Scrollable live article stream preview panel with article cards and highlight animations. |
| `live_source_monitor.py` | Heartbeat-style source status monitor. Shows last-fetch time and health state for each source. |

#### Dialogs — `gui_qt/dialogs/`

| Dialog | Description |
|---|---|
| `article_viewer.py` | Full article content viewer. Displays complete article content with formatting, metadata (source, date, category, sentiment), and an "Open in Browser" button via `QDesktopServices`. |
| `sentiment_dialog.py` | Sentiment Dashboard dialog. Charts and statistics showing sentiment distribution across all fetched articles. Tabbed view with category breakdown and trend visualization. |

---

## Quick Start

### Prerequisites

- Python 3.8+
- pip
- (Optional) Redis — for real-time features, caching, and distributed queue
- (Optional) Playwright — for advanced Cloudflare bypass
- (Optional) Elasticsearch 8.x — for full-text search
- (Optional) Rust toolchain + `maturin` — to rebuild the Rust bypass extension

### Installation

**1. Clone the repository:**
```bash
git clone https://github.com/amalssaienthusiast/Tech_News_Scrapper.git
cd Tech_News_Scrapper
```

**2. Create a virtual environment:**
```bash
python -m venv env
source env/bin/activate # On Windows: env\Scripts\activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Install Playwright browsers (optional):**
```bash
playwright install chromium
```

**5. Copy and configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

---

## Configuration Reference

Create a `.env` file in the project root. All keys are optional unless marked **Required**.

```env
# 
# GOOGLE (Required for Google News + Search)
# 
GOOGLE_API_KEY=AIza... # Google Custom Search API key
GOOGLE_CSE_ID=your_cse_id # Custom Search Engine ID

# 
# AI / LLM
# 
GEMINI_API_KEY=your_gemini_api_key # Google Gemini 1.5 Flash

# 
# NEWS SOURCES
# 
NEWSAPI_KEY=your_newsapi_key # newsapi.org (free: 100 req/day)
BING_API_KEY=your_bing_api_key # Azure Bing News Search v7
REDDIT_CLIENT_ID=your_client_id # Reddit API (PRAW)
REDDIT_CLIENT_SECRET=your_secret
TWITTER_BEARER_TOKEN=your_token # Twitter/X API v2 bearer token
SERPAPI_KEY=your_serpapi_key # SerpAPI (paid, real-time Google)

# 
# NOTIFICATIONS
# 
TELEGRAM_BOT_TOKEN=123456:abc... # Telegram bot token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_BOT_TOKEN=xoxb-... # Slack SDK token

# 
# EMAIL DIGEST
# 
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your@gmail.com
SENDER_PASSWORD=your_app_password

# 
# NEWSLETTER (Beehiiv)
# 
BEEHIIV_API_KEY=your_beehiiv_key
BEEHIIV_PUBLICATION_ID=your_pub_id

# 
# DATABASE
# 
# Default: SQLite (no config needed)
# DATABASE_URL=postgresql://user:pass@localhost/technews

# 
# REDIS (optional)
# 
REDIS_URL=redis://localhost:6379/0

# 
# ELASTICSEARCH (optional)
# 
ELASTICSEARCH_URL=http://localhost:9200

# 
# API
# 
API_KEY=your_secret_api_key # For REST API authentication
```

---

## Running the Application

### PyQt6 GUI Dashboard
```bash
python run_qt.py
```

### Interactive CLI (TUI)
```bash
python cli.py
```

### FastAPI REST Server
```bash
uvicorn src.api.main:app --reload --port 8000
# Or:
python -m src.api.main
```

### Basic Scraper (headless)
```bash
python main.py
```

### Celery Worker (distributed queue)
```bash
celery -A src.queue.celery_app worker --loglevel=info
```

### Celery Beat Scheduler
```bash
celery -A src.queue.celery_app beat --loglevel=info
```

---

## Project Structure

```
tech_news_scraper/
 src/
 api/ # FastAPI REST API & WebSocket endpoints
 bypass/ # Anti-bot bypass (Rust extension + TLS + Playwright)
 target/ # Compiled Rust native library
 cache/ # Redis cache layer
 compatibility/ # Package shims and RSS adapters
 compliance/ # GDPR/CCPA data privacy management
 core/ # Types, protocols, exceptions, events
 crawler/ # Link-following web crawler
 data_structures/ # Article queue and custom data types
 db_storage/ # Async DB, migrations, unified storage
 discovery/ # Global source discovery system
 engine/ # Core orchestrator + scraper logic
 extraction/ # Content extractors (API sniffer, LLM, Medium)
 feed_generator/ # Live feed buffer + deduplicator
 infrastructure/ # Redis event bus
 intelligence/ # AI/ML: LLM, sentiment, disruption, classifier
 monitoring/ # Health checks + Prometheus metrics
 newsletter/ # LangGraph newsletter pipeline + Beehiiv publisher
 notifications/ # Email digest service
 operations/ # Diagnostic toolkit
 performance/ # Parallel scraper + LRU cache
 personalization/ # User preference-based scoring
 processing/ # Multi-method deduplication engine
 queue/ # Celery app + distributed task definitions
 realtime/ # WebSocket server + SSE server
 resilience/ # Auto-fixer, source health, deprecation manager
 scheduler/ # APScheduler task scheduling
 scrapers/ # Scraper implementations (RSS, API, Google News, factory)
 search/ # Elasticsearch client + indexer + query builder
 security/ # API key manager
 sources/ # All source integrations (10+ providers)
 user/ # User preferences model
 utils/ # Shared utilities
 database.py # Main SQLite singleton
 discovery.py # Legacy discovery module
 rate_limiter.py # Global rate limiter
 scraper.py # Legacy base scraper

 gui_qt/ # PyQt6 desktop dashboard
 app_qt_migrated.py # Main PyQt6 application window
 dialogs/
 article_viewer.py # Full article content viewer
 sentiment_dialog.py # Sentiment dashboard dialog
 widgets/
 live_monitor_overlay.py # Full-screen 7-widget live monitor
 live_activity_log.py # Color-coded real-time log
 live_article_stream.py # Live article stream panel
 live_source_monitor.py # Source heartbeat monitor
 network_graph.py # Network throughput bar graph
 pipeline_visualizer.py # 6-stage pipeline indicator
 source_activity_matrix.py # Source grid with progress bars
 theme.py # Color constants and font definitions

 api/ # Additional API configuration
 BOT_setup_telegram/ # Telegram bot setup scripts
 config/ # YAML configuration files
 data/ # SQLite databases
 docs/ # Additional documentation
 logs/ # Application log files
 tests/ # Full test suite (25 test files)

 cli.py # Interactive TUI (Rich-based)
 main.py # Headless scraper entry point
 run_qt.py # PyQt6 GUI launcher
 requirements.txt # All Python dependencies
 config.yaml # Application configuration
 .env.example # Environment variable template
 LICENSE # Proprietary license
```

---

## Test Suite

All tests live in `tests/`. Run with:

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src tests/

# Run specific module tests
pytest tests/test_bypass.py -v
pytest tests/test_resilience.py -v
pytest tests/test_rust_integration.py -v
```

| Test File | Coverage Area |
|---|---|
| `test_scraper.py` | Core scraper logic |
| `test_database.py` | Database CRUD and schema |
| `test_async_database.py` | Async DB operations |
| `test_ai_processor.py` | AI summarization and classification |
| `test_rate_limiter.py` | Rate limiting behavior |
| `test_bypass.py` | Bypass system unit tests |
| `test_live_bypass.py` | Live site bypass integration |
| `test_content_platform_bypass.py` | Content platform (Medium etc.) bypass |
| `test_integration_bypass.py` | End-to-end bypass pipeline |
| `test_rust_integration.py` | Rust extension bindings |
| `test_discovery.py` | Source discovery |
| `test_compatibility.py` | Package shim compatibility |
| `test_resilience.py` | Auto-fixer and health monitor |
| `test_realtime_logging.py` | Real-time log streaming |
| `test_gui_qt.py` | PyQt6 widget instantiation |
| `test_user_preferences.py` | User preference model |
| `test_directory_scraper_selectors.py` | CSS selector scraping |
| `test_medium_pipeline.py` | Medium.com extraction pipeline |
| `test_google_search_diagnostic.py` | Google Search API diagnostics |
| `test_neural_eraser.py` | Neural content filtering |
| `test_pdf_handling.py` | PDF content extraction |
| `performance_benchmark.py` | Scraper throughput benchmarks |
| `verify_system.py` | Full system health verification |
| `debug_medium.py` | Medium.com debug utilities |

---

## Dependencies

Key dependencies grouped by subsystem:

| Category | Packages |
|---|---|
| **HTTP / Scraping** | `aiohttp`, `requests`, `beautifulsoup4`, `feedparser`, `lxml`, `Brotli` |
| **Bypass** | `playwright`, `curl-cffi`, `fake-useragent`, `maturin` (Rust) |
| **AI / ML** | `google-generativeai`, `langchain-google-genai`, `langchain-core`, `transformers`, `sentence-transformers`, `torch` |
| **Newsletter** | `langgraph`, `slack-sdk`, `APScheduler` |
| **API / Realtime** | `fastapi`, `uvicorn`, `websockets`, `redis` |
| **Queue** | `celery` |
| **Search** | `elasticsearch` |
| **Deduplication** | `datasketch` (MinHash LSH), `fuzzywuzzy`, `python-Levenshtein` |
| **Sources** | `newsapi-python`, `google-api-python-client`, `praw`, `tweepy`, `ddgs`, `pytrends` |
| **GUI** | `PyQt6` |
| **Validation** | `pydantic>=2.0`, `PyYAML`, `python-dotenv` |
| **Monitoring** | `psutil`, `python-dateutil` |
| **Testing** | `pytest`, `pytest-asyncio`, `aioresponses` |

---

## Roadmap

- [x] Multi-source aggregation (RSS, Google, Bing, NewsAPI, Reddit, Twitter, DDG, Trends)
- [x] AI-powered analysis (Gemini + local fallback)
- [x] 25-category classification
- [x] Advanced bypass (Rust + TLS + Playwright)
- [x] Real-time delivery (WebSocket + SSE + Redis)
- [x] LangGraph newsletter pipeline
- [x] PyQt6 desktop dashboard with live monitoring
- [x] Resilience system and auto-healing
- [x] Prometheus metrics + health endpoints
- [x] GDPR/CCPA compliance module
- [ ] PostgreSQL production migration with full schema
- [ ] Kubernetes deployment manifests
- [ ] GraphQL API endpoint
- [ ] Mobile companion app (iOS/Android)
- [ ] Advanced analytics dashboard (Grafana integration)
- [ ] Multi-language news support

---

## License

This repository is proprietary. Permission is restricted to viewing the source code for educational purposes. See the [LICENSE](LICENSE) file for complete details.

**Copyright © 2026 amalssaienthusiast. All Rights Reserved.**