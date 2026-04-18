"""
Unit tests for RealTimeLogHandler and EventBus integration.

These tests validate:
1. RealTimeLogHandler correctly publishes LogMessage events
2. EventBus.publish() receives correctly formatted events
3. Callback type signatures are enforced
"""

import logging
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.protocol import LogMessage, EventType
from src.core.events import EventBus


class MockEventBus:
    """Mock EventBus for testing publish calls."""
    
    def __init__(self):
        self.published_events = []
        self._running = True
    
    def publish(self, event):
        """Capture published events for assertion."""
        self.published_events = self.published_events or []
        self.published_events.append(event)
    
    def get_last_event(self):
        return self.published_events[-1] if self.published_events else None
    
    def clear(self):
        self.published_events = []


class TestLogMessage(unittest.TestCase):
    """Tests for LogMessage dataclass."""
    
    def test_log_message_has_correct_fields(self):
        """Verify LogMessage uses 'component' not 'source'."""
        msg = LogMessage(
            level="INFO",
            message="Test message",
            component="TestComponent"
        )
        self.assertEqual(msg.component, "TestComponent")
        self.assertEqual(msg.level, "INFO")
        self.assertEqual(msg.message, "Test message")
        self.assertEqual(msg.event_type, EventType.LOG_MESSAGE)
    
    def test_log_message_rejects_source_kwarg(self):
        """Ensure 'source' keyword raises TypeError (security test)."""
        with self.assertRaises(TypeError):
            LogMessage(
                level="INFO",
                message="Test",
                source="BadField"  # This should fail
            )


class TestRealTimeLogHandler(unittest.TestCase):
    """Tests for RealTimeLogHandler in gui/app.py."""
    
    def setUp(self):
        """Set up mock EventBus."""
        self.mock_bus = MockEventBus()
        self.patcher = patch('gui.app.event_bus', self.mock_bus)
        self.patcher.start()
    
    def tearDown(self):
        """Clean up patches."""
        self.patcher.stop()
    
    def test_handler_publishes_single_event_argument(self):
        """Verify handler adds LogMessage to the thread-safe buffer."""
        # Import after patching
        from gui.app import RealTimeLogHandler, _log_buffer, _log_buffer_lock
        
        # Clear the global buffer before test
        with _log_buffer_lock:
            _log_buffer.clear()
        
        handler = RealTimeLogHandler()
        
        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test log message",
            args=(),
            exc_info=None
        )
        
        # Emit the record
        handler.emit(record)
        
        # Verify LogMessage was added to _log_buffer
        with _log_buffer_lock:
            self.assertGreater(len(_log_buffer), 0, "Buffer should have at least one message")
            event = _log_buffer[-1]
        
        self.assertIsInstance(event, LogMessage)
        self.assertEqual(event.message, "Test log message")
        self.assertEqual(event.component, "test.logger")
        self.assertEqual(event.level, "INFO")


class TestEventBusPublish(unittest.TestCase):
    """Tests for EventBus.publish() signature."""
    
    def test_publish_accepts_single_event(self):
        """Verify publish() takes only 1 positional argument."""
        bus = EventBus()
        msg = LogMessage(level="INFO", message="Test", component="Test")
        
        # This should work (1 argument)
        try:
            bus.publish(msg)
        except TypeError:
            self.fail("publish() should accept a single event argument")
    
    def test_publish_rejects_two_arguments(self):
        """Verify publish() rejects 2 positional arguments."""
        bus = EventBus()
        msg = LogMessage(level="INFO", message="Test", component="Test")
        
        # This should fail (2 arguments)
        with self.assertRaises(TypeError):
            bus.publish(EventType.LOG_MESSAGE, msg)


class TestCallbackTypeHints(unittest.TestCase):
    """Tests for callback type hints in orchestrator."""
    
    def test_article_callback_signature(self):
        """Verify new article callback accepts Article type."""
        from src.core.types import Article
        from src.engine.orchestrator import TechNewsOrchestrator
        
        with patch("src.engine.orchestrator.Database"):
            orchestrator = TechNewsOrchestrator()
        
        received_articles = []
        
        def callback(article: Article) -> None:
            received_articles.append(article)
        
        # Register callback - should not raise
        orchestrator.register_new_article_callback(callback)
        self.assertEqual(orchestrator._new_article_callback, callback)


if __name__ == '__main__':
    unittest.main()
