# Resilience System Runbook

## Overview

The Resilience System provides permanent solutions for common issues:
- **Package deprecations** (feedparser, duckduckgo_search)
- **RSS feed format changes** (date normalization)
- **Source failures and blocking**
- **Warning spam reduction**

---

## Quick Start

### 1. Deploy the System
```bash
python deploy_resilience.py
```

### 2. Check System Health
```bash
python -c "
from src.resilience import resilience
import asyncio
asyncio.run(resilience.initialize())
print(resilience.get_system_health())
"
```

### 3. Generate Migration Report
```bash
python -c "
from src.resilience import resilience
print(resilience.generate_migration_plan())
"
```

---

## Common Operations

### Check Package Health
```python
from src.compatibility.package_shim import package_shim
health = package_shim.check_package_health()
print(health)
```

### Auto-fix Issues
```python
from src.resilience import resilience
import asyncio

async def fix_all():
    await resilience.initialize()
    result = await resilience.auto_fix_all()
    print(result)

asyncio.run(fix_all())
```

### Use RSS Compatibility Engine
```python
from src.compatibility.rss_adapter import RSSCompatibilityEngine

engine = RSSCompatibilityEngine()
result = engine.parse_feed("https://example.com/feed.xml")

for entry in result.entries:
    print(entry['title'], entry['published'])
```

---

## Troubleshooting

### Issue: RSS Warnings Persist
```python
from src.compatibility.rss_adapter import RSSCompatibilityEngine
engine = RSSCompatibilityEngine()  # Force re-initialize
```

### Issue: DuckDuckGo Warnings
```python
from src.compatibility.package_shim import safe_import
ddgs = safe_import('duckduckgo_search')  # Uses compatibility wrapper
```

### Issue: Source Returning Zero Results
Check source health:
```python
from src.resilience import resilience
health = resilience.source_health.get_detailed_report()
print(health)
```

---

## Maintenance

| Frequency | Task |
|-----------|------|
| Daily | Check resilience logs: `tail -f logs/resilience.log` |
| Weekly | Review migration recommendations |
| Monthly | Update package compatibility registry |

---

## Configuration

Edit `config/resilience.yaml`:
- `resilience.auto_fix`: Enable/disable auto-fixing
- `resilience.monitoring.health_check_interval`: Health check frequency
- `resilience.sources.degraded_threshold`: Success rate threshold

---

## Key Files

| File | Purpose |
|------|---------|
| `src/compatibility/rss_adapter.py` | RSS/feedparser compatibility |
| `src/compatibility/package_shim.py` | Package rename handling |
| `src/resilience/auto_fixer.py` | Self-healing engine |
| `src/resilience/__init__.py` | Main ResilienceSystem |
| `config/resilience.yaml` | Configuration |
