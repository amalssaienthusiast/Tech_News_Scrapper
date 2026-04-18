"""
Real-Time Event Manager - Bridge between backend systems and GUI.

Provides seamless integration of:
- System metrics updates
- Resilience system events
- Bypass operation results
- AI processing status
- Alert notifications
"""

import asyncio
import logging
import threading
import queue
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events the manager handles."""
    METRICS_UPDATE = auto()
    SYSTEM_ALERT = auto()
    AI_PROCESSING = auto()
    BYPASS_RESULT = auto()
    RESILIENCE_EVENT = auto()
    NEWS_UPDATE = auto()
    CONFIG_CHANGE = auto()
    MODE_SWITCH = auto()


@dataclass
class GUIEvent:
    """Event structure for GUI updates."""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: int = 5  # 1=highest, 10=lowest
    user_visible: bool = True


class RealTimeEventManager:
    """
    Manages real-time updates between backend systems and GUI.
    
    Features:
    - Thread-safe event queuing
    - Priority-based processing
    - Configurable update frequency
    - Graceful degradation when backends unavailable
    
    Usage:
        event_manager = RealTimeEventManager(gui_instance)
        event_manager.start()
        
        # Subscribe to events
        event_manager.subscribe(EventType.METRICS_UPDATE, my_handler)
        
        # Publish events from backend
        event_manager.publish(EventType.SYSTEM_ALERT, {'message': 'Alert!'})
    """
    
    def __init__(self, gui_instance, update_interval_ms: int = 100):
        """
        Initialize the event manager.
        
        Args:
            gui_instance: The main TechNewsGUI instance
            update_interval_ms: How often to process events (default 100ms)
        """
        self.gui = gui_instance
        self.update_interval = update_interval_ms
        
        # Event queue (thread-safe)
        self._event_queue: queue.PriorityQueue = queue.PriorityQueue()
        
        # Subscribers by event type
        self._subscribers: Dict[EventType, List[Callable]] = {
            et: [] for et in EventType
        }
        
        # State
        self._running = False
        self._counter = 0  # For stable sort in priority queue
        
        # Metrics cache (avoid excessive updates)
        self._metrics_cache: Dict[str, Any] = {}
        self._last_metrics_update: Optional[datetime] = None
        
        logger.info("RealTimeEventManager initialized")
    
    def start(self) -> None:
        """Start the event processing loop."""
        if self._running:
            return
        
        self._running = True
        self._schedule_processing()
        
        # Try to connect to backend event bus
        self._connect_to_event_bus()
        
        logger.info("RealTimeEventManager started")
    
    def stop(self) -> None:
        """Stop the event processing loop."""
        self._running = False
        logger.info("RealTimeEventManager stopped")
    
    def subscribe(self, event_type: EventType, handler: Callable[[GUIEvent], None]) -> None:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Callback function for events
        """
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed {handler.__name__} to {event_type.name}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe from events."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
    
    def publish(self, event_type: EventType, data: Dict[str, Any], 
                priority: int = 5, user_visible: bool = True) -> None:
        """
        Publish an event to be processed.
        
        Args:
            event_type: Type of event
            data: Event data dictionary
            priority: 1=highest, 10=lowest
            user_visible: Whether this should trigger visible UI updates
        """
        event = GUIEvent(
            event_type=event_type,
            data=data,
            priority=priority,
            user_visible=user_visible
        )
        
        # Priority queue uses (priority, counter, event) for stable sorting
        self._counter += 1
        self._event_queue.put((priority, self._counter, event))
    
    def _schedule_processing(self) -> None:
        """Schedule the next event processing cycle."""
        if not self._running:
            return
        
        try:
            self._process_events()
            self.gui.root.after(self.update_interval, self._schedule_processing)
        except Exception as e:
            logger.error(f"Error in event processing: {e}")
            # Retry after a delay
            if self._running:
                self.gui.root.after(1000, self._schedule_processing)
    
    def _process_events(self) -> None:
        """Process all queued events."""
        events_processed = 0
        max_per_cycle = 20  # Limit to prevent UI freezing
        
        while not self._event_queue.empty() and events_processed < max_per_cycle:
            try:
                _, _, event = self._event_queue.get_nowait()
                self._dispatch_event(event)
                events_processed += 1
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error dispatching event: {e}")
    
    def _dispatch_event(self, event: GUIEvent) -> None:
        """Dispatch event to all subscribers."""
        handlers = self._subscribers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler {handler.__name__} error: {e}")
    
    def _connect_to_event_bus(self) -> None:
        """Connect to the core EventBus if available."""
        try:
            from src.core.events import event_bus
            from src.core.protocol import EventType as CoreEventType
            
            # Subscribe to relevant core events and forward to GUI
            async def forward_stats(event):
                self.publish(EventType.METRICS_UPDATE, event.data, priority=3)
            
            async def forward_log(event):
                self.publish(EventType.SYSTEM_ALERT, event.data, priority=5)
            
            # Register handlers
            event_bus.subscribe(CoreEventType.STATS_UPDATE, forward_stats)
            event_bus.subscribe(CoreEventType.LOG_MESSAGE, forward_log)
            
            logger.info("Connected to core EventBus")
        except ImportError:
            logger.debug("Core EventBus not available")
        except Exception as e:
            logger.warning(f"Could not connect to EventBus: {e}")
    
    # =========================================================================
    # HIGH-LEVEL HANDLERS
    # =========================================================================
    
    def handle_metrics_update(self, event: GUIEvent) -> None:
        """Handle metrics update event."""
        if not hasattr(self.gui, '_developer_dashboard'):
            return
        
        if self.gui._current_mode == 'developer':
            dashboard = self.gui._developer_dashboard
            if dashboard:
                data = event.data
                # Update relevant dashboard components
                if hasattr(dashboard, 'update_metrics'):
                    dashboard.update_metrics(data)
    
    def handle_system_alert(self, event: GUIEvent) -> None:
        """Handle system alert event."""
        data = event.data
        severity = data.get('severity', 'info')
        message = data.get('message', '')
        
        # Update status bar
        if hasattr(self.gui, '_set_status'):
            icon = {'critical': '🔴', 'warning': '⚠️', 'info': 'ℹ️'}.get(severity, 'ℹ️')
            self.gui._set_status(f"{icon} {message}", severity)
    
    def handle_resilience_event(self, event: GUIEvent) -> None:
        """Handle resilience system events."""
        if self.gui._current_mode != 'developer':
            return
        
        dashboard = getattr(self.gui, '_developer_dashboard', None)
        if dashboard and hasattr(dashboard, '_update_resilience_status'):
            dashboard._update_resilience_status()
    
    def handle_bypass_result(self, event: GUIEvent) -> None:
        """Handle bypass operation results."""
        if self.gui._current_mode != 'developer':
            return
        
        data = event.data
        # Log to debug console if available
        dashboard = getattr(self.gui, '_developer_dashboard', None)
        if dashboard and hasattr(dashboard, 'console_text'):
            result = data.get('success', False)
            technique = data.get('technique', 'unknown')
            status = '✅' if result else '❌'
            timestamp = datetime.now().strftime('%H:%M:%S')
            dashboard.console_text.insert(
                'end', 
                f"[{timestamp}] Bypass {technique}: {status}\n"
            )
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        return self._metrics_cache.copy()
    
    def force_refresh(self) -> None:
        """Force immediate refresh of all subscribed components."""
        # Publish refresh signals
        self.publish(EventType.METRICS_UPDATE, {'refresh': True}, priority=1)
        self.publish(EventType.RESILIENCE_EVENT, {'refresh': True}, priority=1)
    
    def clear_queue(self) -> None:
        """Clear all pending events."""
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except queue.Empty:
                break


# Singleton instance
_event_manager: Optional[RealTimeEventManager] = None


def get_event_manager(gui_instance=None) -> Optional[RealTimeEventManager]:
    """Get or create the global event manager instance."""
    global _event_manager
    if _event_manager is None and gui_instance is not None:
        _event_manager = RealTimeEventManager(gui_instance)
    return _event_manager
