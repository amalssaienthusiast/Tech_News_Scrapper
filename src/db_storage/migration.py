"""
Migration utilities for SQLite to PostgreSQL data transfer.

This module provides tools to migrate existing SQLite data to PostgreSQL
for production deployment with minimal downtime.

Usage:
    python -m src.db_storage.migration --source sqlite --target postgresql

Or programmatically:
    from src.db_storage.migration import migrate_sqlite_to_postgresql
    await migrate_sqlite_to_postgresql(sqlite_path, pg_url)
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from dateutil import parser as date_parser
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

from config.settings import DATA_DIR

logger = logging.getLogger(__name__)


def _parse_datetime(value: Any) -> Any:
    """
    Parse datetime string to datetime object for PostgreSQL.

    Args:
        value: DateTime string, datetime object, or None

    Returns:
        datetime object or None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date_parser.isoparse(value)
        except (ValueError, TypeError):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None
    return None


async def migrate_sqlite_to_postgresql(
    sqlite_path: Optional[Path] = None,
    postgresql_url: Optional[str] = None,
    batch_size: int = 500,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Migrate data from SQLite to PostgreSQL.

    Args:
        sqlite_path: Path to SQLite database (default: DATA_DIR/tech_news.db)
        postgresql_url: PostgreSQL connection URL (default: DATABASE_URL env var)
        batch_size: Number of records to insert per batch
        dry_run: If True, only report what would be migrated without writing

    Returns:
        Migration summary with counts and timing
    """
    if not asyncpg or not aiosqlite:
        raise ImportError(
            "Both asyncpg and aiosqlite are required for migration. "
            "Install with: pip install asyncpg aiosqlite"
        )

    sqlite_path = sqlite_path or (DATA_DIR / "tech_news.db")
    postgresql_url = postgresql_url or os.environ.get("DATABASE_URL")

    if not postgresql_url:
        raise ValueError(
            "PostgreSQL URL required. Set DATABASE_URL or pass postgresql_url"
        )

    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    start_time = datetime.now()
    stats = {
        "articles_migrated": 0,
        "sources_migrated": 0,
        "intelligence_migrated": 0,
        "newsletters_migrated": 0,
        "errors": [],
    }

    logger.info(f"Starting migration from {sqlite_path} to PostgreSQL")
    logger.info(f"Dry run: {dry_run}")

    # Connect to both databases
    async with aiosqlite.connect(sqlite_path) as sqlite_db:
        sqlite_db.row_factory = aiosqlite.Row

        pg_pool = await asyncpg.create_pool(postgresql_url, min_size=2, max_size=10)

        try:
            async with pg_pool.acquire() as pg_conn:
                # Create schema if not exists
                await _ensure_postgresql_schema(pg_conn)

                # Migrate articles
                stats["articles_migrated"] = await _migrate_articles(
                    sqlite_db, pg_conn, batch_size, dry_run
                )

                # Migrate sources
                stats["sources_migrated"] = await _migrate_sources(
                    sqlite_db, pg_conn, batch_size, dry_run
                )

                # Migrate intelligence
                stats["intelligence_migrated"] = await _migrate_intelligence(
                    sqlite_db, pg_conn, batch_size, dry_run
                )

                # Migrate newsletters
                stats["newsletters_migrated"] = await _migrate_newsletters(
                    sqlite_db, pg_conn, batch_size, dry_run
                )

        finally:
            await pg_pool.close()

    stats["duration_seconds"] = (datetime.now() - start_time).total_seconds()

    logger.info(f"Migration completed in {stats['duration_seconds']:.2f}s")
    logger.info(f"Articles: {stats['articles_migrated']}")
    logger.info(f"Sources: {stats['sources_migrated']}")
    logger.info(f"Intelligence: {stats['intelligence_migrated']}")
    logger.info(f"Newsletters: {stats['newsletters_migrated']}")

    if stats["errors"]:
        logger.warning(f"Errors: {len(stats['errors'])}")

    return stats


async def _ensure_postgresql_schema(conn: "asyncpg.Connection") -> None:
    """Ensure PostgreSQL schema exists."""
    from src.db_storage.async_database import AsyncDatabaseManager

    # Use the schema creation from AsyncDatabaseManager
    db = AsyncDatabaseManager.__new__(AsyncDatabaseManager)
    await db._create_postgresql_schema(conn)


async def _migrate_articles(
    sqlite_db: "aiosqlite.Connection",
    pg_conn: "asyncpg.Connection",
    batch_size: int,
    dry_run: bool,
) -> int:
    """Migrate articles table."""
    cursor = await sqlite_db.execute("""
        SELECT id, title, url, source, published, scraped_at,
               ai_summary, full_content, tech_score, tier, topics
        FROM articles
    """)
    rows = await cursor.fetchall()

    if dry_run:
        logger.info(f"[DRY RUN] Would migrate {len(rows)} articles")
        return len(rows)

    count = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]

        await pg_conn.executemany(
            """
            INSERT INTO articles 
            (id, title, url, source, published, scraped_at, ai_summary, full_content,
             tech_score, tier, topics)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (url) DO NOTHING
        """,
            [
                (
                    row["id"],
                    row["title"],
                    row["url"],
                    row["source"],
                    _parse_datetime(row["published"]),
                    _parse_datetime(row["scraped_at"]) or datetime.now(timezone.utc),
                    row["ai_summary"],
                    row["full_content"],
                    row["tech_score"],
                    row["tier"],
                    row["topics"],
                )
                for row in batch
            ],
        )

        count += len(batch)
        logger.info(f"Migrated {count}/{len(rows)} articles")

    return count


async def _migrate_sources(
    sqlite_db: "aiosqlite.Connection",
    pg_conn: "asyncpg.Connection",
    batch_size: int,
    dry_run: bool,
) -> int:
    """Migrate sources table."""
    cursor = await sqlite_db.execute("""
        SELECT url, original_url, type, name, verified,
               discovered_at, quality_score, article_count
        FROM sources
    """)
    rows = await cursor.fetchall()

    if dry_run:
        logger.info(f"[DRY RUN] Would migrate {len(rows)} sources")
        return len(rows)

    count = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]

        await pg_conn.executemany(
            """
            INSERT INTO sources 
            (url, original_url, type, name, verified, discovered_at, 
             quality_score, article_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (url) DO NOTHING
        """,
            [
                (
                    row["url"],
                    row["original_url"],
                    row["type"],
                    row["name"],
                    bool(row["verified"]),
                    _parse_datetime(row["discovered_at"]),
                    row["quality_score"],
                    row["article_count"],
                )
                for row in batch
            ],
        )

        count += len(batch)
        logger.info(f"Migrated {count}/{len(rows)} sources")

    return count


async def _migrate_intelligence(
    sqlite_db: "aiosqlite.Connection",
    pg_conn: "asyncpg.Connection",
    batch_size: int,
    dry_run: bool,
) -> int:
    """Migrate article_intelligence table."""
    cursor = await sqlite_db.execute("""
        SELECT article_id, analyzed_at, provider, disruptive, criticality,
               justification, affected_markets, affected_companies, sentiment,
               relevance_score, categories, key_insights, alert_sent, alert_channel
        FROM article_intelligence
    """)
    rows = await cursor.fetchall()

    if dry_run:
        logger.info(f"[DRY RUN] Would migrate {len(rows)} intelligence records")
        return len(rows)

    count = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]

        await pg_conn.executemany(
            """
            INSERT INTO article_intelligence 
            (article_id, analyzed_at, provider, disruptive, criticality,
             justification, affected_markets, affected_companies, sentiment,
             relevance_score, categories, key_insights, alert_sent, alert_channel)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (article_id) DO NOTHING
        """,
            [
                (
                    row["article_id"],
                    _parse_datetime(row["analyzed_at"]) or datetime.now(timezone.utc),
                    row["provider"],
                    bool(row["disruptive"]),
                    row["criticality"],
                    row["justification"],
                    row["affected_markets"],  # Already JSON string
                    row["affected_companies"],
                    row["sentiment"],
                    row["relevance_score"],
                    row["categories"],
                    row["key_insights"],
                    bool(row["alert_sent"]),
                    row["alert_channel"],
                )
                for row in batch
            ],
        )

        count += len(batch)
        logger.info(f"Migrated {count}/{len(rows)} intelligence records")

    return count


async def _migrate_newsletters(
    sqlite_db: "aiosqlite.Connection",
    pg_conn: "asyncpg.Connection",
    batch_size: int,
    dry_run: bool,
) -> int:
    """Migrate newsletters table."""
    cursor = await sqlite_db.execute("""
        SELECT edition_date, name, subject_line, markdown_content,
               story_count, top_story_ids, generated_at, export_path, status
        FROM newsletters
    """)
    rows = await cursor.fetchall()

    if dry_run:
        logger.info(f"[DRY RUN] Would migrate {len(rows)} newsletters")
        return len(rows)

    count = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]

        await pg_conn.executemany(
            """
            INSERT INTO newsletters 
            (edition_date, name, subject_line, markdown_content,
             story_count, top_story_ids, generated_at, export_path, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (edition_date) DO NOTHING
        """,
            [
                (
                    row["edition_date"],
                    row["name"],
                    row["subject_line"],
                    row["markdown_content"],
                    row["story_count"],
                    row["top_story_ids"],  # Already JSON string
                    _parse_datetime(row["generated_at"]) or datetime.now(timezone.utc),
                    row["export_path"],
                    row["status"],
                )
                for row in batch
            ],
        )

        count += len(batch)
        logger.info(f"Migrated {count}/{len(rows)} newsletters")

    return count


async def verify_migration(
    sqlite_path: Optional[Path] = None,
    postgresql_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify migration by comparing record counts between databases.

    Returns:
        Comparison results with counts from both databases
    """
    sqlite_path = sqlite_path or (DATA_DIR / "tech_news.db")
    postgresql_url = postgresql_url or os.environ.get("DATABASE_URL")

    results = {
        "sqlite": {},
        "postgresql": {},
        "match": True,
    }

    # Get SQLite counts
    async with aiosqlite.connect(sqlite_path) as db:
        for table in ["articles", "sources", "article_intelligence", "newsletters"]:
            cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            results["sqlite"][table] = row[0]

    # Get PostgreSQL counts
    pg_pool = await asyncpg.create_pool(postgresql_url, min_size=1, max_size=2)
    try:
        async with pg_pool.acquire() as conn:
            for table in ["articles", "sources", "article_intelligence", "newsletters"]:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                results["postgresql"][table] = count
    finally:
        await pg_pool.close()

    # Compare
    for table in results["sqlite"]:
        if results["sqlite"][table] != results["postgresql"][table]:
            results["match"] = False
            logger.warning(
                f"Mismatch in {table}: "
                f"SQLite={results['sqlite'][table]}, "
                f"PostgreSQL={results['postgresql'][table]}"
            )

    return results


def main():
    """CLI entry point for migration."""
    parser = argparse.ArgumentParser(
        description="Migrate Tech News Scraper data from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=None,
        help="Path to SQLite database (default: data/tech_news.db)",
    )
    parser.add_argument(
        "--postgresql-url",
        type=str,
        default=None,
        help="PostgreSQL connection URL (default: DATABASE_URL env var)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500, help="Records per batch (default: 500)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be migrated without writing",
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify migration after completion"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    async def run():
        stats = await migrate_sqlite_to_postgresql(
            sqlite_path=args.sqlite_path,
            postgresql_url=args.postgresql_url,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        print("\n=== Migration Summary ===")
        print(f"Duration: {stats['duration_seconds']:.2f}s")
        print(f"Articles: {stats['articles_migrated']}")
        print(f"Sources: {stats['sources_migrated']}")
        print(f"Intelligence: {stats['intelligence_migrated']}")
        print(f"Newsletters: {stats['newsletters_migrated']}")

        if stats["errors"]:
            print(f"\nErrors: {len(stats['errors'])}")
            for err in stats["errors"][:5]:
                print(f"  - {err}")

        if args.verify and not args.dry_run:
            print("\n=== Verification ===")
            verify_results = await verify_migration(
                sqlite_path=args.sqlite_path,
                postgresql_url=args.postgresql_url,
            )
            print(f"Match: {verify_results['match']}")
            for table in verify_results["sqlite"]:
                sqlite_count = verify_results["sqlite"][table]
                pg_count = verify_results["postgresql"][table]
                status = "✓" if sqlite_count == pg_count else "✗"
                print(
                    f"  {table}: SQLite={sqlite_count}, PostgreSQL={pg_count} {status}"
                )

    asyncio.run(run())


if __name__ == "__main__":
    main()
