"""Cache module for Tech News Scraper."""

from src.cache.redis_cache import (
    RedisCache,
    get_redis_cache,
    CHANNEL_ARTICLES,
    CHANNEL_ALERTS,
    CHANNEL_EVENTS,
)

__all__ = [
    "RedisCache",
    "get_redis_cache",
    "CHANNEL_ARTICLES",
    "CHANNEL_ALERTS", 
    "CHANNEL_EVENTS",
]
