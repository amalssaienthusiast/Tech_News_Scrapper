
import asyncio
import json
import logging
import signal
import sys
import uvicorn
from multiprocessing import Process

from config.config import load_config
from src.scrapers.factory import ScraperFactory
from src.scheduler.task_scheduler import ScraperScheduler
from src.feed_generator.live_feed import LiveFeedGenerator
from src.db_storage.db_handler import DatabaseHandler

class RealTimeNewsAggregator:
    """Main application class"""
    
    def __init__(self):
        self.config = load_config()
        self.scrapers = []
        self.scheduler = None
        self.feed_generator = LiveFeedGenerator()
        self.db_handler = DatabaseHandler()
        self.logger = logging.getLogger('aggregator')
        
    async def initialize(self):
        """Initialize the aggregator"""
        self.logger.info("Initializing Real-Time News Aggregator")
        
        # Load scrapers from config
        self.scrapers = await self._create_scrapers()
        
        # Initialize scheduler
        max_concurrent = self.config['general']['max_concurrent_scrapers']
        self.scheduler = ScraperScheduler(self.scrapers, max_concurrent)
        
        # Initialize database
        await self.db_handler.initialize()
        
        self.logger.info(f"Initialized {len(self.scrapers)} scrapers")
    
    async def _create_scrapers(self) -> list:
        """Create scraper instances from config"""
        scrapers = []
        factory = ScraperFactory()
        
        for source_config in self.config['sources']:
            if source_config.get('enabled', True):
                scraper = factory.create_scraper(source_config)
                if scraper:
                    scrapers.append(scraper)
        
        return scrapers
    
    async def run_continuous(self):
        """Run aggregator continuously"""
        self.logger.info("Starting continuous aggregation")
        
        # Start scheduler
        scheduler_task = asyncio.create_task(self.scheduler.start())
        
        # Run feed generation every 30 seconds
        while True:
            try:
                # Get latest articles from all scrapers (from scheduler or direct request?)
                # Scheduler runs them in background and stores results? 
                # Actually base `run_once` collects results. 
                # The scheduler runs tasks periodically, but where do results go?
                # In current implementation `task_scheduler._run_scraper_task` returns articles,
                # but `start` ignores return values.
                # We need to bridge this. The scheduler should probably trigger a callback or we manually run once here.
                # For this implementation, let's keep it simple: `run_once` gathers everything manually in this loop
                # OR refine scheduler to store results.
                # Let's use `run_once` here for periodic aggregation instead of purely background scheduling for simplicity and control.
                
                # If using scheduler.start(), we need a way to collect results.
                # Let's skip scheduler.start() and control loop manually or trust run_once.
                
                articles_by_source = await self.scheduler.run_once()
                
                # Generate live feed
                all_articles = []
                for source_articles in articles_by_source.values():
                     all_articles.extend(source_articles)
                
                if all_articles:
                    feed = await self.feed_generator.generate_feed([all_articles])
                    
                    # Store in database
                    await self.db_handler.store_feed(feed)
                    
                    # Log statistics
                    self._log_statistics(feed, articles_by_source)
                
                # Wait before next cycle
                # This effectively overrides per-scraper refresh rate in config for a global cycle 
                # but simplifies data collection.
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                 break
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(60)
        
        # Cleanup
        await self.shutdown()
    
    async def _log_statistics(self, feed: dict, articles_by_source: dict):
        """Log scraping statistics"""
        total_articles = sum(len(articles) for articles in articles_by_source.values())
        unique_articles = len(feed['articles'])
        
        self.logger.info(
            f"Statistics - Total: {total_articles}, "
            f"Unique: {unique_articles}, "
            f"Sources: {len(articles_by_source)}"
        )
    
    async def shutdown(self):
        """Shutdown gracefully"""
        self.logger.info("Shutting down...")
        
        if self.scheduler:
            self.scheduler.stop()
        
        # Close all scraper sessions
        for scraper in self.scrapers:
            await scraper.close()
        
        # Close database
        await self.db_handler.close()
        
        self.logger.info("Shutdown complete")

def run_api():
    """Run FastAPI server"""
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=False)

async def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('news_aggregator.log'),
            logging.StreamHandler()
        ]
    )
    
    # Start API in separate process (or task if using uvicorn programmatically async, but process is safer for blocking)
    api_process = Process(target=run_api)
    api_process.start()
    
    aggregator = RealTimeNewsAggregator()
    
    # Setup signal handlers
    loop = asyncio.get_running_loop()
    
    def handle_signal():
        asyncio.create_task(aggregator.shutdown())
        api_process.terminate()
        
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    
    try:
        await aggregator.initialize()
        await aggregator.run_continuous()
    except Exception as e:
        aggregator.logger.error(f"Fatal error: {str(e)}")
        await aggregator.shutdown()
        api_process.terminate()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass