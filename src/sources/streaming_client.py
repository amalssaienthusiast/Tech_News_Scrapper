"""
Streaming Client for Real-Time News Delivery.

Handles WebSocket and Server-Sent Events (SSE) connections for zero-latency news.
Uses asyncio for non-blocking I/O.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, List, Optional, Dict
from datetime import datetime, UTC

import aiohttp

logger = logging.getLogger(__name__)

class StreamingEvent:
    """Represents a streaming event (news article or update)."""
    def __init__(self, event_type: str, data: Dict[str, Any], source: str):
        self.type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.now(UTC)

class StreamingClient:
    """
    Manages real-time connections (WebSockets & SSE).
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._own_session = False
        self._running = False
        self._callbacks: List[Callable[[StreamingEvent], None]] = []
        self._tasks: List[asyncio.Task] = []
        
        # known WebSocket endpoints (public/example)
        self.websocket_urls = [
            # "wss://stream.example.com/news", # Placeholder
        ]
        
        # known SSE endpoints
        self.sse_urls = [
            # "https://news-api.example.com/stream", # Placeholder
        ]
        
    async def start(self):
        """Start streaming from all sources."""
        if self._running:
            return
            
        self._running = True
        
        if not self._session:
            self._session = aiohttp.ClientSession()
            self._own_session = True
            
        # Start connection tasks (simulated for now if no real URLs)
        # In a real scenario, we would iterate self.websocket_urls and self.sse_urls
        # and start _listen_websocket / _listen_sse tasks.
        
        # For demonstration of the "Antigravity" capability:
        # We will start a simulated quantum stream that generates high-frequency
        # news updates for testing the UI responsiveness.
        self._tasks.append(asyncio.create_task(self._simulate_quantum_stream()))
        
        logger.info("StreamingClient started")
        
    async def stop(self):
        """Stop all streaming connections."""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks = []
            
        if self._own_session and self._session:
            await self._session.close()
            
        logger.info("StreamingClient stopped")
        
    def add_callback(self, callback: Callable[[StreamingEvent], None]):
        """Subscribe to streaming events."""
        self._callbacks.append(callback)
        
    def _emit(self, event: StreamingEvent):
        """Emit event to subscribers."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Streaming callback error: {e}")

    async def _listen_websocket(self, url: str):
        """Listen to a WebSocket feed."""
        while self._running:
            try:
                async with self._session.ws_connect(url) as ws:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            event = StreamingEvent("news", data, "websocket")
                            self._emit(event)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
            except Exception as e:
                logger.debug(f"WS connection error ({url}): {e}")
                await asyncio.sleep(5) # Reconnect delay

    async def _listen_sse(self, url: str):
        """Listen to an SSE feed (manual implementation)."""
        while self._running:
            try:
                async with self._session.get(url, headers={'Accept': 'text/event-stream'}) as response:
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = json.loads(line[6:])
                            event = StreamingEvent("news", data, "sse")
                            self._emit(event)
            except Exception as e:
                logger.debug(f"SSE connection error ({url}): {e}")
                await asyncio.sleep(5)

    async def _simulate_quantum_stream(self):
        """
        Simulates a quantum news stream for the Antigravity UI.
        Generates events to verify the real-time pipeline.
        """
        import random
        topics = ["Quantum Computing", "AI Singularity", "Nuclear Fusion", "SpaceX Mars"]
        
        while self._running:
            await asyncio.sleep(random.uniform(5.0, 15.0)) # Random interval
            
            topic = random.choice(topics)
            event = StreamingEvent(
                event_type="news",
                data={
                    "title": f"BREAKING: New Breakthrough in {topic}",
                    "url": f"https://example.com/news/{int(datetime.now().timestamp())}",
                    "summary": f"Scientists have just announced a major discovery in {topic} field...",
                    "source": "QuantumStream",
                    "published_at": datetime.now(UTC).isoformat()
                },
                source="AntigravityFeed"
            )
            self._emit(event)
