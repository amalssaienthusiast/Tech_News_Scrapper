---
description: Run the test suite for the tech news scraper
---

## Running Tests

1. Ensure you're in the project root directory

// turbo
2. Run the full test suite:
```bash
python3 -m pytest tests/ -v
```

3. Run specific test files:
```bash
python3 -m pytest tests/test_bypass.py -v
python3 -m pytest tests/test_scraper.py -v
```

4. Run with coverage:
```bash
python3 -m pytest tests/ -v --cov=src --cov-report=term-missing
```
