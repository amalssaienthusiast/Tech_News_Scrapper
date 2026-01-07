"""
Unit tests for the Database module.

Tests SQLite operations, data migration, and CRUD functionality.
"""

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import sys
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import Database


class TestDatabase(unittest.TestCase):
    """Test cases for Database class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_news.db"
        
        # Patch settings to use temp directory
        with patch('src.database.DB_FILE', self.db_path):
            with patch('src.database.OUTPUT_FILE', Path(self.temp_dir) / "articles.json"):
                with patch('src.database.DISCOVERED_SOURCES_FILE', Path(self.temp_dir) / "sources.json"):
                    self.db = Database(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test database initializes correctly."""
        self.assertIsInstance(self.db.articles, list)
        self.assertIsInstance(self.db.url_cache, set)
        self.assertIsInstance(self.db.discovered_sources, list)
        self.assertTrue(self.db_path.exists())
    
    def test_schema_creation(self):
        """Test database schema is created correctly."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check articles table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='articles'"
        )
        self.assertIsNotNone(cursor.fetchone())
        
        # Check sources table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sources'"
        )
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()
    
    def test_add_article(self):
        """Test adding an article."""
        article = {
            "title": "Test Article",
            "url": "https://example.com/test-article",
            "source": "Test Source",
            "published": datetime.now(UTC).isoformat(),
            "ai_summary": "This is a test summary.",
            "full_content": "Full article content here."
        }
        
        result = self.db.add_article(article)
        self.assertTrue(result)
        self.assertEqual(len(self.db.articles), 1)
        self.assertIn(article["url"], self.db.url_cache)
    
    def test_add_duplicate_article(self):
        """Test that duplicate articles are rejected."""
        article = {
            "title": "Test Article",
            "url": "https://example.com/test-article",
            "source": "Test Source",
        }
        
        self.db.add_article(article)
        result = self.db.add_article(article)
        
        self.assertFalse(result)
        self.assertEqual(len(self.db.articles), 1)
    
    def test_add_discovered_source(self):
        """Test adding a discovered source."""
        source = {
            "url": "https://example.com/feed",
            "type": "rss",
            "name": "Example RSS",
            "verified": True
        }
        
        result = self.db.add_discovered_source(source)
        self.assertTrue(result)
        self.assertEqual(len(self.db.discovered_sources), 1)
    
    def test_add_duplicate_source(self):
        """Test that duplicate sources are rejected."""
        source = {
            "url": "https://example.com/feed",
            "type": "rss",
            "name": "Example RSS",
        }
        
        self.db.add_discovered_source(source)
        result = self.db.add_discovered_source(source)
        
        self.assertFalse(result)
        self.assertEqual(len(self.db.discovered_sources), 1)
    
    def test_get_all_articles(self):
        """Test retrieving all articles."""
        # Add some articles
        for i in range(3):
            self.db.add_article({
                "title": f"Article {i}",
                "url": f"https://example.com/article-{i}",
                "source": "Test",
            })
        
        articles = self.db.get_all_articles()
        self.assertEqual(len(articles), 3)
    
    def test_get_article_count(self):
        """Test article count method."""
        for i in range(5):
            self.db.add_article({
                "title": f"Article {i}",
                "url": f"https://example.com/article-{i}",
                "source": "Test",
            })
        
        count = self.db.get_article_count()
        self.assertEqual(count, 5)
    
    def test_search_articles(self):
        """Test basic text search."""
        self.db.add_article({
            "title": "Python Programming Guide",
            "url": "https://example.com/python",
            "source": "Test",
            "full_content": "Learn Python programming basics."
        })
        self.db.add_article({
            "title": "JavaScript Tutorial",
            "url": "https://example.com/javascript",
            "source": "Test",
            "full_content": "Learn JavaScript for web development."
        })
        
        results = self.db.search_articles("Python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Python Programming Guide")
    
    def test_update_source_article_count(self):
        """Test updating source article count."""
        source = {
            "url": "https://example.com/feed",
            "type": "rss",
            "name": "Example RSS",
            "article_count": 0
        }
        self.db.add_discovered_source(source)
        
        self.db.update_source_article_count("https://example.com/feed", 5)
        
        # Check in-memory cache
        updated = next(
            s for s in self.db.discovered_sources 
            if s["url"] == "https://example.com/feed"
        )
        self.assertEqual(updated["article_count"], 5)


class TestDatabaseMigration(unittest.TestCase):
    """Test cases for JSON to SQLite migration."""
    
    def setUp(self):
        """Set up test fixtures with JSON files."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_news.db"
        self.json_articles = Path(self.temp_dir) / "articles.json"
        self.json_sources = Path(self.temp_dir) / "sources.json"
        
        # Create JSON files with test data
        articles = [
            {
                "id": "abc123",
                "title": "Legacy Article",
                "url": "https://legacy.com/article",
                "source": "Legacy Source",
                "published": "2024-01-01T00:00:00Z",
                "scraped_at": "2024-01-01T00:00:00Z",
                "ai_summary": "Legacy summary",
                "full_content": "Legacy content"
            }
        ]
        with open(self.json_articles, "w") as f:
            json.dump(articles, f)
        
        sources = [
            {
                "url": "https://legacy.com/feed",
                "type": "rss",
                "name": "Legacy Feed",
                "verified": True
            }
        ]
        with open(self.json_sources, "w") as f:
            json.dump(sources, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_migration_from_json(self):
        """Test that existing JSON data is migrated to SQLite."""
        with patch('src.database.DB_FILE', self.db_path):
            with patch('src.database.OUTPUT_FILE', self.json_articles):
                with patch('src.database.DISCOVERED_SOURCES_FILE', self.json_sources):
                    db = Database(db_path=self.db_path)
        
        # Check articles migrated
        self.assertEqual(len(db.articles), 1)
        self.assertEqual(db.articles[0]["title"], "Legacy Article")
        
        # Check sources migrated
        self.assertEqual(len(db.discovered_sources), 1)
        self.assertEqual(db.discovered_sources[0]["name"], "Legacy Feed")


if __name__ == '__main__':
    unittest.main()
