
import asyncio
import aioschedule
from datetime import datetime
import logging
from typing import Dict, List, Any
import time

class ScraperScheduler:
    """Scheduler for running scrapers at intervals"""
    
    def __init__(self, scrapers: List, max_concurrent: int = 10):
        self.scrapers = scrapers
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger('scheduler')
        self.running = False
        self.tasks = []
        
    async def start(self):
        """Start the scheduler"""
        self.running = True
        
        # Schedule each scraper based on its refresh rate
        for scraper in self.scrapers:
            refresh_rate = getattr(scraper, 'refresh_rate', 300)
            
            # Create a localized function to capture scraper instance
            def job_factory(s=scraper):
                return asyncio.create_task(self._run_scraper_task(s))
                
            aioschedule.every(refresh_rate).seconds.do(job_factory)
        
        self.logger.info(f"Scheduled {len(self.scrapers)} scrapers")
        
        # Run scheduler loop
        while self.running:
            await aioschedule.run_pending()
            await asyncio.sleep(1)
    
    async def _run_scraper_task(self, scraper) -> List[Dict]:
        """Run a scraper with concurrency control"""
        async with self.semaphore:
            self.logger.debug(f"Starting scrape for {scraper.name}")
            try:
                articles = await scraper.scrape()
                return articles
            except Exception as e:
                self.logger.error(f"Error in scraper {scraper.name}: {str(e)}")
                return []
    
    async def run_once(self) -> Dict[str, List[Dict]]:
        """Run all scrapers once immediately"""
        tasks = []
        for scraper in self.scrapers:
            tasks.append(self._run_scraper_task(scraper))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile results
        compiled = {}
        for scraper, result in zip(self.scrapers, results):
            if isinstance(result, Exception):
                self.logger.error(f"Scraper {scraper.name} failed: {str(result)}")
                compiled[scraper.name] = []
            else:
                compiled[scraper.name] = result
        
        return compiled
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        # potentially wait for tasks?
