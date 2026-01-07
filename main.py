"""
Main application entry point for the Tech News Scraper.

This module provides the main orchestration layer for the tech news
scraper, coordinating database, scraper, discovery, and AI components
into a unified agent interface.
"""

import asyncio
import logging
import logging.handlers
import queue
import threading
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from config.settings import (
    CHECK_INTERVAL,
    GLOBAL_TOPICS,
    LOG_FORMAT,
    LOG_LEVEL,
    LOGS_DIR,
)
from src.ai_processor import (
    build_search_index,
    initialize_ai_models,
    semantic_search,
)
from src.database import Database
from src.discovery import WebDiscoveryAgent
from src.scraper import TechNewsScraper

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / 'tech_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TechNewsAgent:
    """
    Main application class that coordinates all components.
    
    The TechNewsAgent serves as the central orchestrator, providing
    a unified interface to the database, scraper, discovery, and
    AI processing components.
    
    Attributes:
        db: Database instance for article and source storage.
        scraper: Scraper instance for fetching articles.
        discovery_agent: Discovery agent for finding new sources.
        ai_available: Whether AI models are successfully loaded.
        article_embeddings: Cached embeddings for semantic search.
    
    Example:
        agent = TechNewsAgent()
        
        # Run scraping cycle
        new_articles = agent.run_scrape_cycle()
        
        # Search articles
        results = agent.search("artificial intelligence", top_k=5)
    """
    
    def __init__(self, log_queue: Optional[queue.Queue] = None) -> None:
        """
        Initialize the Tech News Agent.
        
        Args:
            log_queue: Optional queue for GUI log forwarding.
        """
        # Initialize database
        self.db = Database()
        
        # Initialize scraper
        self.scraper = TechNewsScraper(self.db)
        
        # Initialize discovery agent
        self.discovery_agent = WebDiscoveryAgent(self.db)
        
        # Initialize AI models
        self.ai_available = initialize_ai_models()
        
        # Search index
        self.article_embeddings: Any = None
        
        # Set up logging to queue if provided
        if log_queue:
            self.log_queue = log_queue
            queue_handler = logging.handlers.QueueHandler(log_queue)
            queue_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(queue_handler)
        
        # Build initial search index
        self.build_search_index()
        
        logger.info("Tech News Agent initialized successfully")
    
    def build_search_index(self) -> None:
        """
        Build semantic search index from articles.
        
        Creates embeddings for all articles in the database for
        efficient semantic search. Skips if AI models unavailable.
        """
        if not self.ai_available:
            logger.warning(
                "AI models not available. Search functionality limited."
            )
            return
        
        self.article_embeddings = build_search_index(self.db.articles)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Semantic search for articles.
        
        Args:
            query: Search query string.
            top_k: Number of results to return.
        
        Returns:
            List of result dicts with 'score' and 'article' keys.
        """
        if not self.ai_available or self.article_embeddings is None:
            logger.error("Search functionality not available.")
            return []
        
        return semantic_search(
            query, 
            self.article_embeddings, 
            self.db.articles, 
            top_k
        )
    
    def run_scrape_cycle(self) -> int:
        """
        Run a complete scraping cycle.
        
        Returns:
            Number of new articles found.
        """
        new_articles = self.scraper.run_scrape_cycle()
        if new_articles > 0:
            self.build_search_index()
        return new_articles
    
    async def run_scrape_cycle_async(self) -> int:
        """
        Run a complete async scraping cycle.
        
        Returns:
            Number of new articles found.
        """
        new_articles = await self.scraper.run_scrape_cycle_async()
        if new_articles > 0:
            self.build_search_index()
        return new_articles
    
    def discover_new_sources(self, max_new: int = 3) -> List[Dict[str, Any]]:
        """
        Discover new sources.
        
        Args:
            max_new: Maximum number of new sources to discover.
        
        Returns:
            List of newly discovered source dictionaries.
        """
        return self.discovery_agent.discover_new_sources(max_new_sources=max_new)
    
    def process_single_url(
        self, 
        url: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Process a single URL.
        
        Args:
            url: URL to process.
        
        Returns:
            Tuple of (success, message, article_dict).
        """
        result = self.scraper.process_single_url(url)
        if result[0]:  # If successful
            self.build_search_index()
        return result
    
    def search_and_scrape_web(self, query: str) -> Tuple[int, int]:
        """
        Search and scrape web for a topic.
        
        Args:
            query: Search topic.
        
        Returns:
            Tuple of (num_sources, num_articles).
        """
        result = self.scraper.search_and_scrape_web(query)
        if result[1] > 0:  # If new articles found
            self.build_search_index()
        return result
    
    def auto_discovery_cycle(self) -> Tuple[str, int, int]:
        """
        Autonomous discovery cycle.
        
        Randomly selects a global topic and searches for sources/articles.
        
        Returns:
            Tuple of (topic, num_sources, num_articles).
        """
        import random
        topic = random.choice(GLOBAL_TOPICS)
        logger.info(f"🤖 Auto-Discovery: Selected topic '{topic}'")
        
        num_sources, num_articles = self.search_and_scrape_web(topic)
        
        return topic, num_sources, num_articles
    
    def get_source_stats(self) -> Dict[str, int]:
        """
        Get source statistics.
        
        Returns:
            Dictionary with source and article counts.
        """
        return self.scraper.get_source_stats()
    
    def get_latest_articles(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get latest articles.
        
        Args:
            count: Number of articles to return.
        
        Returns:
            List of article dictionaries.
        """
        return self.scraper.get_latest_articles(count)
    
    def save_url_to_txt(self, url: str) -> Optional[str]:
        """
        Save URL content to text file.
        
        Args:
            url: URL to save.
        
        Returns:
            Path to saved file if successful.
        """
        return self.scraper.save_url_to_txt(url)


async def daemon_loop_async(
    agent: TechNewsAgent, 
    auto_discovery: bool = True
) -> None:
    """
    Async background daemon loop for periodic scraping.
    
    Args:
        agent: TechNewsAgent instance.
        auto_discovery: Enable auto-discovery of new sources.
    """
    while True:
        try:
            # Regular scrape cycle
            logger.info("🤖 Daemon: Starting async scrape cycle...")
            await agent.run_scrape_cycle_async()
            
            # Auto-discovery cycle if enabled
            if auto_discovery:
                logger.info("🤖 Daemon: Starting Auto-Discovery...")
                try:
                    topic, sources, articles = agent.auto_discovery_cycle()
                    if sources > 0:
                        logger.info(
                            f"✨ Auto-Discovery: Found {sources} sources "
                            f"for '{topic}'"
                        )
                    else:
                        logger.info(
                            f"🤖 Auto-Discovery: No new sources for '{topic}'"
                        )
                except Exception as e:
                    logger.error(f"⚠️ Auto-Discovery Error: {e}")
            
            logger.info(
                f"✓ Daemon: Cycle finished. Next run in {CHECK_INTERVAL}s"
            )
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in async daemon loop: {e}")
            await asyncio.sleep(60)


def daemon_loop(agent: TechNewsAgent, auto_discovery: bool = True) -> None:
    """
    Background daemon loop for periodic scraping (sync version).
    
    Args:
        agent: TechNewsAgent instance.
        auto_discovery: Enable auto-discovery of new sources.
    """
    while True:
        try:
            # Regular scrape cycle
            logger.info("🤖 Daemon: Starting automatic scrape cycle...")
            agent.run_scrape_cycle()
            
            # Auto-discovery cycle if enabled
            if auto_discovery:
                logger.info("🤖 Daemon: Starting Auto-Discovery...")
                try:
                    topic, sources, articles = agent.auto_discovery_cycle()
                    if sources > 0:
                        logger.info(
                            f"✨ Auto-Discovery: Found {sources} sources "
                            f"for '{topic}'"
                        )
                    else:
                        logger.info(
                            f"🤖 Auto-Discovery: No new sources for '{topic}'"
                        )
                except Exception as e:
                    logger.error(f"⚠️ Auto-Discovery Error: {e}")
            
            logger.info(
                f"✓ Daemon: Cycle finished. Next run in {CHECK_INTERVAL}s"
            )
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in daemon loop: {e}")
            time.sleep(60)


def main() -> None:
    """Main entry point for CLI mode."""
    # Initialize agent
    agent = TechNewsAgent()
    
    # Start daemon thread
    daemon_thread = threading.Thread(
        target=daemon_loop,
        args=(agent, True),
        daemon=True
    )
    daemon_thread.start()
    
    logger.info("Tech News Agent started successfully")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Tech News Agent...")


async def main_async() -> None:
    """Main entry point for fully async mode."""
    agent = TechNewsAgent()
    logger.info("Tech News Agent started in async mode")
    
    try:
        await daemon_loop_async(agent, auto_discovery=True)
    except KeyboardInterrupt:
        logger.info("Shutting down Tech News Agent...")


if __name__ == "__main__":
    main()