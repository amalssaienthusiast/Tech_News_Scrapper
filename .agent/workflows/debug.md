---
description: Debug common issues in the tech news scraper
---

## Debugging Guide

### Check Import Issues

1. Test module imports:
```bash
python3 -c "from src.bypass import AntiBotBypass; print('OK')"
python3 -c "from src.scraper import TechNewsScraper; print('OK')"
```

### Run Specific Failing Tests

// turbo
2. Run bypass tests in verbose mode:
```bash
python3 -m pytest tests/test_bypass.py -v --tb=long
```

### Check Database

3. Verify database connectivity:
```bash
python3 -c "from src.database import Database; db=Database(); print(f'Articles: {db.get_article_count()}')"
```

### Common Issues

- **ImportError on ProtectionType**: Check `src/bypass/__init__.py` exports
- **max_retries TypeError**: Update `AntiBotBypass.__init__` signature
- **detect_protection missing**: Add method to `AntiBotBypass` class
