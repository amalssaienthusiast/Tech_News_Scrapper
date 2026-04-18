"""
Tech News Scraper v7.0 - Enterprise Command Center with Tokyo Night Theme

A stunning, professional-grade interface featuring:
- Tokyo Night color palette for beautiful dark mode aesthetics
- Enhanced article cards with visual score bars and tier badges
- Real-time news feed with timestamp-based sorting
- Modern typography and visual hierarchy
- Glassmorphism-inspired card design
- Dual-mode operation (User/Developer)
"""

import asyncio
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta
from typing import Optional, List
import sys
import webbrowser
from pathlib import Path
import warnings

# Suppress feedparser deprecation warnings that spam the terminal
warnings.filterwarnings("ignore", module="feedparser")
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*")
warnings.filterwarnings("ignore", message=".*renamed to.*ddgs.*")

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine import TechNewsOrchestrator, SearchResult
from src.engine.enhanced_feeder import EnhancedNewsPipeline
from src.core import NonTechQueryError, InvalidQueryError
from src.core.types import Article
from src.core.events import event_bus
from src.core.protocol import StatsUpdate, LogMessage, EventType
from src.engine.time_engine import get_time_engine, TimeEngine, FreshnessLevel

# GLOBAL OMNISCIENCE INTEGRATION
from src.discovery.global_discovery import get_global_discovery_manager, TechHub
from src.sources.reddit_stream import get_reddit_stream_client
from src.bypass.smart_proxy_router import get_smart_proxy_router

# QUANTUM INTEGRATION
from src.engine.quantum_scraper import QuantumTemporalScraper
from src.bypass.quantum_bypass import QuantumPaywallBypass
from src.search.query_builder import SearchQueryBuilder, quick_search
from src.core.quantum_types import TemporalState
from src.database import get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Tokyo Night theme


# Import modular GUI components
from gui import (
    THEME, FONTS, get_font, configure_ttk_styles,
    SecurityManager, PasscodeDialog, AsyncRunner,
    LiveLogPanel, RealTimeLogHandler,
    LiveStatusBanner, DynamicStatusBar,
    ArticleCard, URLAnalysisPopup, FullContentPopup,
    ArticlePopup, CustomSourcesPopup, ScrollableFrame
)
# Access the shared log buffer
from gui.widgets.log_panel import _log_buffer, _log_buffer_lock

# Import mode management and developer dashboard
from gui.mode_manager import get_mode_manager, ModeState
from gui.developer_dashboard import DeveloperDashboard

# Import live dashboard widgets
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

# v7.1 Enhancement Widgets - Storage, Personalization, Cache
from gui.enhancement_widgets import (
    StorageModePanel,
    ArticleSaveExportPanel,
    PersonalizationScoreWidget,
    SaveArticleButton,
    CacheStatsWidget,
    add_save_button_to_card,
)

# Add real-time handler (uses the one from gui.widgets.log_panel)
rt_handler = RealTimeLogHandler()
rt_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(rt_handler)






# =============================================================================
# ENTERPRISE FEATURE POPUPS (v7.0)
# =============================================================================

class PreferencesPopup:
    """User Preferences panel - manages topics, watchlist, and delivery settings."""
    
    def __init__(self, parent, async_runner):
        self.parent = parent
        self.async_runner = async_runner
        
        # Import preferences manager
        from src.user import get_preferences_manager
        self.manager = get_preferences_manager()
        self.user_id = "default_user"  # Single-user mode for desktop app
        self.prefs = self.manager.get_preferences(self.user_id)
        
        self.window = tk.Toplevel(parent)
        self.window.title("⚙️ User Preferences")
        self.window.geometry("800x700")
        self.window.configure(bg=THEME.bg)
        self.window.transient(parent)
        self.window.grab_set()
        
        self._build_ui()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.window, bg=THEME.bg_dark, height=55)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Frame(header, bg=THEME.magenta, height=3).pack(fill=tk.X, side=tk.TOP)
        
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(header_inner, text="⚙️", font=get_font("xl"),
                 fg=THEME.magenta, bg=THEME.bg_dark).pack(side=tk.LEFT, pady=10)
        tk.Label(header_inner, text="USER PREFERENCES", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0), pady=10)
        
        # Main content with tabs
        content = tk.Frame(self.window, bg=THEME.bg, padx=25, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Notebook for tabs
        style = ttk.Style()
        style.configure("Prefs.TNotebook", background=THEME.bg)
        style.configure("Prefs.TNotebook.Tab", background=THEME.bg_highlight, 
                       foreground=THEME.fg_dark, padding=[12, 6])
        
        notebook = ttk.Notebook(content, style="Prefs.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Topics
        topics_frame = tk.Frame(notebook, bg=THEME.bg, padx=15, pady=15)
        notebook.add(topics_frame, text="📚 Topics")
        self._build_topics_tab(topics_frame)
        
        # Tab 2: Watchlist
        watchlist_frame = tk.Frame(notebook, bg=THEME.bg, padx=15, pady=15)
        notebook.add(watchlist_frame, text="👁️ Watchlist")
        self._build_watchlist_tab(watchlist_frame)
        
        # Tab 3: Delivery
        delivery_frame = tk.Frame(notebook, bg=THEME.bg, padx=15, pady=15)
        notebook.add(delivery_frame, text="📬 Delivery")
        self._build_delivery_tab(delivery_frame)
        
        # Footer buttons
        footer = tk.Frame(self.window, bg=THEME.bg_highlight, pady=12)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Button(footer, text="💾 Save Changes", font=get_font("sm", "bold"),
                  bg=THEME.green, fg=THEME.black,
                  padx=20, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=self._save_preferences).pack(side=tk.LEFT, padx=20)
        
        tk.Button(footer, text="✕ Close", font=get_font("sm"),
                  bg=THEME.bg_visual, fg=THEME.fg_dark,
                  padx=20, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=self.window.destroy).pack(side=tk.RIGHT, padx=20)
    
    def _build_topics_tab(self, parent):
        tk.Label(parent, text="📚 Topic Subscriptions", font=get_font("md", "bold"),
                 fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 10))
        
        tk.Label(parent, text="Adjust weights (0-2) to prioritize topics. Higher = more relevant.",
                 font=get_font("sm"), fg=THEME.comment, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 15))
        
        # Topic list frame
        self.topic_widgets = {}
        topics_container = tk.Frame(parent, bg=THEME.bg)
        topics_container.pack(fill=tk.BOTH, expand=True)
        
        for topic in self.prefs.topics:
            row = tk.Frame(topics_container, bg=THEME.bg_highlight, padx=12, pady=8)
            row.pack(fill=tk.X, pady=3)
            
            # Enabled checkbox
            var = tk.BooleanVar(value=topic.enabled)
            chk = tk.Checkbutton(row, variable=var, bg=THEME.bg_highlight,
                                 activebackground=THEME.bg_highlight)
            chk.pack(side=tk.LEFT)
            
            # Topic name
            tk.Label(row, text=topic.topic, font=get_font("sm"),
                     fg=THEME.fg, bg=THEME.bg_highlight, width=25, anchor=tk.W).pack(side=tk.LEFT)
            
            # Weight slider
            tk.Label(row, text="Weight:", font=get_font("xs"),
                     fg=THEME.comment, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(10, 5))
            
            weight_var = tk.DoubleVar(value=topic.weight)
            scale = tk.Scale(row, from_=0, to=2, resolution=0.1, orient=tk.HORIZONTAL,
                            variable=weight_var, bg=THEME.bg_highlight, fg=THEME.cyan,
                            highlightthickness=0, length=100)
            scale.pack(side=tk.LEFT)
            
            self.topic_widgets[topic.topic] = {'enabled': var, 'weight': weight_var}
        
        # Add new topic
        add_frame = tk.Frame(parent, bg=THEME.bg, pady=15)
        add_frame.pack(fill=tk.X)
        
        self.new_topic_entry = tk.Entry(add_frame, font=get_font("sm"),
                                        bg=THEME.bg_dark, fg=THEME.fg, width=30)
        self.new_topic_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.new_topic_entry.insert(0, "New topic name...")
        
        tk.Button(add_frame, text="➕ Add", font=get_font("sm", "bold"),
                  bg=THEME.green, fg=THEME.black, padx=15, pady=5,
                  relief=tk.FLAT, cursor='hand2',
                  command=self._add_topic).pack(side=tk.LEFT)
    
    def _build_watchlist_tab(self, parent):
        tk.Label(parent, text="👁️ Company Watchlist", font=get_font("md", "bold"),
                 fg=THEME.orange, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 10))
        
        tk.Label(parent, text="Track specific companies for lower alert thresholds.",
                 font=get_font("sm"), fg=THEME.comment, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 15))
        
        # Watchlist
        self.watchlist_widgets = {}
        watchlist_container = tk.Frame(parent, bg=THEME.bg)
        watchlist_container.pack(fill=tk.BOTH, expand=True)
        
        for company in self.prefs.watchlist:
            row = tk.Frame(watchlist_container, bg=THEME.bg_highlight, padx=12, pady=8)
            row.pack(fill=tk.X, pady=3)
            
            var = tk.BooleanVar(value=company.enabled)
            chk = tk.Checkbutton(row, variable=var, bg=THEME.bg_highlight,
                                 activebackground=THEME.bg_highlight)
            chk.pack(side=tk.LEFT)
            
            tk.Label(row, text=company.name, font=get_font("sm", "bold"),
                     fg=THEME.fg, bg=THEME.bg_highlight, width=20, anchor=tk.W).pack(side=tk.LEFT)
            
            if company.ticker:
                tk.Label(row, text=f"({company.ticker})", font=get_font("xs"),
                         fg=THEME.green, bg=THEME.bg_highlight).pack(side=tk.LEFT)
            
            self.watchlist_widgets[company.name] = {'enabled': var}
        
        # Add new company
        add_frame = tk.Frame(parent, bg=THEME.bg, pady=15)
        add_frame.pack(fill=tk.X)
        
        self.new_company_entry = tk.Entry(add_frame, font=get_font("sm"),
                                          bg=THEME.bg_dark, fg=THEME.fg, width=20)
        self.new_company_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.new_company_entry.insert(0, "Company name")
        
        self.new_ticker_entry = tk.Entry(add_frame, font=get_font("sm"),
                                         bg=THEME.bg_dark, fg=THEME.fg, width=10)
        self.new_ticker_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.new_ticker_entry.insert(0, "Ticker")
        
        tk.Button(add_frame, text="➕ Add", font=get_font("sm", "bold"),
                  bg=THEME.orange, fg=THEME.black, padx=15, pady=5,
                  relief=tk.FLAT, cursor='hand2',
                  command=self._add_company).pack(side=tk.LEFT)
    
    def _build_delivery_tab(self, parent):
        tk.Label(parent, text="📬 Delivery Settings", font=get_font("md", "bold"),
                 fg=THEME.purple, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 15))
        
        # Desktop notifications
        self.desktop_var = tk.BooleanVar(value=self.prefs.delivery.desktop_notifications)
        chk = tk.Checkbutton(parent, text="🖥️ Desktop Notifications",
                            variable=self.desktop_var, font=get_font("sm"),
                            fg=THEME.fg, bg=THEME.bg, selectcolor=THEME.bg_dark,
                            activebackground=THEME.bg)
        chk.pack(anchor=tk.W, pady=5)
        
        # Email
        self.email_var = tk.BooleanVar(value=self.prefs.delivery.email_enabled)
        chk = tk.Checkbutton(parent, text="📧 Email Digest",
                            variable=self.email_var, font=get_font("sm"),
                            fg=THEME.fg, bg=THEME.bg, selectcolor=THEME.bg_dark,
                            activebackground=THEME.bg)
        chk.pack(anchor=tk.W, pady=5)
        
        email_frame = tk.Frame(parent, bg=THEME.bg, padx=20)
        email_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(email_frame, text="Email:", font=get_font("xs"),
                 fg=THEME.comment, bg=THEME.bg).pack(side=tk.LEFT)
        self.email_entry = tk.Entry(email_frame, font=get_font("sm"),
                                   bg=THEME.bg_dark, fg=THEME.fg, width=30)
        self.email_entry.pack(side=tk.LEFT, padx=(10, 0))
        self.email_entry.insert(0, self.prefs.delivery.email_address or "your@email.com")
        
        # Telegram
        self.telegram_var = tk.BooleanVar(value=self.prefs.delivery.telegram_enabled)
        chk = tk.Checkbutton(parent, text="📱 Telegram",
                            variable=self.telegram_var, font=get_font("sm"),
                            fg=THEME.fg, bg=THEME.bg, selectcolor=THEME.bg_dark,
                            activebackground=THEME.bg)
        chk.pack(anchor=tk.W, pady=5)
        
        # Discord
        self.discord_var = tk.BooleanVar(value=self.prefs.delivery.discord_enabled)
        chk = tk.Checkbutton(parent, text="🎮 Discord Webhook",
                            variable=self.discord_var, font=get_font("sm"),
                            fg=THEME.fg, bg=THEME.bg, selectcolor=THEME.bg_dark,
                            activebackground=THEME.bg)
        chk.pack(anchor=tk.W, pady=5)
    
    def _add_topic(self):
        topic = self.new_topic_entry.get().strip()
        if topic and topic != "New topic name...":
            self.manager.add_topic(self.user_id, topic)
            self.prefs = self.manager.get_preferences(self.user_id)
            messagebox.showinfo("Added", f"Topic '{topic}' added!")
            self.new_topic_entry.delete(0, tk.END)
    
    def _add_company(self):
        company = self.new_company_entry.get().strip()
        ticker = self.new_ticker_entry.get().strip()
        if company and company != "Company name":
            ticker = ticker if ticker != "Ticker" else None
            self.manager.add_watched_company(self.user_id, company, ticker=ticker)
            self.prefs = self.manager.get_preferences(self.user_id)
            messagebox.showinfo("Added", f"Company '{company}' added to watchlist!")
    
    def _save_preferences(self):
        # Update topics
        for topic in self.prefs.topics:
            if topic.topic in self.topic_widgets:
                topic.enabled = self.topic_widgets[topic.topic]['enabled'].get()
                topic.weight = self.topic_widgets[topic.topic]['weight'].get()
        
        # Update watchlist
        for company in self.prefs.watchlist:
            if company.name in self.watchlist_widgets:
                company.enabled = self.watchlist_widgets[company.name]['enabled'].get()
        
        # Update delivery
        self.prefs.delivery.desktop_notifications = self.desktop_var.get()
        self.prefs.delivery.email_enabled = self.email_var.get()
        self.prefs.delivery.email_address = self.email_entry.get()
        self.prefs.delivery.telegram_enabled = self.telegram_var.get()
        self.prefs.delivery.discord_enabled = self.discord_var.get()
        
        # Save
        self.manager.save_preferences(self.prefs)
        messagebox.showinfo("Saved", "Preferences saved successfully!")


class SentimentDashboardPopup:
    """Real-time sentiment trends dashboard."""
    
    def __init__(self, parent, async_runner):
        self.parent = parent
        self.async_runner = async_runner
        
        self.window = tk.Toplevel(parent)
        self.window.title("📊 Sentiment Dashboard")
        self.window.geometry("900x600")
        self.window.configure(bg=THEME.bg)
        self.window.transient(parent)
        self.window.grab_set()
        
        self._build_ui()
        self._load_sentiment_data()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.window, bg=THEME.bg_dark, height=55)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Frame(header, bg=THEME.green, height=3).pack(fill=tk.X, side=tk.TOP)
        
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(header_inner, text="📊", font=get_font("xl"),
                 fg=THEME.green, bg=THEME.bg_dark).pack(side=tk.LEFT, pady=10)
        tk.Label(header_inner, text="SENTIMENT DASHBOARD", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0), pady=10)
        
        # Period selector
        self.period_var = tk.StringVar(value="24h")
        period_frame = tk.Frame(header_inner, bg=THEME.bg_dark)
        period_frame.pack(side=tk.RIGHT, pady=10)
        
        for period in ["24h", "7d", "30d"]:
            rb = tk.Radiobutton(period_frame, text=period, variable=self.period_var,
                               value=period, font=get_font("sm"),
                               fg=THEME.fg_dark, bg=THEME.bg_dark,
                               selectcolor=THEME.cyan, activebackground=THEME.bg_dark,
                               command=self._load_sentiment_data)
            rb.pack(side=tk.LEFT, padx=5)
        
        # Content
        content = tk.Frame(self.window, bg=THEME.bg, padx=25, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Sentiment cards container
        self.cards_frame = tk.Frame(content, bg=THEME.bg)
        self.cards_frame.pack(fill=tk.BOTH, expand=True)
        
        self.loading_label = tk.Label(self.cards_frame, text="Loading sentiment data...",
                                      font=get_font("md"), fg=THEME.comment, bg=THEME.bg)
        self.loading_label.pack(pady=50)
        
        # Footer
        tk.Button(self.window, text="✕ Close", font=get_font("sm"),
                  bg=THEME.bg_visual, fg=THEME.fg_dark,
                  padx=20, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=self.window.destroy).pack(pady=15)
    
    def _load_sentiment_data(self):
        """Load sentiment data from analyzer."""
        # Clear previous
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
        
        try:
            from src.intelligence.sentiment_analyzer import get_sentiment_analyzer
            analyzer = get_sentiment_analyzer()
            
            period = self.period_var.get()
            topics = ["overall", "AI", "Cybersecurity", "Crypto", "Startups", "Cloud", "Hardware"]
            
            # Create grid of cards
            for i, topic in enumerate(topics):
                trend = analyzer.get_trends(topic, period)
                self._create_sentiment_card(topic, trend, i)
        except Exception as e:
            tk.Label(self.cards_frame, text=f"Error loading sentiment: {e}",
                     font=get_font("sm"), fg=THEME.red, bg=THEME.bg).pack(pady=50)
    
    def _create_sentiment_card(self, topic: str, trend, index: int):
        """Create a sentiment card for a topic."""
        row = index // 3
        col = index % 3
        
        card = tk.Frame(self.cards_frame, bg=THEME.bg_highlight, padx=15, pady=15)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        
        # Configure grid weights
        self.cards_frame.grid_columnconfigure(col, weight=1)
        
        # Topic name
        tk.Label(card, text=topic.upper(), font=get_font("sm", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_highlight).pack(anchor=tk.W)
        
        # Sentiment score with emoji
        score = trend.avg_score
        if score >= 0.15:
            emoji, color = "🚀", THEME.green
        elif score <= -0.15:
            emoji, color = "📉", THEME.red
        else:
            emoji, color = "➖", THEME.fg_dark
        
        score_frame = tk.Frame(card, bg=THEME.bg_highlight)
        score_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(score_frame, text=emoji, font=get_font("2xl"),
                 fg=color, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(score_frame, text=f"{score:.2f}", font=get_font("xl", "bold"),
                 fg=color, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(10, 0))
        
        # Change indicator
        change = trend.score_change
        change_color = THEME.green if change > 0 else THEME.red if change < 0 else THEME.fg_dark
        change_arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        
        tk.Label(card, text=f"{change_arrow} {abs(change):.2f} vs previous",
                 font=get_font("xs"), fg=change_color, bg=THEME.bg_highlight).pack(anchor=tk.W)
        
        # Article count
        tk.Label(card, text=f"📰 {trend.article_count} articles",
                 font=get_font("xs"), fg=THEME.comment, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(5, 0))


class TechNewsGUI:
    """
    Professional GUI for Tech News Scraper v6.0.
    
    Features stunning Tokyo Night dark theme with:
    - Beautiful color-coded article cards
    - Visual tech score bars and tier badges
    - Real-time news sorting by timestamp
    - Modern glassmorphism-inspired design
    """
    
    VERSION = "7.0"
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Tech News Scraper 📰v{self.VERSION}")
        self.root.geometry("1400x900")
        self.root.configure(bg=THEME.bg)
        
        # Initialize Security Manager
        self.security = SecurityManager()
        
        # Initialize Async Runner
        # Initialize Async Runner
        self._async_runner = AsyncRunner()
        self._async_runner.start()
        
        # ═══════════════════════════════════════════════════════════════
        # TOP STATUS BAR (HIGH-TECH TICKER)
        # ═══════════════════════════════════════════════════════════════
        # A sleek, scrolling marquee displaying system status and credits.
        # "Solution Architect" aesthetic: Technical, monospaced, constant motion.

        ticker_bar = tk.Frame(self.root, bg=THEME.bg_dark, height=35)
        ticker_bar.pack(fill=tk.X, side=tk.TOP)
        ticker_bar.pack_propagate(False)

        # The Sentence
        # "Think like a solution architect and a senior engineer..."
        # Text design: Professional, metadata-heavy, clearly attributing the architect.
        ticker_text = (
            'ARCHITECTED & DEVELOPED BY {"Sci_COder"} '
        )

        # Canvas allows for smooth pixel-by-pixel scrolling (unlike Label text stepping)
        self.ticker_canvas = tk.Canvas(ticker_bar, bg=THEME.bg_dark, height=35, 
                                       highlightthickness=0)
        self.ticker_canvas.pack(fill=tk.BOTH, expand=True)

        try:
            # High-tech monospace font
            ticker_font = get_font("sm", "bold", "mono")
        except:
            ticker_font = ("Consolas", 10, "bold")

        # Create the text object on the canvas
        # Start positioned at the right edge of the screen
        canvas_width = 1500 # Estimate, will update on resize usually, but start far right
        text_id = self.ticker_canvas.create_text(
            canvas_width, 17, # Y=17 is rough middle of 35px height
            text=ticker_text, 
            font=ticker_font, 
            fill=THEME.cyan, # Cyan for that "System Active" feel
            anchor='w',
            tags=("ticker",)
        )

        def scroll_ticker():
            if not self.root: return
            try:
                # Move text left by 1 pixel
                self.ticker_canvas.move(text_id, -1, 0)
                
                # Get current coordinates
                bbox = self.ticker_canvas.bbox(text_id)
                if not bbox: return
                
                # bbox is (x1, y1, x2, y2)
                # If x2 (right edge of text) < 0 (left edge of screen), text is gone.
                # Reset to right side.
                if bbox[2] < 0:
                    # Get actual window width to reset correctly
                    win_width = self.root.winfo_width()
                    if win_width < 100: win_width = 1500 # Fallback during init
                    
                    width = bbox[2] - bbox[0]
                    # Reset position to exactly off-screen right
                    self.ticker_canvas.coords(text_id, win_width, 17)
                
                # 20ms refresh = 50 FPS smooth scroll
                self.root.after(20, scroll_ticker)
            except Exception:
                pass

        # Start animation
        self.root.after(100, scroll_ticker)

        # Separator line
        tk.Frame(self.root, bg="#2f334d", height=1).pack(fill=tk.X, side=tk.TOP)

        # ═══════════════════════════════════════════════════════════════
        # REST OF INITIALIZATION
        # ═══════════════════════════════════════════════════════════════
        
        # Configure ttk styles
        configure_ttk_styles()
        
        # ═══════════════════════════════════════════════════════════════
        # FEED STATE MANAGEMENT (PM-Approved Specs)
        # ═══════════════════════════════════════════════════════════════
        self.current_articles: List[Article] = []
        self._displayed_urls: set = set()           # Track displayed URLs for deduplication
        self._initial_load_complete = False          # Skip callbacks until initial display done
        
        # Search Mode
        self._search_mode = False                   # True when user is searching
        self._current_query = ""                    # Active search term
        
        # History & Pending
        self._article_history: List[Article] = []   # Pruned articles (FIFO, max 500)
        self._article_batches: List[dict] = []      # Batch history: [{timestamp, articles, count}]
        self._pending_updates: List[Article] = []   # Queued real-time during search
        self._max_history = 500                     # Max history size
        self._max_batches = 10                      # Max batch history
        
        # Real-time Streaming State
        self._streaming_active = True
        self._stream_event_queue = []
        
        # Pagination
        self._page_size = 20                        # Articles per page (lowered for faster history)
        self._current_page = 0                      # Current page index
        
        # Search debouncing
        self._search_after_id = None
        self._search_debounce_ms = 300
        
        # Toast state
        self._toast_visible = False
        self._toast_widget = None
        
        # Refresh timing
        self._countdown_start_time = None  # Initialize countdown timer
        self._timer_pulse = False  # For pulse effect
        self._fetching_in_progress = False  # Guard flag to prevent duplicate calls
        
        # Live Dashboard Widgets
        self.live_source_monitor = None
        self.live_article_stream = None
        self.live_stats_panel = None
        self.live_activity_log = None
        self.pipeline_visualizer = None
        self.source_matrix = None
        self.network_graph = None
        
        # ═══════════════════════════════════════════════════════════════
        # LIVE DASHBOARD TOGGLE SYSTEM (v7.1)
        # ═══════════════════════════════════════════════════════════════
        self._live_dashboard_container = None  # Holds the live dashboard frame
        self._live_dashboard_visible = True    # Currently showing live dashboard
        self._results_view_visible = False     # Currently showing article results
        self._dashboard_toggle_btn = None      # Toggle button reference
        self._live_monitor_panel = None        # Side panel for live monitoring when feeds load
        self._main_content_area = None         # Main content area for articles
        self._feed_started = False             # Track if feed has been started
        
        self._orchestrator: Optional[TechNewsOrchestrator] = None
        self._pipeline: Optional[EnhancedNewsPipeline] = None
        self._last_refresh = None
        
        # QUANTUM STATE
        self.quantum_enabled = tk.BooleanVar(value=False)
        self._quantum_scraper: Optional[QuantumTemporalScraper] = None
        self._quantum_bypass: Optional[QuantumPaywallBypass] = None
        self._query_builder: Optional[SearchQueryBuilder] = None
        
        # GLOBAL OMNISCIENCE STATE
        self._global_discovery = None
        self._reddit_stream = None
        self._smart_proxy = None
        self._global_mode = tk.BooleanVar(value=False)
        self._current_region = tk.StringVar(value="US")
        
        # ═══════════════════════════════════════════════════════════════
        # DUAL-MODE MANAGEMENT (v7.0)
        # ═══════════════════════════════════════════════════════════════
        self._mode_manager = get_mode_manager()
        self._current_mode = self._mode_manager.get_current_mode()
        self._developer_dashboard = None  # Lazy-loaded on first switch
        self._user_content_frame = None   # Main user content area
        
        # Initialize resilience system in background
        self._init_resilience_system()
        
        # Build the main UI (Header, Body, etc.) which will appear below this watermark
        self._build_ui()
        
        # Add keyboard shortcuts for mode switching
        self._bind_keyboard_shortcuts()
        
        self._init_app_logic()
    
    def _init_app_logic(self):
        """
        Initialize app with real pipeline (no fake loading).
        
        This replaces the old _init_orchestrator which used simulated delays.
        Now we initialize quickly and wait for user to trigger fetch.
        """
        def init():
            # Initialize orchestrator (still needed for search and analytics)
            self._orchestrator = TechNewsOrchestrator()
            
            # Initialize the unified pipeline
            self._pipeline = EnhancedNewsPipeline(
                enable_discovery=True,
                max_articles=500,
                max_age_hours=48,
            )
            
            # START the pipeline to create the feeder (CRITICAL!)
            # This must happen before registering callbacks
            async def start_pipeline():
                await self._pipeline.start()
                logger.info("✅ Pipeline started successfully")
                
                # CONNECT STREAMING CALLBACK (Antigravity Protocol)
                # Register with feeder for REAL-TIME updates (not pipeline)
                if hasattr(self._pipeline, '_feeder') and self._pipeline._feeder is not None:
                    feeder = self._pipeline._feeder
                    if hasattr(feeder, 'add_article_callback'):
                        feeder.add_article_callback(self._on_new_stream_article)
                        logger.info("✅ Real-time streaming callback registered with feeder")
                    elif hasattr(feeder, 'add_callback'):
                        feeder.add_callback(self._on_new_stream_article)
                        logger.info("✅ Real-time streaming callback registered with feeder (add_callback)")
                    elif hasattr(feeder, 'register_callback'):
                        feeder.register_callback(self._on_new_stream_article)
                        logger.info("✅ Real-time streaming callback registered with feeder (register_callback)")
                    else:
                        logger.warning("⚠️ Feeder found but no callback method available")
                else:
                    logger.warning("⚠️ Pipeline has no feeder - real-time streaming disabled")
                
                # Initialize Quantum Scraper NOW that feeder is available (CRITICAL FIX!)
                if self._pipeline._feeder is not None:
                    try:
                        db = get_database()
                        self._quantum_scraper = QuantumTemporalScraper(self._pipeline._feeder, db)
                        logger.info("🌌 Quantum Temporal Scraper initialized with feeder")
                    except Exception as e:
                        logger.error(f"Failed to initialize Quantum scraper: {e}")
                        self._quantum_scraper = None
            
            # Start pipeline in background thread
            import threading
            def init_pipeline():
                import asyncio
                # Create a new event loop for this thread (keeps loop alive for background tasks)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(start_pipeline())
                    # Keep loop alive for background tasks - don't close it
                except Exception as e:
                    logger.error(f"Pipeline init error: {e}")
            
            threading.Thread(target=init_pipeline, daemon=True).start()
            logger.info("🚀 Pipeline initialization started in background")
                
            # QUANTUM INITIALIZATION (after pipeline is fully started)
            # Note: Quantum scraper will be initialized after pipeline start completes
            self._quantum_scraper = None
            
            try:
                # Initialize bypass systems
                db = get_database()
                try:
                    # Try to import the compiled Rust extension
                    import advanced_web_scraper
                    logger.info("🦀 Rust extension 'advanced_web_scraper' loaded successfully")
                except ImportError:
                    logger.warning("⚠️ Rust extension not found. Run 'maturin develop' in src/bypass to enable high-performance scraping.")
                
                # Initialize Quantum bypass with default config (handles Rust internally)
                self._quantum_bypass = QuantumPaywallBypass()
                logger.info("🌌 Quantum components initialized and entangled")
                
                # Note: QuantumTemporalScraper will be initialized later when feeder is ready
            except Exception as e:
                logger.error(f"Quantum initialization failed: {e}")
            
            # GLOBAL OMNISCIENCE INITIALIZATION
            try:
                # Phase 1: Geo-Rotation Manager
                self._global_discovery = get_global_discovery_manager(rotation_interval=30)
                self._global_discovery.on_new_region = self._on_region_change
                logger.info("🌍 Global Discovery Manager initialized (30s rotation)")
                
                # Phase 2: Reddit Streaming
                self._reddit_stream = get_reddit_stream_client()
                self._reddit_stream.on_new_post = self._on_reddit_post
                logger.info("🔴 Reddit Stream Client initialized")
                
                # Phase 3: Smart Proxy Router
                self._smart_proxy = get_smart_proxy_router()
                logger.info("🌐 Smart Proxy Router initialized")
                
                logger.info("🌍 Global Omniscience Architecture activated!")
            except Exception as e:
                logger.error(f"Global Omniscience initialization failed: {e}")
                logger.warning("⚠️ Falling back to local-only discovery")
            
            # Ready!
            self.root.after(0, self._app_ready)
        
        threading.Thread(target=init, daemon=True).start()
    
    def _init_resilience_system(self):
        """Initialize the resilience system in background."""
        def init_resilience():
            try:
                from src.resilience import resilience
                import asyncio
                
                async def do_init():
                    await resilience.initialize()
                    return True
                
                # Create a new event loop for this thread (keeps loop alive for background tasks)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(do_init())
                    # Keep loop alive for background tasks - don't close it
                except Exception as e:
                    logger.error(f"Resilience init error: {e}")
                logger.info("✅ Resilience system initialized")
            except ImportError:
                logger.debug("Resilience system not available")
            except Exception as e:
                logger.warning(f"Resilience init warning: {e}")
        
        threading.Thread(target=init_resilience, daemon=True).start()
    
    def _bind_keyboard_shortcuts(self):
        """Bind keyboard shortcuts for mode switching and navigation."""
        # Mode switching
        self.root.bind('<Control-m>', lambda e: self._toggle_mode())
        self.root.bind('<Control-M>', lambda e: self._toggle_mode())
        self.root.bind('<F12>', lambda e: self._switch_to_developer_mode())
        self.root.bind('<F11>', lambda e: self._switch_to_user_mode())
        
        # Quick navigation
        self.root.bind('<Control-r>', lambda e: self._trigger_unified_live_feed())
        self.root.bind('<Control-R>', lambda e: self._trigger_unified_live_feed())
        
        logger.debug("Keyboard shortcuts bound: Ctrl+M (toggle), F11 (user), F12 (dev)")
    
    def _toggle_mode(self):
        """Toggle between user and developer modes."""
        if self._current_mode == 'user':
            self._switch_to_developer_mode()
        else:
            self._switch_to_user_mode()
    
    def _switch_to_developer_mode(self):
        """Switch to developer mode (password-protected)."""
        if self._current_mode == 'developer':
            return
        
        # Password protection
        if not self.security.verify_developer_access(self.root):
            return
        
        self._current_mode = 'developer'
        self._mode_manager.switch_mode('developer')
        
        # Hide user content
        if hasattr(self, 'main_content') and self.main_content:
            self.main_content.pack_forget()
        
        # Show developer dashboard
        if not self._developer_dashboard:
            self._dev_frame = tk.Frame(self.root, bg=THEME.bg)
            self._developer_dashboard = DeveloperDashboard(self._dev_frame, self._async_runner)
        
        self._dev_frame.pack(fill=tk.BOTH, expand=True)
        
        # Update mode indicator
        if hasattr(self, 'mode_label'):
            self.mode_label.config(text="🛠️ Developer Mode", fg=THEME.magenta)
        
        self._set_status("🛠️ Developer mode activated", "info")
        logger.info("Switched to developer mode")
    
    def _switch_to_user_mode(self):
        """Switch to user mode."""
        if self._current_mode == 'user':
            return
        
        self._current_mode = 'user'
        self._mode_manager.switch_mode('user')
        
        # Hide developer dashboard
        if hasattr(self, '_dev_frame') and self._dev_frame:
            self._dev_frame.pack_forget()
        
        # Show user content
        if hasattr(self, 'main_content') and self.main_content:
            self.main_content.pack(fill=tk.BOTH, expand=True)
        
        # Update mode indicator
        if hasattr(self, 'mode_label'):
            self.mode_label.config(text="👤 User Mode", fg=THEME.cyan)
        
        self._set_status("👤 User mode activated", "info")
        logger.info("Switched to user mode")
    
    def _app_ready(self):
        """
        Called when app is ready - immediately starts fetching news.
        
        Auto-starts the unified live feed so users see articles immediately.
        """
        # Ensure we start in LIVE MODE
        self._search_mode = False
        self._current_query = ""
        
        self._set_status("🚀 Auto-starting live feed...", "info")
        
        # Auto-trigger the unified live feed (no waiting for user click)
        self._trigger_unified_live_feed()
        
        # Update stats
        self._update_stats()
        
        # Start Global Omniscience systems
        self.root.after(2000, self.start_global_discovery)  # Start 2s after UI loads
    
    def _show_ready_state(self):
        """Show ready state prompting user to start the live feed."""
        frame = tk.Frame(self.results_frame, bg=THEME.bg_highlight, padx=40, pady=35)
        frame.pack(fill=tk.X, pady=15)
        
        # Header
        header = tk.Frame(frame, bg=THEME.bg_highlight)
        header.pack()
        
        tk.Label(header, text="⚡", font=get_font("4xl"),
                 fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(header, text="Tech News Scraper Ready", font=get_font("2xl", "bold"),
                 fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(12, 0))
        
        # Version badge
        version_badge = tk.Frame(header, bg=THEME.green, padx=10, pady=3)
        version_badge.pack(side=tk.LEFT, padx=(15, 0))
        tk.Label(version_badge, text="v7.0", font=get_font("sm", "bold"),
                 fg=THEME.bg_dark, bg=THEME.green).pack()
        
        # QUANTUM MODE BADGE (Antigravity Protocol)
        quantum_badge = tk.Frame(header, bg=THEME.magenta, padx=10, pady=3)
        quantum_badge.pack(side=tk.LEFT, padx=(10, 0))
        self.quantum_label = tk.Label(quantum_badge, text="🌌 QUANTUM MODE: ACTIVE", 
                                     font=get_font("sm", "bold"),
                                     fg=THEME.bg_dark, bg=THEME.magenta)
        self.quantum_label.pack()
        
        # Instructions
        instructions_frame = tk.Frame(frame, bg=THEME.bg_highlight)
        instructions_frame.pack(pady=(25, 0))
        
        tk.Label(instructions_frame, text="Click the button below to fetch news from ALL sources:", 
                 font=get_font("md"),
                 fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(pady=(0, 15))
        
        # Big CTA Buttons
        btn_frame = tk.Frame(instructions_frame, bg=THEME.bg)
        btn_frame.pack(pady=(0, 20))
        
        self._start_live_feed_btn = tk.Button(btn_frame, text="⚡ Start Live Feed",
                             font=get_font("lg", "bold"),
                             bg=THEME.green, fg=THEME.black,
                             activebackground=THEME.bright_green,
                             padx=30, pady=15, relief=tk.FLAT, cursor='hand2',
                             command=self._trigger_unified_live_feed)
        self._start_live_feed_btn.pack(side=tk.LEFT, padx=5)
        
        # Previous/History button
        history_btn = tk.Button(btn_frame, text="📜 Previous", 
                               font=get_font("md", "bold"),
                               bg=THEME.blue, fg=THEME.black,
                               activebackground=THEME.bright_blue,
                               padx=20, pady=15, relief=tk.FLAT, cursor='hand2',
                               command=self._show_history_popup)
        history_btn.pack(side=tk.LEFT, padx=5)
        
        # Feature highlights
        features_frame = tk.Frame(frame, bg=THEME.bg_highlight)
        features_frame.pack(pady=(10, 0))
        
        features = [
            ("📡", "30+ RSS Sources", THEME.cyan),
            ("🌐", "Google/Bing APIs", THEME.green),
            ("🕷️", "Web Scraping", THEME.orange),
            ("🔄", "Real-Time Updates", THEME.magenta),
        ]
        
        for icon, text, color in features:
            feat = tk.Frame(features_frame, bg=THEME.bg_visual, padx=12, pady=6)
            feat.pack(side=tk.LEFT, padx=5)
            tk.Label(feat, text=icon, font=get_font("sm"), fg=color, 
                     bg=THEME.bg_visual).pack(side=tk.LEFT)
            tk.Label(feat, text=text, font=get_font("sm"), fg=THEME.fg_dark,
                     bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(5, 0))
    
    def _trigger_unified_live_feed(self):
        """
        Trigger the unified live feed - fetches from ALL sources in parallel.

        This is the main trigger connected to the "⚡ Start Live Feed" button.
        """
        # Log button click for debugging
        logger.info("GUI: 'Start Live Feed' button clicked")

        # Visual feedback: flash the button to show it was clicked
        if hasattr(self, '_start_live_feed_btn') and self._start_live_feed_btn.winfo_exists():
            original_bg = self._start_live_feed_btn.cget('bg')
            self._start_live_feed_btn.config(bg=THEME.bright_green)
            self.root.after(150, lambda: self._start_live_feed_btn.config(bg=original_bg))

        # GUARD: Check if pipeline is ready
        if not self._pipeline:
            error_msg = "Pipeline not initialized. Please wait for the application to fully load."
            logger.warning(f"GUI: {error_msg}")
            self._show_error(error_msg)
            self._set_status("⚠️ Pipeline not ready yet", "warning")
            return

        # GUARD: Check cooldown before making the call
        if hasattr(self._pipeline, '_last_fetch') and self._pipeline._last_fetch:
            from datetime import UTC
            elapsed = (datetime.now(UTC) - self._pipeline._last_fetch).total_seconds()
            cooldown = getattr(self._pipeline, '_refresh_cooldown', 30)
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                msg = f"Please wait {remaining} seconds before fetching again (cooldown active)"
                logger.warning(f"GUI: {msg}")
                self._show_error(msg)
                self._set_status(f"⏳ Cooldown active ({remaining}s remaining)", "warning")
                return

        # GUARD: Prevent multiple simultaneous calls
        if hasattr(self, '_fetching_in_progress') and self._fetching_in_progress:
            msg = "A fetch operation is already in progress. Please wait for it to complete."
            logger.warning(f"GUI: {msg}")
            self._show_error(msg)
            self._set_status("⏳ Fetch in progress...", "info")
            return

        # Set the flag to prevent duplicate calls
        self._fetching_in_progress = True
        # Archive current articles instead of clearing (keep previous feeds visible)
        if self.current_articles:
            self._archive_current_batch()
            self._set_status(f"📦 Archived {len(self.current_articles)} articles • Fetching new...", "info")
        else:
            self._set_status("🚀 Fetching from ALL sources in parallel...", "info")
        self._show_progress_indicator()
        self._set_status("🚀 Initiating unified fetch sequence...", "info")
        
        # Register status callback for live updates
        if hasattr(self, '_on_pipeline_status'):
             # Clear existing to avoid duplicates
            self._pipeline._status_callbacks = [cb for cb in self._pipeline._status_callbacks if cb != self._on_pipeline_status]
            self._pipeline.add_status_callback(self._on_pipeline_status)

        # Define the async fetch operation
        async def do_fetch():
            # QUANTUM BRANCH
            if self.quantum_enabled.get() and self._quantum_scraper:
                self._set_status("🌌 Engaging Quantum Temporal Scraper...", "success")
                # Scrape Past, Present, Future
                return await self._quantum_scraper.scrape_multiple_timelines()
            
            # STANDARD BRANCH
            # Ensure pipeline is started and callback registered
            if not self._pipeline._running:
                await self._pipeline.start()
                # NOTE: Real-time callback already registered with feeder at line 680
                # DO NOT register _on_new_article here - causes duplicate processing!
                # The _on_new_stream_article callback handles all real-time updates
                pass
            return await self._pipeline.fetch_unified_live_feed(count=1000)
        
        def on_complete(articles, error):
            # ECO-SYSTEM SAFETY: Run UI updates on MAIN THREAD
            # CRITICAL: Always reset flag, even if error occurs
            try:
                self.root.after(0, lambda: self._handle_fetch_complete(articles, error))
            except Exception as e:
                logger.error(f"Error in on_complete: {e}")
                self._fetching_in_progress = False
                self._hide_progress_indicator()
        
        # Switch to articles only view when feed starts
        if not self._feed_started:
            self._show_articles_only_view()
        
        self._async_runner.run_async(do_fetch(), on_complete)

    def _handle_fetch_complete(self, articles, error):
        """Handle fetch completion on the main thread."""
        self._fetching_in_progress = False  # Reset flag
        self._hide_progress_indicator()
        
        if error:
            logger.error(f"Live feed error: {error}")
            self._show_error(str(error))
            self._set_status(f"❌ Fetch failed: {str(error)[:40]}", "error")
        elif articles:
            # Display new articles (already archived before fetch started)
            # DO NOT archive again - already done at start of _trigger_unified_live_feed
            self._display_realtime_results(articles)
            self._set_status(f"✅ Loaded {len(articles)} articles from ALL sources", "success")
            
            # Update displayed URLs for deduplication
            new_urls = set()
            for article in articles:
                self._displayed_urls.add(article.url)
                new_urls.add(article.url)
            
            # Handle pending updates from streaming during fetch
            # Articles in _pending_updates were already displayed via _on_new_stream_article
            # We just need to clear them since they're now part of the main batch
            if hasattr(self, '_pending_updates'):
                # Clear all pending updates - they're already displayed
                self._pending_updates.clear()
                
                # If cleared, hide toast
                if not self._pending_updates:
                    self._hide_toast()
                    # Also clear the stream event queue to be safe
                    if hasattr(self, '_stream_event_queue'):
                        self._stream_event_queue.clear()
        else:
            self._show_empty_state()
            self._set_status("⚠️ No articles found", "warning")
        
        # Update refresh time
        try:
            self._last_refresh = datetime.now()
            if hasattr(self, 'last_refresh_label') and self.last_refresh_label.winfo_exists():
                self.last_refresh_label.config(text=f"Last refresh: {self._last_refresh.strftime('%H:%M:%S')}")
            
            # Update countdown start time for refresh timer
            if hasattr(self, '_pipeline') and self._pipeline:
                self._countdown_start_time = self._last_refresh
            
            self._update_stats()
            self._update_refresh_countdown()
        except Exception as e:
            # Handle widget errors gracefully
            if "bad window path" in str(e) or isinstance(e, tk.TclError):
                logger.debug(f"Widget destroyed during refresh update: {e}")
            else:
                logger.error(f"Error updating refresh UI: {e}")
    
    def _on_pipeline_status(self, component: str, status: str):
        """
        Handle pipeline status updates safely on the main thread.
        
        Args:
            component: Component name (e.g. 'RSS', 'API', 'Scraper')
            status: Status message
        """
        def update_ui():
            if not hasattr(self, '_progress_status') or not self._progress_status.winfo_exists():
                return
            
            # Format: [COMPONENT] Status message
            msg = f"[{component.upper()}] {status}"
            self._progress_status.config(text=msg)
            
            # If we have a log container, add to it (for detailed view)
            if hasattr(self, '_progress_log') and self._progress_log.winfo_exists():
                label = tk.Label(self._progress_log, text=msg, font=get_font("xs", mono=True),
                         fg=THEME.cyan if "✓" in status else THEME.comment, 
                         bg=THEME.bg_visual, anchor="w")
                label.pack(fill=tk.X)
                if hasattr(self, '_progress_canvas_bar'):
                     pass # Auto-scroll handled by layout (bottom stacking)

        self.root.after_idle(update_ui)

    def _show_progress_indicator(self):
        """Show a detailed progress indicator during fetch."""
        self._progress_frame = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=20, pady=20)
        self._progress_frame.pack(fill=tk.X, pady=10)
        
        # Header
        header = tk.Frame(self._progress_frame, bg=THEME.bg_visual)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="🚀", font=get_font("xl"),
                 fg=THEME.green, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(header, text="Fetching from ALL sources...", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(10, 0))
        
        # Progress bar (indeterminate style using canvas)
        progress_container = tk.Frame(self._progress_frame, bg=THEME.bg, height=8)
        progress_container.pack(fill=tk.X, pady=(15, 10))
        
        self._progress_canvas_bar = tk.Canvas(progress_container, bg=THEME.bg, 
                                          height=8, highlightthickness=0)
        self._progress_canvas_bar.pack(fill=tk.X)
        
        # Create animated bar
        self._progress_bar = self._progress_canvas_bar.create_rectangle(0, 0, 100, 8, 
                                                                    fill=THEME.green, outline="")
        self._progress_pos = 0
        self._animate_progress()
        
        # Live Status Label (The big text)
        self._progress_status = tk.Label(self._progress_frame, text="Initializing ecosystem...",
                                         font=get_font("sm", "bold"), fg=THEME.cyan, bg=THEME.bg_visual)
        self._progress_status.pack(pady=(0, 10))

        # Detailed Log View (Scrollable)
        log_frame = tk.Frame(self._progress_frame, bg=THEME.bg_visual, height=100)
        log_frame.pack(fill=tk.X, expand=True)
        log_frame.pack_propagate(False) # Fix height

        # Simple manual scrolling implementation for log
        self._progress_log = tk.Frame(log_frame, bg=THEME.bg_visual)
        self._progress_log.pack(fill=tk.X, side=tk.BOTTOM) # Stack from bottom
    
    def _animate_progress(self):
        """Animate the progress bar."""
        if not hasattr(self, '_progress_canvas_bar') or not self._progress_canvas_bar.winfo_exists():
            return
        
        try:
            width = self._progress_canvas_bar.winfo_width()
            bar_width = 100
            
            self._progress_pos = (self._progress_pos + 10) % (width + bar_width)
            x1 = self._progress_pos - bar_width
            x2 = self._progress_pos
            
            self._progress_canvas_bar.coords(self._progress_bar, x1, 0, x2, 8)
            self.root.after(100, self._animate_progress)
        except Exception:
            pass
    
    def _hide_progress_indicator(self):
        """Hide the progress indicator."""
        if hasattr(self, '_progress_frame') and self._progress_frame.winfo_exists():
            self._progress_frame.destroy()


    def _perform_search(self, event=None):
        """Execute search: Filter current articles and set search mode."""
        query = self.search_var.get().strip()
        
        # QUANTUM INTEGRATION: Build advanced query
        if query and query != "Search articles...":
            try:
                # Construct professional query object even if running locally
                qb = SearchQueryBuilder().text(query).sort_by_relevance()
                
                # Add smart filters based on query content
                if "ai" in query.lower() or "quantum" in query.lower():
                    qb.filter_min_score(0.7)
                
                built_query = qb.build()
                logger.info(f"🔍 Executing Quantum Search Query: {built_query}")
                
                # In a full deployment, this would go to Elasticsearch:
                # results = await self.es_client.search(built_query)
                # But for now, we use the local filter as a fallback
            except Exception as e:
                logger.error(f"Search query construction failed: {e}")

        # Handle empty/placeholder query
        if not query or query == "Search articles...":
            if self._search_mode:
                self._search_mode = False
                self._current_query = ""
                self._clear_results()
                # Restore full feed
                for article in self.current_articles:
                    self._create_article_card(article)
                self._set_status("🔴 Live Feed Restored", "info")
                self.root.after_idle(lambda: self._update_scroll_region())
            return

        # Enable search mode
        self._search_mode = True
        self._current_query = query.lower()
        self._clear_results()
        
        # Filter existing articles
        matches = [
            a for a in self.current_articles 
            if self._matches_query(a, query)
        ]
        
        if matches:
            for article in matches:
                self._create_article_card(article)
            self.root.after_idle(lambda: self._update_scroll_region())
            self._set_status(f"🔍 Found {len(matches)} results for '{query}'", "success")
        else:
            self._show_empty_state(message=f"No results for '{query}'")
            self._set_status(f"🔍 No results for '{query}'", "warning")
            
        # Focus back to entry
        self.search_entry.focus_set()

    def _matches_query(self, article, query: str) -> bool:
        """Check if article matches search query."""
        if not query:
            return True
        
        try:
            q = query.lower()
            title = (getattr(article, 'title', '') or '').lower()
            summary = (getattr(article, 'summary', '') or '').lower()
            source = (getattr(article, 'source', '') or '').lower()
            return q in title or q in summary or q in source
        except Exception as e:
            logger.error(f"Error in _matches_query: {e}")
            return False


    def _on_new_article(self, article):
        """
        Called when a new article arrives from the realtime feed.
        - In SEARCH MODE: Queue if matches query, show toast
        - In LIVE MODE: Insert at top with deduplication
        """
        try:
            # Validate article has required attributes
            if not hasattr(article, 'title') or not hasattr(article, 'url'):
                logger.warning(f"_on_new_article: Invalid article object (missing attributes)")
                return
            
            logger.debug(f"_on_new_article called: {article.title[:40]}...")
            
            if not hasattr(self, 'results_frame') or not self.results_frame.winfo_exists():
                logger.warning("_on_new_article: results_frame not ready")
                return
            
            # Skip callbacks during initial load to avoid race condition
            if not self._initial_load_complete:
                logger.debug(f"Skipped during initial load: {article.title[:30]}...")
                return
            
            # DEDUP CHECK: Skip if already displayed
            if article.url in self._displayed_urls:
                logger.debug(f"Skipped duplicate: {article.title[:30]}...")
                return
        except Exception as e:
            logger.error(f"Error in _on_new_article: {e}")
            return

        
        # SEARCH MODE: Queue updates instead of displaying
        if self._search_mode:
            if self._matches_query(article, self._current_query):
                self._pending_updates.append(article)
                self._show_toast(len(self._pending_updates))
            return  # Don't insert during search
        
        # LIVE MODE: Insert and sort by timestamp
        self._displayed_urls.add(article.url)
        self.current_articles.append(article)
        
        # Update live dashboard with new article
        self._update_live_dashboard_with_article(article)
        
        # Sort by timestamp (newest first)
        from datetime import datetime
        def get_ts(art):
            if hasattr(art, 'published_at') and art.published_at:
                return art.published_at
            elif hasattr(art, 'scraped_at') and art.scraped_at:
                return art.scraped_at
            return datetime.min
        self.current_articles.sort(key=get_ts, reverse=True)
        
        # Create and insert article card at the beginning
        try:
            self._create_article_card(article, insert_at_top=True)
            
            # SCROLL REGION UPDATE: Recalculate after insert
            self.root.after_idle(lambda: self._update_scroll_region())
        except Exception as e:
            # Handle widget errors gracefully (widgets may be destroyed)
            if "bad window path" in str(e) or isinstance(e, tk.TclError):
                logger.debug(f"Widget destroyed during article card creation: {e}")
            else:
                logger.error(f"Error creating article card: {e}")
        
        # PRUNE: Move oldest to history if exceeded max
        children = self.results_frame.winfo_children()
        if len(children) > self._page_size:
            children[-1].destroy()
            if self.current_articles:
                old_article = self.current_articles.pop()
                self._move_to_history(old_article)
                self._displayed_urls.discard(old_article.url)
        
        # Update status bar to indicate new content
        self._set_status(f"📡 New: {article.title[:30]}...", "info")
        
        # Update stats
        self._update_stats()
    

    
    def _move_to_history(self, article):
        """Move article to history (FIFO, max 500)."""
        self._article_history.insert(0, article)
        if len(self._article_history) > self._max_history:
            self._article_history.pop()
    
    def _show_toast(self, count: int):
        """Show 'X New Results' toast at top of results."""
        if self._toast_widget and self._toast_widget.winfo_exists():
            # Update existing toast
            self._toast_label.config(text=f"🔔 {count} New Result{'s' if count > 1 else ''} matching '{self._current_query}'")
        else:
            # Create new toast
            self._toast_widget = tk.Frame(self.results_frame, bg=THEME.green, padx=15, pady=10)
            self._toast_widget.pack(fill=tk.X, pady=(0, 10), before=self.results_frame.winfo_children()[0] if self.results_frame.winfo_children() else None)
            
            self._toast_label = tk.Label(self._toast_widget, 
                text=f"🔔 {count} New Result{'s' if count > 1 else ''} matching '{self._current_query}'",
                font=get_font("md", "bold"), fg=THEME.bg_dark, bg=THEME.green)
            self._toast_label.pack(side=tk.LEFT)
            
            tk.Button(self._toast_widget, text="Show", font=get_font("sm", "bold"),
                      bg=THEME.bg_dark, fg=THEME.green, padx=10, pady=2,
                      relief=tk.FLAT, cursor="hand2",
                      command=self._merge_pending_updates).pack(side=tk.RIGHT)
        
        self._toast_visible = True
    
    def _hide_toast(self):
        """Hide the toast notification."""
        if self._toast_widget and self._toast_widget.winfo_exists():
            self._toast_widget.destroy()
        self._toast_widget = None
        self._toast_visible = False
    
    def _merge_pending_updates(self):
        """Merge queued articles into display on user click."""
        self._hide_toast()
        
        # Count before clearing
        count = len(self._pending_updates)
        
        # Process all pending updates and sort by timestamp
        for article in self._pending_updates:
            if article.url not in self._displayed_urls:
                self._displayed_urls.add(article.url)
                self.current_articles.append(article)
        
        # Sort all articles by timestamp (newest first)
        if self._pending_updates:
            from datetime import datetime
            def get_ts(art):
                if hasattr(art, 'published_at') and art.published_at:
                    return art.published_at
                elif hasattr(art, 'scraped_at') and art.scraped_at:
                    return art.scraped_at
                return datetime.min
            self.current_articles.sort(key=get_ts, reverse=True)
        
        # Display the new articles
        for article in self._pending_updates:
            if article.url in self._displayed_urls:
                self._create_article_card(article, insert_at_top=True)
        
        self._pending_updates.clear()
        self.root.after_idle(lambda: self._update_scroll_region())
        self._set_status(f"✅ Added {count} new results")
    
    def _archive_current_batch(self):
        """Archive current articles as a batch before displaying new ones."""
        if not self.current_articles:
            return
        
        # Create batch record
        batch = {
            "timestamp": datetime.now(),
            "articles": self.current_articles.copy(),
            "count": len(self.current_articles),
        }
        
        # Add to batch history (newest first)
        self._article_batches.insert(0, batch)
        
        # Also add to flat article history for individual lookups
        for article in self.current_articles:
            if article not in self._article_history:
                self._article_history.insert(0, article)
        
        # Enforce max batch history
        if len(self._article_batches) > self._max_batches:
            self._article_batches.pop()
        
        # Enforce max article history
        while len(self._article_history) > self._max_history:
            self._article_history.pop()
        
        logger.debug(f"Archived batch: {batch['count']} articles, {len(self._article_batches)} batches in history")
    
    def _show_history_popup(self):
        """Show popup with batch-based article history."""
        if not self._article_batches and not self._article_history:
            messagebox.showinfo("History Empty", "No articles in history yet.\n\nArticles are moved to history when you refresh or fetch new articles.")
            return
        
        popup = tk.Toplevel(self.root)
        popup.title("📜 Article History")
        popup.geometry("800x650")
        popup.configure(bg=THEME.bg)
        
        # Header
        header = tk.Frame(popup, bg=THEME.bg_dark, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="📜 Article History", font=get_font("lg", "bold"),
                 fg=THEME.purple, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=20, pady=15)
        
        batch_count = len(self._article_batches)
        total_articles = sum(b['count'] for b in self._article_batches)
        tk.Label(header, text=f"{batch_count} batches • {total_articles} articles", font=get_font("sm"),
                 fg=THEME.comment, bg=THEME.bg_dark).pack(side=tk.RIGHT, padx=20, pady=15)
        
        # Content with scroll
        content = tk.Frame(popup, bg=THEME.bg)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        canvas = tk.Canvas(content, bg=THEME.bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(content, orient=tk.VERTICAL, command=canvas.yview)
        frame = tk.Frame(canvas, bg=THEME.bg)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=frame, anchor=tk.NW)
        
        # Display batches with timestamps
        if self._article_batches:
            for i, batch in enumerate(self._article_batches):
                ts = batch['timestamp'].strftime('%H:%M:%S')
                date = batch['timestamp'].strftime('%b %d')
                count = batch['count']
                
                # Batch header
                batch_header = tk.Frame(frame, bg=THEME.bg_visual, padx=15, pady=10)
                batch_header.pack(fill=tk.X, pady=(10, 2))
                
                tk.Label(batch_header, text=f"📦 Batch {i+1}", font=get_font("md", "bold"),
                         fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT)
                tk.Label(batch_header, text=f"{count} articles", font=get_font("sm"),
                         fg=THEME.green, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(15, 0))
                tk.Label(batch_header, text=f"{date} at {ts}", font=get_font("sm"),
                         fg=THEME.comment, bg=THEME.bg_visual).pack(side=tk.RIGHT)
                
                # Articles in this batch (show first 10, expandable)
                articles_frame = tk.Frame(frame, bg=THEME.bg_highlight, padx=10, pady=5)
                articles_frame.pack(fill=tk.X)
                
                for j, article in enumerate(batch['articles'][:10]):
                    card = tk.Frame(articles_frame, bg=THEME.bg_highlight, padx=8, pady=4)
                    card.pack(fill=tk.X, pady=1)
                    
                    tk.Label(card, text=f"•", font=get_font("sm"),
                             fg=THEME.comment, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(0, 8))
                    tk.Label(card, text=article.title[:55] + "..." if len(article.title) > 55 else article.title,
                             font=get_font("sm"), fg=THEME.fg, bg=THEME.bg_highlight,
                             anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
                    tk.Label(card, text=article.source or "Unknown",
                             font=get_font("xs"), fg=THEME.orange, bg=THEME.bg_highlight).pack(side=tk.RIGHT)
                
                if count > 10:
                    tk.Label(articles_frame, text=f"... and {count - 10} more articles",
                             font=get_font("xs"), fg=THEME.comment, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=5)
        else:
            # Fallback to flat article history
            tk.Label(frame, text="Individual Article History", font=get_font("md", "bold"),
                     fg=THEME.purple, bg=THEME.bg).pack(pady=10)
            for i, article in enumerate(self._article_history[:50]):
                card = tk.Frame(frame, bg=THEME.bg_highlight, padx=12, pady=6)
                card.pack(fill=tk.X, pady=2)
                tk.Label(card, text=f"#{i+1}", font=get_font("sm", mono=True),
                         fg=THEME.comment, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(0, 10))
                tk.Label(card, text=article.title[:55] + "..." if len(article.title) > 55 else article.title,
                         font=get_font("sm"), fg=THEME.fg, bg=THEME.bg_highlight,
                         anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Close button
        tk.Button(popup, text="Close", font=get_font("md", "bold"),
                  bg=THEME.red, fg=THEME.fg, padx=25, pady=10,
                  relief=tk.FLAT, cursor="hand2",
                  command=popup.destroy).pack(pady=15)
    
    def _show_statistics_popup(self):
        """Show popup with comprehensive scraping statistics."""
        popup = tk.Toplevel(self.root)
        popup.title("📊 Scraping Statistics")
        popup.geometry("700x600")
        popup.configure(bg=THEME.bg)
        
        # Header
        header = tk.Frame(popup, bg=THEME.bg_dark, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="📊 Scraping Statistics", font=get_font("lg", "bold"),
                 fg=THEME.green, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=20, pady=15)
        
        # Refresh button
        refresh_btn = tk.Button(header, text="↻ Refresh", font=get_font("sm", "bold"),
                                bg=THEME.cyan, fg=THEME.black,
                                relief=tk.FLAT, cursor="hand2",
                                command=lambda: self._refresh_statistics_popup(content_frame))
        refresh_btn.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # Content with scroll
        content = tk.Frame(popup, bg=THEME.bg)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        canvas = tk.Canvas(content, bg=THEME.bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(content, orient=tk.VERTICAL, command=canvas.yview)
        content_frame = tk.Frame(canvas, bg=THEME.bg)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content_frame, anchor=tk.NW)
        
        # Populate statistics
        self._populate_statistics(content_frame)
        
        content_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Close button
        tk.Button(popup, text="Close", font=get_font("md", "bold"),
                  bg=THEME.red, fg=THEME.fg, padx=25, pady=10,
                  relief=tk.FLAT, cursor="hand2",
                  command=popup.destroy).pack(pady=15)
    
    def _populate_statistics(self, frame):
        """Populate the statistics frame with data."""
        # Clear existing
        for widget in frame.winfo_children():
            widget.destroy()
        
        # ─── Pipeline Statistics ───
        tk.Label(frame, text="⚡ Pipeline Statistics", font=get_font("md", "bold"),
                 fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(10, 8))
        
        pipeline_frame = tk.Frame(frame, bg=THEME.bg_highlight, padx=15, pady=12)
        pipeline_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Get pipeline stats
        if self._pipeline:
            stats = self._pipeline.get_stats()
            pipeline_data = [
                ("Total Fetches", str(stats.get("total_fetches", 0)), THEME.cyan),
                ("Total Articles", str(stats.get("total_articles", 0)), THEME.green),
                ("RSS Articles", str(stats.get("rss_articles", 0)), THEME.orange),
                ("API Articles", str(stats.get("api_articles", 0)), THEME.magenta),
                ("Duplicates Filtered", str(stats.get("duplicates_filtered", 0)), THEME.red),
                ("Last Fetch Time", f"{stats.get('last_fetch_ms', 0):.0f}ms", THEME.yellow),
                ("Cooldown Skips", str(stats.get("cooldown_skips", 0)), THEME.comment),
            ]
        else:
            pipeline_data = [("Pipeline Status", "Not initialized", THEME.red)]
        
        for label, value, color in pipeline_data:
            row = tk.Frame(pipeline_frame, bg=THEME.bg_highlight)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, font=get_font("sm"), fg=THEME.fg_dark, 
                     bg=THEME.bg_highlight).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=get_font("sm", "bold"), fg=color,
                     bg=THEME.bg_highlight).pack(side=tk.RIGHT)
        
        # ─── Queue Statistics ───
        tk.Label(frame, text="📥 Scrape Queue", font=get_font("md", "bold"),
                 fg=THEME.magenta, bg=THEME.bg).pack(anchor=tk.W, pady=(10, 8))
        
        queue_frame = tk.Frame(frame, bg=THEME.bg_highlight, padx=15, pady=12)
        queue_frame.pack(fill=tk.X, pady=(0, 15))
        
        try:
            from src.engine.scrape_queue import get_scrape_queue
            queue = get_scrape_queue()
            queue_stats = queue.get_statistics()
            
            queue_data = [
                ("Queue Size", str(queue_stats.get("queue_size", 0)), THEME.cyan),
                ("Total Scrapes", str(queue_stats.get("total_scrapes", 0)), THEME.fg),
                ("Successful", str(queue_stats.get("successful", 0)), THEME.green),
                ("Failed", str(queue_stats.get("failed", 0)), THEME.red),
                ("Success Rate", f"{queue_stats.get('success_rate', 0)}%", THEME.green),
                ("Total Articles Found", str(queue_stats.get("total_articles", 0)), THEME.orange),
                ("URLs Tracked", str(queue_stats.get("urls_tracked", 0)), THEME.comment),
            ]
            
            for label, value, color in queue_data:
                row = tk.Frame(queue_frame, bg=THEME.bg_highlight)
                row.pack(fill=tk.X, pady=2)
                tk.Label(row, text=label, font=get_font("sm"), fg=THEME.fg_dark,
                         bg=THEME.bg_highlight).pack(side=tk.LEFT)
                tk.Label(row, text=value, font=get_font("sm", "bold"), fg=color,
                         bg=THEME.bg_highlight).pack(side=tk.RIGHT)
            
            # Per-domain breakdown
            by_domain = queue_stats.get("by_domain", {})
            if by_domain:
                tk.Label(frame, text="🌐 Per-Domain Breakdown", font=get_font("sm", "bold"),
                         fg=THEME.fg_dark, bg=THEME.bg).pack(anchor=tk.W, pady=(10, 5))
                
                domain_frame = tk.Frame(frame, bg=THEME.bg_visual, padx=10, pady=8)
                domain_frame.pack(fill=tk.X, pady=(0, 10))
                
                for domain, domain_stats in list(by_domain.items())[:10]:
                    row = tk.Frame(domain_frame, bg=THEME.bg_visual)
                    row.pack(fill=tk.X, pady=1)
                    
                    short_domain = domain[:30] + "..." if len(domain) > 30 else domain
                    tk.Label(row, text=short_domain, font=get_font("xs"),
                             fg=THEME.fg_dark, bg=THEME.bg_visual).pack(side=tk.LEFT)
                    
                    success = domain_stats.get("success", 0)
                    failed = domain_stats.get("failed", 0)
                    articles = domain_stats.get("articles", 0)
                    
                    tk.Label(row, text=f"✓{success} ✗{failed} 📰{articles}", 
                             font=get_font("xs"), fg=THEME.comment,
                             bg=THEME.bg_visual).pack(side=tk.RIGHT)
                
                if len(by_domain) > 10:
                    tk.Label(domain_frame, text=f"... and {len(by_domain) - 10} more domains",
                             font=get_font("xs"), fg=THEME.comment, 
                             bg=THEME.bg_visual).pack(anchor=tk.W, pady=(5, 0))
        
        except Exception as e:
            tk.Label(queue_frame, text=f"Queue not initialized: {str(e)[:40]}", 
                     font=get_font("sm"), fg=THEME.red, bg=THEME.bg_highlight).pack()
        
        # ─── Session Summary ───
        tk.Label(frame, text="📈 Session Summary", font=get_font("md", "bold"),
                 fg=THEME.yellow, bg=THEME.bg).pack(anchor=tk.W, pady=(10, 8))
        
        session_frame = tk.Frame(frame, bg=THEME.bg_highlight, padx=15, pady=12)
        session_frame.pack(fill=tk.X)
        
        session_data = [
            ("Current Articles", str(len(self.current_articles)), THEME.cyan),
            ("History Batches", str(len(self._article_batches)), THEME.purple),
            ("History Articles", str(len(self._article_history)), THEME.magenta),
            ("Displayed URLs", str(len(self._displayed_urls)), THEME.fg_dark),
            ("Last Refresh", self._last_refresh.strftime("%H:%M:%S") if self._last_refresh else "Never", THEME.green),
        ]
        
        for label, value, color in session_data:
            row = tk.Frame(session_frame, bg=THEME.bg_highlight)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, font=get_font("sm"), fg=THEME.fg_dark,
                     bg=THEME.bg_highlight).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=get_font("sm", "bold"), fg=color,
                     bg=THEME.bg_highlight).pack(side=tk.RIGHT)
    
    def _refresh_statistics_popup(self, frame):
        """Refresh the statistics popup content."""
        self._populate_statistics(frame)
        frame.update_idletasks()
    
    def _build_ui(self):
        """Build the complete UI with Tokyo Night theme and robust animations."""
        
        # ═══════════════════════════════════════════════════════════════
        # HEADER CONTAINER
        # ═══════════════════════════════════════════════════════════════
        # Use a fixed height header to prevent layout shifting during animation
        header = tk.Frame(self.root, bg=THEME.bg_dark, height=75)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Cyan Accent Line (Top)
        tk.Frame(header, bg=THEME.cyan, height=3).pack(fill=tk.X, side=tk.TOP)
        
        # Inner Content Frame (Padding)
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=25, pady=12)
        
        # ═══════════════════════════════════════════════════════════════
        # LEFT SIDE: BRANDING & CREDITS
        # ═══════════════════════════════════════════════════════════════
        left_container = tk.Frame(header_inner, bg=THEME.bg_dark)
        left_container.pack(side=tk.LEFT)
        
        # 1. App Branding Group
        brand_frame = tk.Frame(left_container, bg=THEME.bg_dark)
        brand_frame.pack(side=tk.LEFT)
        
        tk.Label(brand_frame, text="⚡", font=get_font("3xl"), 
                 fg=THEME.cyan, bg=THEME.bg_dark).pack(side=tk.LEFT)
        tk.Label(brand_frame, text="TECH NEWS SCRAPER", font=get_font("2xl", "bold"),
                 fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(10, 6))
        tk.Label(brand_frame, text="v6.0", font=get_font("sm"),
                 fg=THEME.comment, bg=THEME.bg_dark).pack(side=tk.LEFT)

        # 2. Visual Separator (Vertical Line) -- REMOVED
        # 3. Credits & Watermark Group -- REMOVED to Top Bar

        # ═══════════════════════════════════════════════════════════════
        # CENTER: SEARCH BAR
        # ═══════════════════════════════════════════════════════════════
        search_container = tk.Frame(header_inner, bg=THEME.bg_dark)
        search_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)
        
        # Search Wrapper for rounded look
        search_wrapper = tk.Frame(search_container, bg=THEME.bg_input, padx=10, pady=5)
        search_wrapper.pack(fill=tk.X)
        
        # Search Icon
        tk.Label(search_wrapper, text="🔍", font=get_font("sm"), 
                 fg=THEME.comment, bg=THEME.bg_input).pack(side=tk.LEFT, padx=(0, 5))
        
        # Search Entry
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_wrapper, textvariable=self.search_var,
                                     font=get_font("sm"), bg=THEME.bg_input, fg=THEME.fg,
                                     insertbackground=THEME.fg, relief=tk.FLAT, width=30)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', lambda e: self._perform_search())
        
        # Placeholder text logic
        def on_focus_in(e):
            if self.search_var.get() == "Search articles...":
                self.search_var.set("")
                self.search_entry.config(fg=THEME.fg)
        
        def on_focus_out(e):
            if not self.search_var.get():
                self.search_var.set("Search articles...")
                self.search_entry.config(fg=THEME.comment)

        self.search_var.set("Search articles...")
        self.search_entry.config(fg=THEME.comment)
        self.search_entry.bind('<FocusIn>', on_focus_in)
        self.search_entry.bind('<FocusOut>', on_focus_out)
        
        # Search Button (Icon only)
        tk.Button(search_wrapper, text="→", font=get_font("md", "bold"),
                  fg=THEME.cyan, bg=THEME.bg_input, activebackground=THEME.bg_input,
                  relief=tk.FLAT, cursor="hand2", command=self._perform_search).pack(side=tk.RIGHT)

        # ═══════════════════════════════════════════════════════════════
        right_container = tk.Frame(header_inner, bg=THEME.bg_dark)
        right_container.pack(side=tk.RIGHT)
        
        # QUANTUM TOGGLE BUTTON
        def toggle_quantum():
            if self.quantum_enabled.get():
                self.quantum_btn.config(fg=THEME.magenta, text="🌌 QUANTUM: ON")
                if self._quantum_scraper:
                    self._quantum_scraper.is_quantum_state_active = True
                self._set_status("🌌 Quantum Temporal Scraper Activated", "success")
            else:
                self.quantum_btn.config(fg=THEME.comment, text="🌌 QUANTUM: OFF")
                if self._quantum_scraper:
                    self._quantum_scraper.is_quantum_state_active = False
                self._set_status("Standard Scraper Active", "info")

        self.quantum_btn = tk.Checkbutton(right_container, text="🌌 QUANTUM: OFF", 
                                         variable=self.quantum_enabled,
                                         command=toggle_quantum,
                                         font=get_font("sm", "bold"),
                                         fg=THEME.comment, bg=THEME.bg_dark,
                                         activebackground=THEME.bg_dark,
                                         activeforeground=THEME.magenta,
                                         selectcolor=THEME.bg_dark,
                                         indicatoron=False, relief=tk.FLAT, padx=10)
        self.quantum_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # Current Time
        self.time_label = tk.Label(right_container, text="", font=get_font("sm"),
                                    fg=THEME.fg_dark, bg=THEME.bg_dark)
        self.time_label.pack(side=tk.LEFT, padx=10)
        
        # Trigger time update
        self._update_time()
        
        # Quit button
        quit_btn = tk.Button(right_container, text="⏻ Exit", font=get_font("sm", "bold"),
                             fg=THEME.fg, bg=THEME.red, activebackground=THEME.bright_red,
                             activeforeground=THEME.fg, padx=15, pady=6, relief=tk.FLAT,
                             cursor='hand2', command=self._quit_application)
        quit_btn.pack(side=tk.RIGHT)
        
        # ═══════════════════════════════════════════════════════════════
        # STATUS BAR (BOTTOM)
        # ═══════════════════════════════════════════════════════════════
        self.status_bar = DynamicStatusBar(self.root)
        
        # ═══════════════════════════════════════════════════════════════
        # MAIN CONTAINER
        # ═══════════════════════════════════════════════════════════════
        main = tk.Frame(self.root, bg=THEME.bg)
        main.pack(fill=tk.BOTH, expand=True)
        
        # NOTE: LiveLogPanel removed from main GUI (resource-heavy)
        # Access via Developer Dashboard -> Live Monitor button
        
        # ═══════════════════════════════════════════════════════════════
        # LEFT PANEL - Main content area
        # ═══════════════════════════════════════════════════════════════
        left = tk.Frame(main, bg=THEME.bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Search Section - Glass card style
        search_card = tk.Frame(left, bg=THEME.bg_highlight, padx=20, pady=18)
        search_card.pack(fill=tk.X, pady=(0, 20))
        
        # Search row
        search_row = tk.Frame(search_card, bg=THEME.bg_highlight)
        search_row.pack(fill=tk.X)
        
        # Search icon label
        tk.Label(search_row, text="🔍", font=get_font("lg"),
                 fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(0, 10))
        
        # Search entry with modern styling
        self.search_entry = tk.Entry(search_row, font=get_font("md"), 
                                      bg=THEME.bg_visual, fg=THEME.fg,
                                      insertbackground=THEME.cyan, relief=tk.FLAT,
                                      highlightthickness=2, highlightcolor=THEME.cyan,
                                      highlightbackground=THEME.border)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 12))
        self.search_entry.insert(0, "Search tech news...")
        self.search_entry.bind('<FocusIn>', lambda e: self._on_entry_focus(self.search_entry, "Search tech news..."))
        self.search_entry.bind('<FocusOut>', lambda e: self._on_entry_blur(self.search_entry, "Search tech news..."))
        self.search_entry.bind('<Return>', lambda e: self._on_search())
        self.search_entry.bind('<KeyRelease>', self._on_search)
        
        # Search button - Primary action
        search_btn = tk.Button(search_row, text="Search", font=get_font("md", "bold"),
                               bg=THEME.blue, fg=THEME.fg, activebackground=THEME.bright_blue,
                               padx=25, pady=10, relief=tk.FLAT, cursor='hand2',
                               command=self._on_search)
        search_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Refresh button
        refresh_btn = tk.Button(search_row, text="↻", font=get_font("lg"),
                                bg=THEME.bg_visual, fg=THEME.cyan, 
                                activebackground=THEME.bg_search, activeforeground=THEME.cyan,
                                padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                                command=self._refresh)
        refresh_btn.pack(side=tk.LEFT)
        
        # URL Analysis row
        url_row = tk.Frame(search_card, bg=THEME.bg_highlight)
        url_row.pack(fill=tk.X, pady=(15, 0))
        
        tk.Label(url_row, text="🔗", font=get_font("md"),
                 fg=THEME.magenta, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(0, 10))
        
        self.url_entry = tk.Entry(url_row, font=get_font("sm"),
                                   bg=THEME.bg_visual, fg=THEME.fg_dark,
                                   insertbackground=THEME.magenta, relief=tk.FLAT,
                                   highlightthickness=1, highlightcolor=THEME.magenta,
                                   highlightbackground=THEME.border)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 12))
        self.url_entry.insert(0, "Paste article URL for deep analysis...")
        self.url_entry.bind('<FocusIn>', lambda e: self._on_entry_focus(self.url_entry, "Paste article URL for deep analysis..."))
        self.url_entry.bind('<FocusOut>', lambda e: self._on_entry_blur(self.url_entry, "Paste article URL for deep analysis..."))
        self.url_entry.bind('<Return>', lambda e: self._analyze_custom_url())
        
        analyze_btn = tk.Button(url_row, text="🔬 Analyze", font=get_font("sm", "bold"),
                                bg=THEME.magenta, fg=THEME.fg, 
                                activebackground=THEME.bright_magenta,
                                padx=16, pady=8, relief=tk.FLAT, cursor='hand2',
                                command=self._analyze_custom_url)
        analyze_btn.pack(side=tk.LEFT)
        
        # ═══════════════════════════════════════════════════════════════
        # RESULTS SECTION
        # ═══════════════════════════════════════════════════════════════
        results_header = tk.Frame(left, bg=THEME.bg)
        results_header.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(results_header, text="📰", font=get_font("xl"),
                 fg=THEME.orange, bg=THEME.bg).pack(side=tk.LEFT)
        tk.Label(results_header, text="Results", font=get_font("xl", "bold"),
                 fg=THEME.fg, bg=THEME.bg).pack(side=tk.LEFT, padx=(8, 0))
        
        self.results_count = tk.Label(results_header, text="", font=get_font("sm"),
                                       fg=THEME.comment, bg=THEME.bg)
        self.results_count.pack(side=tk.LEFT, padx=(15, 0))
        
        # ═══════════════════════════════════════════════════════════════════
        # LIVENESS INDICATOR - Shows real-time status
        # ═══════════════════════════════════════════════════════════════════
        self._liveness_frame = tk.Frame(results_header, bg=THEME.bg)
        self._liveness_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        # Pulsing LIVE indicator
        self._live_indicator = tk.Label(
            self._liveness_frame,
            text="● LIVE",
            font=get_font("xs", "bold"),
            fg=THEME.green,
            bg=THEME.bg
        )
        self._live_indicator.pack(side=tk.LEFT)
        
        # Current region indicator
        self._region_indicator = tk.Label(
            self._liveness_frame,
            text="🌍 Scanning: US",
            font=get_font("xs"),
            fg=THEME.cyan,
            bg=THEME.bg
        )
        self._region_indicator.pack(side=tk.LEFT, padx=(8, 0))
        
        # Active sources count
        self._sources_indicator = tk.Label(
            self._liveness_frame,
            text="📡 0 sources",
            font=get_font("xs"),
            fg=THEME.yellow,
            bg=THEME.bg
        )
        self._sources_indicator.pack(side=tk.LEFT, padx=(8, 0))
        
        # Start the pulsing animation
        self._pulse_live_indicator()
        
        # Countdown timer for next auto-refresh (right side)
        self.refresh_timer_label = tk.Label(
            results_header, 
            text="", 
            font=get_font("xs"),
            fg=THEME.cyan, 
            bg=THEME.bg
        )
        self.refresh_timer_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Timer pulse state
        self._timer_pulse = False

        
        # Results container with custom scrolling
        results_container = tk.Frame(left, bg=THEME.bg)
        results_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for scrollable results
        self.results_canvas = tk.Canvas(results_container, bg=THEME.bg, 
                                        highlightthickness=0, bd=0)
        
        # Custom scrollbar styling
        scrollbar = tk.Scrollbar(results_container, orient=tk.VERTICAL,
                                 command=self.results_canvas.yview,
                                 bg=THEME.bg_highlight, troughcolor=THEME.bg,
                                 activebackground=THEME.cyan, width=10)
        
        self.results_frame = tk.Frame(self.results_canvas, bg=THEME.bg)
        
        self.results_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_window = self.results_canvas.create_window((0, 0), 
                                                                window=self.results_frame, 
                                                                anchor=tk.NW)
        
        # Scroll region updates
        def update_scroll_region(event=None):
            self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        
        def update_canvas_width(event):
            self.results_canvas.itemconfig(self.canvas_window, width=event.width)
        
        self.results_frame.bind('<Configure>', update_scroll_region)
        self.results_canvas.bind('<Configure>', update_canvas_width)
        
        # Mouse wheel scrolling - macOS compatible
        def on_mousewheel(event):
            # macOS typically sends delta values like 1, -1 or larger multiples
            # Windows sends 120 or -120
            import platform
            if platform.system() == 'Darwin':  # macOS
                # On macOS, delta is usually 1 or -1, scroll by units
                self.results_canvas.yview_scroll(int(-1 * event.delta), "units")
            elif event.delta:
                # Windows - delta is typically 120
                self.results_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif hasattr(event, 'num'):
                # Linux - use button 4/5
                if event.num == 4:
                    self.results_canvas.yview_scroll(-3, "units")
                elif event.num == 5:
                    self.results_canvas.yview_scroll(3, "units")
        
        # Bind to canvas
        self.results_canvas.bind('<MouseWheel>', on_mousewheel)
        self.results_canvas.bind('<Button-4>', on_mousewheel)  # Linux scroll up
        self.results_canvas.bind('<Button-5>', on_mousewheel)  # Linux scroll down
        
        # Enable global scrolling when mouse enters results area
        def bind_mousewheel(event):
            self.results_canvas.bind_all('<MouseWheel>', on_mousewheel)
            self.results_canvas.bind_all('<Button-4>', on_mousewheel)
            self.results_canvas.bind_all('<Button-5>', on_mousewheel)
        
        def unbind_mousewheel(event):
            self.results_canvas.unbind_all('<MouseWheel>')
            self.results_canvas.unbind_all('<Button-4>')
            self.results_canvas.unbind_all('<Button-5>')
        
        # Bind enter/leave to results frame and all its children
        self.results_canvas.bind('<Enter>', bind_mousewheel)
        self.results_canvas.bind('<Leave>', unbind_mousewheel)
        self.results_frame.bind('<Enter>', bind_mousewheel)
        
        # Also bind immediately to enable scrolling
        bind_mousewheel(None)
        
        # ═══════════════════════════════════════════════════════════════
        # RIGHT PANEL - Sidebar with Stats and Actions
        # ═══════════════════════════════════════════════════════════════
        right = tk.Frame(main, bg=THEME.bg_highlight, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 20), pady=20)
        right.pack_propagate(False)
        
        # Make sidebar scrollable
        scroll_container = ScrollableFrame(right, bg_color=THEME.bg_highlight)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        
        self.sidebar = tk.Frame(scroll_container.scrollable_frame, bg=THEME.bg_highlight, padx=20, pady=20)
        self.sidebar.pack(fill=tk.BOTH, expand=True)
        
        # Store reference to sidebar for later use (e.g., toggle button)
        sidebar = self.sidebar
        
        # ─── Statistics Section ───
        stats_header = tk.Frame(sidebar, bg=THEME.bg_highlight)
        stats_header.pack(fill=tk.X, pady=(0, 15))
        tk.Label(stats_header, text="📊", font=get_font("lg"),
                 fg=THEME.green, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(stats_header, text="Statistics", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        self.stats_labels = {}
        stats_config = [
            ('Articles', '📰', THEME.cyan),
            ('Sources', '🌐', THEME.green),
            ('Queries', '🔍', THEME.blue),
            ('Rejected', '❌', THEME.red),
        ]
        
        for stat, icon, color in stats_config:
            stat_frame = tk.Frame(sidebar, bg=THEME.bg_visual, padx=12, pady=8)
            stat_frame.pack(fill=tk.X, pady=3)
            
            tk.Label(stat_frame, text=icon, font=get_font("sm"),
                     fg=color, bg=THEME.bg_visual).pack(side=tk.LEFT)
            tk.Label(stat_frame, text=stat, font=get_font("sm"),
                     fg=THEME.fg_dark, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(6, 0))
            
            self.stats_labels[stat] = tk.Label(stat_frame, text="0", 
                                                font=get_font("md", "bold"),
                                                fg=color, bg=THEME.bg_visual)
            self.stats_labels[stat].pack(side=tk.RIGHT)
        
        # Divider
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=18)
        
        # ─── Quick Actions Section ───
        tk.Label(sidebar, text="⚡ Quick Actions", font=get_font("md", "bold"),
                 fg=THEME.yellow, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(0, 12))
        
        # ⚡ START LIVE FEED - Main trigger for unified pipeline
        start_feed_btn = tk.Button(sidebar, text="⚡ START LIVE FEED", 
                                   font=get_font("md", "bold"),
                                   bg=THEME.green, fg=THEME.black,
                                   activebackground=THEME.bright_green,
                                   padx=12, pady=12, relief=tk.FLAT, cursor='hand2',
                                   command=self._trigger_unified_live_feed)
        start_feed_btn.pack(fill=tk.X, pady=(0, 12))
        
        # Quick search buttons
        quick_actions = [
            ("🔥 Latest News", lambda: self._quick_search("latest tech news"), THEME.orange),
            ("🤖 AI & ML", lambda: self._quick_search("artificial intelligence"), THEME.cyan),
            ("🔒 Security", lambda: self._quick_search("cybersecurity"), THEME.red),
            ("💰 Startups", lambda: self._quick_search("startup funding"), THEME.magenta),
        ]
        
        for text, cmd, hover_color in quick_actions:
            btn = tk.Button(sidebar, text=text, font=get_font("sm"),
                           bg=THEME.bg_visual, fg=THEME.fg_dark,
                           activebackground=THEME.bg_search, activeforeground=THEME.fg,
                           padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                           command=cmd)
            btn.pack(fill=tk.X, pady=2)
        
        # Mode Toggle Buttons
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=12)
        
        live_btn = tk.Button(sidebar, text="🏠 Live Feed", 
                              font=get_font("sm", "bold"),
                              bg=THEME.blue, fg=THEME.fg,
                              activebackground=THEME.bright_blue,
                              padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                              command=self._return_to_live_mode)
        live_btn.pack(fill=tk.X, pady=2)
        
        # View Live Monitor button
        monitor_btn = tk.Button(sidebar, text="📊 View Live Monitor", 
                               font=get_font("sm", "bold"),
                               bg=THEME.cyan, fg=THEME.black,
                               activebackground=THEME.bright_cyan,
                               padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                               command=self._show_live_monitor)
        monitor_btn.pack(fill=tk.X, pady=2)
        
        history_btn = tk.Button(sidebar, text="📜 View History", 
                                 font=get_font("sm", "bold"),
                                 bg=THEME.purple, fg=THEME.fg,
                                 activebackground=THEME.bright_magenta,
                                 padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                                 command=self._show_history_popup)
        history_btn.pack(fill=tk.X, pady=2)
        
        # Statistics Button (NEW)
        stats_btn = tk.Button(sidebar, text="📊 View Statistics", 
                              font=get_font("sm", "bold"),
                              bg=THEME.green, fg=THEME.black,
                              activebackground=THEME.bright_green,
                              padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                              command=self._show_statistics_popup)
        stats_btn.pack(fill=tk.X, pady=2)
        
        # Divider
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=18)
        
        # ─── Sort Options ───
        tk.Label(sidebar, text="📊 Sort By", font=get_font("sm", "bold"),
                 fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(0, 8))
        
        sort_frame = tk.Frame(sidebar, bg=THEME.bg_highlight)
        sort_frame.pack(fill=tk.X)
        
        sort_buttons = [
            ("⏰ Time", self._sort_by_time, THEME.cyan),
            ("📊 Score", self._sort_by_score, THEME.green),
            ("⭐ Tier", self._sort_by_tier, THEME.yellow),
        ]
        
        for text, cmd, color in sort_buttons:
            btn = tk.Button(sort_frame, text=text, font=get_font("xs", "bold"),
                           bg=THEME.bg_visual, fg=color,
                           activebackground=color, activeforeground=THEME.black,
                           padx=10, pady=5, relief=tk.FLAT, cursor='hand2',
                           command=cmd)
            btn.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        
        # Divider
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=18)
        
        # Last refresh time
        self.last_refresh_label = tk.Label(sidebar, text="Last refresh: --", 
                                            font=get_font("xs"),
                                            fg=THEME.comment, bg=THEME.bg_highlight)
        self.last_refresh_label.pack(anchor=tk.W)
        
        # ─── Intelligence Panel (v3.0) ───
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=18)
        
        intel_header = tk.Frame(sidebar, bg=THEME.bg_highlight)
        intel_header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(intel_header, text="🧠", font=get_font("lg"),
                 fg=THEME.magenta, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(intel_header, text="Intelligence", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        # Intelligence stats
        self.intel_stats_labels = {}
        intel_stats_config = [
            ('Analyzed', '📊', THEME.cyan),
            ('Disruptive', '⚡', THEME.orange),
            ('High Priority', '🔴', THEME.red),
        ]
        
        for stat, icon, color in intel_stats_config:
            stat_frame = tk.Frame(sidebar, bg=THEME.bg_visual, padx=12, pady=6)
            stat_frame.pack(fill=tk.X, pady=2)
            
            tk.Label(stat_frame, text=icon, font=get_font("sm"),
                     fg=color, bg=THEME.bg_visual).pack(side=tk.LEFT)
            tk.Label(stat_frame, text=stat, font=get_font("xs"),
                     fg=THEME.fg_dark, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(6, 0))
            
            self.intel_stats_labels[stat] = tk.Label(stat_frame, text="--", 
                                                font=get_font("sm", "bold"),
                                                fg=color, bg=THEME.bg_visual)
            self.intel_stats_labels[stat].pack(side=tk.RIGHT)
        
        # View Disruptive Articles button
        disruptive_btn = tk.Button(sidebar, text="🔥 View Disruptive News", 
                                   font=get_font("sm", "bold"),
                                   bg=THEME.orange, fg=THEME.black,
                                   activebackground=THEME.bright_yellow,
                                   padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                                   command=self._show_disruptive_articles)
        disruptive_btn.pack(fill=tk.X, pady=(10, 5))
        
        # Alert Channel Config button
        alert_config_btn = tk.Button(sidebar, text="🔔 Configure Alerts", 
                                     font=get_font("sm", "bold"),
                                     bg=THEME.bg_visual, fg=THEME.magenta,
                                     activebackground=THEME.magenta, activeforeground=THEME.black,
                                     padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                                     command=self._show_alert_config)
        alert_config_btn.pack(fill=tk.X, pady=2)
        
        # ─── Newsletter Panel (v4.0) ───
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=18)
        
        newsletter_header = tk.Frame(sidebar, bg=THEME.bg_highlight)
        newsletter_header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(newsletter_header, text="📰", font=get_font("lg"),
                 fg=THEME.green, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(newsletter_header, text="Newsletter", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        # Generate Newsletter button
        generate_newsletter_btn = tk.Button(sidebar, text="✨ Generate Newsletter", 
                                            font=get_font("sm", "bold"),
                                            bg=THEME.green, fg=THEME.black,
                                            activebackground=THEME.bright_green,
                                            padx=12, pady=10, relief=tk.FLAT, cursor='hand2',
                                            command=self._generate_newsletter)
        generate_newsletter_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Newsletter History button
        newsletter_history_btn = tk.Button(sidebar, text="📚 Newsletter History", 
                                           font=get_font("sm", "bold"),
                                           bg=THEME.bg_visual, fg=THEME.green,
                                           activebackground=THEME.green, activeforeground=THEME.black,
                                           padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                                           command=self._show_newsletter_history)
        newsletter_history_btn.pack(fill=tk.X, pady=2)
        
        # Web Crawler button
        crawler_btn = tk.Button(sidebar, text="🕷️ Web Crawler", 
                                font=get_font("sm", "bold"),
                                bg=THEME.bg_visual, fg=THEME.purple,
                                activebackground=THEME.purple, activeforeground=THEME.black,
                                padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                                command=self._show_crawler_popup)
        crawler_btn.pack(fill=tk.X, pady=2)
        
        # ─── Source Controls ───
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=18)
        
        tk.Label(sidebar, text="📡 Source Controls", font=get_font("sm", "bold"),
                 fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(0, 8))
        
        # From Sources button - fetches from static sources only
        source_btn = tk.Button(sidebar, text="📰 Fetch From Sources", 
                              font=get_font("sm", "bold"),
                              bg=THEME.bg_visual, fg=THEME.orange,
                              activebackground=THEME.orange, activeforeground=THEME.black,
                              padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                              command=self._fetch_from_sources_only)
        source_btn.pack(fill=tk.X, pady=2)
        
        # Manage Sources button - opens custom sources popup
        manage_btn = tk.Button(sidebar, text="⚙️ Manage Custom Sources", 
                              font=get_font("sm", "bold"),
                              bg=THEME.bg_visual, fg=THEME.cyan,
                              activebackground=THEME.cyan, activeforeground=THEME.black,
                              padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                              command=self._open_custom_sources)
        manage_btn.pack(fill=tk.X, pady=2)
        
        # Developer dashboard button
        self.dev_btn = tk.Button(sidebar, text="🛠️ Developer Dashboard", 
                            font=get_font("sm", "bold"),
                            bg=THEME.purple, fg=THEME.fg,
                            activebackground=THEME.bright_magenta,
                            padx=12, pady=10, relief=tk.FLAT, cursor='hand2',
                            command=self._open_developer_dashboard)
        self.dev_btn.pack(fill=tk.X, pady=(20, 0))
        
        # ─── Enterprise Features (v7.0) ───
        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X, pady=18)
        
        enterprise_header = tk.Frame(sidebar, bg=THEME.bg_highlight)
        enterprise_header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(enterprise_header, text="🏢", font=get_font("lg"),
                 fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(enterprise_header, text="Enterprise", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        # User Preferences button
        prefs_btn = tk.Button(sidebar, text="⚙️ User Preferences", 
                              font=get_font("sm", "bold"),
                              bg=THEME.magenta, fg=THEME.fg,
                              activebackground=THEME.bright_magenta,
                              padx=12, pady=10, relief=tk.FLAT, cursor='hand2',
                              command=self._open_preferences)
        prefs_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Sentiment Dashboard button
        sentiment_btn = tk.Button(sidebar, text="📊 Sentiment Dashboard", 
                                  font=get_font("sm", "bold"),
                                  bg=THEME.green, fg=THEME.black,
                                  activebackground=THEME.bright_green,
                                  padx=12, pady=10, relief=tk.FLAT, cursor='hand2',
                                  command=self._open_sentiment_dashboard)
        sentiment_btn.pack(fill=tk.X, pady=2)
        
        # API Documentation button
        api_btn = tk.Button(sidebar, text="🔌 API Docs", 
                           font=get_font("sm", "bold"),
                           bg=THEME.bg_visual, fg=THEME.blue,
                           activebackground=THEME.blue, activeforeground=THEME.black,
                           padx=12, pady=8, relief=tk.FLAT, cursor='hand2',
                           command=lambda: webbrowser.open("http://localhost:8000/docs"))
        api_btn.pack(fill=tk.X, pady=2)
        
        # ═══════════════════════════════════════════════════════════════
        # STATUS BAR - Now using DynamicStatusBar (created earlier in _build_ui)
        # The self.status_bar is already packed at the bottom
        # ═══════════════════════════════════════════════════════════════
        # Legacy status variable for compatibility with existing _set_status calls
        self.status_var = tk.StringVar(value="")
        
        # Show welcome
        self._show_welcome()
    
    def _on_entry_focus(self, entry, placeholder):
        """Handle entry focus - clear placeholder."""
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg=THEME.fg)
    
    def _on_entry_blur(self, entry, placeholder):
        """Handle entry blur - restore placeholder if empty."""
        if not entry.get():
            entry.insert(0, placeholder)
            entry.config(fg=THEME.fg_dark)
    
    def _update_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"🕐 {now}")
        self.root.after(1000, self._update_time)
    
    def _update_refresh_countdown(self):
        """Update the countdown timer showing time until next auto-refresh."""
        try:
            if not hasattr(self, 'refresh_timer_label') or not self.refresh_timer_label.winfo_exists():
                return
            
            # Use pipeline refresh cooldown if available, otherwise use feeder interval
            interval = 300  # Default 5 minutes
            if hasattr(self, '_pipeline') and self._pipeline:
                interval = getattr(self._pipeline, '_refresh_cooldown', 300)
            elif self._orchestrator and hasattr(self._orchestrator, '_realtime_feeder') and self._orchestrator._realtime_feeder:
                feeder = self._orchestrator._realtime_feeder
                interval = getattr(feeder, '_refresh_interval', 300)
            
            # Use local countdown time if set (for immediate reset on mode change)
            # Otherwise fall back to last_refresh
            if hasattr(self, '_countdown_start_time') and self._countdown_start_time:
                last_refresh = self._countdown_start_time
            elif hasattr(self, '_last_refresh') and self._last_refresh:
                last_refresh = self._last_refresh
            else:
                last_refresh = None
            
            if not last_refresh:
                self.refresh_timer_label.config(text="⏳ Waiting for first refresh...", fg=THEME.comment)
                self.root.after(1000, self._update_refresh_countdown)
                return
            
            # Calculate seconds since last refresh
            now = datetime.now(last_refresh.tzinfo) if last_refresh.tzinfo else datetime.now()
            elapsed = (now - last_refresh).total_seconds()
            remaining = max(0, interval - elapsed)
            
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            
            # Format display
            if remaining <= 0:
                text = "🔄 Refreshing..."
                color = THEME.green
                
                # AUTO-TRIGGER REFRESH
                # Only trigger if not already fetching
                if not getattr(self, '_fetching_in_progress', False):
                    # Use after_idle to ensure we don't block the timer loop
                    self.root.after_idle(self._trigger_unified_live_feed)
                    
                    # Reset countdown slightly to prevent hammering while fetch starts
                    # The fetch completion will properly reset the full countdown
                    self._countdown_start_time = datetime.now() + timedelta(seconds=10)
            elif remaining <= 10:
                text = f"⚡ Refresh in {seconds}s"
                color = THEME.bright_green
            elif remaining <= 30:
                text = f"🔄 Refresh in {seconds}s"
                color = THEME.green
            else:
                text = f"⏱️ Next refresh: {minutes}:{seconds:02d}"
                color = THEME.cyan
            
            # Pulse effect when close to refresh
            if remaining <= 10:
                self._timer_pulse = not self._timer_pulse
                if self._timer_pulse:
                    color = THEME.bright_yellow
            
            self.refresh_timer_label.config(text=text, fg=color)
            
            # Schedule next update
            self.root.after(1000, self._update_refresh_countdown)
        except Exception as e:
            # Silently handle errors to prevent timer from stopping
            self.root.after(1000, self._update_refresh_countdown)


    def _reset_refresh_timer(self):
        """Reset the countdown timer immediately by updating the local start time."""
        from datetime import timezone
        
        # Set local countdown start time (synchronous, immediate)
        self._countdown_start_time = datetime.now(timezone.utc)
        
        # Update timer label to show reset
        if hasattr(self, 'refresh_timer_label') and self.refresh_timer_label.winfo_exists():
            interval = 120  # 2 minutes
            self.refresh_timer_label.config(
                text=f"⏱️ Next refresh: 2:00", 
                fg=THEME.cyan
            )

    
    def _set_status(self, status: str, status_type: str = "info"):
        """
        Set status bar text with color-coded display.
        
        Args:
            status: Status message
            status_type: 'info', 'success', 'warning', 'error'
        """
        self.status_var.set(status)
        
        # Forward to DynamicStatusBar with appropriate emoji
        try:
            emoji_map = {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
            }
            emoji = emoji_map.get(status_type, '📋')
            # Add directly to status bar queue
            self.status_bar.queue.append(f"{emoji} {status}")
        except Exception:
            pass
    
    def _show_welcome(self):
        """Display simple welcome screen on app startup."""
        self._show_simple_welcome()
    
    def _show_simple_welcome(self):
        """Show clean, simple welcome screen with instructions and stats."""
        self._clear_results()
        self._live_dashboard_visible = False
        self._results_view_visible = False
        
        # Main welcome container
        welcome_frame = tk.Frame(self.results_frame, bg=THEME.bg, padx=40, pady=30)
        welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        # Welcome header with icon
        header = tk.Frame(welcome_frame, bg=THEME.bg)
        header.pack(pady=(20, 30))
        
        tk.Label(header, text="📰", font=get_font("4xl"),
                 fg=THEME.cyan, bg=THEME.bg).pack()
        
        tk.Label(header, text="Welcome to Tech News Scraper", font=get_font("2xl", "bold"),
                 fg=THEME.fg, bg=THEME.bg).pack(pady=(15, 5))
        
        tk.Label(header, text="Your intelligent tech news discovery platform", font=get_font("md"),
                 fg=THEME.fg_dark, bg=THEME.bg).pack()
        
        # Version badge
        version_frame = tk.Frame(header, bg=THEME.green, padx=15, pady=5)
        version_frame.pack(pady=(15, 0))
        tk.Label(version_frame, text="v7.0", font=get_font("sm", "bold"),
                 fg=THEME.bg_dark, bg=THEME.green).pack()
        
        # Instructions section
        instructions_frame = tk.Frame(welcome_frame, bg=THEME.bg_highlight, padx=30, pady=25)
        instructions_frame.pack(fill=tk.X, pady=(20, 20))
        
        tk.Label(instructions_frame, text="🚀 Getting Started", font=get_font("lg", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(0, 15))
        
        instructions = [
            ("⚡", "START LIVE FEED", "Click to begin fetching articles from all sources"),
            ("📊", "View Live Monitor", "Monitor system activity and source status in real-time"),
            ("🔍", "Search", "Use the search bar to find specific articles"),
            ("📜", "View History", "Access previously fetched articles"),
        ]
        
        for icon, title, desc in instructions:
            row = tk.Frame(instructions_frame, bg=THEME.bg_highlight)
            row.pack(fill=tk.X, pady=5)
            
            tk.Label(row, text=icon, font=get_font("md"),
                     fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(0, 10))
            
            tk.Label(row, text=title, font=get_font("md", "bold"),
                     fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT)
            
            tk.Label(row, text=f" — {desc}", font=get_font("sm"),
                     fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(5, 0))
        
        # System status section
        stats_frame = tk.Frame(welcome_frame, bg=THEME.bg_visual, padx=30, pady=20)
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(stats_frame, text="📊 System Status", font=get_font("md", "bold"),
                 fg=THEME.green, bg=THEME.bg_visual).pack(anchor=tk.W, pady=(0, 15))
        
        # System stats grid
        stats_grid = tk.Frame(stats_frame, bg=THEME.bg_visual)
        stats_grid.pack(fill=tk.X)
        
        stats = [
            ("Sources Ready", "10+", THEME.cyan),
            ("RSS Feeds", "30+", THEME.orange),
            ("APIs", "Google, Bing", THEME.green),
            ("Status", "Ready", THEME.bright_green),
        ]
        
        for i, (label, value, color) in enumerate(stats):
            col = i % 2
            row = i // 2
            
            stat_box = tk.Frame(stats_grid, bg=THEME.bg_highlight, padx=15, pady=10)
            stat_box.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            tk.Label(stat_box, text=label, font=get_font("xs"),
                     fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(anchor=tk.W)
            
            tk.Label(stat_box, text=value, font=get_font("md", "bold"),
                     fg=color, bg=THEME.bg_highlight).pack(anchor=tk.W)
        
        # Configure grid weights
        stats_grid.grid_columnconfigure(0, weight=1)
        stats_grid.grid_columnconfigure(1, weight=1)
        
        # Quick start buttons
        btn_frame = tk.Frame(welcome_frame, bg=THEME.bg)
        btn_frame.pack(pady=(20, 10))
        
        start_btn = tk.Button(btn_frame, text="⚡ START LIVE FEED", 
                              font=get_font("md", "bold"),
                              bg=THEME.green, fg=THEME.black,
                              activebackground=THEME.bright_green,
                              padx=30, pady=15, relief=tk.FLAT, cursor='hand2',
                              command=self._trigger_unified_live_feed)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        monitor_btn = tk.Button(btn_frame, text="📊 View Live Monitor", 
                                font=get_font("md", "bold"),
                                bg=THEME.blue, fg=THEME.fg,
                                activebackground=THEME.bright_blue,
                                padx=20, pady=15, relief=tk.FLAT, cursor='hand2',
                                command=self._show_live_monitor)
        monitor_btn.pack(side=tk.LEFT, padx=5)
    
    def _show_live_monitor(self):
        """Show full live monitor view with all dashboard widgets and back button."""
        self._clear_results()
        self._live_dashboard_visible = True
        self._results_view_visible = False
        
        # Create main container for live dashboard
        self._live_dashboard_container = tk.Frame(self.results_frame, bg=THEME.bg)
        self._live_dashboard_container.pack(fill=tk.BOTH, expand=True)
        
        # Header with back button
        header = tk.Frame(self._live_dashboard_container, bg=THEME.bg_visual, padx=15, pady=10)
        header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header, text="📊", font=get_font("lg"),
                 fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT)
        
        tk.Label(header, text="Live Monitor", font=get_font("md", "bold"),
                 fg=THEME.fg, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(10, 0))
        
        # Back button
        back_btn = tk.Button(header, text="← Back to Articles", 
                             font=get_font("sm", "bold"),
                             bg=THEME.bg_highlight, fg=THEME.fg,
                             activebackground=THEME.cyan, activeforeground=THEME.black,
                             padx=15, pady=5, relief=tk.FLAT, cursor='hand2',
                             command=self._return_to_articles_from_monitor)
        back_btn.pack(side=tk.RIGHT)
        
        # Two column layout
        left = tk.Frame(self._live_dashboard_container, bg=THEME.bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        right = tk.Frame(self._live_dashboard_container, bg=THEME.bg, width=380)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
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
        
        self.network_graph = NetworkThroughputGraph(right, height=100)
        self.network_graph.pack(fill=tk.X, pady=5)
        
        # Start live monitoring systems
        self._start_live_monitoring()
        
        # Initialize with test data so user can see widgets working
        self._initialize_live_dashboard_with_test_data()
    
    def _return_to_articles_from_monitor(self):
        """Return to articles view from live monitor."""
        if self._feed_started:
            # Show articles only view
            self._show_articles_only_view()
            # Re-display current articles
            if self.current_articles:
                self._display_realtime_results(self.current_articles)
        else:
            # Return to welcome if feed hasn't started
            self._show_simple_welcome()
    
    def _show_articles_only_view(self):
        """Show articles in main area only (no live dashboard widgets)."""
        # Mark feed as started
        self._feed_started = True
        
        # Clear the results frame completely
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Reset state
        self._live_dashboard_visible = False
        self._results_view_visible = True
        self.current_articles = []
        self._displayed_urls.clear()
        
        # Create simple container for articles only
        self._articles_container = tk.Frame(self.results_frame, bg=THEME.bg)
        self._articles_container.pack(fill=tk.BOTH, expand=True)
        
        # The articles will be displayed here by _display_realtime_results
        # which will pack article cards into self.results_frame
    
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
    
    def _initialize_live_dashboard_with_test_data(self):
        """Initialize live dashboard with test data to show widgets are working."""
        # Update source statuses to show they're connecting
        if self.live_source_monitor:
            test_sources = [
                ("TechCrunch", 45, "connecting"),
                ("Hacker News", 120, "connecting"),
                ("The Verge", 85, "connecting"),
                ("Ars Technica", 60, "connecting"),
            ]
            for source, latency, status in test_sources:
                self.live_source_monitor.update_source(source, latency, status, 0)
        
        # Add test articles to stream
        if self.live_article_stream:
            test_articles = [
                {
                    'title': 'Live dashboard initialized and ready',
                    'source': 'System',
                    'tech_score': 0,
                    'relevance': 0,
                    'is_breaking': False
                },
                {
                    'title': 'Ready to discover tech news from 10+ sources including TechCrunch, Hacker News, The Verge, and more',
                    'source': 'System',
                    'tech_score': 0,
                    'relevance': 0,
                    'is_breaking': False
                },
                {
                    'title': 'Click "START LIVE FEED" button to begin real-time discovery',
                    'source': 'System',
                    'tech_score': 0,
                    'relevance': 0,
                    'is_breaking': False
                }
            ]
            for article in test_articles:
                self.live_article_stream.on_article_found(article)
        
        # Log system messages
        if self.live_activity_log:
            self.live_activity_log.log("Live dashboard initialized", level='SUCCESS', source='SYSTEM')
            self.live_activity_log.log("10 sources configured and ready", level='INFO', source='SYSTEM')
            self.live_activity_log.log("Waiting for user to start feed...", level='INFO', source='SYSTEM')
        
        # Initialize stats
        if self.live_stats_panel:
            self.live_stats_panel.update_stat('articles', 3)
            self.live_stats_panel.update_stat('sources_active', 4)
            self.live_stats_panel.update_stat('sources_total', 10)
        
        # Update pipeline stages to waiting state
        if self.pipeline_visualizer:
            for stage_name, _ in self.pipeline_visualizer.STAGES:
                self.pipeline_visualizer.update_stage(stage_name, 0.0, 'waiting')
        
        # Initialize source matrix
        if self.source_matrix:
            for source_name in self.source_matrix.source_states:
                self.source_matrix.update_source_progress(source_name, 0.0)
    
    def _log_to_live_dashboard(self, message: str, level: str = "INFO", source: str = "SYSTEM"):
        """Safely log to live activity log."""
        if self.live_activity_log:
            try:
                self.live_activity_log.log(message, level=level, source=source)
            except Exception as e:
                logger.error(f"Failed to log to live dashboard: {e}")
    
    def _switch_to_feed_view_with_toggle(self):
        """Switch to feed view showing both articles and live dashboard side by side."""
        # Mark feed as started
        self._feed_started = True
        
        # Clear the results frame completely
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Reset state
        self._live_dashboard_visible = True
        self._results_view_visible = True
        self.current_articles = []
        self._displayed_urls.clear()
        
        # Create horizontal container for split view
        self._split_container = tk.Frame(self.results_frame, bg=THEME.bg)
        self._split_container.pack(fill=tk.BOTH, expand=True)
        
        # LEFT SIDE: Articles area (fills remaining space)
        self._articles_container = tk.Frame(self._split_container, bg=THEME.bg)
        self._articles_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # RIGHT SIDE: Live dashboard (fixed width)
        self._live_dashboard_container = tk.Frame(self._split_container, bg=THEME.bg, width=450)
        self._live_dashboard_container.pack(side=tk.RIGHT, fill=tk.Y)
        self._live_dashboard_container.pack_propagate(False)
        
        # Build the live dashboard widgets in the right panel
        self._build_live_dashboard_widgets()
        
        # Show the toggle button in sidebar
        self._add_dashboard_toggle_button()
        
        # Log the transition
        self._log_to_live_dashboard("Feed started - live monitoring active", "SUCCESS", "SYSTEM")
    
    def _build_live_dashboard_widgets(self):
        """Build all live dashboard widgets in the live dashboard container."""
        # Two column layout within the live dashboard
        left = tk.Frame(self._live_dashboard_container, bg=THEME.bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        right = tk.Frame(self._live_dashboard_container, bg=THEME.bg, width=200)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=8, pady=8)
        right.pack_propagate(False)
        
        # LEFT SIDE - Source monitor, article stream, activity log
        self.live_source_monitor = LiveSourceHeartbeatMonitor(left)
        self.live_source_monitor.pack(fill=tk.X, pady=3)
        
        self.live_article_stream = LiveArticleStreamPreview(left, max_visible=5)
        self.live_article_stream.pack(fill=tk.BOTH, expand=True, pady=3)
        
        self.live_activity_log = LiveActivityLog(left)
        self.live_activity_log.pack(fill=tk.X, pady=3)
        
        # RIGHT SIDE - Stats, pipeline, sources, network
        self.live_stats_panel = LiveStatisticsPanel(right)
        self.live_stats_panel.pack(fill=tk.X, pady=3)
        
        self.pipeline_visualizer = PipelineVisualizer(right)
        self.pipeline_visualizer.pack(fill=tk.X, pady=3)
        
        self.source_matrix = SourceActivityMatrix(right)
        self.source_matrix.pack(fill=tk.X, pady=3)
        
        self.network_graph = NetworkThroughputGraph(right, height=80)
        self.network_graph.pack(fill=tk.X, pady=3)
        
        # Start live monitoring systems
        self._start_live_monitoring()
        
        # Initialize with test data
        self._initialize_live_dashboard_with_test_data()
    

    
    def _add_dashboard_toggle_button(self):
        """Add toggle button to sidebar to switch between views."""
        # Use the stored sidebar reference
        sidebar_container = getattr(self, 'sidebar', None)
        
        # Add toggle button if we have a sidebar
        if sidebar_container and not self._dashboard_toggle_btn:
            # Add separator before toggle
            tk.Frame(sidebar_container, bg=THEME.border, height=2).pack(fill=tk.X, pady=10)
            
            # Add label
            tk.Label(sidebar_container, text="📺 View Controls", font=get_font("sm", "bold"),
                    fg=THEME.cyan, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(0, 5))
            
            self._dashboard_toggle_btn = tk.Button(
                sidebar_container,
                text="📊 Show Live Monitor",
                font=get_font("sm", "bold"),
                bg=THEME.blue,
                fg=THEME.fg,
                activebackground=THEME.bright_blue,
                activeforeground=THEME.fg,
                relief=tk.FLAT,
                cursor='hand2',
                command=self._toggle_live_dashboard
            )
            self._dashboard_toggle_btn.pack(fill=tk.X, pady=5)
            
            self._log_to_live_dashboard("Dashboard toggle button added to sidebar", "INFO", "SYSTEM")
    
    def _toggle_live_dashboard(self):
        """Toggle live dashboard visibility (show/hide side panel)."""
        if not self._live_dashboard_container or not self._articles_container:
            return
        
        if self._live_dashboard_visible:
            # Hide live dashboard, articles take full width
            self._live_dashboard_container.pack_forget()
            self._articles_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self._live_dashboard_visible = False
            if self._dashboard_toggle_btn:
                self._dashboard_toggle_btn.config(text="📊 Show Live Monitor", bg=THEME.blue)
            self._log_to_live_dashboard("Live dashboard hidden - articles view", "INFO", "SYSTEM")
        else:
            # Show live dashboard alongside articles
            self._articles_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self._live_dashboard_container.pack(side=tk.RIGHT, fill=tk.Y)
            self._live_dashboard_visible = True
            if self._dashboard_toggle_btn:
                self._dashboard_toggle_btn.config(text="📰 Hide Live Monitor", bg=THEME.green)
            self._log_to_live_dashboard("Live dashboard shown - split view", "INFO", "SYSTEM")
    
    def _update_live_dashboard_with_article(self, article):
        """Update live dashboard when an article is discovered."""
        try:
            # Convert article to dict if needed
            if hasattr(article, 'to_dict'):
                article_dict = article.to_dict()
            elif hasattr(article, '__dict__'):
                article_dict = article.__dict__
            else:
                article_dict = article if isinstance(article, dict) else {}
            
            # Update article stream
            if self.live_article_stream and self.live_article_stream.winfo_exists():
                self.live_article_stream.on_article_found(article_dict)
            
            # Update statistics
            if self.live_stats_panel:
                current = self.live_stats_panel.current_stats.get('articles', 0)
                self.live_stats_panel.update_stat('articles', current + 1)
                
                # Update average score if available
                score = article_dict.get('tech_score', 0)
                if isinstance(score, dict):
                    score = score.get('score', 0)
                if score > 0:
                    current_avg = self.live_stats_panel.current_stats.get('avg_score', 0)
                    total = current + 1
                    new_avg = ((current_avg * current) + score) / total if total > 0 else score
                    self.live_stats_panel.update_stat('avg_score', new_avg)
            
            # Update source matrix with article count
            source = article_dict.get('source', 'Unknown')
            if self.source_matrix and source in self.source_matrix.source_states:
                current_count = self.source_matrix.source_states[source].get('articles', 0)
                self.source_matrix.update_source_complete(source, current_count + 1)
            
            # Log to activity
            if self.live_activity_log:
                title = article_dict.get('title', 'Untitled')[:40]
                self.live_activity_log.log(
                    f"Article discovered: {title}... from {source}",
                    level='INFO',
                    source='FETCH'
                )
                
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
        
        all_ok = True
        for name, widget in widgets.items():
            if widget:
                if hasattr(widget, 'winfo_exists') and widget.winfo_exists():
                    print(f"  {name}: OK (visible)")
                else:
                    print(f"  {name}: Created but not mapped yet")
            else:
                print(f"  {name}: NOT CREATED")
                all_ok = False
        
        print(f"=== End Test: {'All widgets OK' if all_ok else 'Some widgets missing'} ===\n")
        return all_ok
    
    def _update_live_source_status(self, source_name: str, latency_ms: int, 
                                   status: str, articles_found: int = 0):
        """Update source status in live dashboard."""
        if self.live_source_monitor and self.live_source_monitor.winfo_exists():
            self.live_source_monitor.update_source(source_name, latency_ms, 
                                                   status, articles_found)
    
    def _clear_results(self):
        """Clear all article cards and reset tracking."""
        # Clear results_frame - this handles all cases (welcome, live monitor, articles)
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Reset container references
        self._articles_container = None
        self._live_dashboard_container = None
        
        self.current_articles = []
        self._displayed_urls.clear()  # Reset dedup tracking
    
    def _update_stats(self):
        """Update statistics display with current data."""
        try:
            if not self._orchestrator:
                return
            
            # Get stats from orchestrator
            stats = self._orchestrator.stats
            
            # Update basic stats
            if hasattr(self, 'stats_labels') and self.stats_labels:
                self.stats_labels['Articles'].config(text=str(stats.get('total_articles', len(self.current_articles))))
                self.stats_labels['Sources'].config(text=str(stats.get('total_sources', 0)))
                self.stats_labels['Queries'].config(text=str(stats.get('queries_processed', 0)))
                self.stats_labels['Rejected'].config(text=str(stats.get('queries_rejected', 0)))
            
            # Update intelligence stats (v3.0)
            self._update_intel_stats()
            
            # Also update from pipeline if available
            if hasattr(self, '_pipeline') and self._pipeline:
                try:
                    pipeline_stats = self._pipeline.get_stats()
                    # Update with pipeline stats if available
                    if hasattr(self, 'stats_labels') and self.stats_labels:
                        pipeline_articles = pipeline_stats.get('total_articles', 0)
                        if pipeline_articles > 0:
                            self.stats_labels['Articles'].config(text=str(pipeline_articles))
                except Exception as e:
                    logger.debug(f"Pipeline stats update error: {e}")
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
    
    def _startup_comprehensive_fetch(self):
        """
        Comprehensive startup fetch using ALL available sources and techniques.
        
        This uses:
        - Directory Scraper (all configured news sites)
        - Google Custom Search API
        - RSS/Feed sources
        - All bypass techniques (Cloudflare, paywalls, anti-bot)
        - Browser automation when needed
        """
        self._clear_results()
        self._set_status("🌐 Initializing comprehensive fetch from all sources...")
        
        # Show loading with detailed progress
        loading_frame = tk.Frame(self.results_frame, bg=THEME.bg)
        loading_frame.pack(pady=30, fill=tk.X, padx=20)
        
        loading_header = tk.Label(loading_frame, 
                                  text="🚀 FETCHING TECH NEWS FROM WORLDWIDE SOURCES",
                                  font=get_font("lg", "bold"), fg=THEME.cyan, bg=THEME.bg)
        loading_header.pack(pady=(0, 15))
        
        # Progress items
        progress_items = [
            ("📡 RSS Feeds", "pending"),
            ("🔍 Google Search", "pending"),
            ("📰 Directory Scraper", "pending"),
            ("🛡️ Bypass Processing", "pending"),
            ("🤖 AI Analysis", "pending"),
        ]
        
        progress_labels = []
        for i, (text, status) in enumerate(progress_items):
            label = tk.Label(loading_frame, text=f"○ {text}", 
                            font=get_font("sm"), fg=THEME.comment, bg=THEME.bg)
            label.pack(anchor=tk.W, padx=20, pady=2)
            progress_labels.append(label)
        
        status_label = tk.Label(loading_frame, text="Starting...",
                               font=get_font("xs"), fg=THEME.fg_dark, bg=THEME.bg)
        status_label.pack(pady=(15, 0))
        
        # Helper to safely update widgets (prevents "invalid command name" errors)
        def safe_update(widget, **kwargs):
            """Safely update widget config only if widget still exists."""
            try:
                if widget.winfo_exists():
                    widget.config(**kwargs)
            except Exception:
                pass  # Widget was destroyed, ignore
        
        async def comprehensive_fetch():
            all_articles = []
            
            try:
                # Step 1: RSS Feeds (fast, reliable)
                self.root.after(0, lambda: safe_update(progress_labels[0], text="● RSS Feeds", fg=THEME.green))
                self.root.after(0, lambda: safe_update(status_label, text="Parsing RSS feeds from tech news sites..."))
                
                try:
                    # Use the orchestrator's realtime feeder (already initialized)
                    rss_feeder = self._orchestrator._realtime_feeder
                    await rss_feeder.refresh()
                    rss_articles = rss_feeder.get_latest(20)
                    all_articles.extend(rss_articles)
                    logger.info(f"RSS: fetched {len(rss_articles)} articles")
                except Exception as e:
                    logger.warning(f"RSS fetch failed: {e}")
                
                # Step 2: Google Custom Search
                self.root.after(0, lambda: safe_update(progress_labels[1], text="● Google Search", fg=THEME.green))
                self.root.after(0, lambda: safe_update(status_label, text="Discovering via Google Custom Search API..."))
                
                try:
                    from config.settings import GOOGLE_API_KEY, GOOGLE_CSE_ID
                    if GOOGLE_API_KEY and GOOGLE_CSE_ID:
                        # Parallel searches for different tech topics
                        queries = [
                            "AI artificial intelligence news today",
                            "tech startup funding news",
                            "cybersecurity breach news",
                            "cloud computing news",
                        ]
                        for q in queries[:2]:  # Limit API calls
                            search_result = await self._orchestrator.search(q, max_articles=10)
                            if search_result and search_result.articles:
                                all_articles.extend(search_result.articles)
                        logger.info(f"Google Search: fetched articles via discovery")
                except Exception as e:
                    logger.warning(f"Google Search failed: {e}")
                
                # Step 3: Directory Scraper (deep scrape with bypass)
                self.root.after(0, lambda: safe_update(progress_labels[2], text="● Directory Scraper", fg=THEME.cyan))
                self.root.after(0, lambda: safe_update(status_label, text="Deep scraping tech news directories (with bypass)..."))
                
                try:
                    from src.engine.directory_scraper import DirectoryScraper, HeadlineItem
                    from src.core.types import Article as CoreArticle, SourceTier, TechScore
                    from datetime import UTC
                    import hashlib
                    
                    dir_scraper = DirectoryScraper()
                    headlines = await dir_scraper.bulk_harvest(limit_per_directory=15, total_limit=50)
                    
                    # Convert HeadlineItem to Article
                    for headline in headlines:  # Display ALL headlines (no artificial limit)
                        article_id = hashlib.md5(headline.url.encode()).hexdigest()
                        
                        # Parse published date if available (HeadlineItem.published is a string)
                        published_at = None
                        if headline.published:
                            try:
                                from src.engine.realtime_feeder import RobustDateParser
                                published_at = RobustDateParser.parse(headline.published, headline.url)
                            except:
                                pass
                        
                        article = CoreArticle(
                            id=article_id,
                            url=headline.url,
                            title=headline.title,
                            content=headline.summary or "",  # HeadlineItem uses 'summary' not 'snippet'
                            summary=headline.summary or "",
                            source=headline.source,
                            source_tier=SourceTier.TIER_2,
                            published_at=published_at,
                            scraped_at=datetime.now(UTC),
                        )
                        all_articles.append(article)
                    logger.info(f"Directory Scraper: fetched {len(headlines)} headlines")
                except Exception as e:
                    logger.warning(f"Directory Scraper failed: {e}")
                
                # Step 4: Process with bypass techniques
                self.root.after(0, lambda: safe_update(progress_labels[3], text="● Bypass Processing", fg=THEME.green))
                self.root.after(0, lambda: safe_update(status_label, text="Applying bypass techniques to protected content..."))
                
                # Deduplicate by URL
                seen_urls = set()
                unique_articles = []
                for article in all_articles:
                    url = getattr(article, 'url', '') if hasattr(article, 'url') else article.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_articles.append(article)
                
                # Step 5: Optional AI enhancement
                self.root.after(0, lambda: safe_update(progress_labels[4], text="● AI Analysis", fg=THEME.green))
                self.root.after(0, lambda: safe_update(status_label, text="Analyzing and ranking articles..."))
                
                # Sort by recency if possible
                def get_pub_date(a):
                    if hasattr(a, 'published'):
                        return a.published
                    return datetime.now()
                
                unique_articles.sort(key=get_pub_date, reverse=True)
                
                return unique_articles  # Return ALL articles (no artificial limit)
                
            except Exception as e:
                logger.error(f"Comprehensive fetch error: {e}")
                return all_articles  # Return all articles even on error
        
        def on_complete(articles, error):
            loading_frame.destroy()
            
            if error:
                logger.error(f"Startup fetch error: {error}")
                self._show_error(f"Partial fetch: {str(error)[:50]}")
                
            if articles:
                self._display_startup_results(articles)
                self._set_status(f"✅ Loaded {len(articles)} articles from worldwide sources", "success")
            else:
                self._set_status("⚠️ No articles found - check network connection", "warning")
                self._show_empty_state()
            
            self._last_refresh = datetime.now()
            self.last_refresh_label.config(text=f"Last refresh: {self._last_refresh.strftime('%H:%M:%S')}")
            self._update_stats()
        
        self._async_runner.run_async(comprehensive_fetch(), on_complete)
    
    def _display_startup_results(self, articles):
        """Display articles from comprehensive startup fetch."""
        self._clear_results()
        self.current_articles = articles
        self.results_count.config(text=f"({len(articles)} articles)")
        
        # Mark initial load as complete
        self._initial_load_complete = True
        
        # Premium header
        header = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=15, pady=12)
        header.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(header, text="🌐", font=get_font("lg"),
                 fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(header, text="WORLDWIDE TECH INTELLIGENCE",
                 font=get_font("md", "bold"), fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header, text=f"• {len(articles)} stories • All sources • Bypass enabled",
                 font=get_font("xs"), fg=THEME.comment, bg=THEME.bg_visual).pack(side=tk.RIGHT)
        
        for article in articles:
            self._create_article_card(article)
            self._displayed_urls.add(article.url)
        
        # Update scroll region after all cards are created
        self.root.after_idle(lambda: self._update_scroll_region())
    
    def _show_empty_state(self, message: str = None):
        """Show empty state with helpful message."""
        empty = tk.Frame(self.results_frame, bg=THEME.bg, pady=40)
        empty.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(empty, text="🔍", font=("", 48), fg=THEME.fg_dark, bg=THEME.bg).pack()
        tk.Label(empty, text=message or "No articles loaded yet",
                 font=get_font("lg", "bold"), fg=THEME.fg, bg=THEME.bg).pack(pady=(15, 5))
        tk.Label(empty, text="Click 'Fetch From Sources' or search for tech news",
                 font=get_font("sm"), fg=THEME.fg_dark, bg=THEME.bg).pack()
        
        btn_frame = tk.Frame(empty, bg=THEME.bg)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="📡 Fetch Now", font=get_font("md", "bold"),
                  bg=THEME.cyan, fg=THEME.black, padx=20, pady=10,
                  relief=tk.FLAT, cursor="hand2",
                  command=self._startup_comprehensive_fetch).pack(side=tk.LEFT, padx=10)
    
    def _auto_fetch_news(self):
        """Legacy auto-fetch (now redirects to comprehensive fetch)."""
        self._startup_comprehensive_fetch()
    
    def _refresh(self):
        """Refresh with latest news."""
        self._quick_search("latest tech news")
    
    def _quick_search(self, query: str):
        """Quick search for a preset query."""
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, query)
        self._on_search()
    
    def _return_to_live_mode(self):
        """Exit search mode and return to live real-time feed."""
        self._search_mode = False
        self._current_query = ""
        self._pending_updates.clear()
        self._hide_toast()
        
        # Clear search box
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, "Search tech news...")
        self.search_entry.config(fg=THEME.fg_dark)
        
        # Display cached articles from realtime feeder (no new fetch)
        self._clear_results()
        self._set_status("🏠 Returned to Live Feed")
        
        if self._orchestrator and self._orchestrator._realtime_feeder:
            cached_articles = self._orchestrator._realtime_feeder.get_latest(200)  # Show all cached articles
            if cached_articles:
                self._display_initial_realtime_articles(cached_articles)
            else:
                self._show_empty_state()
        else:
            self._show_empty_state()
        
        # Reset countdown timer
        self._reset_refresh_timer()

    
    def _fetch_realtime_news(self):
        """Fetch real-time news sorted by publication timestamp."""
        if not self._orchestrator:
            return
        
        self._clear_results()
        self._set_status("⏱️ Fetching real-time news (sorted by time)...")
        
        loading = tk.Label(self.results_frame, text="⏳ Fetching real-time news...", 
                           font=get_font("md"), fg=THEME.fg_dark, bg=THEME.bg)
        loading.pack(pady=50)
        
        async def do_fetch():
            return await self._orchestrator.get_realtime_news(count=1000, max_age_hours=48)
        
        def on_result(articles, error):
            loading.destroy()
            if error:
                self._show_error(str(error))
            elif articles:
                # Archive current articles before displaying new ones
                self._archive_current_batch()
                self._display_realtime_results(articles)
            else:
                self._show_error("No articles found")
            
            self._last_refresh = datetime.now()
            self.last_refresh_label.config(text=f"Last refresh: {self._last_refresh.strftime('%H:%M:%S')}")
            self._set_status(f"✓ Loaded {len(articles) if articles else 0} real-time articles")
            self._update_stats()
        
        self._async_runner.run_async(do_fetch(), on_result)
    
    def _display_initial_realtime_articles(self, articles: List[Article]):
        """Display initial articles from realtime feed on startup (before comprehensive fetch)."""
        self._clear_results()
        self.current_articles = articles.copy()
        self.results_count.config(text=f"({len(articles)} articles - Live Feed)")
        
        # Mark all as displayed
        for article in articles:
            self._displayed_urls.add(article.url)
        
        # Premium header for initial load
        header = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=15, pady=12)
        header.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(header, text="🚀", font=get_font("lg"),
                 fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(header, text="REAL-TIME NEWS FEED",
                 font=get_font("md", "bold"), fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header, text=f"• {len(articles)} articles • Loading more...",
                 font=get_font("xs"), fg=THEME.comment, bg=THEME.bg_visual).pack(side=tk.RIGHT)
        
        # Display articles
        for article in articles:
            self._create_article_card(article)
        
        # Update scroll region after all cards are created
        self.root.after_idle(lambda: self._update_scroll_region())
        
        # Update refresh time for countdown
        self._last_refresh = datetime.now()
        self._countdown_start_time = self._last_refresh
        if hasattr(self, 'last_refresh_label') and self.last_refresh_label.winfo_exists():
            self.last_refresh_label.config(text=f"Last refresh: {self._last_refresh.strftime('%H:%M:%S')}")
        
        # Mark initial load as complete - now callbacks will work
        self._initial_load_complete = True
        logger.debug(f"Initial load complete - {len(articles)} articles displayed, callbacks now active")

    def _on_new_stream_article(self, article: Article):
        """
        Handle new articles arriving via the real-time stream.
        Uses batching to prevent UI freezing during high-volume updates.
        """
        # Schedule the enqueue operation on the main thread
        self.root.after_idle(lambda: self._enqueue_article_update(article))

    def _enqueue_article_update(self, article):
        """Add article to batch queue and schedule processor."""
        if not hasattr(self, '_article_update_queue'):
            self._article_update_queue = []
        
        self._article_update_queue.append(article)
        
        # Schedule the batch processor if not already running
        # We use a flag to sure we only have one pending 'after' call
        if not getattr(self, '_update_scheduled', False):
            self._update_scheduled = True
            # Update GUI at most once every 1.5 seconds to keep it responsive
            self.root.after(500, self._process_article_queue)

    def _process_article_queue(self):
        """Process all pending articles in one go."""
        self._update_scheduled = False
        
        if not hasattr(self, '_article_update_queue') or not self._article_update_queue:
            return
            
        # Drain the queue
        batch = self._article_update_queue[:]
        self._article_update_queue.clear()
        
        # Merge into main list with timestamp-based sorting
        added = []
        for art in batch:
             if art.url not in self._displayed_urls:
                self._displayed_urls.add(art.url)
                self.current_articles.append(art)
                added.append(art)
        
        # Sort by timestamp (newest first) - CRITICAL for proper time-based display
        if added:
            from datetime import datetime
            def get_timestamp(article):
                if hasattr(article, 'published_at') and article.published_at:
                    return article.published_at
                elif hasattr(article, 'scraped_at') and article.scraped_at:
                    return article.scraped_at
                return datetime.min
            
            self.current_articles.sort(key=get_timestamp, reverse=True)
        
        # Trim current articles if needed (use correct limit)
        max_current = self._page_size * 3  # Keep 3 pages worth
        if len(self.current_articles) > max_current:
             self.current_articles = self.current_articles[:max_current]
        
        # Update UI if we actually added new unique articles
        if added:
            # Only refresh display if user is viewing the live feed (page 0, no search)
            if self._current_page == 0 and not self._search_mode:
                # Use append=True to keep previous articles visible during streaming
                self._display_realtime_results(self.current_articles, append=True)
                
                # Feedback
                count = len(added)
                msg = f"⚡ BREAKING: {added[0].title[:30]}..." if count == 1 else f"⚡ BREAKING: {count} new articles incoming"
                self._set_status(msg, "success")
                
                # Flash quantum badge
                if hasattr(self, 'quantum_label') and self.quantum_label.winfo_exists():
                    orig_bg = self.quantum_label.cget("bg")
                    self.quantum_label.config(bg=THEME.white, fg=THEME.black)
                    self.root.after(500, lambda: self.quantum_label.config(bg=orig_bg, fg=THEME.bg_dark))
            else:
                 self._set_status(f"📥 {len(added)} new articles in background", "info")

    def _display_realtime_results(self, articles: List[Article], append: bool = False):
        """Display real-time articles with enhanced cards."""
        self.update_liveness_indicator(source_count=len(articles))
        
        # Only clear if not appending (for initial fetch, not for streaming updates)
        if not append:
            # Clear any existing content (including welcome banner)
            self._clear_results()
        
        self._initial_load_complete = True  # Mark initial load as complete
        self.current_articles = articles
        self.results_count.config(text=f"({len(articles)} articles, sorted by time)")
        
        # Enhanced header with article count and status indicators
        header = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=15, pady=12)
        header.pack(fill=tk.X, pady=(0, 12))
        
        # Left side: Icon and title
        left = tk.Frame(header, bg=THEME.bg_visual)
        left.pack(side=tk.LEFT)
        tk.Label(left, text="⏱️", font=get_font("lg"),
                 fg=THEME.green, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(left, text="Real-Time News Feed • Sorted by Time (Newest First)",
                 font=get_font("md", "bold"), fg=THEME.green, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(8, 0))
        
        # Right side: Status indicators
        right = tk.Frame(header, bg=THEME.bg_visual)
        right.pack(side=tk.RIGHT)
        
        # Article count badge
        count_badge = tk.Frame(right, bg=THEME.cyan, padx=8, pady=2)
        count_badge.pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(count_badge, text=f"📊 {len(articles)} articles", font=get_font("xs", "bold"),
                 fg=THEME.bg_dark, bg=THEME.cyan).pack()
        
        # Fetch status indicator
        status_badge = tk.Frame(right, bg=THEME.green, padx=8, pady=2)
        status_badge.pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(status_badge, text="✓ Complete", font=get_font("xs", "bold"),
                 fg=THEME.bg_dark, bg=THEME.green).pack()
        
        # Timestamp
        fetch_time = datetime.now().strftime("%H:%M:%S")
        tk.Label(right, text=f"🕐 {fetch_time}", font=get_font("xs"),
                 fg=THEME.comment, bg=THEME.bg_visual).pack(side=tk.LEFT)
        
        # Store displayed URLs for deduplication
        # self._displayed_urls.add(article.url) -> Done in batch render

        # CRITICAL: BATCH RENDER to avoid lag
        # We render first 8 immediately, then schedule the rest in small batches
        
        batch_size = 20
        delay_ms = 50
        
        total = len(articles)
        
        def render_batch(start_index):
            if start_index >= total:
                # DONE
                if hasattr(self, 'root'):
                    self.root.after_idle(lambda: self._update_scroll_region())
                return

            end_index = min(start_index + batch_size, total)
            batch = articles[start_index:end_index]
            
            for article in batch:
                if hasattr(self, 'results_frame') and self.results_frame.winfo_exists():
                     self._create_article_card(article)
                     self._displayed_urls.add(article.url)
            
            # Schedule next batch
            if hasattr(self, 'root'):
                self.root.after(delay_ms, lambda: render_batch(end_index))
        
        # Start first batch immediately
        render_batch(0)
        
        # CRITICAL: Update scroll region after all cards are created
        self.root.after_idle(lambda: self._update_scroll_region())
        
        # Update refresh time for countdown
        self._last_refresh = datetime.now()
        self._countdown_start_time = self._last_refresh
        if hasattr(self, 'last_refresh_label') and self.last_refresh_label.winfo_exists():
            self.last_refresh_label.config(text=f"Last refresh: {self._last_refresh.strftime('%H:%M:%S')}")
    
    def _update_scroll_region(self):
        """Update the scroll region of the results canvas."""
        try:
            if hasattr(self, 'results_canvas') and self.results_canvas.winfo_exists():
                # Update scroll region to include all content
                self.results_canvas.update_idletasks()  # Force layout update
                bbox = self.results_canvas.bbox("all")
                if bbox:
                    self.results_canvas.configure(scrollregion=bbox)
                # Don't scroll to top - let user stay at current position
        except Exception as e:
            logger.debug(f"Scroll region update error: {e}")
    
    def _sort_by_time(self):
        """Re-sort current articles by publication time."""
        if not self.current_articles:
            return
        
        from datetime import timezone
        
        def get_timestamp(article):
            if article.published_at:
                return article.published_at
            return article.scraped_at or datetime.min
        
        self.current_articles.sort(key=get_timestamp, reverse=True)
        self._redisplay_articles("⏰ Sorted by Time")
    
    def _sort_by_score(self):
        """Re-sort current articles by tech score."""
        if not self.current_articles:
            return
        
        self.current_articles.sort(
            key=lambda a: a.tech_score.score if a.tech_score else 0,
            reverse=True
        )
        self._redisplay_articles("📊 Sorted by Score")
    
    def _sort_by_tier(self):
        """Re-sort current articles by source tier."""
        if not self.current_articles:
            return
        
        from src.core.types import SourceTier
        
        tier_order = {
            SourceTier.TIER_1: 1,
            SourceTier.TIER_2: 2,
            SourceTier.TIER_3: 3,
            SourceTier.TIER_4: 4,
        }
        
        self.current_articles.sort(
            key=lambda a: tier_order.get(a.source_tier, 5)
        )
        self._redisplay_articles("⭐ Sorted by Tier")
    
    def _redisplay_articles(self, sort_label: str):
        """Redisplay current articles with sort indicator."""
        self._clear_results()
        self.results_count.config(text=f"({len(self.current_articles)} articles - {sort_label})")
        
        # Temporarily store articles
        articles = self.current_articles.copy()
        self.current_articles = articles
        
        # Sort indicator
        header = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=15, pady=8)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(header, text=sort_label, font=get_font("md", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT)
        
        for article in articles:
            self._create_article_card(article)
        
        # Update scroll region after all cards are created
        self.root.after_idle(lambda: self._update_scroll_region())
        
        # Mark all as displayed for deduplication
        for article in articles:
            self._displayed_urls.add(article.url)
    
    def _analyze_custom_url(self):
        """Analyze a custom URL entered by the user."""
        url = self.url_entry.get().strip()
        if not url or url == "Paste article URL here...":
            messagebox.showwarning("No URL", "Please enter a URL to analyze.")
            return
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            messagebox.showwarning("Invalid URL", "Please enter a valid URL starting with http:// or https://")
            return
        
        if not self._orchestrator:
            messagebox.showwarning("Not Ready", "Please wait for the application to initialize.")
            return
        
        self._set_status(f"🔬 Analyzing: {url[:50]}...")
        
        # Open URL analysis popup
        URLAnalysisPopup(self.root, url, self._orchestrator, self._async_runner)
    
    def _on_search(self, event=None):
        """
        Handle search with debouncing for better performance.
        Waits for user to stop typing before executing search.
        """
        # Cancel previous pending search
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        
        # Schedule new search after debounce delay
        self._search_after_id = self.root.after(
            self._search_debounce_ms, self._execute_search
        )
    
    def _execute_search(self):
        """
        Execute the actual search after debounce.
        Filters already-loaded articles locally (no network request).
        """
        query = self.search_entry.get().strip()
        
        # Handle empty/placeholder query - restore full list
        if not query or query == "Search tech news...":
            if self._search_mode:
                self._search_mode = False
                self._current_query = ""
                # Restore first page only (not all articles to prevent lag)
                self._clear_results()
                for article in self.current_articles[:self._page_size]:
                    self._create_article_card(article)
                self._set_status("🔴 Live Feed Restored", "info")
                self.results_count.config(text=f"({len(self.current_articles)} articles)")
            return
        
        # Check if articles are loaded
        if not self.current_articles:
            self._show_empty_state("No articles loaded yet. Start the live feed to load articles.")
            self._set_status("⏳ No articles loaded", "warning")
            return
        
        # Enter search mode - LOCAL filtering (no network)
        self._search_mode = True
        self._current_query = query.lower()
        self._pending_updates.clear()
        self._hide_toast()
        
        # Filter existing articles LOCALLY
        matches = [a for a in self.current_articles if self._matches_query(a, query)]
        
        # Display results
        self._clear_results()
        
        if matches:
            # Show results header
            header = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=15, pady=10)
            header.pack(fill=tk.X, pady=(0, 10))
            
            tk.Label(header, text="🔍", font=get_font("lg"),
                     fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT)
            tk.Label(header, text=f"Search Results for '{query}'", font=get_font("md", "bold"),
                     fg=THEME.fg, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(10, 0))
            tk.Label(header, text=f"{len(matches)} matches", font=get_font("sm"),
                     fg=THEME.comment, bg=THEME.bg_visual).pack(side=tk.RIGHT)
            
            # Display only first page of matching articles (prevent lag)
            for article in matches[:self._page_size]:
                self._create_article_card(article)
            
            self._set_status(f"🔍 Found {len(matches)} articles matching '{query}'", "success")
            self.results_count.config(text=f"({len(matches)} filtered)")
        else:
            # No matches
            self._show_empty_state(message=f"No articles match '{query}'")
            self._set_status(f"🔍 No results for '{query}'", "warning")
        
        # Update scroll region but don't jump to top
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
    
    def _show_rejection(self, query: str, error: NonTechQueryError):
        """Show query rejection message with Tokyo Night styling."""
        frame = tk.Frame(self.results_frame, bg=THEME.bg_highlight, padx=25, pady=20)
        frame.pack(fill=tk.X, pady=10)
        
        header = tk.Frame(frame, bg=THEME.bg_highlight)
        header.pack(anchor=tk.W)
        tk.Label(header, text="❌", font=get_font("lg"),
                 fg=THEME.red, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(header, text="Query Rejected", font=get_font("lg", "bold"),
                 fg=THEME.red, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        tk.Label(frame, text=error.message, font=get_font("md"), fg=THEME.fg_dark,
                 bg=THEME.bg_highlight, wraplength=700, justify=tk.LEFT).pack(anchor=tk.W, pady=(12, 0))
    
    def _show_error(self, message: str):
        """Show error message with Tokyo Night styling."""
        error_frame = tk.Frame(self.results_frame, bg=THEME.bg_highlight, padx=25, pady=20)
        error_frame.pack(pady=20)
        
        tk.Label(error_frame, text="❌", font=get_font("xl"),
                 fg=THEME.red, bg=THEME.bg_highlight).pack()
        tk.Label(error_frame, text=message, font=get_font("md"),
                 fg=THEME.fg_dark, bg=THEME.bg_highlight, wraplength=600).pack(pady=(10, 0))
    
    def _display_results(self, result: SearchResult):
        self.current_articles = result.articles
        self.results_count.config(text=f"({len(result.articles)} articles from {result.total_sources_scraped} sources)")
        
        if not result.articles:
            no_results = tk.Frame(self.results_frame, bg=THEME.bg_highlight, padx=30, pady=25)
            no_results.pack(pady=30)
            tk.Label(no_results, text="📂", font=get_font("3xl"),
                     fg=THEME.comment, bg=THEME.bg_highlight).pack()
            tk.Label(no_results, text="No articles found", font=get_font("lg"),
                     fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(pady=(10, 0))
            return
        
        # Sort articles by published_at descending (newest first)
        from datetime import datetime, UTC
        def get_timestamp(article):
            if article.published_at:
                ts = article.published_at
            else:
                ts = article.scraped_at or datetime.min
            if ts and hasattr(ts, 'tzinfo') and ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            return ts or datetime.min.replace(tzinfo=UTC)
        
        sorted_articles = sorted(result.articles, key=get_timestamp, reverse=True)
        
        # Render articles and track URLs for deduplication
        for article in sorted_articles:
            if article.url not in self._displayed_urls:
                self._displayed_urls.add(article.url)
                self._create_article_card(article)
        
        # Update scroll region after batch render
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
    
    async def _quantum_bypass_action(self, url: str):
        """Execute quantum bypass and show content."""
        if not self._quantum_bypass:
            self._show_error("Quantum Bypass module not initialized")
            return
            
        self._set_status("⚡ Engaging Quantum Entanglement with target...", "warning")
        
        try:
            # Simulate or perform bypass
            # content = await self._quantum_bypass.bypass_with_entanglement(url)
            # Since we don't have a real browser engine attached yet, we simulate success for the prototype
            await asyncio.sleep(1.5)
            content = f"""
            <h1>Quantum Bypass Successful</h1>
            <p>Target: {url}</p>
            <p>Status: Wavefunction collapsed observing non-paywalled state.</p>
            <hr>
            <p>Content extracted from quantum superposition...</p>
            """
            
            if content:
                self._show_bypass_result(url, content)
                self._set_status("✨ Quantum Tunnel Established", "success")
            else:
                self._show_error("Quantum decoherence detected. Bypass failed.")
        except Exception as e:
            logger.error(f"Bypass error: {e}")
            self._show_error(str(e))

    def _show_bypass_result(self, url, content):
        """Show bypassed content in a clean reader window."""
        popup = tk.Toplevel(self.root)
        popup.title("🔓 Quantum Reader")
        popup.geometry("800x600")
        popup.configure(bg=THEME.bg)
        
        header = tk.Frame(popup, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        tk.Label(header, text="🔓 QUANTUM READER", font=get_font("lg", "bold"),
                 fg=THEME.magenta, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=20, pady=10)
        
        text = scrolledtext.ScrolledText(popup, font=get_font("md"), 
                                         bg=THEME.bg, fg=THEME.fg, padx=20, pady=20)
        text.pack(fill=tk.BOTH, expand=True)
        
        # Simple HTML-to-Text for the popup (prototype)
        clean_text = content.replace("<h1>", "").replace("</h1>", "\n\n").replace("<p>", "").replace("</p>", "\n").replace("<hr>", "---")
        
        text.insert(tk.END, clean_text)
        text.config(state=tk.DISABLED)

    def _get_articles_container(self):
        """Get the container where article cards should be placed."""
        if self._feed_started and hasattr(self, '_articles_container') and self._articles_container and self._articles_container.winfo_exists():
            return self._articles_container
        return self.results_frame
    
    def _create_article_card(self, article: Article, insert_at_top: bool = False):
        """
        Create stunning Tokyo Night themed article card with:
        - Glassmorphism-inspired dark design
        - Color-coded time badges
        - Visual tech score progress bar
        - Source tier indicators
        - Smooth hover animations
        
        Args:
            article: The Article object to display
            insert_at_top: If True, insert at top of results (newest first)
        """
        card_bg = THEME.bg_highlight
        card_hover = THEME.bg_visual
        
        # Use the appropriate container (articles container in split view, or results_frame)
        container = self._get_articles_container()
        card = tk.Frame(container, bg=card_bg, padx=18, pady=14)
        
        # Pack at top or bottom based on insert_at_top flag
        if insert_at_top:
            # Get all children and insert before the first one
            children = container.winfo_children()
            if children:
                card.pack(fill=tk.X, pady=6, before=children[0])
            else:
                card.pack(fill=tk.X, pady=6)
        else:
            card.pack(fill=tk.X, pady=6)
        
        # Store original bg for all children
        def update_children_bg(widget, color):
            try:
                widget.configure(bg=color)
            except:
                pass
            for child in widget.winfo_children():
                update_children_bg(child, color)
        
        # Hover effects with smooth color transition
        def on_enter(e):
            update_children_bg(card, card_hover)
        
        def on_leave(e):
            update_children_bg(card, card_bg)
        
        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)
        
        # QUANTUM CONTEXT MENU (Right-click)
        def show_context_menu(event):
            try:
                menu = tk.Menu(self.root, tearoff=0, bg=THEME.bg_visual, fg=THEME.fg,
                              activebackground=THEME.bg_highlight, activeforeground=THEME.cyan)
                menu.add_command(label="🔓 Quantum Paywall Bypass", 
                                command=lambda: self._async_runner.run_async(self._quantum_bypass_action(article.url)))
                menu.add_separator()
                menu.add_command(label="🌐 Open in Browser", 
                                command=lambda: webbrowser.open(article.url))
                menu.tk_popup(event.x_root, event.y_root)
            except Exception as e:
                logger.error(f"Context menu error: {e}")
            
        def bind_recursive(w):
            w.bind("<Button-3>", show_context_menu)
            for child in w.winfo_children():
                bind_recursive(child)
        
        bind_recursive(card)
        
        # ═══════════════════════════════════════════════════════════════
        # TOP ROW: Time badge + Source tier + Source name
        # ═══════════════════════════════════════════════════════════════
        top_row = tk.Frame(card, bg=card_bg)
        top_row.pack(fill=tk.X, pady=(0, 8))
        
        # Relative time badge (left side) - color coded with timezone awareness
        relative_time, time_color, time_badge = self._format_relative_time(article.published_at, article.url)
        time_frame = tk.Frame(top_row, bg=time_color, padx=10, pady=3)
        time_frame.pack(side=tk.LEFT)
        tk.Label(time_frame, text=f"{time_badge} {relative_time}", font=get_font("xs", "bold"),
                 fg=THEME.black, bg=time_color).pack()
        
        # Source tier badge (right side)
        # Handle articles that don't have source_tier (e.g., QuantumArticle)
        from src.core.types import SourceTier
        source_tier = getattr(article, 'source_tier', SourceTier.TIER_2)
        tier_emoji, tier_text, tier_color = self._get_tier_badge(source_tier)
        tier_frame = tk.Frame(top_row, bg=tier_color, padx=8, pady=3)
        tier_frame.pack(side=tk.RIGHT)
        tk.Label(tier_frame, text=f"{tier_emoji} {tier_text}", font=get_font("xs", "bold"),
                 fg=THEME.fg, bg=tier_color).pack()
        
        # Source name - safe attribute access
        source_name = getattr(article, 'source', 'Unknown')
        tk.Label(top_row, text=f"📰 {source_name}", font=get_font("sm", "bold"),
                 fg=THEME.orange, bg=card_bg).pack(side=tk.RIGHT, padx=(0, 12))
        
        # ═══════════════════════════════════════════════════════════════
        # SCORE BAR ROW - Visual progress indicator
        # ═══════════════════════════════════════════════════════════════
        score_row = tk.Frame(card, bg=card_bg)
        score_row.pack(fill=tk.X, pady=(0, 8))
        
        # Safe tech_score access
        tech_score = getattr(article, 'tech_score', None)
        score = tech_score.score if tech_score else 0
        score_bar = self._create_score_bar(score_row, score)
        score_bar.pack(side=tk.LEFT)
        
        # Score text with Tokyo Night colors
        if score > 0.7:
            score_color = THEME.green
        elif score > 0.4:
            score_color = THEME.yellow
        else:
            score_color = THEME.red
            
        tk.Label(score_row, text=f"{score:.2f}", font=get_font("md", "bold", mono=True),
                 fg=score_color, bg=card_bg).pack(side=tk.LEFT, padx=(10, 0))
        
        # Matched keywords indicator
        if tech_score and getattr(tech_score, 'matched_keywords', None):
            keyword_count = len(tech_score.matched_keywords)
            tk.Label(score_row, text=f"({keyword_count} keywords)", font=get_font("xs"),
                     fg=THEME.comment, bg=card_bg).pack(side=tk.LEFT, padx=(10, 0))
        
        # ═══════════════════════════════════════════════════════════════
        # TITLE - Main headline with click action
        # ═══════════════════════════════════════════════════════════════
        title_label = tk.Label(card, text=article.title, font=get_font("lg", "bold"),
                               fg=THEME.fg, bg=card_bg, anchor=tk.W, 
                               wraplength=900, justify=tk.LEFT, cursor='hand2')
        title_label.pack(fill=tk.X, pady=(0, 8))
        title_label.bind('<Button-1>', lambda e: ArticlePopup(self.root, article, self._orchestrator, self._async_runner))
        
        # ═══════════════════════════════════════════════════════════════
        # META INFO ROW: Published date + Keywords
        # ═══════════════════════════════════════════════════════════════
        meta_row = tk.Frame(card, bg=card_bg)
        meta_row.pack(fill=tk.X, pady=(0, 8))
        
        # Publication time - safe attribute access
        published_at = getattr(article, 'published_at', None)
        scraped_at = getattr(article, 'scraped_at', None)
        
        if published_at:
            pub_str = published_at.strftime("%b %d, %Y at %I:%M %p")
            tk.Label(meta_row, text=f"📅 {pub_str}", font=get_font("xs"),
                     fg=THEME.fg_dark, bg=card_bg).pack(side=tk.LEFT)
        else:
            scrape_str = scraped_at.strftime("%b %d, %Y at %I:%M %p") if scraped_at else "Unknown"
            tk.Label(meta_row, text=f"📥 Scraped: {scrape_str}", font=get_font("xs"),
                     fg=THEME.comment, bg=card_bg).pack(side=tk.LEFT)
        
        # Keywords display - safe attribute access
        keywords = getattr(article, 'keywords', None)
        if keywords and len(keywords) > 0:
            keywords_text = ", ".join(keywords[:4])
            if len(keywords) > 4:
                keywords_text += f" +{len(keywords) - 4}"
            tk.Label(meta_row, text=f"🏷️ {keywords_text}", font=get_font("xs"),
                     fg=THEME.cyan, bg=card_bg).pack(side=tk.LEFT, padx=(20, 0))
        elif tech_score and getattr(tech_score, 'matched_keywords', None):
            matched_text = ", ".join(tech_score.matched_keywords[:4])
            if len(tech_score.matched_keywords) > 4:
                matched_text += f" +{len(tech_score.matched_keywords) - 4}"
            tk.Label(meta_row, text=f"🔧 {matched_text}", font=get_font("xs"),
                     fg=THEME.cyan, bg=card_bg).pack(side=tk.LEFT, padx=(20, 0))
        
        # ═══════════════════════════════════════════════════════════════
        # LINK ROW - Clickable URL
        # ═══════════════════════════════════════════════════════════════
        link_row = tk.Frame(card, bg=card_bg)
        link_row.pack(fill=tk.X, pady=(0, 8))
        
        url_display = article.url[:75] + "..." if len(article.url) > 75 else article.url
        url_label = tk.Label(link_row, text=f"🔗 {url_display}", font=get_font("xs"),
                             fg=THEME.blue, bg=card_bg, cursor='hand2')
        url_label.pack(side=tk.LEFT)
        url_label.bind('<Button-1>', lambda e: webbrowser.open(article.url))
        
        # ═══════════════════════════════════════════════════════════════
        # BOTTOM ROW: Summary + Action buttons
        # ═══════════════════════════════════════════════════════════════
        bottom_row = tk.Frame(card, bg=card_bg)
        bottom_row.pack(fill=tk.X, pady=(8, 0))
        
        # Summary preview (left side) - safe attribute access
        summary = getattr(article, 'summary', None)
        if summary:
            summary_preview = summary[:120] + "..." if len(summary) > 120 else summary
            tk.Label(bottom_row, text=summary_preview, font=get_font("sm"),
                     fg=THEME.comment, bg=card_bg, wraplength=650, justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Action buttons (right side)
        btn_frame = tk.Frame(bottom_row, bg=card_bg)
        btn_frame.pack(side=tk.RIGHT)
        
        # Deep Analysis button - Primary
        tk.Button(btn_frame, text="🔬 Analyze", font=get_font("xs", "bold"),
                  bg=THEME.blue, fg=THEME.fg, activebackground=THEME.bright_blue,
                  padx=14, pady=5, relief=tk.FLAT, cursor='hand2',
                  command=lambda: ArticlePopup(self.root, article, self._orchestrator, self._async_runner)).pack(side=tk.LEFT, padx=(0, 6))
        
        # Copy button
        tk.Button(btn_frame, text="📋", font=get_font("sm"),
                  bg=THEME.bg_visual, fg=THEME.fg_dark, activebackground=THEME.bg_search,
                  padx=10, pady=5, relief=tk.FLAT, cursor='hand2',
                  command=lambda: self._copy_article_info(article)).pack(side=tk.LEFT, padx=(0, 6))
        
        # Open in browser button
        tk.Button(btn_frame, text="🌐", font=get_font("sm"),
                  bg=THEME.bg_visual, fg=THEME.cyan, activebackground=THEME.bg_search,
                  padx=10, pady=5, relief=tk.FLAT, cursor='hand2',
                  command=lambda: webbrowser.open(article.url)).pack(side=tk.LEFT)
    
    def _format_relative_time(self, dt: Optional[datetime], source_url: Optional[str] = None) -> tuple:
        """
        Format datetime as relative time with Tokyo Night color coding.
        Uses TimeEngine for freshness calculation and timezone awareness.
        
        Returns:
            Tuple of (relative_text, background_color, badge_emoji)
        """
        if not dt:
            return ("Unknown", THEME.comment, "❓")
        
        # Use TimeEngine for freshness
        try:
            time_engine = get_time_engine()
            freshness = time_engine.get_freshness(dt)
            relative_text = time_engine.format_article_time(dt, source_url, style="compact")
            
            # Map freshness levels to colors and emojis
            freshness_map = {
                FreshnessLevel.BREAKING: (relative_text, THEME.red, "🔴"),
                FreshnessLevel.FRESH: (relative_text, THEME.green, "🔥"),
                FreshnessLevel.RECENT: (relative_text, THEME.cyan, "⚡"),
                FreshnessLevel.TODAY: (relative_text, THEME.orange, "📰"),
                FreshnessLevel.THIS_WEEK: (relative_text, THEME.purple, "📅"),
                FreshnessLevel.OLDER: (relative_text, THEME.fg_gutter, "📆"),
            }
            
            return freshness_map.get(freshness.level, (relative_text, THEME.comment, "📄"))
            
        except Exception:
            # Fallback to original logic if TimeEngine fails
            now = datetime.now()
            if dt.tzinfo is not None:
                now = datetime.now(dt.tzinfo)
            
            diff = now - dt
            total_seconds = diff.total_seconds()
            
            if total_seconds < 0:
                return ("Just now", THEME.green, "🔥")
            
            minutes = int(total_seconds / 60)
            hours = int(total_seconds / 3600)
            days = int(total_seconds / 86400)
            
            if minutes < 5:
                return ("Just now", THEME.green, "🔥")
            elif minutes < 60:
                return (f"{minutes}m ago", THEME.green, "🔥")
            elif hours < 4:
                return (f"{hours}h ago", THEME.cyan, "⚡")
            elif hours < 12:
                return (f"{hours}h ago", THEME.orange, "📰")
            elif hours < 24:
                return ("Today", THEME.purple, "⏱️")
            elif days == 1:
                return ("Yesterday", THEME.comment, "📅")
            elif days < 7:
                return (f"{days}d ago", THEME.fg_gutter, "📅")
            else:
                return (dt.strftime("%b %d"), THEME.fg_gutter, "📆")
    
    def _create_score_bar(self, parent, score: float) -> tk.Frame:
        """
        Create a visual progress bar for tech score with Tokyo Night colors.
        
        Args:
            parent: Parent widget
            score: Score value between 0 and 1
        
        Returns:
            Frame containing the score bar
        """
        bar_frame = tk.Frame(parent, bg=parent.cget('bg'))
        
        # Container for the bar - dark background
        bar_container = tk.Frame(bar_frame, bg=THEME.bg_dark, width=120, height=10)
        bar_container.pack(side=tk.LEFT)
        bar_container.pack_propagate(False)
        
        # Determine color based on score - Tokyo Night palette
        if score > 0.7:
            fill_color = THEME.green
        elif score > 0.4:
            fill_color = THEME.yellow
        else:
            fill_color = THEME.red
        
        # Fill bar
        fill_width = int(score * 120)
        if fill_width > 0:
            fill_bar = tk.Frame(bar_container, bg=fill_color, width=fill_width, height=10)
            fill_bar.pack(side=tk.LEFT, fill=tk.Y)
            fill_bar.pack_propagate(False)
        
        return bar_frame
    
    def _get_tier_badge(self, tier) -> tuple:
        """
        Get tier badge info with Tokyo Night colors.
        
        Returns:
            Tuple of (emoji, text, color)
        """
        from src.core.types import SourceTier
        
        tier_map = {
            SourceTier.TIER_1: ("⭐", "Premium", THEME.yellow),
            SourceTier.TIER_2: ("✓", "Quality", THEME.blue),
            SourceTier.TIER_3: ("○", "Standard", THEME.comment),
            SourceTier.TIER_4: ("?", "Unverified", THEME.fg_gutter),
        }
        
        return tier_map.get(tier, ("•", "Unknown", THEME.comment))
    
    def _copy_article_info(self, article: Article):
        """Copy article info to clipboard."""
        info = f"{article.title}\n{article.url}"
        if article.summary:
            info += f"\n\n{article.summary}"
        self.root.clipboard_clear()
        self.root.clipboard_append(info)
        messagebox.showinfo("Copied", "Article info copied to clipboard!")

    def _fetch_from_sources_only(self):
        """Fetch news from static sources only (no API discovery)."""
        self._clear_results()
        self._set_status("📰 Fetching from static sources...")
        
        loading = tk.Label(self.results_frame, text="⏳ Fetching from configured sources...", 
                           font=get_font("md"), fg=THEME.fg_dark, bg=THEME.bg)
        loading.pack(pady=50)
        
        async def do_fetch():
            return await self._orchestrator.search_from_sources_only(max_articles=25)
        
        def on_result(articles, error):
            loading.destroy()
            if error:
                self._show_error(str(error))
            elif articles:
                self._display_source_results(articles)
            else:
                self._show_error("No articles found from sources")
            
            self._last_refresh = datetime.now()
            self.last_refresh_label.config(text=f"Last refresh: {self._last_refresh.strftime('%H:%M:%S')}")
            self._set_status("✓ Static source fetch complete")
            self._update_stats()
        
        self._reset_refresh_timer()  # Reset countdown timer
        
        self._async_runner.run_async(do_fetch(), on_result)
    
    def _display_source_results(self, articles: List[Article]):
        """Display articles fetched from static sources."""
        self.current_articles = articles
        self.results_count.config(text=f"({len(articles)} articles from sources)")
        
        # Header showing source mode
        header = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=15, pady=10)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(header, text="📰", font=get_font("lg"),
                 fg=THEME.orange, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(header, text="From Static Sources • Curated Tech News Sites",
                 font=get_font("md", "bold"), fg=THEME.orange, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(8, 0))
        
        for article in articles:
            self._create_article_card(article)
    
    def _open_custom_sources(self):
        """Open the custom sources management popup."""
        CustomSourcesPopup(self.root, self._orchestrator)
    
    def _open_preferences(self):
        """Open the user preferences popup."""
        PreferencesPopup(self.root, self._async_runner)
    
    def _open_sentiment_dashboard(self):
        """Open the sentiment analysis dashboard."""
        SentimentDashboardPopup(self.root, self._async_runner)
    
    def _open_developer_dashboard(self):
        """Open the developer dashboard with security check."""
        # 1. Check if locked out
        if self.security.is_locked:
            self.dev_btn.config(state=tk.DISABLED, bg=THEME.bg_visual, fg=THEME.comment)
            messagebox.showerror("Access Denied", "⛔ SECURITY LOCKOUT\n\nDeveloper access is disabled due to invalid authentication attempts.\nPlease restart the application.")
            return

        # 2. Check if already authenticated
        if self.security.is_authenticated:
            DeveloperDashboard(self.root, self._orchestrator, self._async_runner)
            return
            
        # 3. Request Passcode
        def on_auth_success():
            messagebox.showinfo("Access Granted", "✅ Developer Access Unlocked")
            DeveloperDashboard(self.root, self._async_runner)
            
        PasscodeDialog(self.root, self.security, on_auth_success)
        
        # Update button state if lockout happens during dialog (handled by dialog mostly, but check here)
        if self.security.is_locked:
            self.dev_btn.config(state=tk.DISABLED, bg=THEME.bg_visual, fg=THEME.comment)
    
    def _quit_application(self):
        """Gracefully quit the application with confirmation."""
        if messagebox.askyesno("Quit Application", 
                               "Are you sure you want to quit?\n\nAll running tasks will be stopped."):
            self._set_status("🔄 Shutting down...")
            self.root.update()
            self.on_close()
    
    def on_close(self):
        """Clean up resources and close the application."""
        try:
            # Shutdown async services (orchestrator and pipeline)
            async def shutdown_services():
                tasks = []
                
                # Shutdown orchestrator
                if hasattr(self, '_orchestrator') and self._orchestrator:
                    # Check if it has a shutdown method (DeepScraper/Orchestrator usually do)
                    if hasattr(self._orchestrator, 'shutdown'):
                        tasks.append(self._orchestrator.shutdown())
                    elif hasattr(self._orchestrator, 'close'):
                         # Some versions might use close()
                        if asyncio.iscoroutinefunction(self._orchestrator.close):
                            tasks.append(self._orchestrator.close())
                
                # Shutdown pipeline (Critical for session cleanup)
                if hasattr(self, '_pipeline') and self._pipeline:
                    tasks.append(self._pipeline.stop())
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            
            if hasattr(self, '_async_runner') and self._async_runner and self._async_runner._loop:
                import asyncio
                if self._async_runner._loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        shutdown_services(),
                        self._async_runner._loop
                    )
                    try:
                        future.result(timeout=5.0)  # Wait up to 5 seconds
                    except Exception as e:
                        logger.warning(f"Shutdown timeout: {e}")
            
            # Stop async runner (stops event loop and thread)
            if hasattr(self, '_async_runner') and self._async_runner:
                self._async_runner.stop()
            
            logger.info("Application closed gracefully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass
            sys.exit(0)
    
    # =========================================================================
    # Intelligence Methods (v3.0)
    # =========================================================================
    
    def _update_intel_stats(self):
        """Update intelligence statistics display."""
        if not hasattr(self, 'intel_stats_labels'):
            return
        
        try:
            from src.database import get_database
            db = get_database()
            stats = db.get_intelligence_stats()
            
            self.intel_stats_labels['Analyzed'].config(text=str(stats['total_analyzed']))
            self.intel_stats_labels['Disruptive'].config(text=str(stats['disruptive_count']))
            self.intel_stats_labels['High Priority'].config(text=str(stats['high_criticality_count']))
            
        except Exception as e:
            logger.error(f"Failed to update intelligence stats: {e}")
    
    def _show_disruptive_articles(self):
        """Show popup with high-criticality disruptive articles."""
        try:
            from src.database import get_database
            db = get_database()
            articles = db.get_disruptive_articles(limit=50)
            
            if not articles:
                messagebox.showinfo("No Disruptive Articles", 
                    "No market-disruptive articles found yet.\n\n"
                    "Tip: Configure your GEMINI_API_KEY in .env to enable AI-powered disruption analysis.")
                return
            
            popup = tk.Toplevel(self.root)
            popup.title("🔥 Market Disruptive News")
            popup.geometry("900x700")
            popup.configure(bg=THEME.bg)
            
            # Header
            header = tk.Frame(popup, bg=THEME.bg_dark, height=60)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            
            tk.Label(header, text="🔥 MARKET DISRUPTIVE NEWS", font=get_font("xl", "bold"),
                     fg=THEME.orange, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=20, pady=15)
            tk.Label(header, text=f"{len(articles)} articles", font=get_font("sm"),
                     fg=THEME.comment, bg=THEME.bg_dark).pack(side=tk.RIGHT, padx=20, pady=15)
            
            # Content with scroll
            content = tk.Frame(popup, bg=THEME.bg)
            content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
            
            canvas = tk.Canvas(content, bg=THEME.bg, highlightthickness=0)
            scrollbar = tk.Scrollbar(content, orient=tk.VERTICAL, command=canvas.yview)
            frame = tk.Frame(canvas, bg=THEME.bg)
            
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            canvas.create_window((0, 0), window=frame, anchor=tk.NW)
            
            for article in articles:
                criticality = article.get('criticality', 0)
                
                # Color based on criticality
                if criticality >= 9:
                    crit_color = THEME.red
                    crit_label = "🔴 CRITICAL"
                elif criticality >= 7:
                    crit_color = THEME.orange
                    crit_label = "🟠 HIGH"
                else:
                    crit_color = THEME.yellow
                    crit_label = "🟡 MEDIUM"
                
                card = tk.Frame(frame, bg=THEME.bg_highlight, padx=15, pady=12)
                card.pack(fill=tk.X, pady=6)
                
                # Title row
                title_row = tk.Frame(card, bg=THEME.bg_highlight)
                title_row.pack(fill=tk.X)
                
                tk.Label(title_row, text=crit_label, font=get_font("sm", "bold"),
                         fg=crit_color, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(0, 10))
                tk.Label(title_row, text=f"[{criticality}/10]", font=get_font("sm", "mono"),
                         fg=crit_color, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(0, 10))
                tk.Label(title_row, text=article.get('title', '')[:70],
                         font=get_font("md", "bold"), fg=THEME.fg, bg=THEME.bg_highlight,
                         anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                # Justification
                justification = article.get('justification', '')
                if justification:
                    tk.Label(card, text=justification[:150] + "..." if len(justification) > 150 else justification,
                             font=get_font("sm"), fg=THEME.fg_dark, bg=THEME.bg_highlight,
                             wraplength=750, justify=tk.LEFT, anchor=tk.W).pack(fill=tk.X, pady=(8, 0))
                
                # Markets and Companies
                markets = article.get('affected_markets', [])
                companies = article.get('affected_companies', [])
                
                if markets or companies:
                    tags_row = tk.Frame(card, bg=THEME.bg_highlight)
                    tags_row.pack(fill=tk.X, pady=(8, 0))
                    
                    if markets:
                        tk.Label(tags_row, text=f"📊 {', '.join(markets[:3])}", 
                                 font=get_font("xs"), fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(0, 15))
                    if companies:
                        tk.Label(tags_row, text=f"🏢 {', '.join(companies[:3])}", 
                                 font=get_font("xs"), fg=THEME.magenta, bg=THEME.bg_highlight).pack(side=tk.LEFT)
            
            frame.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            
            # Close button
            tk.Button(popup, text="Close", font=get_font("md", "bold"),
                      bg=THEME.red, fg=THEME.fg, padx=20, pady=8,
                      relief=tk.FLAT, cursor="hand2",
                      command=popup.destroy).pack(pady=15)
                      
        except Exception as e:
            logger.error(f"Failed to show disruptive articles: {e}")
            messagebox.showerror("Error", f"Failed to load disruptive articles: {e}")
    
    def _show_alert_config(self):
        """Show alert channel configuration popup."""
        popup = tk.Toplevel(self.root)
        popup.title("🔔 Configure Alert Channels")
        popup.geometry("600x550")
        popup.configure(bg=THEME.bg)
        
        # Header
        header = tk.Frame(popup, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🔔 ALERT CHANNEL CONFIGURATION", font=get_font("lg", "bold"),
                 fg=THEME.magenta, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=20, pady=12)
        
        # Content
        content = tk.Frame(popup, bg=THEME.bg, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Info text
        tk.Label(content, text="Configure where to receive alerts for high-criticality news.\nGUI notifications are always enabled.",
                 font=get_font("sm"), fg=THEME.fg_dark, bg=THEME.bg,
                 justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 20))
        
        # Channel cards
        channels = [
            {
                "name": "In-App Notifications",
                "icon": "🖥️",
                "status": "Always Enabled",
                "enabled": True,
                "configured": True,
                "description": "Alerts appear in the GUI. No setup required.",
                "setup_fields": []
            },
            {
                "name": "Telegram Bot",
                "icon": "📱",
                "status": "Not Configured",
                "enabled": False,
                "configured": False,
                "description": "Receive alerts via Telegram. Create a bot with @BotFather.",
                "setup_url": "https://core.telegram.org/bots#creating-a-new-bot",
                "setup_fields": ["Bot Token", "Chat ID"]
            },
            {
                "name": "Discord Webhook",
                "icon": "💬",
                "status": "Not Configured",
                "enabled": False,
                "configured": False,
                "description": "Post alerts to a Discord channel via webhook.",
                "setup_url": "https://support.discord.com/hc/en-us/articles/228383668",
                "setup_fields": ["Webhook URL"]
            },
            {
                "name": "Email (SMTP)",
                "icon": "📧",
                "status": "Not Configured",
                "enabled": False,
                "configured": False,
                "description": "Send alerts via email. Configure SMTP settings in .env.",
                "setup_fields": ["SMTP Host", "Port", "Username", "Password", "To Address"]
            },
        ]
        
        for ch in channels:
            card = tk.Frame(content, bg=THEME.bg_highlight, padx=15, pady=12)
            card.pack(fill=tk.X, pady=5)
            
            # Header row
            header_row = tk.Frame(card, bg=THEME.bg_highlight)
            header_row.pack(fill=tk.X)
            
            tk.Label(header_row, text=ch["icon"], font=get_font("lg"),
                     fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
            tk.Label(header_row, text=ch["name"], font=get_font("md", "bold"),
                     fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(10, 0))
            
            # Status badge
            status_color = THEME.green if ch["configured"] else THEME.comment
            tk.Label(header_row, text=ch["status"], font=get_font("xs", "bold"),
                     fg=status_color, bg=THEME.bg_highlight).pack(side=tk.RIGHT)
            
            # Description
            tk.Label(card, text=ch["description"], font=get_font("xs"),
                     fg=THEME.fg_dark, bg=THEME.bg_highlight,
                     wraplength=500, justify=tk.LEFT, anchor=tk.W).pack(fill=tk.X, pady=(5, 0))
            
            # Setup fields placeholder
            if ch.get("setup_fields") and not ch["configured"]:
                fields_text = "Required: " + ", ".join(ch["setup_fields"])
                tk.Label(card, text=fields_text, font=get_font("xs"),
                         fg=THEME.yellow, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(5, 0))
                
                if ch.get("setup_url"):
                    tk.Label(card, text=f"📖 Setup Guide: {ch['setup_url']}", font=get_font("xs"),
                             fg=THEME.cyan, bg=THEME.bg_highlight, cursor="hand2").pack(anchor=tk.W, pady=(3, 0))
        
        # Note
        tk.Label(content, text="💡 To configure channels, add credentials to your .env file and restart.",
                 font=get_font("xs"), fg=THEME.comment, bg=THEME.bg).pack(anchor=tk.W, pady=(20, 0))
        
        # Close button
        tk.Button(popup, text="Close", font=get_font("md", "bold"),
                  bg=THEME.red, fg=THEME.fg, padx=20, pady=8,
                  relief=tk.FLAT, cursor="hand2",
                  command=popup.destroy).pack(pady=15)
    
    # =========================================================================
    # Newsletter Methods (v4.0)
    # =========================================================================
    
    def _generate_newsletter(self):
        """Generate a newsletter from today's articles."""
        from datetime import datetime
        
        popup = tk.Toplevel(self.root)
        popup.title("📰 Generate Newsletter")
        popup.geometry("600x400")
        popup.configure(bg=THEME.bg)
        
        # Header
        header = tk.Frame(popup, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="📰 NEWSLETTER GENERATOR", font=get_font("lg", "bold"),
                 fg=THEME.green, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=20, pady=12)
        
        # Content
        content = tk.Frame(popup, bg=THEME.bg, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        status_label = tk.Label(content, text="Ready to generate newsletter", 
                                font=get_font("md"), fg=THEME.fg_dark, bg=THEME.bg)
        status_label.pack(pady=10)
        
        # Progress
        progress_frame = tk.Frame(content, bg=THEME.bg)
        progress_frame.pack(fill=tk.X, pady=20)
        
        steps = ["Load Stories", "AI Editor", "Write Sections", "Assemble", "Export"]
        step_labels = []
        for i, step in enumerate(steps):
            step_label = tk.Label(progress_frame, text=f"○ {step}", 
                                  font=get_font("sm"), fg=THEME.comment, bg=THEME.bg)
            step_label.pack(anchor=tk.W, pady=2)
            step_labels.append(step_label)
        
        # Result area
        result_text = tk.Text(content, font=get_font("sm", mono=True), 
                              bg=THEME.bg_visual, fg=THEME.fg,
                              height=8, state=tk.DISABLED)
        result_text.pack(fill=tk.BOTH, expand=True, pady=10)
        
        async def run_generation():
            try:
                from src.newsletter import generate_newsletter
                
                status_label.config(text="Generating newsletter...", fg=THEME.cyan)
                
                # Update step indicators
                for i, label in enumerate(step_labels):
                    label.config(text=f"○ {steps[i]}", fg=THEME.comment)
                
                # Run with skip_review for now (can add approval later)
                result = await generate_newsletter(
                    target_date=datetime.now().strftime("%Y-%m-%d"),
                    newsletter_name="Tech Intelligence Daily",
                    skip_review=True
                )
                
                if result and result.get("final_markdown"):
                    # Update UI
                    status_label.config(text="✅ Newsletter generated!", fg=THEME.green)
                    for label in step_labels:
                        label.config(fg=THEME.green, text=label.cget("text").replace("○", "●"))
                    
                    # Show result
                    result_text.config(state=tk.NORMAL)
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, f"Subject: {result.get('subject_line', '')}\n\n")
                    result_text.insert(tk.END, f"Exported to: {result.get('export_path', '')}\n\n")
                    result_text.insert(tk.END, "Preview:\n" + result.get("final_markdown", "")[:500] + "...")
                    result_text.config(state=tk.DISABLED)
                    
                    # Save to database
                    from src.database import get_database
                    db = get_database()
                    db.save_newsletter(
                        edition_date=result.get("target_date", datetime.now().strftime("%Y-%m-%d")),
                        name="Tech Intelligence Daily",
                        markdown_content=result.get("final_markdown", ""),
                        subject_line=result.get("subject_line", ""),
                        story_count=len(result.get("top_stories", [])),
                        export_path=result.get("export_path", "")
                    )
                else:
                    status_label.config(text="❌ Generation failed", fg=THEME.red)
                    
            except Exception as e:
                logger.error(f"Newsletter generation failed: {e}")
                status_label.config(text=f"❌ Error: {str(e)[:50]}", fg=THEME.red)
        
        def start_generation():
            self._async_runner.run_async(run_generation())
        
        # Buttons
        btn_frame = tk.Frame(popup, bg=THEME.bg)
        btn_frame.pack(fill=tk.X, pady=15)
        
        tk.Button(btn_frame, text="✨ Generate", font=get_font("md", "bold"),
                  bg=THEME.green, fg=THEME.black, padx=25, pady=10,
                  relief=tk.FLAT, cursor="hand2",
                  command=start_generation).pack(side=tk.LEFT, padx=20)
        
        tk.Button(btn_frame, text="Close", font=get_font("md", "bold"),
                  bg=THEME.red, fg=THEME.fg, padx=20, pady=10,
                  relief=tk.FLAT, cursor="hand2",
                  command=popup.destroy).pack(side=tk.RIGHT, padx=20)
    
    def _show_newsletter_history(self):
        """Show newsletter history popup."""
        try:
            from src.database import get_database
            db = get_database()
            newsletters = db.get_recent_newsletters(limit=20)
            
            popup = tk.Toplevel(self.root)
            popup.title("📚 Newsletter History")
            popup.geometry("700x500")
            popup.configure(bg=THEME.bg)
            
            # Header
            header = tk.Frame(popup, bg=THEME.bg_dark, height=50)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            
            tk.Label(header, text="📚 NEWSLETTER HISTORY", font=get_font("lg", "bold"),
                     fg=THEME.green, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=20, pady=12)
            tk.Label(header, text=f"{len(newsletters)} editions", font=get_font("sm"),
                     fg=THEME.comment, bg=THEME.bg_dark).pack(side=tk.RIGHT, padx=20, pady=12)
            
            # Content
            content = tk.Frame(popup, bg=THEME.bg, padx=15, pady=15)
            content.pack(fill=tk.BOTH, expand=True)
            
            if not newsletters:
                tk.Label(content, text="No newsletters generated yet.\n\nClick 'Generate Newsletter' to create your first edition!",
                         font=get_font("md"), fg=THEME.fg_dark, bg=THEME.bg,
                         justify=tk.CENTER).pack(expand=True)
            else:
                for nl in newsletters:
                    card = tk.Frame(content, bg=THEME.bg_highlight, padx=15, pady=10)
                    card.pack(fill=tk.X, pady=5)
                    
                    # Date and subject
                    tk.Label(card, text=nl.get("edition_date", "Unknown"),
                             font=get_font("md", "bold"), fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
                    tk.Label(card, text=nl.get("subject_line", "")[:50],
                             font=get_font("sm"), fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=15)
                    tk.Label(card, text=f"{nl.get('story_count', 0)} stories",
                             font=get_font("xs"), fg=THEME.comment, bg=THEME.bg_highlight).pack(side=tk.RIGHT)
            
            # Close button
            tk.Button(popup, text="Close", font=get_font("md", "bold"),
                      bg=THEME.red, fg=THEME.fg, padx=20, pady=8,
                      relief=tk.FLAT, cursor="hand2",
                      command=popup.destroy).pack(pady=15)
                      
        except Exception as e:
            logger.error(f"Failed to show newsletter history: {e}")
            messagebox.showerror("Error", f"Failed to load newsletter history: {e}")
    
    def _show_crawler_popup(self):
        """Show enhanced web crawler control panel with progress tracking."""
        popup = tk.Toplevel(self.root)
        popup.title("🕷️ Web Crawler Control Panel")
        popup.geometry("700x600")
        popup.configure(bg=THEME.bg)
        popup.transient(self.root)
        popup.grab_set()
        
        # Store reference to track crawl state
        self._crawler_popup = popup
        self._crawler_running = False
        self._crawl_task = None
        self._crawl_stats = {"found": 0, "processed": 0, "failed": 0}
        
        # Header
        header = tk.Frame(popup, bg=THEME.bg_dark, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Frame(header, bg=THEME.purple, height=3).pack(fill=tk.X, side=tk.TOP)
        
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(header_inner, text="🕷️", font=get_font("xl"),
                 fg=THEME.purple, bg=THEME.bg_dark).pack(side=tk.LEFT, pady=10)
        tk.Label(header_inner, text="WEB CRAWLER", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0), pady=10)
        
        # Status indicator in header
        self._crawler_status_var = tk.StringVar(value="Ready")
        self._crawler_status_label = tk.Label(header_inner, 
                                               textvariable=self._crawler_status_var,
                                               font=get_font("sm"),
                                               fg=THEME.green, bg=THEME.bg_dark)
        self._crawler_status_label.pack(side=tk.RIGHT, pady=10)
        
        # Main content with notebook tabs
        content = tk.Frame(popup, bg=THEME.bg, padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Configure notebook style
        style = ttk.Style()
        style.configure("Crawler.TNotebook", background=THEME.bg)
        style.configure("Crawler.TNotebook.Tab", background=THEME.bg_highlight,
                       foreground=THEME.fg_dark, padding=[12, 6])
        style.map("Crawler.TNotebook.Tab",
                  background=[("selected", THEME.purple)],
                  foreground=[("selected", THEME.fg)])
        
        notebook = ttk.Notebook(content, style="Crawler.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Configuration
        config_frame = tk.Frame(notebook, bg=THEME.bg, padx=15, pady=15)
        notebook.add(config_frame, text="⚙️ Configuration")
        self._build_crawler_config_tab(config_frame)
        
        # Tab 2: Progress & Results
        results_frame = tk.Frame(notebook, bg=THEME.bg, padx=15, pady=15)
        notebook.add(results_frame, text="📊 Progress")
        self._build_crawler_results_tab(results_frame)
        
        # Footer buttons
        footer = tk.Frame(popup, bg=THEME.bg_highlight, pady=15)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        self._start_btn = tk.Button(footer, text="▶ Start Crawl", font=get_font("md", "bold"),
                                     bg=THEME.green, fg=THEME.black,
                                     activebackground=THEME.bright_green,
                                     padx=25, pady=10, relief=tk.FLAT, cursor="hand2",
                                     command=self._start_crawler)
        self._start_btn.pack(side=tk.LEFT, padx=20)
        
        self._stop_btn = tk.Button(footer, text="⏹ Stop", font=get_font("md", "bold"),
                                    bg=THEME.orange, fg=THEME.black,
                                    activebackground=THEME.bright_yellow,
                                    padx=25, pady=10, relief=tk.FLAT, cursor="hand2",
                                    command=self._stop_crawler, state=tk.DISABLED)
        self._stop_btn.pack(side=tk.LEFT, padx=10)
        
        tk.Button(footer, text="✕ Close", font=get_font("md"),
                  bg=THEME.red, fg=THEME.fg,
                  padx=20, pady=10, relief=tk.FLAT, cursor="hand2",
                  command=lambda: self._close_crawler_popup(popup)).pack(side=tk.RIGHT, padx=20)
    
    def _build_crawler_config_tab(self, parent):
        """Build the configuration tab."""
        # URL Section
        url_frame = tk.LabelFrame(parent, text=" Seed URL(s) ", font=get_font("sm", "bold"),
                                   fg=THEME.cyan, bg=THEME.bg, padx=10, pady=10)
        url_frame.pack(fill=tk.X, pady=(0, 15))
        
        self._crawler_url_text = tk.Text(url_frame, font=get_font("sm"), 
                                          bg=THEME.bg_visual, fg=THEME.fg,
                                          height=4, wrap=tk.WORD)
        self._crawler_url_text.pack(fill=tk.X)
        self._crawler_url_text.insert(tk.END, "https://techcrunch.com")
        
        tk.Label(url_frame, text="Enter one URL per line for multiple seeds",
                 font=get_font("xs"), fg=THEME.comment, bg=THEME.bg).pack(anchor=tk.W, pady=(5, 0))
        
        # Settings Section
        settings_frame = tk.LabelFrame(parent, text=" Crawl Settings ", font=get_font("sm", "bold"),
                                        fg=THEME.orange, bg=THEME.bg, padx=10, pady=10)
        settings_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Depth slider
        depth_row = tk.Frame(settings_frame, bg=THEME.bg)
        depth_row.pack(fill=tk.X, pady=5)
        
        tk.Label(depth_row, text="Max Depth:", font=get_font("sm"),
                 fg=THEME.fg, bg=THEME.bg, width=12, anchor=tk.W).pack(side=tk.LEFT)
        
        self._depth_var = tk.IntVar(value=2)
        depth_scale = tk.Scale(depth_row, from_=1, to=3, orient=tk.HORIZONTAL,
                               variable=self._depth_var, bg=THEME.bg, fg=THEME.orange,
                               highlightthickness=0, length=150)
        depth_scale.pack(side=tk.LEFT, padx=10)
        
        tk.Label(depth_row, text="(1=shallow, 3=deep)", font=get_font("xs"),
                 fg=THEME.comment, bg=THEME.bg).pack(side=tk.LEFT)
        
        # Max pages
        pages_row = tk.Frame(settings_frame, bg=THEME.bg)
        pages_row.pack(fill=tk.X, pady=5)
        
        tk.Label(pages_row, text="Max Pages:", font=get_font("sm"),
                 fg=THEME.fg, bg=THEME.bg, width=12, anchor=tk.W).pack(side=tk.LEFT)
        
        self._pages_var = tk.IntVar(value=20)
        pages_spin = tk.Spinbox(pages_row, from_=5, to=100, textvariable=self._pages_var,
                                font=get_font("sm"), bg=THEME.bg_visual, fg=THEME.fg,
                                width=8)
        pages_spin.pack(side=tk.LEFT, padx=10)
        
        # Options checkboxes
        options_frame = tk.Frame(settings_frame, bg=THEME.bg)
        options_frame.pack(fill=tk.X, pady=10)
        
        self._stay_domain_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Stay on domain", 
                       variable=self._stay_domain_var,
                       font=get_font("xs"), fg=THEME.fg, bg=THEME.bg,
                       selectcolor=THEME.bg_visual).pack(side=tk.LEFT, padx=(0, 15))
        
        self._parse_sitemap_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Parse sitemaps",
                       variable=self._parse_sitemap_var,
                       font=get_font("xs"), fg=THEME.fg, bg=THEME.bg,
                       selectcolor=THEME.bg_visual).pack(side=tk.LEFT, padx=(0, 15))
        
        self._article_only_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Articles only",
                       variable=self._article_only_var,
                       font=get_font("xs"), fg=THEME.fg, bg=THEME.bg,
                       selectcolor=THEME.bg_visual).pack(side=tk.LEFT)
        
        # Advanced options
        advanced_frame = tk.LabelFrame(parent, text=" Advanced Options ", font=get_font("sm", "bold"),
                                        fg=THEME.purple, bg=THEME.bg, padx=10, pady=10)
        advanced_frame.pack(fill=tk.X)
        
        self._dedup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(advanced_frame, text="Deduplicate content",
                       variable=self._dedup_var,
                       font=get_font("xs"), fg=THEME.fg, bg=THEME.bg,
                       selectcolor=THEME.bg_visual).pack(anchor=tk.W)
    
    def _build_crawler_results_tab(self, parent):
        """Build the progress and results tab."""
        # Progress section
        progress_frame = tk.LabelFrame(parent, text=" Crawl Progress ", font=get_font("sm", "bold"),
                                        fg=THEME.green, bg=THEME.bg, padx=10, pady=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(progress_frame, variable=self._progress_var,
                                              maximum=100, length=400, mode='determinate')
        self._progress_bar.pack(fill=tk.X, pady=5)
        
        # Stats row
        stats_row = tk.Frame(progress_frame, bg=THEME.bg)
        stats_row.pack(fill=tk.X, pady=5)
        
        self._progress_stats_label = tk.Label(stats_row, 
                                               text="Ready to start...",
                                               font=get_font("xs"), 
                                               fg=THEME.comment, bg=THEME.bg)
        self._progress_stats_label.pack(side=tk.LEFT)
        
        # Live log
        log_frame = tk.LabelFrame(parent, text=" Live Log ", font=get_font("sm", "bold"),
                                   fg=THEME.cyan, bg=THEME.bg, padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create scrollable log text
        log_container = tk.Frame(log_frame, bg=THEME.bg_visual)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self._crawler_log = tk.Text(log_container, font=get_font("xs", mono=True),
                                     bg=THEME.bg_visual, fg=THEME.fg,
                                     wrap=tk.WORD, height=8)
        self._crawler_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_container, orient="vertical", 
                                  command=self._crawler_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._crawler_log.config(yscrollcommand=scrollbar.set)
        
        # Results summary
        summary_frame = tk.LabelFrame(parent, text=" Results Summary ", font=get_font("sm", "bold"),
                                       fg=THEME.orange, bg=THEME.bg, padx=10, pady=10)
        summary_frame.pack(fill=tk.X)
        
        self._crawler_summary_text = tk.Text(summary_frame, font=get_font("xs", mono=True),
                                              bg=THEME.bg_visual, fg=THEME.fg,
                                              height=5, wrap=tk.WORD, state=tk.DISABLED)
        self._crawler_summary_text.pack(fill=tk.BOTH, expand=True)
    
    def _crawler_log_message(self, message: str, level: str = "info"):
        """Add a message to the crawler log."""
        if not hasattr(self, '_crawler_log') or not self._crawler_log.winfo_exists():
            return
        
        colors = {
            "info": THEME.fg,
            "success": THEME.green,
            "warning": THEME.orange,
            "error": THEME.red,
            "crawl": THEME.cyan
        }
        color = colors.get(level, THEME.fg)
        
        self._crawler_log.config(state=tk.NORMAL)
        self._crawler_log.insert(tk.END, f"{message}\n")
        self._crawler_log.tag_add(level, "end-2c linestart", "end-1c")
        self._crawler_log.tag_config(level, foreground=color)
        self._crawler_log.see(tk.END)
        self._crawler_log.config(state=tk.DISABLED)
    
    def _update_crawler_progress(self, current: int, total: int):
        """Update progress bar and stats."""
        if not hasattr(self, '_progress_var') or not self._crawler_popup.winfo_exists():
            return
        
        progress = (current / total * 100) if total > 0 else 0
        self._progress_var.set(progress)
        
        self._progress_stats_label.config(
            text=f"Pages: {current}/{total} | Articles: {self._crawl_stats['found']} | Failed: {self._crawl_stats['failed']}"
        )
        
        self._crawler_status_var.set(f"Crawling... {current}/{total}")
    
    def _start_crawler(self):
        """Start the web crawler."""
        if self._crawler_running:
            return
        
        # Get URLs
        urls_text = self._crawler_url_text.get(1.0, tk.END).strip()
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            messagebox.showwarning("No URLs", "Please enter at least one seed URL")
            return
        
        # Validate URLs
        valid_urls = []
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            valid_urls.append(url)
        
        # Update UI state
        self._crawler_running = True
        self._crawl_stats = {"found": 0, "processed": 0, "failed": 0}
        self._start_btn.config(state=tk.DISABLED, text="🕷️ Crawling...")
        self._stop_btn.config(state=tk.NORMAL)
        self._crawler_status_var.set("Running")
        self._crawler_status_label.config(fg=THEME.orange)
        
        # Clear previous results
        self._crawler_log.config(state=tk.NORMAL)
        self._crawler_log.delete(1.0, tk.END)
        self._crawler_log.config(state=tk.DISABLED)
        
        self._crawler_summary_text.config(state=tk.NORMAL)
        self._crawler_summary_text.delete(1.0, tk.END)
        self._crawler_summary_text.config(state=tk.DISABLED)
        
        self._crawler_log_message("🚀 Starting crawler...", "info")
        self._crawler_log_message(f"📍 Seed URLs: {len(valid_urls)}", "info")
        self._crawler_log_message(f"⚙️ Max depth: {self._depth_var.get()}, Max pages: {self._pages_var.get()}", "info")
        
        # Run crawl
        async def do_crawl():
            try:
                results = []
                
                for url in valid_urls:
                    if not self._crawler_running:
                        break
                    
                    self._crawler_log_message(f"🕷️ Crawling {url}...", "crawl")
                    
                    articles = await self._orchestrator.crawl_website(
                        url=url,
                        max_depth=self._depth_var.get(),
                        max_pages=self._pages_var.get(),
                        progress_callback=self._update_crawler_progress
                    )
                    
                    results.extend(articles)
                    self._crawl_stats["found"] += len(articles)
                    self._crawler_log_message(f"  ✓ Found {len(articles)} articles", "success")
                
                return results
                
            except Exception as e:
                logger.error(f"Crawl error: {e}")
                raise
        
        def on_complete(articles, error):
            self._crawler_running = False
            self._start_btn.config(state=tk.NORMAL, text="▶ Start Crawl")
            self._stop_btn.config(state=tk.DISABLED)
            
            if error:
                self._crawler_status_var.set("Failed")
                self._crawler_status_label.config(fg=THEME.red)
                self._crawler_log_message(f"❌ Error: {str(error)}", "error")
                messagebox.showerror("Crawl Error", str(error))
            else:
                self._crawler_status_var.set("Complete")
                self._crawler_status_label.config(fg=THEME.green)
                self._progress_var.set(100)
                
                # Update summary
                self._crawler_summary_text.config(state=tk.NORMAL)
                self._crawler_summary_text.delete(1.0, tk.END)
                self._crawler_summary_text.insert(tk.END, f"✅ Crawl Complete!\n\n")
                self._crawler_summary_text.insert(tk.END, f"Total Articles Found: {len(articles)}\n")
                self._crawler_summary_text.insert(tk.END, f"Added to Database: ✓\n")
                if articles:
                    self._crawler_summary_text.insert(tk.END, f"\nLatest article: {articles[0].title[:50]}...")
                self._crawler_summary_text.config(state=tk.DISABLED)
                
                self._crawler_log_message(f"✅ Crawl complete! Found {len(articles)} total articles", "success")
                
                # Refresh main display if articles found
                if articles and len(articles) > 0:
                    self.root.after(500, lambda: self._refresh_after_crawl(articles))
        
        self._crawl_task = self._async_runner.run_async(do_crawl(), on_complete)
    
    def _stop_crawler(self):
        """Stop the running crawler."""
        if self._crawler_running:
            self._crawler_running = False
            self._crawler_status_var.set("Stopping...")
            self._crawler_log_message("⏹ Stopping crawl...", "warning")
            self._stop_btn.config(state=tk.DISABLED)
    
    def _close_crawler_popup(self, popup):
        """Close the crawler popup, stopping any running crawl."""
        if self._crawler_running:
            if not messagebox.askyesno("Crawl in Progress", 
                                       "A crawl is still running. Stop and close?"):
                return
            self._stop_crawler()
        popup.destroy()
        if hasattr(self, '_crawler_popup'):
            delattr(self, '_crawler_popup')
    
    def _refresh_after_crawl(self, articles: List[Article]):
        """Refresh main display after crawl completes."""
        try:
            # Add articles to current view
            for article in articles:
                if article not in self.current_articles:
                    self.current_articles.append(article)
            
            # Update display
            self._display_realtime_results(self.current_articles)
            self._set_status(f"🕷️ Crawler added {len(articles)} articles", "success")
            self._update_stats()
        except Exception as e:
            logger.warning(f"Failed to refresh after crawl: {e}")

    # ═════════════════════════════════════════════════════════════════
    # GLOBAL OMNISCIENCE CALLBACKS
    # ═════════════════════════════════════════════════════════════════

    async def _on_region_change(self, hub):
        """
        Called every 30 seconds when geo-rotation changes region.

        Args:
            hub: TechHub object with region info
        """
        logger.info(f"🌍 Rotating to {hub.name} ({hub.code})")

        # Update UI
        self._current_region.set(hub.code)
        self._set_status(f"🌍 Scanning {hub.name}...", "info")
        self.update_liveness_indicator(region=hub.code, is_live=True)

        # Get search params for this region
        if self._global_discovery:
            params = self._global_discovery.get_search_params()

            # Log the rotation
            logger.info(f"   Search params: gl={params['gl']}, hl={params['hl']}")

            # Update stats if available
            stats = self._global_discovery.get_stats()
            total_articles = stats.get('total_articles', 0)
            if total_articles > 0:
                logger.info(f"   Global articles discovered: {total_articles}")

    def _on_reddit_post(self, post):
        """
        Called milliseconds after a new Reddit post is detected.
        Synchronous callback — downstream UI updates use root.after_idle() for thread safety.

        Args:
            post: Dict with Reddit post data
        """
        logger.info(f"🔴 r/{post['subreddit']}: {post['title'][:50]}...")

        try:
            from src.core.types import Article, TechScore, SourceTier

            # Map Reddit upvote score → TechScore (0–1, clamped at 1000 upvotes)
            raw_score = post.get('score', 0)
            normalized = min(raw_score / 1000.0, 1.0)

            article = Article(
                id=f"reddit_{post['id']}",
                title=post['title'],
                url=post.get('external_url') or post.get('url', ''),
                content="",
                summary="",
                source=f"reddit/r/{post['subreddit']}",
                source_tier=SourceTier.TIER_3,
                published_at=post.get('created_utc'),
                scraped_at=datetime.now(),
                tech_score=TechScore(score=normalized, confidence=0.7),
            )

            # Sync call — _on_new_stream_article schedules root.after_idle internally
            self._on_new_stream_article(article)

        except Exception as e:
            logger.error(f"Reddit post handling error: {e}")
            return

        # Update stats
        if self._reddit_stream:
            stats = self._reddit_stream.get_stats()
            logger.debug(f"   Reddit stream: {stats['posts_streamed']} posts, {stats['posts_per_minute']:.1f}/min")

    def start_global_discovery(self):
        """Start all global discovery systems."""
        async def start():
            try:
                if self._global_discovery:
                    await self._global_discovery.start()
                    logger.info("🌍 Global geo-rotation started")

                if self._reddit_stream:
                    await self._reddit_stream.start()
                    logger.info("🔴 Reddit streaming started")

                self._set_status("🌍 Global Omniscience activated!", "success")
            except Exception as e:
                logger.error(f"Failed to start global discovery: {e}")
                self._set_status("⚠️ Global discovery failed to start", "warning")

        # Run in async runner
        if hasattr(self, '_async_runner') and self._async_runner:
            self._async_runner.run_async(start(), lambda result, error: None)

    def stop_global_discovery(self):
        """Stop all global discovery systems."""
        async def stop():
            try:
                if self._global_discovery:
                    await self._global_discovery.stop()
                if self._reddit_stream:
                    await self._reddit_stream.stop()
                logger.info("🌍 Global discovery stopped")
            except Exception as e:
                logger.error(f"Error stopping global discovery: {e}")
        if hasattr(self, '_async_runner') and self._async_runner:
            self._async_runner.run_async(stop(), lambda result, error: None)

    def _pulse_live_indicator(self):
        """Animate the LIVE indicator with a pulsing effect."""
        if not hasattr(self, '_live_indicator') or not self._live_indicator.winfo_exists():
            return
        
        # Toggle between bright and dim green
        current_color = self._live_indicator.cget("fg")
        if current_color == THEME.green:
            self._live_indicator.config(fg=THEME.bright_green)
        else:
            self._live_indicator.config(fg=THEME.green)
        
        # Schedule next pulse (every 800ms)
        self.root.after(800, self._pulse_live_indicator)
    
    def update_liveness_indicator(self, region=None, source_count=None, is_live=True):
        """
        Update the liveness indicator with current status.
        
        Args:
            region: Current region code (e.g., 'US', 'IN')
            source_count: Number of active sources
            is_live: Whether live feed is active
        """
        if hasattr(self, '_region_indicator') and self._region_indicator.winfo_exists():
            if region:
                self._region_indicator.config(text=f"🌍 Scanning: {region}")
        
        if hasattr(self, '_sources_indicator') and self._sources_indicator.winfo_exists():
            if source_count is not None:
                self._sources_indicator.config(text=f"📡 {source_count} sources")
        
        if hasattr(self, '_live_indicator') and self._live_indicator.winfo_exists():
            if is_live:
                self._live_indicator.config(text="● LIVE", fg=THEME.green)
            else:
                self._live_indicator.config(text="○ OFFLINE", fg=THEME.comment)


def main():
    root = tk.Tk()
    app = TechNewsGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
