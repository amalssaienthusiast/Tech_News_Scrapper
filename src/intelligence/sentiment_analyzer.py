"""
Sentiment Analyzer for Tech News Scraper v7.0

Provides real-time sentiment scoring for tech news articles:
- VADER-based sentiment scoring (-1 to +1)
- Per-topic and per-company sentiment tracking
- Rolling sentiment trends (24h/7d/30d)
- SQLite persistence for historical analysis

Integrates with existing news_classifier.py for topic detection.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================

class SentimentLabel(str, Enum):
    """Sentiment classification labels."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"
    
    @classmethod
    def from_score(cls, score: float) -> "SentimentLabel":
        """Convert sentiment score to label."""
        if score >= 0.5:
            return cls.VERY_POSITIVE
        elif score >= 0.15:
            return cls.POSITIVE
        elif score > -0.15:
            return cls.NEUTRAL
        elif score > -0.5:
            return cls.NEGATIVE
        else:
            return cls.VERY_NEGATIVE
    
    @property
    def emoji(self) -> str:
        """Get emoji for sentiment label."""
        mapping = {
            self.VERY_POSITIVE: "🚀",
            self.POSITIVE: "📈",
            self.NEUTRAL: "➖",
            self.NEGATIVE: "📉",
            self.VERY_NEGATIVE: "💥",
        }
        return mapping.get(self, "❓")
    
    @property
    def color(self) -> str:
        """Get hex color for sentiment label."""
        mapping = {
            self.VERY_POSITIVE: "#22c55e",  # Green
            self.POSITIVE: "#84cc16",       # Lime
            self.NEUTRAL: "#6b7280",        # Gray
            self.NEGATIVE: "#f97316",       # Orange
            self.VERY_NEGATIVE: "#ef4444",  # Red
        }
        return mapping.get(self, "#6b7280")


# Tech industry sentiment modifiers
TECH_SENTIMENT_WORDS = {
    # Positive tech indicators
    "breakthrough": 0.3,
    "innovation": 0.25,
    "revolutionary": 0.25,
    "launch": 0.15,
    "funding": 0.2,
    "partnership": 0.15,
    "growth": 0.2,
    "acquisition": 0.1,
    "milestone": 0.2,
    "record": 0.15,
    "success": 0.25,
    "profitable": 0.25,
    "upgrade": 0.1,
    "expansion": 0.15,
    "ai": 0.05,
    "blockchain": 0.05,
    
    # Negative tech indicators
    "layoff": -0.3,
    "downturn": -0.25,
    "hack": -0.35,
    "breach": -0.4,
    "lawsuit": -0.25,
    "investigation": -0.2,
    "decline": -0.2,
    "crash": -0.35,
    "vulnerability": -0.3,
    "exploit": -0.3,
    "fine": -0.2,
    "antitrust": -0.15,
    "shutdown": -0.25,
    "bankruptcy": -0.4,
    "scandal": -0.35,
}


# =============================================================================
# DATA MODELS
# =============================================================================

class SentimentResult(BaseModel):
    """Sentiment analysis result for a single article."""
    # Core metrics
    score: float = Field(description="Sentiment score from -1.0 to 1.0")
    magnitude: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence/intensity")
    label: SentimentLabel = Field(description="Categorical label")
    
    # Breakdown
    positive_score: float = Field(default=0.0)
    negative_score: float = Field(default=0.0)
    neutral_score: float = Field(default=0.0)
    
    # Context
    topics: Dict[str, float] = Field(default_factory=dict, description="Per-topic sentiment")
    companies: Dict[str, float] = Field(default_factory=dict, description="Per-company sentiment")
    keywords_detected: List[str] = Field(default_factory=list)
    
    # Metadata
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model_version: str = Field(default="vader_tech_1.0")


class SentimentTrend(BaseModel):
    """Sentiment trend over a time period."""
    topic: str = Field(description="Topic or 'overall'")
    period: str = Field(description="24h, 7d, 30d")
    
    avg_score: float = Field(description="Average sentiment score")
    score_change: float = Field(description="Change from previous period")
    article_count: int = Field(default=0)
    
    highest_article_id: Optional[str] = Field(default=None)
    lowest_article_id: Optional[str] = Field(default=None)
    
    trend_direction: str = Field(default="stable")  # up, down, stable


# =============================================================================
# SENTIMENT ANALYZER
# =============================================================================

class SentimentAnalyzer:
    """
    VADER-based sentiment analyzer optimized for tech news.
    
    Features:
    - VADER base sentiment analysis
    - Tech industry word modifiers
    - Company and topic extraction
    - Historical trend tracking
    - SQLite persistence
    
    Example:
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze(
            "OpenAI announces major breakthrough in AI capabilities"
        )
        print(f"Sentiment: {result.label.emoji} {result.score:.2f}")
        
        trends = analyzer.get_trends("AI", period="24h")
    """
    
    def __init__(self, database=None):
        """
        Initialize the sentiment analyzer.
        
        Args:
            database: Optional Database instance for persistence
        """
        self._db = database
        self._vader = None
        self._cache: Dict[str, SentimentResult] = {}
        
        # Initialize VADER (lazy load)
        self._init_vader()
        
        # Ensure schema
        self._ensure_schema()
        
        logger.info("SentimentAnalyzer initialized")
    
    def _init_vader(self):
        """Initialize VADER sentiment analyzer."""
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
            
            # Add tech-specific words to VADER lexicon
            for word, score in TECH_SENTIMENT_WORDS.items():
                self._vader.lexicon[word] = score * 4  # VADER uses -4 to 4 scale
            
            logger.info("VADER initialized with tech lexicon")
        except ImportError:
            logger.warning("NLTK not available, using basic sentiment analysis")
            self._vader = None
    
    def _get_db(self):
        """Get or create database connection."""
        if self._db is None:
            from src.database import Database
            self._db = Database()
        return self._db
    
    def _ensure_schema(self):
        """Ensure sentiment tables exist in database."""
        db = self._get_db()
        
        try:
            with db._get_connection() as conn:
                cursor = conn.cursor()
                
                # Article sentiment scores
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS article_sentiment (
                        article_id TEXT PRIMARY KEY,
                        score REAL NOT NULL,
                        magnitude REAL DEFAULT 0.0,
                        label TEXT,
                        positive_score REAL DEFAULT 0.0,
                        negative_score REAL DEFAULT 0.0,
                        neutral_score REAL DEFAULT 0.0,
                        topics_json TEXT DEFAULT '{}',
                        companies_json TEXT DEFAULT '{}',
                        keywords_json TEXT DEFAULT '[]',
                        analyzed_at TEXT,
                        model_version TEXT DEFAULT 'vader_tech_1.0'
                    )
                """)
                
                # Daily aggregated trends
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sentiment_daily (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        topic TEXT DEFAULT 'overall',
                        avg_score REAL,
                        min_score REAL,
                        max_score REAL,
                        article_count INTEGER DEFAULT 0,
                        UNIQUE(date, topic)
                    )
                """)
                
                # Create indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sentiment_date ON article_sentiment(analyzed_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_daily_topic ON sentiment_daily(topic, date)"
                )
                
                conn.commit()
                
            logger.info("Sentiment schema ensured")
        except Exception as e:
            logger.error(f"Failed to create sentiment schema: {e}")
    
    def analyze(
        self,
        text: str,
        article_id: Optional[str] = None,
        topics: Optional[List[str]] = None,
        companies: Optional[List[str]] = None,
        persist: bool = True
    ) -> SentimentResult:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            article_id: Optional article ID for persistence
            topics: Pre-detected topics (otherwise auto-detected)
            companies: Pre-detected companies (otherwise auto-detected)
            persist: Whether to save to database
            
        Returns:
            SentimentResult with scores and metadata
        """
        if not text or not text.strip():
            return SentimentResult(
                score=0.0,
                label=SentimentLabel.NEUTRAL
            )
        
        # Check cache
        cache_key = f"{article_id or hash(text[:100])}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Base sentiment analysis
        if self._vader:
            scores = self._vader.polarity_scores(text)
            compound = scores['compound']
            pos = scores['pos']
            neg = scores['neg']
            neu = scores['neu']
        else:
            # Fallback: simple word counting
            compound, pos, neg, neu = self._basic_sentiment(text)
        
        # Detect tech keywords
        keywords = self._detect_keywords(text)
        
        # Extract topics if not provided
        if topics is None:
            topics = self._extract_topics(text)
        
        # Extract companies if not provided
        if companies is None:
            companies = self._extract_companies(text)
        
        # Calculate per-entity sentiment
        topic_sentiment = {t: compound for t in topics}
        company_sentiment = {c: compound for c in companies}
        
        # Create result
        result = SentimentResult(
            score=round(compound, 4),
            magnitude=round(max(pos, neg), 4),
            label=SentimentLabel.from_score(compound),
            positive_score=round(pos, 4),
            negative_score=round(neg, 4),
            neutral_score=round(neu, 4),
            topics=topic_sentiment,
            companies=company_sentiment,
            keywords_detected=keywords,
        )
        
        # Cache and persist
        self._cache[cache_key] = result
        
        if persist and article_id:
            self._save_result(article_id, result)
        
        return result
    
    def _basic_sentiment(self, text: str) -> Tuple[float, float, float, float]:
        """Basic sentiment without VADER."""
        text_lower = text.lower()
        
        pos_count = sum(1 for word, score in TECH_SENTIMENT_WORDS.items() 
                        if score > 0 and word in text_lower)
        neg_count = sum(1 for word, score in TECH_SENTIMENT_WORDS.items() 
                        if score < 0 and word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0, 0.0, 0.0, 1.0
        
        pos_ratio = pos_count / (total + 1)
        neg_ratio = neg_count / (total + 1)
        compound = (pos_ratio - neg_ratio)
        
        return compound, pos_ratio, neg_ratio, 1 - pos_ratio - neg_ratio
    
    def _detect_keywords(self, text: str) -> List[str]:
        """Detect sentiment-relevant keywords."""
        text_lower = text.lower()
        found = []
        
        for word in TECH_SENTIMENT_WORDS.keys():
            if word in text_lower:
                found.append(word)
        
        return found[:10]  # Limit to top 10
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract tech topics from text."""
        text_lower = text.lower()
        topics = []
        
        topic_keywords = {
            "AI": ["artificial intelligence", "machine learning", "neural", "gpt", "llm", "openai", "ai "],
            "Cybersecurity": ["hack", "breach", "security", "vulnerability", "cyber", "malware"],
            "Cloud": ["aws", "azure", "google cloud", "cloud computing", "kubernetes", "docker"],
            "Crypto": ["bitcoin", "crypto", "blockchain", "ethereum", "nft", "web3"],
            "Startups": ["startup", "funding", "series a", "venture", "vc ", "unicorn"],
            "Hardware": ["chip", "processor", "gpu", "nvidia", "intel", "amd", "device"],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_companies(self, text: str) -> List[str]:
        """Extract company names from text."""
        companies = []
        
        # Common tech companies
        company_patterns = [
            "OpenAI", "Google", "Microsoft", "Apple", "Amazon", "Meta",
            "Tesla", "NVIDIA", "AMD", "Intel", "IBM", "Oracle", "Salesforce",
            "Twitter", "Uber", "Airbnb", "Stripe", "SpaceX", "Anthropic",
            "Netflix", "Spotify", "Adobe", "GitHub", "Slack", "Zoom",
        ]
        
        for company in company_patterns:
            if company.lower() in text.lower() or company in text:
                companies.append(company)
        
        return companies[:5]  # Limit to top 5
    
    def _save_result(self, article_id: str, result: SentimentResult) -> bool:
        """Save sentiment result to database."""
        import json
        
        db = self._get_db()
        
        try:
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO article_sentiment
                    (article_id, score, magnitude, label, positive_score, 
                     negative_score, neutral_score, topics_json, companies_json,
                     keywords_json, analyzed_at, model_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id,
                    result.score,
                    result.magnitude,
                    result.label.value,
                    result.positive_score,
                    result.negative_score,
                    result.neutral_score,
                    json.dumps(result.topics),
                    json.dumps(result.companies),
                    json.dumps(result.keywords_detected),
                    result.analyzed_at.isoformat(),
                    result.model_version
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save sentiment: {e}")
            return False
    
    def get_sentiment(self, article_id: str) -> Optional[SentimentResult]:
        """Get stored sentiment for an article."""
        import json
        
        db = self._get_db()
        
        try:
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM article_sentiment WHERE article_id = ?",
                    (article_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return SentimentResult(
                    score=row['score'],
                    magnitude=row['magnitude'],
                    label=SentimentLabel(row['label']),
                    positive_score=row['positive_score'],
                    negative_score=row['negative_score'],
                    neutral_score=row['neutral_score'],
                    topics=json.loads(row['topics_json'] or '{}'),
                    companies=json.loads(row['companies_json'] or '{}'),
                    keywords_detected=json.loads(row['keywords_json'] or '[]'),
                    analyzed_at=datetime.fromisoformat(row['analyzed_at']) if row['analyzed_at'] else datetime.now(UTC),
                    model_version=row['model_version'],
                )
        except Exception as e:
            logger.error(f"Failed to get sentiment: {e}")
            return None
    
    def get_trends(
        self,
        topic: str = "overall",
        period: str = "24h"
    ) -> SentimentTrend:
        """
        Get sentiment trends for a topic over a period.
        
        Args:
            topic: Topic name or "overall"
            period: "24h", "7d", or "30d"
            
        Returns:
            SentimentTrend with averages and changes
        """
        import json
        
        # Calculate date range
        now = datetime.now(UTC)
        if period == "24h":
            start = now - timedelta(hours=24)
            prev_start = now - timedelta(hours=48)
        elif period == "7d":
            start = now - timedelta(days=7)
            prev_start = now - timedelta(days=14)
        else:  # 30d
            start = now - timedelta(days=30)
            prev_start = now - timedelta(days=60)
        
        db = self._get_db()
        
        try:
            with db._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query based on topic
                if topic == "overall":
                    cursor.execute("""
                        SELECT AVG(score) as avg_score, 
                               MIN(score) as min_score,
                               MAX(score) as max_score,
                               COUNT(*) as article_count
                        FROM article_sentiment
                        WHERE analyzed_at >= ?
                    """, (start.isoformat(),))
                else:
                    # Filter by topic
                    cursor.execute("""
                        SELECT AVG(score) as avg_score,
                               MIN(score) as min_score,
                               MAX(score) as max_score,
                               COUNT(*) as article_count
                        FROM article_sentiment
                        WHERE analyzed_at >= ?
                        AND topics_json LIKE ?
                    """, (start.isoformat(), f'%"{topic}"%'))
                
                row = cursor.fetchone()
                
                avg_score = row['avg_score'] or 0.0
                article_count = row['article_count'] or 0
                
                # Get previous period for comparison
                if topic == "overall":
                    cursor.execute("""
                        SELECT AVG(score) as avg_score
                        FROM article_sentiment
                        WHERE analyzed_at >= ? AND analyzed_at < ?
                    """, (prev_start.isoformat(), start.isoformat()))
                else:
                    cursor.execute("""
                        SELECT AVG(score) as avg_score
                        FROM article_sentiment
                        WHERE analyzed_at >= ? AND analyzed_at < ?
                        AND topics_json LIKE ?
                    """, (prev_start.isoformat(), start.isoformat(), f'%"{topic}"%'))
                
                prev_row = cursor.fetchone()
                prev_avg = prev_row['avg_score'] or 0.0
                
                score_change = avg_score - prev_avg
                
                # Determine trend direction
                if score_change > 0.05:
                    trend_direction = "up"
                elif score_change < -0.05:
                    trend_direction = "down"
                else:
                    trend_direction = "stable"
                
                return SentimentTrend(
                    topic=topic,
                    period=period,
                    avg_score=round(avg_score, 4),
                    score_change=round(score_change, 4),
                    article_count=article_count,
                    trend_direction=trend_direction,
                )
                
        except Exception as e:
            logger.error(f"Failed to get trends: {e}")
            return SentimentTrend(
                topic=topic,
                period=period,
                avg_score=0.0,
                score_change=0.0,
            )
    
    def get_topic_sentiment_summary(self) -> Dict[str, SentimentTrend]:
        """Get sentiment summary for all major topics."""
        topics = ["AI", "Cybersecurity", "Cloud", "Crypto", "Startups", "Hardware", "overall"]
        
        return {topic: self.get_trends(topic, "24h") for topic in topics}
    
    def analyze_batch(
        self,
        articles: List[Dict[str, Any]],
        text_field: str = "content",
        id_field: str = "id"
    ) -> List[SentimentResult]:
        """
        Analyze sentiment for a batch of articles.
        
        Args:
            articles: List of article dictionaries
            text_field: Field containing text to analyze
            id_field: Field containing article ID
            
        Returns:
            List of SentimentResult objects
        """
        results = []
        
        for article in articles:
            text = article.get(text_field, "") or article.get("title", "")
            article_id = article.get(id_field)
            
            result = self.analyze(text, article_id=article_id)
            results.append(result)
        
        logger.info(f"Analyzed batch of {len(results)} articles")
        return results
    
    def clear_cache(self):
        """Clear the analysis cache."""
        self._cache.clear()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_sentiment_analyzer: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create the global sentiment analyzer."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer
