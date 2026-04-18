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
import threading
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

# Concurrency and performance settings
DB_WAL_MODE = True  # Enable Write-Ahead Logging for better concurrency
DB_TIMEOUT = 30  # Connection timeout in seconds
DB_POOL_SIZE = 5  # Connection pool size
DB_CACHE_LIMIT = 10000  # Maximum articles to keep in memory
DB_CHECKPOINT_INTERVAL = 1000  # Auto-checkpoint after N writes

# Singleton instance cache
_database_instance: Optional["Database"] = None
_database_lock = threading.Lock()

# Write operation counter for checkpointing
_write_count = 0
_write_lock = threading.Lock()


def get_database() -> "Database":
    """
    Get or create singleton Database instance.
    
    This prevents repeated database schema initialization and reduces
    resource usage by reusing a single Database connection pool.
    
    Returns:
        Singleton Database instance.
    """
    global _database_instance
    if _database_instance is None:
        with _database_lock:
            # Double-check pattern to avoid race condition
            if _database_instance is None:
                _database_instance = Database()
    return _database_instance


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
    def _get_connection(self, timeout: Optional[int] = None) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections with WAL mode support.
        
        Args:
            timeout: Connection timeout in seconds (defaults to DB_TIMEOUT)
            
        Yields:
            sqlite3.Connection: Database connection with row factory set and WAL mode enabled.
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=timeout or DB_TIMEOUT,
            check_same_thread=False  # Allow use across threads with proper locking
        )
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency if configured
        if DB_WAL_MODE:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and performance
            conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            conn.execute("PRAGMA temp_store=MEMORY")
        
        try:
            yield conn
        finally:
            conn.close()
    
    def _maybe_checkpoint(self, conn: sqlite3.Connection) -> None:
        """
        Perform auto-checkpoint if write threshold reached.
        
        This prevents the WAL file from growing too large.
        
        Args:
            conn: Active database connection
        """
        global _write_count
        with _write_lock:
            _write_count += 1
            if _write_count >= DB_CHECKPOINT_INTERVAL:
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    _write_count = 0
                    logger.debug("Database checkpoint completed")
                except sqlite3.Error as e:
                    logger.warning(f"Checkpoint failed: {e}")
    
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
            
            # Intelligence analysis table (v3.0)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_intelligence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    
                    -- Intelligence fields
                    disruptive INTEGER DEFAULT 0,
                    criticality INTEGER DEFAULT 1 CHECK (criticality BETWEEN 1 AND 10),
                    justification TEXT,
                    affected_markets TEXT,
                    affected_companies TEXT,
                    sentiment TEXT DEFAULT 'neutral',
                    relevance_score REAL DEFAULT 0.0,
                    categories TEXT,
                    key_insights TEXT,
                    
                    -- Alert tracking
                    alert_sent INTEGER DEFAULT 0,
                    alert_channel TEXT,
                    
                    -- Foreign key relationship
                    FOREIGN KEY (article_id) REFERENCES articles(id),
                    UNIQUE(article_id)
                )
            """)
            
            # Indexes for intelligence queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_intelligence_article 
                ON article_intelligence(article_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_intelligence_criticality 
                ON article_intelligence(criticality DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_intelligence_disruptive 
                ON article_intelligence(disruptive)
            """)
            
            # Newsletters table (v4.0)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS newsletters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    edition_date TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    subject_line TEXT,
                    markdown_content TEXT,
                    story_count INTEGER DEFAULT 0,
                    top_story_ids TEXT,
                    generated_at TEXT NOT NULL,
                    export_path TEXT,
                    status TEXT DEFAULT 'draft'
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_newsletters_date 
                ON newsletters(edition_date DESC)
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
                
                # Trigger checkpoint if needed
                self._maybe_checkpoint(conn)
            
            # Update in-memory cache with size limit
            article["id"] = article_id
            article["scraped_at"] = scraped_at
            self.articles.insert(0, article)
            self.url_cache.add(article["url"])
            
            # Enforce cache size limit to prevent unbounded growth
            if len(self.articles) > DB_CACHE_LIMIT:
                removed = self.articles[DB_CACHE_LIMIT:]
                self.articles = self.articles[:DB_CACHE_LIMIT]
                for old_article in removed:
                    self.url_cache.discard(old_article["url"])
                logger.debug(f"Trimmed {len(removed)} articles from cache")
            
            return True
        except sqlite3.IntegrityError:
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"Database error adding article: {e}")
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
    
    # =========================================================================
    # Intelligence Methods (v3.0)
    # =========================================================================
    
    def add_intelligence(
        self,
        article_id: str,
        provider: str,
        disruptive: bool,
        criticality: int,
        justification: str,
        affected_markets: Optional[List[str]] = None,
        affected_companies: Optional[List[str]] = None,
        sentiment: str = "neutral",
        relevance_score: float = 0.0,
        categories: Optional[List[str]] = None,
        key_insights: Optional[List[str]] = None
    ) -> bool:
        """
        Add intelligence analysis for an article.
        
        Args:
            article_id: ID of the article being analyzed
            provider: LLM provider used (gemini, langchain, local)
            disruptive: Whether article is market-disruptive
            criticality: Criticality score (1-10)
            justification: Explanation for the analysis
            affected_markets: List of affected markets
            affected_companies: List of affected companies
            sentiment: Article sentiment
            relevance_score: Relevance score (0.0-1.0)
            categories: News categories
            key_insights: Key insights list
            
        Returns:
            True if added/updated, False on error
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO article_intelligence 
                    (article_id, analyzed_at, provider, disruptive, criticality,
                     justification, affected_markets, affected_companies, sentiment,
                     relevance_score, categories, key_insights)
                    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id,
                    provider,
                    1 if disruptive else 0,
                    max(1, min(10, criticality)),
                    justification,
                    json.dumps(affected_markets or []),
                    json.dumps(affected_companies or []),
                    sentiment,
                    relevance_score,
                    json.dumps(categories or []),
                    json.dumps(key_insights or [])
                ))
                conn.commit()
                
            logger.info(f"Added intelligence for article {article_id}: criticality={criticality}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add intelligence: {e}")
            return False
    
    def get_intelligence(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Get intelligence analysis for an article.
        
        Args:
            article_id: Article ID to retrieve intelligence for
            
        Returns:
            Intelligence dict if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT article_id, analyzed_at, provider, disruptive, criticality,
                       justification, affected_markets, affected_companies, sentiment,
                       relevance_score, categories, key_insights, alert_sent, alert_channel
                FROM article_intelligence
                WHERE article_id = ?
            """, (article_id,))
            row = cursor.fetchone()
            
            if row:
                return self._parse_intelligence_row(dict(row))
            return None
    
    def get_high_criticality_articles(
        self,
        min_criticality: int = 7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get articles with high criticality scores.
        
        Args:
            min_criticality: Minimum criticality threshold
            limit: Maximum results
            
        Returns:
            List of article dicts with intelligence data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, i.disruptive, i.criticality, i.justification,
                       i.affected_markets, i.affected_companies, i.sentiment,
                       i.categories, i.key_insights, i.analyzed_at
                FROM articles a
                JOIN article_intelligence i ON a.id = i.article_id
                WHERE i.criticality >= ?
                ORDER BY i.criticality DESC, a.scraped_at DESC
                LIMIT ?
            """, (min_criticality, limit))
            
            results = []
            for row in cursor.fetchall():
                article = dict(row)
                article = self._parse_intelligence_row(article)
                results.append(article)
            
            return results
    
    def get_disruptive_articles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all disruptive articles.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of disruptive article dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, i.disruptive, i.criticality, i.justification,
                       i.affected_markets, i.affected_companies, i.sentiment,
                       i.categories, i.analyzed_at
                FROM articles a
                JOIN article_intelligence i ON a.id = i.article_id
                WHERE i.disruptive = 1
                ORDER BY i.criticality DESC
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                article = dict(row)
                article = self._parse_intelligence_row(article)
                results.append(article)
            
            return results
    
    def update_alert_status(
        self,
        article_id: str,
        alert_sent: bool,
        alert_channel: str = ""
    ) -> bool:
        """
        Update alert status for an article.
        
        Args:
            article_id: Article ID
            alert_sent: Whether alert was sent
            alert_channel: Channel alert was sent to
            
        Returns:
            True if updated, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE article_intelligence 
                    SET alert_sent = ?, alert_channel = ?
                    WHERE article_id = ?
                """, (1 if alert_sent else 0, alert_channel, article_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update alert status: {e}")
            return False
    
    def get_pending_alerts(self, min_criticality: int = 7) -> List[Dict[str, Any]]:
        """
        Get high-criticality articles that haven't been alerted yet.
        
        Args:
            min_criticality: Minimum criticality for alerts
            
        Returns:
            List of article dicts pending alert
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, i.disruptive, i.criticality, i.justification,
                       i.affected_markets, i.affected_companies
                FROM articles a
                JOIN article_intelligence i ON a.id = i.article_id
                WHERE i.criticality >= ? AND i.alert_sent = 0
                ORDER BY i.criticality DESC
            """, (min_criticality,))
            
            results = []
            for row in cursor.fetchall():
                article = dict(row)
                article = self._parse_intelligence_row(article)
                results.append(article)
            
            return results
    
    def get_intelligence_stats(self) -> Dict[str, Any]:
        """
        Get intelligence analysis statistics.
        
        Returns:
            Dict with counts and averages
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM article_intelligence")
            total_analyzed = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM article_intelligence WHERE disruptive = 1")
            disruptive_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(criticality) FROM article_intelligence")
            avg_criticality = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM article_intelligence WHERE criticality >= 7")
            high_criticality_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM article_intelligence WHERE alert_sent = 1")
            alerts_sent = cursor.fetchone()[0]
            
            return {
                "total_analyzed": total_analyzed,
                "disruptive_count": disruptive_count,
                "avg_criticality": round(avg_criticality, 2),
                "high_criticality_count": high_criticality_count,
                "alerts_sent": alerts_sent,
                "disruptive_rate": round(disruptive_count / max(1, total_analyzed) * 100, 1)
            }
    
    def _parse_intelligence_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON fields in intelligence row."""
        json_fields = ["affected_markets", "affected_companies", "categories", "key_insights"]
        
        for field in json_fields:
            if field in row and row[field]:
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    row[field] = []
        
        if "disruptive" in row:
            row["disruptive"] = bool(row["disruptive"])
        
        return row
    
    # =========================================================================
    # Newsletter CRUD Methods (v4.0)
    # =========================================================================
    
    def save_newsletter(
        self,
        edition_date: str,
        name: str,
        markdown_content: str,
        subject_line: str = "",
        story_count: int = 0,
        top_story_ids: Optional[List[str]] = None,
        export_path: str = "",
        status: str = "draft"
    ) -> bool:
        """
        Save a generated newsletter.
        
        Args:
            edition_date: Newsletter date (YYYY-MM-DD)
            name: Newsletter name
            markdown_content: Full markdown content
            subject_line: Email subject
            story_count: Number of stories
            top_story_ids: IDs of featured stories
            export_path: Path to exported file
            status: draft, published, archived
            
        Returns:
            True if saved successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO newsletters 
                    (edition_date, name, subject_line, markdown_content, 
                     story_count, top_story_ids, generated_at, export_path, status)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
                """, (
                    edition_date,
                    name,
                    subject_line,
                    markdown_content,
                    story_count,
                    json.dumps(top_story_ids or []),
                    export_path,
                    status
                ))
                conn.commit()
                logger.info(f"Newsletter saved: {edition_date}")
                return True
            except Exception as e:
                logger.error(f"Failed to save newsletter: {e}")
                return False
    
    def get_newsletter(self, edition_date: str) -> Optional[Dict[str, Any]]:
        """Get newsletter by date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM newsletters WHERE edition_date = ?",
                (edition_date,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result.get("top_story_ids"):
                    try:
                        result["top_story_ids"] = json.loads(result["top_story_ids"])
                    except json.JSONDecodeError:
                        result["top_story_ids"] = []
                return result
            return None
    
    def get_recent_newsletters(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent newsletters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM newsletters ORDER BY edition_date DESC LIMIT ?",
                (limit,)
            )
            newsletters = [dict(row) for row in cursor.fetchall()]
            for nl in newsletters:
                if nl.get("top_story_ids"):
                    try:
                        nl["top_story_ids"] = json.loads(nl["top_story_ids"])
                    except json.JSONDecodeError:
                        nl["top_story_ids"] = []
            return newsletters
    
    def get_newsletter_count(self) -> int:
        """Get total newsletter count."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM newsletters")
            return cursor.fetchone()[0]
