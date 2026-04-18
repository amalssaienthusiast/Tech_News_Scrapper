
import asyncio
import threading
import logging
from typing import Optional
from src.core.events import event_bus

logger = logging.getLogger(__name__)

class AsyncRunner:
    """Runs async tasks in a separate thread."""
    
    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        # Start event bus
        self._loop.create_task(event_bus.start())
        self._loop.run_forever()
    
    def run_async(self, coro, callback=None):
        if self._loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if callback:
            def on_done(f):
                try:
                    result = f.result()
                    callback(result, None)
                except Exception as e:
                    callback(None, e)
            future.add_done_callback(on_done)
    
    def stop(self):
        """Gracefully stop the async event loop and close all sessions."""
        if self._loop and self._loop.is_running():
            def shutdown():
                # Cancel all running tasks
                tasks = [t for t in asyncio.all_tasks(self._loop) if t is not asyncio.current_task()]
                for task in tasks:
                    task.cancel()
                
                async def cleanup():
                    """Await all task cancellations."""
                    # Wait for all tasks to finish cancelling
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        # Log any unexpected errors (not CancelledError)
                        for result in results:
                            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                                logger.debug(f"Task cleanup exception: {result}")
                    
                    # Stop the loop (event bus task already cancelled above)
                    self._loop.stop()
                
                asyncio.create_task(cleanup())
            
            self._loop.call_soon_threadsafe(shutdown)
            
            # Wait for thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
