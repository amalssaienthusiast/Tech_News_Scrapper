"""
Tech News Scraper Main Window - PySide6
Complete main window matching tkinter gui/app.py functionality

Features:
- Ticker bar with scrolling credits
- Header with branding, search, controls
- Content area with splitter (results + sidebar)
- Status bar with dynamic updates
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSplitter, QScrollArea,
    QStatusBar, QStackedWidget, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Signal, Slot, Qt, QTimer, QPropertyAnimation, QPoint
from PySide6.QtGui import QFont, QAction, QKeySequence

from .theme import COLORS, Fonts, apply_theme, TOKYO_NIGHT_QSS
from .widgets import (
    SearchBar, StatsPanel, LiveFeedContainer, ArticleListView
)

logger = logging.getLogger(__name__)


class TickerBar(QFrame):
    """Scrolling ticker bar at top of window"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = "🚀 Tech News Scraper v7.0"
        self._position = 0
        self._speed = 1
        
        self._setup_ui()
        self._start_scrolling()
    
    def _setup_ui(self):
        """Build ticker UI"""
        self.setFixedHeight(28)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.bg_dark};
                border-bottom: 1px solid {COLORS.terminal_black};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.label = QLabel(self._text, self)
        self.label.setFont(Fonts.get_qfont('sm'))
        self.label.setStyleSheet(f"color: {COLORS.fg_dark}; padding: 0 20px;")
        layout.addWidget(self.label)
        layout.addStretch()
        logger.info("TickerBar UI setup complete")
    
    def _start_scrolling(self):
        """Start ticker animation"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._scroll)
        self.timer.start(50)  # 20 FPS
    
    def _scroll(self):
        """Animate ticker text"""
        # Rotate text for continuous scrolling effect
        self._position = (self._position + 1) % len(self._text)
        display = self._text[self._position:] + "   " + self._text[:self._position]
        self.label.setText(display)
    
    def set_text(self, text: str):
        """Update ticker text"""
        self._text = text


class HeaderBar(QFrame):
    """Header bar with branding, search, and controls"""
    
    # Signals
    search_requested = Signal(str)
    mode_toggled = Signal(str)
    refresh_requested = Signal()
    quit_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_mode = "user"
        self._quantum_enabled = True
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Build header UI"""
        self.setFixedHeight(70)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.bg_dark};
                border-bottom: 1px solid {COLORS.terminal_black};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(16)
        
        # Left: Branding
        branding = self._create_branding()
        layout.addLayout(branding)
        
        # Center: Search bar (stretch)
        self.search_bar = SearchBar(self, placeholder="🔍 Search tech news...")
        self.search_bar.search_triggered.connect(self.search_requested.emit)
        layout.addWidget(self.search_bar, 1)
        
        # Right: Controls
        controls = self._create_controls()
        layout.addLayout(controls)
    
    def _create_branding(self) -> QHBoxLayout:
        """Create branding section"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # Logo
        logo = QLabel("📰", self)
        logo.setStyleSheet("font-size: 24px;")
        layout.addWidget(logo)
        
        # Title
        title = QLabel("Tech News Scraper", self)
        title.setFont(Fonts.get_qfont('lg', 'bold'))
        title.setStyleSheet(f"color: {COLORS.cyan};")
        layout.addWidget(title)
        
        # Version badge
        version = QLabel("v7.0", self)
        version.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS.green};
                color: {COLORS.black};
                font-size: {Fonts.get_size('xs')}px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 3px;
            }}
        """)
        layout.addWidget(version)
        
        return layout
    
    def _create_controls(self) -> QHBoxLayout:
        """Create control buttons"""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        # Quantum toggle
        self.quantum_btn = QPushButton("⚡ Quantum", self)
        self.quantum_btn.setCheckable(True)
        self.quantum_btn.setChecked(True)
        self.quantum_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.magenta};
                color: {COLORS.black};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:checked {{
                background-color: {COLORS.magenta};
            }}
            QPushButton:!checked {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.comment};
            }}
            QPushButton:hover {{
                background-color: {COLORS.bright_magenta};
            }}
        """)
        self.quantum_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quantum_btn.toggled.connect(self._on_quantum_toggled)
        layout.addWidget(self.quantum_btn)
        
        # Mode indicator
        self.mode_label = QLabel("👤 User Mode", self)
        self.mode_label.setFont(Fonts.get_qfont('sm'))
        self.mode_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS.cyan};
                background-color: {COLORS.bg_visual};
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self.mode_label)
        
        # Time display
        self.time_label = QLabel(self)
        self.time_label.setFont(Fonts.get_qfont('sm'))
        self.time_label.setStyleSheet(f"color: {COLORS.fg_dark};")
        self._update_time()
        layout.addWidget(self.time_label)
        
        # Quit button
        quit_btn = QPushButton("✕", self)
        quit_btn.setFixedSize(32, 32)
        quit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.red};
                color: {COLORS.black};
                border: none;
                border-radius: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bright_red};
            }}
        """)
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.clicked.connect(self.quit_requested.emit)
        layout.addWidget(quit_btn)
        
        return layout
    
    def _update_time(self):
        """Update time display"""
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(f"🕐 {now}")
        QTimer.singleShot(1000, self._update_time)
    
    def _on_quantum_toggled(self, checked: bool):
        """Handle quantum toggle"""
        self._quantum_enabled = checked
    
    def set_mode(self, mode: str):
        """Update mode display"""
        self._current_mode = mode
        if mode == "developer":
            self.mode_label.setText("🛠️ Developer Mode")
            self.mode_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS.orange};
                    background-color: {COLORS.bg_visual};
                    padding: 6px 12px;
                    border-radius: 6px;
                }}
            """)
        else:
            self.mode_label.setText("👤 User Mode")
            self.mode_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS.cyan};
                    background-color: {COLORS.bg_visual};
                    padding: 6px 12px;
                    border-radius: 6px;
                }}
            """)


class Sidebar(QFrame):
    """Right sidebar with stats, actions, and controls"""
    
    # Signals
    refresh_clicked = Signal()
    history_clicked = Signal()
    statistics_clicked = Signal()
    preferences_clicked = Signal()
    developer_clicked = Signal()
    sources_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Build sidebar UI"""
        self.setMinimumWidth(280)
        self.setMaximumWidth(350)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.bg_highlight};
                border-left: 1px solid {COLORS.terminal_black};
            }}
        """)
        
        # Scroll area for content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # Content widget
        content = QWidget(scroll)
        scroll.setWidget(content)
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Stats panel
        self.stats_panel = StatsPanel(self)
        layout.addWidget(self.stats_panel)
        
        # Separator
        layout.addWidget(self._create_separator())
        
        # Quick Actions
        layout.addWidget(self._create_quick_actions())
        
        # Separator
        layout.addWidget(self._create_separator())
        
        # Sort options
        layout.addWidget(self._create_sort_section())
        
        # Separator
        layout.addWidget(self._create_separator())
        
        # Intelligence panel
        layout.addWidget(self._create_intelligence_section())
        
        # Separator
        layout.addWidget(self._create_separator())
        
        # Enterprise features
        layout.addWidget(self._create_enterprise_section())
        
        # Spacer at bottom
        layout.addStretch()
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_separator(self) -> QFrame:
        """Create horizontal separator"""
        sep = QFrame(self)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS.border};")
        return sep
    
    def _create_quick_actions(self) -> QWidget:
        """Create quick actions section"""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("⚡ Quick Actions", container)
        header.setFont(Fonts.get_qfont('md', 'bold'))
        header.setStyleSheet(f"color: {COLORS.yellow};")
        layout.addWidget(header)
        
        # Buttons
        buttons = [
            ("⚡ START LIVE FEED", COLORS.green, COLORS.black, self.refresh_clicked),
            ("📜 View History", COLORS.bg_visual, COLORS.cyan, self.history_clicked),
            ("📈 Statistics", COLORS.bg_visual, COLORS.blue, self.statistics_clicked),
        ]
        
        for text, bg, fg, signal in buttons:
            btn = QPushButton(text, container)
            btn.setFont(Fonts.get_qfont('sm', 'bold'))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {fg};
                    border: none;
                    border-radius: 6px;
                    padding: 10px 12px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.comment if bg == COLORS.bg_visual else COLORS.bright_green};
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn)
        
        return container
    
    def _create_sort_section(self) -> QWidget:
        """Create sort options section"""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("📊 Sort Articles", container)
        header.setFont(Fonts.get_qfont('md', 'bold'))
        header.setStyleSheet(f"color: {COLORS.cyan};")
        layout.addWidget(header)
        
        # Sort buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        sort_options = [
            ("📅 Date", "date"),
            ("⭐ Score", "score"),
            ("📰 Source", "source"),
        ]
        
        for text, sort_type in sort_options:
            btn = QPushButton(text, container)
            btn.setFont(Fonts.get_qfont('xs'))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.bg_visual};
                    color: {COLORS.fg_dark};
                    border: none;
                    border-radius: 4px;
                    padding: 6px 10px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.comment};
                    color: {COLORS.fg};
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        return container
    
    def _create_intelligence_section(self) -> QWidget:
        """Create intelligence panel"""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("🧠 Intelligence", container)
        header.setFont(Fonts.get_qfont('md', 'bold'))
        header.setStyleSheet(f"color: {COLORS.magenta};")
        layout.addWidget(header)
        
        # Info text
        info = QLabel("AI-powered article analysis and trend detection", container)
        info.setFont(Fonts.get_qfont('xs'))
        info.setStyleSheet(f"color: {COLORS.comment};")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        return container
    
    def _create_enterprise_section(self) -> QWidget:
        """Create enterprise features section"""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        icon = QLabel("🏢", container)
        icon.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(icon)
        
        header = QLabel("Enterprise", container)
        header.setFont(Fonts.get_qfont('md', 'bold'))
        header.setStyleSheet(f"color: {COLORS.fg};")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Buttons
        buttons = [
            ("⚙️ User Preferences", COLORS.magenta, self.preferences_clicked),
            ("🛠️ Developer Dashboard", COLORS.purple, self.developer_clicked),
            ("🔧 Manage Sources", COLORS.bg_visual, self.sources_clicked),
        ]
        
        for text, bg, signal in buttons:
            btn = QPushButton(text, container)
            btn.setFont(Fonts.get_qfont('sm', 'bold'))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {COLORS.fg if bg != COLORS.bg_visual else COLORS.cyan};
                    border: none;
                    border-radius: 6px;
                    padding: 10px 12px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.bright_magenta if bg == COLORS.magenta else COLORS.comment};
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn)
        
        return container
    
    def update_stats(self, stats: Dict[str, Any]):
        """Update statistics display"""
        self.stats_panel.update_stats(stats)


class DynamicStatusBar(QStatusBar):
    """Status bar with dynamic message queue"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: List[str] = []
        self._current_index = 0
        
        self._setup_ui()
        self._start_rotation()
    
    def _setup_ui(self):
        """Build status bar UI"""
        self.setStyleSheet(f"""
            QStatusBar {{
                background-color: {COLORS.bg_dark};
                color: {COLORS.fg_dark};
                border-top: 1px solid {COLORS.terminal_black};
                font-size: {Fonts.get_size('sm')}px;
            }}
        """)
        
        # Main message label
        self.message_label = QLabel("Ready", self)
        self.message_label.setStyleSheet(f"color: {COLORS.fg_dark}; padding: 0 8px;")
        self.addWidget(self.message_label, 1)
        
        # Article count
        self.count_label = QLabel("📰 0 articles", self)
        self.count_label.setStyleSheet(f"color: {COLORS.cyan}; padding: 0 8px;")
        self.addPermanentWidget(self.count_label)
        
        # Mode indicator
        self.mode_label = QLabel("👤 User", self)
        self.mode_label.setStyleSheet(f"color: {COLORS.comment}; padding: 0 8px;")
        self.addPermanentWidget(self.mode_label)
    
    def _start_rotation(self):
        """Start message rotation timer"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate_message)
        self.timer.start(3000)  # Rotate every 3 seconds
    
    def _rotate_message(self):
        """Rotate to next message in queue"""
        if self._queue:
            self._current_index = (self._current_index + 1) % len(self._queue)
            self.message_label.setText(self._queue[self._current_index])
    
    def set_message(self, message: str, timeout: int = 0):
        """Set status message"""
        self.message_label.setText(message)
        if timeout > 0:
            QTimer.singleShot(timeout * 1000, lambda: self.message_label.setText("Ready"))
    
    def add_to_queue(self, message: str):
        """Add message to rotation queue"""
        self._queue.append(message)
        if len(self._queue) == 1:
            self.message_label.setText(message)
    
    def clear_queue(self):
        """Clear message queue"""
        self._queue.clear()
        self._current_index = 0
        self.message_label.setText("Ready")
    
    def update_count(self, count: int):
        """Update article count"""
        self.count_label.setText(f"📰 {count} articles")
    
    def set_mode(self, mode: str):
        """Update mode indicator"""
        if mode == "developer":
            self.mode_label.setText("🛠️ Developer")
            self.mode_label.setStyleSheet(f"color: {COLORS.orange}; padding: 0 8px;")
        else:
            self.mode_label.setText("👤 User")
            self.mode_label.setStyleSheet(f"color: {COLORS.comment}; padding: 0 8px;")


class TechNewsMainWindow(QMainWindow):
    """Main application window
    
    Signals:
        search_requested(str): Search query submitted
        refresh_requested(): Live feed refresh requested
        article_clicked(dict): Article was clicked
        mode_changed(str): Mode switched (user/developer)
    """
    
    VERSION = "7.0"
    
    # Signals
    search_requested = Signal(str)
    refresh_requested = Signal()
    article_clicked = Signal(dict)
    mode_changed = Signal(str)
    
    # Dialog signals (forwarded from sidebar)
    history_clicked = Signal()
    preferences_clicked = Signal()
    developer_clicked = Signal()
    sources_clicked = Signal()
    statistics_clicked = Signal()
    
    def __init__(self):
        super().__init__()
        
        self._current_mode = "user"
        
        self._setup_window()
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        
        logger.info("TechNewsMainWindow initialized")
    
    def _setup_window(self):
        """Configure window properties"""
        self.setWindowTitle(f"Tech News Scraper v{self.VERSION}")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Apply theme
        self.setStyleSheet(TOKYO_NIGHT_QSS)
    
    def _setup_ui(self):
        """Build the main UI"""
        # Central widget
        central = QWidget(self)
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Ticker bar
        self.ticker = TickerBar(central)
        main_layout.addWidget(self.ticker)
        
        # Header bar
        self.header = HeaderBar(central)
        main_layout.addWidget(self.header)
        
        # Content area with splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal, central)
        self.splitter.setHandleWidth(4)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS.terminal_black};
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS.comment};
            }}
        """)
        
        # Left: Live feed container (results)
        self.feed_container = LiveFeedContainer(self.splitter)
        self.splitter.addWidget(self.feed_container)
        
        # Right: Sidebar
        self.sidebar = Sidebar(self.splitter)
        self.splitter.addWidget(self.sidebar)
        
        # Set splitter sizes (70% / 30%)
        self.splitter.setSizes([700, 300])
        
        main_layout.addWidget(self.splitter, 1)
        
        # Status bar
        self.status_bar = DynamicStatusBar(self)
        self.setStatusBar(self.status_bar)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+F: Focus search
        search_action = QAction("Search", self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(lambda: self.header.search_bar.focus())
        self.addAction(search_action)
        
        # F5: Refresh
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.refresh_requested.emit)
        self.addAction(refresh_action)
        
        # Ctrl+M: Toggle mode
        mode_action = QAction("Toggle Mode", self)
        mode_action.setShortcut(QKeySequence("Ctrl+M"))
        mode_action.triggered.connect(self._toggle_mode)
        self.addAction(mode_action)
        
        # Escape: Clear search
        esc_action = QAction("Clear", self)
        esc_action.setShortcut(QKeySequence("Escape"))
        esc_action.triggered.connect(self.header.search_bar.clear)
        self.addAction(esc_action)
    
    def _connect_signals(self):
        """Connect internal signals"""
        # Header
        self.header.search_requested.connect(self.search_requested.emit)
        self.header.quit_requested.connect(self.close)
        
        # Sidebar - forward signals
        self.sidebar.refresh_clicked.connect(self._on_refresh)
        self.sidebar.history_clicked.connect(self.history_clicked.emit)
        self.sidebar.statistics_clicked.connect(self.statistics_clicked.emit)
        self.sidebar.preferences_clicked.connect(self.preferences_clicked.emit)
        self.sidebar.developer_clicked.connect(self.developer_clicked.emit)
        self.sidebar.sources_clicked.connect(self.sources_clicked.emit)
        
        # Feed container
        self.feed_container.start_live_feed.connect(self._on_refresh)
        self.feed_container.article_clicked.connect(self.article_clicked.emit)
    
    def _toggle_mode(self):
        """Toggle between user and developer mode"""
        if self._current_mode == "user":
            self._current_mode = "developer"
        else:
            self._current_mode = "user"
        
        self.header.set_mode(self._current_mode)
        self.status_bar.set_mode(self._current_mode)
        self.mode_changed.emit(self._current_mode)
    
    # Event handlers
    def _on_refresh(self):
        """Handle refresh request"""
        self.feed_container.show_loading("Fetching tech news...")
        self.refresh_requested.emit()
    
    def _show_history(self):
        """Show history popup"""
        logger.info("History requested")
        # Will be connected to controller
    
    def _show_statistics(self):
        """Show statistics popup"""
        logger.info("Statistics requested")
        # Will be connected to controller
    
    def _show_preferences(self):
        """Show preferences popup"""
        logger.info("Preferences requested")
        # Will be connected to controller
    
    def _show_developer(self):
        """Show developer dashboard"""
        logger.info("Developer dashboard requested")
        # Will be connected to controller
    
    # Public API
    def set_status(self, message: str, timeout: int = 0):
        """Set status bar message"""
        self.status_bar.set_message(message, timeout)
    
    def update_stats(self, stats: Dict[str, Any]):
        """Update sidebar statistics"""
        self.sidebar.update_stats(stats)
        if 'articles' in stats:
            self.status_bar.update_count(stats['articles'])
    
    def add_article(self, article: Dict[str, Any]):
        """Add article to feed"""
        self.feed_container.add_article(article)
        count = self.feed_container.get_article_count()
        self.status_bar.update_count(count)
    
    def set_articles(self, articles: List[Dict[str, Any]]):
        """Set all articles"""
        self.feed_container.set_articles(articles)
        self.status_bar.update_count(len(articles))
    
    def clear_articles(self):
        """Clear all articles"""
        self.feed_container.clear_articles()
        self.status_bar.update_count(0)
    
    def show_loading(self, message: str = "Loading..."):
        """Show loading state"""
        self.feed_container.show_loading(message)
    
    def show_articles(self):
        """Switch to articles view"""
        self.feed_container.show_articles()
    
    def show_welcome(self):
        """Show welcome screen"""
        self.feed_container.show_welcome()
    
    def get_search_query(self) -> str:
        """Get current search query"""
        return self.header.search_bar.get_query()
    
    def get_feed_container(self) -> LiveFeedContainer:
        """Get the feed container widget"""
        return self.feed_container
    
    def get_article_list(self) -> ArticleListView:
        """Get the article list widget"""
        return self.feed_container.get_article_list()
