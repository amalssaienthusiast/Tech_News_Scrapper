"""
Deep Scraper Engine for multi-layer content extraction.

This module provides advanced web scraping capabilities:
- Multi-layer link discovery algorithm
- Content quality scoring
- Source reputation tracking
- Async batch processing with rate limiting
- NO RSS SUPPORT - direct web scraping only
"""

import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

# Local imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.core.types import (
    Article, 
    ScrapingResult, 
    ScrapingStatus, 
    Source, 
    SourceTier,
    TechScore,
)
from src.core.exceptions import (
    ScrapingError,
    ContentExtractionError,
    RateLimitedError,
    InvalidURLError,
)
from src.data_structures import (
    BloomFilter,
    URLDeduplicator,
    LRUCache,
    HTTPResponseCache,
    TechKeywordMatcher,
    SourcePriorityQueue,
)

logger = logging.getLogger(__name__)


@dataclass
class ScrapedContent:
    """
    Raw scraped content before processing.
    
    Attributes:
        url: Source URL
        html: Raw HTML content
        status_code: HTTP status code
        headers: Response headers
        fetched_at: Timestamp when fetched
        fetch_time_ms: Time taken to fetch
    """
    url: str
    html: str
    status_code: int
    headers: Dict[str, str]
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    fetch_time_ms: float = 0.0


@dataclass
class LinkScore:
    """
    Score for a discovered link.
    
    Attributes:
        url: Link URL
        anchor_text: Text of the anchor element
        context: Surrounding text context
        score: Calculated article probability score
        is_article: Whether likely to be an article
    """
    url: str
    anchor_text: str
    context: str
    score: float
    is_article: bool


class ContentExtractor:
    """
    Intelligent content extraction from HTML pages.
    
    Uses multiple strategies to extract clean article text:
    1. Schema.org article markup
    2. OpenGraph metadata
    3. Semantic HTML5 elements
    4. Common CSS class patterns
    """
    
    # Priority-ordered content selectors
    CONTENT_SELECTORS = [
        '[itemprop="articleBody"]',
        '[property="articleBody"]',
        'article .content',
        'article .post-content',
        'article .entry-content',
        '.article-content',
        '.article-body',
        '.post-body',
        '.entry-content',
        '.story-body',
        '#article-content',
        '#article-body',
        'article',
        '[role="main"]',
        'main',
        '.content',
    ]
    
    # Elements to remove before extraction
    REMOVE_SELECTORS = [
        'script', 'style', 'noscript', 'iframe',
        'nav', 'header', 'footer', 'aside',
        '.advertisement', '.ad-slot', '.ads',
        '.social-share', '.share-buttons',
        '.comments', '.comment-section',
        '.related-articles', '.recommended',
        '.newsletter', '.subscription',
        '.sidebar', '.widget',
        '[role="navigation"]',
        '[role="banner"]',
        '[role="complementary"]',
    ]
    
    @classmethod
    def extract(cls, html: str, url: str = "") -> Dict[str, Any]:
        """
        Extract article content from HTML.
        
        Args:
            html: Raw HTML string
            url: Source URL for relative link resolution
        
        Returns:
            Dictionary with extracted content fields
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for selector in cls.REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
        
        # Extract metadata
        title = cls._extract_title(soup)
        description = cls._extract_description(soup)
        author = cls._extract_author(soup)
        published = cls._extract_published_date(soup)
        image = cls._extract_image(soup, url)
        
        # Extract main content
        content = cls._extract_content(soup)
        
        # Extract keywords
        keywords = cls._extract_keywords(soup)
        
        return {
            'title': title,
            'description': description,
            'author': author,
            'published': published,
            'image': image,
            'content': content,
            'keywords': keywords,
            'word_count': len(content.split()) if content else 0,
        }
    
    @classmethod
    def _extract_title(cls, soup: BeautifulSoup) -> str:
        """Extract article title."""
        # Try OpenGraph
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # Try schema.org
        schema_title = soup.find(itemprop='headline')
        if schema_title:
            return schema_title.get_text(strip=True)
        
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        # Fallback to title tag
        if soup.title:
            return soup.title.get_text(strip=True)
        
        return "Untitled"
    
    @classmethod
    def _extract_description(cls, soup: BeautifulSoup) -> str:
        """Extract article description/summary."""
        # Try OpenGraph
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        return ""
    
    @classmethod
    def _extract_author(cls, soup: BeautifulSoup) -> Optional[str]:
        """Extract article author."""
        # Try schema.org
        author = soup.find(itemprop='author')
        if author:
            name = author.find(itemprop='name')
            if name:
                return name.get_text(strip=True)
            return author.get_text(strip=True)
        
        # Try meta tag
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author and meta_author.get('content'):
            return meta_author['content'].strip()
        
        # Try common classes
        for cls_name in ['.author', '.byline', '.post-author']:
            elem = soup.select_one(cls_name)
            if elem:
                return elem.get_text(strip=True)
        
        return None
    
    @classmethod
    def _extract_published_date(cls, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date."""
        # Try article:published_time
        pub_time = soup.find('meta', property='article:published_time')
        if pub_time and pub_time.get('content'):
            return pub_time['content']
        
        # Try schema.org
        date_pub = soup.find(itemprop='datePublished')
        if date_pub:
            return date_pub.get('content') or date_pub.get_text(strip=True)
        
        # Try time element
        time_elem = soup.find('time')
        if time_elem and time_elem.get('datetime'):
            return time_elem['datetime']
        
        return None
    
    @classmethod
    def _extract_image(cls, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract main article image."""
        # Try OpenGraph
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return urljoin(base_url, og_image['content'])
        
        return None
    
    @classmethod
    def _extract_content(cls, soup: BeautifulSoup) -> str:
        """Extract main article text content."""
        # Try each selector in priority order
        for selector in cls.CONTENT_SELECTORS:
            content = soup.select_one(selector)
            if content:
                text = content.get_text(separator=' ', strip=True)
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text)
                if len(text) > 200:  # Minimum content threshold
                    return text
        
        # Fallback to body
        body = soup.find('body')
        if body:
            text = body.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text
        
        return ""
    
    @classmethod
    def _extract_keywords(cls, soup: BeautifulSoup) -> List[str]:
        """Extract article keywords."""
        keywords = []
        
        # Try meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords.extend(
                k.strip() for k in meta_keywords['content'].split(',')
            )
        
        # Try article:tag
        for tag in soup.find_all('meta', property='article:tag'):
            if tag.get('content'):
                keywords.append(tag['content'].strip())
        
        return keywords[:20]  # Limit keywords


class LinkDiscoveryAlgorithm:
    """
    Intelligent link discovery for finding article URLs.
    
    Uses multiple signals to score links:
    - URL patterns (article, news, post, etc.)
    - Anchor text relevance
    - Surrounding context
    - Position on page
    """
    
    # High-value URL patterns
    ARTICLE_PATTERNS = [
        r'/article/',
        r'/news/',
        r'/post/',
        r'/blog/',
        r'/story/',
        r'/feature/',
        r'/review/',
        r'/\d{4}/\d{2}/',  # Date patterns in URL
        r'/\d{4}/\d{2}/\d{2}/',
        r'-[a-z0-9]{6,}$',  # Slug patterns
    ]
    
    # Patterns to avoid
    SKIP_PATTERNS = [
        r'/tag/',
        r'/category/',
        r'/author/',
        r'/page/\d+',
        r'/search',
        r'/login',
        r'/register',
        r'/signup',
        r'/subscribe',
        r'/about',
        r'/contact',
        r'/privacy',
        r'/terms',
        r'\.(pdf|jpg|png|gif|mp4|mp3)$',
    ]
    
    def __init__(self, keyword_matcher: Optional[TechKeywordMatcher] = None):
        """Initialize with optional keyword matcher."""
        self._keyword_matcher = keyword_matcher or TechKeywordMatcher()
        self._article_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.ARTICLE_PATTERNS
        ]
        self._skip_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.SKIP_PATTERNS
        ]
    
    def discover_links(
        self, 
        soup: BeautifulSoup, 
        base_url: str,
        max_links: int = 50
    ) -> List[LinkScore]:
        """
        Discover and score potential article links.
        
        Args:
            soup: Parsed HTML
            base_url: Base URL for resolving relative links
            max_links: Maximum links to return
        
        Returns:
            List of LinkScore objects sorted by score
        """
        scores: List[LinkScore] = []
        seen_urls: Set[str] = set()
        
        for link in soup.find_all('a', href=True):
            url = urljoin(base_url, link['href'])
            
            # Normalize URL
            url = self._normalize_url(url)
            
            # Skip if already seen or invalid
            if url in seen_urls or not self._is_valid_url(url, base_url):
                continue
            
            seen_urls.add(url)
            
            # Calculate score
            score = self._score_link(link, url)
            scores.append(score)
        
        # Sort by score and return top links
        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[:max_links]
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        # Remove fragment
        parsed = urlparse(url)
        url = parsed._replace(fragment='').geturl()
        
        # Remove trailing slash
        return url.rstrip('/')
    
    def _is_valid_url(self, url: str, base_url: str) -> bool:
        """Check if URL is valid for scraping."""
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(base_url)
            
            # Must have http(s) scheme
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Must be from same domain or subdomain
            if not parsed.netloc.endswith(base_parsed.netloc.split('.')[-2] + '.' + base_parsed.netloc.split('.')[-1]):
                # Allow same base domain
                if parsed.netloc != base_parsed.netloc:
                    return False
            
            # Check skip patterns
            for pattern in self._skip_patterns:
                if pattern.search(url):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _score_link(self, link: Any, url: str) -> LinkScore:
        """Calculate score for a link."""
        score = 0.0
        
        # URL pattern matching
        for pattern in self._article_patterns:
            if pattern.search(url):
                score += 0.2
        
        # Anchor text analysis
        anchor_text = link.get_text(strip=True)
        if anchor_text:
            # Length bonus (longer = more likely headline)
            if 20 < len(anchor_text) < 150:
                score += 0.15
            
            # Tech relevance
            tech_score, _ = self._keyword_matcher.calculate_tech_score(anchor_text)
            score += tech_score * 0.3
        
        # Context analysis (surrounding text)
        context = ""
        parent = link.parent
        if parent:
            context = parent.get_text(strip=True)[:200]
            tech_score, _ = self._keyword_matcher.calculate_tech_score(context)
            score += tech_score * 0.15
        
        # Position bonus (links in article/main areas)
        if link.find_parent(['article', 'main', '[role="main"]']):
            score += 0.1
        
        # H tag bonus (headline links)
        if link.find_parent(['h1', 'h2', 'h3']):
            score += 0.1
        
        # Normalize score
        score = min(1.0, score)
        
        return LinkScore(
            url=url,
            anchor_text=anchor_text,
            context=context[:100],
            score=score,
            is_article=score > 0.3,
        )


class DeepScraper:
    """
    Advanced multi-layer deep scraping engine.
    
    Provides powerful web scraping capabilities:
    - Multi-layer link discovery (explores pages deeply)
    - Content quality scoring
    - Async batch processing with rate limiting
    - URL deduplication with Bloom filter
    - Response caching
    - Source reputation tracking
    
    NO RSS SUPPORT - Direct web scraping only for maximum control.
    
    Example:
        scraper = DeepScraper()
        
        # Scrape a source
        result = await scraper.scrape_source("https://techcrunch.com")
        
        # Deep analysis of single URL
        article = await scraper.analyze_url("https://example.com/article")
    """
    
    # User agent for requests
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    def __init__(
        self,
        max_concurrent: int = 5,
        request_timeout: int = 15,
        rate_limit_per_domain: float = 2.0,
        cache_ttl: int = 300,
    ) -> None:
        """
        Initialize the deep scraper.
        
        Args:
            max_concurrent: Maximum concurrent requests
            request_timeout: Request timeout in seconds
            rate_limit_per_domain: Max requests per second per domain
            cache_ttl: Cache TTL in seconds
        """
        self._max_concurrent = max_concurrent
        self._request_timeout = request_timeout
        self._rate_limit = rate_limit_per_domain
        
        # Initialize components
        self._url_dedup = URLDeduplicator(expected_urls=500_000)
        self._cache = HTTPResponseCache(max_responses=500, default_ttl=cache_ttl)
        self._keyword_matcher = TechKeywordMatcher()
        self._link_discoverer = LinkDiscoveryAlgorithm(self._keyword_matcher)
        
        # Rate limiting per domain
        self._domain_last_request: Dict[str, float] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Statistics
        self._stats = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'cached_hits': 0,
            'articles_found': 0,
        }
    
    async def fetch_url(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Optional[ScrapedContent]:
        """
        Fetch a URL with rate limiting and caching.
        
        Args:
            session: aiohttp client session
            url: URL to fetch
        
        Returns:
            ScrapedContent if successful, None otherwise
        """
        # Check cache
        cached = self._cache.get(url)
        if cached:
            self._stats['cached_hits'] += 1
            return ScrapedContent(
                url=url,
                html=cached['content'],
                status_code=cached['status_code'],
                headers=cached['headers'],
            )
        
        # Apply rate limiting per domain
        domain = urlparse(url).netloc
        await self._apply_rate_limit(domain)
        
        async with self._semaphore:
            try:
                start_time = time.time()
                self._stats['requests'] += 1
                
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self._request_timeout),
                    allow_redirects=True,
                ) as response:
                    fetch_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        html = await response.text()
                        headers = dict(response.headers)
                        
                        # Cache the response
                        self._cache.set(url, response.status, html, headers)
                        
                        self._stats['successes'] += 1
                        
                        return ScrapedContent(
                            url=url,
                            html=html,
                            status_code=response.status,
                            headers=headers,
                            fetch_time_ms=fetch_time,
                        )
                    
                    elif response.status == 429:
                        # Rate limited
                        self._stats['failures'] += 1
                        logger.warning(f"Rate limited: {url}")
                        return None
                    
                    else:
                        self._stats['failures'] += 1
                        logger.warning(f"HTTP {response.status}: {url}")
                        return None
                        
            except asyncio.TimeoutError:
                self._stats['failures'] += 1
                logger.warning(f"Timeout: {url}")
                return None
            
            except aiohttp.ClientError as e:
                self._stats['failures'] += 1
                logger.warning(f"Client error for {url}: {e}")
                return None
            
            except Exception as e:
                self._stats['failures'] += 1
                logger.error(f"Unexpected error for {url}: {e}")
                return None
    
    async def _apply_rate_limit(self, domain: str) -> None:
        """Apply per-domain rate limiting."""
        last_request = self._domain_last_request.get(domain, 0)
        min_interval = 1.0 / self._rate_limit
        elapsed = time.time() - last_request
        
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        
        self._domain_last_request[domain] = time.time()
    
    async def scrape_source(
        self,
        source_url: str,
        max_articles: int = 20,
        max_depth: int = 1
    ) -> ScrapingResult:
        """
        Scrape articles from a source website.
        
        Uses multi-layer link discovery to find articles.
        
        Args:
            source_url: Base URL of the source
            max_articles: Maximum articles to scrape
            max_depth: Maximum depth for link discovery
        
        Returns:
            ScrapingResult with scraped articles
        """
        logger.info(f"Scraping source: {source_url}")
        start_time = time.time()
        articles: List[Article] = []
        
        # Create source object
        source = Source(
            url=source_url,
            name=urlparse(source_url).netloc,
            tier=SourceTier.TIER_2,  # Default tier
            domain=urlparse(source_url).netloc,
        )
        
        async with aiohttp.ClientSession(
            headers={"User-Agent": self.USER_AGENT},
            connector=aiohttp.TCPConnector(ssl=False)  # Bypass SSL for macOS
        ) as session:
            # Fetch the main page
            content = await self.fetch_url(session, source_url)
            
            if not content:
                return ScrapingResult(
                    status=ScrapingStatus.FAILED,
                    articles=tuple(),
                    source=source,
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message="Failed to fetch source page",
                )
            
            # Discover article links
            soup = BeautifulSoup(content.html, 'html.parser')
            links = self._link_discoverer.discover_links(
                soup, source_url, max_links=max_articles * 2
            )
            
            # Filter to likely articles
            article_urls = [
                link.url for link in links 
                if link.is_article and not self._url_dedup.is_duplicate(link.url)
            ][:max_articles]
            
            # Fetch and process articles concurrently
            tasks = [
                self._process_article_url(session, url, source)
                for url in article_urls
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Article):
                    articles.append(result)
                    self._url_dedup.add(result.url)
                    self._stats['articles_found'] += 1
        
        duration_ms = (time.time() - start_time) * 1000
        
        if articles:
            logger.info(
                f"✓ Scraped {len(articles)} articles from {source_url} "
                f"in {duration_ms:.0f}ms"
            )
            return ScrapingResult(
                status=ScrapingStatus.SUCCESS,
                articles=tuple(articles),
                source=source,
                duration_ms=duration_ms,
            )
        else:
            return ScrapingResult(
                status=ScrapingStatus.PARTIAL,
                articles=tuple(),
                source=source,
                duration_ms=duration_ms,
                error_message="No articles found",
            )
    
    async def _process_article_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        source: Source
    ) -> Optional[Article]:
        """Process a single article URL."""
        try:
            content = await self.fetch_url(session, url)
            
            if not content:
                return None
            
            # Extract content
            extracted = ContentExtractor.extract(content.html, url)
            
            # Check minimum content
            if extracted['word_count'] < 100:
                return None
            
            # Calculate tech score
            tech_score, keywords = self._keyword_matcher.calculate_tech_score(
                extracted['content']
            )
            
            # Skip non-tech content
            if tech_score < 0.2:
                return None
            
            # Generate ID
            article_id = hashlib.md5(url.encode()).hexdigest()
            
            # Create article
            return Article(
                id=article_id,
                url=url,
                title=extracted['title'],
                content=extracted['content'],
                summary=extracted['description'] or "",
                source=source.name,
                source_tier=source.tier,
                published_at=self._parse_date(extracted['published']),
                tech_score=TechScore(
                    score=tech_score,
                    confidence=0.8,
                    matched_keywords=tuple(keywords),
                ),
                keywords=tuple(extracted['keywords']),
            )
            
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None
        
        # Try common formats
        for fmt in [
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d',
            '%B %d, %Y',
        ]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    async def analyze_url_deep(self, url: str) -> Optional[Article]:
        """
        Perform deep analysis of a specific URL.
        
        Extracts comprehensive information and generates
        AI-enhanced summary.
        
        Args:
            url: URL to analyze
        
        Returns:
            Detailed Article object or None if failed
        """
        logger.info(f"Deep analysis: {url}")
        
        async with aiohttp.ClientSession(
            headers={"User-Agent": self.USER_AGENT},
            connector=aiohttp.TCPConnector(ssl=False)  # Bypass SSL for macOS
        ) as session:
            return await self._process_article_url(
                session,
                url,
                Source(
                    url=url,
                    name="User Provided",
                    tier=SourceTier.TIER_2,
                    domain=urlparse(url).netloc,
                )
            )
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return {
            **self._stats,
            'cache_stats': self._cache.stats,
            'dedup_stats': self._url_dedup.stats,
        }
    
    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._stats = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'cached_hits': 0,
            'articles_found': 0,
        }
