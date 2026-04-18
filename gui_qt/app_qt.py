"""
Tech News Scraper v7.5 - PyQt6 Enterprise Edition

A full-featured, professional-grade interface with:
- Tokyo Night theme
- TechNewsOrchestrator integration
- Global Omniscience (19 tech hubs, Reddit streaming)
- Quantum Scraper with Rust acceleration
- Developer mode with full system control
- Real-time article streaming
- Keyboard shortcuts (F11/F12, Ctrl+M/R)
- Passcode-protected developer access

Usage:
    python -m gui_qt.app_qt
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow,
    QMenuBar, QPushButton, QStatusBar, QVBoxLayout,
    QWidget, QFrame, QComboBox
)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gui_qt.theme import apply_theme, COLORS
from gui_qt.utils.async_bridge import run_async, cleanup
from gui_qt.panels.feed_panel import FeedPanel
from gui_qt.panels.dashboard_panel import LiveDashboardPanel
from gui_qt.widgets.article_card import ArticleCard
from gui_qt.widgets.dialogs import (
    PreferencesDialog, StatisticsDialog, HistoryViewer, ExportDialog
)
from gui_qt.mode_manager import get_mode_manager, ModeState
from gui_qt.developer_dashboard import show_developer_dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeaderBar(QFrame):
    """
    Application header with branding, quantum toggle, and mode indicator.
    """
    
    quantum_toggled = pyqtSignal(bool)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"""
            HeaderBar {{
                background-color: {COLORS.bg_dark};
                border-bottom: 3px solid {COLORS.cyan};
            }}
        """)
        self.setFixedHeight(80)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(20)
        
        # Branding
        branding = QWidget()
        branding_layout = QHBoxLayout(branding)
        branding_layout.setContentsMargins(0, 0, 0, 0)
        branding_layout.setSpacing(10)
        
        logo = QLabel("⚡")
        logo.setStyleSheet(f"color: {COLORS.cyan}; font-size: 32px;")
        branding_layout.addWidget(logo)
        
        title = QLabel("TECH NEWS SCRAPER")
        title.setStyleSheet(f"color: {COLORS.fg}; font-size: 20px; font-weight: bold; letter-spacing: 1px;")
        branding_layout.addWidget(title)
        
        version = QLabel("v7.5")
        version.setStyleSheet(f"color: {COLORS.comment}; font-size: 12px; margin-top: 8px;")
        branding_layout.addWidget(version)
        
        layout.addWidget(branding)
        
        layout.addStretch()
        
        # Quantum Toggle
        self.quantum_btn = QPushButton("🌌 QUANTUM: OFF")
        self.quantum_btn.setCheckable(True)
        self.quantum_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quantum_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.comment};
                border: 1px solid {COLORS.border};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-family: "JetBrains Mono", monospace;
            }}
            QPushButton:checked {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.magenta};
                border: 1px solid {COLORS.magenta};
            }}
            QPushButton:hover {{
                border: 1px solid {COLORS.fg_dark};
            }}
        """)
        self.quantum_btn.toggled.connect(self._on_quantum_toggle)
        layout.addWidget(self.quantum_btn)
        
        # Mode Indicator
        self.mode_badge = QLabel("👤 USER")
        self.mode_badge.setStyleSheet(f"""
            background-color: {COLORS.blue};
            color: {COLORS.fg};
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
            font-size: 11px;
        """)
        layout.addWidget(self.mode_badge)
        
        # Time Label
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {COLORS.fg_dark}; font-size: 13px;")
        layout.addWidget(self.time_label)
        
        # Timer for clock
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()
        
        # Exit Button
        exit_btn = QPushButton("⏻ Exit")
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.red};
                color: {COLORS.fg};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bright_red};
            }}
        """)
        exit_btn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(exit_btn)

    def _update_time(self):
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _on_quantum_toggle(self, checked: bool):
        if checked:
            self.quantum_btn.setText("🌌 QUANTUM: ON")
        else:
            self.quantum_btn.setText("🌌 QUANTUM: OFF")
        self.quantum_toggled.emit(checked)
        
    def set_mode_indicator(self, mode: str):
        if mode == "developer":
            self.mode_badge.setText("⚡ DEV")
            self.mode_badge.setStyleSheet(f"""
                background-color: {COLORS.magenta};
                color: {COLORS.fg};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            """)
        else:
            self.mode_badge.setText("👤 USER")
            self.mode_badge.setStyleSheet(f"""
                background-color: {COLORS.blue};
                color: {COLORS.fg};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            """)


class Sidebar(QFrame):
    """Left sidebar with controls, storage mode, and live indicators."""
    
    start_feed_clicked = pyqtSignal()
    mode_changed = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet(f"background-color: {COLORS.bg_dark}; border-right: 1px solid {COLORS.border};")
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(24)
        
        # Start Feed Button
        self.start_btn = QPushButton("⚡ Start Live Feed")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setFixedHeight(50)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.cyan};
                color: {COLORS.bg_dark};
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bright_cyan};
            }}
            QPushButton:disabled {{
                background-color: {COLORS.bg_highlight};
                color: {COLORS.comment};
            }}
        """)
        self.start_btn.clicked.connect(self.start_feed_clicked.emit)
        layout.addWidget(self.start_btn)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS.border};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)
        
        # Live indicators
        self.live_frame = QFrame()
        self.live_frame.setStyleSheet(f"""
            background-color: {COLORS.bg_highlight};
            border-radius: 8px;
            padding: 12px;
        """)
        live_layout = QVBoxLayout(self.live_frame)
        live_layout.setSpacing(8)
        
        self.live_indicator = QLabel("● OFFLINE")
        self.live_indicator.setStyleSheet(f"color: {COLORS.comment}; font-weight: bold; font-size: 12px;")
        live_layout.addWidget(self.live_indicator)
        
        self.region_indicator = QLabel("🌍 Region: --")
        self.region_indicator.setStyleSheet(f"color: {COLORS.fg_dark}; font-size: 12px;")
        live_layout.addWidget(self.region_indicator)
        
        self.source_indicator = QLabel("📡 Sources: 0")
        self.source_indicator.setStyleSheet(f"color: {COLORS.fg_dark}; font-size: 12px;")
        live_layout.addWidget(self.source_indicator)
        
        layout.addWidget(self.live_frame)
        
        # Storage Mode section
        storage_label = QLabel("💾 Storage Mode")
        storage_label.setStyleSheet(f"color: {COLORS.fg}; font-weight: bold; font-size: 13px;")
        layout.addWidget(storage_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["⚡ Ephemeral", "🔄 Hybrid", "💿 Persistent"])
        self.mode_combo.setCurrentIndex(1)  # Default to Hybrid
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.fg};
                border: 1px solid {COLORS.border};
                border-radius: 6px;
                padding: 8px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_change)
        layout.addWidget(self.mode_combo)
        
        mode_desc = QLabel("Live feed + AI cache")
        mode_desc.setStyleSheet(f"color: {COLORS.comment}; font-size: 11px;")
        self.mode_desc = mode_desc
        layout.addWidget(mode_desc)
        
        # Stats section
        layout.addSpacing(20)
        
        stats_label = QLabel("📊 Statistics")
        stats_label.setStyleSheet(f"color: {COLORS.fg}; font-weight: bold; font-size: 13px;")
        layout.addWidget(stats_label)
        
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(f"""
            background-color: {COLORS.bg_visual};
            border-radius: 8px;
            padding: 16px;
        """)
        stats_layout = QVBoxLayout(self.stats_frame)
        stats_layout.setSpacing(12)
        
        self.stats_articles = QLabel("📰 Articles: 0")
        self.stats_articles.setStyleSheet(f"color: {COLORS.fg_dark}; font-size: 12px;")
        stats_layout.addWidget(self.stats_articles)
        
        self.stats_sources = QLabel("🔗 Sources: 0")
        self.stats_sources.setStyleSheet(f"color: {COLORS.fg_dark}; font-size: 12px;")
        stats_layout.addWidget(self.stats_sources)
        
        self.stats_saved = QLabel("💾 Saved: 0")
        self.stats_saved.setStyleSheet(f"color: {COLORS.fg_dark}; font-size: 12px;")
        stats_layout.addWidget(self.stats_saved)
        
        layout.addWidget(self.stats_frame)
        
        layout.addStretch()
        
        # Watermark
        watermark = QLabel("Architected by Sci_Coder")
        watermark.setStyleSheet(f"color: {COLORS.comment}; font-size: 10px; opacity: 0.5;")
        watermark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(watermark)
    
    def _on_mode_change(self, index: int) -> None:
        modes = ["ephemeral", "hybrid", "persistent"]
        descriptions = [
            "Articles auto-expire (2hr TTL)",
            "Live feed + AI cache",
            "Full database storage"
        ]
        
        self.mode_desc.setText(descriptions[index])
        if 0 <= index < len(modes):
            self.mode_changed.emit(modes[index])
    
    def update_stats(self, articles: int = 0, sources: int = 0, saved: int = 0) -> None:
        """Update statistics display."""
        self.stats_articles.setText(f"📰 Articles: {articles}")
        self.stats_sources.setText(f"🔗 Sources: {sources}")
        self.stats_saved.setText(f"💾 Saved: {saved}")
    
    def set_fetching(self, is_fetching: bool) -> None:
        """Update button state during fetch."""
        if is_fetching:
            self.start_btn.setText("⏳ Fetching...")
            self.start_btn.setEnabled(False)
        else:
            self.start_btn.setText("⚡ Start Live Feed")
            self.start_btn.setEnabled(True)
    
    def set_live_status(self, is_live: bool, region: str = "", source_count: int = 0) -> None:
        """Update live indicators."""
        if is_live:
            self.live_indicator.setText("● LIVE")
            self.live_indicator.setStyleSheet(f"color: {COLORS.green}; font-weight: bold; font-size: 12px;")
            self.region_indicator.setText(f"🌍 Region: {region}")
            self.source_indicator.setText(f"📡 Sources: {source_count}")
        else:
            self.live_indicator.setText("○ OFFLINE")
            self.live_indicator.setStyleSheet(f"color: {COLORS.comment}; font-weight: bold; font-size: 12px;")


class TechNewsApp(QMainWindow):
    """
    Main application window with full feature parity.
    
    Features:
    - TechNewsOrchestrator integration
    - Global Omniscience (19 tech hubs, Reddit streaming)
    - Quantum Scraper with Rust acceleration
    - Developer mode with passcode protection
    - Real-time article streaming
    - Keyboard shortcuts (F11/F12, Ctrl+M/R)
    """
    
    VERSION = "7.5"
    
    def __init__(self) -> None:
        super().__init__()
        
        self.setWindowTitle(f"Tech News Scraper v{self.VERSION}")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        # State
        self.articles: List[Dict[str, Any]] = []
        self.saved_articles: set = set()
        self._fetching = False
        self.quantum_enabled = False
        self._current_region = "US"
        
        # Core components
        self._orchestrator = None
        self._pipeline = None
        self._global_discovery = None
        self._reddit_stream = None
        self._proxy_router = None
        self._quantum_scraper = None
        self._quantum_bypass = None
        
        # Mode manager
        self._mode_manager = get_mode_manager(self)
        
        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._init_all_systems()
        
        logger.info(f"Tech News Scraper v{self.VERSION} (PyQt6 Enterprise) started")
    
    def _setup_ui(self) -> None:
        """Build the main UI."""
        # Central widget
        central = QWidget()
        central.setStyleSheet(f"background-color: {COLORS.bg};")
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        self.header = HeaderBar()
        main_layout.addWidget(self.header)
        
        # Content area (sidebar + feed + dashboard)
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        content.addWidget(self.sidebar)
        
        # Feed panel
        self.feed_panel = FeedPanel(on_save=self._on_article_saved)
        content.addWidget(self.feed_panel, 1)
        
        # Live Dashboard (right panel)
        self.dashboard = LiveDashboardPanel()
        content.addWidget(self.dashboard)
        
        content_widget = QWidget()
        content_widget.setLayout(content)
        main_layout.addWidget(content_widget, 1)
        
        # Menu bar
        self._setup_menu_bar()
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"background-color: {COLORS.bg_dark}; color: {COLORS.fg}; border-top: 1px solid {COLORS.border};")
        self.setStatusBar(self.status_bar)
        self._set_status("Ready - Press F12 for Developer Mode or click 'Start Live Feed'")
    
    def _setup_menu_bar(self) -> None:
        """Setup application menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        prefs_action = QAction("⚙️ Preferences", self)
        prefs_action.setShortcut("Ctrl+,")
        prefs_action.triggered.connect(self._show_preferences)
        file_menu.addAction(prefs_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        
        stats_action = QAction("📊 Statistics", self)
        stats_action.setShortcut("Ctrl+I")
        stats_action.triggered.connect(self._show_statistics)
        view_menu.addAction(stats_action)
        
        history_action = QAction("📜 History", self)
        history_action.setShortcut("Ctrl+H")
        history_action.triggered.connect(self._show_history)
        view_menu.addAction(history_action)
        
        view_menu.addSeparator()
        
        toggle_dash_action = QAction("🖥️ Toggle Dashboard", self)
        toggle_dash_action.setShortcut("Ctrl+D")
        toggle_dash_action.triggered.connect(self._toggle_dashboard)
        view_menu.addAction(toggle_dash_action)
        
        # Developer menu (only visible in dev mode)
        self.dev_menu = menu_bar.addMenu("Developer")
        
        dev_dashboard_action = QAction("🛠️ Dashboard", self)
        dev_dashboard_action.setShortcut("Ctrl+Shift+D")
        dev_dashboard_action.triggered.connect(self._show_developer_dashboard)
        self.dev_menu.addAction(dev_dashboard_action)
        
        change_passcode_action = QAction("🔐 Change Passcode", self)
        change_passcode_action.triggered.connect(self._change_dev_passcode)
        self.dev_menu.addAction(change_passcode_action)
        
        # Hide dev menu initially
        self.dev_menu.menuAction().setVisible(False)
        
        # Export menu
        export_menu = menu_bar.addMenu("Export")
        
        export_action = QAction("📤 Export Articles", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._show_export)
        export_menu.addAction(export_action)
    
    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # F11 - User Mode
        user_shortcut = QShortcut(QKeySequence("F11"), self)
        user_shortcut.activated.connect(lambda: self._request_mode_switch('user'))
        
        # F12 - Developer Mode (with passcode)
        dev_shortcut = QShortcut(QKeySequence("F12"), self)
        dev_shortcut.activated.connect(lambda: self._request_mode_switch('developer'))
        
        # Ctrl+M - Toggle mode
        mode_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        mode_shortcut.activated.connect(self._toggle_mode)
        
        # Ctrl+R - Refresh/Start feed
        refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_shortcut.activated.connect(self._start_live_feed)
        
        logger.info("Keyboard shortcuts registered: F11 (User), F12 (Developer), Ctrl+M (Toggle), Ctrl+R (Refresh)")
    
    def _init_all_systems(self) -> None:
        """Initialize all systems asynchronously."""
        async def init():
            await self._init_orchestrator()
            await self._init_pipeline()
            await self._init_global_discovery()
            await self._init_reddit_stream()
            await self._init_smart_proxy()
            await self._init_quantum_scraper()
        
        run_async(init())
    
    async def _init_orchestrator(self) -> None:
        """Initialize TechNewsOrchestrator."""
        try:
            from src.engine import TechNewsOrchestrator
            
            self._orchestrator = TechNewsOrchestrator()
            
            # Load existing articles from database
            await self._load_existing_articles()
            
            logger.info("✓ TechNewsOrchestrator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
    
    async def _load_existing_articles(self) -> None:
        """Load existing articles from database and display them."""
        try:
            from src.database import get_database
            
            db = get_database()
            articles = db.get_all_articles()
            
            if articles:
                # Convert to dicts using the same method as fetch
                article_dicts = []
                for a in articles:
                    article_dicts.append(self._convert_article_to_dict(a))
                
                self.articles = article_dicts
                
                # Schedule UI update on main thread
                def update_ui():
                    try:
                        self.feed_panel.set_articles(article_dicts)
                        
                        # Update stats
                        sources = set(a.get("source", "") for a in article_dicts)
                        self.sidebar.update_stats(
                            articles=len(article_dicts),
                            sources=len(sources),
                            saved=len(self.saved_articles)
                        )
                        
                        self._set_status(f"📚 Loaded {len(article_dicts)} existing articles from database")
                        logger.info(f"Loaded {len(article_dicts)} existing articles")
                    except Exception as ui_error:
                        logger.error(f"Error updating UI: {ui_error}")
                
                # Use QTimer to schedule on main thread
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, update_ui)
                
        except Exception as e:
            logger.warning(f"Could not load existing articles: {e}")
    
    async def _init_pipeline(self) -> None:
        """Initialize EnhancedNewsPipeline."""
        try:
            from src.engine.enhanced_feeder import EnhancedNewsPipeline
            
            self._pipeline = EnhancedNewsPipeline(
                enable_discovery=True,
                max_articles=500,
                max_age_hours=48,
            )
            await self._pipeline.start()
            
            # Set up article callback
            if hasattr(self._pipeline, 'on_article'):
                self._pipeline.on_article = self._on_new_stream_article
            
            logger.info("✓ Pipeline initialized")
            self._set_status("All systems ready")
        except Exception as e:
            logger.error(f"Pipeline init failed: {e}")
            self._set_status(f"Pipeline error: {e}", "error")
    
    async def _init_global_discovery(self) -> None:
        """Initialize Global Discovery with geo-rotation."""
        try:
            from src.discovery.global_discovery import get_global_discovery_manager
            
            self._global_discovery = get_global_discovery_manager()
            if self._global_discovery:
                self._global_discovery.on_new_region = self._on_region_change
                await self._global_discovery.start()
                logger.info("✓ Global discovery started (19 tech hubs, 30s rotation)")
        except Exception as e:
            logger.warning(f"Global discovery not available: {e}")
    
    async def _init_reddit_stream(self) -> None:
        """Initialize Reddit streaming."""
        try:
            from src.sources.reddit_stream import get_reddit_stream_client
            
            self._reddit_stream = get_reddit_stream_client()
            if self._reddit_stream:
                self._reddit_stream.on_new_post = self._on_reddit_post
                await self._reddit_stream.start()
                logger.info("✓ Reddit streaming started")
        except Exception as e:
            logger.warning(f"Reddit stream not available: {e}")
    
    async def _init_smart_proxy(self) -> None:
        """Initialize Smart Proxy Router."""
        try:
            from src.bypass.smart_proxy_router import get_smart_proxy_router
            
            self._proxy_router = get_smart_proxy_router()
            if self._proxy_router:
                logger.info("✓ Smart proxy router initialized")
        except Exception as e:
            logger.warning(f"Smart proxy not available: {e}")
    
    async def _init_quantum_scraper(self) -> None:
        """Initialize Quantum Temporal Scraper."""
        try:
            from src.engine.quantum_scraper import QuantumTemporalScraper
            from src.bypass.quantum_bypass import QuantumPaywallBypass
            from src.database import get_database
            
            # Quantum scraper needs the realtime feeder and database
            if self._pipeline and hasattr(self._pipeline, '_feeder') and self._pipeline._feeder:
                db = get_database()
                self._quantum_scraper = QuantumTemporalScraper(self._pipeline._feeder, db)
                logger.info("✓ Quantum scraper initialized with feeder")
            else:
                logger.warning("⚠️ Quantum scraper deferred - waiting for pipeline feeder")
            
            # Initialize quantum bypass separately
            try:
                self._quantum_bypass = QuantumPaywallBypass()
                logger.info("✓ Quantum bypass initialized")
            except Exception:
                self._quantum_bypass = None
            
            # Try loading Rust extension
            try:
                import advanced_web_scraper
                logger.info("🦀 Rust extension 'advanced_web_scraper' loaded")
            except ImportError:
                logger.debug("Rust extension not available")
                
        except Exception as e:
            logger.warning(f"Quantum scraper not available: {e}")
    
    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.header.quantum_toggled.connect(self._on_quantum_toggle)
        
        self.sidebar.start_feed_clicked.connect(self._start_live_feed)
        self.sidebar.mode_changed.connect(self._on_mode_change)
        
        self.feed_panel.article_clicked.connect(self._on_article_click)
        self.feed_panel.article_saved.connect(self._on_article_saved)
        self.feed_panel.search_requested.connect(self._on_search)
        self.feed_panel.url_analysis_requested.connect(self._on_url_analysis)
        
        # Mode manager signals
        self._mode_manager.mode_changed.connect(self._on_mode_changed)
    
    def _request_mode_switch(self, mode: str) -> None:
        """Request mode switch with passcode protection."""
        success = self._mode_manager.request_mode_switch(mode)
        if success:
            self._set_status(f"Switched to {mode.upper()} mode")
    
    def _toggle_mode(self) -> None:
        """Toggle between user and developer modes."""
        target = 'developer' if self._mode_manager.get_current_mode() == 'user' else 'user'
        self._request_mode_switch(target)
    
    def _on_mode_changed(self, old_mode: str, new_mode: str) -> None:
        """Handle mode change."""
        self.header.set_mode_indicator(new_mode)
        
        # Show/hide developer menu
        self.dev_menu.menuAction().setVisible(new_mode == 'developer')
        
        if new_mode == 'developer':
            self._set_status("🛠️ Developer Mode - Full system access granted", "success")
        else:
            self._set_status("👤 User Mode - Standard features only")
    
    def _show_developer_dashboard(self) -> None:
        """Show developer dashboard."""
        show_developer_dashboard(self, self._orchestrator)
    
    def _change_dev_passcode(self) -> None:
        """Change developer passcode."""
        self._mode_manager.change_passcode()
    
    async def _on_region_change(self, hub) -> None:
        """Called when geo-rotation changes region."""
        self._current_region = hub.code
        self._set_status(f"🌍 Scanning {hub.name} ({hub.code})...", "info")
        self.sidebar.set_live_status(True, hub.code, 19)
    
    async def _on_reddit_post(self, post: Dict) -> None:
        """Handle new Reddit post. Fully wrapped so errors never crash the stream."""
        try:
            from src.core.types import Article, TechScore, SourceTier

            # Map Reddit upvote score to a TechScore (0–1 scale, clamped at 1000 upvotes)
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

            await self._on_new_stream_article(article)
        except Exception as e:
            logger.error(f"Reddit post handling error: {e}")
    
    async def _on_new_stream_article(self, article) -> None:
        """Handle new article from stream. Schedules Qt widget updates on the main thread."""
        try:
            # Convert Article dataclass to dict
            from dataclasses import asdict, is_dataclass
            if is_dataclass(article):
                article_dict = self._convert_article_to_dict(article)
            elif isinstance(article, dict):
                article_dict = article
            else:
                return

            # Capture for lambda closure
            _dict = article_dict

            def _update_ui():
                try:
                    self.articles.insert(0, _dict)
                    self.feed_panel.add_article(_dict)
                    sources = set(a.get("source", "") for a in self.articles)
                    self.sidebar.update_stats(
                        articles=len(self.articles),
                        sources=len(sources),
                        saved=len(self.saved_articles)
                    )
                    self.sidebar.set_live_status(True, self._current_region, len(sources))
                except Exception as e:
                    logger.error(f"UI update error: {e}")

            # Schedule on the Qt main thread (safe from any thread/async context)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, _update_ui)

        except Exception as e:
            logger.error(f"Stream article handling error: {e}")
    
    def _on_quantum_toggle(self, enabled: bool) -> None:
        """Handle quantum mode toggle."""
        self.quantum_enabled = enabled
        
        if self._quantum_scraper:
            self._quantum_scraper.is_quantum_state_active = enabled
        
        status = "🌌 Quantum Temporal Scraper Activated" if enabled else "Standard Scraper Active"
        level = "success" if enabled else "info"
        self._set_status(status, level)
    
    def _on_url_analysis(self, url: str) -> None:
        """Handle URL analysis request."""
        self._set_status(f"🔬 Analyzing {url[:50]}...")
        
        async def analyze():
            try:
                if self._orchestrator:
                    result = await self._orchestrator.analyze_url(url)
                    return result
                return None
            except Exception as e:
                logger.error(f"URL analysis error: {e}")
                raise
        
        def on_complete(result):
            if result:
                # URLAnalysisResult has article.title, not title directly
                title = result.article.title if hasattr(result, 'article') and result.article else "Unknown"
                self._set_status(f"✓ URL analysis complete: {title[:50]}...", "success")
                # Could show a popup here with detailed analysis
            else:
                self._set_status("✗ URL analysis failed", "error")
        
        def on_error(e):
            self._set_status(f"Analysis error: {e}", "error")
        
        run_async(analyze(), on_complete=on_complete, on_error=on_error)
    
    def _show_preferences(self) -> None:
        """Show preferences dialog."""
        dialog = PreferencesDialog(self)
        dialog.preferences_changed.connect(self._apply_preferences)
        dialog.exec()
    
    def _show_statistics(self) -> None:
        """Show statistics dialog."""
        stats = {
            "total_articles": len(self.articles),
            "sources": len(set(a.get("source", "") for a in self.articles)),
            "saved": len(self.saved_articles),
            "successful": len(self.articles),
            "failed": 0,
            "dedup_rate": 15.0,
            "avg_fetch_ms": 850,
        }
        dialog = StatisticsDialog(stats, self)
        dialog.exec()
    
    def _toggle_dashboard(self) -> None:
        """Toggle dashboard visibility."""
        self.dashboard.setVisible(not self.dashboard.isVisible())
    
    def _apply_preferences(self, prefs: dict) -> None:
        """Apply changed preferences."""
        mode = prefs.get("storage", {}).get("mode", "hybrid")
        mode_index = ["ephemeral", "hybrid", "persistent"].index(mode)
        self.sidebar.mode_combo.setCurrentIndex(mode_index)
        self._set_status("Preferences saved")
    
    def _show_history(self) -> None:
        """Show history viewer dialog."""
        history = []
        if self.articles:
            history.append({
                "timestamp": datetime.now().isoformat(),
                "articles": self.articles[:50]
            })
        
        dialog = HistoryViewer(history, self)
        dialog.batch_restored.connect(self._on_batch_restored)
        dialog.exec()
    
    def _on_batch_restored(self, articles: list) -> None:
        """Handle batch restoration from history."""
        self.articles = articles
        self.feed_panel.set_articles(articles)
        self._set_status(f"Restored {len(articles)} articles from history")
    
    def _show_export(self) -> None:
        """Show export dialog."""
        if not self.articles:
            self._set_status("No articles to export", "warning")
            return
        
        dialog = ExportDialog(self.articles, self)
        dialog.exec()
    
    def _start_live_feed(self) -> None:
        """Start fetching articles."""
        if self._fetching:
            return
        
        self._fetching = True
        self.sidebar.set_fetching(True)
        self.sidebar.set_live_status(True, self._current_region, 0)
        self._set_status("Fetching articles from all sources...")
        
        async def fetch():
            try:
                if self._pipeline:
                    articles = await self._pipeline.fetch_unified_live_feed(count=200)
                    return articles
                return []
            except Exception as e:
                logger.error(f"Fetch error: {e}")
                raise
        
        def on_complete(articles):
            self._on_fetch_complete(articles)
        
        def on_error(e):
            self._fetching = False
            self.sidebar.set_fetching(False)
            self.sidebar.set_live_status(False, self._current_region, 0)
            self._set_status(f"Fetch error: {e}", "error")
        
        run_async(fetch(), on_complete=on_complete, on_error=on_error)
    
    def _convert_article_to_dict(self, article) -> Dict[str, Any]:
        """Convert Article dataclass or object to dictionary."""
        if isinstance(article, dict):
            # Ensure critical fields have defaults
            result = dict(article)
            result.setdefault('id', '')
            result.setdefault('url', '')
            result.setdefault('title', 'Untitled')
            result.setdefault('source', 'Unknown')
            result.setdefault('tech_score', 0.5)
            result.setdefault('relevance_score', 0.5)
            result.setdefault('source_tier', 'standard')
            result.setdefault('tier', result.get('source_tier', 'standard'))
            result.setdefault('topics', [])
            result.setdefault('keywords', [])
            result.setdefault('entities', [])
            return result
        
        # Try dataclass conversion first
        from dataclasses import asdict, is_dataclass
        if is_dataclass(article):
            result = asdict(article)
            # Ensure critical fields have defaults (asdict preserves None values)
            if result.get('tech_score') is None:
                result['tech_score'] = 0.5
            if result.get('relevance_score') is None:
                result['relevance_score'] = 0.5
            if result.get('tier') is None:
                result['tier'] = result.get('source_tier', 'standard')
            return result
        
        # Fallback to manual attribute extraction
        return {
            'id': getattr(article, 'id', ''),
            'url': getattr(article, 'url', ''),
            'title': getattr(article, 'title', '') or 'Untitled',
            'content': getattr(article, 'content', ''),
            'summary': getattr(article, 'summary', ''),
            'ai_summary': getattr(article, 'ai_summary', getattr(article, 'summary', '')),
            'full_content': getattr(article, 'full_content', getattr(article, 'content', '')),
            'source': getattr(article, 'source', 'Unknown') or 'Unknown',
            'source_tier': getattr(article, 'source_tier', 'standard'),
            'published_at': getattr(article, 'published_at', None),
            'scraped_at': getattr(article, 'scraped_at', None),
            'tech_score': getattr(article, 'tech_score', 0.5) or 0.5,
            'relevance_score': getattr(article, 'relevance_score', 0.5) or 0.5,
            'tier': getattr(article, 'tier', getattr(article, 'source_tier', 'standard')),
            'topics': getattr(article, 'topics', []),
            'keywords': getattr(article, 'keywords', []),
            'entities': getattr(article, 'entities', []),
        }
    
    def _on_fetch_complete(self, articles: List[Dict]) -> None:
        """Handle fetch completion."""
        self._fetching = False
        self.sidebar.set_fetching(False)
        
        if articles:
            article_dicts = []
            for a in articles:
                article_dicts.append(self._convert_article_to_dict(a))
            
            self.articles = article_dicts
            self.feed_panel.set_articles(article_dicts)
            
            sources = set(a.get("source", "") for a in article_dicts)
            
            self.sidebar.update_stats(
                articles=len(article_dicts),
                sources=len(sources),
                saved=len(self.saved_articles)
            )
            
            self.sidebar.set_live_status(True, self._current_region, len(sources))
            self._set_status(f"Loaded {len(article_dicts)} articles from {len(sources)} sources")
        else:
            self._set_status("No articles found", "warning")
    
    def _on_article_saved(self, article_id: str, is_saved: bool) -> None:
        """Handle article save/unsave."""
        if is_saved:
            self.saved_articles.add(article_id)
        else:
            self.saved_articles.discard(article_id)
        
        self.sidebar.update_stats(
            articles=len(self.articles),
            saved=len(self.saved_articles)
        )
    
    def _on_article_click(self, article: Dict) -> None:
        """Handle article card click."""
        title = article.get("title", "")
        logger.info(f"Article clicked: {title[:50]}")
        # Could open ArticlePopup here
    
    def _on_search(self, query: str) -> None:
        """Handle search request."""
        if not query:
            self.feed_panel.set_articles(self.articles)
            return
        
        query_lower = query.lower()
        filtered = [
            a for a in self.articles
            if query_lower in a.get("title", "").lower()
            or query_lower in a.get("source", "").lower()
            or query_lower in a.get("ai_summary", "").lower()
        ]
        
        self.feed_panel.set_articles(filtered)
        self._set_status(f"Found {len(filtered)} articles matching '{query}'")
    
    def _on_mode_change(self, mode: str) -> None:
        """Handle storage mode change."""
        async def change_mode():
            try:
                from src.db_storage import set_storage_mode, StorageMode
                mode_enum = StorageMode(mode)
                await set_storage_mode(mode_enum)
                logger.info(f"Storage mode: {mode}")
            except Exception as e:
                logger.error(f"Mode change error: {e}")
        
        run_async(change_mode())
        self._set_status(f"Storage mode: {mode.upper()}")
    
    def _set_status(self, message: str, level: str = "info") -> None:
        """Update status bar."""
        colors = {
            "info": COLORS.fg,
            "success": COLORS.green,
            "warning": COLORS.orange,
            "error": COLORS.red,
        }
        color = colors.get(level, COLORS.fg)
        self.status_bar.setStyleSheet(f"color: {color};")
        self.status_bar.showMessage(message)
    
    def closeEvent(self, event) -> None:
        """Handle application close."""
        cleanup()
        
        # Stop all systems
        async def shutdown():
            if self._global_discovery:
                await self._global_discovery.stop()
            if self._reddit_stream:
                await self._reddit_stream.stop()
            if self._pipeline:
                await self._pipeline.stop()
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(shutdown())
            loop.close()
        except Exception as e:
            logger.debug(f"Shutdown error: {e}")
        
        logger.info("Application closed")
        event.accept()


from gui_qt.app_qt_migrated import TechNewsApp as MigratedTechNewsApp, main as migrated_main


TechNewsApp = MigratedTechNewsApp


def main() -> None:
    """Delegates to refactored migration entrypoint."""
    migrated_main()


if __name__ == "__main__":
    main()
