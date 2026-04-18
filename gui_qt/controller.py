"""
Enhanced Controller for Tech News Scraper - PySide6
Full-featured controller matching tkinter gui/app.py functionality

Features:
- TechNewsOrchestrator integration
- EnhancedNewsPipeline with real-time streaming
- Quantum Temporal Scraper
- Quantum Paywall Bypass
- Global Discovery Manager with geo-rotation
- Reddit Stream Client
- Smart Proxy Router
- Thread-safe operations
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Callable
from functools import partial

from PySide6.QtCore import (
    QObject, Signal, Slot, QTimer, QThread, 
    QRunnable, QThreadPool, QMetaObject, Qt
)

logger = logging.getLogger(__name__)


class AsyncWorker(QRunnable):
    """Worker for running async functions in QThreadPool"""
    
    def __init__(
        self, 
        async_func: Callable,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None
    ):
        super().__init__()
        self.async_func = async_func
        self.callback = callback
        self.error_callback = error_callback
        self.progress_callback = progress_callback
        self.setAutoDelete(True)
    
    def run(self):
        """Run the async function"""
        loop = None
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async function
            result = loop.run_until_complete(self.async_func())
            
            # Call callback with result
            if self.callback:
                self.callback(result)
                
        except Exception as e:
            logger.error(f"Async worker error: {e}", exc_info=True)
            if self.error_callback:
                self.error_callback(str(e))
        finally:
            if loop:
                loop.close()


class StreamWorker(AsyncWorker):
    """Backward-compatible alias for stream background worker."""


class TechNewsController(QObject):
    """Main controller connecting GUI to business logic
    
    Enhanced with Quantum components, Global Discovery, Reddit Streaming,
    and Smart Proxy Router for full feature parity with tkinter version.
    
    Signals:
        articles_loaded(list): Batch of articles loaded
        article_added(dict): Single article added
        stats_updated(dict): Statistics updated
        status_changed(str): Status message changed
        error_occurred(str): Error occurred
        loading_started(): Loading started
        loading_finished(): Loading finished
        quantum_initialized(): Quantum components ready
        discovery_rotated(str): Geo-rotation changed
    """
    
    # Signals
    articles_loaded = Signal(list)
    article_added = Signal(dict)
    stats_updated = Signal(dict)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    loading_started = Signal()
    loading_finished = Signal()
    quantum_initialized = Signal()
    discovery_rotated = Signal(str)
    
    # Refresh interval in seconds
    REFRESH_INTERVAL = 300  # 5 minutes
    MAX_ARTICLES = 500
    
    def __init__(self, window, orchestrator=None, parent=None):
        super().__init__(parent)
        
        self.window = window
        self._orchestrator = orchestrator
        self._pipeline = None
        
        # Advanced components (matching tkinter version)
        self._quantum_scraper = None
        self._quantum_bypass = None
        self._global_discovery = None
        self._reddit_stream = None
        self._smart_proxy = None
        
        # State
        self._current_mode = "user"
        self._fetching = False
        self._articles: List[Dict[str, Any]] = []
        self._displayed_urls: set = set()
        self._history_batches: List[Dict[str, Any]] = []
        self._last_refresh: Optional[datetime] = None
        
        # Thread pool for async operations
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)
        
        # Timers (main thread only)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._on_refresh_timer)
        
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._update_countdown)
        
        # Connect to window signals
        self._connect_window_signals()
        
        logger.info("✅ TechNewsController initialized (Enhanced)")
    
    def _connect_window_signals(self):
        """Connect to window signals"""
        self.window.search_requested.connect(self._on_search)
        self.window.refresh_requested.connect(self._on_refresh)
        self.window.article_clicked.connect(self._on_article_clicked)
        self.window.mode_changed.connect(self._on_mode_changed)
        
        # Dialog signals
        self.window.history_clicked.connect(self._show_history)
        self.window.preferences_clicked.connect(self._show_preferences)
        self.window.developer_clicked.connect(self._show_developer)
        
        # Connect our signals to window
        self.article_added.connect(self.window.add_article)
        self.articles_loaded.connect(self.window.set_articles)
        self.status_changed.connect(self._safe_status_update)
        self.stats_updated.connect(self.window.update_stats)
    
    def _safe_status_update(self, message: str):
        """Thread-safe status update"""
        # Use signal to ensure main thread execution
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.window.set_status(message))
    
    def set_orchestrator(self, orchestrator):
        """Set the orchestrator instance"""
        self._orchestrator = orchestrator
        logger.info("Orchestrator set")
    
    def set_pipeline(self, pipeline):
        """Set the enhanced pipeline instance"""
        self._pipeline = pipeline
        logger.info("Pipeline set")
        
        # Initialize advanced components (like tkinter version does)
        self._init_advanced_components()
    
    def _init_advanced_components(self):
        """Initialize Quantum and advanced components (matching tkinter)"""
        if not self._pipeline:
            return
        
        try:
            # Phase 1: Quantum components
            self._init_quantum_components()
            
            # Phase 2: Global Discovery
            self._init_global_discovery()
            
            # Phase 3: Reddit Streaming
            self._init_reddit_streaming()
            
            # Phase 4: Smart Proxy Router
            self._init_smart_proxy()
            
            self.quantum_initialized.emit()
            self.status_changed.emit("🌌 Quantum & Advanced systems initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize advanced components: {e}")
            self.status_changed.emit("⚠️ Advanced components partially initialized")
    
    def _init_quantum_components(self):
        """Initialize Quantum scraper and bypass"""
        try:
            from src.engine.quantum_scraper import QuantumTemporalScraper
            from src.bypass.quantum_bypass import QuantumPaywallBypass
            from src.database import get_database
            
            # Initialize Quantum bypass
            self._quantum_bypass = QuantumPaywallBypass()
            logger.info("🌌 Quantum Paywall Bypass initialized")
            
            # Initialize Quantum scraper with feeder if available
            if hasattr(self._pipeline, '_feeder'):
                try:
                    db = get_database()
                    self._quantum_scraper = QuantumTemporalScraper(self._pipeline._feeder, db)
                    logger.info("🌌 Quantum Temporal Scraper initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Quantum scraper: {e}")
            else:
                logger.info("Quantum scraper deferred - feeder not ready")
            
            logger.info("🌌 Quantum components initialized and entangled")
            
        except ImportError as e:
            logger.warning(f"Quantum components not available: {e}")
        except Exception as e:
            logger.error(f"Quantum initialization failed: {e}")
    
    def _init_global_discovery(self):
        """Initialize Global Discovery Manager with geo-rotation"""
        try:
            from src.discovery.global_discovery import GlobalDiscoveryManager
            
            self._global_discovery = GlobalDiscoveryManager()
            
            # Start rotation
            if hasattr(self._global_discovery, 'start_rotation'):
                self._global_discovery.start_rotation()
                logger.info("🌍 Global Discovery rotation started")
            
            # Connect rotation signal
            if hasattr(self._global_discovery, 'rotated'):
                self._global_discovery.rotated.connect(self._on_discovery_rotated)
            
            logger.info("🌍 Global Discovery Manager initialized (30s rotation)")
            self.status_changed.emit("🌍 Global Discovery Manager initialized")
            
        except ImportError as e:
            logger.warning(f"Global Discovery not available: {e}")
        except Exception as e:
            logger.error(f"Global Discovery initialization failed: {e}")
    
    def _init_reddit_streaming(self):
        """Initialize Reddit Stream Client"""
        try:
            from src.sources.reddit_stream import RedditStreamClient
            import asyncio
            
            self._reddit_stream = RedditStreamClient()
            
            # Start streaming (async - run in background)
            if hasattr(self._reddit_stream, 'start'):
                async def start_stream():
                    try:
                        await self._reddit_stream.start()
                    except Exception as e:
                        logger.error(f"Reddit stream error: {e}")
                
                # Create task in event loop
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(start_stream())
                except RuntimeError:
                    # No running loop, skip for now
                    pass
                
                logger.info("🔴 Reddit streaming started (async)")
            
            logger.info("🔴 Reddit Stream Client initialized")
            self.status_changed.emit("🔴 Reddit Stream Client initialized")
            
        except ImportError as e:
            logger.warning(f"Reddit Stream not available: {e}")
        except Exception as e:
            logger.error(f"Reddit Stream initialization failed: {e}")
    
    def _init_smart_proxy(self):
        """Initialize Smart Proxy Router"""
        try:
            from src.bypass.smart_proxy_router import SmartProxyRouter
            
            self._smart_proxy = SmartProxyRouter()
            logger.info("🌐 Smart Proxy Router initialized")
            self.status_changed.emit("🌐 Smart Proxy Router initialized")
            
        except ImportError as e:
            logger.warning(f"Smart Proxy not available: {e}")
        except Exception as e:
            logger.error(f"Smart Proxy initialization failed: {e}")
    
    def _on_discovery_rotated(self, country_code: str):
        """Handle geo-rotation"""
        logger.info(f"🌍 Rotating to {country_code}")
        self.discovery_rotated.emit(country_code)
        self.status_changed.emit(f"🌍 Rotating to {country_code}")
    
    # ─────────────────────────────────────────────────────────────────
    # SEARCH
    # ─────────────────────────────────────────────────────────────────
    
    @Slot(str)
    def _on_search(self, query: str):
        """Handle search request"""
        if not query.strip():
            # Empty search - show all articles
            self.window.set_articles(self._articles)
            self.status_changed.emit(f"Showing all {len(self._articles)} articles")
            return
        
        logger.info(f"🔍 Executing Quantum Search Query: {query}")
        self.status_changed.emit(f"🔍 Searching for: {query}...")
        
        # Filter articles locally first
        filtered = self._filter_articles(query)
        
        if filtered:
            self.window.set_articles(filtered)
            self.status_changed.emit(f"✅ Found {len(filtered)} matching articles")
        else:
            # No local matches - search via orchestrator
            self._search_remote(query)
    
    def _filter_articles(self, query: str) -> List[Dict[str, Any]]:
        """Filter articles by query locally with quantum scoring"""
        query_lower = query.lower()
        results = []
        
        for article in self._articles:
            title = article.get('title', '').lower()
            source = article.get('source', '').lower()
            summary = article.get('summary', '').lower()
            
            # Calculate relevance score (quantum-inspired)
            score = 0
            if query_lower in title:
                score += 3
            if query_lower in source:
                score += 2
            if query_lower in summary:
                score += 1
            
            if score > 0:
                article['_search_score'] = score
                results.append(article)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get('_search_score', 0), reverse=True)
        
        return results
    
    def _search_remote(self, query: str):
        """Search via orchestrator"""
        if not self._orchestrator:
            self.status_changed.emit("⚠️ Orchestrator not available")
            return
        
        # Build quantum-enhanced query
        built_query = self._build_quantum_query(query)
        
        async def do_search():
            return await self._orchestrator.search(built_query)
        
        worker = AsyncWorker(
            async_func=do_search,
            callback=self._on_search_results,
            error_callback=self._on_error
        )
        self.thread_pool.start(worker)
    
    def _build_quantum_query(self, query: str) -> str:
        """Build enhanced search query (quantum-style)"""
        # Add tech context if not present
        tech_terms = ['technology', 'tech', 'software', 'AI', 'programming']
        query_lower = query.lower()
        
        if not any(term.lower() in query_lower for term in tech_terms):
            return f"{query} technology"
        
        return query
    
    def _on_search_results(self, results):
        """Handle search results from orchestrator"""
        if results:
            articles = [self._to_dict(a) for a in results]
            self.window.set_articles(articles)
            self.status_changed.emit(f"✅ Found {len(articles)} articles")
        else:
            self.window.set_articles([])
            self.status_changed.emit("No results found")
    
    # ─────────────────────────────────────────────────────────────────
    # LIVE FEED / REFRESH
    # ─────────────────────────────────────────────────────────────────
    
    @Slot()
    def _on_refresh(self):
        """Handle refresh/live feed request with quantum enhancement"""
        if self._fetching:
            logger.info("Already fetching, ignoring refresh request")
            return
        
        self._fetching = True
        self.loading_started.emit()
        self.status_changed.emit("🚀 Engaging Quantum Live Feed...")
        
        # Save current batch to history
        if self._articles:
            self._save_to_history()
        
        # Clear current articles
        self._articles.clear()
        self._displayed_urls.clear()
        
        # Start fetching with quantum status
        self.status_changed.emit("🌌 Engaging Quantum Temporal Scraper...")
        
        if self._pipeline:
            self._start_pipeline_fetch()
        elif self._orchestrator:
            self._start_orchestrator_fetch()
        else:
            self._fetching = False
            self.loading_finished.emit()
            self.error_occurred.emit("No data source available")
    
    def _start_pipeline_fetch(self):
        """Start fetching via enhanced pipeline"""
        logger.info("Starting quantum-enhanced pipeline fetch")
        
        async def do_fetch():
            # Use fetch_unified_live_feed which returns a list of articles
            return await self._pipeline.fetch_unified_live_feed(count=200)
        
        worker = AsyncWorker(
            async_func=do_fetch,
            callback=self._on_batch_results,
            error_callback=self._on_error
        )
        self.thread_pool.start(worker)
    
    def _start_orchestrator_fetch(self):
        """Start fetching via orchestrator"""
        logger.info("Starting orchestrator fetch")
        
        async def do_fetch():
            return await self._orchestrator.fetch_all_sources()
        
        worker = AsyncWorker(
            async_func=do_fetch,
            callback=self._on_batch_results,
            error_callback=self._on_error
        )
        self.thread_pool.start(worker)
    
    def _on_batch_results(self, results):
        """Handle batch results from pipeline/orchestrator"""
        if results:
            articles = [self._to_dict(a) for a in results]
            self._articles = articles
            
            # Update displayed URLs for deduplication
            for article in articles:
                url = article.get('url')
                if url:
                    self._displayed_urls.add(url)
            
            self.articles_loaded.emit(articles)
            self._on_fetch_complete(len(articles))
        else:
            self._on_fetch_complete(0)
    
    def _on_fetch_complete(self, count: int):
        """Handle fetch completion - called from worker thread, use thread-safe updates"""
        self._fetching = False
        self._last_refresh = datetime.now(timezone.utc)
        
        # Thread-safe UI updates via QTimer (main thread)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.loading_finished.emit)
        QTimer.singleShot(0, lambda: self.status_changed.emit(f"✅ Quantum Fetch Complete: {count} articles"))
        QTimer.singleShot(0, self._update_stats)
        QTimer.singleShot(0, self._start_refresh_timer)
        
        logger.info(f"Fetch complete: {count} articles")
    
    def _on_error(self, error: str):
        """Handle error - called from worker thread, use thread-safe updates"""
        self._fetching = False
        
        # Thread-safe updates via QTimer
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.loading_finished.emit)
        QTimer.singleShot(0, lambda: self.error_occurred.emit(error))
        QTimer.singleShot(0, lambda: self.status_changed.emit(f"❌ Error: {error}"))
        
        logger.error(f"Controller error: {error}")
    
    # ─────────────────────────────────────────────────────────────────
    # AUTO-REFRESH
    # ─────────────────────────────────────────────────────────────────
    
    def _start_refresh_timer(self):
        """Start auto-refresh timer"""
        self._refresh_timer.start(self.REFRESH_INTERVAL * 1000)
        self._countdown_timer.start(1000)
    
    def _on_refresh_timer(self):
        """Handle auto-refresh timer"""
        if not self._fetching:
            logger.info("Auto-refresh triggered")
            self._on_refresh()
    
    def _update_countdown(self):
        """Update countdown display"""
        if not self._last_refresh:
            return
        
        elapsed = (datetime.now(timezone.utc) - self._last_refresh).total_seconds()
        remaining = max(0, self.REFRESH_INTERVAL - elapsed)
        
        if remaining <= 0:
            return
        
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        if remaining <= 10:
            status = f"⚡ Quantum Refresh in {seconds}s"
        elif remaining <= 30:
            status = f"🔄 Refresh in {seconds}s"
        else:
            status = f"⏱️ Next quantum refresh: {minutes}:{seconds:02d}"
        
        # Update status bar (thread-safe via signal)
        if hasattr(self.window, 'status_bar'):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.window.status_bar.set_message(status))
    
    # ─────────────────────────────────────────────────────────────────
    # HISTORY
    # ─────────────────────────────────────────────────────────────────
    
    def _save_to_history(self):
        """Save current batch to history"""
        if not self._articles:
            return
        
        batch = {
            'timestamp': datetime.now().isoformat(),
            'articles': self._articles.copy(),
            'count': len(self._articles)
        }
        
        self._history_batches.insert(0, batch)
        
        # Limit history batches
        if len(self._history_batches) > 10:
            self._history_batches = self._history_batches[:10]
        
        logger.info(f"Saved batch to history: {batch['count']} articles")
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get history batches"""
        return self._history_batches
    
    def load_history_batch(self, index: int):
        """Load a history batch"""
        if 0 <= index < len(self._history_batches):
            batch = self._history_batches[index]
            self._articles = batch['articles'].copy()
            self.articles_loaded.emit(self._articles)
            self.status_changed.emit(
                f"📜 Loaded history batch from {batch['timestamp']}"
            )
    
    # ─────────────────────────────────────────────────────────────────
    # DIALOGS
    # ─────────────────────────────────────────────────────────────────
    
    def _show_history(self):
        """Show history popup"""
        logger.info("Opening history popup")
        from .dialogs import HistoryPopup
        
        articles = self._articles
        
        dialog = HistoryPopup(self.window, articles)
        dialog.exec()
        self.status_changed.emit("📜 History viewed")
    
    def _show_preferences(self):
        """Show preferences dialog"""
        logger.info("Opening preferences dialog")
        from .dialogs import PreferencesDialog
        
        dialog = PreferencesDialog(self.window)
        if dialog.exec():
            self.status_changed.emit("⚙️ Preferences updated")
    
    def _show_developer(self):
        """Show developer dashboard"""
        logger.info("Opening developer dashboard")
        from .dialogs import DeveloperDashboard
        
        dialog = DeveloperDashboard(self.window, self._orchestrator)
        if dialog.authenticate():
            dialog.exec()
            self.status_changed.emit("🔧 Developer dashboard opened")
    
    # ─────────────────────────────────────────────────────────────────
    # ARTICLE HANDLING
    # ─────────────────────────────────────────────────────────────────
    
    @Slot(dict)
    def _on_article_clicked(self, article: dict):
        """Handle article click"""
        logger.info(f"Article clicked: {article.get('title', 'Unknown')[:50]}")
        
        # Open article popup dialog
        from .dialogs import ArticlePopup
        
        # Convert dict to a simple object if needed
        class ArticleObj:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        article_obj = ArticleObj(article)
        dialog = ArticlePopup(self.window, article_obj)
        dialog.exec()
    
    # ─────────────────────────────────────────────────────────────────
    # MODE SWITCHING
    # ─────────────────────────────────────────────────────────────────
    
    @Slot(str)
    def _on_mode_changed(self, mode: str):
        """Handle mode change"""
        self._current_mode = mode
        logger.info(f"Mode changed to: {mode}")
        
        if mode == "developer":
            self.status_changed.emit("🛠️ Developer mode activated")
        else:
            self.status_changed.emit("👤 User mode activated")
    
    # ─────────────────────────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────────────────────────
    
    def _update_stats(self):
        """Update statistics"""
        stats = {
            'articles': len(self._articles),
            'sources': len(set(a.get('source', 'Unknown') for a in self._articles)),
            'queries': 0,
            'rejected': 0,
        }
        
        # Calculate average score
        scores = [
            self._get_score(a) for a in self._articles
        ]
        if scores:
            stats['avg_score'] = sum(scores) / len(scores)
        
        self.stats_updated.emit(stats)
    
    def _get_score(self, article: dict) -> float:
        """Extract score from article"""
        score = article.get('tech_score', 0)
        if isinstance(score, dict):
            score = score.get('score', 0)
        return float(score) if score else 0.0
    
    # ─────────────────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────────────────
    
    def _to_dict(self, article) -> dict:
        """Convert article to dictionary"""
        if hasattr(article, 'to_dict'):
            return article.to_dict()
        elif hasattr(article, '__dict__'):
            return article.__dict__
        elif isinstance(article, dict):
            return article
        else:
            return {'title': str(article), 'source': 'Unknown'}
    
    def get_current_articles(self) -> List[Dict[str, Any]]:
        """Get current articles list"""
        return self._articles.copy()
    
    def is_fetching(self) -> bool:
        """Check if currently fetching"""
        return self._fetching
    
    def get_quantum_scraper(self):
        """Get quantum scraper instance"""
        return self._quantum_scraper
    
    def get_quantum_bypass(self):
        """Get quantum bypass instance"""
        return self._quantum_bypass
    
    def stop(self):
        """Stop all operations"""
        self._refresh_timer.stop()
        self._countdown_timer.stop()
        
        # Stop advanced components
        if self._reddit_stream and hasattr(self._reddit_stream, 'stop'):
            self._reddit_stream.stop()
        
        if self._global_discovery and hasattr(self._global_discovery, 'stop_rotation'):
            self._global_discovery.stop_rotation()
        
        self.thread_pool.waitForDone(3000)
        
        # Close aiohttp sessions to prevent "unclosed client session" warnings
        self._close_aiohttp_sessions()
        
        logger.info("Controller stopped")
    
    def _close_aiohttp_sessions(self):
        """Close any remaining aiohttp client sessions"""
        import asyncio
        import aiohttp
        
        try:
            # Get all running event loops and close their sessions
            try:
                loop = asyncio.get_running_loop()
                # Cancel all pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # Close any aiohttp sessions in the orchestrator or pipeline
                if self._orchestrator:
                    if hasattr(self._orchestrator, '_session') and self._orchestrator._session:
                        if not self._orchestrator._session.closed:
                            asyncio.create_task(self._orchestrator._session.close())
                
                if self._pipeline:
                    if hasattr(self._pipeline, '_session') and self._pipeline._session:
                        if not self._pipeline._session.closed:
                            asyncio.create_task(self._pipeline._session.close())
                
            except RuntimeError:
                # No running loop
                pass
                
        except Exception as e:
            logger.warning(f"Error closing aiohttp sessions: {e}")
