"""
Unit tests for the WebDiscoveryAgent module.

Tests source discovery, verification, and API integration.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import Database
from src.discovery import WebDiscoveryAgent


class TestWebDiscoveryAgent(unittest.TestCase):
    """Test cases for WebDiscoveryAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=Database)
        self.mock_db.discovered_sources = []
        self.mock_db.add_discovered_source = MagicMock(return_value=True)
        
        with patch('src.discovery.GOOGLE_API_KEY', ''):
            with patch('src.discovery.GOOGLE_CSE_ID', ''):
                with patch('src.discovery.BING_API_KEY', ''):
                    self.agent = WebDiscoveryAgent(self.mock_db)
        
        self.agent.session = MagicMock()
    
    def test_initialization(self):
        """Test agent initializes correctly."""
        self.assertIsNotNone(self.agent.session)
        self.assertIsInstance(self.agent.api_available, dict)
    
    def test_is_tech_related_true(self):
        """Test tech-related content detection."""
        tech_text = """
        This article discusses artificial intelligence and machine learning
        in the context of software development and cloud computing.
        """
        
        result = self.agent.is_tech_related(tech_text)
        self.assertTrue(result)
    
    def test_is_tech_related_false(self):
        """Test non-tech content detection."""
        non_tech_text = """
        Today we went to the park and had a lovely picnic.
        The weather was beautiful and the kids played soccer.
        """
        
        result = self.agent.is_tech_related(non_tech_text)
        self.assertFalse(result)
    
    def test_verify_source_valid(self):
        """Test source verification with valid tech source."""
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <head>
            <title>Tech News Daily</title>
            <link type="application/rss+xml" href="/feed.xml">
        </head>
        <body>
            <article>
            Latest news about artificial intelligence, machine learning,
            software development, and cloud computing technologies.
            </article>
        </body>
        </html>
        '''
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        self.agent.session.get.return_value = mock_response
        self.agent.rate_limiter.wait = MagicMock(return_value=True)
        
        result = self.agent.verify_source("https://technews.com")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'rss')
        self.assertTrue(result['verified'])
    
    def test_verify_source_invalid_non_tech(self):
        """Test source verification with non-tech content."""
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
        <head><title>Cooking Blog</title></head>
        <body>
            <article>
            Today we're making delicious pasta with homemade sauce.
            This recipe is perfect for family dinners.
            </article>
        </body>
        </html>
        '''
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        self.agent.session.get.return_value = mock_response
        self.agent.rate_limiter.wait = MagicMock(return_value=True)
        
        result = self.agent.verify_source("https://cooking.com")
        
        self.assertIsNone(result)
    
    def test_fallback_sources(self):
        """Test fallback sources are returned when search fails."""
        # Mock search to return empty
        with patch.object(
            self.agent,
            '_scrape_search_engines',
            return_value=[]
        ):
            result = self.agent.search_web_for_sources("test query")
        
        # Should return fallback sources
        self.assertGreater(len(result), 0)
        self.assertTrue(
            any('techcrunch' in url for url in result) or
            any('verge' in url for url in result)
        )
    
    def test_discover_new_sources(self):
        """Test source discovery process."""
        # Mock search and verify
        with patch.object(
            self.agent,
            'search_web_for_sources',
            return_value=["https://example-tech.com"]
        ):
            with patch.object(
                self.agent,
                'verify_source',
                return_value={
                    'url': 'https://example-tech.com/feed',
                    'type': 'rss',
                    'name': 'Example Tech',
                    'verified': True
                }
            ):
                result = self.agent.discover_new_sources(max_new_sources=1)
        
        self.assertEqual(len(result), 1)
        self.mock_db.add_discovered_source.assert_called()


class TestWebDiscoveryAgentAPI(unittest.TestCase):
    """Test cases for API-based discovery."""
    
    def test_google_api_configured(self):
        """Test Google API availability check."""
        mock_db = MagicMock(spec=Database)
        mock_db.discovered_sources = []
        
        with patch('src.discovery.GOOGLE_API_KEY', 'test-key'):
            with patch('src.discovery.GOOGLE_CSE_ID', 'test-cse'):
                with patch('src.discovery.BING_API_KEY', ''):
                    agent = WebDiscoveryAgent(mock_db)
        
        self.assertTrue(agent.api_available['google'])
        self.assertFalse(agent.api_available['bing'])
    
    def test_bing_api_configured(self):
        """Test Bing API availability check."""
        mock_db = MagicMock(spec=Database)
        mock_db.discovered_sources = []
        
        with patch('src.discovery.GOOGLE_API_KEY', ''):
            with patch('src.discovery.GOOGLE_CSE_ID', ''):
                with patch('src.discovery.BING_API_KEY', 'test-key'):
                    agent = WebDiscoveryAgent(mock_db)
        
        self.assertFalse(agent.api_available['google'])
        self.assertTrue(agent.api_available['bing'])


if __name__ == '__main__':
    unittest.main()
