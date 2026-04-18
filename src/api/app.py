from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import asyncio
import json
import os
from datetime import datetime


# Import main class components (need to handle imports carefully to avoid circular dependency if main imports app)
# Ideally main imports app to run it, or app imports aggregator logic.
# Let's import RealTimeNewsAggregator here if possible, but it might depend on loop.
# Better design: Pass aggregator instance to app state or create one.
# For simplicity, we will instantiate a lightweight interface or shared singleton resource.

from src.db_storage.db_handler import DatabaseHandler
from config.config import load_config
from src.feed_generator.live_feed import LiveFeedGenerator
from src.scheduler.task_scheduler import ScraperScheduler
from src.scrapers.factory import ScraperFactory


app = FastAPI(title="Real-Time News API")

# Comma-separated list in env, e.g. "http://localhost:3000,https://example.com"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("API_CORS_ORIGINS", "http://localhost,http://127.0.0.1").split(",")
    if origin.strip()
]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
class AppState:
    aggregator = None # Reference to main aggregator instance if running in same process

state = AppState()

# WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
db_handler = DatabaseHandler()

@app.on_event("startup")
async def startup_event():
    await db_handler.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    await db_handler.close()

@app.get("/")
async def root():
    return {"message": "Real-Time News Aggregator API", "status": "running"}

@app.get("/feed/latest")
async def get_latest_feed(limit: int = 50):
    """Get latest news feed from database"""
    articles = await db_handler.get_latest_articles(limit=limit)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(articles),
        "articles": articles
    }

@app.websocket("/feed/ws")
async def websocket_feed(websocket: WebSocket):
    """WebSocket for real-time feed updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Poll DB for latest updates every 30s? 
            # In a real app, aggregator would push updates to this manager via an event bus.
            # Here we just send current DB state periodically.
            articles = await db_handler.get_latest_articles(limit=20)
            feed = {
                 "type": "update",
                 "timestamp": datetime.utcnow().isoformat(),
                 "articles": articles
            }
            await websocket.send_json(feed)
            await asyncio.sleep(30)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/sources")
async def get_sources():
    """Get available news sources"""
    config = load_config()
    return {
        "sources": [
            {
                "name": source["name"],
                "type": source["type"],
                "refresh_rate": source.get("refresh_rate", 300),
                "enabled": source.get("enabled", True)
            }
            for source in config["sources"]
            if source.get("enabled", True)
        ]
    }
