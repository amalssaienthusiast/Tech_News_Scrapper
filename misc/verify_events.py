
import asyncio
import logging
import sys
from datetime import datetime, UTC

# Add project root to path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.events import event_bus
from src.core.protocol import SystemEvent, StatsUpdate, LogMessage, EventType

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verification")

async def test_event_flow():
    print("🚀 Starting EventBus Verification...")
    
    # 1. Start Bus
    await event_bus.start()
    
    # 2. Define Subscriber
    received_events = []
    
    async def on_log_message(event: LogMessage):
        print(f"✅ Received Log: [{event.level}] {event.message}")
        received_events.append(event)
        
    async def on_stats_update(event: StatsUpdate):
        print(f"✅ Received Stats: {event.total_articles} articles found")
        received_events.append(event)

    # 3. Subscribe
    event_bus.subscribe(EventType.LOG_MESSAGE, on_log_message)
    event_bus.subscribe(EventType.STATS_UPDATE, on_stats_update)
    
    # 4. Burn-in Time for async startup
    await asyncio.sleep(0.1)
    
    # 5. Publish Events
    print("Creating test events...")
    log_event = LogMessage(
        message="Test Log Message",
        level="INFO",
        component="TestScript"
    )
    
    stats_event = StatsUpdate(
        total_articles=42,
        total_sources=5,
        total_requests=100
    )
    
    event_bus.publish(log_event)
    event_bus.publish(stats_event)
    
    # 6. Wait for processing
    print("Waiting for processing...")
    await asyncio.sleep(0.5)
    
    # 7. Stop Bus
    await event_bus.stop()
    
    # 8. Verify
    if len(received_events) == 2:
        print("🎉 SUCCESS: All events received correctly!")
    else:
        print(f"❌ FAILURE: Expected 2 events, got {len(received_events)}")

if __name__ == "__main__":
    asyncio.run(test_event_flow())
