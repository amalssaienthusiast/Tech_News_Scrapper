"""
Feed Panel - Scrollable article feed with lazy loading.

Displays article cards in a scrollable vertical list with
smooth scrolling and efficient rendering. Matches Tkinter layout.
"""

from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget, QHBoxLayout,
    QPushButton, QSizePolicy, QApplication, QLineEdit
)

from gui_qt.theme import COLORS
from gui_qt.widgets.article_card import ArticleCard


class FeedPanel(QFrame):
    """
    Scrollable article feed panel.
    
    Features:
    - Smooth scrolling with native Qt scroll
    - Lazy loading for performance
    - Search and URL analysis inputs (matching Tkinter)
    - Article count display
    - Empty state handling
    """
    
    # Signals
    article_clicked = pyqtSignal(dict)
    article_saved = pyqtSignal(str, bool)
    search_requested = pyqtSignal(str)
    url_analysis_requested = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    
    def __init__(
        self,
        on_save: Optional[Callable[[str, bool], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.on_save = on_save
        self.articles: List[Dict[str, Any]] = []
        self.cards: List[ArticleCard] = []
        
        self.setStyleSheet(f"background-color: {COLORS.bg}; border: none;")
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # ─── SEARCH & URL BAR ───
        # Matching Tkinter's "Search Section - Glass card style"
        search_card = QFrame()
        search_card.setStyleSheet(f"""
            background-color: {COLORS.bg_highlight};
            border-radius: 12px;
        """)
        search_layout = QVBoxLayout(search_card)
        search_layout.setContentsMargins(20, 18, 20, 18)
        search_layout.setSpacing(15)
        
        # Row 1: Search
        search_row = QHBoxLayout()
        search_row.setSpacing(12)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"color: {COLORS.cyan}; font-size: 18px;")
        search_row.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tech news...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.fg};
                border: 2px solid {COLORS.border};
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS.cyan};
            }}
        """)
        self.search_input.returnPressed.connect(self._on_search)
        search_row.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.blue};
                color: {COLORS.fg};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bright_blue};
            }}
        """)
        search_btn.clicked.connect(self._on_search)
        search_row.addWidget(search_btn)
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setToolTip("Refresh Feed")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.cyan};
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.bg_search};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        search_row.addWidget(refresh_btn)
        
        search_layout.addLayout(search_row)
        
        # Row 2: URL Analysis
        url_row = QHBoxLayout()
        url_row.setSpacing(12)
        
        url_icon = QLabel("🔗")
        url_icon.setStyleSheet(f"color: {COLORS.magenta}; font-size: 16px;")
        url_row.addWidget(url_icon)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste article URL for deep analysis...")
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.bg_visual};
                color: {COLORS.fg_dark};
                border: 1px solid {COLORS.border};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS.magenta};
            }}
        """)
        self.url_input.returnPressed.connect(self._on_url_analysis)
        url_row.addWidget(self.url_input)
        
        search_layout.addLayout(url_row)
        
        layout.addWidget(search_card)
        
        # ─── FEED HEADER ───
        feed_header = QHBoxLayout()
        
        self.count_label = QLabel("Waiting for content...")
        self.count_label.setStyleSheet(f"color: {COLORS.comment}; font-size: 13px; font-weight: bold;")
        feed_header.addWidget(self.count_label)
        
        feed_header.addStretch()
        
        layout.addLayout(feed_header)
        
        # ─── SCROLL AREA ───
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS.bg};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS.bg_highlight};
                min-height: 20px;
                border-radius: 5px;
            }}
        """)
        
        # Container for cards
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(12)
        self.container_layout.addStretch()
        
        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)
        
        # Initial empty state
        self._show_empty_state()
    
    def _show_empty_state(self) -> None:
        """Show empty state message."""
        self.empty_widget = QFrame()
        self.empty_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.bg_highlight};
                border-radius: 12px;
            }}
        """)
        
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setContentsMargins(40, 60, 40, 60)
        
        icon = QLabel("📭")
        icon.setStyleSheet("font-size: 64px; margin-bottom: 20px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon)
        
        title = QLabel("Feed is Empty")
        title.setStyleSheet(f"color: {COLORS.fg}; font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(title)
        
        subtitle = QLabel("Click 'Start Live Feed' or use the search bar above\nto discover the latest technology news.")
        subtitle.setStyleSheet(f"color: {COLORS.comment}; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(subtitle)
        
        self.container_layout.insertWidget(0, self.empty_widget)
        # Ensure it expands to fill available space visually
        self.empty_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def _hide_empty_state(self) -> None:
        """Hide empty state message."""
        if hasattr(self, 'empty_widget') and self.empty_widget:
            self.empty_widget.deleteLater()
            self.empty_widget = None
    
    def _on_search(self):
        """Handle search."""
        query = self.search_input.text().strip()
        if query:
            self.search_requested.emit(query)
    
    def _on_url_analysis(self):
        """Handle URL analysis."""
        url = self.url_input.text().strip()
        if url:
            self.url_analysis_requested.emit(url)
            self.url_input.clear()
            self.url_input.setPlaceholderText("Analysis started...")
            QTimer.singleShot(2000, lambda: self.url_input.setPlaceholderText("Paste article URL for deep analysis..."))
    
    def set_articles(self, articles: List[Dict[str, Any]]) -> None:
        """
        Set all articles with batched loading to prevent UI freeze.
        
        Args:
            articles: List of article dictionaries
        """
        # Clear existing
        self.clear()
        self._hide_empty_state()
        
        if not articles:
            self._show_empty_state()
            self.count_label.setText("No articles found")
            return
            
        # Store pending articles for batch loading
        self._pending_articles = list(articles)
        self._batch_size = 10  # Load 10 at a time
        self._batch_index = 0
        
        # Update count immediately
        self.count_label.setText(f"Loading {len(articles)} articles...")
        
        # Start batch loading
        self._load_batch()
    
    def _load_batch(self) -> None:
        """Load a batch of articles, then schedule next batch."""
        if not hasattr(self, '_pending_articles') or not self._pending_articles:
            return
        
        # Get next batch
        start = self._batch_index
        end = min(start + self._batch_size, len(self._pending_articles))
        batch = self._pending_articles[start:end]
        
        # Add cards for this batch
        for article in batch:
            card = ArticleCard(article, on_save=self.on_save)
            card.clicked.connect(self.article_clicked.emit)
            card.saved.connect(self.article_saved.emit)
            
            # Insert before stretch
            self.container_layout.insertWidget(self.container_layout.count() - 1, card)
            self.articles.append(article)
            self.cards.append(card)
        
        self._batch_index = end
        
        # Process pending events to keep UI responsive
        QApplication.processEvents()
        
        # Schedule next batch or finish
        if self._batch_index < len(self._pending_articles):
            QTimer.singleShot(10, self._load_batch)  # 10ms delay
        else:
            # Done loading
            self._pending_articles = []
            self._update_count()
    
    def add_article(self, article: Dict[str, Any], prepend: bool = False) -> None:
        """
        Add a single article card.
        
        Args:
            article: Article dictionary
            prepend: If True, add to top of list
        """
        self._hide_empty_state()
        
        card = ArticleCard(article, on_save=self.on_save)
        card.clicked.connect(self.article_clicked.emit)
        card.saved.connect(self.article_saved.emit)
        
        if prepend:
            self.container_layout.insertWidget(0, card)
            self.articles.insert(0, article)
            self.cards.insert(0, card)
        else:
            # Insert before stretch
            self.container_layout.insertWidget(self.container_layout.count() - 1, card)
            self.articles.append(article)
            self.cards.append(card)
        
        self._update_count()
    
    def clear(self) -> None:
        """Clear all articles."""
        for card in self.cards:
            card.deleteLater()
        
        self.cards.clear()
        self.articles.clear()
        self._show_empty_state()
        self._update_count()
    
    def _update_count(self) -> None:
        """Update article count label."""
        count = len(self.articles)
        if count == 0:
            self.count_label.setText("No articles")
        else:
            self.count_label.setText(f"Showing {count} Article{'s' if count != 1 else ''}")
    
    def scroll_to_top(self) -> None:
        """Scroll to top of feed."""
        self.scroll_area.verticalScrollBar().setValue(0)
