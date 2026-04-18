
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime
from typing import Dict, List

Base = declarative_base()

class ArticleModel(Base):
    __tablename__ = 'live_articles'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    url = Column(String, index=True)
    source = Column(String)
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    content = Column(Text)
    media_url = Column(String)
    categories = Column(JSON)
    metadata_json = Column(JSON) # Store extra fields

class DatabaseHandler:
    """Async database handler for real-time feed"""
    
    def __init__(self, db_url: str = "sqlite+aiosqlite:///live_feed.db"):
        self.db_url = db_url
        self.engine = None
        self.logger = logging.getLogger('db_handler')
        self.SessionLocal = None
        
    async def initialize(self):
        """Initialize database connection and tables"""
        self.engine = create_async_engine(self.db_url, echo=False)
        self.SessionLocal = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    async def store_feed(self, feed_data: Dict):
        """Store articles from feed generation"""
        if not self.SessionLocal:
            await self.initialize()
            
        async with self.SessionLocal() as session:
            try:
                for article in feed_data.get('articles', []):
                    # Check if exists
                    article_id = article.get('id')
                    existing = await session.get(ArticleModel, article_id)
                    
                    if not existing:
                        # Prepare metadata which might contain datetimes
                        meta = article.copy()
                        # specific fields already in columns might duplicate but thats fine for metadata
                        # Ensure serialization of datetime objects
                        def json_serial(obj):
                            if isinstance(obj, (datetime, datetime.date)):
                                return obj.isoformat()
                            raise TypeError (f"Type {type(obj)} not serializable")
                        
                        # We can just convert known datetime fields in meta manually or use a helper
                        # Simpler: convert published_at and scraped_at in meta to str
                        if 'published_at' in meta and isinstance(meta['published_at'], datetime):
                            meta['published_at'] = meta['published_at'].isoformat()
                        if 'scraped_at' in meta and isinstance(meta['scraped_at'], datetime):
                            meta['scraped_at'] = meta['scraped_at'].isoformat()
                            
                        db_article = ArticleModel(
                            id=article_id,
                            title=article.get('title'),
                            url=article.get('url'),
                            source=article.get('source'),
                            published_at=article.get('published_at'), # Should be datetime obj, handled by Column(DateTime)
                            scraped_at=datetime.utcnow(),
                            description=article.get('description'),
                            content=article.get('content', ''),
                            media_url=article.get('media_url'),
                            categories=article.get('categories', []),
                            metadata_json=meta
                        )
                        session.add(db_article)
                
                await session.commit()
            except Exception as e:
                self.logger.error(f"Error storing feed: {e}")
                await session.rollback()
    
    async def get_latest_articles(self, limit: int = 100) -> List[Dict]:
        """Retrieve latest articles"""
        from sqlalchemy import select
        
        if not self.SessionLocal:
            await self.initialize()
            
        async with self.SessionLocal() as session:
            result = await session.execute(
                select(ArticleModel).order_by(ArticleModel.published_at.desc()).limit(limit)
            )
            articles = result.scalars().all()
            
            return [
                {
                    'id': a.id,
                    'title': a.title,
                    'url': a.url,
                    'source': a.source,
                    'published_at': a.published_at,
                    'description': a.description,
                    'media_url': a.media_url,
                    'categories': a.categories
                }
                for a in articles
            ]

    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
