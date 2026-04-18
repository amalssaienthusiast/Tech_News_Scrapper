"""
Revised Layout Structure for Tech News Scraper GUI

User Requirements:
1. Initially: Show SIMPLE welcome screen (not live dashboard)
2. "Start Live Feed": Show ARTICLES in main area only
3. "View Live Monitor" button: Show live dashboard SEPARATELY (full view)
4. Articles and Live Monitor are separate views, not mixed

Implementation Plan:
- _show_simple_welcome(): Simple welcome message
- _start_live_feed(): Shows articles in main area
- _show_live_monitor(): Shows full live dashboard (separate view)
- Sidebar button: "📊 View Live Monitor" to switch to live view
- Articles view: Just articles, no live widgets mixed in
"""

# ADD THESE METHODS TO gui/app.py

# =============================================================================
# 1. INITIAL WELCOME SCREEN (Simple, not live dashboard)
# =============================================================================

def _show_simple_welcome(self):
    """Display simple welcome screen initially."""
    self._clear_results()
    
    # Welcome container
    welcome_frame = tk.Frame(self.results_frame, bg=THEME.bg_highlight, padx=40, pady=40)
    welcome_frame.pack(fill=tk.BOTH, expand=True)
    
    # Header
    header = tk.Frame(welcome_frame, bg=THEME.bg_highlight)
    header.pack(pady=(0, 20))
    
    tk.Label(header, text="⚡", font=get_font("4xl"),
             fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
    tk.Label(header, text="Tech News Scraper", font=get_font("2xl", "bold"),
             fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(12, 0))
    
    # Version badge
    version_badge = tk.Frame(header, bg=THEME.purple, padx=10, pady=3)
    version_badge.pack(side=tk.LEFT, padx=(15, 0))
    tk.Label(version_badge, text="v7.0", font=get_font("sm", "bold"),
             fg=THEME.fg, bg=THEME.purple).pack()
    
    # Welcome message
    tk.Label(welcome_frame, 
             text="Welcome to your tech news aggregator",
             font=get_font("lg"),
             fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(pady=(10, 5))
    
    # Instructions
    instructions = tk.Frame(welcome_frame, bg=THEME.bg_highlight)
    instructions.pack(pady=20)
    
    tk.Label(instructions,
             text="🚀 Click '⚡ START LIVE FEED' to begin fetching articles",
             font=get_font("md"),
             fg=THEME.green, bg=THEME.bg_highlight).pack(pady=5)
    
    tk.Label(instructions,
             text="📊 Use 'View Live Monitor' to see real-time system status",
             font=get_font("md"),
             fg=THEME.blue, bg=THEME.bg_highlight).pack(pady=5)
    
    tk.Label(instructions,
             text="🔍 Search for specific topics using the search bar",
             font=get_font("md"),
             fg=THEME.cyan, bg=THEME.bg_highlight).pack(pady=5)
    
    # Stats summary
    stats_frame = tk.Frame(welcome_frame, bg=THEME.bg_visual, padx=20, pady=15)
    stats_frame.pack(pady=20)
    
    tk.Label(stats_frame,
             text="📈 System Ready",
             font=get_font("md", "bold"),
             fg=THEME.fg, bg=THEME.bg_visual).pack()
    
    stats_text = f"10 sources configured • 84 articles in database"
    tk.Label(stats_frame,
             text=stats_text,
             font=get_font("sm"),
             fg=THEME.comment, bg=THEME.bg_visual).pack(pady=(5, 0))


# =============================================================================
# 2. MODIFY _show_welcome to use simple version
# =============================================================================

# Replace existing _show_welcome method:
def _show_welcome(self):
    """Display simple welcome screen initially (not live dashboard)."""
    self._show_simple_welcome()


# =============================================================================
# 3. LIVE MONITOR VIEW (Full screen, separate from articles)
# =============================================================================

def _show_live_monitor(self):
    """Show full live dashboard monitor (separate view from articles)."""
    self._clear_results()
    self._live_dashboard_visible = True
    self._results_view_visible = False
    
    # Create container for live dashboard
    self._live_dashboard_container = tk.Frame(self.results_frame, bg=THEME.bg)
    self._live_dashboard_container.pack(fill=tk.BOTH, expand=True)
    
    # Header with back button
    header = tk.Frame(self._live_dashboard_container, bg=THEME.bg_highlight, padx=10, pady=10)
    header.pack(fill=tk.X)
    
    tk.Label(header, text="📊", font=get_font("lg"),
             fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
    tk.Label(header, text="Live System Monitor", font=get_font("lg", "bold"),
             fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
    
    # Back to articles button
    back_btn = tk.Button(header, text="← Back to Articles",
                        font=get_font("sm"),
                        bg=THEME.blue, fg=THEME.fg,
                        command=self._show_articles_view)
    back_btn.pack(side=tk.RIGHT)
    
    # Main content - two columns
    content = tk.Frame(self._live_dashboard_container, bg=THEME.bg)
    content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # LEFT COLUMN - Source monitor, article stream, activity log
    left = tk.Frame(content, bg=THEME.bg)
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
    
    self.live_source_monitor = LiveSourceHeartbeatMonitor(left)
    self.live_source_monitor.pack(fill=tk.X, pady=5)
    
    self.live_article_stream = LiveArticleStreamPreview(left, max_visible=5)
    self.live_article_stream.pack(fill=tk.BOTH, expand=True, pady=5)
    
    self.live_activity_log = LiveActivityLog(left)
    self.live_activity_log.pack(fill=tk.X, pady=5)
    
    # RIGHT COLUMN - Stats, pipeline, sources, network
    right = tk.Frame(content, bg=THEME.bg, width=380)
    right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
    right.pack_propagate(False)
    
    self.live_stats_panel = LiveStatisticsPanel(right)
    self.live_stats_panel.pack(fill=tk.X, pady=5)
    
    self.pipeline_visualizer = PipelineVisualizer(right)
    self.pipeline_visualizer.pack(fill=tk.X, pady=5)
    
    self.source_matrix = SourceActivityMatrix(right)
    self.source_matrix.pack(fill=tk.X, pady=5)
    
    self.network_graph = NetworkThroughputGraph(right, height=100)
    self.network_graph.pack(fill=tk.X, pady=5)
    
    # Start monitoring
    self._start_live_monitoring()
    
    # Log
    if self.live_activity_log:
        self.live_activity_log.log("Live monitor view opened", "INFO", "SYSTEM")


def _show_articles_view(self):
    """Switch back to articles view from live monitor."""
    self._live_dashboard_visible = False
    self._results_view_visible = True
    
    # Clear and show articles
    self._clear_results()
    
    # Redisplay current articles
    for article in self.current_articles[:self._page_size]:
        self._create_article_card(article)


# =============================================================================
# 4. ARTICLES VIEW (Articles only, no live widgets mixed)
# =============================================================================

def _show_articles_only_view(self):
    """Show articles in main area only (after feed starts)."""
    self._clear_results()
    self._live_dashboard_visible = False
    self._results_view_visible = True
    self._feed_started = True
    
    # Create container for articles only
    self._articles_container = tk.Frame(self.results_frame, bg=THEME.bg)
    self._articles_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Articles will be added here by _create_article_card
    # No live widgets mixed in - pure article view


# =============================================================================
# 5. SIDEBAR BUTTONS
# =============================================================================

# Add these buttons in sidebar (in _build_ui method):

# After the "Start Live Feed" button, add:
"""
# View Live Monitor button
live_monitor_btn = tk.Button(
    sidebar, 
    text="📊 View Live Monitor",
    font=get_font("sm", "bold"),
    bg=THEME.blue,
    fg=THEME.fg,
    command=self._show_live_monitor
)
live_monitor_btn.pack(fill=tk.X, pady=5)
"""

# =============================================================================
# 6. MODIFY FEED START METHOD
# =============================================================================

def _trigger_unified_live_feed(self):
    """Start live feed and show articles view only."""
    if not self._orchestrator:
        messagebox.showwarning("Not Ready", "Orchestrator not initialized")
        return
    
    # Switch to articles-only view (no live widgets mixed)
    self._show_articles_only_view()
    
    # Start the feed
    self._async_runner.run_async(self._fetch_live_feed())


# =============================================================================
# 7. HELPER METHODS
# =============================================================================

def _get_articles_container(self):
    """Get container for article cards."""
    if hasattr(self, '_articles_container') and self._articles_container:
        if self._articles_container.winfo_exists():
            return self._articles_container
    return self.results_frame


# =============================================================================
# USER FLOW
# =============================================================================

"""
INITIAL STATE (App opens):
┌─────────────────────────────────────────────────┐
│  ⚡ Tech News Scraper v7.0                       │
│                                                  │
│  Welcome to your tech news aggregator           │
│                                                  │
│  🚀 Click '⚡ START LIVE FEED' to begin         │
│  📊 Use 'View Live Monitor' to see real-time    │
│  🔍 Search for specific topics                  │
│                                                  │
│  📈 System Ready                                │
│  10 sources configured • 84 articles in db      │
└─────────────────────────────────────────────────┘
        [⚡ START LIVE FEED]
        [📊 View Live Monitor]
        [🔍 Search...]

AFTER "Start Live Feed" clicked:
┌─────────────────────────────────────────────────┐
│  ARTICLES (Full Width)                          │
│  ┌─────────────────────────────────────────┐    │
│  │ Article 1                               │    │
│  │ Article 2                               │    │
│  │ Article 3                               │    │
│  │ ...                                     │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
        [📊 View Live Monitor]  ← Click to see monitor

AFTER "View Live Monitor" clicked:
┌─────────────────────────────────────────────────┐
│  📊 Live System Monitor        [← Back to Articles]│
├─────────────────────────────────────────────────┤
│  ┌──────────────┬─────────────────────────────┐ │
│  │ Sources      │ Statistics                  │ │
│  │ Articles     │ Pipeline                    │ │
│  │ Activity Log │ Sources Matrix              │ │
│  │              │ Network Graph               │ │
│  └──────────────┴─────────────────────────────┘ │
└─────────────────────────────────────────────────┘
"""
