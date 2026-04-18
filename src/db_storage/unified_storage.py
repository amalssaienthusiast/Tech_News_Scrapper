"""
Unified Storage Manager - Switchable between Ephemeral, Persistent, and Hybrid modes.

This module provides a single interface for article storage that can be
configured to use different backends based on user preference.

Usage:
    from src.db_storage import get_storage_manager
    
    # Get manager (mode from config or env var)
    storage = await get_storage_manager()
    
    # Use unified API
    await storage.add_article(article)
    articles = await storage.get_all_articles()
    
    # Switch modes at runtime
    await storage.set_mode(StorageMode.EPHEMERAL)
"""

import asyncio
import json
import logging
import os
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.db_storage.ephemeral_store import (
    EphemeralArticleStore,
    StorageMode,
    get_ephemeral_store,
)

logger = logging.getLogger(__name__)


# Configuration file for storage settings
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
STORAGE_CONFIG_FILE = CONFIG_DIR / "storage_config.json"


class UnifiedStorageManager:
    """
    Unified storage interface with switchable modes.
    
    Modes:
    - EPHEMERAL: In-memory only, articles expire after TTL
    - PERSISTENT: Full PostgreSQL/SQLite storage
    - HYBRID: In-memory articles + persistent dedup/AI cache
    
    The mode can be changed at runtime via set_mode() or configuration.
    """
    
    def __init__(
        self,
        mode: StorageMode = StorageMode.HYBRID,
        ttl_seconds: int = 7200,
        max_articles: int = 1000,
    ) -> None:
        """
        Initialize unified storage manager.
        
        Args:
            mode: Initial storage mode
            ttl_seconds: TTL for ephemeral articles
            max_articles: Max articles in ephemeral store
        """
        self._mode = mode
        self._ttl_seconds = ttl_seconds
        self._max_articles = max_articles
        
        # Backends
        self._ephemeral: Optional[EphemeralArticleStore] = None
        self._persistent_db = None  # AsyncDatabaseManager
        self._initialized = False
        
        # Bloom filter for dedup (used in all modes)
        self._seen_urls: set = set()
        
        logger.info(f"UnifiedStorageManager created with mode: {mode.value}")
    
    async def initialize(self) -> None:
        """Initialize storage backends based on mode."""
        if self._initialized:
            return
        
        # Always create ephemeral store (used in EPHEMERAL and HYBRID)
        if self._mode in (StorageMode.EPHEMERAL, StorageMode.HYBRID):
            self._ephemeral = get_ephemeral_store(
                ttl_seconds=self._ttl_seconds,
                max_articles=self._max_articles,
            )
            await self._ephemeral.start()
        
        # Create persistent store if needed (PERSISTENT or HYBRID for cache)
        if self._mode in (StorageMode.PERSISTENT, StorageMode.HYBRID):
            try:
                from src.db_storage.async_database import get_async_database
                self._persistent_db = await get_async_database()
                
                # In HYBRID mode, load seen URLs from persistent store
                if self._mode == StorageMode.HYBRID:
                    await self._load_seen_urls()
                    
            except Exception as e:
                logger.warning(f"Persistent store unavailable: {e}")
                if self._mode == StorageMode.PERSISTENT:
                    raise
                # HYBRID mode can fall back to pure ephemeral
                logger.info("Falling back to ephemeral-only mode")
        
        self._initialized = True
        logger.info(f"UnifiedStorageManager initialized in {self._mode.value} mode")
    
    async def _load_seen_urls(self) -> None:
        """Load seen URLs from persistent store for dedup."""
        if self._persistent_db:
            try:
                articles = await self._persistent_db.get_all_articles()
                self._seen_urls = {a["url"] for a in articles}
                logger.info(f"Loaded {len(self._seen_urls)} URLs for dedup")
            except Exception as e:
                logger.warning(f"Could not load seen URLs: {e}")
    
    @property
    def mode(self) -> StorageMode:
        """Get current storage mode."""
        return self._mode
    
    async def set_mode(self, new_mode: StorageMode) -> None:
        """
        Switch storage mode at runtime.
        
        Args:
            new_mode: New storage mode to use
        """
        if new_mode == self._mode:
            return
        
        old_mode = self._mode
        logger.info(f"Switching storage mode: {old_mode.value} -> {new_mode.value}")
        
        # Migrate data if switching from persistent to ephemeral
        if old_mode == StorageMode.PERSISTENT and new_mode in (StorageMode.EPHEMERAL, StorageMode.HYBRID):
            if not self._ephemeral:
                self._ephemeral = get_ephemeral_store(
                    ttl_seconds=self._ttl_seconds,
                    max_articles=self._max_articles,
                )
                await self._ephemeral.start()
        
        # Initialize persistent if switching to it
        if new_mode in (StorageMode.PERSISTENT, StorageMode.HYBRID) and not self._persistent_db:
            try:
                from src.db_storage.async_database import get_async_database
                self._persistent_db = await get_async_database()
            except Exception as e:
                logger.error(f"Cannot switch to persistent mode: {e}")
                return
        
        self._mode = new_mode
        
        # Save preference
        await self._save_config()
        
        logger.info(f"Storage mode changed to {new_mode.value}")
    
    async def _save_config(self) -> None:
        """Save current configuration to file."""
        config = {
            "mode": self._mode.value,
            "ttl_seconds": self._ttl_seconds,
            "max_articles": self._max_articles,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(STORAGE_CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save config: {e}")
    
    # =========================================================================
    # Article CRUD - Unified API
    # =========================================================================
    
    async def add_article(self, article: Dict[str, Any]) -> bool:
        """
        Add article to storage.
        
        Behavior depends on mode:
        - EPHEMERAL: Store in memory with TTL
        - PERSISTENT: Store in database
        - HYBRID: Store in memory, cache AI summary in DB
        """
        url = article.get("url", "")
        
        # Check dedup
        if url in self._seen_urls:
            return False
        
        if self._mode == StorageMode.EPHEMERAL:
            result = self._ephemeral.add_article(article)
            if result:
                self._seen_urls.add(url)
            return result
        
        elif self._mode == StorageMode.PERSISTENT:
            result = await self._persistent_db.add_article(article)
            if result:
                self._seen_urls.add(url)
            return result
        
        else:  # HYBRID
            # Add to ephemeral store
            result = self._ephemeral.add_article(article)
            if result:
                self._seen_urls.add(url)
                
                # Cache AI summary in persistent store if available
                if self._persistent_db and article.get("ai_summary"):
                    try:
                        await self._cache_ai_summary(article)
                    except Exception as e:
                        logger.debug(f"AI cache failed: {e}")
            
            return result
    
    async def _cache_ai_summary(self, article: Dict[str, Any]) -> None:
        """Cache AI summary to persistent store (HYBRID mode)."""
        # Only store minimal data for AI cache
        cache_data = {
            "id": article.get("id"),
            "url": article["url"],
            "title": article.get("title", ""),
            "source": article.get("source", ""),
            "ai_summary": article.get("ai_summary"),
        }
        await self._persistent_db.add_article(cache_data)
    
    async def get_all_articles(self) -> List[Dict[str, Any]]:
        """Get all articles based on mode."""
        if self._mode == StorageMode.EPHEMERAL:
            return self._ephemeral.get_all_articles()
        
        elif self._mode == StorageMode.PERSISTENT:
            return await self._persistent_db.get_all_articles()
        
        else:  # HYBRID
            return self._ephemeral.get_all_articles()
    
    async def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get article by ID."""
        if self._mode == StorageMode.EPHEMERAL:
            return self._ephemeral.get_article(article_id)
        
        elif self._mode == StorageMode.PERSISTENT:
            articles = await self._persistent_db.get_all_articles()
            for a in articles:
                if a.get("id") == article_id:
                    return a
            return None
        
        else:  # HYBRID
            return self._ephemeral.get_article(article_id)
    
    async def search_articles(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search articles."""
        if self._mode == StorageMode.EPHEMERAL:
            return self._ephemeral.search(query, limit)
        
        elif self._mode == StorageMode.PERSISTENT:
            return await self._persistent_db.search_articles(query, limit)
        
        else:  # HYBRID
            return self._ephemeral.search(query, limit)
    
    async def get_article_count(self) -> int:
        """Get article count."""
        if self._mode == StorageMode.EPHEMERAL:
            return self._ephemeral.article_count
        
        elif self._mode == StorageMode.PERSISTENT:
            return await self._persistent_db.get_article_count()
        
        else:  # HYBRID
            return self._ephemeral.article_count
    
    def has_url(self, url: str) -> bool:
        """Check if URL has been seen (for dedup)."""
        return url in self._seen_urls
    
    # =========================================================================
    # User Save/Export (Ephemeral & Hybrid modes)
    # =========================================================================
    
    def save_article(self, article_id: str) -> bool:
        """Mark article as saved by user (won't expire)."""
        if self._mode in (StorageMode.EPHEMERAL, StorageMode.HYBRID):
            return self._ephemeral.save_article(article_id)
        return True  # In persistent mode, all articles are "saved"
    
    def unsave_article(self, article_id: str) -> bool:
        """Remove saved status from article."""
        if self._mode in (StorageMode.EPHEMERAL, StorageMode.HYBRID):
            return self._ephemeral.unsave_article(article_id)
        return True
    
    def get_saved_articles(self) -> List[Dict[str, Any]]:
        """Get user-saved articles."""
        if self._mode in (StorageMode.EPHEMERAL, StorageMode.HYBRID):
            return self._ephemeral.get_saved_articles()
        return []
    
    def export_articles(
        self,
        article_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Export articles for download."""
        if self._mode in (StorageMode.EPHEMERAL, StorageMode.HYBRID):
            return self._ephemeral.export_articles(article_ids)
        return []
    
    # =========================================================================
    # AI Summary Cache (Hybrid mode)
    # =========================================================================
    
    async def get_cached_summary(self, url: str) -> Optional[str]:
        """Get cached AI summary for URL (HYBRID mode)."""
        if self._mode == StorageMode.HYBRID and self._persistent_db:
            try:
                articles = await self._persistent_db.get_all_articles()
                for a in articles:
                    if a.get("url") == url:
                        return a.get("ai_summary")
            except Exception:
                pass
        return None
    
    # =========================================================================
    # Statistics & Management
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "mode": self._mode.value,
            "seen_urls_count": len(self._seen_urls),
        }
        
        if self._ephemeral:
            stats["ephemeral"] = self._ephemeral.stats
        
        if self._persistent_db:
            stats["persistent_available"] = True
            if hasattr(self._persistent_db, "pool_stats"):
                stats["pool_stats"] = self._persistent_db.pool_stats
        
        return stats
    
    async def clear_ephemeral(self) -> int:
        """Clear ephemeral articles (keeps saved ones)."""
        if self._ephemeral:
            return self._ephemeral.clear()
        return 0
    
    async def close(self) -> None:
        """Close all storage backends."""
        if self._ephemeral:
            await self._ephemeral.stop()
        
        if self._persistent_db:
            await self._persistent_db.close()
        
        self._initialized = False
        logger.info("UnifiedStorageManager closed")


# Singleton instance
_storage_manager: Optional[UnifiedStorageManager] = None
_storage_lock = asyncio.Lock()


async def get_storage_manager(
    mode: Optional[StorageMode] = None,
    ttl_seconds: int = 7200,
    max_articles: int = 1000,
) -> UnifiedStorageManager:
    """
    Get or create singleton UnifiedStorageManager.
    
    Mode priority:
    1. Explicit mode argument
    2. STORAGE_MODE environment variable
    3. Saved config file
    4. Default: HYBRID
    """
    global _storage_manager
    
    async with _storage_lock:
        if _storage_manager is None:
            # Determine mode
            if mode is None:
                # Check env var
                env_mode = os.environ.get("STORAGE_MODE", "").lower()
                if env_mode in ("ephemeral", "persistent", "hybrid"):
                    mode = StorageMode(env_mode)
                else:
                    # Check config file
                    mode = _load_mode_from_config() or StorageMode.HYBRID
            
            _storage_manager = UnifiedStorageManager(
                mode=mode,
                ttl_seconds=ttl_seconds,
                max_articles=max_articles,
            )
            await _storage_manager.initialize()
    
    return _storage_manager


def _load_mode_from_config() -> Optional[StorageMode]:
    """Load storage mode from config file."""
    try:
        if STORAGE_CONFIG_FILE.exists():
            with open(STORAGE_CONFIG_FILE) as f:
                config = json.load(f)
                mode_str = config.get("mode", "")
                if mode_str in ("ephemeral", "persistent", "hybrid"):
                    return StorageMode(mode_str)
    except Exception:
        pass
    return None


async def set_storage_mode(mode: StorageMode) -> None:
    """Convenience function to change storage mode."""
    manager = await get_storage_manager()
    await manager.set_mode(mode)
