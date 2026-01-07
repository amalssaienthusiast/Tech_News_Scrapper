"""
Configuration settings for the Tech News Scraper application.

This module contains all configurable parameters for the application,
including paths, timing, API keys, and model settings. Environment
variables are used for sensitive values like API keys.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

# =============================================================================
# DIRECTORY CONFIGURATION
# =============================================================================

# Base directory (project root)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Directory paths
DATA_DIR: Path = BASE_DIR / "data"
LOGS_DIR: Path = BASE_DIR / "logs"
CACHE_DIR: Path = BASE_DIR / "cache"
SOURCES_DIR: Path = BASE_DIR / "discovered_sources"

# Create directories if they don't exist
for directory in [DATA_DIR, LOGS_DIR, CACHE_DIR, SOURCES_DIR]:
    directory.mkdir(exist_ok=True)

# =============================================================================
# FILE PATHS
# =============================================================================

# Legacy JSON files (kept for migration support)
OUTPUT_FILE: Path = DATA_DIR / "tech_news_ai.json"
DISCOVERED_SOURCES_FILE: Path = SOURCES_DIR / "discovered_sources.json"
URL_CACHE_FILE: Path = CACHE_DIR / "url_cache_ai.json"

# SQLite database file
DB_FILE: Path = DATA_DIR / "tech_news.db"

# =============================================================================
# SCRAPING SETTINGS
# =============================================================================

# Time intervals (in seconds)
CHECK_INTERVAL: int = 3600  # 1 hour between scrape cycles
MAX_AGE_HOURS: int = 72     # Only fetch articles within 72 hours
MAX_RETRIES: int = 3        # Retry count for failed requests
RETRY_DELAY: int = 5        # Initial retry delay (doubles each retry)
MAX_WORKERS: int = 5        # Max concurrent scraping tasks

# Rate limiting
SOURCE_SCRAPE_DELAY: float = 2.0      # Delay between sources (sync mode)
ARTICLE_SCRAPE_DELAY: float = 1.0     # Delay between articles (sync mode)
DISCOVERY_RATE_LIMIT: float = 2.0     # Discovery requests per second

# Token bucket rate limiter settings
RATE_LIMIT_TOKENS_PER_SECOND: float = 2.0  # Refill rate
RATE_LIMIT_BUCKET_SIZE: int = 10           # Max burst capacity

# User agent for HTTP requests
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# =============================================================================
# TECH KEYWORDS
# =============================================================================

# Keywords for source discovery and validation
TECH_KEYWORDS: List[str] = [
    "technology", "tech", "artificial intelligence", "AI", "machine learning",
    "software", "hardware", "cybersecurity", "blockchain", "cloud computing",
    "programming", "coding", "data science", "robotics", "IoT", "5G",
    "quantum computing", "virtual reality", "augmented reality", "startup",
    "innovation", "digital", "computer", "electronics", "semiconductor",
    "neural network", "deep learning", "automation", "API", "SaaS",
    "open source", "developer", "DevOps", "infrastructure", "microservices"
]

# =============================================================================
# DISCOVERY CONFIGURATION
# =============================================================================

# Search queries for discovering new tech news sources
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

# Global topics for auto-discovery
GLOBAL_TOPICS: List[str] = [
    "Artificial Intelligence",
    "Machine Learning",
    "Cybersecurity",
    "Blockchain",
    "Cloud Computing",
    "Data Science",
    "Internet of Things",
    "5G Technology",
    "Quantum Computing",
    "Virtual Reality",
    "Augmented Reality",
    "Robotics",
    "Software Engineering",
    "Web Development",
    "Mobile App Development",
    "DevOps",
    "Big Data",
    "Cryptocurrency",
    "Tech Startups",
    "Consumer Electronics",
]

# =============================================================================
# DEFAULT SOURCES
# =============================================================================

# Curated default sources (always available)
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
    {
        "url": "https://www.theverge.com/rss/index.xml",
        "type": "rss",
        "name": "The Verge",
        "verified": True
    },
    {
        "url": "https://www.wired.com/feed/rss",
        "type": "rss",
        "name": "Wired",
        "verified": True
    },
    {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "type": "rss",
        "name": "Ars Technica",
        "verified": True
    },
]

# =============================================================================
# AI MODEL SETTINGS
# =============================================================================

# Summarization model (HuggingFace)
SUMMARIZATION_MODEL: str = "sshleifer/distilbart-cnn-6-6"
SUMMARY_MAX_LENGTH: int = 100
SUMMARY_MIN_LENGTH: int = 30
MAX_CONTENT_FOR_SUMMARY: int = 1500

# Semantic search model (Sentence Transformers)
SEARCH_MODEL: str = "all-MiniLM-L6-v2"

# =============================================================================
# API KEYS (from environment variables)
# =============================================================================

# Google Custom Search API
# Get your API key: https://developers.google.com/custom-search/v1/overview
# Create CSE: https://programmablesearchengine.google.com/
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", "")

# Bing Search API
# Get your API key: https://www.microsoft.com/en-us/bing/apis/bing-web-search-api
BING_API_KEY: str = os.getenv("BING_API_KEY", "")

# =============================================================================
# GUI SETTINGS
# =============================================================================

GUI_WIDTH: int = 1200
GUI_HEIGHT: int = 800
STATS_UPDATE_INTERVAL: int = 5000   # 5 seconds
LOG_POLL_INTERVAL: int = 100        # 100ms

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")