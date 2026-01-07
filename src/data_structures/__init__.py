"""
Custom data structures module.

Provides high-performance data structures for the scraper:
- Trie: O(k) keyword matching
- BloomFilter: Probabilistic URL deduplication
- LRUCache: Response caching with TTL
- PriorityQueue: Source ranking
"""

from src.data_structures.trie import (
    Trie,
    TrieNode,
    TechKeywordMatcher,
)

from src.data_structures.bloom_filter import (
    BloomFilter,
    URLDeduplicator,
)

from src.data_structures.lru_cache import (
    LRUCache,
    CacheEntry,
    HTTPResponseCache,
)

from src.data_structures.priority_queue import (
    PriorityQueue,
    PriorityItem,
    SourcePriorityQueue,
    TaskScheduler,
)

__all__ = [
    # Trie
    "Trie",
    "TrieNode",
    "TechKeywordMatcher",
    # Bloom Filter
    "BloomFilter",
    "URLDeduplicator",
    # LRU Cache
    "LRUCache",
    "CacheEntry",
    "HTTPResponseCache",
    # Priority Queue
    "PriorityQueue",
    "PriorityItem",
    "SourcePriorityQueue",
    "TaskScheduler",
]
