"""
Tests for AsyncDatabaseManager with PostgreSQL and SQLite backends.

Run with:
    pytest tests/test_async_database.py -v
    
For PostgreSQL tests, set DATABASE_URL:
    DATABASE_URL=postgresql://postgres:test@localhost:5432/tech_news pytest tests/test_async_database.py -v
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

# Check for required dependencies
try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

try:
    import asyncpg
    HAS_ASYNCPG = True  
except ImportError:
    HAS_ASYNCPG = False


# Skip all tests if aiosqlite not available
pytestmark = pytest.mark.skipif(
    not HAS_AIOSQLITE,
    reason="aiosqlite required for async database tests"
)


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_news.db"


@pytest.fixture
def mock_data_dir(temp_db_path):
    """Mock DATA_DIR to use temporary location."""
    with patch("src.db_storage.async_database.DATA_DIR", temp_db_path.parent):
        yield temp_db_path.parent


class TestDatabaseBackend:
    """Tests for DatabaseBackend enum and detection."""
    
    def test_backend_enum_values(self):
        from src.db_storage.async_database import DatabaseBackend
        
        assert DatabaseBackend.SQLITE.value == "sqlite"
        assert DatabaseBackend.POSTGRESQL.value == "postgresql"
    
    def test_sqlite_detection_no_url(self, mock_data_dir):
        """SQLite should be selected when no DATABASE_URL is set."""
        from src.db_storage.async_database import AsyncDatabaseManager
        
        with patch.dict(os.environ, {}, clear=True):
            db = AsyncDatabaseManager(database_url=None)
            assert db.backend.value == "sqlite"
    
    @pytest.mark.skipif(not HAS_ASYNCPG, reason="asyncpg required")
    def test_postgresql_detection_with_url(self, mock_data_dir):
        """PostgreSQL should be selected when DATABASE_URL is set."""
        from src.db_storage.async_database import AsyncDatabaseManager
        
        db = AsyncDatabaseManager(database_url="postgresql://user:pass@localhost/test")
        assert db.backend.value == "postgresql"


class TestAsyncDatabaseManagerSQLite:
    """Tests for AsyncDatabaseManager with SQLite backend."""
    
    @pytest_asyncio.fixture
    async def db(self, mock_data_dir):
        """Create and initialize a test database."""
        from src.db_storage.async_database import AsyncDatabaseManager
        
        db = AsyncDatabaseManager(database_url=None)
        db.db_path = mock_data_dir / "tech_news.db"
        await db.initialize()
        yield db
        await db.close()
    
    @pytest.mark.asyncio
    async def test_initialize_creates_schema(self, db):
        """Test that initialization creates database schema."""
        assert db._initialized
        assert db.db_path.exists()
    
    @pytest.mark.asyncio
    async def test_add_article(self, db):
        """Test adding an article."""
        article = {
            "title": "Test Article",
            "url": "https://example.com/article1",
            "source": "Test Source",
        }
        
        result = await db.add_article(article)
        assert result is True
        
        # Should not add duplicate
        result = await db.add_article(article)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_all_articles(self, db):
        """Test retrieving all articles."""
        # Add test articles
        for i in range(5):
            await db.add_article({
                "title": f"Article {i}",
                "url": f"https://example.com/article{i}",
                "source": "Test Source",
            })
        
        articles = await db.get_all_articles()
        assert len(articles) == 5
    
    @pytest.mark.asyncio
    async def test_add_source(self, db):
        """Test adding a discovered source."""
        source = {
            "url": "https://example.com/feed.rss",
            "type": "rss",
            "name": "Example Feed",
        }
        
        result = await db.add_discovered_source(source)
        assert result is True
        
        # Should not add duplicate
        result = await db.add_discovered_source(source)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_search_articles(self, db):
        """Test article search functionality."""
        await db.add_article({
            "title": "Machine Learning Breakthrough",
            "url": "https://example.com/ml",
            "source": "Tech News",
            "ai_summary": "A new approach to neural networks",
        })
        await db.add_article({
            "title": "Cryptocurrency Update",
            "url": "https://example.com/crypto",
            "source": "Finance News",
        })
        
        results = await db.search_articles("Machine Learning")
        assert len(results) >= 1
        assert "Machine Learning" in results[0]["title"]
    
    @pytest.mark.asyncio
    async def test_article_count(self, db):
        """Test getting article count."""
        initial_count = await db.get_article_count()
        
        await db.add_article({
            "title": "Test",
            "url": "https://example.com/test",
            "source": "Test",
        })
        
        new_count = await db.get_article_count()
        assert new_count == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_add_intelligence(self, db):
        """Test adding intelligence analysis."""
        # First add an article
        await db.add_article({
            "id": "test-article-1",
            "title": "Breaking Tech News",
            "url": "https://example.com/breaking",
            "source": "Tech News",
        })
        
        # Add intelligence
        result = await db.add_intelligence(
            article_id="test-article-1",
            provider="gemini",
            disruptive=True,
            criticality=8,
            justification="Major market impact expected",
            affected_markets=["cloud", "ai"],
            affected_companies=["GOOGL", "MSFT"],
            sentiment="positive",
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_high_criticality_articles(self, db):
        """Test retrieving high criticality articles."""
        # Add article with intelligence
        await db.add_article({
            "id": "critical-1",
            "title": "Critical News",
            "url": "https://example.com/critical",
            "source": "News",
        })
        await db.add_intelligence(
            article_id="critical-1",
            provider="gemini",
            disruptive=True,
            criticality=9,
            justification="Very important",
        )
        
        results = await db.get_high_criticality_articles(min_criticality=7)
        assert len(results) >= 1


@pytest.mark.skipif(
    not HAS_ASYNCPG or not os.environ.get("DATABASE_URL"),
    reason="asyncpg and DATABASE_URL required for PostgreSQL tests"
)
class TestAsyncDatabaseManagerPostgreSQL:
    """Tests for AsyncDatabaseManager with PostgreSQL backend."""
    
    @pytest_asyncio.fixture
    async def db(self):
        """Create and initialize a PostgreSQL test database."""
        from src.db_storage.async_database import AsyncDatabaseManager
        
        database_url = os.environ.get("DATABASE_URL")
        db = AsyncDatabaseManager(database_url=database_url)
        await db.initialize()
        yield db
        
        # Cleanup: remove test data
        async with db.acquire() as conn:
            await conn.execute("DELETE FROM articles WHERE url LIKE '%example.com%'")
            await conn.execute("DELETE FROM sources WHERE url LIKE '%example.com%'")
        
        await db.close()
    
    @pytest.mark.asyncio
    async def test_postgresql_connection(self, db):
        """Test PostgreSQL connection and pool."""
        assert db.is_postgresql
        assert db._pg_pool is not None
        
        stats = db.pool_stats
        assert stats is not None
        assert stats["size"] >= 1
    
    @pytest.mark.asyncio
    async def test_add_and_retrieve_article(self, db):
        """Test adding and retrieving articles via PostgreSQL."""
        import uuid
        
        unique_id = str(uuid.uuid4())
        article = {
            "id": unique_id,
            "title": f"PostgreSQL Test Article {unique_id}",
            "url": f"https://example.com/pg-test-{unique_id}",
            "source": "PostgreSQL Test",
        }
        
        result = await db.add_article(article)
        assert result is True
        
        count = await db.get_article_count()
        assert count >= 1
    
    @pytest.mark.asyncio
    async def test_full_text_search(self, db):
        """Test PostgreSQL full-text search with GIN index."""
        import uuid
        
        unique_id = str(uuid.uuid4())
        await db.add_article({
            "id": unique_id,
            "title": f"Quantum Computing Advancement {unique_id}",
            "url": f"https://example.com/quantum-{unique_id}",
            "source": "Science News",
            "ai_summary": "Researchers demonstrate quantum supremacy",
        })
        
        results = await db.search_articles("quantum computing")
        # Should find the article using full-text search
        assert any(unique_id in str(r) for r in results)


class TestSingleton:
    """Tests for singleton pattern."""
    
    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self, mock_data_dir):
        """get_async_database should return the same instance."""
        import src.db_storage.async_database as db_module
        
        # Reset singleton
        db_module._async_db_instance = None
        
        db1 = await db_module.get_async_database()
        db2 = await db_module.get_async_database()
        
        assert db1 is db2
        
        await db1.close()
        db_module._async_db_instance = None
