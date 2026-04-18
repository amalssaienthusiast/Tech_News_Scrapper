
import asyncio
import logging
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.engine.enhanced_feeder import EnhancedNewsPipeline
from src.resilience import resilience

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PipelineVerifier")

async def verify_pipelines():
    print("\n" + "="*50)
    print("🧪 PIPELINE VERIFICATION & VALIDATION")
    print("="*50 + "\n")

    # 1. VERIFY RESILIENCE
    print("🔍 [1/3] Verifying Resilience System...")
    try:
        await resilience.initialize()
        health = resilience.get_system_health()
        print(f"✅ Resilience initialized successfully")
        print(f"   - Monitoring: {'Active' if health['initialized'] else 'Inactive'}")
        print(f"   - Sources Monitored: {len(health['sources'].get('sources', {}))}")
    except Exception as e:
        print(f"❌ Resilience verification failed: {e}")
        return

    # 2. VERIFY PIPELINE ORCHESTRATION
    print("\n🔍 [2/3] Verifying Enhanced Pipeline Orchestration...")
    pipeline = None
    try:
        pipeline = EnhancedNewsPipeline(
            enable_discovery=True,
            max_articles=10  # Low count for quick verification
        )
        await pipeline.start()
        print("✅ Pipeline started successfully")
        
        # Check components
        components = {
            "RSS Feeder": pipeline._feeder is not None,
            "Discovery Aggregator": pipeline._aggregator is not None,
            "Dedup Engine": pipeline._dedup_engine is not None
        }
        
        for name, active in components.items():
            print(f"   - {name}: {'✅ Active' if active else '❌ Inactive'}")
            
    except Exception as e:
        print(f"❌ Pipeline initialization failed: {e}")
        return

    # 3. LIVE DATA VALIDATION (Dry Run)
    print("\n🔍 [3/3] Validating Live Data Fetch (10 articles max)...")
    try:
        # Mocking or limiting actual requests would be ideal, but here we run a real (limited) fetch
        print("   - Triggering unified fetch (RSS + APIs + Scraper)...")
        
        status_log = []
        pipeline.add_status_callback(lambda c, s: status_log.append(f"[{c}] {s}"))
        
        articles = await pipeline.fetch_unified_live_feed(count=10)
        
        print(f"✅ Fetch completed. Found {len(articles)} articles.")
        
        # Verify diversity
        sources = set(a.source for a in articles)
        print(f"   - Source Diversity: {len(sources)} unique sources")
        print(f"   - Sample Sources: {', '.join(list(sources)[:5])}")
        
    except Exception as e:
        print(f"❌ Live fetch validation failed: {e}")
    finally:
        if pipeline:
            await pipeline.stop()
            print("\n✅ Pipeline resources cleaned up")

    print("\n" + "="*50)
    print("✨ VERIFICATION COMPLETE")
    print("="*50 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(verify_pipelines())
    except KeyboardInterrupt:
        pass
