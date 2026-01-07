"""
Database operations for storing and retrieving articles and sources.

This module provides SQLite-based persistence for the Tech News Scraper,
replacing the previous JSON file storage for better query performance
and scalability.
"""

import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set

from config.settings import (
    DATA_DIR,
    DISCOVERED_SOURCES_FILE,
    OUTPUT_FILE,
)

logger = logging.getLogger(__name__)

# SQLite database file
DB_FILE = DATA_DIR / "tech_news.db"


class Database:
    """
    Handles all database operations for the scraper using SQLite.
    
    Provides CRUD operations for articles and discovered sources with
    automatic schema creation and JSON data migration support.
    
    Attributes:
        db_path: Path to the SQLite database file.
        articles: In-memory cache of articles for backward compatibility.
        url_cache: Set of article URLs for deduplication.
        discovered_sources: In-memory cache of discovered sources.
    """
    
    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialize the database connection and create schema if needed.
        
        Args:
            db_path: Optional custom path to the SQLite database.
                    Defaults to DATA_DIR/tech_news.db.
        """
        self.db_path: Path = db_path or DB_FILE
        self.articles: List[Dict[str, Any]] = []
        self.url_cache: Set[str] = set()
        self.discovered_sources: List[Dict[str, Any]] = []
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._create_schema()
        self._migrate_from_json()
        self._load_all_data()
    
    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection with row factory set.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _create_schema(self) -> None:
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Articles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    published TEXT,
                    scraped_at TEXT NOT NULL,
                    ai_summary TEXT,
                    full_content TEXT
                )
            """)
            
            # Create index on url for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)
            """)
            
            # Create index on scraped_at for sorting
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_scraped_at 
                ON articles(scraped_at DESC)
            """)
            
            # Discovered sources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    original_url TEXT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    verified INTEGER DEFAULT 0,
                    discovered_at TEXT,
                    quality_score REAL DEFAULT 0,
                    article_count INTEGER DEFAULT 0
                )
            """)
            
            # Create index on url for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url)
            """)
            
            conn.commit()
            logger.info("Database schema initialized")
    
    def _migrate_from_json(self) -> None:
        """
        Migrate existing JSON data to SQLite if available.
        
        Checks for existing JSON files and imports their data into SQLite
        tables. Only runs if SQLite database is empty.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if articles table is empty
            cursor.execute("SELECT COUNT(*) FROM articles")
            article_count = cursor.fetchone()[0]
            
            if article_count == 0 and OUTPUT_FILE.exists():
                try:
                    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                        json_articles = json.load(f)
                    
                    for article in json_articles:
                        cursor.execute("""
                            INSERT OR IGNORE INTO articles 
                            (id, title, url, source, published, scraped_at, 
                             ai_summary, full_content)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            article.get("id", hashlib.md5(
                                article["url"].encode()).hexdigest()),
                            article["title"],
                            article["url"],
                            article["source"],
                            article.get("published"),
                            article.get("scraped_at", 
                                       datetime.now(UTC).isoformat()),
                            article.get("ai_summary"),
                            article.get("full_content")
                        ))
                    
                    conn.commit()
                    logger.info(f"Migrated {len(json_articles)} articles from JSON")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not migrate articles JSON: {e}")
            
            # Check if sources table is empty
            cursor.execute("SELECT COUNT(*) FROM sources")
            source_count = cursor.fetchone()[0]
            
            if source_count == 0 and DISCOVERED_SOURCES_FILE.exists():
                try:
                    with open(DISCOVERED_SOURCES_FILE, "r", encoding="utf-8") as f:
                        json_sources = json.load(f)
                    
                    for source in json_sources:
                        cursor.execute("""
                            INSERT OR IGNORE INTO sources 
                            (url, original_url, type, name, verified, 
                             discovered_at, quality_score, article_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            source["url"],
                            source.get("original_url"),
                            source["type"],
                            source["name"],
                            1 if source.get("verified") else 0,
                            source.get("discovered_at"),
                            source.get("quality_score", 0),
                            source.get("article_count", 0)
                        ))
                    
                    conn.commit()
                    logger.info(f"Migrated {len(json_sources)} sources from JSON")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not migrate sources JSON: {e}")
    
    def _load_all_data(self) -> None:
        """Load all data from SQLite into memory caches."""
        self.articles = self.get_all_articles()
        self.url_cache = {article["url"] for article in self.articles}
        self.discovered_sources = self.get_all_sources()
        logger.info(
            f"Loaded {len(self.articles)} articles, "
            f"{len(self.discovered_sources)} sources"
        )
    
    def get_all_articles(self) -> List[Dict[str, Any]]:
        """
        Retrieve all articles from the database.
        
        Returns:
            List of article dictionaries sorted by scraped_at descending.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, url, source, published, scraped_at, 
                       ai_summary, full_content
                FROM articles
                ORDER BY scraped_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_sources(self) -> List[Dict[str, Any]]:
        """
        Retrieve all discovered sources from the database.
        
        Returns:
            List of source dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, original_url, type, name, verified, 
                       discovered_at, quality_score, article_count
                FROM sources
            """)
            sources = []
            for row in cursor.fetchall():
                source = dict(row)
                source["verified"] = bool(source["verified"])
                sources.append(source)
            return sources
    
    def add_article(self, article: Dict[str, Any]) -> bool:
        """
        Add a new article to the database.
        
        Args:
            article: Dictionary containing article data with required fields:
                    title, url, source. Optional: id, published, scraped_at,
                    ai_summary, full_content.
        
        Returns:
            True if article was added, False if it already exists.
        """
        if article["url"] in self.url_cache:
            return False
        
        # Generate ID if not present
        article_id = article.get(
            "id", 
            hashlib.md5(article["url"].encode()).hexdigest()
        )
        
        # Set scraped_at if not present
        scraped_at = article.get("scraped_at", datetime.now(UTC).isoformat())
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO articles 
                    (id, title, url, source, published, scraped_at, 
                     ai_summary, full_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id,
                    article["title"],
                    article["url"],
                    article["source"],
                    article.get("published"),
                    scraped_at,
                    article.get("ai_summary"),
                    article.get("full_content")
                ))
                conn.commit()
            
            # Update in-memory cache
            article["id"] = article_id
            article["scraped_at"] = scraped_at
            self.articles.insert(0, article)
            self.url_cache.add(article["url"])
            
            return True
        except sqlite3.IntegrityError:
            return False
    
    def add_discovered_source(self, source: Dict[str, Any]) -> bool:
        """
        Add a new discovered source to the database.
        
        Args:
            source: Dictionary containing source data with required fields:
                   url, type, name. Optional: original_url, verified,
                   discovered_at, quality_score, article_count.
        
        Returns:
            True if source was added, False if it already exists.
        """
        existing_urls = {src["url"] for src in self.discovered_sources}
        if source["url"] in existing_urls:
            return False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sources 
                    (url, original_url, type, name, verified, 
                     discovered_at, quality_score, article_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source["url"],
                    source.get("original_url"),
                    source["type"],
                    source["name"],
                    1 if source.get("verified") else 0,
                    source.get("discovered_at", datetime.now(UTC).isoformat()),
                    source.get("quality_score", 0),
                    source.get("article_count", 0)
                ))
                conn.commit()
            
            # Update in-memory cache
            self.discovered_sources.append(source)
            
            return True
        except sqlite3.IntegrityError:
            return False
    
    def update_source_article_count(
        self, 
        source_url: str, 
        increment: int = 1
    ) -> None:
        """
        Update the article count for a source.
        
        Args:
            source_url: URL of the source to update.
            increment: Number to add to the article count.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sources 
                SET article_count = article_count + ?
                WHERE url = ?
            """, (increment, source_url))
            conn.commit()
        
        # Update in-memory cache
        for source in self.discovered_sources:
            if source["url"] == source_url:
                source["article_count"] = source.get("article_count", 0) + increment
                break
    
    def search_articles(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search articles by title or content (basic text search).
        
        Args:
            query: Search query string.
            limit: Maximum number of results to return.
        
        Returns:
            List of matching article dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, url, source, published, scraped_at, 
                       ai_summary, full_content
                FROM articles
                WHERE title LIKE ? OR full_content LIKE ?
                ORDER BY scraped_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_article_count(self) -> int:
        """
        Get the total number of articles in the database.
        
        Returns:
            Total article count.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            return cursor.fetchone()[0]
    
    def get_source_count(self) -> int:
        """
        Get the total number of discovered sources.
        
        Returns:
            Total source count.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sources")
            return cursor.fetchone()[0]
    
    # Backward compatibility methods
    def save_articles(self) -> None:
        """
        Save articles to the database.
        
        Note: With SQLite, articles are saved immediately on add_article().
        This method exists for backward compatibility.
        """
        logger.debug("save_articles() called - SQLite saves are automatic")
    
    def load_articles(self) -> None:
        """
        Load articles from the database.
        
        Note: With SQLite, articles are loaded on initialization.
        This method exists for backward compatibility.
        """
        self.articles = self.get_all_articles()
        self.url_cache = {article["url"] for article in self.articles}
    
    def save_discovered_sources(self) -> None:
        """
        Save discovered sources to the database.
        
        Note: With SQLite, sources are saved immediately on add_discovered_source().
        This method exists for backward compatibility.
        """
        logger.debug("save_discovered_sources() called - SQLite saves are automatic")
    
    def load_discovered_sources(self) -> None:
        """
        Load discovered sources from the database.
        
        Note: With SQLite, sources are loaded on initialization.
        This method exists for backward compatibility.
        """
        self.discovered_sources = self.get_all_sources()