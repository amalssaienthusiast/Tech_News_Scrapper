"""
FastAPI Application for Tech News Scraper.

Exposes REST endpoints for the C++ Qt GUI to communicate
with the Python backend.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import existing backend modules
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine import TechNewsOrchestrator
from src.engine.enhanced_feeder import EnhancedNewsPipeline
from src.core.types import Article

logger = logging.getLogger(__name__)

# =============================================================================
# MODELS
# =============================================================================

class ArticleResponse(BaseModel):
    """Article data for API responses."""
    title: str
    summary: Optional[str] = None
    url: str
    source: str
    timestamp: Optional[str] = None
    tech_score: float = 0.0
    tier: str = "standard"
    topics: List[str] = []


class FeedStatus(BaseModel):
    """Current feed status."""
    running: bool
    article_count: int
    last_update: Optional[str] = None
    sources_active: int = 0
    error: Optional[str] = None


class FeedStartRequest(BaseModel):
    """Request to start the feed."""
    max_articles: int = 500
    max_age_hours: int = 48
    enable_discovery: bool = True


class ConfigSection(BaseModel):
    """Configuration section data."""
    section: str
    data: Dict[str, Any]


class MetricsResponse(BaseModel):
    """System metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    articles_processed: int = 0
    sources_active: int = 0
    errors_last_hour: int = 0
    uptime_seconds: float = 0.0


# =============================================================================
# GLOBAL STATE
# =============================================================================

class AppState:
    """Application state management."""
    def __init__(self):
        self.orchestrator: Optional[TechNewsOrchestrator] = None
        self.pipeline: Optional[EnhancedNewsPipeline] = None
        self.articles: List[Article] = []
        self.running: bool = False
        self.websocket_clients: List[WebSocket] = []
        self.start_time: Optional[float] = None
    
    async def broadcast(self, message: dict):
        """Broadcast message to all WebSocket clients."""
        disconnected = []
        for ws in self.websocket_clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.websocket_clients.remove(ws)


state = AppState()


# =============================================================================
# LIFESPAN & APP SETUP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan - startup and shutdown."""
    import time
    
    logger.info("Starting Tech News API...")
    state.start_time = time.time()
    
    # Initialize orchestrator
    try:
        state.orchestrator = TechNewsOrchestrator()
        logger.info("Orchestrator initialized")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Tech News API...")
    if state.pipeline:
        state.running = False


app = FastAPI(
    title="Tech News Scraper API",
    description="REST API for Tech News Scraper - bridges Python backend to C++ Qt GUI",
    version="1.0.0",
    lifespan=lifespan
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("API_CORS_ORIGINS", "http://localhost,http://127.0.0.1").split(",")
    if origin.strip()
]

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_app() -> FastAPI:
    """Get the FastAPI app instance."""
    return app


# =============================================================================
# FEED ROUTES
# =============================================================================

@app.post("/api/feed/start", response_model=FeedStatus)
async def start_feed(request: FeedStartRequest):
    """Start the news feed pipeline."""
    if state.running:
        return FeedStatus(
            running=True,
            article_count=len(state.articles),
            sources_active=10
        )
    
    try:
        state.pipeline = EnhancedNewsPipeline(
            enable_discovery=request.enable_discovery,
            max_articles=request.max_articles,
            max_age_hours=request.max_age_hours,
        )
        
        # Add callback for streaming to WebSocket clients
        if hasattr(state.pipeline, 'add_article_callback'):
            async def on_article(article):
                state.articles.insert(0, article)
                await state.broadcast({
                    "type": "article",
                    "data": {
                        "title": article.title,
                        "summary": getattr(article, 'summary', ''),
                        "url": article.url,
                        "source": article.source,
                        "timestamp": str(getattr(article, 'timestamp', '')),
                        "tech_score": getattr(article, 'tech_score', 0.0),
                        "tier": getattr(article, 'tier', 'standard'),
                    }
                })
            state.pipeline.add_article_callback(on_article)
        
        state.running = True
        logger.info("Feed started successfully")
        
        return FeedStatus(
            running=True,
            article_count=0,
            sources_active=10
        )
    except Exception as e:
        logger.error(f"Failed to start feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feed/stop")
async def stop_feed():
    """Stop the news feed pipeline."""
    state.running = False
    return {"status": "stopped"}


@app.get("/api/feed/status", response_model=FeedStatus)
async def get_feed_status():
    """Get current feed status."""
    return FeedStatus(
        running=state.running,
        article_count=len(state.articles),
        sources_active=10 if state.running else 0
    )


# =============================================================================
# ARTICLES ROUTES
# =============================================================================

@app.get("/api/articles", response_model=List[ArticleResponse])
async def get_articles(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    source: Optional[str] = None,
    tier: Optional[str] = None,
):
    """Get articles with pagination and optional filtering."""
    articles = state.articles
    
    # Apply filters
    if source:
        articles = [a for a in articles if a.source.lower() == source.lower()]
    if tier:
        articles = [a for a in articles if getattr(a, 'tier', 'standard') == tier]
    
    # Paginate
    paginated = articles[offset:offset + limit]
    
    return [
        ArticleResponse(
            title=a.title,
            summary=getattr(a, 'summary', None),
            url=a.url,
            source=a.source,
            timestamp=str(getattr(a, 'timestamp', '')),
            tech_score=getattr(a, 'tech_score', 0.0),
            tier=getattr(a, 'tier', 'standard'),
            topics=getattr(a, 'topics', []),
        )
        for a in paginated
    ]


@app.get("/api/articles/count")
async def get_article_count():
    """Get total article count."""
    return {"count": len(state.articles)}


# =============================================================================
# METRICS ROUTES
# =============================================================================

@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get system metrics."""
    import time
    
    try:
        import psutil
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
    except ImportError:
        cpu = 0.0
        memory = 0.0
    
    uptime = time.time() - state.start_time if state.start_time else 0.0
    
    return MetricsResponse(
        cpu_percent=cpu,
        memory_percent=memory,
        articles_processed=len(state.articles),
        sources_active=10 if state.running else 0,
        errors_last_hour=0,
        uptime_seconds=uptime,
    )


# =============================================================================
# CONFIG ROUTES
# =============================================================================

@app.get("/api/config/{section}")
async def get_config(section: str):
    """Get configuration section."""
    try:
        from gui.config_manager import get_config
        config = get_config()
        data = config.get_section(section)
        return {"section": section, "data": data}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Config section not found: {e}")


@app.put("/api/config/{section}")
async def update_config(section: str, data: Dict[str, Any]):
    """Update configuration section."""
    try:
        from gui.config_manager import get_config
        config = get_config()
        for key, value in data.items():
            config.set(section, key, value)
        config.save()
        return {"status": "updated", "section": section}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WEBSOCKET FOR REAL-TIME EVENTS
# =============================================================================

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time events."""
    await websocket.accept()
    state.websocket_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(state.websocket_clients)}")
    
    try:
        while True:
            # Keep connection alive, listen for any client messages
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        state.websocket_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(state.websocket_clients)}")


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "running": state.running,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
