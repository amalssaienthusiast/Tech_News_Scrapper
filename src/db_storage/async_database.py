"""
Async Database Manager with PostgreSQL + SQLite dual-backend support.

This module provides an async-first database layer that supports both PostgreSQL
for production (high concurrency, horizontal scaling) and SQLite for local
development and testing.

Features:
- Connection pooling with asyncpg for PostgreSQL
- Automatic backend detection via DATABASE_URL
- Full schema compatibility with existing SQLite database
- Migration utilities for SQLite → PostgreSQL transition
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

try:
    import asyncpg

    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    asyncpg = None  # type: ignore

try:
    import aiosqlite

    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False
    aiosqlite = None  # type: ignore

from config.settings import DATA_DIR

logger = logging.getLogger(__name__)


class DatabaseBackend(Enum):
    """Supported database backends."""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


# Configuration defaults
DEFAULT_POOL_SIZE_MIN = 5
DEFAULT_POOL_SIZE_MAX = 20
DEFAULT_POOL_TIMEOUT = 30
DEFAULT_COMMAND_TIMEOUT = 60


# Singleton instance
_async_db_instance: Optional["AsyncDatabaseManager"] = None
_async_db_lock = asyncio.Lock()


async def get_async_database() -> "AsyncDatabaseManager":
    """
    Get or create singleton AsyncDatabaseManager instance.

    Uses DATABASE_URL environment variable if set (PostgreSQL),
    otherwise falls back to SQLite.

    Returns:
        Singleton AsyncDatabaseManager instance.
    """
    global _async_db_instance

    async with _async_db_lock:
        if _async_db_instance is None:
            database_url = os.environ.get("DATABASE_URL")
            _async_db_instance = AsyncDatabaseManager(database_url)
            await _async_db_instance.initialize()

    return _async_db_instance


class AsyncDatabaseManager:
    """
    Async database manager with PostgreSQL + SQLite dual-backend support.

    Provides high-performance async database operations with connection pooling
    for PostgreSQL and aiosqlite for local development.

    Attributes:
        backend: The active database backend (SQLITE or POSTGRESQL)
        database_url: Connection string for PostgreSQL
        db_path: Path to SQLite database file
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size_min: int = DEFAULT_POOL_SIZE_MIN,
        pool_size_max: int = DEFAULT_POOL_SIZE_MAX,
        pool_timeout: int = DEFAULT_POOL_TIMEOUT,
    ) -> None:
        """
        Initialize the async database manager.

        Args:
            database_url: PostgreSQL connection URL (postgresql://user:pass@host:port/db)
                         If None, uses SQLite.
            pool_size_min: Minimum connection pool size for PostgreSQL
            pool_size_max: Maximum connection pool size for PostgreSQL
            pool_timeout: Connection acquisition timeout in seconds
        """
        self.database_url = database_url
        self.pool_size_min = pool_size_min
        self.pool_size_max = pool_size_max
        self.pool_timeout = pool_timeout

        # Detect backend
        if database_url and database_url.startswith("postgresql"):
            if not HAS_ASYNCPG:
                raise ImportError(
                    "asyncpg is required for PostgreSQL support. "
                    "Install with: pip install asyncpg"
                )
            self.backend = DatabaseBackend.POSTGRESQL
            logger.info(f"Using PostgreSQL backend: {self._mask_url(database_url)}")
        else:
            self.backend = DatabaseBackend.SQLITE
            self.db_path = DATA_DIR / "tech_news.db"
            logger.info(f"Using SQLite backend: {self.db_path}")

        # Connection pools
        self._pg_pool: Optional["asyncpg.Pool"] = None
        self._initialized = False

        # In-memory caches for compatibility
        self.articles: List[Dict[str, Any]] = []
        self.url_cache: Set[str] = set()
        self.discovered_sources: List[Dict[str, Any]] = []

    def _mask_url(self, url: str) -> str:
        """Mask password in database URL for logging."""
        if "@" in url:
            # postgresql://user:password@host:port/db -> postgresql://user:***@host:port/db
            parts = url.split("@")
            auth_part = parts[0]
            if ":" in auth_part.split("//")[1]:
                user = auth_part.split(":")[-2].split("//")[-1]
                return f"postgresql://{user}:***@{parts[1]}"
        return url

    async def initialize(self) -> None:
        """
        Initialize database connection and create schema.

        Must be called before first use.
        """
        if self._initialized:
            return

        if self.backend == DatabaseBackend.POSTGRESQL:
            await self._init_postgresql()
        else:
            await self._init_sqlite()

        self._initialized = True
        logger.info(
            f"AsyncDatabaseManager initialized with {self.backend.value} backend"
        )

    async def _init_postgresql(self) -> None:
        """Initialize PostgreSQL connection pool and schema."""
        self._pg_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=self.pool_size_min,
            max_size=self.pool_size_max,
            timeout=self.pool_timeout,
            command_timeout=DEFAULT_COMMAND_TIMEOUT,
        )

        async with self._pg_pool.acquire() as conn:
            await self._create_postgresql_schema(conn)

        # Load initial data into cache
        await self._load_all_data()

    async def _init_sqlite(self) -> None:
        """Initialize SQLite database and schema."""
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await self._create_sqlite_schema(db)
            await self._migrate_sqlite_schema(db)
            await db.commit()

        # Load initial data into cache
        await self._load_all_data()

    async def _migrate_sqlite_schema(self, db: "aiosqlite.Connection") -> None:
        """
        Add any columns that are defined in the schema but missing from the live database.

        SQLite does not support ALTER TABLE ... ADD COLUMN IF NOT EXISTS, so we attempt
        each ALTER and silently ignore the error if the column already exists.
        """
        migrations = [
            "ALTER TABLE articles ADD COLUMN tech_score REAL DEFAULT 0.0",
            "ALTER TABLE articles ADD COLUMN tier TEXT DEFAULT 'standard'",
            "ALTER TABLE articles ADD COLUMN topics TEXT",
        ]
        for stmt in migrations:
            try:
                await db.execute(stmt)
                logger.info(f"Schema migration applied: {stmt}")
            except Exception:
                # Column already exists — this is expected on a current database.
                pass

    async def _create_postgresql_schema(self, conn: "asyncpg.Connection") -> None:
        """Create PostgreSQL schema with optimized indexes and types."""

        # Articles table with PostgreSQL-specific optimizations
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                published TIMESTAMP WITH TIME ZONE,
                scraped_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                ai_summary TEXT,
                full_content TEXT,
                
                -- Additional fields for future features
                tech_score REAL DEFAULT 0.0,
                tier TEXT DEFAULT 'standard',
                topics TEXT[]  -- PostgreSQL array type
            )
        """)

        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_scraped_at 
            ON articles(scraped_at DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)
        """)

        # Full-text search index using GIN
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_search 
            ON articles USING GIN (to_tsvector('english', title || ' ' || COALESCE(ai_summary, '')))
        """)

        # Sources table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                original_url TEXT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                verified BOOLEAN DEFAULT FALSE,
                discovered_at TIMESTAMP WITH TIME ZONE,
                quality_score REAL DEFAULT 0,
                article_count INTEGER DEFAULT 0
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url)
        """)

        # Intelligence analysis table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS article_intelligence (
                id SERIAL PRIMARY KEY,
                article_id TEXT NOT NULL REFERENCES articles(id),
                analyzed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                provider TEXT NOT NULL,
                
                -- Intelligence fields
                disruptive BOOLEAN DEFAULT FALSE,
                criticality INTEGER DEFAULT 1 CHECK (criticality BETWEEN 1 AND 10),
                justification TEXT,
                affected_markets JSONB DEFAULT '[]'::jsonb,
                affected_companies JSONB DEFAULT '[]'::jsonb,
                sentiment TEXT DEFAULT 'neutral',
                relevance_score REAL DEFAULT 0.0,
                categories JSONB DEFAULT '[]'::jsonb,
                key_insights JSONB DEFAULT '[]'::jsonb,
                
                -- Alert tracking
                alert_sent BOOLEAN DEFAULT FALSE,
                alert_channel TEXT,
                
                UNIQUE(article_id)
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_intelligence_article 
            ON article_intelligence(article_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_intelligence_criticality 
            ON article_intelligence(criticality DESC)
        """)

        # Newsletters table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS newsletters (
                id SERIAL PRIMARY KEY,
                edition_date DATE NOT NULL UNIQUE,
                name TEXT NOT NULL,
                subject_line TEXT,
                markdown_content TEXT,
                story_count INTEGER DEFAULT 0,
                top_story_ids JSONB DEFAULT '[]'::jsonb,
                generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                export_path TEXT,
                status TEXT DEFAULT 'draft'
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_newsletters_date 
            ON newsletters(edition_date DESC)
        """)

        logger.info("PostgreSQL schema initialized")

    async def _create_sqlite_schema(self, db: "aiosqlite.Connection") -> None:
        """Create SQLite schema (mirrors sync Database class)."""

        # Enable WAL mode
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA cache_size=-64000")
        await db.execute("PRAGMA temp_store=MEMORY")

        # Articles table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                published TEXT,
                scraped_at TEXT NOT NULL,
                ai_summary TEXT,
                full_content TEXT,
                tech_score REAL DEFAULT 0.0,
                tier TEXT DEFAULT 'standard',
                topics TEXT
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_scraped_at 
            ON articles(scraped_at DESC)
        """)

        # Sources table
        await db.execute("""
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

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url)
        """)

        # Intelligence table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS article_intelligence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT NOT NULL,
                analyzed_at TEXT NOT NULL,
                provider TEXT NOT NULL,
                disruptive INTEGER DEFAULT 0,
                criticality INTEGER DEFAULT 1 CHECK (criticality BETWEEN 1 AND 10),
                justification TEXT,
                affected_markets TEXT,
                affected_companies TEXT,
                sentiment TEXT DEFAULT 'neutral',
                relevance_score REAL DEFAULT 0.0,
                categories TEXT,
                key_insights TEXT,
                alert_sent INTEGER DEFAULT 0,
                alert_channel TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(id),
                UNIQUE(article_id)
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_intelligence_article 
            ON article_intelligence(article_id)
        """)

        # Newsletters table
        await db.execute("""
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

        await db.commit()
        logger.info("SQLite async schema initialized")

    async def _load_all_data(self) -> None:
        """Load data into memory caches for compatibility."""
        self.articles = await self.get_all_articles()
        self.url_cache = {article["url"] for article in self.articles}
        self.discovered_sources = await self.get_all_sources()
        logger.info(
            f"Loaded {len(self.articles)} articles, "
            f"{len(self.discovered_sources)} sources"
        )

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[Any, None]:
        """
        Acquire a database connection from the pool.

        Usage:
            async with db.acquire() as conn:
                result = await conn.fetch("SELECT ...")
        """
        if self.backend == DatabaseBackend.POSTGRESQL:
            async with self._pg_pool.acquire() as conn:
                yield conn
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                yield db

    # =========================================================================
    # Article CRUD Operations
    # =========================================================================

    async def get_all_articles(self) -> List[Dict[str, Any]]:
        """Retrieve all articles, ordered by scraped_at descending."""
        if self.backend == DatabaseBackend.POSTGRESQL:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, title, url, source, published, scraped_at,
                           ai_summary, full_content, tech_score, tier, topics
                    FROM articles
                    ORDER BY scraped_at DESC
                """)
                return [dict(row) for row in rows]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT id, title, url, source, published, scraped_at,
                           ai_summary, full_content, tech_score, tier, topics
                    FROM articles
                    ORDER BY scraped_at DESC
                """)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_sources(self) -> List[Dict[str, Any]]:
        """Retrieve all discovered sources."""
        if self.backend == DatabaseBackend.POSTGRESQL:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT url, original_url, type, name, verified,
                           discovered_at, quality_score, article_count
                    FROM sources
                """)
                return [dict(row) for row in rows]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT url, original_url, type, name, verified,
                           discovered_at, quality_score, article_count
                    FROM sources
                """)
                rows = await cursor.fetchall()
                sources = []
                for row in rows:
                    source = dict(row)
                    source["verified"] = bool(source["verified"])
                    sources.append(source)
                return sources

    async def add_article(self, article: Dict[str, Any]) -> bool:
        """
        Add a new article to the database.

        Args:
            article: Dictionary with title, url, source required.
                    Optional: id, published, scraped_at, ai_summary, full_content,
                    tech_score, tier, topics.

        Returns:
            True if added, False if already exists.
        """
        if article["url"] in self.url_cache:
            return False

        article_id = article.get("id", hashlib.md5(article["url"].encode()).hexdigest())
        scraped_at = article.get("scraped_at", datetime.now(UTC).isoformat())

        try:
            if self.backend == DatabaseBackend.POSTGRESQL:
                async with self._pg_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO articles 
                        (id, title, url, source, published, scraped_at,
                         ai_summary, full_content, tech_score, tier, topics)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (url) DO NOTHING
                    """,
                        article_id,
                        article["title"],
                        article["url"],
                        article["source"],
                        article.get("published"),
                        scraped_at,
                        article.get("ai_summary"),
                        article.get("full_content"),
                        article.get("tech_score", 0.0),
                        article.get("tier", "standard"),
                        article.get("topics", []),
                    )
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO articles 
                        (id, title, url, source, published, scraped_at,
                         ai_summary, full_content, tech_score, tier, topics)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            article_id,
                            article["title"],
                            article["url"],
                            article["source"],
                            article.get("published"),
                            scraped_at,
                            article.get("ai_summary"),
                            article.get("full_content"),
                            article.get("tech_score", 0.0),
                            article.get("tier", "standard"),
                            json.dumps(article.get("topics", [])),
                        ),
                    )
                    await db.commit()

            # Update cache
            article["id"] = article_id
            article["scraped_at"] = scraped_at
            self.articles.insert(0, article)
            self.url_cache.add(article["url"])

            return True

        except Exception as e:
            logger.error(f"Failed to add article: {e}")
            return False

    async def add_discovered_source(self, source: Dict[str, Any]) -> bool:
        """Add a new discovered source."""
        existing_urls = {src["url"] for src in self.discovered_sources}
        if source["url"] in existing_urls:
            return False

        try:
            if self.backend == DatabaseBackend.POSTGRESQL:
                async with self._pg_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO sources 
                        (url, original_url, type, name, verified,
                         discovered_at, quality_score, article_count)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (url) DO NOTHING
                    """,
                        source["url"],
                        source.get("original_url"),
                        source["type"],
                        source["name"],
                        source.get("verified", False),
                        source.get("discovered_at", datetime.now(UTC)),
                        source.get("quality_score", 0),
                        source.get("article_count", 0),
                    )
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO sources 
                        (url, original_url, type, name, verified,
                         discovered_at, quality_score, article_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            source["url"],
                            source.get("original_url"),
                            source["type"],
                            source["name"],
                            1 if source.get("verified") else 0,
                            source.get("discovered_at", datetime.now(UTC).isoformat()),
                            source.get("quality_score", 0),
                            source.get("article_count", 0),
                        ),
                    )
                    await db.commit()

            self.discovered_sources.append(source)
            return True

        except Exception as e:
            logger.error(f"Failed to add source: {e}")
            return False

    async def search_articles(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search articles using full-text search.

        PostgreSQL uses GIN index with tsvector for efficient search.
        SQLite falls back to LIKE matching.
        """
        if self.backend == DatabaseBackend.POSTGRESQL:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, title, url, source, published, scraped_at,
                           ai_summary, full_content,
                           ts_rank(
                               to_tsvector('english', title || ' ' || COALESCE(ai_summary, '')),
                               plainto_tsquery('english', $1)
                           ) AS rank
                    FROM articles
                    WHERE to_tsvector('english', title || ' ' || COALESCE(ai_summary, '')) 
                          @@ plainto_tsquery('english', $1)
                    ORDER BY rank DESC, scraped_at DESC
                    LIMIT $2
                """,
                    query,
                    limit,
                )
                return [dict(row) for row in rows]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    """
                    SELECT id, title, url, source, published, scraped_at,
                           ai_summary, full_content
                    FROM articles
                    WHERE title LIKE ? OR full_content LIKE ?
                    ORDER BY scraped_at DESC
                    LIMIT ?
                """,
                    (f"%{query}%", f"%{query}%", limit),
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_article_count(self) -> int:
        """Get total article count."""
        if self.backend == DatabaseBackend.POSTGRESQL:
            async with self._pg_pool.acquire() as conn:
                return await conn.fetchval("SELECT COUNT(*) FROM articles")
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM articles")
                row = await cursor.fetchone()
                return row[0]

    async def get_source_count(self) -> int:
        """Get total source count."""
        if self.backend == DatabaseBackend.POSTGRESQL:
            async with self._pg_pool.acquire() as conn:
                return await conn.fetchval("SELECT COUNT(*) FROM sources")
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM sources")
                row = await cursor.fetchone()
                return row[0]

    # =========================================================================
    # Intelligence Methods
    # =========================================================================

    async def add_intelligence(
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
        key_insights: Optional[List[str]] = None,
    ) -> bool:
        """Add intelligence analysis for an article."""
        try:
            if self.backend == DatabaseBackend.POSTGRESQL:
                async with self._pg_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO article_intelligence 
                        (article_id, provider, disruptive, criticality,
                         justification, affected_markets, affected_companies,
                         sentiment, relevance_score, categories, key_insights)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (article_id) DO UPDATE SET
                            provider = EXCLUDED.provider,
                            disruptive = EXCLUDED.disruptive,
                            criticality = EXCLUDED.criticality,
                            justification = EXCLUDED.justification,
                            affected_markets = EXCLUDED.affected_markets,
                            affected_companies = EXCLUDED.affected_companies,
                            sentiment = EXCLUDED.sentiment,
                            relevance_score = EXCLUDED.relevance_score,
                            categories = EXCLUDED.categories,
                            key_insights = EXCLUDED.key_insights,
                            analyzed_at = NOW()
                    """,
                        article_id,
                        provider,
                        disruptive,
                        max(1, min(10, criticality)),
                        justification,
                        json.dumps(affected_markets or []),
                        json.dumps(affected_companies or []),
                        sentiment,
                        relevance_score,
                        json.dumps(categories or []),
                        json.dumps(key_insights or []),
                    )
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO article_intelligence 
                        (article_id, analyzed_at, provider, disruptive, criticality,
                         justification, affected_markets, affected_companies,
                         sentiment, relevance_score, categories, key_insights)
                        VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
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
                            json.dumps(key_insights or []),
                        ),
                    )
                    await db.commit()

            logger.info(
                f"Added intelligence for {article_id}: criticality={criticality}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add intelligence: {e}")
            return False

    async def get_high_criticality_articles(
        self, min_criticality: int = 7, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get articles with high criticality scores."""
        if self.backend == DatabaseBackend.POSTGRESQL:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT a.*, i.disruptive, i.criticality, i.justification,
                           i.affected_markets, i.affected_companies, i.sentiment,
                           i.categories, i.key_insights, i.analyzed_at
                    FROM articles a
                    JOIN article_intelligence i ON a.id = i.article_id
                    WHERE i.criticality >= $1
                    ORDER BY i.criticality DESC, a.scraped_at DESC
                    LIMIT $2
                """,
                    min_criticality,
                    limit,
                )
                return [dict(row) for row in rows]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    """
                    SELECT a.*, i.disruptive, i.criticality, i.justification,
                           i.affected_markets, i.affected_companies, i.sentiment,
                           i.categories, i.key_insights, i.analyzed_at
                    FROM articles a
                    JOIN article_intelligence i ON a.id = i.article_id
                    WHERE i.criticality >= ?
                    ORDER BY i.criticality DESC, a.scraped_at DESC
                    LIMIT ?
                """,
                    (min_criticality, limit),
                )
                rows = await cursor.fetchall()
                return [self._parse_intelligence_row(dict(row)) for row in rows]

    def _parse_intelligence_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON fields in intelligence row (for SQLite)."""
        json_fields = [
            "affected_markets",
            "affected_companies",
            "categories",
            "key_insights",
        ]

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
    # Connection Management
    # =========================================================================

    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        if self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None

        self._initialized = False
        logger.info("AsyncDatabaseManager closed")

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL backend."""
        return self.backend == DatabaseBackend.POSTGRESQL

    @property
    def pool_stats(self) -> Optional[Dict[str, int]]:
        """Get connection pool statistics (PostgreSQL only)."""
        if self._pg_pool:
            return {
                "size": self._pg_pool.get_size(),
                "free": self._pg_pool.get_idle_size(),
                "min": self._pg_pool.get_min_size(),
                "max": self._pg_pool.get_max_size(),
            }
        return None
