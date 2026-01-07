"""
Main scraper module for collecting tech news articles.

This module provides async-capable web scraping for tech news from both
RSS feeds and direct web pages. Features concurrent HTTP requests with
proper rate limiting and retry logic.

Architecture:
- TechNewsScraper: Main scraper orchestrator
- Uses aiohttp for concurrent HTTP requests
- Integrates with RateLimiter for polite scraping
- Supports both RSS/Atom feeds and HTML page scraping
"""

import asyncio
import hashlib
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
import feedparser
import requests
from bs4 import BeautifulSoup

from config.settings import (
    DEFAULT_SOURCES,
    MAX_AGE_HOURS,
    MAX_RETRIES,
    RATE_LIMIT_TOKENS_PER_SECOND,
    RETRY_DELAY,
    SOURCE_SCRAPE_DELAY,
    USER_AGENT,
)
from src.ai_processor import summarize_text
from src.content_extractor import ContentExtractor
from src.database import Database
from src.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class TechNewsScraper:
    """
    Main scraper class for collecting tech news articles.
    
    Provides both synchronous and asynchronous methods for scraping
    tech news from RSS feeds and web pages. Implements intelligent
    retry logic, rate limiting, and content extraction.
    
    Attributes:
        db: Database instance for article storage.
        sources: List of news sources to scrape.
        rate_limiter: Rate limiter for controlling request frequency.
        session: Synchronous requests session for fallback.
    
    Example:
        db = Database()
        scraper = TechNewsScraper(db)
        
        # Async scraping
        new_count = await scraper.run_scrape_cycle_async()
        
        # Sync scraping (runs async internally)
        new_count = scraper.run_scrape_cycle()
    """
    
    def __init__(self, db: Database) -> None:
        """
        Initialize the scraper with database and configuration.
        
        Args:
            db: Database instance for storing scraped articles.
        """
        self.db = db
        
        # HTTP session for sync operations
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        
        # Rate limiter for polite scraping
        self.rate_limiter = RateLimiter(
            tokens_per_second=RATE_LIMIT_TOKENS_PER_SECOND,
            bucket_size=10
        )
        
        # Merge default sources with discovered sources
        self.sources: List[Dict[str, Any]] = DEFAULT_SOURCES.copy()
        for src in self.db.discovered_sources:
            if src['url'] not in {s['url'] for s in self.sources}:
                self.sources.append(src)
        
        logger.info(f"TechNewsScraper initialized with {len(self.sources)} sources")
    
    async def _fetch_url_async(
        self,
        session: aiohttp.ClientSession,
        url: str,
        timeout: int = 15
    ) -> Optional[str]:
        """
        Fetch URL content asynchronously with rate limiting.
        
        Args:
            session: aiohttp client session.
            url: URL to fetch.
            timeout: Request timeout in seconds.
        
        Returns:
            Response text if successful, None otherwise.
        """
        # Apply rate limiting
        await self.rate_limiter.wait_async(url)
        
        retries = MAX_RETRIES
        delay = RETRY_DELAY
        
        while retries > 0:
            try:
                async with session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        # Rate limited - wait longer
                        logger.warning(f"Rate limited by {url}, waiting...")
                        await asyncio.sleep(delay * 2)
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching {url}")
            except aiohttp.ClientError as e:
                logger.warning(f"Client error for {url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
            
            retries -= 1
            if retries > 0:
                await asyncio.sleep(delay)
                delay *= 2
        
        return None
    
    async def get_full_article_and_summarize_async(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Tuple[str, str]:
        """
        Fetch full article content and generate AI summary asynchronously.
        
        Args:
            session: aiohttp client session.
            url: Article URL to fetch.
        
        Returns:
            Tuple of (full_content, ai_summary). Returns placeholder strings
            if fetching fails.
        """
        html = await self._fetch_url_async(session, url)
        
        if not html:
            return "Could not fetch content.", "Summary unavailable."
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            full_content = ContentExtractor.extract_text(soup)
            
            # AI summarization is CPU-bound, run in thread pool
            loop = asyncio.get_event_loop()
            ai_summary = await loop.run_in_executor(
                None, summarize_text, full_content
            )
            
            return full_content, ai_summary
            
        except Exception as e:
            logger.error(f"Error processing article {url}: {e}")
            return "Content extraction failed.", "Summary unavailable."
    
    def get_full_article_and_summarize(self, url: str) -> Tuple[str, str]:
        """
        Fetch full article content and generate AI summary (sync wrapper).
        
        Args:
            url: Article URL to fetch.
        
        Returns:
            Tuple of (full_content, ai_summary).
        """
        # Apply rate limiting
        self.rate_limiter.wait(url)
        
        retries = MAX_RETRIES
        delay = RETRY_DELAY
        
        while retries > 0:
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                full_content = ContentExtractor.extract_text(soup)
                ai_summary = summarize_text(full_content)
                return full_content, ai_summary
                
            except requests.RequestException as e:
                retries -= 1
                logger.warning(
                    f"Failed to fetch {url}: {e}. Retries left: {retries}"
                )
                if retries > 0:
                    time.sleep(delay)
                    delay *= 2
        
        logger.error(f"All retries failed for {url}")
        return "Could not fetch content.", "Summary unavailable."
    
    async def scrape_rss_source_async(
        self,
        session: aiohttp.ClientSession,
        source: Dict[str, Any]
    ) -> int:
        """
        Scrape articles from an RSS/Atom feed asynchronously.
        
        Args:
            session: aiohttp client session.
            source: Source configuration dictionary.
        
        Returns:
            Number of new articles added.
        """
        logger.info(f"Processing RSS source: {source['name']}")
        new_articles_count = 0
        
        try:
            # Fetch RSS feed
            feed_content = await self._fetch_url_async(session, source["url"])
            if not feed_content:
                logger.error(f"Could not fetch RSS feed: {source['name']}")
                return 0
            
            feed = feedparser.parse(feed_content)
            
            # Process entries concurrently (limit concurrency)
            tasks = []
            for entry in feed.entries[:20]:
                if entry.link in self.db.url_cache:
                    continue
                
                # Check article age
                published_time = datetime.now(UTC)
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_time = datetime(
                            *entry.published_parsed[:6], 
                            tzinfo=UTC
                        )
                    except (ValueError, TypeError):
                        pass
                
                if published_time < datetime.now(UTC) - timedelta(hours=MAX_AGE_HOURS):
                    continue
                
                tasks.append(self._process_rss_entry_async(
                    session, entry, source, published_time
                ))
            
            # Run with limited concurrency
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, bool) and result:
                    new_articles_count += 1
                elif isinstance(result, Exception):
                    logger.error(f"Error processing entry: {result}")
            
            # Update source article count
            if new_articles_count > 0:
                self.db.update_source_article_count(
                    source['url'], 
                    new_articles_count
                )
            
            return new_articles_count
            
        except Exception as e:
            logger.error(f"Error scraping RSS {source['name']}: {e}")
            return 0
    
    async def _process_rss_entry_async(
        self,
        session: aiohttp.ClientSession,
        entry: Any,
        source: Dict[str, Any],
        published_time: datetime
    ) -> bool:
        """
        Process a single RSS entry asynchronously.
        
        Args:
            session: aiohttp client session.
            entry: RSS feed entry object.
            source: Source configuration dictionary.
            published_time: Parsed publication time.
        
        Returns:
            True if article was added, False otherwise.
        """
        try:
            full_content, ai_summary = await self.get_full_article_and_summarize_async(
                session, entry.link
            )
            
            article = {
                "id": hashlib.md5(entry.link.encode()).hexdigest(),
                "title": entry.title,
                "url": entry.link,
                "source": source["name"],
                "published": published_time.isoformat(),
                "scraped_at": datetime.now(UTC).isoformat(),
                "ai_summary": ai_summary,
                "full_content": full_content,
            }
            
            if self.db.add_article(article):
                logger.info(f"  + Added: {entry.title}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing entry {entry.link}: {e}")
        
        return False
    
    def scrape_rss_source(self, source: Dict[str, Any]) -> int:
        """
        Scrape articles from an RSS/Atom feed (sync wrapper).
        
        Args:
            source: Source configuration dictionary.
        
        Returns:
            Number of new articles added.
        """
        logger.info(f"Processing RSS source: {source['name']}")
        new_articles_count = 0
        
        try:
            feed = feedparser.parse(source["url"])
            
            for entry in feed.entries[:20]:
                if entry.link in self.db.url_cache:
                    continue
                
                # Check article age
                published_time = datetime.now(UTC)
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_time = datetime(
                            *entry.published_parsed[:6],
                            tzinfo=UTC
                        )
                    except (ValueError, TypeError):
                        pass
                
                if published_time < datetime.now(UTC) - timedelta(hours=MAX_AGE_HOURS):
                    continue
                
                full_content, ai_summary = self.get_full_article_and_summarize(
                    entry.link
                )
                
                article = {
                    "id": hashlib.md5(entry.link.encode()).hexdigest(),
                    "title": entry.title,
                    "url": entry.link,
                    "source": source["name"],
                    "published": published_time.isoformat(),
                    "scraped_at": datetime.now(UTC).isoformat(),
                    "ai_summary": ai_summary,
                    "full_content": full_content,
                }
                
                if self.db.add_article(article):
                    new_articles_count += 1
                    logger.info(f"  + Added: {entry.title}")
            
            if new_articles_count > 0:
                self.db.update_source_article_count(
                    source['url'],
                    new_articles_count
                )
            
            return new_articles_count
            
        except Exception as e:
            logger.error(f"Error scraping RSS {source['name']}: {e}")
            return 0
    
    async def scrape_web_source_async(
        self,
        session: aiohttp.ClientSession,
        source: Dict[str, Any]
    ) -> int:
        """
        Scrape articles from a regular web page asynchronously.
        
        Args:
            session: aiohttp client session.
            source: Source configuration dictionary.
        
        Returns:
            Number of new articles added.
        """
        logger.info(f"Processing web source: {source['name']}")
        new_articles_count = 0
        
        try:
            html = await self._fetch_url_async(session, source['url'])
            if not html:
                return 0
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find article links
            article_links = []
            for link in soup.find_all('a', href=True):
                href = urljoin(source['url'], link['href'])
                
                # URL pattern matching for article pages
                if any(pattern in href.lower() for pattern in [
                    '/article/', '/news/', '/post/', '/blog/',
                    '/story/', '/feature/', '/review/'
                ]):
                    if href not in self.db.url_cache:
                        article_links.append({
                            'url': href,
                            'title': link.get_text(strip=True) or 'Untitled'
                        })
            
            # Deduplicate and limit
            seen_urls = set()
            unique_links = []
            for link in article_links[:15]:
                if link['url'] not in seen_urls:
                    seen_urls.add(link['url'])
                    unique_links.append(link)
            
            # Process articles concurrently
            tasks = [
                self._process_web_article_async(session, link, source)
                for link in unique_links[:10]
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, bool) and result:
                    new_articles_count += 1
                elif isinstance(result, Exception):
                    logger.error(f"Error processing article: {result}")
            
            return new_articles_count
            
        except Exception as e:
            logger.error(f"Error scraping web source {source['name']}: {e}")
            return 0
    
    async def _process_web_article_async(
        self,
        session: aiohttp.ClientSession,
        article_link: Dict[str, str],
        source: Dict[str, Any]
    ) -> bool:
        """
        Process a single web article asynchronously.
        
        Args:
            session: aiohttp client session.
            article_link: Dictionary with 'url' and 'title' keys.
            source: Source configuration dictionary.
        
        Returns:
            True if article was added, False otherwise.
        """
        try:
            full_content, ai_summary = await self.get_full_article_and_summarize_async(
                session, article_link['url']
            )
            
            if full_content and full_content != "Could not fetch content.":
                article = {
                    "id": hashlib.md5(article_link['url'].encode()).hexdigest(),
                    "title": article_link['title'],
                    "url": article_link['url'],
                    "source": source["name"],
                    "published": datetime.now(UTC).isoformat(),
                    "scraped_at": datetime.now(UTC).isoformat(),
                    "ai_summary": ai_summary,
                    "full_content": full_content,
                }
                
                if self.db.add_article(article):
                    logger.info(f"  + Added: {article_link['title']}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error processing {article_link['url']}: {e}")
        
        return False
    
    def scrape_web_source(self, source: Dict[str, Any]) -> int:
        """
        Scrape articles from a regular web page (sync wrapper).
        
        Args:
            source: Source configuration dictionary.
        
        Returns:
            Number of new articles added.
        """
        logger.info(f"Processing web source: {source['name']}")
        new_articles_count = 0
        
        try:
            self.rate_limiter.wait(source['url'])
            response = self.session.get(source['url'], timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find article links
            article_links = []
            for link in soup.find_all('a', href=True):
                href = urljoin(source['url'], link['href'])
                
                if any(pattern in href.lower() for pattern in [
                    '/article/', '/news/', '/post/', '/blog/',
                    '/story/', '/feature/', '/review/'
                ]):
                    article_links.append({
                        'url': href,
                        'title': link.get_text(strip=True) or 'Untitled'
                    })
            
            # Process found articles
            for article_link in article_links[:10]:
                if article_link['url'] in self.db.url_cache:
                    continue
                
                full_content, ai_summary = self.get_full_article_and_summarize(
                    article_link['url']
                )
                
                if full_content and full_content != "Could not fetch content.":
                    article = {
                        "id": hashlib.md5(article_link['url'].encode()).hexdigest(),
                        "title": article_link['title'],
                        "url": article_link['url'],
                        "source": source["name"],
                        "published": datetime.now(UTC).isoformat(),
                        "scraped_at": datetime.now(UTC).isoformat(),
                        "ai_summary": ai_summary,
                        "full_content": full_content,
                    }
                    
                    if self.db.add_article(article):
                        new_articles_count += 1
                        logger.info(f"  + Added: {article_link['title']}")
                
                time.sleep(1)  # Rate limiting
            
            return new_articles_count
            
        except Exception as e:
            logger.error(f"Error scraping web source {source['name']}: {e}")
            return 0
    
    async def scrape_source_async(
        self,
        session: aiohttp.ClientSession,
        source: Dict[str, Any]
    ) -> int:
        """
        Route to appropriate async scraper based on source type.
        
        Args:
            session: aiohttp client session.
            source: Source configuration dictionary.
        
        Returns:
            Number of new articles added.
        """
        if source['type'] == 'rss':
            return await self.scrape_rss_source_async(session, source)
        else:
            return await self.scrape_web_source_async(session, source)
    
    def scrape_source(self, source: Dict[str, Any]) -> int:
        """
        Route to appropriate sync scraper based on source type.
        
        Args:
            source: Source configuration dictionary.
        
        Returns:
            Number of new articles added.
        """
        if source['type'] == 'rss':
            return self.scrape_rss_source(source)
        else:
            return self.scrape_web_source(source)
    
    async def run_scrape_cycle_async(self) -> int:
        """
        Run a complete async scraping cycle for all sources.
        
        Scrapes all sources concurrently using aiohttp. This is the
        preferred method for maximum performance.
        
        Returns:
            Total number of new articles found.
        """
        logger.info("=" * 50)
        logger.info("Starting async scraping cycle...")
        logger.info("=" * 50)
        
        total_new_articles = 0
        
        async with aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT}
        ) as session:
            # Create tasks for all sources
            tasks = [
                self.scrape_source_async(session, source)
                for source in self.sources
            ]
            
            # Run with semaphore to limit concurrency
            semaphore = asyncio.Semaphore(5)
            
            async def limited_task(task):
                async with semaphore:
                    return await task
            
            results = await asyncio.gather(
                *[limited_task(task) for task in tasks],
                return_exceptions=True
            )
            
            for i, result in enumerate(results):
                if isinstance(result, int):
                    total_new_articles += result
                elif isinstance(result, Exception):
                    logger.error(
                        f"Error scraping {self.sources[i]['name']}: {result}"
                    )
        
        if total_new_articles > 0:
            logger.info(
                f"✓ Async cycle complete. Found {total_new_articles} new articles."
            )
        else:
            logger.info("✓ Async cycle complete. No new articles found.")
        
        logger.info("=" * 50)
        return total_new_articles
    
    def run_scrape_cycle(self) -> int:
        """
        Run a complete scraping cycle for all sources.
        
        Runs the async scraping cycle in an event loop for backward
        compatibility with sync code.
        
        Returns:
            Total number of new articles found.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context, use sync fallback
                return self._run_scrape_cycle_sync()
            else:
                return loop.run_until_complete(self.run_scrape_cycle_async())
        except RuntimeError:
            # No event loop, create new one
            return asyncio.run(self.run_scrape_cycle_async())
    
    def _run_scrape_cycle_sync(self) -> int:
        """
        Synchronous fallback for scraping cycle.
        
        Used when already running in an async context.
        
        Returns:
            Total number of new articles found.
        """
        logger.info("=" * 50)
        logger.info("Starting sync scraping cycle...")
        logger.info("=" * 50)
        
        total_new_articles = 0
        
        for source in self.sources:
            total_new_articles += self.scrape_source(source)
            time.sleep(SOURCE_SCRAPE_DELAY)
        
        if total_new_articles > 0:
            logger.info(
                f"✓ Sync cycle complete. Found {total_new_articles} new articles."
            )
        else:
            logger.info("✓ Sync cycle complete. No new articles found.")
        
        logger.info("=" * 50)
        return total_new_articles
    
    def process_single_url(self, url: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Fetch, summarize, and store a single URL provided by the user.
        
        Args:
            url: URL to process.
        
        Returns:
            Tuple of (success, message, article_dict).
        """
        logger.info(f"Processing user URL: {url}")
        
        try:
            full_content, ai_summary = self.get_full_article_and_summarize(url)
            
            if not full_content or full_content == "Could not fetch content.":
                return False, "Failed to fetch content from URL.", None
            
            # Try to get a title from the page
            try:
                self.rate_limiter.wait(url)
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string.strip() if soup.title else url
            except Exception:
                title = url
            
            article = {
                "id": hashlib.md5(url.encode()).hexdigest(),
                "title": title,
                "url": url,
                "source": "User Provided",
                "published": datetime.now(UTC).isoformat(),
                "scraped_at": datetime.now(UTC).isoformat(),
                "ai_summary": ai_summary,
                "full_content": full_content,
            }
            
            if self.db.add_article(article):
                return True, "Successfully processed URL.", article
            else:
                return False, "URL already exists in database.", article
                
        except Exception as e:
            logger.error(f"Error processing single URL {url}: {e}")
            return False, str(e), None
    
    def search_and_scrape_web(self, query: str) -> Tuple[int, int]:
        """
        Search the web for a topic and scrape discovered articles.
        
        Args:
            query: Search query string.
        
        Returns:
            Tuple of (num_new_sources, num_new_articles).
        """
        logger.info(f"Initiating Search & Scrape for: {query}")
        
        # Import here to avoid circular imports
        from src.discovery import WebDiscoveryAgent
        
        discovery_agent = WebDiscoveryAgent(self.db)
        
        # Phase 1: Direct Article Search
        logger.info("Phase 1: Searching for specific articles...")
        article_urls = discovery_agent.search_web_for_articles(query, max_results=5)
        
        total_articles = 0
        for url in article_urls:
            if url in self.db.url_cache:
                continue
            
            success, msg, _ = self.process_single_url(url)
            if success:
                total_articles += 1
                logger.info(f"  + Scraped article: {url}")
            time.sleep(1)
        
        # Phase 2: Source Discovery
        logger.info("Phase 2: Discovering new sources...")
        new_sources = discovery_agent.discover_new_sources(
            max_new_sources=2,
            query=query
        )
        
        if new_sources:
            for src in new_sources:
                if src not in self.sources:
                    self.sources.append(src)
            
            for source in new_sources:
                total_articles += self.scrape_source(source)
        
        return len(new_sources), total_articles
    
    def get_source_stats(self) -> Dict[str, int]:
        """
        Get statistics about sources.
        
        Returns:
            Dictionary with source and article counts.
        """
        return {
            'total_sources': len(self.sources),
            'rss_sources': sum(1 for s in self.sources if s['type'] == 'rss'),
            'web_sources': sum(1 for s in self.sources if s['type'] == 'web'),
            'verified_sources': sum(
                1 for s in self.sources if s.get('verified', False)
            ),
            'total_articles': len(self.db.articles)
        }
    
    def get_latest_articles(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the latest articles from the database.
        
        Args:
            count: Maximum number of articles to return.
        
        Returns:
            List of article dictionaries sorted by recency.
        """
        return sorted(
            self.db.articles,
            key=lambda x: x.get("scraped_at", x.get("published", "")),
            reverse=True,
        )[:count]
    
    def save_url_to_txt(self, url: str) -> Optional[str]:
        """
        Save URL content to a text file.
        
        Args:
            url: URL to fetch and save.
        
        Returns:
            Path to saved file if successful, None otherwise.
        """
        try:
            self.rate_limiter.wait(url)
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            content = ContentExtractor.extract_text(soup)
            
            # Generate filename from URL
            filename = hashlib.md5(url.encode()).hexdigest()[:12] + ".txt"
            filepath = f"data/{filename}"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Scraped: {datetime.now(UTC).isoformat()}\n")
                f.write("=" * 60 + "\n\n")
                f.write(content)
            
            logger.info(f"Saved URL content to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving URL to txt: {e}")
            return None