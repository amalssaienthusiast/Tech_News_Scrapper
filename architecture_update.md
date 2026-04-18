---
## Updated Discoveries & Deep Dive Analysis

We have continued to trace the critical internal architectures. Below is the updated breakdown.

### 1. Database & Storage Architecture (`src/db_storage/async_database.py`)
- **Dual-Backend Asynchronous Setup**: The system uses a highly optimized dual-backend configuration via `asyncpg` (PostgreSQL) for production and `aiosqlite` (SQLite) for local environments. 
- **AI Intelligence Tables**: The database schema reveals significant focus on advanced data properties. Alongside standard `articles` and `sources` tables, there is a complex `article_intelligence` table storing:
  - `criticality` (1-10 scale)
  - `disruptive` flags
  - `affected_markets` and `affected_companies` (JSON structured arrays)
  - `sentiment` and `key_insights`
- **Full Text Search**: Employs PostgreSQL `GIN` indexing with `tsvector` for ultra-fast, semantic-ready full-text searching natively at the database level.
- **Newsletter State**: Maintains a `newsletters` schema, suggesting an automated pipeline for generating Markdown/HTML digests.

### 2. AI Processing Core (`src/ai_processor.py`)
- **Semantic Search Engine**: Uses **Sentence-BERT** (`all-MiniLM-L6-v2`) via `sentence_transformers` to map articles to tensor embeddings natively on the CPU/CUDA.
- **Abstractive Summarization**: Utilizes **DistilBART** (`sshleifer/distilbart-cnn-6-6`) from HuggingFace `transformers` for generating concise summaries for articles lacking proper descriptions.

### 3. Content Extraction (`src/extraction/llm_content_extractor.py`)
- **LLM-Powered Extraction Fallback**: A custom `LLMContentExtractor` serves as an intelligent fallback. Instead of brittle CSS selectors, it uses a locally quantized LLM (`Llama-3-8B-Q4` via `llama_cpp`) to isolate the true article body from headers, footers, ads, and sidebars by understanding the DOM semantically.

### 4. Deduplication Engine (`src/processing/deduplication.py`)
A three-tier deduplication engine designed to catch cross-syndicated news:
1. **URL Normalization**: Strips tracking parameters (`utm_source`, `fbclid`) and normalizes domains.
2. **Title Fuzzy Matching**: Uses `fuzzywuzzy` string matching to detect slightly altered headlines.
3. **Semantic Content Hashing**: Employs **MinHash Locality-Sensitive Hashing (LSH)** via `datasketch`. It shingles content into n-grams to detect when an article is republished on another domain with minor edits.

### What's Left to complete the Senior Architectural Breakdown
- Determine how these pipelines are distributed (e.g. reviewing `src/queue/celery_app.py` / `tasks.py`).
- Consolidate the findings into a **Step-by-Step Refactoring / Recreation Plan** for the user.

Let me know if you would like me to finish evaluating the Task Queues, or if I should immediately jump to writing out the complete final architecture procedure!