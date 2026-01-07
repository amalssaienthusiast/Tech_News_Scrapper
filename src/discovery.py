"""
Web discovery module for finding new tech news sources.

This module implements intelligent source discovery using multiple
strategies: API-based search (preferred), web scraping fallback,
and static curated sources as last resort.

Architecture:
- WebDiscoveryAgent: Main discovery orchestrator
- Supports Google Custom Search API and Bing Search API
- Falls back to web scraping when APIs unavailable
- Uses rate limiting and polite delays
"""

import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup

from config.settings import (
    BING_API_KEY,
    DISCOVERY_QUERIES,
    DISCOVERY_RATE_LIMIT,
    GOOGLE_API_KEY,
    GOOGLE_CSE_ID,
    TECH_KEYWORDS,
    USER_AGENT,
)
from src.database import Database
from src.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class WebDiscoveryAgent:
    """
    Discovers and verifies new tech news sources from the web.
    
    Implements a multi-tier discovery strategy:
    1. Official APIs (Google/Bing) - Most reliable
    2. Web scraping search engines - Fallback
    3. Static curated sources - Last resort
    
    Attributes:
        db: Database instance for storing discovered sources.
        session: Synchronous requests session.
        rate_limiter: Rate limiter for polite requests.
        api_available: Dict indicating which APIs are configured.
    
    Example:
        db = Database()
        agent = WebDiscoveryAgent(db)
        new_sources = agent.discover_new_sources(max_new_sources=5)
    """
    
    # Fallback tech news sources when discovery fails
    FALLBACK_SOURCES = [
        "https://techcrunch.com",
        "https://www.theverge.com",
        "https://www.wired.com",
        "https://arstechnica.com",
        "https://venturebeat.com",
        "https://www.engadget.com",
        "https://gizmodo.com",
        "https://www.cnet.com/news/",
        "https://www.zdnet.com",
        "https://thenextweb.com",
        "https://www.techmeme.com",
        "https://news.ycombinator.com",
    ]
    
    def __init__(self, db: Database) -> None:
        """
        Initialize the discovery agent.
        
        Args:
            db: Database instance for storing discovered sources.
        """
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        
        self.rate_limiter = RateLimiter(
            tokens_per_second=DISCOVERY_RATE_LIMIT,
            bucket_size=5
        )
        
        # Check API availability
        self.api_available = {
            "google": bool(GOOGLE_API_KEY and GOOGLE_CSE_ID),
            "bing": bool(BING_API_KEY),
        }
        
        if self.api_available["google"]:
            logger.info("Google Custom Search API configured")
        if self.api_available["bing"]:
            logger.info("Bing Search API configured")
        if not any(self.api_available.values()):
            logger.warning(
                "No search APIs configured. Using web scraping fallback."
            )
    
    async def search_google_api_async(
        self,
        session: aiohttp.ClientSession,
        query: str,
        max_results: int = 10
    ) -> List[str]:
        """
        Search using Google Custom Search API asynchronously.
        
        Args:
            session: aiohttp client session.
            query: Search query string.
            max_results: Maximum number of results.
        
        Returns:
            List of URLs from search results.
        """
        if not self.api_available["google"]:
            return []
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": GOOGLE_API_KEY,
                "cx": GOOGLE_CSE_ID,
                "q": query,
                "num": min(max_results, 10),  # API max is 10
            }
            
            await self.rate_limiter.wait_async(url)
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    urls = [
                        item["link"] 
                        for item in data.get("items", [])
                    ]
                    logger.info(
                        f"Google API returned {len(urls)} results for '{query}'"
                    )
                    return urls
                elif response.status == 403:
                    logger.error("Google API quota exceeded or invalid key")
                else:
                    logger.warning(f"Google API returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"Google API error: {e}")
        
        return []
    
    async def search_bing_api_async(
        self,
        session: aiohttp.ClientSession,
        query: str,
        max_results: int = 10
    ) -> List[str]:
        """
        Search using Bing Search API asynchronously.
        
        Args:
            session: aiohttp client session.
            query: Search query string.
            max_results: Maximum number of results.
        
        Returns:
            List of URLs from search results.
        """
        if not self.api_available["bing"]:
            return []
        
        try:
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
            params = {
                "q": query,
                "count": max_results,
                "responseFilter": "Webpages",
            }
            
            await self.rate_limiter.wait_async(url)
            
            async with session.get(
                url, 
                headers=headers, 
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    urls = [
                        page["url"]
                        for page in data.get("webPages", {}).get("value", [])
                    ]
                    logger.info(
                        f"Bing API returned {len(urls)} results for '{query}'"
                    )
                    return urls
                elif response.status == 401:
                    logger.error("Bing API authentication failed")
                else:
                    logger.warning(f"Bing API returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"Bing API error: {e}")
        
        return []
    
    def search_google_api(self, query: str, max_results: int = 10) -> List[str]:
        """
        Search using Google Custom Search API (sync).
        
        Args:
            query: Search query string.
            max_results: Maximum number of results.
        
        Returns:
            List of URLs from search results.
        """
        if not self.api_available["google"]:
            return []
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": GOOGLE_API_KEY,
                "cx": GOOGLE_CSE_ID,
                "q": query,
                "num": min(max_results, 10),
            }
            
            self.rate_limiter.wait(url)
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return [item["link"] for item in data.get("items", [])]
                
        except Exception as e:
            logger.error(f"Google API error: {e}")
        
        return []
    
    def search_bing_api(self, query: str, max_results: int = 10) -> List[str]:
        """
        Search using Bing Search API (sync).
        
        Args:
            query: Search query string.
            max_results: Maximum number of results.
        
        Returns:
            List of URLs from search results.
        """
        if not self.api_available["bing"]:
            return []
        
        try:
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
            params = {
                "q": query,
                "count": max_results,
                "responseFilter": "Webpages",
            }
            
            self.rate_limiter.wait(url)
            response = self.session.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return [
                    page["url"]
                    for page in data.get("webPages", {}).get("value", [])
                ]
                
        except Exception as e:
            logger.error(f"Bing API error: {e}")
        
        return []
    
    def search_web_for_sources(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[str]:
        """
        Search the web for tech news sources using multiple strategies.
        
        Tries APIs first, then web scraping, then fallback sources.
        
        Args:
            query: Search query string.
            max_results: Maximum number of results to return.
        
        Returns:
            List of discovered URLs.
        """
        logger.info(f"Searching web for: {query}")
        discovered_urls: List[str] = []
        
        # Strategy 1: Try official APIs first
        if self.api_available["google"]:
            discovered_urls = self.search_google_api(query, max_results)
            if discovered_urls:
                return discovered_urls[:max_results]
        
        if self.api_available["bing"]:
            discovered_urls = self.search_bing_api(query, max_results)
            if discovered_urls:
                return discovered_urls[:max_results]
        
        # Strategy 2: Web scraping fallback
        discovered_urls = self._scrape_search_engines(query, max_results)
        
        if discovered_urls:
            return discovered_urls[:max_results]
        
        # Strategy 3: Fallback to curated sources
        logger.warning("Search failed. Using fallback sources.")
        import random
        return random.sample(
            self.FALLBACK_SOURCES,
            min(len(self.FALLBACK_SOURCES), max_results)
        )
    
    def _scrape_search_engines(
        self, 
        query: str, 
        max_results: int
    ) -> List[str]:
        """
        Scrape search engines for results (fallback method).
        
        Args:
            query: Search query string.
            max_results: Maximum number of results.
        
        Returns:
            List of URLs extracted from search results.
        """
        discovered_urls: List[str] = []
        
        engines = [
            ("DuckDuckGo", f"https://lite.duckduckgo.com/lite/?q={requests.utils.quote(query)}"),
            ("Bing", f"https://www.bing.com/search?q={requests.utils.quote(query)}"),
        ]
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        for name, url in engines:
            try:
                logger.info(f"Trying search engine: {name}")
                self.rate_limiter.wait(url)
                
                response = self.session.get(
                    url, 
                    headers=headers, 
                    timeout=10,
                    allow_redirects=True
                )
                
                if response.status_code != 200:
                    logger.warning(f"{name} returned status {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                engine_urls: List[str] = []
                
                # Extract links with filtering
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    # Skip search engine internal links
                    if not href.startswith('http'):
                        continue
                    if any(skip in href for skip in [
                        'google.', 'bing.', 'duckduckgo.', 'microsoft.',
                        'search', 'ads', 'account', 'login', 'signup'
                    ]):
                        continue
                    
                    engine_urls.append(href)
                
                if engine_urls:
                    discovered_urls.extend(engine_urls)
                    logger.info(f"Found {len(engine_urls)} results from {name}")
                    break
                    
            except requests.RequestException as e:
                logger.warning(f"Error with {name}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error with {name}: {e}")
        
        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for url in discovered_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls[:max_results]
    
    def search_web_for_articles(
        self, 
        query: str, 
        max_results: int = 5
    ) -> List[str]:
        """
        Search the web for specific articles matching the query.
        
        Prioritizes deep links over homepages.
        
        Args:
            query: Search query string.
            max_results: Maximum number of article URLs.
        
        Returns:
            List of article URLs.
        """
        logger.info(f"Searching web for articles: {query}")
        
        # Try APIs with article-focused query
        enhanced_query = f"{query} news article"
        article_urls: List[str] = []
        
        if self.api_available["google"]:
            article_urls = self.search_google_api(enhanced_query, max_results * 2)
        elif self.api_available["bing"]:
            article_urls = self.search_bing_api(enhanced_query, max_results * 2)
        else:
            article_urls = self._scrape_search_engines(enhanced_query, max_results * 2)
        
        # Filter for likely article URLs (not homepages)
        filtered_urls: List[str] = []
        for url in article_urls:
            parsed = urlparse(url)
            # Skip if just homepage
            if parsed.path in ['', '/', '/news', '/news/']:
                continue
            # Prefer URLs with longer paths (likely articles)
            if len(parsed.path) > 10:
                filtered_urls.append(url)
        
        logger.info(f"Found {len(filtered_urls)} article URLs")
        return filtered_urls[:max_results]
    
    def is_tech_related(self, text: str) -> bool:
        """
        Check if content is tech-related using keyword matching.
        
        Args:
            text: Text content to analyze.
        
        Returns:
            True if text contains enough tech keywords.
        """
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in TECH_KEYWORDS if keyword in text_lower)
        return keyword_count >= 3
    
    def verify_source(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Verify if a URL is a valid tech news source.
        
        Checks for:
        - Page accessibility
        - Tech-related content
        - RSS/Atom feed availability
        
        Args:
            url: URL to verify.
        
        Returns:
            Source info dict if valid, None otherwise.
        """
        try:
            logger.info(f"Verifying source: {url}")
            
            self.rate_limiter.wait(url)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract page title
            title_tag = soup.find('title')
            page_title = title_tag.text.strip() if title_tag else urlparse(url).netloc
            
            # Check for RSS/Atom feeds
            rss_links = soup.find_all(
                'link', 
                type=['application/rss+xml', 'application/atom+xml']
            )
            
            # Get page text for tech relevance check
            page_text = soup.get_text()[:2000]
            
            # Verify tech relevance
            if not self.is_tech_related(page_text):
                logger.info(f"Not tech-related: {url}")
                return None
            
            # Determine source type and URL
            if rss_links:
                feed_url = urljoin(url, rss_links[0].get('href'))
                source_type = 'rss'
                source_url = feed_url
            else:
                source_type = 'web'
                source_url = url
            
            source_info: Dict[str, Any] = {
                'url': source_url,
                'original_url': url,
                'type': source_type,
                'name': page_title[:100],  # Truncate long titles
                'verified': True,
                'discovered_at': datetime.now(UTC).isoformat(),
                'quality_score': 0.0,
                'article_count': 0
            }
            
            logger.info(f"✓ Verified: {page_title} ({source_type})")
            return source_info
            
        except requests.HTTPError as e:
            logger.warning(f"HTTP error verifying {url}: {e}")
        except requests.RequestException as e:
            logger.warning(f"Request error verifying {url}: {e}")
        except Exception as e:
            logger.error(f"Source verification failed for {url}: {e}")
        
        return None
    
    async def verify_source_async(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify if a URL is a valid tech news source asynchronously.
        
        Args:
            session: aiohttp client session.
            url: URL to verify.
        
        Returns:
            Source info dict if valid, None otherwise.
        """
        try:
            logger.info(f"Verifying source: {url}")
            
            await self.rate_limiter.wait_async(url)
            
            async with session.get(
                url, 
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract page title
                title_tag = soup.find('title')
                page_title = title_tag.text.strip() if title_tag else urlparse(url).netloc
                
                # Check for RSS/Atom feeds
                rss_links = soup.find_all(
                    'link',
                    type=['application/rss+xml', 'application/atom+xml']
                )
                
                # Get page text for tech relevance check
                page_text = soup.get_text()[:2000]
                
                if not self.is_tech_related(page_text):
                    logger.info(f"Not tech-related: {url}")
                    return None
                
                if rss_links:
                    feed_url = urljoin(url, rss_links[0].get('href'))
                    source_type = 'rss'
                    source_url = feed_url
                else:
                    source_type = 'web'
                    source_url = url
                
                source_info: Dict[str, Any] = {
                    'url': source_url,
                    'original_url': url,
                    'type': source_type,
                    'name': page_title[:100],
                    'verified': True,
                    'discovered_at': datetime.now(UTC).isoformat(),
                    'quality_score': 0.0,
                    'article_count': 0
                }
                
                logger.info(f"✓ Verified: {page_title} ({source_type})")
                return source_info
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout verifying {url}")
        except aiohttp.ClientError as e:
            logger.warning(f"Client error verifying {url}: {e}")
        except Exception as e:
            logger.error(f"Verification failed for {url}: {e}")
        
        return None
    
    def discover_new_sources(
        self,
        max_new_sources: int = 5,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Main discovery method - searches web and verifies sources.
        
        Args:
            max_new_sources: Maximum number of new sources to discover.
            query: Optional specific query. Uses default queries if None.
        
        Returns:
            List of newly discovered and verified source dictionaries.
        """
        logger.info("Starting source discovery process...")
        new_sources: List[Dict[str, Any]] = []
        
        # Get existing source URLs
        existing_urls = {src['url'] for src in self.db.discovered_sources}
        
        queries = [query] if query else DISCOVERY_QUERIES[:3]
        
        for q in queries:
            if len(new_sources) >= max_new_sources:
                break
            
            # Search web
            potential_urls = self.search_web_for_sources(q, max_results=5)
            
            for url in potential_urls:
                if len(new_sources) >= max_new_sources:
                    break
                
                if url in existing_urls:
                    continue
                
                # Verify source
                source_info = self.verify_source(url)
                
                if source_info:
                    if self.db.add_discovered_source(source_info):
                        new_sources.append(source_info)
                        existing_urls.add(source_info['url'])
                
                time.sleep(DISCOVERY_RATE_LIMIT)
        
        if new_sources:
            logger.info(f"Discovered {len(new_sources)} new sources!")
        
        return new_sources
    
    async def discover_new_sources_async(
        self,
        max_new_sources: int = 5,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Async version of discover_new_sources.
        
        Args:
            max_new_sources: Maximum number of new sources to discover.
            query: Optional specific query.
        
        Returns:
            List of newly discovered source dictionaries.
        """
        logger.info("Starting async source discovery...")
        new_sources: List[Dict[str, Any]] = []
        existing_urls = {src['url'] for src in self.db.discovered_sources}
        
        queries = [query] if query else DISCOVERY_QUERIES[:3]
        
        async with aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT}
        ) as session:
            for q in queries:
                if len(new_sources) >= max_new_sources:
                    break
                
                # Use APIs async if available
                potential_urls: List[str] = []
                
                if self.api_available["google"]:
                    potential_urls = await self.search_google_api_async(
                        session, q, max_results=5
                    )
                elif self.api_available["bing"]:
                    potential_urls = await self.search_bing_api_async(
                        session, q, max_results=5
                    )
                else:
                    # Fallback to sync web scraping
                    potential_urls = self._scrape_search_engines(q, max_results=5)
                
                # Verify sources concurrently
                tasks = []
                for url in potential_urls:
                    if url in existing_urls:
                        continue
                    tasks.append(self.verify_source_async(session, url))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if len(new_sources) >= max_new_sources:
                        break
                    
                    if isinstance(result, dict) and result:
                        if self.db.add_discovered_source(result):
                            new_sources.append(result)
                            existing_urls.add(result['url'])
        
        if new_sources:
            logger.info(f"Discovered {len(new_sources)} new sources!")
        
        return new_sources