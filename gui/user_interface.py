"""
User Interface - Simplified interface for end-users.

Provides an intuitive news browsing experience with:
- Smart news feed with AI-enhanced articles
- One-click actions (save, share, summarize)
- Personalization controls
- Zero-configuration smart defaults
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

from gui.theme import THEME, get_font, get_mode_theme
from gui.config_manager import get_config

logger = logging.getLogger(__name__)


class UserInterface:
    """
    Simplified interface for end-users.
    
    Features:
    - Clean news feed layout
    - AI-powered article summaries
    - One-click actions
    - Personalization options
    - Smart defaults (no configuration needed)
    """
    
    def __init__(self, parent_frame: tk.Frame, async_runner, on_article_select: Optional[Callable] = None):
        """
        Initialize user interface.
        
        Args:
            parent_frame: Parent tkinter frame
            async_runner: AsyncRunner for background tasks
            on_article_select: Callback when article is selected
        """
        self.parent = parent_frame
        self.async_runner = async_runner
        self.on_article_select = on_article_select
        
        # Configuration
        self._config = get_config()
        mode_theme = get_mode_theme('user')
        
        # State
        self._articles: List[Any] = []
        self._filtered_articles: List[Any] = []
        self._search_query: str = ""
        self._current_filter: str = "all"
        
        # Build UI
        self._build_ui()
        
        logger.info("UserInterface initialized")
    
    def _build_ui(self):
        """Build the main user interface."""
        # Configure parent
        self.parent.configure(bg=THEME.bg)
        
        # Main container
        self.main_container = tk.Frame(self.parent, bg=THEME.bg)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Header with controls
        self._build_header()
        
        # Content area
        self._build_content_area()
        
        # Sidebar with quick actions
        self._build_sidebar()
    
    def _build_header(self):
        """Build header with search and controls."""
        header = tk.Frame(self.main_container, bg=THEME.bg_dark, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Search box
        search_frame = tk.Frame(header_inner, bg=THEME.bg_highlight, padx=10, pady=5)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(search_frame, text="🔍", font=get_font("md"),
                 fg=THEME.comment, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                     font=get_font("md"), bg=THEME.bg_highlight,
                                     fg=THEME.fg, relief=tk.FLAT, width=40,
                                     insertbackground=THEME.fg)
        self.search_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', self._on_search)
        self.search_entry.insert(0, "Search articles...")
        self.search_entry.bind('<FocusIn>', lambda e: self._on_search_focus(True))
        self.search_entry.bind('<FocusOut>', lambda e: self._on_search_focus(False))
        
        # Quick filter buttons
        filter_frame = tk.Frame(header_inner, bg=THEME.bg_dark)
        filter_frame.pack(side=tk.RIGHT, padx=(20, 0))
        
        filters = [
            ("All", "all", THEME.cyan),
            ("🔥 Hot", "hot", THEME.orange),
            ("📰 Latest", "latest", THEME.green),
            ("⭐ Saved", "saved", THEME.yellow),
        ]
        
        for label, filter_id, color in filters:
            btn = tk.Button(filter_frame, text=label, font=get_font("sm"),
                           bg=THEME.bg_visual, fg=THEME.fg_dark,
                           activebackground=color, activeforeground=THEME.black,
                           relief=tk.FLAT, padx=12, pady=4,
                           command=lambda f=filter_id: self._set_filter(f))
            btn.pack(side=tk.LEFT, padx=2)
    
    def _build_content_area(self):
        """Build main content area."""
        content_container = tk.Frame(self.main_container, bg=THEME.bg)
        content_container.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Article feed area
        self.feed_canvas = tk.Canvas(content_container, bg=THEME.bg, 
                                     highlightthickness=0)
        feed_scrollbar = ttk.Scrollbar(content_container, orient="vertical",
                                       command=self.feed_canvas.yview)
        
        self.feed_frame = tk.Frame(self.feed_canvas, bg=THEME.bg)
        
        self.feed_canvas.configure(yscrollcommand=feed_scrollbar.set)
        
        feed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.feed_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_window = self.feed_canvas.create_window((0, 0), 
                                                            window=self.feed_frame,
                                                            anchor="nw")
        
        # Bind scroll events
        self.feed_frame.bind("<Configure>", self._on_feed_configure)
        self.feed_canvas.bind("<Configure>", self._on_canvas_configure)
        self.feed_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _build_sidebar(self):
        """Build right sidebar with quick actions."""
        sidebar = tk.Frame(self.main_container, bg=THEME.bg_dark, width=280)
        sidebar.pack(fill=tk.Y, side=tk.RIGHT)
        sidebar.pack_propagate(False)
        
        # Quick Stats
        stats_frame = tk.Frame(sidebar, bg=THEME.bg_dark, padx=15, pady=15)
        stats_frame.pack(fill=tk.X)
        
        tk.Label(stats_frame, text="📊 TODAY'S STATS", font=get_font("sm", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_dark).pack(anchor=tk.W)
        
        self.stats_labels = {}
        stats = [
            ("articles", "Articles", "0"),
            ("sources", "Sources", "0"),
            ("saved", "Saved", "0"),
        ]
        
        for key, label, default in stats:
            row = tk.Frame(stats_frame, bg=THEME.bg_dark)
            row.pack(fill=tk.X, pady=3)
            
            tk.Label(row, text=label, font=get_font("sm"),
                     fg=THEME.fg_dark, bg=THEME.bg_dark).pack(side=tk.LEFT)
            
            value_label = tk.Label(row, text=default, font=get_font("sm", "bold"),
                                   fg=THEME.fg, bg=THEME.bg_dark)
            value_label.pack(side=tk.RIGHT)
            self.stats_labels[key] = value_label
        
        # Separator
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=10)
        
        # Quick Actions
        actions_frame = tk.Frame(sidebar, bg=THEME.bg_dark, padx=15, pady=10)
        actions_frame.pack(fill=tk.X)
        
        tk.Label(actions_frame, text="⚡ QUICK ACTIONS", font=get_font("sm", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_dark).pack(anchor=tk.W, pady=(0, 10))
        
        actions = [
            ("🔄 Refresh Feed", self._on_refresh),
            ("🤖 AI Summary All", self._on_ai_summary),
            ("📤 Export Articles", self._on_export),
            ("⚙️ Preferences", self._on_preferences),
        ]
        
        for label, command in actions:
            btn = tk.Button(actions_frame, text=label, font=get_font("sm"),
                           bg=THEME.bg_highlight, fg=THEME.fg,
                           activebackground=THEME.bg_visual,
                           relief=tk.FLAT, anchor=tk.W, padx=10, pady=8,
                           command=command)
            btn.pack(fill=tk.X, pady=2)
        
        # Separator
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=10)
        
        # Topics
        topics_frame = tk.Frame(sidebar, bg=THEME.bg_dark, padx=15, pady=10)
        topics_frame.pack(fill=tk.X)
        
        tk.Label(topics_frame, text="🏷️ TOPICS", font=get_font("sm", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_dark).pack(anchor=tk.W, pady=(0, 10))
        
        topics = ["AI/ML", "Cybersecurity", "Startups", "Cloud", "Hardware", "Crypto"]
        
        for topic in topics:
            btn = tk.Button(topics_frame, text=f"  {topic}", font=get_font("sm"),
                           bg=THEME.bg_dark, fg=THEME.fg_dark,
                           activebackground=THEME.bg_highlight,
                           relief=tk.FLAT, anchor=tk.W, padx=5, pady=4,
                           command=lambda t=topic: self._filter_by_topic(t))
            btn.pack(fill=tk.X)
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _on_search_focus(self, focused: bool):
        """Handle search field focus."""
        if focused:
            if self.search_entry.get() == "Search articles...":
                self.search_entry.delete(0, tk.END)
        else:
            if not self.search_entry.get():
                self.search_entry.insert(0, "Search articles...")
    
    def _on_search(self, event=None):
        """Handle search."""
        query = self.search_var.get().strip()
        if query and query != "Search articles...":
            self._search_query = query.lower()
            self._filter_articles()
        else:
            self._search_query = ""
            self._filter_articles()
    
    def _set_filter(self, filter_id: str):
        """Set article filter."""
        self._current_filter = filter_id
        self._filter_articles()
    
    def _filter_articles(self):
        """Apply current filters to articles."""
        # Filter logic would go here
        pass
    
    def _filter_by_topic(self, topic: str):
        """Filter articles by topic."""
        self._search_query = topic.lower()
        self._filter_articles()
    
    def _on_feed_configure(self, event):
        """Handle feed frame resize."""
        self.feed_canvas.configure(scrollregion=self.feed_canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize."""
        self.feed_canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll."""
        self.feed_canvas.yview_scroll(-1 * (event.delta // 120), "units")
    
    def _on_refresh(self):
        """Refresh the feed."""
        logger.info("Refresh requested")
        # Would trigger feed refresh
    
    def _on_ai_summary(self):
        """Generate AI summaries for all articles."""
        messagebox.showinfo("AI Summary", "Generating AI summaries for all visible articles...")
    
    def _on_export(self):
        """Export articles."""
        messagebox.showinfo("Export", "Export feature - select format and destination")
    
    def _on_preferences(self):
        """Open preferences."""
        # Would open preferences popup
        pass
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def set_articles(self, articles: List[Any]):
        """Set articles to display."""
        self._articles = articles
        self._filter_articles()
        self._update_stats()
    
    def add_article(self, article: Any):
        """Add a single article to the feed."""
        self._articles.insert(0, article)
        self._update_stats()
    
    def _update_stats(self):
        """Update sidebar statistics."""
        if 'articles' in self.stats_labels:
            self.stats_labels['articles'].config(text=str(len(self._articles)))
    
    def get_scroll_position(self) -> float:
        """Get current scroll position."""
        return self.feed_canvas.yview()[0]
    
    def restore_scroll_position(self, position: float):
        """Restore scroll position."""
        self.feed_canvas.yview_moveto(position)
    
    def clear_feed(self):
        """Clear all articles from feed."""
        for widget in self.feed_frame.winfo_children():
            widget.destroy()
        self._articles = []
        self._update_stats()
    
    def destroy(self):
        """Clean up resources."""
        pass
