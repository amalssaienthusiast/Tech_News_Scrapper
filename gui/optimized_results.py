"""
Optimized Results Display for Tech News Scraper GUI

Features:
- Virtual scrolling (only renders visible items)
- Widget recycling (reuses article cards)
- Efficient pagination
- Memory leak prevention
- Smooth scrolling without jumps
"""

import tkinter as tk
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VirtualResultsDisplay:
    """
    Virtualized results display that only renders visible article cards.
    
    Features:
    - Renders only ~20 visible cards instead of all 1000+
    - Recycles widgets for smooth scrolling
    - Memory-efficient (O(visible) instead of O(total))
    - Smooth 60fps scrolling
    """
    
    def __init__(self, canvas: tk.Canvas, frame: tk.Frame, theme, get_font_func):
        self.canvas = canvas
        self.frame = frame
        self.theme = theme
        self.get_font = get_font_func
        
        # Virtual scrolling state
        self._all_articles: List[Dict[str, Any]] = []
        self._visible_articles: List[Dict[str, Any]] = []
        self._page_size = 20  # Number of visible items
        self._current_page = 0
        
        # Widget recycling pool
        self._card_pool: List[tk.Frame] = []
        self._card_pool_size = 25  # Keep 25 cards in pool
        self._active_cards: Dict[int, tk.Frame] = {}  # index -> card mapping
        
        # Scroll state
        self._scroll_y = 0
        self._card_height = 120  # Estimated card height
        self._total_height = 0
        
        # Debounced scroll handler
        self._scroll_after_id = None
        
        self._setup_virtual_scrolling()
    
    def _setup_virtual_scrolling(self):
        """Setup efficient scroll handling with debouncing."""
        def on_scroll(*args):
            # Debounce scroll events
            if self._scroll_after_id:
                self.canvas.after_cancel(self._scroll_after_id)
            self._scroll_after_id = self.canvas.after(50, self._update_visible_items)
        
        # Bind to canvas scroll
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Configure>', lambda e: self._update_visible_items())
    
    def _on_mousewheel(self, event):
        """Handle mousewheel with smooth scrolling."""
        import platform
        
        if platform.system() == 'Darwin':
            delta = int(-1 * event.delta)
        else:
            delta = int(-1 * (event.delta / 120))
        
        self.canvas.yview_scroll(delta * 3, "units")
        
        # Update visible items after scroll
        if self._scroll_after_id:
            self.canvas.after_cancel(self._scroll_after_id)
        self._scroll_after_id = self.canvas.after(50, self._update_visible_items)
    
    def display_articles(self, articles: List[Dict[str, Any]], append: bool = False):
        """
        Display articles with virtualization.
        
        Args:
            articles: List of article dictionaries
            append: If True, append to existing; else replace
        """
        if append and self._all_articles:
            # Merge and deduplicate
            existing_urls = {a['url'] for a in self._all_articles}
            new_articles = [a for a in articles if a['url'] not in existing_urls]
            self._all_articles = new_articles + self._all_articles  # Newest first
        else:
            self._all_articles = articles
            self._current_page = 0
        
        # Calculate virtual height
        self._total_height = len(self._all_articles) * self._card_height
        
        # Update visible items
        self._update_visible_items()
        
        logger.info(f"Displaying {len(self._visible_articles)} of {len(self._all_articles)} articles")
    
    def _update_visible_items(self):
        """Update which items are visible based on scroll position."""
        if not self._all_articles:
            return
        
        # Get current scroll position
        yview = self.canvas.yview()
        if yview:
            self._scroll_y = yview[0] * self._total_height
        
        # Calculate visible range
        start_idx = int(self._scroll_y / self._card_height)
        start_idx = max(0, start_idx - 2)  # Buffer of 2 above
        end_idx = start_idx + self._page_size + 4  # Buffer of 2 below
        end_idx = min(end_idx, len(self._all_articles))
        
        # Get articles to display
        visible_indices = set(range(start_idx, end_idx))
        self._visible_articles = self._all_articles[start_idx:end_idx]
        
        # Remove cards that are no longer visible
        for idx in list(self._active_cards.keys()):
            if idx not in visible_indices:
                card = self._active_cards.pop(idx)
                self._recycle_card(card)
        
        # Create/update visible cards
        for i, article in enumerate(self._visible_articles):
            idx = start_idx + i
            if idx not in self._active_cards:
                card = self._get_card_from_pool()
                self._active_cards[idx] = card
                self._update_card_content(card, article, idx)
                card.pack(fill=tk.X, pady=2)
        
        # Update scroll region
        self._update_scroll_region()
    
    def _get_card_from_pool(self) -> tk.Frame:
        """Get a card from the recycle pool or create new."""
        if self._card_pool:
            card = self._card_pool.pop()
            # Clear old content
            for widget in card.winfo_children():
                widget.destroy()
            return card
        else:
            return self._create_card_template()
    
    def _recycle_card(self, card: tk.Frame):
        """Return a card to the recycle pool."""
        card.pack_forget()
        if len(self._card_pool) < self._card_pool_size:
            self._card_pool.append(card)
        else:
            card.destroy()
    
    def _create_card_template(self) -> tk.Frame:
        """Create a new empty card template."""
        card = tk.Frame(
            self.frame,
            bg=self.theme.bg_card,
            padx=12,
            pady=8,
            cursor='hand2'
        )
        return card
    
    def _update_card_content(self, card: tk.Frame, article: Dict[str, Any], index: int):
        """Update card with article content."""
        # Title
        title = article.get('title', 'Untitled')
        title_label = tk.Label(
            card,
            text=title[:100] + '...' if len(title) > 100 else title,
            font=self.get_font('sm', 'bold'),
            fg=self.theme.fg,
            bg=self.theme.bg_card,
            wraplength=500,
            justify=tk.LEFT,
            anchor=tk.W
        )
        title_label.pack(fill=tk.X, pady=(0, 4))
        
        # Source and time row
        info_frame = tk.Frame(card, bg=self.theme.bg_card)
        info_frame.pack(fill=tk.X)
        
        source = article.get('source', 'Unknown')
        tk.Label(
            info_frame,
            text=f"📰 {source}",
            font=self.get_font('xs'),
            fg=self.theme.cyan,
            bg=self.theme.bg_card
        ).pack(side=tk.LEFT)
        
        # Score badge
        score = article.get('tech_score', 0)
        if score > 0:
            score_color = self.theme.green if score >= 8 else self.theme.yellow if score >= 5 else self.theme.red
            tk.Label(
                info_frame,
                text=f"⭐ {score:.1f}",
                font=self.get_font('xs', 'bold'),
                fg=score_color,
                bg=self.theme.bg_card
            ).pack(side=tk.RIGHT)
        
        # Bind click event
        def on_click(event, url=article.get('url')):
            self._open_article(url)
        
        card.bind('<Button-1>', on_click)
        title_label.bind('<Button-1>', on_click)
        info_frame.bind('<Button-1>', on_click)
        
        # Store reference
        card.article_url = article.get('url')
        card.article_index = index
    
    def _open_article(self, url: str):
        """Open article URL in browser."""
        import webbrowser
        if url:
            webbrowser.open(url)
    
    def _update_scroll_region(self):
        """Update canvas scroll region efficiently."""
        try:
            if self.canvas.winfo_exists():
                # Set virtual height based on total articles
                self.canvas.configure(scrollregion=(0, 0, 0, self._total_height))
        except Exception as e:
            logger.debug(f"Scroll update error: {e}")
    
    def clear(self):
        """Clear all articles and recycle cards."""
        # Recycle all active cards
        for card in self._active_cards.values():
            self._recycle_card(card)
        self._active_cards.clear()
        
        # Clear data
        self._all_articles.clear()
        self._visible_articles.clear()
        self._scroll_y = 0
        self._current_page = 0
        
        # Reset scroll
        self.canvas.yview_moveto(0)
        
        logger.info("Results display cleared")
    
    def destroy(self):
        """Clean up all resources."""
        self.clear()
        
        # Destroy pooled cards
        for card in self._card_pool:
            card.destroy()
        self._card_pool.clear()
        
        logger.info("Results display destroyed")


class OptimizedArticleFeeder:
    """
    Optimized article feeder with batching and rate limiting.
    
    Features:
    - Batched article display (no UI freezing)
    - Rate limiting for streaming feeds
    - Automatic deduplication
    - Memory-efficient pruning
    """
    
    def __init__(self, virtual_display: VirtualResultsDisplay, max_articles: int = 500):
        self.display = virtual_display
        self.max_articles = max_articles
        self._article_buffer: List[Dict[str, Any]] = []
        self._displayed_urls: set = set()
        self._batch_size = 10
        self._batch_delay_ms = 100
        self._is_processing = False
        
    def feed_articles(self, articles: List[Dict[str, Any]], streaming: bool = False):
        """
        Feed articles with optional streaming mode.
        
        Args:
            articles: List of articles to display
            streaming: If True, process in background batches
        """
        if not articles:
            return
        
        # Deduplicate
        new_articles = []
        for article in articles:
            url = article.get('url')
            if url and url not in self._displayed_urls:
                self._displayed_urls.add(url)
                new_articles.append(article)
        
        if not new_articles:
            return
        
        if streaming:
            # Add to buffer for background processing
            self._article_buffer.extend(new_articles)
            if not self._is_processing:
                self._process_buffer()
        else:
            # Display immediately
            self.display.display_articles(new_articles, append=True)
            self._prune_if_needed()
    
    def _process_buffer(self):
        """Process buffered articles in batches."""
        if not self._article_buffer:
            self._is_processing = False
            return
        
        self._is_processing = True
        
        # Take batch
        batch = self._article_buffer[:self._batch_size]
        self._article_buffer = self._article_buffer[self._batch_size:]
        
        # Display batch
        self.display.display_articles(batch, append=True)
        
        # Prune if needed
        self._prune_if_needed()
        
        # Schedule next batch
        if self._article_buffer:
            self.display.canvas.after(self._batch_delay_ms, self._process_buffer)
        else:
            self._is_processing = False
    
    def _prune_if_needed(self):
        """Remove oldest articles if exceeding max."""
        total = len(self.display._all_articles)
        if total > self.max_articles:
            # Remove oldest (last in list since sorted by time desc)
            to_remove = total - self.max_articles
            self.display._all_articles = self.display._all_articles[:-to_remove]
            
            # Update URL set
            self._displayed_urls = {a.get('url') for a in self.display._all_articles if a.get('url')}
            
            logger.debug(f"Pruned {to_remove} old articles, {len(self.display._all_articles)} remaining")
    
    def clear(self):
        """Clear all articles and reset state."""
        self._article_buffer.clear()
        self._displayed_urls.clear()
        self._is_processing = False


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def create_optimized_results_section(parent, theme, get_font_func):
    """
    Create optimized results section for GUI.
    
    Usage:
        results_section = create_optimized_results_section(root, THEME, get_font)
        results_section.feeder.feed_articles(articles, streaming=True)
    """
    # Results container
    results_container = tk.Frame(parent, bg=theme.bg)
    results_container.pack(fill=tk.BOTH, expand=True)
    
    # Canvas and scrollbar
    canvas = tk.Canvas(
        results_container,
        bg=theme.bg,
        highlightthickness=0,
        bd=0
    )
    
    scrollbar = tk.Scrollbar(
        results_container,
        orient=tk.VERTICAL,
        command=canvas.yview,
        bg=theme.bg_highlight
    )
    
    results_frame = tk.Frame(canvas, bg=theme.bg)
    
    canvas.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    canvas_window = canvas.create_window(
        (0, 0),
        window=results_frame,
        anchor=tk.NW,
        width=parent.winfo_width() if hasattr(parent, 'winfo_width') else 800
    )
    
    # Create virtual display
    virtual_display = VirtualResultsDisplay(canvas, results_frame, theme, get_font_func)
    
    # Create optimized feeder
    feeder = OptimizedArticleFeeder(virtual_display)
    
    return {
        'canvas': canvas,
        'frame': results_frame,
        'virtual_display': virtual_display,
        'feeder': feeder
    }
