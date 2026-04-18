"""
Enhanced Real-Time News Feeder with Multi-Source Discovery.

Integrates:
- DiscoveryAggregator (Google, Bing, NewsAPI)
- DeduplicationEngine (URL, title, content)
- Redis Event Bus for pub/sub (optional)
- Faster 30-second refresh cycles

Usage:
    feeder = EnhancedRealtimeFeeder()
    await feeder.start()
    
    async for article in feeder.stream():
        print(article.title)
"""

import asyncio
import hashlib
import logging
import time
from datetime import datetime, UTC
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

import aiohttp

# Import original feeder components
from src.engine.realtime_feeder import (
    RealtimeNewsFeeder,
    RobustDateParser,
    Article,
)
from src.core.types import SourceTier
from src.data_structures import BloomFilter

# Import new discovery and processing modules
from src.sources.aggregator import DiscoveryAggregator, UnifiedArticle
from src.processing.deduplication import DeduplicationEngine

# Import event bus (optional)
try:
    from src.infrastructure.redis_event_bus import RedisEventBus, LocalEventBus, Event, EventType
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

try:
    from config.settings import (
        REALTIME_REFRESH_INTERVAL,
        DEDUP_TITLE_SIMILARITY_THRESHOLD,
    )
except ImportError:
    REALTIME_REFRESH_INTERVAL = 30
    DEDUP_TITLE_SIMILARITY_THRESHOLD = 0.85


# =============================================================================
# ENHANCED FEEDER
# =============================================================================

class EnhancedRealtimeFeeder(RealtimeNewsFeeder):
    """
    Enhanced real-time news feeder with multi-source discovery.
    
    Improvements over base RealtimeNewsFeeder:
    - Integrates Google News, Bing News, NewsAPI
    - Uses multi-method deduplication
    - 30-second refresh cycles (vs 300 default)
    - Event-driven architecture with Redis pub/sub
    - Status callbacks for GUI integration
    """
    
    def __init__(
        self,
        refresh_interval: int = REALTIME_REFRESH_INTERVAL,
        max_articles: int = 1000,
        max_age_hours: int = 24,
        sources: Optional[List[str]] = None,
        enable_discovery: bool = True,
        enable_redis: bool = True,
    ):
        """
        Initialize enhanced feeder.
        
        Args:
            refresh_interval: Seconds between refreshes (default 30)
            max_articles: Max articles in memory
            max_age_hours: Max article age
            sources: RSS source URLs
            enable_discovery: Enable API-based discovery
            enable_redis: Enable Redis event publishing
        """
        # Initialize base feeder
        super().__init__(
            refresh_interval=refresh_interval,
            max_articles=max_articles,
            max_age_hours=max_age_hours,
            sources=sources,
        )
        
        # Enhanced components
        self._enable_discovery = enable_discovery
        self._enable_redis = enable_redis
        
        # Discovery aggregator (Google, Bing, NewsAPI)
        self._aggregator: Optional[DiscoveryAggregator] = None
        
        # Enhanced deduplication
        self._dedup_engine = DeduplicationEngine(
            title_threshold=DEDUP_TITLE_SIMILARITY_THRESHOLD,
            use_content_hash=True,
        )
        
        # Event bus for pub/sub
        self._event_bus = None
        
        # Status callbacks for GUI
        self._status_callbacks: List[Callable[[str, str], None]] = []
        
        # Refresh cooldown (prevent too frequent refreshes)
        self._refresh_cooldown = 60  # 1 minute cooldown for feeder refreshes
        
        # Enhanced stats
        self._enhanced_stats = {
            "google_articles": 0,
            "bing_articles": 0,
            "newsapi_articles": 0,
            "rss_articles": 0,
            "dedup_url": 0,
            "dedup_title": 0,
            "dedup_content": 0,
            "last_refresh_ms": 0,
        }
    
    async def stop(self):
        """Stop the enhanced feeder with proper cleanup."""
        # Stop base feeder (handles session cleanup)
        await super().stop()
        
        # Stop streaming client
        if hasattr(self, '_streaming_client') and self._streaming_client:
            await self._streaming_client.stop()
        
        logger.info("EnhancedRealtimeFeeder stopped")
        self._emit_status("feeder", "Stopped")

    async def _setup_streaming(self):
        """Initialize and start the StreamingClient."""
        from src.sources.streaming_client import StreamingClient, StreamingEvent
        
        self._streaming_client = StreamingClient(self._session)
        
        # Register callback
        def on_stream_event(event: StreamingEvent):
            if event.type == "news":
                # Convert event data to Article
                data = event.data
                article = Article(
                    id=hashlib.md5(data.get("url", "").encode()).hexdigest(),
                    url=data.get("url", ""),
                    title=data.get("title", "No Title"),
                    content=data.get("summary", ""),
                    summary=data.get("summary", ""),
                    source=data.get("source", "Stream"),
                    source_tier=SourceTier.TIER_2,
                    published_at=datetime.fromisoformat(data.get("published_at", datetime.now(UTC).isoformat())),
                    scraped_at=datetime.now(UTC)
                )
                
                # Deduplicate and add
                if self._add_article(article):
                    self._stats["articles_added"] += 1
                    self._notify_callbacks(article)
                    logger.info(f"Streamed article: {article.title}")
        
        self._streaming_client.add_callback(on_stream_event)
        await self._streaming_client.start()
        self._emit_status("stream", "Active (Quantum Mode)")

    async def start(self, fresh_start: bool = True, enable_background_refresh: bool = True):
        """
        Start the enhanced feeder.
        
        Args:
            fresh_start: If True, clears old articles before initial fetch
            enable_background_refresh: If False, doesn't start background refresh task
                                      (useful when used by pipeline that controls refreshes)
        """
        logger.info("EnhancedRealtimeFeeder starting...")
        
        # Initialize aggregator
        if self._enable_discovery:
            self._aggregator = DiscoveryAggregator()
            sources = self._aggregator.get_available_sources()
            logger.info(f"Discovery sources available: {sources}")
            self._emit_status("discovery", f"APIs: {', '.join(sources)}")
        
        # Initialize event bus
        if self._enable_redis and EVENT_BUS_AVAILABLE:
            try:
                self._event_bus = RedisEventBus()
                await self._event_bus.connect()
                logger.info("Redis event bus connected")
                self._emit_status("redis", "Connected")
            except Exception as e:
                logger.warning(f"Redis unavailable, using local: {e}")
                self._event_bus = LocalEventBus()
                self._emit_status("redis", "Fallback to local")
        
        # Start base feeder
        if enable_background_refresh:
            await super().start(fresh_start=fresh_start)
        else:
            # Initialize without background refresh task
            self._running = True
            if fresh_start:
                self._article_queue.clear()
                self._url_bloom = BloomFilter(expected_items=10000, false_positive_rate=0.01)
                logger.info("Cleared old articles for fresh start")
            # Do initial refresh manually
            await self.refresh()
            logger.info(f"EnhancedRealtimeFeeder started (background refresh disabled)")
        
        # Start streaming (Antigravity Upgrade)
        # We need to ensure session exists first, which super().start() or refresh() handles,
        # but if background refresh is disabled, self._session might be None if refresh() failed or wasn't called yet.
        # However, manual refresh() above is awaited.
        if self._session is None:
             self._session = aiohttp.ClientSession(
                headers={"User-Agent": self.USER_AGENT},
                connector=aiohttp.TCPConnector(ssl=False)
            )
        
        await self._setup_streaming()
        
        logger.info("EnhancedRealtimeFeeder started")
        self._emit_status("feeder", "Active")
    
    async def refresh(self) -> int:
        """
        Enhanced refresh with multi-source discovery.
        
        Returns:
            Number of new unique articles added
        """
        # Check cooldown to prevent too frequent refreshes
        if hasattr(self, '_last_refresh') and self._last_refresh:
            elapsed = (datetime.now(UTC) - self._last_refresh).total_seconds()
            if elapsed < self._refresh_cooldown:
                logger.debug(f"Enhanced refresh skipped - cooldown ({elapsed:.0f}s < {self._refresh_cooldown}s)")
                return 0
        
        logger.info("Enhanced refresh starting...")
        start_time = time.time()
        new_articles = 0
        
        self._emit_status("refresh", "Starting...")
        
        # Ensure session exists
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": self.USER_AGENT},
                connector=aiohttp.TCPConnector(ssl=False)
            )
        
        # 1. Fetch from discovery APIs (Google, Bing, NewsAPI)
        if self._aggregator:
            self._emit_status("discovery", "Fetching from APIs...")
            try:
                discovery_articles = await self._aggregator.discover_all(
                    session=self._session,
                    topics=["technology", "business", "science", "world"],
                    queries=[],  # No keyword queries - rely on topic-based RSS
                    max_per_source=100,
                )
                
                for unified in discovery_articles:
                    if self._process_unified_article(unified):
                        new_articles += 1
                
                logger.info(f"Discovery: {len(discovery_articles)} found, {new_articles} new")
                self._emit_status("discovery", f"{new_articles} new articles from APIs")
                
            except Exception as e:
                logger.error(f"Discovery error: {e}")
                self._emit_status("discovery", f"Error: {e}")
        
        # 2. Fetch from RSS sources (base feeder method)
        rss_count_before = new_articles
        self._emit_status("rss", "Fetching RSS feeds...")
        
        rss_new = await self._fetch_rss_sources()
        new_articles += rss_new
        
        self._enhanced_stats["rss_articles"] += rss_new
        self._emit_status("rss", f"{rss_new} new from RSS")
        
        # 3. Clean up expired
        self._article_queue.remove_expired()
        
        # 4. Publish to event bus
        if self._event_bus and new_articles > 0:
            await self._publish_refresh_event(new_articles)
        
        # Update stats
        duration_ms = (time.time() - start_time) * 1000
        self._enhanced_stats["last_refresh_ms"] = duration_ms
        self._last_refresh = datetime.now(UTC)
        self._stats["refreshes"] += 1
        
        logger.info(f"Enhanced refresh: {new_articles} new in {duration_ms:.0f}ms")
        self._emit_status("refresh", f"Complete: {new_articles} new ({duration_ms:.0f}ms)")
        
        return new_articles
    
    async def _fetch_rss_sources(self) -> int:
        """Fetch from RSS sources with enhanced dedup."""
        new_articles = 0
        
        tasks = [
            self._fetch_source(self._session, source)
            for source in self._sources
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for articles in results:
            if isinstance(articles, list):
                for article in articles:
                    # Use enhanced dedup - use summary or content for dedup
                    article_content = getattr(article, 'summary', '') or getattr(article, 'content', '')
                    dedup_result = self._dedup_engine.check(
                        url=article.url,
                        title=article.title,
                        content=article_content,
                        article_id=article.id,
                    )
                    
                    if dedup_result.is_duplicate:
                        self._stats["duplicates_skipped"] += 1
                        if dedup_result.reason == "url_match":
                            self._enhanced_stats["dedup_url"] += 1
                        elif dedup_result.reason == "title_similar":
                            self._enhanced_stats["dedup_title"] += 1
                        elif dedup_result.reason == "content_similar":
                            self._enhanced_stats["dedup_content"] += 1
                        continue
                    
                    # Add to queue
                    if self._add_article(article):
                        new_articles += 1
                        self._notify_callbacks(article)
        
        return new_articles
    
    def _process_unified_article(self, unified: UnifiedArticle) -> bool:
        """
        Process a unified article from discovery.
        
        Returns:
            True if article was added (not duplicate)
        """
        # Check deduplication
        dedup_result = self._dedup_engine.check(
            url=unified.url,
            title=unified.title,
            content=unified.description or unified.content or "",
            article_id=unified.id,
        )
        
        if dedup_result.is_duplicate:
            self._stats["duplicates_skipped"] += 1
            if dedup_result.reason == "url_match":
                self._enhanced_stats["dedup_url"] += 1
            elif dedup_result.reason == "title_similar":
                self._enhanced_stats["dedup_title"] += 1
            return False
        
        # Track source
        if unified.source_api == "google":
            self._enhanced_stats["google_articles"] += 1
        elif unified.source_api == "bing":
            self._enhanced_stats["bing_articles"] += 1
        elif unified.source_api == "newsapi":
            self._enhanced_stats["newsapi_articles"] += 1
        
        # Convert to Article (realtime_feeder's Article, not core/types)
        # The realtime feeder Article has different fields
        from src.engine.realtime_feeder import Article as FeedArticle
        from src.core.types import SourceTier
        
        article = FeedArticle(
            id=unified.id,
            url=unified.url,
            title=unified.title,
            content=unified.content or unified.description or "",
            summary=unified.description or "",
            source=unified.source or "Unknown",
            source_tier=SourceTier.TIER_2,  # Default to Tier 2 for API sources
            published_at=unified.published_at,
        )
        
        # Add to queue
        if self._add_article(article):
            self._stats["articles_added"] += 1
            self._notify_callbacks(article)
            return True
        
        return False
    
    def _notify_callbacks(self, article: Article):
        """Notify article callbacks."""
        for callback in self._new_article_callbacks:
            try:
                callback(article)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    async def _publish_refresh_event(self, count: int):
        """Publish refresh event to Redis."""
        if not self._event_bus:
            return
        
        event = Event(
            type=EventType.ARTICLE_NEW,
            data={
                "count": count,
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "enhanced_feeder",
            },
        )
        
        await self._event_bus.publish("news:all", event)
    
    def add_article_callback(self, callback: Callable[[Article], None]):
        """Add callback for new articles."""
        if callback not in self._new_article_callbacks:
            self._new_article_callbacks.append(callback)

    def add_status_callback(self, callback: Callable[[str, str], None]):
        """Add callback for status updates (GUI integration)."""
        self._status_callbacks.append(callback)
    
    def _emit_status(self, component: str, status: str):
        """Emit status update to callbacks."""
        for callback in self._status_callbacks:
            try:
                callback(component, status)
            except Exception as e:
                logger.debug(f"Status callback error: {e}")
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced statistics."""
        base_stats = self.get_stats()
        return {
            **base_stats,
            **self._enhanced_stats,
            "dedup_stats": self._dedup_engine.get_stats(),
            "discovery_enabled": self._enable_discovery,
            "redis_enabled": self._event_bus is not None,
        }


# =============================================================================
# ENHANCED NEWS PIPELINE (Unified Orchestrator)
# =============================================================================

class EnhancedNewsPipeline:
    """
    Unified News Pipeline - Orchestrates ALL fetching strategies in parallel.
    
    This is the single entry point for triggering news fetching. It:
    - Runs all fetchers simultaneously (RSS, APIs, Web Scraping)
    - Deduplicates results by URL and similar titles
    - Sorts by timestamp (newest first)
    - Provides status callbacks for GUI progress
    - No artificial delays - pure async performance
    
    Usage:
        pipeline = EnhancedNewsPipeline()
        await pipeline.start()
        
        # Single trigger to fetch from ALL sources
        articles = await pipeline.fetch_unified_live_feed()
        
        # Cleanup
        await pipeline.stop()
    """
    
    def __init__(
        self,
        enable_discovery: bool = True,
        max_articles: int = 500,
        max_age_hours: int = 48,
    ):
        """
        Initialize the unified pipeline.
        
        Args:
            enable_discovery: Enable API-based discovery (Google, Bing, etc.)
            max_articles: Maximum articles to return
            max_age_hours: Maximum article age to include
        """
        self._enable_discovery = enable_discovery
        self._max_articles = max_articles
        self._max_age_hours = max_age_hours
        
        # Core components
        self._feeder: Optional[EnhancedRealtimeFeeder] = None
        self._aggregator: Optional[DiscoveryAggregator] = None
        self._dedup_engine = DeduplicationEngine(
            title_threshold=DEDUP_TITLE_SIMILARITY_THRESHOLD,
            use_content_hash=True,
        )
        
        # Shared HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Status callbacks for GUI
        self._status_callbacks: List[Callable[[str, str], None]] = []
        self._article_callbacks: List[Callable[[Article], None]] = []
        
        # State
        self._running = False
        self._last_fetch: Optional[datetime] = None
        
        # Refresh cooldown settings
        self._refresh_cooldown = 60   # 1 minute between full refreshes
        self._cached_articles: List[Article] = []  # Cached results during cooldown
        
        # Statistics
        self._stats = {
            "total_fetches": 0,
            "total_articles": 0,
            "rss_articles": 0,
            "api_articles": 0,
            "duplicates_filtered": 0,
            "last_fetch_ms": 0,
            "cooldown_skips": 0,
        }
    
    async def start(self) -> None:
        """Start the pipeline and initialize components."""
        if self._running:
            return
        
        self._running = True
        self._emit_status("pipeline", "Starting...")
        
        # Initialize feeder (handles RSS sources)
        # Note: We don't start the feeder's background refresh task since we control refreshes via fetch_unified_live_feed()
        self._feeder = EnhancedRealtimeFeeder(
            refresh_interval=300,  # 5 minutes (longer since we control it manually)
            max_articles=self._max_articles,
            max_age_hours=self._max_age_hours,
            enable_discovery=False,  # We handle discovery separately
            enable_redis=False,
        )
        # Don't start the feeder's background refresh - we control it via pipeline
        # The feeder will only refresh when explicitly called, not automatically
        
        # Initialize aggregator (handles APIs)
        if self._enable_discovery:
            self._aggregator = DiscoveryAggregator()
            sources = self._aggregator.get_available_sources()
            logger.info(f"Pipeline: {len(sources)} discovery sources available")
            self._emit_status("discovery", f"Sources: {', '.join(sources)}")
        
        # Create shared session
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": EnhancedRealtimeFeeder.USER_AGENT},
            connector=aiohttp.TCPConnector(ssl=False, limit=50),
        )
        
        self._emit_status("pipeline", "Ready")
        logger.info("EnhancedNewsPipeline started")
    
    async def stop(self) -> None:
        """Stop the pipeline and cleanup resources."""
        self._running = False
        self._emit_status("pipeline", "Stopping...")
        
        # Close feeder
        if self._feeder:
            await self._feeder.stop()
            self._feeder = None
        
        # Close aggregator
        if self._aggregator:
            await self._aggregator.close()
            self._aggregator = None
        
        # Close session
        if self._session and not self._session.closed:
            await self._session.close()
            await asyncio.sleep(0.25)  # Allow connector to drain
            self._session = None
        
        self._emit_status("pipeline", "Stopped")
        logger.info("EnhancedNewsPipeline stopped")
    
    async def fetch_unified_live_feed(
        self,
        count: int = 200,
        topics: List[str] = None,
    ) -> List[Article]:
        """
        Fetch from ALL sources in parallel - the single trigger.
        
        This is the main entry point. It:
        1. Fires all fetchers simultaneously (RSS + APIs)
        2. Collects results as they complete
        3. Deduplicates by URL and title similarity
        4. Sorts by timestamp (newest first)
        5. Returns cleaned, unified results
        
        Args:
            count: Maximum articles to return
            topics: Optional topic filters
        
        Returns:
            List of deduplicated articles sorted by timestamp
        """
        if not self._running:
            await self.start()
        
        # Check cooldown - return cached articles if too soon
        if self._last_fetch:
            elapsed = (datetime.now(UTC) - self._last_fetch).total_seconds()
            if elapsed < self._refresh_cooldown:
                remaining = int(self._refresh_cooldown - elapsed)
                self._stats["cooldown_skips"] += 1
                self._emit_status("cooldown", f"⏳ Cooldown active ({remaining}s remaining)")
                logger.debug(f"Refresh skipped - cooldown ({elapsed:.0f}s < {self._refresh_cooldown}s)")
                return self._cached_articles
        
        start_time = time.time()
        self._stats["total_fetches"] += 1
        self._emit_status("fetch", "🚀 Fetching from ALL sources...")
        
        all_articles: List[Article] = []
        tasks = []
        
        # Ensure session exists
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": EnhancedRealtimeFeeder.USER_AGENT},
                connector=aiohttp.TCPConnector(ssl=False, limit=50),
            )
        
        # Task 1: RSS Feeds (via EnhancedRealtimeFeeder)
        if self._feeder:
            self._emit_status("rss", "Fetching RSS feeds...")
            tasks.append(self._fetch_rss())
        
        # Task 2: Discovery APIs (Google, Bing, NewsAPI, DuckDuckGo, Reddit, Twitter)
        if self._aggregator:
            self._emit_status("api", "Fetching from APIs...")
            tasks.append(self._fetch_discovery(topics))
        
        # Task 3: Directory Scraper (existing news site scraping)
        tasks.append(self._fetch_directory_scraper())
        
        # Execute ALL in parallel
        self._emit_status("fetch", f"🔄 Running {len(tasks)} fetchers in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Fetcher {i} error: {result}")
            elif isinstance(result, list):
                all_articles.extend(result)
        
        # Deduplicate
        self._emit_status("dedup", f"Deduplicating {len(all_articles)} articles...")
        unique_articles = self._deduplicate_articles(all_articles)
        
        # Sort by timestamp (newest first)
        unique_articles.sort(
            key=lambda a: a.published_at or a.scraped_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        
        # Limit results
        final_articles = unique_articles[:count]
        
        # Update stats
        duration_ms = (time.time() - start_time) * 1000
        self._stats["last_fetch_ms"] = duration_ms
        self._stats["total_articles"] = len(final_articles)
        self._last_fetch = datetime.now(UTC)
        
        # Emit completion
        self._emit_status("fetch", f"✓ {len(final_articles)} articles in {duration_ms:.0f}ms")
        logger.info(
            f"Unified fetch complete: {len(final_articles)} articles "
            f"(RSS: {self._stats['rss_articles']}, API: {self._stats['api_articles']}) "
            f"in {duration_ms:.0f}ms"
        )
        
        # Notify callbacks
        for article in final_articles:
            for callback in self._article_callbacks:
                try:
                    callback(article)
                except Exception as e:
                    logger.debug(f"Article callback error: {e}")
        
        # Cache results for cooldown period
        self._cached_articles = final_articles
        
        return final_articles
    
    async def _fetch_rss(self) -> List[Article]:
        """Fetch from RSS sources."""
        articles = []
        try:
            # Share our session with the feeder
            self._feeder._session = self._session
            
            # Refresh feeds (feeder's refresh() has its own cooldown)
            # Only refresh if not in cooldown - the feeder will handle this
            await self._feeder.refresh()
            
            # Get latest articles
            rss_articles = self._feeder.get_latest(1000)
            articles.extend(rss_articles)
            
            self._stats["rss_articles"] = len(articles)
            self._emit_status("rss", f"✓ {len(articles)} from RSS")
            
        except Exception as e:
            logger.error(f"RSS fetch error: {e}")
            self._emit_status("rss", f"Error: {str(e)[:30]}")
        
        return articles
    
    async def _fetch_discovery(self, topics: List[str] = None) -> List[Article]:
        """Fetch from discovery APIs (parallel)."""
        articles = []
        try:
            topics = topics or ["technology", "business", "science"]
            
            # Fetch from aggregator
            unified_articles = await self._aggregator.discover_all(
                session=self._session,
                topics=topics,
                queries=[],  # No keyword queries - topic-based RSS
                max_per_source=100,
            )
            
            # Convert UnifiedArticle to Article
            for ua in unified_articles:
                article = Article(
                    id=ua.id,
                    url=ua.url,
                    title=ua.title,
                    content=ua.content or ua.description or "",
                    summary=ua.description or "",
                    source=ua.source,
                    source_tier=SourceTier.TIER_2,
                    published_at=ua.published_at,
                    scraped_at=datetime.now(UTC),
                )
                articles.append(article)
            
            self._stats["api_articles"] = len(articles)
            self._emit_status("api", f"✓ {len(articles)} from APIs")
            
        except Exception as e:
            logger.error(f"Discovery fetch error: {e}")
            self._emit_status("api", f"Error: {str(e)[:30]}")
        
        return articles
    
    async def _fetch_directory_scraper(self) -> List[Article]:
        """Fetch from directory scraper (existing news sites)."""
        articles = []
        try:
            from src.engine.directory_scraper import DirectoryScraper
            import hashlib
            
            self._emit_status("scraper", "Scraping news directories...")
            
            scraper = DirectoryScraper()
            headlines = await scraper.bulk_harvest(
                limit_per_directory=15,
                total_limit=50,
            )
            
            for headline in headlines:
                article_id = hashlib.md5(headline.url.encode()).hexdigest()
                
                # Parse published date
                published_at = None
                if headline.published:
                    try:
                        from src.engine.realtime_feeder import RobustDateParser
                        published_at = RobustDateParser.parse(headline.published, headline.url)
                    except:
                        pass
                
                article = Article(
                    id=article_id,
                    url=headline.url,
                    title=headline.title,
                    content=headline.summary or "",
                    summary=headline.summary or "",
                    source=headline.source,
                    source_tier=SourceTier.TIER_2,
                    published_at=published_at,
                    scraped_at=datetime.now(UTC),
                )
                articles.append(article)
            
            self._emit_status("scraper", f"✓ {len(articles)} from directories")
            
        except Exception as e:
            logger.error(f"Directory scraper error: {e}")
            self._emit_status("scraper", f"Error: {str(e)[:30]}")
        
        return articles
    
    def _deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """Deduplicate articles by URL and title similarity."""
        unique = []
        duplicates = 0
        
        for article in articles:
            result = self._dedup_engine.check(
                url=article.url,
                title=article.title,
                content=article.summary or "",
                article_id=article.id,
            )
            
            if result.is_duplicate:
                duplicates += 1
                continue
            
            unique.append(article)
        
        self._stats["duplicates_filtered"] = duplicates
        logger.debug(f"Deduplication: {len(unique)} unique, {duplicates} duplicates")
        
        return unique
    
    def add_status_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add callback for status updates."""
        self._status_callbacks.append(callback)
    
    def add_article_callback(self, callback: Callable[[Article], None]) -> None:
        """Add callback for new articles."""
        self._article_callbacks.append(callback)
    
    def _emit_status(self, component: str, status: str) -> None:
        """Emit status update to callbacks."""
        for callback in self._status_callbacks:
            try:
                callback(component, status)
            except Exception as e:
                logger.debug(f"Status callback error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            **self._stats,
            "running": self._running,
            "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            "discovery_enabled": self._enable_discovery,
        }
    
    @property
    def last_fetch(self) -> Optional[datetime]:
        """Get last fetch time."""
        return self._last_fetch


# =============================================================================
# STANDALONE RUNNER
# =============================================================================

async def main():
    """Test the enhanced feeder."""
    logging.basicConfig(level=logging.INFO)
    
    feeder = EnhancedRealtimeFeeder(
        refresh_interval=30,
        enable_discovery=True,
        enable_redis=False,
    )
    
    # Status callback for testing
    feeder.add_status_callback(lambda c, s: print(f"[{c}] {s}"))
    
    try:
        await feeder.start()
        
        # Run for 2 minutes
        for i in range(4):
            await asyncio.sleep(30)
            print(f"\n--- Stats after {(i+1)*30}s ---")
            stats = feeder.get_enhanced_stats()
            print(f"Articles: {stats.get('articles_added', 0)}")
            print(f"Google: {stats.get('google_articles', 0)}")
            print(f"Bing: {stats.get('bing_articles', 0)}")
            print(f"NewsAPI: {stats.get('newsapi_articles', 0)}")
            print(f"RSS: {stats.get('rss_articles', 0)}")
            print(f"Dedup: URL={stats.get('dedup_url', 0)} Title={stats.get('dedup_title', 0)}")
    finally:
        await feeder.stop()


if __name__ == "__main__":
    asyncio.run(main())
