"""
Tech News Scraper v8.0 - PyQt6 Enterprise Edition

Refactored migration target for gui/app.py parity:
- Full PyQt6 runtime with thread-safe async bridges
- Live feed, URL analysis, history/restore, export, statistics
- Global discovery + reddit stream + smart proxy + quantum hooks
- Developer/user mode with passcode protection
- Alerts, newsletter, crawler, and sentiment dialog integrations
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

# Fix for macOS Apple Silicon multi-threading import crash
import numpy

try:
    import datasketch
    import src.engine.orchestrator
    import src.intelligence.sentiment_analyzer
    import src.data_structures.trie
except ImportError:
    pass

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gui_qt.dialogs.developer_dashboard import DeveloperDashboard as _DevDashboard


def show_developer_dashboard(parent=None, orchestrator=None):
    """Show the canonical 6-tab developer dashboard."""
    dialog = _DevDashboard(parent, orchestrator)
    dialog.exec()


from gui_qt.dialogs.alert_dialog import show_alert_config
from gui_qt.dialogs.article_viewer import show_article_viewer
from gui_qt.dialogs.crawler_dialog import CrawlerDialog
from gui_qt.dialogs.custom_sources_dialog import show_custom_sources_dialog
from gui_qt.dialogs.newsletter_dialog import show_newsletter_dialog
from gui_qt.dialogs.sentiment_dialog import SentimentDashboard
from gui_qt.dialogs.statistics_popup import StatisticsPopup
from gui_qt.event_manager import get_event_manager, EventType as GUIEventType
from gui_qt.config_manager import get_config
from gui_qt.mode_manager import get_mode_manager
from gui_qt.panels.admin_panel import show_admin_panel
from gui_qt.panels.dashboard_panel import LiveDashboardPanel
from gui_qt.panels.feed_panel import FeedPanel
from gui_qt.security import get_security_manager
from gui_qt.theme import COLORS, apply_theme
from gui_qt.utils.async_bridge import cleanup, run_async, get_async_bridge
from gui_qt.widgets.dialogs.history import ExportDialog, HistoryViewer
from gui_qt.widgets.dialogs.preferences import PreferencesDialog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeaderBar(QFrame):
    """Application header with branding, quantum toggle, and mode indicator."""

    quantum_toggled = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            HeaderBar {{
                background-color: {COLORS.bg_dark};
                border-bottom: 3px solid {COLORS.cyan};
            }}
            """
        )
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
        title.setStyleSheet(
            f"color: {COLORS.fg}; font-size: 20px; font-weight: bold; letter-spacing: 1px;"
        )
        branding_layout.addWidget(title)

        version = QLabel("v8.0")
        version.setStyleSheet(
            f"color: {COLORS.comment}; font-size: 12px; margin-top: 8px;"
        )
        branding_layout.addWidget(version)

        layout.addWidget(branding)
        layout.addStretch()

        # Quantum Toggle
        self.quantum_btn = QPushButton("🌌 QUANTUM: OFF")
        self.quantum_btn.setCheckable(True)
        self.quantum_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quantum_btn.setStyleSheet(
            f"""
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
            """
        )
        self.quantum_btn.toggled.connect(self._on_quantum_toggle)
        layout.addWidget(self.quantum_btn)
        logger.info("HeaderBar initialized with quantum toggle and branding")

        # Mode Indicator
        self.mode_badge = QLabel("👤 USER")
        self.mode_badge.setStyleSheet(
            f"""
            background-color: {COLORS.blue};
            color: {COLORS.fg};
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
            font-size: 11px;
            """
        )
        layout.addWidget(self.mode_badge)

        # Time Label
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {COLORS.fg_dark}; font-size: 13px;")
        layout.addWidget(self.time_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()

        # Exit Button
        exit_btn = QPushButton("⏻ Exit")
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.setStyleSheet(
            f"""
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
            """
        )
        exit_btn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(exit_btn)

    def _update_time(self) -> None:
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _on_quantum_toggle(self, checked: bool) -> None:
        self.quantum_btn.setText("🌌 QUANTUM: ON" if checked else "🌌 QUANTUM: OFF")
        self.quantum_toggled.emit(checked)

    def set_mode_indicator(self, mode: str) -> None:
        if mode == "developer":
            self.mode_badge.setText("⚡ DEV")
            self.mode_badge.setStyleSheet(
                f"""
                background-color: {COLORS.magenta};
                color: {COLORS.fg};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
                """
            )
        else:
            self.mode_badge.setText("👤 USER")
            self.mode_badge.setStyleSheet(
                f"""
                background-color: {COLORS.blue};
                color: {COLORS.fg};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
                """
            )


class Sidebar(QFrame):
    """Left sidebar with controls, storage mode, live indicators, intelligence panel."""

    start_feed_clicked = pyqtSignal()
    mode_changed = pyqtSignal(str)
    view_live_monitor_clicked = pyqtSignal()
    view_disruptive_clicked = pyqtSignal()
    configure_alerts_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(290)
        self.setStyleSheet(
            f"background-color: {COLORS.bg_dark}; border-right: 1px solid {COLORS.border};"
        )
        # Pulse state for ● LIVE indicator
        self._pulse_state = True
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick_pulse)
        self._pulse_timer.start(800)

        # Countdown timer (30 → 0 seconds)
        self._countdown_secs = 30
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick_countdown)
        self._countdown_timer.start(1000)
        self._is_live = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        # Wrap everything in a scroll area so tall sidebar doesn't clip
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(16)

        # ── Start Feed button ──────────────────────────────────────────────
        self.start_btn = QPushButton("⚡ Start Live Feed")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setFixedHeight(50)
        self.start_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS.cyan};
                color: {COLORS.bg_dark};
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bright_cyan};
            }}
            QPushButton:disabled {{
                background-color: {COLORS.bg_highlight};
                color: {COLORS.comment};
            }}
            """
        )
        self.start_btn.clicked.connect(self.start_feed_clicked.emit)
        layout.addWidget(self.start_btn)

        # ── Live Monitor button ────────────────────────────────────────────
        self.monitor_btn = QPushButton("🖥️ View Live Monitor")
        self.monitor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.monitor_btn.setFixedHeight(36)
        self.monitor_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.blue};
                border: 1px solid {COLORS.blue};
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.blue};
                color: {COLORS.fg};
            }}
            """
        )
        self.monitor_btn.clicked.connect(self.view_live_monitor_clicked.emit)
        layout.addWidget(self.monitor_btn)

        _sep1 = QFrame()
        _sep1.setFrameShape(QFrame.Shape.HLine)
        _sep1.setStyleSheet(f"background-color: {COLORS.border};")
        _sep1.setFixedHeight(1)
        layout.addWidget(_sep1)

        # ── Live status indicators ─────────────────────────────────────────
        self.live_frame = QFrame()
        self.live_frame.setStyleSheet(
            f"background-color: {COLORS.bg_highlight}; border-radius: 8px;"
        )
        live_layout = QVBoxLayout(self.live_frame)
        live_layout.setContentsMargins(12, 8, 12, 8)
        live_layout.setSpacing(6)

        live_row = QHBoxLayout()
        self.live_indicator = QLabel("● OFFLINE")
        self.live_indicator.setStyleSheet(
            f"color: {COLORS.comment}; font-weight: bold; font-size: 12px;"
        )
        live_row.addWidget(self.live_indicator)
        live_row.addStretch()
        self.countdown_label = QLabel("⏳ --")
        self.countdown_label.setStyleSheet(f"color: {COLORS.comment}; font-size: 11px;")
        live_row.addWidget(self.countdown_label)
        live_layout.addLayout(live_row)

        self.region_indicator = QLabel("🌍 Region: --")
        self.region_indicator.setStyleSheet(
            f"color: {COLORS.fg_dark}; font-size: 12px;"
        )
        live_layout.addWidget(self.region_indicator)

        self.source_indicator = QLabel("📡 Sources: 0")
        self.source_indicator.setStyleSheet(
            f"color: {COLORS.fg_dark}; font-size: 12px;"
        )
        live_layout.addWidget(self.source_indicator)

        layout.addWidget(self.live_frame)

        # ── Storage mode ───────────────────────────────────────────────────
        storage_label = QLabel("💾 Storage Mode")
        storage_label.setStyleSheet(
            f"color: {COLORS.fg}; font-weight: bold; font-size: 13px;"
        )
        layout.addWidget(storage_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["⚡ Ephemeral", "🔄 Hybrid", "💿 Persistent"])
        self.mode_combo.setCurrentIndex(1)
        self.mode_combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.fg};
                border: 1px solid {COLORS.border};
                border-radius: 6px;
                padding: 8px;
            }}
            QComboBox::drop-down {{ border: none; }}
            """
        )
        self.mode_combo.currentIndexChanged.connect(self._on_mode_change)
        layout.addWidget(self.mode_combo)

        self.mode_desc = QLabel("Live feed + AI cache")
        self.mode_desc.setStyleSheet(f"color: {COLORS.comment}; font-size: 11px;")
        layout.addWidget(self.mode_desc)

        # ── Statistics ─────────────────────────────────────────────────────
        _sep2 = QFrame()
        _sep2.setFrameShape(QFrame.Shape.HLine)
        _sep2.setStyleSheet(f"background-color: {COLORS.border};")
        _sep2.setFixedHeight(1)
        layout.addWidget(_sep2)

        stats_label = QLabel("📊 Statistics")
        stats_label.setStyleSheet(
            f"color: {COLORS.fg}; font-weight: bold; font-size: 13px;"
        )
        layout.addWidget(stats_label)

        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(
            f"background-color: {COLORS.bg_visual}; border-radius: 8px;"
        )
        stats_layout = QVBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(12, 8, 12, 8)
        stats_layout.setSpacing(8)

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

        # ── Intelligence Panel ─────────────────────────────────────────────
        _sep3 = QFrame()
        _sep3.setFrameShape(QFrame.Shape.HLine)
        _sep3.setStyleSheet(f"background-color: {COLORS.border};")
        _sep3.setFixedHeight(1)
        layout.addWidget(_sep3)

        intel_header_row = QHBoxLayout()
        intel_icon = QLabel("🧠")
        intel_icon.setStyleSheet(f"color: {COLORS.magenta}; font-size: 16px;")
        intel_header_row.addWidget(intel_icon)
        intel_title = QLabel("Intelligence")
        intel_title.setStyleSheet(
            f"color: {COLORS.fg}; font-weight: bold; font-size: 13px;"
        )
        intel_header_row.addWidget(intel_title)
        intel_header_row.addStretch()
        layout.addLayout(intel_header_row)

        # Three intelligence stat rows
        self._intel_labels: Dict[str, QLabel] = {}
        intel_stats_config = [
            ("Analyzed", "📊", COLORS.cyan),
            ("Disruptive", "⚡", COLORS.orange),
            ("High Priority", "🔴", COLORS.red),
        ]
        for stat_name, icon, color in intel_stats_config:
            row_frame = QFrame()
            row_frame.setStyleSheet(
                f"background-color: {COLORS.bg_visual}; border-radius: 4px;"
            )
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(10, 5, 10, 5)
            row_layout.setSpacing(6)

            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
            row_layout.addWidget(icon_lbl)

            name_lbl = QLabel(stat_name)
            name_lbl.setStyleSheet(f"color: {COLORS.fg_dark}; font-size: 11px;")
            row_layout.addWidget(name_lbl)
            row_layout.addStretch()

            val_lbl = QLabel("--")
            val_lbl.setStyleSheet(
                f"color: {color}; font-weight: bold; font-size: 12px;"
            )
            row_layout.addWidget(val_lbl)

            self._intel_labels[stat_name] = val_lbl
            layout.addWidget(row_frame)

        # Disruptive News button
        self.disruptive_btn = QPushButton("🔥 View Disruptive News")
        self.disruptive_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.disruptive_btn.setFixedHeight(36)
        self.disruptive_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS.orange};
                color: {COLORS.black};
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bright_yellow};
            }}
            """
        )
        self.disruptive_btn.clicked.connect(self.view_disruptive_clicked.emit)
        layout.addWidget(self.disruptive_btn)

        # Configure Alerts button
        self.alerts_btn = QPushButton("🔔 Configure Alerts")
        self.alerts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.alerts_btn.setFixedHeight(36)
        self.alerts_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.magenta};
                border: 1px solid {COLORS.magenta};
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS.magenta};
                color: {COLORS.black};
            }}
            """
        )
        self.alerts_btn.clicked.connect(self.configure_alerts_clicked.emit)
        layout.addWidget(self.alerts_btn)

        layout.addStretch()

        watermark = QLabel("Architected by Sci_Coder")
        watermark.setStyleSheet(f"color: {COLORS.comment}; font-size: 10px;")
        watermark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(watermark)

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Timers ─────────────────────────────────────────────────────────────

    def _tick_pulse(self) -> None:
        """Toggle ● LIVE indicator color every 800 ms."""
        if not self._is_live:
            return
        self._pulse_state = not self._pulse_state
        color = COLORS.green if self._pulse_state else COLORS.comment
        self.live_indicator.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 12px;"
        )

    def _tick_countdown(self) -> None:
        """Decrement refresh countdown each second and show it."""
        if not self._is_live:
            self.countdown_label.setText("⏳ --")
            return
        self._countdown_secs -= 1
        if self._countdown_secs <= 0:
            self._countdown_secs = 30
            self.countdown_label.setText("🔄 Refreshing…")
            self.start_feed_clicked.emit()
        else:
            color = COLORS.orange if self._countdown_secs <= 10 else COLORS.comment
            self.countdown_label.setStyleSheet(f"color: {color}; font-size: 11px;")
            self.countdown_label.setText(f"⏱ {self._countdown_secs}s")

    def reset_countdown(self) -> None:
        """Reset the 30-second auto-refresh countdown."""
        self._countdown_secs = 30
        self.countdown_label.setText("⏱ 30s")

    # ── Public API ─────────────────────────────────────────────────────────

    def _on_mode_change(self, index: int) -> None:
        modes = ["ephemeral", "hybrid", "persistent"]
        descriptions = [
            "Articles auto-expire (2hr TTL)",
            "Live feed + AI cache",
            "Full database storage",
        ]

        self.mode_desc.setText(descriptions[index])
        if 0 <= index < len(modes):
            self.mode_changed.emit(modes[index])

    def update_stats(self, articles: int = 0, sources: int = 0, saved: int = 0) -> None:
        self.stats_articles.setText(f"📰 Articles: {articles}")
        self.stats_sources.setText(f"🔗 Sources: {sources}")
        self.stats_saved.setText(f"💾 Saved: {saved}")

    def update_intelligence_stats(
        self, analyzed: int = 0, disruptive: int = 0, high_priority: int = 0
    ) -> None:
        """Update the 🧠 Intelligence panel counters."""
        self._intel_labels["Analyzed"].setText(str(analyzed))
        self._intel_labels["Disruptive"].setText(str(disruptive))
        self._intel_labels["High Priority"].setText(str(high_priority))

    def set_fetching(self, is_fetching: bool) -> None:
        if is_fetching:
            self.start_btn.setText("⏳ Fetching...")
            self.start_btn.setEnabled(False)
        else:
            self.start_btn.setText("⚡ Start Live Feed")
            self.start_btn.setEnabled(True)

    def set_live_status(
        self, is_live: bool, region: str = "", source_count: int = 0
    ) -> None:
        self._is_live = is_live
        if is_live:
            self.live_indicator.setText("● LIVE")
            self.live_indicator.setStyleSheet(
                f"color: {COLORS.green}; font-weight: bold; font-size: 12px;"
            )
            self.region_indicator.setText(f"🌍 Region: {region}")
            self.source_indicator.setText(f"📡 Sources: {source_count}")
        else:
            self.live_indicator.setText("○ OFFLINE")
            self.live_indicator.setStyleSheet(
                f"color: {COLORS.comment}; font-weight: bold; font-size: 12px;"
            )


class _StatsControllerAdapter:
    """Minimal adapter so StatisticsPopup can introspect current article list."""

    def __init__(self, app: "TechNewsApp") -> None:
        self._app = app

    @property
    def _articles(self) -> List[Dict[str, Any]]:
        return self._app.articles


class TechNewsApp(QMainWindow):
    """Main application window with Tk parity-focused PyQt6 migration."""

    VERSION = "8.0"

    stream_article_received = pyqtSignal(dict)
    pipeline_status_received = pyqtSignal(str, str)
    region_status_received = pyqtSignal(str, int)

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(f"Tech News Scraper v{self.VERSION}")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        # Runtime state
        self.articles: List[Dict[str, Any]] = []
        self.saved_articles: set[str] = set()
        self._displayed_urls: set[str] = set()
        self._history_batches: List[Dict[str, Any]] = []
        self._history_limit = 30
        self._active_query = ""
        self._fetching = False
        self.quantum_enabled = False
        self._current_region = "US"

        # In-memory intelligence counters (updated after each fetch)
        self._intel_analyzed: int = 0
        self._intel_disruptive: int = 0
        self._intel_high_priority: int = 0

        # Core components
        self._orchestrator = None
        self._pipeline = None
        self._global_discovery = None
        self._reddit_stream = None
        self._proxy_router = None
        self._quantum_scraper = None
        self._quantum_bypass = None

        self._crawler_dialog: Optional[CrawlerDialog] = None

        # Mode manager
        self._mode_manager = get_mode_manager(self)

        # Event manager & config manager (ported from gui/)
        self._event_manager = get_event_manager(parent=self)
        self._config = get_config()
        self._security = get_security_manager()

        self._setup_ui()
        self._setup_menu_bar()
        self._connect_signals()
        self._setup_shortcuts()
        self._init_all_systems()

        # Start event manager after systems are initialised
        self._event_manager.start()

        logger.info("Tech News Scraper v%s (PyQt6) started", self.VERSION)

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(f"background-color: {COLORS.bg};")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.header = HeaderBar()
        main_layout.addWidget(self.header)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.sidebar = Sidebar()
        content_layout.addWidget(self.sidebar)

        self.feed_panel = FeedPanel(on_save=self._on_article_saved)
        content_layout.addWidget(self.feed_panel, 1)

        # LiveDashboardPanel kept as a non-visible widget so internal
        # update calls (set_progress, update_source, add_article, etc.)
        # continue to work without errors.  It is NOT added to the layout.
        self.dashboard = LiveDashboardPanel()

        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget, 1)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            f"background-color: {COLORS.bg_dark}; color: {COLORS.fg}; border-top: 1px solid {COLORS.border};"
        )
        self.setStatusBar(self.status_bar)
        self._set_status(
            "Ready - Press F12 for Developer Mode or click 'Start Live Feed'"
        )

    def _setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        # File
        file_menu = menu_bar.addMenu("File")

        prefs_action = QAction("⚙️ Preferences", self)
        prefs_action.setShortcut("Ctrl+,")
        prefs_action.triggered.connect(self._show_preferences)
        file_menu.addAction(prefs_action)

        export_action = QAction("📤 Export Articles", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._show_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View
        view_menu = menu_bar.addMenu("View")

        stats_action = QAction("📊 Statistics", self)
        stats_action.setShortcut("Ctrl+I")
        stats_action.triggered.connect(self._show_statistics)
        view_menu.addAction(stats_action)

        history_action = QAction("📜 History", self)
        history_action.setShortcut("Ctrl+H")
        history_action.triggered.connect(self._show_history)
        view_menu.addAction(history_action)

        toggle_dash_action = QAction("🖥️ Toggle Dashboard", self)
        toggle_dash_action.setShortcut("Ctrl+D")
        toggle_dash_action.triggered.connect(self._toggle_dashboard)
        view_menu.addAction(toggle_dash_action)

        # Tools (Tk parity features)
        tools_menu = menu_bar.addMenu("Tools")

        crawler_action = QAction("🕷️ Web Crawler", self)
        crawler_action.triggered.connect(self._show_crawler_dialog)
        tools_menu.addAction(crawler_action)

        sentiment_action = QAction("📊 Sentiment Dashboard", self)
        sentiment_action.triggered.connect(self._show_sentiment_dashboard)
        tools_menu.addAction(sentiment_action)

        alerts_action = QAction("🔔 Configure Alerts", self)
        alerts_action.triggered.connect(self._show_alert_config)
        tools_menu.addAction(alerts_action)

        newsletter_action = QAction("📰 Newsletter", self)
        newsletter_action.triggered.connect(self._show_newsletter_dialog)
        tools_menu.addAction(newsletter_action)

        custom_sources_action = QAction("⚙️ Custom Sources", self)
        custom_sources_action.triggered.connect(self._show_custom_sources)
        tools_menu.addAction(custom_sources_action)

        # Developer
        self.dev_menu = menu_bar.addMenu("Developer")

        dev_dashboard_action = QAction("🛠️ Dashboard", self)
        dev_dashboard_action.setShortcut("Ctrl+Shift+D")
        dev_dashboard_action.triggered.connect(self._show_developer_dashboard)
        self.dev_menu.addAction(dev_dashboard_action)

        admin_panel_action = QAction("🖧 Admin Control Panel", self)
        admin_panel_action.setShortcut("Ctrl+Shift+A")
        admin_panel_action.triggered.connect(self._show_admin_panel)
        self.dev_menu.addAction(admin_panel_action)

        change_passcode_action = QAction("🔐 Change Passcode", self)
        change_passcode_action.triggered.connect(self._change_dev_passcode)
        self.dev_menu.addAction(change_passcode_action)

        self.dev_menu.menuAction().setVisible(False)

    def _setup_shortcuts(self) -> None:
        user_shortcut = QShortcut(QKeySequence("F11"), self)
        user_shortcut.activated.connect(lambda: self._request_mode_switch("user"))

        dev_shortcut = QShortcut(QKeySequence("F12"), self)
        dev_shortcut.activated.connect(lambda: self._request_mode_switch("developer"))

        mode_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        mode_shortcut.activated.connect(self._toggle_mode)

        refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_shortcut.activated.connect(self._start_live_feed)

        logger.info(
            "Keyboard shortcuts registered: F11 (User), F12 (Developer), Ctrl+M (Toggle), Ctrl+R (Refresh)"
        )

    def _connect_signals(self) -> None:
        self.header.quantum_toggled.connect(self._on_quantum_toggle)

        self.sidebar.start_feed_clicked.connect(self._start_live_feed)
        self.sidebar.mode_changed.connect(self._on_mode_change)
        self.sidebar.view_live_monitor_clicked.connect(self._show_live_monitor)
        self.sidebar.view_disruptive_clicked.connect(self._show_disruptive_news)
        self.sidebar.configure_alerts_clicked.connect(self._show_alert_config)

        self.feed_panel.article_clicked.connect(self._on_article_click)
        self.feed_panel.article_saved.connect(self._on_article_saved)
        self.feed_panel.search_requested.connect(self._on_search)
        self.feed_panel.url_analysis_requested.connect(self._on_url_analysis)
        self.feed_panel.refresh_requested.connect(self._start_live_feed)

        self._mode_manager.mode_changed.connect(self._on_mode_changed)

        self.stream_article_received.connect(self._on_pipeline_stream_article)
        self.pipeline_status_received.connect(self._on_pipeline_status_received)
        self.region_status_received.connect(self._on_region_status)

    def _init_all_systems(self) -> None:
        """Kick off system initialization from the main thread.

        Submits the bootstrap coroutine to the persistent AsyncBridge loop so
        all async systems (pipeline, sessions, Reddit stream) share one event
        loop for their entire lifetime.  This eliminates 'Event loop is closed'
        errors that occurred when sessions created during bootstrap were later
        used in throwaway AsyncWorker loops.
        """
        # Startup animated progress: show 5-step progress on the status bar
        self._startup_steps = [
            "Initializing orchestrator...",
            "Starting pipeline...",
            "Connecting global discovery...",
            "Starting Reddit stream...",
            "Initializing quantum components...",
        ]
        self._startup_step_idx = 0
        self._startup_timer = QTimer(self)
        self._startup_timer.timeout.connect(self._advance_startup_step)
        self._startup_timer.start(900)

        # Bootstrap all async systems on the persistent AsyncBridge loop.
        # Using the same loop for bootstrap AND every subsequent fetch means
        # aiohttp ClientSessions are never orphaned on a closed loop.
        bridge = get_async_bridge()
        bridge.run_coro(
            self._bootstrap_systems(),
            error_callback=lambda exc: logger.error("Bootstrap error: %s", exc),
        )

    def _advance_startup_step(self) -> None:
        """Advance the animated startup progress shown in the status bar."""
        if self._startup_step_idx < len(self._startup_steps):
            msg = self._startup_steps[self._startup_step_idx]
            progress = int(
                (self._startup_step_idx + 1) / len(self._startup_steps) * 100
            )
            self._set_status(f"[{progress}%] {msg}")
            self.dashboard.set_progress(progress)
            self._startup_step_idx += 1
        else:
            self._startup_timer.stop()

    async def _bootstrap_systems(self) -> None:
        for init_fn in (
            self._init_orchestrator,
            self._init_pipeline,
            self._init_global_discovery,
            self._init_reddit_stream,
            self._init_smart_proxy,
            self._init_quantum_scraper,
        ):
            try:
                await init_fn()
            except Exception as exc:
                logger.error("Init step %s failed: %s", init_fn.__name__, exc)
        self._set_status("All systems ready", "success")

    async def _init_orchestrator(self) -> None:
        try:
            from src.engine import TechNewsOrchestrator

            self._orchestrator = TechNewsOrchestrator()
            await self._load_existing_articles()
            logger.info("✓ TechNewsOrchestrator initialized")
        except Exception as exc:
            logger.error("Failed to initialize orchestrator: %s", exc)
            self._set_status(f"Orchestrator init warning: {exc}", "warning")

    async def _load_existing_articles(self) -> None:
        try:
            from src.database import get_database

            db = get_database()
            raw_articles = db.get_all_articles()
            articles = self._canonicalize_articles(raw_articles)

            if not articles:
                return

            QTimer.singleShot(0, lambda: self._apply_loaded_articles(articles))

        except Exception as exc:
            logger.warning("Could not load existing articles: %s", exc)

    def _apply_loaded_articles(self, articles: List[Dict[str, Any]]) -> None:
        self.articles = list(articles)
        self.feed_panel.set_articles(articles)
        self._update_caches_from_articles(articles)
        self._update_live_metrics(progress=100)
        self._set_status(f"📚 Loaded {len(articles)} existing articles from database")

    async def _init_pipeline(self) -> None:
        try:
            from src.engine.enhanced_feeder import EnhancedNewsPipeline

            self._pipeline = EnhancedNewsPipeline(
                enable_discovery=True,
                max_articles=500,
                max_age_hours=48,
            )
            self._pipeline.add_status_callback(self._pipeline_status_callback)
            self._pipeline.add_article_callback(self._pipeline_article_callback)
            await self._pipeline.start()

            logger.info("✓ Enhanced pipeline initialized")
        except Exception as exc:
            logger.error("Pipeline init failed: %s", exc)
            self._set_status(f"Pipeline init warning: {exc}", "warning")

    async def _init_global_discovery(self) -> None:
        try:
            from src.discovery.global_discovery import get_global_discovery_manager

            self._global_discovery = get_global_discovery_manager()
            if self._global_discovery:
                self._global_discovery.on_new_region = self._on_region_change
                await self._global_discovery.start()
                logger.info("✓ Global discovery started")
        except Exception as exc:
            logger.warning("Global discovery unavailable: %s", exc)

    async def _init_reddit_stream(self) -> None:
        try:
            from src.sources.reddit_stream import get_reddit_stream_client

            self._reddit_stream = get_reddit_stream_client()
            if self._reddit_stream:
                self._reddit_stream.on_new_post = self._on_reddit_post
                # Bootstrap already runs on the AsyncBridge loop, so
                # asyncio.create_task() inside start() will attach to the
                # correct persistent loop automatically.
                await self._reddit_stream.start()
                logger.info("✓ Reddit stream started")
        except Exception as exc:
            logger.warning("Reddit stream unavailable: %s", exc)

    async def _init_smart_proxy(self) -> None:
        try:
            from src.bypass.smart_proxy_router import get_smart_proxy_router

            self._proxy_router = get_smart_proxy_router()
            if self._proxy_router:
                logger.info("✓ Smart proxy router initialized")
        except Exception as exc:
            logger.warning("Smart proxy unavailable: %s", exc)

    async def _init_quantum_scraper(self) -> None:
        try:
            from src.bypass.quantum_bypass import QuantumPaywallBypass
            from src.database import get_database
            from src.engine.quantum_scraper import QuantumTemporalScraper

            if (
                self._pipeline
                and hasattr(self._pipeline, "_feeder")
                and self._pipeline._feeder
            ):
                db = get_database()
                self._quantum_scraper = QuantumTemporalScraper(
                    self._pipeline._feeder, db
                )
                logger.info("✓ Quantum scraper initialized")

            try:
                self._quantum_bypass = QuantumPaywallBypass()
                logger.info("✓ Quantum bypass initialized")
            except Exception:
                self._quantum_bypass = None
        except Exception as exc:
            logger.warning("Quantum components unavailable: %s", exc)

    def _pipeline_status_callback(self, component: str, status: str) -> None:
        self.pipeline_status_received.emit(component, status)

    def _pipeline_article_callback(self, article: Any) -> None:
        try:
            converted = self._convert_article_to_dict(article)
            self.stream_article_received.emit(converted)
        except Exception as exc:
            logger.debug("Pipeline article callback error: %s", exc)

    def _on_pipeline_status_received(self, component: str, status: str) -> None:
        text = f"[{component}] {status}"
        self._set_status(text)

        # Heuristic progress updates based on pipeline status text.
        lowered = status.lower()
        if "starting" in lowered:
            self.dashboard.set_progress(5)
        elif "fetch" in lowered or "running" in lowered:
            self.dashboard.set_progress(35)
        elif "dedup" in lowered:
            self.dashboard.set_progress(70)
        elif "ready" in lowered or "stopped" in lowered:
            self.dashboard.set_progress(0)
        elif "✓" in status:
            self.dashboard.set_progress(100)

        source_name = component.replace("_", " ").title()
        if source_name in self.dashboard.source_grid.sources:
            active = "error" not in lowered
            self.dashboard.update_source(
                source_name, "active" if active else "error", 0
            )

    def _on_pipeline_stream_article(self, article: Dict[str, Any]) -> None:
        if self._is_duplicate_article(article):
            return

        self.articles.insert(0, article)
        self.feed_panel.add_article(article, prepend=True)
        self._displayed_urls.add(article.get("url", ""))

        if len(self.articles) > 1000:
            self.articles = self.articles[:1000]
            self._update_caches_from_articles(self.articles)

        self.dashboard.add_article(article)
        self._update_live_metrics(progress=100)

    def _request_mode_switch(self, mode: str) -> None:
        if self._mode_manager.request_mode_switch(mode):
            self._set_status(f"Switched to {mode.upper()} mode")

    def _toggle_mode(self) -> None:
        target = (
            "developer" if self._mode_manager.get_current_mode() == "user" else "user"
        )
        self._request_mode_switch(target)

    def _on_mode_changed(self, old_mode: str, new_mode: str) -> None:
        self.header.set_mode_indicator(new_mode)
        self.dev_menu.menuAction().setVisible(new_mode == "developer")

        if new_mode == "developer":
            self._set_status("🛠️ Developer Mode - Full system access granted", "success")
        else:
            self._set_status("👤 User Mode - Standard features only")

    def _show_developer_dashboard(self) -> None:
        show_developer_dashboard(self, self._orchestrator)

    def _show_admin_panel(self) -> None:
        show_admin_panel(self)

    def _show_custom_sources(self) -> None:
        show_custom_sources_dialog(self)

    def _change_dev_passcode(self) -> None:
        self._mode_manager.change_passcode()

    def _on_region_change(self, hub: Any) -> None:
        """Sync callback — only emits a Qt signal for thread-safe UI update."""
        code = getattr(hub, "code", "--")
        self._current_region = code
        self.region_status_received.emit(code, 19)

    def _on_region_status(self, region: str, source_count: int) -> None:
        self.sidebar.set_live_status(True, region, source_count)
        self._set_status(f"🌍 Scanning region {region}...")

    def _on_reddit_post(self, post: Dict[str, Any]) -> None:
        """Sync callback — converts Reddit post to Article and emits Qt signal."""
        try:
            from src.core.types import Article, SourceTier, TechScore

            raw_score = post.get("score", 0)
            normalized = min(raw_score / 1000.0, 1.0)

            article = Article(
                id=f"reddit_{post.get('id', '')}",
                title=post.get("title", "Untitled"),
                url=post.get("external_url") or post.get("url", ""),
                content="",
                summary="",
                source=f"reddit/r/{post.get('subreddit', 'technology')}",
                source_tier=SourceTier.TIER_3,
                published_at=post.get("created_utc"),
                scraped_at=datetime.now(),
                tech_score=TechScore(score=normalized, confidence=0.7),
            )
            self.stream_article_received.emit(self._convert_article_to_dict(article))
        except Exception as exc:
            logger.error("Reddit post handling error: %s", exc)

    def _normalize_score(self, score: Any) -> float:
        try:
            if isinstance(score, dict):
                score = score.get("score", 0)
            score = float(score)
        except Exception:
            return 0.0

        # Normalize commonly-seen ranges: 0-1, 0-10, 0-100.
        if score <= 1.0:
            score *= 100.0
        elif score <= 10.0:
            score *= 10.0

        return max(0.0, min(100.0, score))

    def _convert_article_to_dict(self, article: Any) -> Dict[str, Any]:
        if isinstance(article, dict):
            result = dict(article)
        elif is_dataclass(article):
            result = asdict(article)
        else:
            result = {
                "id": getattr(article, "id", ""),
                "url": getattr(article, "url", ""),
                "title": getattr(article, "title", "") or "Untitled",
                "content": getattr(article, "content", ""),
                "summary": getattr(article, "summary", ""),
                "ai_summary": getattr(
                    article, "ai_summary", getattr(article, "summary", "")
                ),
                "full_content": getattr(
                    article, "full_content", getattr(article, "content", "")
                ),
                "source": getattr(article, "source", "Unknown") or "Unknown",
                "source_tier": getattr(article, "source_tier", "standard"),
                "tier": getattr(
                    article, "tier", getattr(article, "source_tier", "standard")
                ),
                "published_at": getattr(article, "published_at", None),
                "published": getattr(article, "published", None),
                "scraped_at": getattr(article, "scraped_at", None),
                "tech_score": getattr(article, "tech_score", 0.0),
                "relevance_score": getattr(article, "relevance_score", 0.0),
                "topics": getattr(article, "topics", []),
                "keywords": getattr(article, "keywords", []),
                "entities": getattr(article, "entities", []),
            }

        url = result.get("url", "") or ""
        title = result.get("title", "") or "Untitled"

        result["url"] = url
        result["title"] = title
        result.setdefault("source", "Unknown")
        result.setdefault("ai_summary", result.get("summary", "") or "")
        result.setdefault("full_content", result.get("content", "") or "")
        result.setdefault("topics", [])
        result.setdefault("keywords", [])
        result.setdefault("entities", [])
        result.setdefault("source_tier", result.get("tier", "standard"))
        result.setdefault("tier", result.get("source_tier", "standard"))

        # Normalize published keys for ArticleCard compatibility.
        published = result.get("published") or result.get("published_at")
        result["published"] = published
        result["published_at"] = published

        result["tech_score"] = self._normalize_score(result.get("tech_score", 0.0))

        article_id = result.get("id")
        if not article_id:
            basis = f"{url}|{title}"
            article_id = hashlib.md5(basis.encode("utf-8", errors="ignore")).hexdigest()
            result["id"] = article_id

        return result

    def _canonicalize_articles(self, raw_articles: List[Any]) -> List[Dict[str, Any]]:
        converted = [self._convert_article_to_dict(article) for article in raw_articles]

        unique: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()
        for article in converted:
            url = article.get("url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            unique.append(article)

        return unique

    def _is_duplicate_article(self, article: Dict[str, Any]) -> bool:
        url = article.get("url", "")
        article_id = article.get("id", "")

        if url and url in self._displayed_urls:
            return True

        if article_id and any(a.get("id") == article_id for a in self.articles[:200]):
            return True

        return False

    def _update_caches_from_articles(self, articles: List[Dict[str, Any]]) -> None:
        self._displayed_urls = {a.get("url", "") for a in articles if a.get("url")}

    def _update_live_metrics(self, progress: Optional[int] = None) -> None:
        sources = {a.get("source", "") for a in self.articles if a.get("source")}

        self.sidebar.update_stats(
            articles=len(self.articles),
            sources=len(sources),
            saved=len(self.saved_articles),
        )

        self.sidebar.set_live_status(
            is_live=len(self.articles) > 0 or self._fetching,
            region=self._current_region,
            source_count=len(sources),
        )

        self.dashboard.update_stats(
            total=len(self.articles),
            rss=self._pipeline.get_stats().get("rss_articles", 0)
            if self._pipeline
            else 0,
            api=self._pipeline.get_stats().get("api_articles", 0)
            if self._pipeline
            else 0,
            dedup_rate=self._pipeline.get_stats().get("duplicates_filtered", 0)
            if self._pipeline
            else 0,
        )

        if progress is not None:
            self.dashboard.set_progress(progress)

    def _record_history_snapshot(self, reason: str) -> None:
        if not self.articles:
            return

        snapshot = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "articles": [dict(article) for article in self.articles],
        }

        self._history_batches.insert(0, snapshot)
        if len(self._history_batches) > self._history_limit:
            self._history_batches = self._history_batches[: self._history_limit]

    def _start_live_feed(self) -> None:
        if self._fetching:
            return

        self._fetching = True
        self.sidebar.set_fetching(True)
        self.sidebar.set_live_status(True, self._current_region, 0)
        self.dashboard.set_progress(10)
        self._set_status("Fetching articles from all sources...")

        async def fetch() -> List[Any]:
            if not self._pipeline:
                return []
            return await self._pipeline.fetch_unified_live_feed(count=200)

        def on_complete(articles: List[Any]) -> None:
            self._on_fetch_complete(articles)

        def on_error(error: Exception) -> None:
            self._fetching = False
            self.sidebar.set_fetching(False)
            self.sidebar.set_live_status(False, self._current_region, 0)
            self.dashboard.set_progress(0)
            self._set_status(f"Fetch error: {error}", "error")

        # Use the persistent AsyncBridge loop so the pipeline's aiohttp
        # ClientSession (created during bootstrap on that same loop) is
        # never handed to a different, throwaway loop.
        get_async_bridge().run_coro(
            fetch(), callback=on_complete, error_callback=on_error
        )

    # ------------------------------------------------------------------
    # In-memory article scoring (FIX 5)
    # ------------------------------------------------------------------

    _DISRUPTIVE_KW = [
        "breach",
        "hack",
        "attack",
        "ban",
        "crisis",
        "collapse",
        "emergency",
        "shutdown",
        "recall",
        "lawsuit",
        "explosion",
        "war",
        "sanction",
        "fine",
        "regulation",
        "outage",
        "leaked",
        "arrested",
        "fraud",
        "bankruptcy",
    ]

    def _score_articles_in_memory(self, articles: List[Dict[str, Any]]) -> None:
        """Score articles using actual backend pipelines (TechKeywordMatcher & SentimentAnalyzer).

        Sets:
          article['_disruptive']   = True/False
          article['_criticality']  = float 0.0–1.0
        Also refreshes the three intel counters.
        """
        analyzed = 0
        disruptive = 0
        high_priority = 0

        try:
            from src.data_structures.trie import TechKeywordMatcher
            from src.intelligence.sentiment_analyzer import SentimentAnalyzer

            matcher = TechKeywordMatcher()
            sentiment_analyzer = SentimentAnalyzer()

            for article in articles:
                text = " ".join(
                    filter(
                        None,
                        [
                            article.get("title", ""),
                            article.get("summary", ""),
                            article.get("content", ""),
                            article.get("ai_summary", ""),
                        ],
                    )
                ).lower()

                # Use backend Keyword Matcher
                matches = matcher.extract_keywords(text)

                # Calculate real Tech Score based on match weights
                tech_score = (
                    sum(matcher.TECH_KEYWORDS.get(kw.lower(), 1.0) for kw in matches)
                    / 10.0
                )

                # Use backend VADER Sentiment Analyzer
                sentiment = sentiment_analyzer.analyze_text(text)

                # Highly negative or highly positive sentiment combined with tech score = disruptive
                is_disruptive = tech_score > 0.4 and abs(sentiment.score) > 0.3
                criticality = min(tech_score * 2.0 + abs(sentiment.score), 1.0)

                article["_disruptive"] = is_disruptive
                article["_criticality"] = round(criticality, 3)
                article["sentiment_label"] = sentiment.label.value
                article["sentiment_score"] = sentiment.score

                analyzed += 1
                if is_disruptive:
                    disruptive += 1
                if criticality >= 0.4 or tech_score >= 0.8:
                    high_priority += 1

        except Exception as e:
            logger.error(f"Intelligence backend scoring failed: {e}")
            # Fallback
            for article in articles:
                article["_disruptive"] = False
                article["_criticality"] = 0.0
                analyzed += 1

        self._intel_analyzed = analyzed
        self._intel_disruptive = disruptive
        self._intel_high_priority = high_priority

    def _on_fetch_complete(self, raw_articles: List[Any]) -> None:
        self._fetching = False
        self.sidebar.set_fetching(False)
        self.sidebar.reset_countdown()

        articles = self._canonicalize_articles(raw_articles or [])

        if not articles:
            self.sidebar.set_live_status(False, self._current_region, 0)
            self.dashboard.set_progress(0)
            self._set_status("No articles found", "warning")
            return

        self._record_history_snapshot("manual_fetch")

        self.articles = list(articles)
        self._score_articles_in_memory(self.articles)  # FIX 5: keyword scoring
        self.feed_panel.set_articles(articles)
        self._update_caches_from_articles(articles)
        self._update_live_metrics(progress=100)
        self._update_intelligence_stats()

        sources = {a.get("source", "") for a in articles if a.get("source")}
        self._set_status(
            f"Loaded {len(articles)} articles from {len(sources)} sources", "success"
        )

    def _on_article_saved(self, article_id: str, is_saved: bool) -> None:
        if is_saved:
            self.saved_articles.add(article_id)
        else:
            self.saved_articles.discard(article_id)

        self.sidebar.update_stats(
            articles=len(self.articles),
            sources=len(
                {a.get("source", "") for a in self.articles if a.get("source")}
            ),
            saved=len(self.saved_articles),
        )

    def _on_article_click(self, article: Dict[str, Any]) -> None:
        try:
            show_article_viewer(self, article)
        except Exception as exc:
            logger.warning("Article viewer failed: %s", exc)
            self._set_status(f"Could not open article viewer: {exc}", "error")

    def _on_search(self, query: str) -> None:
        self._active_query = query.strip()

        if not self._active_query:
            self.feed_panel.set_articles(self.articles)
            self._set_status("Search cleared")
            return

        query_lower = self._active_query.lower()

        def article_matches(article: Dict[str, Any]) -> bool:
            haystacks = [
                article.get("title", ""),
                article.get("source", ""),
                article.get("ai_summary", ""),
                article.get("summary", ""),
                article.get("full_content", ""),
                " ".join(article.get("topics", []) or []),
                " ".join(article.get("keywords", []) or []),
                " ".join(article.get("entities", []) or []),
            ]
            return any(
                query_lower in str(value).lower() for value in haystacks if value
            )

        filtered = [article for article in self.articles if article_matches(article)]

        if filtered:
            self.feed_panel.set_articles(filtered)
            self._set_status(
                f"Found {len(filtered)} articles matching '{self._active_query}'"
            )
            return

        self._set_status(
            f"No local match for '{self._active_query}', trying remote search..."
        )
        get_async_bridge().run_coro(
            self._run_remote_search(self._active_query),
            callback=self._on_fetch_complete,
        )

    async def _run_remote_search(self, query: str) -> List[Any]:
        if not self._orchestrator:
            return []

        try:
            result = await self._orchestrator.search(
                query, max_articles=50, max_sources=5
            )
            return list(getattr(result, "articles", []) or [])
        except Exception as exc:
            logger.warning("Remote search failed for '%s': %s", query, exc)
            return []

    def _on_mode_change(self, mode: str) -> None:
        async def change_mode() -> None:
            try:
                from src.db_storage import StorageMode, set_storage_mode

                await set_storage_mode(StorageMode(mode))
            except Exception as exc:
                logger.debug("Storage mode switch warning: %s", exc)

        get_async_bridge().run_coro(change_mode())
        self._set_status(f"Storage mode: {mode.upper()}")

    def _on_quantum_toggle(self, enabled: bool) -> None:
        self.quantum_enabled = enabled

        if self._quantum_scraper:
            self._quantum_scraper.is_quantum_state_active = enabled

        if enabled:
            self._set_status("🌌 Quantum Temporal Scraper Activated", "success")
        else:
            self._set_status("Standard scraper mode active")

    def _on_url_analysis(self, url: str) -> None:
        url = url.strip()

        if not url:
            self._set_status("Paste a URL first", "warning")
            return

        if not url.startswith(("http://", "https://")):
            self._set_status("URL must start with http:// or https://", "warning")
            return

        self._set_status(f"🔬 Analyzing {url[:80]}...")

        async def analyze() -> Any:
            if self._orchestrator:
                return await self._orchestrator.analyze_url(url)
            return None

        def on_complete(result: Any) -> None:
            if result and getattr(result, "article", None):
                article = self._convert_article_to_dict(result.article)
                if not self._is_duplicate_article(article):
                    self.articles.insert(0, article)
                    self.feed_panel.add_article(article, prepend=True)
                    self._displayed_urls.add(article.get("url", ""))
                    self._update_live_metrics(progress=100)

                self._set_status("✓ URL analysis complete", "success")
                self._on_article_click(article)
            else:
                self._set_status("URL analysis returned no article", "warning")

        def on_error(error: Exception) -> None:
            self._set_status(f"URL analysis error: {error}", "error")

        get_async_bridge().run_coro(
            analyze(), callback=on_complete, error_callback=on_error
        )

    def _show_preferences(self) -> None:
        dialog = PreferencesDialog(self)
        dialog.preferences_changed.connect(self._apply_preferences)
        dialog.exec()

    def _show_statistics(self) -> None:
        try:
            dialog = StatisticsPopup(
                self,
                orchestrator=self._orchestrator,
                controller=_StatsControllerAdapter(self),
            )
            dialog.exec()
        except Exception as exc:
            logger.warning("Statistics popup fallback due to: %s", exc)
            self._set_status(f"Statistics popup error: {exc}", "error")

    def _toggle_dashboard(self) -> None:
        self.dashboard.setVisible(not self.dashboard.isVisible())

    def _apply_preferences(self, prefs: Dict[str, Any]) -> None:
        mode = prefs.get("storage", {}).get("mode", "hybrid")
        mode_lookup = {"ephemeral": 0, "hybrid": 1, "persistent": 2}
        self.sidebar.mode_combo.setCurrentIndex(mode_lookup.get(mode, 1))
        self._set_status("Preferences saved", "success")

    def _show_history(self) -> None:
        history = list(self._history_batches)

        if self.articles:
            history.insert(
                0,
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "reason": "current_state",
                    "articles": [dict(article) for article in self.articles],
                },
            )

        dialog = HistoryViewer(history=history, parent=self)
        dialog.batch_restored.connect(self._on_batch_restored)
        dialog.exec()

    def _on_batch_restored(self, articles: List[Dict[str, Any]]) -> None:
        canonical = self._canonicalize_articles(articles)
        self.articles = canonical
        self.feed_panel.set_articles(canonical)
        self._update_caches_from_articles(canonical)
        self._update_live_metrics(progress=100)
        self._set_status(f"Restored {len(canonical)} articles from history", "success")

    def _show_export(self) -> None:
        if not self.articles:
            self._set_status("No articles to export", "warning")
            return

        dialog = ExportDialog(self.articles, self)
        dialog.exec()

    def _show_sentiment_dashboard(self) -> None:
        if not self.articles:
            self._set_status("No articles available for sentiment analysis", "warning")
            return

        dialog = SentimentDashboard(self.articles, self)
        dialog.exec()

    def _show_alert_config(self) -> None:
        show_alert_config(self)

    def _show_newsletter_dialog(self) -> None:
        show_newsletter_dialog(self, articles=self.articles)

    def _show_crawler_dialog(self) -> None:
        if self._crawler_dialog and self._crawler_dialog.isVisible():
            self._crawler_dialog.raise_()
            self._crawler_dialog.activateWindow()
            return

        self._crawler_dialog = CrawlerDialog(self, orchestrator=self._orchestrator)
        self._crawler_dialog.crawl_completed.connect(self._on_crawler_completed)
        self._crawler_dialog.show()

    def _on_crawler_completed(self, crawled_articles: List[Any]) -> None:
        if not crawled_articles:
            self._set_status("Crawler completed with no new articles", "warning")
            return

        converted = self._canonicalize_articles(crawled_articles)
        converted_urls = {c.get("url") for c in converted if c.get("url")}
        merged = converted + [
            a for a in self.articles if a.get("url") not in converted_urls
        ]
        self._record_history_snapshot("crawler_merge")
        self.articles = merged[:1000]
        self.feed_panel.set_articles(self.articles)
        self._update_caches_from_articles(self.articles)
        self._update_live_metrics(progress=100)
        self._set_status(f"Crawler merged {len(converted)} articles", "success")

    def _update_intelligence_stats(self) -> None:
        """Push in-memory intelligence counters to the sidebar panel.

        Counters are updated by _score_articles_in_memory() after each fetch.
        Falls back to a DB query only when no articles have been scored yet.
        """
        analyzed = self._intel_analyzed
        disruptive = self._intel_disruptive
        high_priority = self._intel_high_priority

        if analyzed == 0 and self.articles:
            # First load or DB-only mode: try to get counts from DB
            try:
                from src.database import get_database

                db = get_database()
                stats = db.get_intelligence_stats()
                analyzed = stats.get("total_analyzed", 0)
                disruptive = stats.get("disruptive_count", 0)
                high_priority = stats.get("high_criticality_count", 0)
            except Exception as exc:
                logger.debug("DB intelligence stats unavailable: %s", exc)

        QTimer.singleShot(
            0,
            lambda a=analyzed, d=disruptive, h=high_priority: (
                self.sidebar.update_intelligence_stats(
                    analyzed=a,
                    disruptive=d,
                    high_priority=h,
                )
            ),
        )

    def _show_live_monitor(self) -> None:
        """Open the full-screen Live Monitor overlay with real pipeline data."""
        try:
            from gui_qt.widgets.live_monitor_overlay import LiveMonitorOverlay

            # Score articles if not yet done
            if self._intel_analyzed == 0 and self.articles:
                self._score_articles_in_memory(self.articles)

            sources_active = len(
                {a.get("source", "") for a in self.articles if a.get("source")}
            )
            overlay = LiveMonitorOverlay(
                self,
                articles=self.articles,
                intel_analyzed=self._intel_analyzed,
                intel_disruptive=self._intel_disruptive,
                intel_high_prio=self._intel_high_priority,
                sources_active=sources_active,
            )

            # Pass the orchestrator to the overlay for deeper metrics if possible
            if hasattr(overlay, "set_orchestrator"):
                overlay.set_orchestrator(self._orchestrator)

            overlay.exec()
        except Exception as exc:
            logger.warning("Live Monitor overlay not available: %s", exc)
            self._set_status("Live Monitor not available yet", "warning")

    def _show_disruptive_news(self) -> None:
        """Open the Disruptive News dialog, seeded with in-memory scored articles."""
        try:
            from gui_qt.dialogs.disruptive_news_dialog import DisruptiveNewsDialog

            # If we haven't scored yet, run scoring now so the dialog has data.
            if self._intel_analyzed == 0 and self.articles:
                self._score_articles_in_memory(self.articles)

            dialog = DisruptiveNewsDialog(self, in_memory_articles=self.articles)
            dialog.exec()
        except Exception as exc:
            logger.warning("Disruptive News dialog not available: %s", exc)
            self._set_status("Disruptive News dialog not available yet", "warning")

    def _set_status(self, message: str, level: str = "info") -> None:
        """Thread-safe status bar update — always dispatches to the main thread."""

        def _do_update():
            try:
                colors = {
                    "info": COLORS.fg,
                    "success": COLORS.green,
                    "warning": COLORS.orange,
                    "error": COLORS.red,
                }
                self.status_bar.setStyleSheet(
                    f"background-color: {COLORS.bg_dark}; color: {colors.get(level, COLORS.fg)}; border-top: 1px solid {COLORS.border};"
                )
                self.status_bar.showMessage(message)
            except RuntimeError:
                pass  # Widget already deleted during shutdown

        QTimer.singleShot(0, _do_update)

    def closeEvent(self, event) -> None:
        self._event_manager.stop()

        async def shutdown() -> None:
            if self._global_discovery:
                await self._global_discovery.stop()
            if self._reddit_stream:
                await self._reddit_stream.stop()
            if self._pipeline:
                await self._pipeline.stop()
            if self._orchestrator and hasattr(self._orchestrator, "shutdown"):
                await self._orchestrator.shutdown()

        # Submit shutdown to the persistent bridge loop (pipeline session lives there)
        # then wait up to 5s for it to finish before stopping the bridge.
        try:
            bridge = get_async_bridge()
            future = bridge.run_coro(shutdown())
            future.result(timeout=5)
        except Exception as exc:
            logger.debug("Shutdown warning: %s", exc)

        cleanup()
        logger.info("Application closed")
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Tech News Scraper")
    app.setApplicationVersion(TechNewsApp.VERSION)

    apply_theme(app)

    window = TechNewsApp()
    window.show()

    # macOS: bring app to front once at startup.
    import platform

    if platform.system() == "Darwin":
        window.raise_()
        window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
