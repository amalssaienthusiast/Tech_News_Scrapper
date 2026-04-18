# Tech News Scraper - Hybrid Rust + Python Migration Plan

## Overview

This document outlines the migration strategy to create a high-performance hybrid architecture combining:
- **Rust** for performance-critical modules (web scraping, data processing, bypass engines)
- **Python** for business logic, AI/ML, and GUI (modern framework replacement)

## Project Structure

```
tech_news_scraper/
├── rust/                           # NEW: Rust native modules
│   ├── Cargo.toml
│   ├── Cargo.lock
│   ├── src/
│   │   ├── lib.rs                   # PyO3 bindings entry point
│   │   ├── scraper/                 # High-performance HTTP scraper
│   │   │   ├── mod.rs
│   │   │   ├── client.rs            # reqwest-based HTTP client
│   │   │   ├── parser.rs            # HTML parsing utilities
│   │   │   └── rate_limiter.rs     # Token bucket rate limiting
│   │   ├── bypass/                  # Anti-detection engines
│   │   │   ├── mod.rs
│   │   │   ├── fingerprint.rs        # Browser fingerprint generation
│   │   │   ├── headers.rs           # Smart header rotation
│   │   │   └── stealth.rs          # Stealth browser simulation
│   │   ├── processor/               # Fast data processing
│   │   │   ├── mod.rs
│   │   │   ├── text.rs             # Text cleaning and normalization
│   │   │   ├── dedup.rs            # Content deduplication
│   │   │   └── encoding.rs         # Brotli/gzip decompression
│   │   └── utils/                  # Shared utilities
│   │       ├── mod.rs
│   │       ├── cache.rs             # LRU cache implementation
│   │       └── async.rs             # Tokio async utilities
│   ├── tests/                      # Rust integration tests
│   │   └── integration_test.rs
│   └── build.rs                    # Build script
│
├── src/                            # EXISTING: Python backend (keep 80%)
│   ├── engine/                      # Keep: Pipeline orchestration
│   ├── core/                       # Keep: Types, events
│   ├── intelligence/                # Keep: AI/ML modules
│   ├── database/                   # Keep: SQLite wrapper
│   └── ...                        # Other existing modules
│
├── gui/                            # MODERNIZE: Replace with PyQt6
│   ├── modern_ui/                  # NEW: PyQt6-based UI
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── widgets/
│   │   └── dialogs/
│   └── legacy/                     # Keep old Tkinter for reference (temporary)
│
├── tests/                          # NEW: Cross-language tests
│   ├── test_rust_integration.py     # Test Rust-Python bridge
│   └── performance_benchmarks.py    # Compare Python vs Rust
│
├── build_rust.py                   # NEW: Build script for Rust extension
├── pyproject.toml                  # UPDATED: Include maturin config
└── requirements.txt                # UPDATED: Add maturin
```

## Migration Phases

### Phase 1: Infrastructure Setup (Week 1-2)

**Goals:**
- Set up Rust project with PyO3
- Create build pipeline
- Establish Python-Rust communication

**Tasks:**
- [ ] Initialize Cargo project with PyO3
- [ ] Set up maturin for Python bindings
- [ ] Create build script (build_rust.py)
- [ ] Set up cross-language testing
- [ ] Update CI/CD pipeline

**Deliverables:**
- `rust/` directory with basic PyO3 setup
- Build script that compiles Rust extension
- Test suite verifying Python-Rust communication

### Phase 2: Core Rust Modules (Week 3-6)

#### Module 2.1: HTTP Scraper Engine (Week 3-4)

**Purpose:** Replace Python `requests` library with high-performance `reqwest`

**Rust Implementation:**
```rust
// rust/src/scraper/client.rs
use pyo3::prelude::*;
use reqwest::Client;
use tokio::runtime::Runtime;

#[pyclass]
pub struct RustScraper {
    client: Client,
    runtime: Runtime,
}

#[pymethods]
impl RustScraper {
    #[new]
    fn new() -> PyResult<Self> {
        let client = Client::builder()
            .user_agent("Mozilla/5.0...")
            .build()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        let runtime = Runtime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        Ok(RustScraper { client, runtime })
    }

    fn fetch_url(&self, url: &str) -> PyResult<String> {
        let future = self.client.get(url).send();
        let response = self.runtime.block_on(future)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        let text = response.text();
        let content = self.runtime.block_on(text)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        Ok(content)
    }
}
```

**Python Integration:**
```python
# src/engine/rust_scraper.py
from rust.technews import RustScraper

class HybridScraper:
    """Hybrid scraper using Rust for HTTP, Python for logic."""
    
    def __init__(self):
        self.rust_client = RustScraper()
        
    async def fetch(self, url: str):
        # Use Rust for HTTP (fast)
        content = self.rust_client.fetch_url(url)
        
        # Use Python for parsing (flexible with AI/ML)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'lxml')
        return soup
```

**Performance Target:**
- 3-5x faster HTTP requests vs Python requests
- 50% lower memory usage
- Concurrent connection pooling (up to 100 connections)

---

#### Module 2.2: Bypass Engine (Week 5)

**Purpose:** High-performance anti-detection techniques

**Rust Implementation:**
```rust
// rust/src/bypass/fingerprint.rs
use pyo3::prelude::*;
use rand::Rng;

#[pyfunction]
fn generate_fingerprint(profile: &str) -> PyResult<String> {
    let user_agents = vec![
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    ];
    
    let mut rng = rand::thread_rng();
    let ua = user_agents[rng.gen_range(0..user_agents.len())];
    
    Ok(ua.to_string())
}
```

**Features:**
- Browser fingerprint generation (1000+ signatures)
- Header rotation with smart persistence
- Cookie jar management (in-memory)
- Request delay simulation (human-like)

---

#### Module 2.3: Data Processor (Week 6)

**Purpose:** Fast text processing and deduplication

**Rust Implementation:**
```rust
// rust/src/processor/dedup.rs
use pyo3::prelude::*;
use std::collections::HashSet;

#[pyclass]
pub struct Deduplicator {
    seen: HashSet<String>,
}

#[pymethods]
impl Deduplicator {
    #[new]
    fn new() -> Self {
        Deduplicator {
            seen: HashSet::new(),
        }
    }
    
    fn is_duplicate(&mut self, url: &str) -> bool {
        if self.seen.contains(url) {
            true
        } else {
            self.seen.insert(url.to_string());
            false
        }
    }
}
```

**Performance Target:**
- 10x faster deduplication vs Python sets
- MinHash-based similarity detection
- 100,000+ URL checks per second

---

### Phase 3: Python Layer Integration (Week 7-10)

#### 3.1 Update Existing Python Modules

**Changes to `src/engine/`:**
```python
# src/engine/enhanced_feeder.py (MODIFIED)
from rust.technews import RustScraper, Deduplicator

class EnhancedNewsPipeline:
    def __init__(self):
        # Use Rust for performance-critical operations
        self.rust_scraper = RustScraper()
        self.deduplicator = Deduplicator()
        
        # Keep Python for business logic
        self.analyzer = None  # AI sentiment analyzer
        self.db = get_database()
    
    async def fetch_article(self, url: str) -> Optional[Article]:
        # Check duplicates with Rust (fast)
        if self.deduplicator.is_duplicate(url):
            return None
        
        # Fetch with Rust (fast HTTP)
        content = self.rust_scraper.fetch_url(url)
        
        # Parse with Python (AI/ML integration)
        article = await self.parse_article(url, content)
        return article
```

#### 3.2 GUI Modernization (PyQt6)

**Replace Tkinter with PyQt6:**
```python
# gui/modern_ui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal
from rust.technews import RustScraper

class ModernMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rust_scraper = RustScraper()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Tech News Scraper v8.0 (Hybrid)")
        self.resize(1400, 900)
        
        # Modern widgets with better performance
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Article list with Rust-backed fetching
        self.article_list = ArticleListWidget()
        layout.addWidget(self.article_list)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
```

**Benefits:**
- Native look and feel
- Hardware-accelerated rendering
- Better multi-threading support
- Custom widgets and animations

---

### Phase 4: Testing & Optimization (Week 11-12)

#### 4.1 Performance Benchmarks

**Test Script:**
```python
# tests/performance_benchmarks.py
import time
from rust.technews import RustScraper
import requests

def benchmark_scraping():
    urls = ["https://example.com/page1", ...] * 100
    
    # Python requests
    start = time.time()
    for url in urls:
        requests.get(url, timeout=5)
    python_time = time.time() - start
    
    # Rust reqwest
    rust_scraper = RustScraper()
    start = time.time()
    for url in urls:
        rust_scraper.fetch_url(url)
    rust_time = time.time() - start
    
    print(f"Python: {python_time:.2f}s, Rust: {rust_time:.2f}s")
    print(f"Speedup: {python_time / rust_time:.2f}x")

if __name__ == "__main__":
    benchmark_scraping()
```

**Target Metrics:**
| Operation | Python (Current) | Rust (Target) | Improvement |
|-----------|------------------|----------------|-------------|
| HTTP GET 100 URLs | 45s | 12s | 3.75x |
| Deduplicate 100K URLs | 8s | 0.8s | 10x |
| Parse HTML | 5s | 1.5s | 3.3x |
| Total pipeline time | 60s | 18s | 3.3x |

---

### Phase 5: Deployment & Documentation (Week 12+)

**Deliverables:**
- [ ] Updated README with build instructions
- [ ] Migration guide for developers
- [ ] CI/CD pipeline updates
- [ ] Performance comparison report
- [ ] API documentation (Sphinx + Rust docs)

---

## Build System

### Build Script (build_rust.py)

```python
#!/usr/bin/env python3
"""
Build script for Rust-Python hybrid project.
Compiles Rust extension with maturin.
"""

import subprocess
import sys
from pathlib import Path

def build_rust():
    """Build Rust extension using maturin."""
    print("🦀 Building Rust extension...")
    
    # Check if maturin is installed
    try:
        subprocess.run(["maturin", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing maturin...")
        subprocess.run([sys.executable, "-m", "pip", "install", "maturin"], check=True)
    
    # Build in development mode
    print("Building development extension...")
    subprocess.run(
        ["maturin", "develop", "--release"],
        cwd=Path(__file__).parent / "rust",
        check=True
    )
    
    print("✅ Rust extension built successfully!")

def build_release():
    """Build for production."""
    print("🦀 Building release wheel...")
    subprocess.run(
        ["maturin", "build", "--release"],
        cwd=Path(__file__).parent / "rust",
        check=True
    )
    print("✅ Release wheel built!")

if __name__ == "__main__":
    if "--release" in sys.argv:
        build_release()
    else:
        build_rust()
```

### Cargo.toml

```toml
[package]
name = "technews-rust"
version = "0.1.0"
edition = "2021"

[lib]
name = "technews"
crate-type = ["cdylib"]

[dependencies]
# PyO3 for Python bindings
pyo3 = { version = "0.20", features = ["extension-module"] }

# Async runtime
tokio = { version = "1.35", features = ["full"] }

# HTTP client
reqwest = { version = "0.11", features = ["json", "cookies", "brotli"] }

# Parsing
scraper = "0.18"
select = "0.6"

# Utils
rand = "0.8"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true
```

---

## Integration Points

### 1. Article Fetch Pipeline

```
┌─────────────┐
│  Python     │
│  Orchestr.  │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────┐
│  Rust Scraper Module       │
│  - HTTP requests (fast)    │
│  - Connection pooling      │
│  - Bypass techniques       │
└──────┬────────────────────┘
       │ HTML content
       ↓
┌─────────────────────────────┐
│  Python Parsing Layer      │
│  - BeautifulSoup          │
│  - AI/ML analysis        │
│  - Content extraction     │
└─────────────────────────────┘
```

### 2. Deduplication Flow

```
┌─────────────┐
│  New Article│
│  URL        │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────┐
│  Rust Deduplicator        │
│  - Hash-based lookup      │
│  - MinHash similarity     │
│  - LRU cache             │
└──────┬────────────────────┘
       │
       ↓
    New? ──Yes──► Process
       │
       No
       ↓
    Skip
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| PyO3 compilation issues | Medium | High | Test on Windows/Mac/Linux; provide pre-built wheels |
| Performance not as expected | Low | Medium | Benchmark early; fallback to Python if needed |
| Integration complexity | Medium | Medium | Start with isolated modules; gradual migration |
| Maintenance burden | Medium | High | Document Rust module boundaries; keep Rust simple |

---

## Success Criteria

- [ ] 3x+ improvement in article fetching speed
- [ ] 50% reduction in memory usage
- [ ] All existing Python tests pass
- [ ] New Rust modules have 90%+ test coverage
- [ ] GUI responsive with 10,000+ articles loaded
- [ ] Build time < 2 minutes on developer machines

---

## Next Steps

1. **Run this command to start:**
   ```bash
   cd /Users/sci_coderamalamicia/PROJECTS/tech_news_scraper
   python build_rust.py
   ```

2. **Review the initial Rust modules** (will be created next)

3. **Test the Python-Rust bridge** with integration tests

4. **Iterate on performance** based on benchmarks

---

**Document Version:** 1.0  
**Last Updated:** January 2026  
**Status:** Planning Phase
