"""
Main Orchestrator for the Tech News Scraper.

This module provides the central coordination layer that ties
together all components into a unified, high-performance
tech news scraping system.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

# Local imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.core.types import (
    Article,
    QueryIntent,
    QueryResult,
    ScrapingResult,
    ScrapingStatus,
    Source,
    SourceTier,
    TechScore,
)
from src.core.exceptions import (
    NonTechQueryError,
    InvalidQueryError,
    TechScraperError,
)
from src.data_structures import (
    URLDeduplicator,
    SourcePriorityQueue,
    HTTPResponseCache,
)
from src.engine.query_engine import QueryEngine
from src.engine.deep_scraper import DeepScraper
from src.engine.url_analyzer import URLAnalyzer, URLAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """
    Result of a search operation.
    
    Attributes:
        query: Original query
        query_result: Query analysis result
        articles: Found articles
        total_sources_scraped: Number of sources scraped
        total_time_ms: Total time taken
        errors: Any errors encountered
    """
    query: str
    query_result: QueryResult
    articles: List[Article]
    total_sources_scraped: int
    total_time_ms: float
    errors: List[str] = field(default_factory=list)


# Premium tech news sources (Tier 1)
PREMIUM_SOURCES = [
    {
        "url": "https://techcrunch.com",
        "name": "TechCrunch",
        "tier": SourceTier.TIER_1,
    },
    {
        "url": "https://www.theverge.com",
        "name": "The Verge",
        "tier": SourceTier.TIER_1,
    },
    {
        "url": "https://arstechnica.com",
        "name": "Ars Technica",
        "tier": SourceTier.TIER_1,
    },
    {
        "url": "https://www.wired.com",
        "name": "Wired",
        "tier": SourceTier.TIER_1,
    },
    {
        "url": "https://www.technologyreview.com",
        "name": "MIT Technology Review",
        "tier": SourceTier.TIER_1,
    },
]

# High-quality tech sources (Tier 2)
QUALITY_SOURCES = [
    {
        "url": "https://news.ycombinator.com",
        "name": "Hacker News",
        "tier": SourceTier.TIER_2,
    },
    {
        "url": "https://www.engadget.com",
        "name": "Engadget",
        "tier": SourceTier.TIER_2,
    },
    {
        "url": "https://gizmodo.com",
        "name": "Gizmodo",
        "tier": SourceTier.TIER_2,
    },
    {
        "url": "https://venturebeat.com",
        "name": "VentureBeat",
        "tier": SourceTier.TIER_2,
    },
    {
        "url": "https://www.zdnet.com",
        "name": "ZDNet",
        "tier": SourceTier.TIER_2,
    },
]


class TechNewsOrchestrator:
    """
    Central orchestrator for the Tech News Scraper.
    
    Coordinates all components to provide a unified interface
    for intelligent tech news scraping with:
    
    - Query understanding and validation
    - Multi-source deep scraping
    - URL deep analysis
    - Source priority management
    - Result aggregation and ranking
    
    Example:
        orchestrator = TechNewsOrchestrator()
        
        # Search for tech news
        result = await orchestrator.search("artificial intelligence breakthroughs")
        for article in result.articles:
            print(f"- {article.title}")
        
        # Analyze specific URL
        analysis = await orchestrator.analyze_url("https://example.com/article")
        print(analysis.key_points)
    """
    
    def __init__(
        self,
        enable_cache: bool = True,
        max_concurrent_scrapes: int = 5,
    ) -> None:
        """
        Initialize the orchestrator.
        
        Args:
            enable_cache: Whether to enable response caching
            max_concurrent_scrapes: Maximum concurrent scraping operations
        """
        # Initialize components
        self._query_engine = QueryEngine(tech_threshold=0.3)
        self._scraper = DeepScraper(max_concurrent=max_concurrent_scrapes)
        self._url_analyzer = URLAnalyzer()
        
        # Initialize source queue with premium sources
        self._source_queue = SourcePriorityQueue()
        self._initialize_sources()
        
        # URL deduplication
        self._url_dedup = URLDeduplicator(expected_urls=100_000)
        
        # Article storage (in-memory)
        self._articles: List[Article] = []
        
        # Statistics
        self._stats = {
            "queries_processed": 0,
            "queries_rejected": 0,
            "urls_analyzed": 0,
            "articles_scraped": 0,
            "sources_scraped": 0,
        }
        
        logger.info("TechNewsOrchestrator initialized")
    
    def _initialize_sources(self) -> None:
        """Initialize source queue with known sources."""
        all_sources = PREMIUM_SOURCES + QUALITY_SOURCES
        
        for source_data in all_sources:
            source = {
                "url": source_data["url"],
                "name": source_data["name"],
                "tier": source_data["tier"].value,
                "success_rate": 1.0,
                "article_rate": 0.5,
                "last_scraped": 0,
            }
            self._source_queue.add_source(source)
        
        logger.info(f"Initialized {len(all_sources)} sources")
    
    async def search(
        self,
        query: str,
        max_articles: int = 20,
        max_sources: int = 5,
    ) -> SearchResult:
        """
        Search for tech news matching the query.
        
        Analyzes the query, validates tech relevance, and scrapes
        multiple sources for matching articles.
        
        Args:
            query: User search query
            max_articles: Maximum articles to return
            max_sources: Maximum sources to scrape
        
        Returns:
            SearchResult with found articles
        
        Raises:
            NonTechQueryError: If query is not tech-related
            InvalidQueryError: If query is malformed
        """
        logger.info(f"Searching: {query}")
        start_time = time.time()
        errors: List[str] = []
        
        # Analyze query
        try:
            query_result = self._query_engine.analyze_strict(query)
        except NonTechQueryError as e:
            self._stats["queries_rejected"] += 1
            raise
        except InvalidQueryError as e:
            self._stats["queries_rejected"] += 1
            raise
        
        self._stats["queries_processed"] += 1
        
        # Handle different intents
        if query_result.intent == QueryIntent.ANALYZE_URL:
            # Extract URL and analyze
            import re
            urls = re.findall(r'https?://[^\s]+', query)
            if urls:
                analysis = await self.analyze_url(urls[0])
                if analysis:
                    return SearchResult(
                        query=query,
                        query_result=query_result,
                        articles=[analysis.article],
                        total_sources_scraped=1,
                        total_time_ms=(time.time() - start_time) * 1000,
                    )
        
        # Get search terms for filtering
        search_terms = self._query_engine.get_search_terms(query_result)
        
        # Scrape sources
        articles: List[Article] = []
        sources_scraped = 0
        
        # Get top sources
        sources = self._source_queue.get_all_sources_ordered()[:max_sources]
        
        # Scrape concurrently
        tasks = [
            self._scrape_source_with_filter(source, search_terms)
            for source in sources
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, ScrapingResult):
                sources_scraped += 1
                self._stats["sources_scraped"] += 1
                
                for article in result.articles:
                    if not self._url_dedup.is_duplicate(article.url):
                        articles.append(article)
                        self._url_dedup.add(article.url)
                        self._articles.append(article)
                        self._stats["articles_scraped"] += 1
            
            elif isinstance(result, Exception):
                errors.append(str(result))
        
        # Sort by tech score and limit
        articles.sort(
            key=lambda a: a.tech_score.score if a.tech_score else 0,
            reverse=True
        )
        articles = articles[:max_articles]
        
        total_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Search complete: {len(articles)} articles from "
            f"{sources_scraped} sources in {total_time:.0f}ms"
        )
        
        return SearchResult(
            query=query,
            query_result=query_result,
            articles=articles,
            total_sources_scraped=sources_scraped,
            total_time_ms=total_time,
            errors=errors,
        )
    
    async def _scrape_source_with_filter(
        self,
        source: Dict[str, Any],
        search_terms: List[str],
    ) -> ScrapingResult:
        """Scrape a source and filter by search terms."""
        result = await self._scraper.scrape_source(source["url"])
        
        if not search_terms:
            return result
        
        # Filter articles by search terms
        terms_lower = [t.lower() for t in search_terms]
        filtered_articles = []
        
        for article in result.articles:
            content_lower = (article.title + " " + article.content).lower()
            if any(term in content_lower for term in terms_lower):
                filtered_articles.append(article)
        
        return ScrapingResult(
            status=result.status,
            articles=tuple(filtered_articles),
            source=result.source,
            duration_ms=result.duration_ms,
            error_message=result.error_message,
        )
    
    async def analyze_url(self, url: str) -> Optional[URLAnalysisResult]:
        """
        Perform deep analysis of a specific URL.
        
        Args:
            url: URL to analyze
        
        Returns:
            URLAnalysisResult with comprehensive analysis
        """
        logger.info(f"Analyzing URL: {url}")
        self._stats["urls_analyzed"] += 1
        
        result = await self._url_analyzer.analyze(url)
        
        if result:
            # Add to articles if valid
            if not self._url_dedup.is_duplicate(url):
                self._url_dedup.add(url)
                self._articles.append(result.article)
        
        return result
    
    def format_url_analysis(self, result: URLAnalysisResult) -> str:
        """Format URL analysis as readable report."""
        return self._url_analyzer.format_analysis_report(result)
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a query without executing search.
        
        Args:
            query: Query to validate
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        try:
            result = self._query_engine.analyze(query)
            if result.is_accepted:
                return True, None
            else:
                return False, result.rejection_reason
        except Exception as e:
            return False, str(e)
    
    def suggest_queries(self, failed_query: str) -> List[str]:
        """Get suggested tech queries for a rejected query."""
        return self._query_engine.suggest_tech_queries(failed_query)
    
    def get_latest_articles(self, count: int = 10) -> List[Article]:
        """Get the latest scraped articles."""
        return sorted(
            self._articles,
            key=lambda a: a.scraped_at,
            reverse=True
        )[:count]
    
    def get_top_articles(self, count: int = 10) -> List[Article]:
        """Get top articles by tech score."""
        return sorted(
            self._articles,
            key=lambda a: a.tech_score.score if a.tech_score else 0,
            reverse=True
        )[:count]
    
    def search_articles(self, query: str) -> List[Article]:
        """Search through scraped articles (local search)."""
        query_lower = query.lower()
        matches = []
        
        for article in self._articles:
            content = (article.title + " " + article.content).lower()
            if query_lower in content:
                matches.append(article)
        
        return matches
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            **self._stats,
            "total_articles": len(self._articles),
            "total_sources": len(self._source_queue),
            "scraper_stats": self._scraper.stats,
        }
    
    @property
    def source_count(self) -> int:
        """Get number of configured sources."""
        return len(self._source_queue)
    
    @property
    def article_count(self) -> int:
        """Get number of scraped articles."""
        return len(self._articles)
