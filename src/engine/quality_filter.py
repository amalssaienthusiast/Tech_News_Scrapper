"""
Source Quality and Time-Based Filtering Engine.

Ensures only high-quality, relevant, and timely content reaches the user.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import List, Optional

from src.core.types import Article, SourceTier
from src.core.protocol import SourceStatus, EventType
from src.core.events import event_bus

logger = logging.getLogger(__name__)


class SourceQualityFilter:
    """
    Advanced filter for source quality and time relevance.
    """
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self._source_reliability = {}  # Map source domain to reliability score (0.0 - 1.0)
    
    def filter_articles(self, articles: List[Article], max_age_hours: int = 24) -> List[Article]:
        """
        Filter articles based on strict time windows and quality checks.
        
        Args:
            articles: List of articles to filter
            max_age_hours: Maximum age in hours
            
        Returns:
            Filtered list of articles
        """
        filtered = []
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=max_age_hours)
        
        for article in articles:
            # 1. Strict Time Check
            if not self._is_timely(article, cutoff):
                continue
            
            # 2. Quality Check (Title length, content, etc.)
            if not self._is_quality_content(article):
                continue
                
            filtered.append(article)
            
        logger.info(f"Quality Filter: {len(articles)} -> {len(filtered)} articles")
        return filtered

    def _is_timely(self, article: Article, cutoff: datetime) -> bool:
        """Check if article is within acceptable time window."""
        # Prefer published_at, fall back to scraped_at
        timestamp = article.published_at or article.scraped_at
        
        if not timestamp:
            return False
            
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
            
        return timestamp >= cutoff

    def _is_quality_content(self, article: Article) -> bool:
        """Perform heuristic checks for content quality."""
        # Reject very short titles
        if len(article.title) < 10:
            return False
            
        # Reject generic titles (e.g. "Home", "Login")
        generic_terms = {"home", "login", "signup", "subscribe", "page not found"}
        if article.title.lower().strip() in generic_terms:
            return False
            
        return True

    def update_source_score(self, source_url: str, success: bool):
        """Update reliability score for a source."""
        # Simple moving average-like update
        current = self._source_reliability.get(source_url, 1.0)
        if success:
            new_score = min(1.0, current + 0.05)
        else:
            new_score = max(0.0, current - 0.2)  # Penalty is harsher
            
        self._source_reliability[source_url] = new_score
