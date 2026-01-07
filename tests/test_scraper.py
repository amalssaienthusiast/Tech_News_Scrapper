"""
Unit tests for the TechNewsScraper module.

Tests scraping functionality with mocked HTTP responses.
"""

import asyncio
import hashlib
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import Database
from src.scraper import TechNewsScraper


class TestTechNewsScraper(unittest.TestCase):
    """Test cases for TechNewsScraper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock database
        self.mock_db = MagicMock(spec=Database)
        self.mock_db.articles = []
        self.mock_db.url_cache = set()
        self.mock_db.discovered_sources = []
        self.mock_db.add_article = MagicMock(return_value=True)
        
        # Create scraper with mock
        with patch('src.scraper.RateLimiter'):
            self.scraper = TechNewsScraper(self.mock_db)
        
        # Mock session
        self.scraper.session = MagicMock()
    
    def test_initialization(self):
        """Test scraper initializes with sources."""
        self.assertIsInstance(self.scraper.sources, list)
        self.assertGreater(len(self.scraper.sources), 0)
    
    def test_get_source_stats(self):
        """Test source statistics method."""
        stats = self.scraper.get_source_stats()
        
        self.assertIn('total_sources', stats)
        self.assertIn('rss_sources', stats)
        self.assertIn('web_sources', stats)
        self.assertIn('total_articles', stats)
    
    def test_scrape_web_source_mock(self):
        """Test web scraping with mocked response."""
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <body>
            <a href="/article/test-article-1">Test Article 1</a>
            <a href="/news/test-article-2">Test Article 2</a>
            <a href="/about">About Us</a>
        </body>
        </html>
        '''
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        self.scraper.session.get.return_value = mock_response
        
        # Mock rate limiter
        self.scraper.rate_limiter.wait = MagicMock(return_value=True)
        
        source = {
            "url": "https://example.com",
            "type": "web",
            "name": "Test Source"
        }
        
        # Mock article fetching
        with patch.object(
            self.scraper, 
            'get_full_article_and_summarize',
            return_value=("Full content", "AI Summary")
        ):
            articles = self.scraper.scrape_web_source(source)
        
        self.assertIsInstance(articles, int)
    
    def test_process_single_url_success(self):
        """Test processing a single URL successfully."""
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <head><title>Test Page Title</title></head>
        <body><article>Article content here</article></body>
        </html>
        '''
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        self.scraper.session.get.return_value = mock_response
        
        # Mock rate limiter
        self.scraper.rate_limiter.wait = MagicMock(return_value=True)
        
        with patch.object(
            self.scraper,
            'get_full_article_and_summarize',
            return_value=("Full content", "AI Summary")
        ):
            success, message, article = self.scraper.process_single_url(
                "https://example.com/article"
            )
        
        self.assertTrue(success)
        self.assertIsNotNone(article)
        self.mock_db.add_article.assert_called()
    
    def test_process_single_url_duplicate(self):
        """Test processing a URL already in database."""
        self.mock_db.add_article.return_value = False
        
        mock_response = MagicMock()
        mock_response.text = '<html><head><title>Test</title></head><body></body></html>'
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        self.scraper.session.get.return_value = mock_response
        
        self.scraper.rate_limiter.wait = MagicMock(return_value=True)
        
        with patch.object(
            self.scraper,
            'get_full_article_and_summarize',
            return_value=("Content", "Summary")
        ):
            success, message, article = self.scraper.process_single_url(
                "https://example.com/duplicate"
            )
        
        self.assertFalse(success)
        self.assertIn("already exists", message)
    
    def test_get_latest_articles(self):
        """Test getting latest articles."""
        # Add mock articles
        self.mock_db.articles = [
            {"title": f"Article {i}", "scraped_at": f"2024-01-0{i}T00:00:00Z"}
            for i in range(1, 6)
        ]
        
        articles = self.scraper.get_latest_articles(3)
        
        self.assertEqual(len(articles), 3)
        # Should be sorted by scraped_at descending
        self.assertEqual(articles[0]["title"], "Article 5")


class TestTechNewsScraperAsync(unittest.TestCase):
    """Test cases for async scraper operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=Database)
        self.mock_db.articles = []
        self.mock_db.url_cache = set()
        self.mock_db.discovered_sources = []
        self.mock_db.add_article = MagicMock(return_value=True)
        
        with patch('src.scraper.RateLimiter'):
            self.scraper = TechNewsScraper(self.mock_db)
    
    def test_fetch_url_async(self):
        """Test async URL fetching."""
        async def run_test():
            # Create mock session
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="<html>content</html>")
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_session.get.return_value = mock_context
            
            # Mock rate limiter
            self.scraper.rate_limiter.wait_async = AsyncMock(return_value=True)
            
            result = await self.scraper._fetch_url_async(
                mock_session, 
                "https://example.com"
            )
            
            return result
        
        result = asyncio.run(run_test())
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
