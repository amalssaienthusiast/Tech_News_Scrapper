"""
Integration Guide: Real-Time Live Dashboard

This file shows how to integrate the live dashboard widgets into the main GUI.
Copy and adapt these code snippets into gui/app.py
"""

# =============================================================================
# STEP 1: Import the live dashboard widgets
# =============================================================================

# Add to the top of gui/app.py with other imports:
"""
from gui.live_dashboard import (
    LiveSourceHeartbeatMonitor,
    LiveArticleStreamPreview,
    LiveStatisticsPanel,
    LiveActivityLog
)
from gui.live_dashboard_part2 import (
    PipelineVisualizer,
    SourceActivityMatrix,
    NetworkThroughputGraph
)
"""

# =============================================================================
# STEP 2: Add live dashboard to TechNewsGUI class
# =============================================================================

# In TechNewsGUI.__init__(), add after other initializations:
"""
# Live dashboard widgets
self.live_source_monitor = None
self.live_article_stream = None
self.live_stats_panel = None
self.live_activity_log = None
self.pipeline_visualizer = None
self.source_matrix = None
self.network_graph = None
"""

# =============================================================================
# STEP 3: Replace _build_ui welcome screen with live dashboard
# =============================================================================

# Find the _build_ui method and replace the welcome screen creation:

"""
# OLD CODE (around line 2550):
    def _show_welcome_screen(self):
        frame = tk.Frame(self.results_frame, bg=THEME.bg_highlight, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Static welcome message...
        tk.Label(loading_frame, text="Loading articles from 8+ premium sources...")

# NEW CODE - Replace with live dashboard:
    def _show_live_dashboard(self):
        \"\"\"Show the real-time live dashboard instead of static welcome.\"\"\"
        
        # Clear any existing content
        self._clear_results()
        
        # Main container with two columns
        main_container = tk.Frame(self.results_frame, bg=THEME.bg)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # LEFT COLUMN - Main live content
        left_column = tk.Frame(main_container, bg=THEME.bg)
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # TOP: Live source heartbeat monitor
        self.live_source_monitor = LiveSourceHeartbeatMonitor(
            left_column, 
            orchestrator=self._orchestrator
        )
        self.live_source_monitor.pack(fill=tk.X, pady=(0, 10))
        
        # MIDDLE: Live article stream preview
        self.live_article_stream = LiveArticleStreamPreview(
            left_column,
            orchestrator=self._orchestrator,
            max_visible=5
        )
        self.live_article_stream.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # BOTTOM: Live activity log
        self.live_activity_log = LiveActivityLog(left_column)
        self.live_activity_log.pack(fill=tk.X, pady=(0, 10))
        
        # RIGHT COLUMN - Stats and info
        right_column = tk.Frame(main_container, bg=THEME.bg, width=350)
        right_column.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_column.pack_propagate(False)
        
        # Live statistics panel
        self.live_stats_panel = LiveStatisticsPanel(
            right_column,
            orchestrator=self._orchestrator
        )
        self.live_stats_panel.pack(fill=tk.X, pady=(0, 10))
        
        # Log initial activity
        if self.live_activity_log:
            self.live_activity_log.log(
                "Live dashboard initialized and ready",
                level='INFO',
                source='SYSTEM'
            )
"""

# =============================================================================
# STEP 4: Replace fetching status panel with enhanced version
# =============================================================================

# Find where the fetching status panel is created and replace:

"""
# OLD CODE:
    def _create_fetching_panel(self):
        panel = tk.Frame(self.root, bg=THEME.bg_dark)
        # Simple progress bar and status...

# NEW CODE:
    def _create_enhanced_fetching_panel(self):
        \"\"\"Create enhanced fetching panel with pipeline visualizer.\"\"\"
        panel = tk.Frame(self.root, bg=THEME.bg_dark)
        
        # Multi-stage pipeline visualizer
        self.pipeline_visualizer = PipelineVisualizer(
            panel, 
            orchestrator=self._orchestrator
        )
        self.pipeline_visualizer.pack(fill=tk.X, padx=20, pady=10)
        
        # Source activity matrix
        self.source_matrix = SourceActivityMatrix(
            panel,
            orchestrator=self._orchestrator
        )
        self.source_matrix.pack(fill=tk.X, padx=20, pady=5)
        
        # Network throughput graph
        self.network_graph = NetworkThroughputGraph(panel)
        self.network_graph.pack(fill=tk.X, padx=20, pady=10)
        
        return panel
"""

# =============================================================================
# STEP 5: Connect to orchestrator events
# =============================================================================

# Add event handlers to receive real-time updates:

"""
    def _setup_live_event_handlers(self):
        \"\"\"Connect to orchestrator event bus for live updates.\"\"\"
        from src.core.events import event_bus
        from src.core.protocol import EventType
        
        # Article discovered - update stream immediately
        event_bus.subscribe(
            EventType.ARTICLE_DISCOVERED,
            self._on_live_article_discovered
        )
        
        # Source status updates
        event_bus.subscribe(
            EventType.SOURCE_STATUS_UPDATE,
            self._on_source_status_update
        )
        
        # Pipeline progress
        event_bus.subscribe(
            EventType.PIPELINE_STAGE_UPDATE,
            self._on_pipeline_stage_update
        )
        
        # Statistics updates
        event_bus.subscribe(
            EventType.STATS_UPDATE,
            self._on_stats_update
        )
        
        # Log messages
        event_bus.subscribe(
            EventType.LOG_MESSAGE,
            self._on_log_message
        )

    def _on_live_article_discovered(self, article):
        \"\"\"Called immediately when article is discovered.\"\"\"
        if self.live_article_stream:
            # Convert article to dict if needed
            article_dict = article.to_dict() if hasattr(article, 'to_dict') else article
            
            # Update on main thread
            self.root.after(0, lambda: self.live_article_stream.on_article_found(article_dict))
        
        # Update stats
        if self.live_stats_panel:
            current = self.live_stats_panel.current_stats['articles']
            self.live_stats_panel.update_stat('articles', current + 1)
    
    def _on_source_status_update(self, event):
        \"\"\"Update source heartbeat monitor.\"\"\"
        if self.live_source_monitor:
            self.root.after(0, lambda: self.live_source_monitor.update_source(
                source_name=event.source_name,
                latency_ms=event.latency_ms,
                status=event.status,
                articles_found=event.articles_found
            ))
    
    def _on_pipeline_stage_update(self, event):
        \"\"\"Update pipeline visualizer.\"\"\"
        if self.pipeline_visualizer:
            self.root.after(0, lambda: self.pipeline_visualizer.update_stage(
                stage_name=event.stage,
                progress=event.progress,
                status=event.status,
                processed=event.processed_count,
                total=event.total_count,
                current_item=event.current_item,
                metrics=event.metrics
            ))
    
    def _on_stats_update(self, stats):
        \"\"\"Update statistics panel.\"\"\"
        if self.live_stats_panel:
            for key, value in stats.items():
                self.live_stats_panel.update_stat(key, value)
    
    def _on_log_message(self, log_message):
        \"\"\"Add to activity log.\"\"\"
        if self.live_activity_log:
            self.root.after(0, lambda: self.live_activity_log.log(
                message=log_message.text,
                level=log_message.level,
                source=log_message.source
            ))
"""

# =============================================================================
# STEP 6: Modify fetch methods to use live updates
# =============================================================================

# Update the fetch methods to stream articles instead of batch:

"""
    async def _fetch_with_live_updates(self, query: str = None):
        \"\"\"Fetch articles with live real-time updates.\"\"\"
        
        # Show live dashboard
        self._show_live_dashboard()
        
        # Setup event handlers
        self._setup_live_event_handlers()
        
        # Log start
        if self.live_activity_log:
            self.live_activity_log.log(
                f"Starting fetch: {query or 'latest news'}",
                level='INFO',
                source='FETCH'
            )
        
        try:
            # Use streaming API if available
            if hasattr(self._orchestrator, 'search_stream'):
                async for article in self._orchestrator.search_stream(query):
                    # Article appears immediately in live stream
                    # Event handlers will update UI
                    pass
            else:
                # Fallback to regular search
                result = await self._orchestrator.search_news(query)
                # Process results with live updates
                for article in result.articles:
                    self._on_live_article_discovered(article)
                    
        except Exception as e:
            if self.live_activity_log:
                self.live_activity_log.log(
                    f"Fetch error: {str(e)}",
                    level='ERROR',
                    source='SYSTEM'
                )
            raise
"""

# =============================================================================
# STEP 7: Update quick action buttons to use live dashboard
# =============================================================================

"""
    def _quick_search(self, query: str):
        \"\"\"Execute quick search with live dashboard.\"\"\"
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, query)
        
        # Trigger fetch with live updates
        self._async_runner.run_async(self._fetch_with_live_updates(query))
    
    def _trigger_unified_live_feed(self):
        \"\"\"Start live feed with real-time dashboard.\"\"\"
        # Show dashboard
        self._show_live_dashboard()
        
        # Log
        if self.live_activity_log:
            self.live_activity_log.log(
                "Starting unified live feed...",
                level='INFO',
                source='LIVE'
            )
        
        # Start fetching
        self._async_runner.run_async(self._fetch_with_live_updates())
"""

# =============================================================================
# STEP 8: Add cleanup method
# =============================================================================

"""
    def _cleanup_live_dashboard(self):
        \"\"\"Clean up live dashboard resources.\"\"\"
        if self.live_source_monitor:
            self.live_source_monitor.stop_monitoring()
        
        # Unsubscribe from events
        from src.core.events import event_bus
        # event_bus.unsubscribe(...) - implement as needed
"""

# =============================================================================
# USAGE EXAMPLE
# =============================================================================

"""
# In your main GUI initialization:

class TechNewsGUI:
    def __init__(self, root):
        # ... existing init code ...
        
        # Build UI with live dashboard
        self._build_ui()
        
        # Show live dashboard immediately (instead of welcome screen)
        self._show_live_dashboard()
        
        # Setup event handlers
        self._setup_live_event_handlers()
        
        # Start monitoring
        if self.live_source_monitor:
            self.live_source_monitor._start_monitoring()

# The live dashboard will now:
# 1. Show immediately instead of static welcome
# 2. Display real source connection status
# 3. Show articles as they're discovered (not after completion)
# 4. Update statistics in real-time
# 5. Stream activity logs
# 6. Visualize pipeline progress
# 7. Show per-source fetch progress
# 8. Display network throughput graph
"""

# =============================================================================
# TESTING CHECKLIST
# =============================================================================

"""
After integration, verify:

- [ ] Live dashboard appears immediately on app start
- [ ] Source heartbeat monitor shows all sources with ping/latency
- [ ] Articles appear one-by-one as discovered (not batch)
- [ ] Statistics increment in real-time (articles counter, etc.)
- [ ] Activity log shows real system events
- [ ] Pipeline visualizer shows 6 stages with progress
- [ ] Source matrix shows individual fetch progress per source
- [ ] Network graph displays scrolling throughput data
- [ ] "Time ago" labels update every second
- [ ] Everything updates WITHOUT blocking UI
- [ ] No fake/simulated data - all real from orchestrator
"""

print("Integration guide created! Follow the steps above to integrate the live dashboard.")
