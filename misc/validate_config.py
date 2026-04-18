
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

def validate_config():
    print("🔍 Validating Configuration...\n")
    
    # Check .env existence
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        print(f"✅ Found .env file at {env_path}")
    else:
        print(f"❌ .env file missing at {env_path}")
        print("   -> Run 'touch .env' and add configuration.")
        return

    # Check API Keys
    google_key = os.getenv("GOOGLE_API_KEY")
    google_cx = os.getenv("GOOGLE_CSE_ID")
    bing_key = os.getenv("BING_API_KEY")
    
    print("\nAPI Key Status:")
    
    # Google
    if google_key and google_cx:
        print(f"✅ Google Custom Search API: Configured")
        print(f"   - Key: {google_key[:5]}...{google_key[-3:]}")
        print(f"   - CX:  {google_cx[:5]}...")
    else:
        print(f"⚠️  Google Custom Search API: Not Configured")
        if not google_key: print("   - Missing GOOGLE_API_KEY")
        if not google_cx: print("   - Missing GOOGLE_CSE_ID")

    # Bing
    if bing_key:
        print(f"✅ Bing Search API: Configured")
        print(f"   - Key: {bing_key[:5]}...{bing_key[-3:]}")
    else:
        print(f"⚠️  Bing Search API: Not Configured")
    
    # Summary
    print("\nDiscovery Mode:")
    if (google_key and google_cx) or bing_key:
        print("🚀 API MOde: ACTIVE")
        print("   Using official APIs for fast, reliable source discovery.")
    else:
        print("🐢 Scraping Mode: ACTIVE (Fallback)")
        print("   Using web scraping for source discovery.")
        print("   NOTE: This is slower and less reliable than APIs.")
        print("   ACTION: Edit .env to add API keys for better performance.")

if __name__ == "__main__":
    validate_config()
