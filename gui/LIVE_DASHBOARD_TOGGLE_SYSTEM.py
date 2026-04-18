"""
Revised Live Dashboard Integration - Toggle System

This implementation:
1. Shows live dashboard initially when app starts
2. When feeds load, moves live dashboard to a toggle-accessible panel
3. User can toggle between "Articles View" and "Live Monitor View"
4. Fixes the widget initialization issues
"""

# INSTRUCTIONS FOR gui/app.py

# =============================================================================
# STEP 1: Import widgets (already done - keep existing imports)
# =============================================================================

# =============================================================================
# STEP 2: Add new initialization variables in __init__
# =============================================================================
"""
# Add these to __init__ method (around line 660):

# Live Dashboard State
self._live_dashboard_container = None  # Holds the live dashboard frame
self._live_dashboard_visible = True    # Currently showing live dashboard
self._results_view_visible = False     # Currently showing article results
self._dashboard_toggle_btn = None      # Toggle button reference

# Content containers
self._main_content_area = None         # Main results area
self._live_monitor_panel = None        # Side panel for live monitoring
"""

# =============================================================================
# STEP 3: Create the revised _show_live_dashboard method
# =============================================================================

def _show_live_dashboard(self):
    """Show live dashboard in main area (initial state)."""
    self._clear_results()
    self._live_dashboard_visible = True
    self._results_view_visible = False
    
    # Create main container
    self._live_dashboard_container = tk.Frame(self.results_frame, bg=THEME.bg)
    self._live_dashboard_container.pack(fill=tk.BOTH, expand=True)
    
    # Two column layout
    left = tk.Frame(self._live_dashboard_container, bg=THEME.bg)
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
    
    right = tk.Frame(self._live_dashboard_container, bg=THEME.bg, width=350)
    right.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
    right.pack_propagate(False)
    
    # LEFT SIDE - Source monitor, article stream, activity log
    self.live_source_monitor = LiveSourceHeartbeatMonitor(left)
    self.live_source_monitor.pack(fill=tk.X, pady=5)
    
    self.live_article_stream = LiveArticleStreamPreview(left, max_visible=5)
    self.live_article_stream.pack(fill=tk.BOTH, expand=True, pady=5)
    
    self.live_activity_log = LiveActivityLog(left)
    self.live_activity_log.pack(fill=tk.X, pady=5)
    
    # RIGHT SIDE - Stats, pipeline, sources, network
    self.live_stats_panel = LiveStatisticsPanel(right)
    self.live_stats_panel.pack(fill=tk.X, pady=5)
    
    self.pipeline_visualizer = PipelineVisualizer(right)
    self.pipeline_visualizer.pack(fill=tk.X, pady=5)
    
    self.source_matrix = SourceActivityMatrix(right)
    self.source_matrix.pack(fill=tk.X, pady=5)
    
    self.network_graph = NetworkThroughputGraph(right, height=80)
    self.network_graph.pack(fill=tk.X, pady=5)
    
    # Start live monitoring
    self._start_live_monitoring()
    
    # Log initial messages
    self._log_to_live_dashboard("Live dashboard initialized", "INFO", "SYSTEM")
    self._log_to_live_dashboard("Click 'Start Live Feed' to begin", "INFO", "SYSTEM")


# =============================================================================
# STEP 4: Add toggle system when feed starts
# =============================================================================

def _start_feed_with_toggle_system(self):
    """Start live feed and switch to toggle-able view."""
    # Hide live dashboard from main area
    if self._live_dashboard_container:
        self._live_dashboard_container.pack_forget()
    
    self._live_dashboard_visible = False
    self._results_view_visible = True
    
    # Create main content area for articles
    self._main_content_area = tk.Frame(self.results_frame, bg=THEME.bg)
    self._main_content_area.pack(fill=tk.BOTH, expand=True)
    
    # Create side panel for live monitoring (collapsed initially)
    self._live_monitor_panel = tk.Frame(self.results_frame, bg=THEME.bg, width=400)
    self._live_monitor_panel.pack(side=tk.RIGHT, fill=tk.Y)
    self._live_monitor_panel.pack_propagate(False)
    self._live_monitor_panel.pack_forget()  # Hidden by default
    
    # Move live widgets to side panel
    self._move_live_widgets_to_panel()
    
    # Add toggle button to sidebar
    self._add_dashboard_toggle_button()
    
    # Start the actual feed
    self._async_runner.run_async(self._fetch_live_feed())


def _move_live_widgets_to_panel(self):
    """Move live dashboard widgets to side panel."""
    if not self._live_monitor_panel:
        return
    
    # Repack widgets into side panel
    if self.live_source_monitor:
        self.live_source_monitor.pack_forget()
        self.live_source_monitor.pack(in_=self._live_monitor_panel, fill=tk.X, pady=5)
    
    if self.live_article_stream:
        self.live_article_stream.pack_forget()
        self.live_article_stream.pack(in_=self._live_monitor_panel, fill=tk.BOTH, expand=True, pady=5)
    
    if self.live_activity_log:
        self.live_activity_log.pack_forget()
        self.live_activity_log.pack(in_=self._live_monitor_panel, fill=tk.X, pady=5)
    
    if self.live_stats_panel:
        self.live_stats_panel.pack_forget()
        self.live_stats_panel.pack(in_=self._live_monitor_panel, fill=tk.X, pady=5)
    
    if self.pipeline_visualizer:
        self.pipeline_visualizer.pack_forget()
        self.pipeline_visualizer.pack(in_=self._live_monitor_panel, fill=tk.X, pady=5)
    
    if self.source_matrix:
        self.source_matrix.pack_forget()
        self.source_matrix.pack(in_=self._live_monitor_panel, fill=tk.X, pady=5)
    
    if self.network_graph:
        self.network_graph.pack_forget()
        self.network_graph.pack(in_=self._live_monitor_panel, fill=tk.X, pady=5)


def _add_dashboard_toggle_button(self):
    """Add toggle button to switch between views."""
    # Find the right sidebar
    sidebar = None
    for child in self.root.winfo_children():
        if isinstance(child, tk.Frame):
            for subchild in child.winfo_children():
                if hasattr(subchild, '_live_feed_btn'):
                    sidebar = subchild
                    break
    
    if sidebar:
        self._dashboard_toggle_btn = tk.Button(
            sidebar,
            text="📊 Show Live Monitor",
            font=get_font("sm", "bold"),
            bg=THEME.blue,
            fg=THEME.fg,
            command=self._toggle_live_dashboard
        )
        self._dashboard_toggle_btn.pack(fill=tk.X, pady=5)


def _toggle_live_dashboard(self):
    """Toggle between articles view and live monitor view."""
    if self._live_dashboard_visible:
        # Hide live dashboard, show articles full width
        if self._live_monitor_panel:
            self._live_monitor_panel.pack_forget()
        if self._main_content_area:
            self._main_content_area.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self._live_dashboard_visible = False
        if self._dashboard_toggle_btn:
            self._dashboard_toggle_btn.config(text="📊 Show Live Monitor")
    else:
        # Show live dashboard alongside articles
        if self._main_content_area:
            self._main_content_area.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        if self._live_monitor_panel:
            self._live_monitor_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self._live_dashboard_visible = True
        if self._dashboard_toggle_btn:
            self._dashboard_toggle_btn.config(text="📰 Show Articles Only")


# =============================================================================
# STEP 5: Fix widget initialization and monitoring
# =============================================================================

def _start_live_monitoring(self):
    """Start all live monitoring systems."""
    # Start source heartbeat
    if self.live_source_monitor:
        self.live_source_monitor.monitoring_active = True
        self.live_source_monitor._start_monitoring()
    
    # Start network graph
    if self.network_graph:
        self.network_graph._start_monitoring()
    
    # Start pipeline monitoring
    if self.pipeline_visualizer:
        self.pipeline_visualizer._start_monitoring()
    
    # Simulate initial activity to test widgets
    self._simulate_initial_activity()


def _simulate_initial_activity(self):
    """Simulate initial activity to verify widgets work."""
    # Add test articles
    test_articles = [
        {
            'title': 'Live dashboard active - waiting for feeds...',
            'source': 'System',
            'tech_score': 0,
            'relevance': 0
        },
        {
            'title': 'Ready to discover tech news from 10+ sources',
            'source': 'System', 
            'tech_score': 0,
            'relevance': 0
        }
    ]
    
    for article in test_articles:
        if self.live_article_stream:
            self.live_article_stream.on_article_found(article)
    
    # Log system messages
    self._log_to_live_dashboard("System ready", "SUCCESS", "SYSTEM")
    self._log_to_live_dashboard("10 sources configured", "INFO", "SYSTEM")
    self._log_to_live_dashboard("Click 'Start Live Feed' to begin", "INFO", "SYSTEM")


def _log_to_live_dashboard(self, message: str, level: str = "INFO", source: str = "SYSTEM"):
    """Safely log to live activity log."""
    if self.live_activity_log:
        try:
            self.live_activity_log.log(message, level=level, source=source)
        except Exception as e:
            logger.error(f"Failed to log to live dashboard: {e}")


# =============================================================================
# STEP 6: Fix article update handler
# =============================================================================

def _update_live_dashboard_with_article(self, article):
    """Update live dashboard when article discovered."""
    try:
        # Convert article to dict
        article_dict = self._article_to_dict(article)
        
        # Update article stream
        if self.live_article_stream and self.live_article_stream.winfo_exists():
            self.live_article_stream.on_article_found(article_dict)
        
        # Update stats
        if self.live_stats_panel:
            current = self.live_stats_panel.current_stats.get('articles', 0)
            self.live_stats_panel.update_stat('articles', current + 1)
        
        # Update source matrix
        source = article_dict.get('source', 'Unknown')
        if self.source_matrix and source in self.source_matrix.source_states:
            current_count = self.source_matrix.source_states[source].get('articles', 0)
            self.source_matrix.update_source_complete(source, current_count + 1)
        
        # Log activity
        title = article_dict.get('title', 'Untitled')[:30]
        self._log_to_live_dashboard(f"Found: {title}...", "SUCCESS", "FETCH")
        
    except Exception as e:
        logger.error(f"Error updating live dashboard: {e}")


def _article_to_dict(self, article) -> dict:
    """Convert article object to dictionary safely."""
    if hasattr(article, 'to_dict'):
        return article.to_dict()
    elif hasattr(article, '__dict__'):
        return article.__dict__
    elif isinstance(article, dict):
        return article
    else:
        return {'title': str(article), 'source': 'Unknown'}


# =============================================================================
# STEP 7: Connect to fetch methods
# =============================================================================

# Modify _trigger_unified_live_feed to use new system:
def _trigger_unified_live_feed(self):
    """Start live feed with toggle-able dashboard."""
    if not self._orchestrator:
        messagebox.showwarning("Not Ready", "Orchestrator not initialized")
        return
    
    # Switch to toggle system
    self._start_feed_with_toggle_system()


# =============================================================================
# TESTING - Add this to verify widgets work
# =============================================================================

def _test_live_widgets(self):
    """Test that all live widgets are working."""
    print("\n=== Testing Live Dashboard Widgets ===")
    
    widgets = {
        'live_source_monitor': self.live_source_monitor,
        'live_article_stream': self.live_article_stream,
        'live_stats_panel': self.live_stats_panel,
        'live_activity_log': self.live_activity_log,
        'pipeline_visualizer': self.pipeline_visualizer,
        'source_matrix': self.source_matrix,
        'network_graph': self.network_graph
    }
    
    for name, widget in widgets.items():
        if widget:
            print(f"✅ {name}: Created")
            if hasattr(widget, 'winfo_exists') and widget.winfo_exists():
                print(f"   └─ Visible: True")
            else:
                print(f"   └─ Visible: False (may be packed but not mapped)")
        else:
            print(f"❌ {name}: NOT CREATED")
    
    print("=== End Test ===\n")
