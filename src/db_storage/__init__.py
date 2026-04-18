"""
Database storage package for Tech News Scraper.

Provides flexible storage with three modes:
- EPHEMERAL: In-memory only, articles expire after TTL (best for live feeds)
- PERSISTENT: Full PostgreSQL/SQLite storage
- HYBRID: In-memory articles + persistent dedup/AI cache (recommended)

Usage:
    from src.db_storage import get_storage_manager, StorageMode
    
    # Get unified storage (mode from config or env var)
    storage = await get_storage_manager()
    
    # Or specify mode explicitly
    storage = await get_storage_manager(mode=StorageMode.HYBRID)
    
    # Unified API works in all modes
    await storage.add_article({"title": "...", "url": "...", "source": "..."})
    articles = await storage.get_all_articles()
    
    # Save/export (ephemeral & hybrid modes)
    storage.save_article(article_id)  # Won't expire
    saved = storage.get_saved_articles()
    
    # Switch modes at runtime
    await storage.set_mode(StorageMode.EPHEMERAL)
    
Environment variables:
    STORAGE_MODE: "ephemeral", "persistent", or "hybrid"
    DATABASE_URL: PostgreSQL URL (for persistent/hybrid modes)
"""

# Storage modes
from src.db_storage.ephemeral_store import StorageMode

# Unified storage manager (recommended)
from src.db_storage.unified_storage import (
    UnifiedStorageManager,
    get_storage_manager,
    set_storage_mode,
)

# Ephemeral store (for direct access)
from src.db_storage.ephemeral_store import (
    EphemeralArticleStore,
    get_ephemeral_store,
)

# Async database (for persistent mode)
from src.db_storage.async_database import (
    AsyncDatabaseManager,
    DatabaseBackend,
    get_async_database,
)


__all__ = [
    # Modes
    "StorageMode",
    
    # Unified storage (recommended API)
    "UnifiedStorageManager",
    "get_storage_manager",
    "set_storage_mode",
    
    # Ephemeral storage
    "EphemeralArticleStore",
    "get_ephemeral_store",
    
    # Persistent storage
    "AsyncDatabaseManager",
    "DatabaseBackend",
    "get_async_database",
]