"""
Ephemeral Article Store - In-memory storage with TTL for live feed mode.

This module provides a lightweight, memory-efficient article store designed
for live feed applications where articles don't need permanent persistence.

Features:
- In-memory storage with automatic TTL expiration
- Thread-safe operations
- Memory-bounded with configurable limits
- Bloom filter integration for URL deduplication
- Export functionality for user-saved articles
"""

import asyncio
import hashlib
import logging
import time
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class StorageMode(Enum):
    """Storage mode for the application."""
    EPHEMERAL = "ephemeral"      # In-memory only, articles expire
    PERSISTENT = "persistent"    # Full database storage
    HYBRID = "hybrid"            # In-memory articles + persistent dedup/cache


@dataclass
class EphemeralArticle:
    """Article with TTL metadata."""
    id: str
    title: str
    url: str
    source: str
    published: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    ai_summary: Optional[str] = None
    full_content: Optional[str] = None
    expires_at: float = 0.0  # Unix timestamp
    saved_by_user: bool = False  # User explicitly saved this
    
    def is_expired(self) -> bool:
        """Check if article has expired."""
        if self.saved_by_user:
            return False  # Never expire user-saved articles
        return time.time() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published,
            "scraped_at": self.scraped_at,
            "ai_summary": self.ai_summary,
            "full_content": self.full_content,
            "saved_by_user": self.saved_by_user,
        }


class EphemeralArticleStore:
    """
    In-memory article store with TTL expiration.
    
    Designed for live feed applications where articles are temporary
    and users explicitly save what they want to keep.
    
    Features:
    - Configurable TTL (default: 2 hours)
    - Memory limit (default: 1000 articles)
    - Automatic cleanup of expired articles
    - Thread-safe operations
    - Export functionality
    """
    
    def __init__(
        self,
        ttl_seconds: int = 7200,  # 2 hours default
        max_articles: int = 1000,
        cleanup_interval: int = 300,  # 5 minutes
    ) -> None:
        """
        Initialize the ephemeral store.
        
        Args:
            ttl_seconds: Time-to-live for articles in seconds
            max_articles: Maximum articles to keep in memory
            cleanup_interval: Interval for cleanup task in seconds
        """
        self.ttl_seconds = ttl_seconds
        self.max_articles = max_articles
        self.cleanup_interval = cleanup_interval
        
        # Storage - OrderedDict for LRU-style eviction
        self._articles: OrderedDict[str, EphemeralArticle] = OrderedDict()
        self._url_index: Dict[str, str] = {}  # url -> article_id
        self._saved_articles: Dict[str, EphemeralArticle] = {}  # User-saved
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Stats
        self._stats = {
            "added": 0,
            "expired": 0,
            "evicted": 0,
            "saved": 0,
        }
        
        logger.info(
            f"EphemeralArticleStore initialized: "
            f"TTL={ttl_seconds}s, max={max_articles}"
        )
    
    async def start(self) -> None:
        """Start the background cleanup task."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("EphemeralArticleStore cleanup task started")
    
    async def stop(self) -> None:
        """Stop the background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("EphemeralArticleStore stopped")
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired articles."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                expired_count = self._cleanup_expired()
                if expired_count > 0:
                    logger.debug(f"Cleaned up {expired_count} expired articles")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def _cleanup_expired(self) -> int:
        """Remove expired articles. Returns count removed."""
        with self._lock:
            expired_ids = [
                aid for aid, article in self._articles.items()
                if article.is_expired()
            ]
            
            for aid in expired_ids:
                article = self._articles.pop(aid, None)
                if article:
                    self._url_index.pop(article.url, None)
                    self._stats["expired"] += 1
            
            return len(expired_ids)
    
    def add_article(self, article: Dict[str, Any]) -> bool:
        """
        Add an article to the store.
        
        Args:
            article: Article dictionary with title, url, source required
        
        Returns:
            True if added, False if duplicate
        """
        url = article.get("url", "")
        
        with self._lock:
            # Check for duplicate
            if url in self._url_index:
                return False
            
            # Generate ID if not present
            article_id = article.get(
                "id",
                hashlib.md5(url.encode()).hexdigest()
            )
            
            # Create ephemeral article
            ephemeral = EphemeralArticle(
                id=article_id,
                title=article.get("title", ""),
                url=url,
                source=article.get("source", ""),
                published=article.get("published"),
                scraped_at=article.get("scraped_at", datetime.now(UTC).isoformat()),
                ai_summary=article.get("ai_summary"),
                full_content=article.get("full_content"),
                expires_at=time.time() + self.ttl_seconds,
            )
            
            # Evict oldest if at capacity
            while len(self._articles) >= self.max_articles:
                oldest_id, oldest = self._articles.popitem(last=False)
                if not oldest.saved_by_user:
                    self._url_index.pop(oldest.url, None)
                    self._stats["evicted"] += 1
                else:
                    # Don't evict saved articles, put back
                    self._articles[oldest_id] = oldest
                    self._articles.move_to_end(oldest_id)
                    break
            
            # Add new article
            self._articles[article_id] = ephemeral
            self._url_index[url] = article_id
            self._stats["added"] += 1
            
            return True
    
    def get_all_articles(self) -> List[Dict[str, Any]]:
        """Get all non-expired articles."""
        with self._lock:
            return [
                article.to_dict()
                for article in reversed(self._articles.values())
                if not article.is_expired()
            ]
    
    def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get article by ID."""
        with self._lock:
            article = self._articles.get(article_id)
            if article and not article.is_expired():
                return article.to_dict()
            return None
    
    def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get article by URL."""
        with self._lock:
            article_id = self._url_index.get(url)
            if article_id:
                return self.get_article(article_id)
            return None
    
    def has_url(self, url: str) -> bool:
        """Check if URL exists in store."""
        with self._lock:
            return url in self._url_index
    
    def save_article(self, article_id: str) -> bool:
        """
        Mark article as saved by user (won't expire).
        
        Args:
            article_id: Article ID to save
        
        Returns:
            True if saved, False if not found
        """
        with self._lock:
            article = self._articles.get(article_id)
            if article:
                article.saved_by_user = True
                self._saved_articles[article_id] = article
                self._stats["saved"] += 1
                return True
            return False
    
    def unsave_article(self, article_id: str) -> bool:
        """Remove saved status from article."""
        with self._lock:
            article = self._articles.get(article_id)
            if article:
                article.saved_by_user = False
                article.expires_at = time.time() + self.ttl_seconds
                self._saved_articles.pop(article_id, None)
                return True
            return False
    
    def get_saved_articles(self) -> List[Dict[str, Any]]:
        """Get all user-saved articles."""
        with self._lock:
            return [
                article.to_dict()
                for article in self._saved_articles.values()
            ]
    
    def export_articles(
        self,
        article_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Export articles for saving/download.
        
        Args:
            article_ids: Specific IDs to export, or None for all saved
        
        Returns:
            List of article dictionaries
        """
        with self._lock:
            if article_ids:
                return [
                    self._articles[aid].to_dict()
                    for aid in article_ids
                    if aid in self._articles
                ]
            else:
                return self.get_saved_articles()
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Basic text search in titles."""
        query_lower = query.lower()
        with self._lock:
            results = []
            for article in reversed(self._articles.values()):
                if article.is_expired():
                    continue
                if query_lower in article.title.lower():
                    results.append(article.to_dict())
                    if len(results) >= limit:
                        break
            return results
    
    def clear(self) -> int:
        """Clear all non-saved articles. Returns count cleared."""
        with self._lock:
            count = 0
            to_remove = [
                aid for aid, article in self._articles.items()
                if not article.saved_by_user
            ]
            for aid in to_remove:
                article = self._articles.pop(aid)
                self._url_index.pop(article.url, None)
                count += 1
            return count
    
    @property
    def article_count(self) -> int:
        """Get current article count."""
        with self._lock:
            return len(self._articles)
    
    @property
    def saved_count(self) -> int:
        """Get saved article count."""
        with self._lock:
            return len(self._saved_articles)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        with self._lock:
            return {
                **self._stats,
                "current_count": len(self._articles),
                "saved_count": len(self._saved_articles),
                "ttl_seconds": self.ttl_seconds,
                "max_articles": self.max_articles,
            }


# Singleton instance
_ephemeral_store: Optional[EphemeralArticleStore] = None


def get_ephemeral_store(
    ttl_seconds: int = 7200,
    max_articles: int = 1000,
) -> EphemeralArticleStore:
    """Get or create singleton EphemeralArticleStore."""
    global _ephemeral_store
    
    if _ephemeral_store is None:
        _ephemeral_store = EphemeralArticleStore(
            ttl_seconds=ttl_seconds,
            max_articles=max_articles,
        )
    
    return _ephemeral_store
