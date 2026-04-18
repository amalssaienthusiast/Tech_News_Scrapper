"""
ZeroMQ Event Publisher for Real-Time Updates.

Publishes events from the Python backend to C++ Qt clients
via ZeroMQ PUB/SUB pattern.
"""

import json
import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import ZeroMQ, gracefully degrade if not available
try:
    import zmq
    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False
    logger.warning("ZeroMQ not installed. Install with: pip install pyzmq")


class EventPublisher:
    """
    Publishes events via ZeroMQ for real-time C++ client consumption.
    
    Events are published as JSON strings with format:
    {
        "type": "article" | "metrics" | "log" | "resilience",
        "data": {...},
        "timestamp": "2024-01-01T00:00:00Z"
    }
    """
    
    DEFAULT_PORT = 5555
    
    def __init__(self, port: int = DEFAULT_PORT):
        """
        Initialize the event publisher.
        
        Args:
            port: ZeroMQ port to bind to (default 5555)
        """
        self.port = port
        self.socket: Optional[Any] = None
        self.context: Optional[Any] = None
        self._running = False
        self._lock = threading.Lock()
        
        if HAS_ZMQ:
            self._init_socket()
    
    def _init_socket(self):
        """Initialize ZeroMQ PUB socket."""
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PUB)
            self.socket.bind(f"tcp://*:{self.port}")
            self._running = True
            logger.info(f"ZeroMQ publisher bound to tcp://*:{self.port}")
        except Exception as e:
            logger.error(f"Failed to initialize ZeroMQ: {e}")
            self.socket = None
    
    def publish(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Publish an event.
        
        Args:
            event_type: Type of event ("article", "metrics", "log", "resilience")
            data: Event data dictionary
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.socket:
            return False
        
        from datetime import datetime, timezone
        
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            with self._lock:
                # Topic is the event type, for subscriber filtering
                topic = event_type.encode('utf-8')
                payload = json.dumps(message).encode('utf-8')
                self.socket.send_multipart([topic, payload])
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    def publish_article(self, article) -> bool:
        """Publish a new article event."""
        return self.publish("article", {
            "title": article.title,
            "summary": getattr(article, 'summary', ''),
            "url": article.url,
            "source": article.source,
            "timestamp": str(getattr(article, 'timestamp', '')),
            "tech_score": getattr(article, 'tech_score', 0.0),
            "tier": getattr(article, 'tier', 'standard'),
            "topics": getattr(article, 'topics', []),
        })
    
    def publish_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Publish metrics update."""
        return self.publish("metrics", metrics)
    
    def publish_log(self, level: str, message: str, module: str = "") -> bool:
        """Publish log message."""
        return self.publish("log", {
            "level": level,
            "message": message,
            "module": module,
        })
    
    def publish_resilience(self, event_data: Dict[str, Any]) -> bool:
        """Publish resilience system event."""
        return self.publish("resilience", event_data)
    
    def close(self):
        """Close the publisher."""
        self._running = False
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        logger.info("ZeroMQ publisher closed")


# Global publisher instance
_publisher: Optional[EventPublisher] = None


def get_publisher(port: int = EventPublisher.DEFAULT_PORT) -> EventPublisher:
    """Get or create the global event publisher."""
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher(port)
    return _publisher


def publish_event(event_type: str, data: Dict[str, Any]) -> bool:
    """Convenience function to publish an event."""
    return get_publisher().publish(event_type, data)
