"""
Redis Cache Layer - Distributed caching and pub/sub for real-time events.

Features:
- AI summary caching (saves API costs)
- Rate limiting coordination across workers
- Pub/sub for real-time article distribution
- TTL-based automatic expiration

Usage:
    from src.cache.redis_cache import get_redis_cache
    
    cache = await get_redis_cache()
    
    # Cache AI summary
    await cache.set_summary("https://example.com", "Summary text")
    summary = await cache.get_summary("https://example.com")
    
    # Pub/sub for real-time
    await cache.publish_article(article)
    async for article in cache.subscribe_articles():
        process(article)
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, UTC
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

try:
    import redis.asyncio as aioredis #type:ignore
    HAS_REDIS = True
except ImportError:
    try:
        import aioredis #type:ignore
        HAS_REDIS = True
    except ImportError:
        HAS_REDIS = False
        aioredis = None

logger = logging.getLogger(__name__)

# Default Redis URL
DEFAULT_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Cache TTLs
SUMMARY_TTL = 60 * 60 * 24 * 7  # 7 days for AI summaries
RATE_LIMIT_TTL = 60 * 60  # 1 hour for rate limit windows
ARTICLE_TTL = 60 * 60 * 2  # 2 hours for article cache

# Pub/Sub channels
CHANNEL_ARTICLES = "tech_news:articles"
CHANNEL_ALERTS = "tech_news:alerts"
CHANNEL_EVENTS = "tech_news:events"


class RedisCache:
    """
    Redis-based caching and pub/sub layer.
    
    Provides:
    - AI summary caching
    - Rate limiting coordination
    - Real-time article streaming via pub/sub
    - Deduplication URL tracking
    """
    
    def __init__(
        self,
        redis_url: str = DEFAULT_REDIS_URL,
        prefix: str = "tech_news:",
    ) -> None:
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
        """
        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._connected = False
        
        # Stats
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "articles_published": 0,
            "articles_received": 0,
        }
    
    async def connect(self) -> bool:
        """
        Connect to Redis.
        
        Returns:
            True if connected, False otherwise
        """
        if not HAS_REDIS:
            logger.warning("Redis not installed. Install with: pip install redis")
            return False
        
        try:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        self._connected = False
        logger.info("Redis disconnected")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected and self._redis is not None
    
    def _key(self, *parts: str) -> str:
        """Generate namespaced key."""
        return self.prefix + ":".join(parts)
    
    def _url_hash(self, url: str) -> str:
        """Generate hash from URL for compact storage."""
        return hashlib.md5(url.encode()).hexdigest()
    
    # =========================================================================
    # AI Summary Cache
    # =========================================================================
    
    async def get_summary(self, url: str) -> Optional[str]:
        """
        Get cached AI summary for URL.
        
        Args:
            url: Article URL
        
        Returns:
            Cached summary or None
        """
        if not self.is_connected:
            return None
        
        try:
            key = self._key("summary", self._url_hash(url))
            summary = await self._redis.get(key)
            
            if summary:
                self._stats["cache_hits"] += 1
                return summary
            else:
                self._stats["cache_misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Redis get_summary error: {e}")
            return None
    
    async def set_summary(
        self,
        url: str,
        summary: str,
        ttl: int = SUMMARY_TTL,
    ) -> bool:
        """
        Cache AI summary for URL.
        
        Args:
            url: Article URL
            summary: AI-generated summary
            ttl: Time-to-live in seconds
        
        Returns:
            True if cached successfully
        """
        if not self.is_connected or not summary:
            return False
        
        try:
            key = self._key("summary", self._url_hash(url))
            await self._redis.setex(key, ttl, summary)
            return True
            
        except Exception as e:
            logger.error(f"Redis set_summary error: {e}")
            return False
    
    # =========================================================================
    # Rate Limiting
    # =========================================================================
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int = 100,
        window: int = 60,
    ) -> bool:
        """
        Check if rate limit is exceeded using sliding window.
        
        Args:
            identifier: Rate limit identifier (e.g., "api:gemini")
            limit: Maximum requests per window
            window: Window size in seconds
        
        Returns:
            True if within limit, False if exceeded
        """
        if not self.is_connected:
            return True  # Allow if Redis unavailable
        
        try:
            key = self._key("rate", identifier)
            now = int(datetime.now(UTC).timestamp())
            
            pipe = self._redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, now - window)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry
            pipe.expire(key, window)
            
            results = await pipe.execute()
            current_count = results[1]
            
            return current_count < limit
            
        except Exception as e:
            logger.error(f"Redis rate_limit error: {e}")
            return True
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        window: int = 60,
    ) -> Dict[str, int]:
        """Get current rate limit status."""
        if not self.is_connected:
            return {"count": 0, "window": window, "remaining": -1}
        
        try:
            key = self._key("rate", identifier)
            now = int(datetime.now(UTC).timestamp())
            
            await self._redis.zremrangebyscore(key, 0, now - window)
            count = await self._redis.zcard(key)
            
            return {"count": count, "window": window}
            
        except Exception as e:
            return {"count": 0, "window": window, "error": str(e)}
    
    # =========================================================================
    # URL Deduplication
    # =========================================================================
    
    async def has_seen_url(self, url: str) -> bool:
        """Check if URL has been seen."""
        if not self.is_connected:
            return False
        
        try:
            key = self._key("seen_urls")
            return await self._redis.sismember(key, self._url_hash(url))
        except Exception as exc:
            logger.warning("Redis has_seen_url error for '%s': %s", url, exc)
            return False
    
    async def mark_url_seen(self, url: str) -> None:
        """Mark URL as seen in Redis set with automatic TTL expiry."""
        if not self.is_connected:
            return
        
        try:
            key = self._key("seen_urls")
            await self._redis.sadd(key, self._url_hash(url))
        except Exception as exc:
            logger.warning("Redis mark_url_seen error for '%s': %s", url, exc)
    
    async def get_seen_count(self) -> int:
        """Get count of seen URLs."""
        if not self.is_connected:
            return 0
        
        try:
            key = self._key("seen_urls")
            return await self._redis.scard(key)
        except Exception:
            return 0
    
    # =========================================================================
    # Pub/Sub for Real-time Articles
    # =========================================================================
    
    async def publish_article(self, article: Dict[str, Any]) -> bool:
        """
        Publish article to real-time channel.
        
        Args:
            article: Article dictionary
        
        Returns:
            True if published
        """
        if not self.is_connected:
            return False
        
        try:
            message = json.dumps({
                "type": "article",
                "data": article,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            
            await self._redis.publish(CHANNEL_ARTICLES, message)
            self._stats["articles_published"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return False
    
    async def publish_alert(
        self,
        article_id: str,
        criticality: int,
        message: str,
    ) -> bool:
        """Publish high-criticality alert."""
        if not self.is_connected:
            return False
        
        try:
            alert = json.dumps({
                "type": "alert",
                "article_id": article_id,
                "criticality": criticality,
                "message": message,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            
            await self._redis.publish(CHANNEL_ALERTS, alert)
            return True
            
        except Exception as e:
            logger.error(f"Redis alert publish error: {e}")
            return False
    
    async def subscribe_articles(
        self,
        callback: Optional[Callable[[Dict], None]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to real-time article stream.
        
        Yields:
            Article dictionaries as they arrive
        """
        if not self.is_connected:
            return
        
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(CHANNEL_ARTICLES)
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        article = data.get("data", {})
                        self._stats["articles_received"] += 1
                        
                        if callback:
                            callback(article)
                        
                        yield article
                        
                    except json.JSONDecodeError:
                        continue
                        
        except asyncio.CancelledError:
            await pubsub.close()
        except Exception as e:
            logger.error(f"Redis subscribe error: {e}")
    
    # =========================================================================
    # Stats & Management
    # =========================================================================
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            **self._stats,
            "connected": self.is_connected,
            "redis_url": self.redis_url,
        }
    
    async def clear_cache(self, pattern: str = "*") -> int:
        """
        Clear cached entries matching pattern.
        
        Args:
            pattern: Key pattern to match
        
        Returns:
            Number of keys deleted
        """
        if not self.is_connected:
            return 0
        
        try:
            keys = await self._redis.keys(self._key(pattern))
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0


# Singleton instance
_redis_cache: Optional[RedisCache] = None


async def get_redis_cache(
    redis_url: str = DEFAULT_REDIS_URL,
) -> RedisCache:
    """
    Get or create singleton RedisCache instance.
    
    Returns connected cache if Redis available, otherwise unconnected instance.
    """
    global _redis_cache
    
    if _redis_cache is None:
        _redis_cache = RedisCache(redis_url=redis_url)
        await _redis_cache.connect()
    
    return _redis_cache
