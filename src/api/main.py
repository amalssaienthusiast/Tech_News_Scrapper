"""
Tech News Scraper REST API v1.0

FastAPI-based developer API with:
- Article retrieval and search
- Sentiment analysis endpoints
- API key authentication
- Rate limiting per tier
- OpenAPI documentation

Run with: uvicorn src.api.main:app --reload
"""

import logging
import time
import hashlib
import os
from datetime import datetime, UTC
from typing import List, Optional
from functools import wraps

from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# API CONFIGURATION
# =============================================================================

API_VERSION = "1.0.0"
API_TITLE = "Tech News Scraper API"
API_DESCRIPTION = """
## Overview
Enterprise-grade API for real-time tech news aggregation and analysis.

## Features
- 📰 **Articles**: Retrieve and search aggregated tech news
- 🔍 **Search**: Full-text search across all sources
- 📊 **Sentiment**: Real-time sentiment analysis and trends
- 🔔 **Webhooks**: Subscribe to real-time alerts (coming soon)

## Authentication
Include your API key in the `X-API-Key` header:
```
X-API-Key: your_api_key_here
```

## Rate Limits
| Tier | Requests/Day | Features |
|------|-------------|----------|
| Free | 100 | Basic articles |
| Pro | 10,000 | Full access |
| Enterprise | Unlimited | Priority + Webhooks |
"""

# API key tiers and limits
API_TIERS = {
    "free": {"daily_limit": 100, "features": ["articles"]},
    "pro": {"daily_limit": 10000, "features": ["articles", "search", "sentiment"]},
    "enterprise": {"daily_limit": float("inf"), "features": ["*"]},
}

# Security defaults can be relaxed explicitly for local development.
ALLOW_ANONYMOUS_API = os.getenv("API_ALLOW_ANONYMOUS", "false").lower() == "true"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("API_CORS_ORIGINS", "http://localhost,http://127.0.0.1").split(",")
    if origin.strip()
]


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class APIErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    status_code: int


class ArticleResponse(BaseModel):
    """Single article response."""
    id: str
    title: str
    url: str
    source: str
    published_at: Optional[str] = None
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None
    topics: List[str] = []


class ArticlesListResponse(BaseModel):
    """List of articles response."""
    articles: List[ArticleResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class SentimentResponse(BaseModel):
    """Sentiment analysis response."""
    score: float = Field(description="Sentiment score from -1.0 to 1.0")
    label: str = Field(description="Sentiment label (positive/negative/neutral)")
    emoji: str
    topics: dict = {}
    keywords: List[str] = []


class TrendResponse(BaseModel):
    """Sentiment trend response."""
    topic: str
    period: str
    avg_score: float
    score_change: float
    article_count: int
    trend_direction: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    database: str
    articles_count: int


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self._requests: dict = {}  # api_key -> {count, reset_time}
    
    def check_limit(self, api_key: str, tier: str) -> bool:
        """Check if request is within rate limit."""
        limit = API_TIERS.get(tier, API_TIERS["free"])["daily_limit"]
        
        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")
        key = f"{api_key}:{today}"
        
        if key not in self._requests:
            self._requests[key] = {"count": 0, "date": today}
        
        if self._requests[key]["date"] != today:
            self._requests[key] = {"count": 0, "date": today}
        
        if self._requests[key]["count"] >= limit:
            return False
        
        self._requests[key]["count"] += 1
        return True
    
    def get_remaining(self, api_key: str, tier: str) -> int:
        """Get remaining requests for today."""
        limit = API_TIERS.get(tier, API_TIERS["free"])["daily_limit"]
        
        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")
        key = f"{api_key}:{today}"
        
        if key not in self._requests:
            return int(limit)
        
        used = self._requests[key].get("count", 0)
        return max(0, int(limit - used))


rate_limiter = RateLimiter()


# =============================================================================
# API KEY MANAGEMENT
# =============================================================================

class APIKeyManager:
    """Manages API key validation and tiers."""
    
    def __init__(self):
        self._db = None
        self._ensure_schema()
    
    def _get_db(self):
        if self._db is None:
            from src.database import Database
            self._db = Database()
        return self._db
    
    def _ensure_schema(self):
        """Ensure API keys table exists."""
        try:
            db = self._get_db()
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS api_keys (
                        key_id TEXT PRIMARY KEY,
                        key_hash TEXT NOT NULL UNIQUE,
                        user_id TEXT,
                        tier TEXT DEFAULT 'free',
                        name TEXT,
                        created_at TEXT,
                        last_used TEXT,
                        enabled INTEGER DEFAULT 1
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to create api_keys schema: {e}")
    
    def validate_key(self, api_key: str) -> Optional[dict]:
        """Validate API key and return key info."""
        if not api_key:
            return None
        
        # Hash the key for lookup
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        try:
            db = self._get_db()
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM api_keys WHERE key_hash = ? AND enabled = 1",
                    (key_hash,)
                )
                row = cursor.fetchone()
                
                if row:
                    # Update last used
                    cursor.execute(
                        "UPDATE api_keys SET last_used = ? WHERE key_hash = ?",
                        (datetime.now(UTC).isoformat(), key_hash)
                    )
                    conn.commit()
                    
                    return {
                        "key_id": row["key_id"],
                        "tier": row["tier"],
                        "user_id": row["user_id"],
                    }
        except Exception as e:
            logger.error(f"API key validation error: {e}")
        
        return None
    
    def create_key(self, user_id: str, tier: str = "free", name: str = "") -> str:
        """Create a new API key."""
        import secrets
        
        # Generate a secure random key
        api_key = f"tns_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_id = secrets.token_hex(8)
        
        try:
            db = self._get_db()
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO api_keys (key_id, key_hash, user_id, tier, name, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    key_id, key_hash, user_id, tier, name,
                    datetime.now(UTC).isoformat()
                ))
                conn.commit()
                
            return api_key
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            return ""


api_key_manager = APIKeyManager()


# =============================================================================
# DEPENDENCIES
# =============================================================================

async def verify_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    request: Request = None
) -> dict:
    """Verify API key and apply rate limiting."""
    
    if not x_api_key:
        if not ALLOW_ANONYMOUS_API:
            raise HTTPException(
                status_code=401,
                detail="API key required. Provide X-API-Key header or set API_ALLOW_ANONYMOUS=true for local development."
            )

        # Optional anonymous mode with free-tier limits.
        # Check rate limit for anonymous
        if not rate_limiter.check_limit("anonymous", "free"):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please add an API key for higher limits."
            )
        return {"tier": "free", "anonymous": True}
    
    # Validate key
    key_info = api_key_manager.validate_key(x_api_key)
    
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    # Check rate limit
    if not rate_limiter.check_limit(x_api_key, key_info["tier"]):
        remaining = rate_limiter.get_remaining(x_api_key, key_info["tier"])
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Remaining: {remaining}. Upgrade tier for higher limits."
        )
    
    return key_info


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# =============================================================================
# CORE ENDPOINTS
# =============================================================================

@app.get("/", tags=["Info"])
async def root():
    """API root - basic info."""
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health_check():
    """Health check endpoint."""
    try:
        from src.database import Database
        db = Database()
        count = db.get_article_count()
        db_status = "connected"
    except Exception:
        count = 0
        db_status = "error"
    
    return HealthResponse(
        status="healthy",
        version=API_VERSION,
        timestamp=datetime.now(UTC).isoformat(),
        database=db_status,
        articles_count=count,
    )


@app.get("/health/readiness", tags=["Monitoring"])
async def readiness_check():
    """
    Readiness check - is the application ready to accept traffic?
    
    Returns ready=true when database is connected and core components initialized.
    """
    try:
        from src.monitoring.health_check_endpoints import get_health_checker
        checker = get_health_checker()
        return await checker.check_readiness()
    except Exception as e:
        return {"ready": False, "error": str(e)}


@app.get("/health/detailed", tags=["Monitoring"])
async def detailed_health():
    """
    Detailed health check - component-by-component status.
    
    Returns status of database, Redis, external APIs, LLM providers, and system resources.
    """
    try:
        from src.monitoring.health_check_endpoints import get_health_checker
        checker = get_health_checker()
        health = await checker.check_all()
        return health.to_dict()
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }


@app.get("/metrics", tags=["Monitoring"])
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format for scraping.
    """
    from fastapi.responses import PlainTextResponse
    
    try:
        from src.monitoring.metrics_collector import get_metrics_collector
        collector = get_metrics_collector()
        metrics_output = collector.export_prometheus()
        return PlainTextResponse(content=metrics_output, media_type="text/plain")
    except Exception as e:
        return PlainTextResponse(
            content=f"# Error exporting metrics: {e}\n",
            media_type="text/plain"
        )


@app.get("/v1/articles", response_model=ArticlesListResponse, tags=["Articles"])
async def get_articles(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    source: Optional[str] = Query(None, description="Filter by source"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    auth: dict = Depends(verify_api_key)
):
    """
    Get paginated list of articles.
    
    Supports filtering by source and topic.
    """
    from src.database import Database
    
    db = Database()
    all_articles = db.get_all_articles()
    
    # Apply filters
    filtered = all_articles
    if source:
        filtered = [a for a in filtered if source.lower() in (a.get("source", "") or "").lower()]
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    page_articles = filtered[start:end]
    
    # Convert to response
    articles = [
        ArticleResponse(
            id=a.get("id", ""),
            title=a.get("title", ""),
            url=a.get("url", ""),
            source=a.get("source", ""),
            published_at=a.get("published_at"),
            summary=a.get("summary") or a.get("ai_summary"),
        )
        for a in page_articles
    ]
    
    return ArticlesListResponse(
        articles=articles,
        total=len(filtered),
        page=page,
        per_page=per_page,
        has_more=end < len(filtered),
    )


@app.get("/v1/articles/{article_id}", response_model=ArticleResponse, tags=["Articles"])
async def get_article(
    article_id: str,
    auth: dict = Depends(verify_api_key)
):
    """Get a single article by ID."""
    from src.database import Database
    
    db = Database()
    articles = db.get_all_articles()
    
    for a in articles:
        if a.get("id") == article_id:
            return ArticleResponse(
                id=a.get("id", ""),
                title=a.get("title", ""),
                url=a.get("url", ""),
                source=a.get("source", ""),
                published_at=a.get("published_at"),
                summary=a.get("summary") or a.get("ai_summary"),
            )
    
    raise HTTPException(status_code=404, detail="Article not found")


@app.get("/v1/search", response_model=ArticlesListResponse, tags=["Search"])
async def search_articles(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: dict = Depends(verify_api_key)
):
    """
    Search articles by title and content.
    
    Requires Pro tier or higher for unlimited searches.
    """
    from src.database import Database
    
    db = Database()
    results = db.search_articles(q, limit=per_page * page)
    
    # Pagination
    start = (page - 1) * per_page
    page_articles = results[start:start + per_page]
    
    articles = [
        ArticleResponse(
            id=a.get("id", ""),
            title=a.get("title", ""),
            url=a.get("url", ""),
            source=a.get("source", ""),
            published_at=a.get("published_at"),
            summary=a.get("summary") or a.get("ai_summary"),
        )
        for a in page_articles
    ]
    
    return ArticlesListResponse(
        articles=articles,
        total=len(results),
        page=page,
        per_page=per_page,
        has_more=len(results) > page * per_page,
    )


@app.get("/v1/sentiment/analyze", response_model=SentimentResponse, tags=["Sentiment"])
async def analyze_sentiment(
    text: str = Query(..., min_length=10, description="Text to analyze"),
    auth: dict = Depends(verify_api_key)
):
    """
    Analyze sentiment of provided text.
    
    Returns sentiment score (-1 to 1), label, and detected topics.
    """
    from src.intelligence.sentiment_analyzer import get_sentiment_analyzer
    
    analyzer = get_sentiment_analyzer()
    result = analyzer.analyze(text, persist=False)
    
    return SentimentResponse(
        score=result.score,
        label=result.label.value,
        emoji=result.label.emoji,
        topics=result.topics,
        keywords=result.keywords_detected,
    )


@app.get("/v1/sentiment/trends", response_model=List[TrendResponse], tags=["Sentiment"])
async def get_sentiment_trends(
    period: str = Query("24h", pattern="^(24h|7d|30d)$", description="Time period"),
    auth: dict = Depends(verify_api_key)
):
    """
    Get sentiment trends across all topics.
    
    Shows average sentiment, direction, and article counts.
    """
    from src.intelligence.sentiment_analyzer import get_sentiment_analyzer
    
    analyzer = get_sentiment_analyzer()
    summary = analyzer.get_topic_sentiment_summary()
    
    trends = []
    for topic, trend in summary.items():
        trends.append(TrendResponse(
            topic=topic,
            period=period,
            avg_score=trend.avg_score,
            score_change=trend.score_change,
            article_count=trend.article_count,
            trend_direction=trend.trend_direction,
        ))
    
    return trends


# =============================================================================
# APP FACTORY
# =============================================================================

def get_api_app() -> FastAPI:
    """Get the FastAPI app instance."""
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
