
import asyncio
import os
import sys
import logging

# Add project root to path
sys.path.append(os.getcwd())

from src.scrapers.factory import ScraperFactory
from src.feed_generator.live_feed import LiveFeedGenerator
from src.db_storage.db_handler import DatabaseHandler
from config.config import load_config

async def verify_system():
    print("Verifying Real-Time Aggregator System...")
    
    # 1. Config Loading
    config = load_config()
    print(f"✅ Config loaded. Found {len(config.get('sources', []))} sources.")
    
    # 2. Database Init
    db_handler = DatabaseHandler("sqlite+aiosqlite:///test_live_feed.db")
    await db_handler.initialize()
    print("✅ Database initialized.")
    
    # 3. Scraper Factory
    factory = ScraperFactory()
    scrapers = []
    for source in config['sources']:
        if source.get('enabled'):
            scraper = factory.create_scraper(source)
            if scraper:
                scrapers.append(scraper)
    print(f"✅ Scrapers created: {[s.name for s in scrapers]}")
    
    # 4. Run Scrapers (Limit to 1 concurrent for test stability)
    print("running scrapers...")
    articles_list = []
    for scraper in scrapers:
        try:
            print(f"  Scraping {scraper.name}...")
            articles = await scraper.scrape()
            print(f"  -> Found {len(articles)} articles.")
            articles_list.append(articles)
        except Exception as e:
            print(f"  ❌ Error scraping {scraper.name}: {e}")
            
    # 5. Feed Generation
    feed_gen = LiveFeedGenerator()
    feed = await feed_gen.generate_feed(articles_list)
    print(f"✅ Feed Generated. Total unique articles: {feed['total_articles']}")
    
    # 6. Store in DB
    await db_handler.store_feed(feed)
    print("✅ Feed stored in DB.")
    
    # 7. Retrieve from DB
    stored = await db_handler.get_latest_articles(limit=5)
    print(f"✅ Retrieved {len(stored)} articles from DB.")
    if stored:
        print(f"   Sample: {stored[0]['title']}")
        
    await db_handler.close()
    for scraper in scrapers:
        await scraper.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR) # Quiet logs
    asyncio.run(verify_system())
